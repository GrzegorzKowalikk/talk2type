import logging
import threading
import time

import numpy as np

from talk2type.core.cancellation import CancellationToken
from talk2type.core.states import DictationStateMachine, State
from talk2type.db.service import save_transcription

log = logging.getLogger(__name__)

MIN_SAMPLES = 4800  # ~0.3 s @ 16 kHz -- shorter is an accidental tap


class DictationPipeline:
    """Orchestrates record -> STT -> LLM -> paste with cancellation between stages."""

    def __init__(self, machine, recorder, transcription, cleanup, paste,
                 level_callback=None, on_activity=lambda: None):
        self._machine = machine
        self._recorder = recorder
        self._transcription = transcription
        self._cleanup = cleanup
        self._paste = paste
        self._level_callback = level_callback
        self._on_activity = on_activity
        # written/read only from the pynput listener thread (events arrive
        # sequentially); workers get their token as an argument, not via this attr
        self._token: CancellationToken | None = None

    # --- events (pynput thread) ---

    def on_press(self, lang: str) -> None:
        if not self._machine.press(lang):
            return
        self._on_activity()
        self._recorder.start(level_callback=self._level_callback)
        threading.Thread(target=self._preload, daemon=True).start()
        log.info("Recording started [%s]", lang)

    def on_release(self, _lang: str | None = None) -> None:
        if not self._machine.release():
            return
        audio = self._recorder.stop()
        if audio.size < MIN_SAMPLES:
            log.info("Audio too short (%d samples) -- discarded", audio.size)
            self._machine.finish("too_short")
            return
        token = CancellationToken()
        self._token = token
        threading.Thread(
            target=self._run, args=(audio, self._machine.lang, token), daemon=True
        ).start()

    def on_cancel(self) -> None:
        prev = self._machine.cancel()
        if prev is State.RECORDING:
            self._recorder.stop()
            log.info("Recording cancelled")
        elif prev is State.PROCESSING and self._token is not None:
            self._token.cancel()
            log.info("Processing cancelled -- result will be discarded")

    # --- worker thread ---

    def _preload(self) -> None:
        try:
            self._transcription.preload()
            self._cleanup.preload()
        except Exception:
            log.exception("Preload failed")

    def _run(self, audio: np.ndarray, lang: str, token: CancellationToken) -> None:
        try:
            t0 = time.monotonic()
            raw = self._transcription.transcribe(audio, language=lang)
            stt_ms = int((time.monotonic() - t0) * 1000)
            if token.cancelled:
                log.info("Cancelled after STT -- discarded: %s", raw)
                return
            self._on_activity()
            log.info("STT [%s] %dms: %s", lang, stt_ms, raw)

            t1 = time.monotonic()
            cleaned = self._cleanup.cleanup(raw, language=lang)
            llm_ms = int((time.monotonic() - t1) * 1000)
            if token.cancelled:
                log.info("Cancelled after LLM -- discarded: %s", cleaned)
                return
            log.info("LLM %dms: %s", llm_ms, cleaned)

            self._paste.paste(cleaned)
            if raw:
                save_transcription(raw, cleaned, stt_ms=stt_ms, llm_ms=llm_ms)
        except Exception:
            log.exception("Pipeline failed")
            if not token.cancelled:
                self._machine.finish("error")
        else:
            if not token.cancelled:
                self._machine.finish("done")
