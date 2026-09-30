import logging
import queue
import threading
import time

import numpy as np

from talk2type.core.states import DictationStateMachine, State
from talk2type.db.service import save_transcription

log = logging.getLogger(__name__)

MIN_SAMPLES = 4800  # ~0.3 s @ 16 kHz -- shorter is an accidental tap


class DictationPipeline:
    """Orchestrates record -> STT -> LLM -> paste with cancellation between stages."""

    def __init__(self, machine, recorder, transcription, cleanup, paste,
                 level_callback=None,
                 begin_use=lambda: None, end_use=lambda: None):
        self._machine = machine
        self._recorder = recorder
        self._transcription = transcription
        self._cleanup = cleanup
        self._paste = paste
        self._level_callback = level_callback
        self._begin_use = begin_use
        self._end_use = end_use
        self._event_lock = threading.RLock()
        # written/read only from the pynput listener thread (events arrive
        # sequentially); workers get their token as an argument, not via this attr
        self._token: threading.Event | None = None
        self._stopped = False
        self._jobs = queue.Queue()
        threading.Thread(target=self._work, daemon=True).start()

    # --- events (pynput thread) ---

    def on_press(self, lang: str) -> None:
        with self._event_lock:
            if self._stopped or not self._machine.press(lang):
                return
            self._begin_use()
            try:
                self._recorder.start(level_callback=self._level_callback)
            except Exception:
                log.exception("Recording start failed")
                self._end_use()
                self._machine.release()
                self._machine.finish("error")
                return
            self._token = threading.Event()
            self._submit(self._preload, (), self._token)
            log.info("Recording started [%s]", lang)

    def on_release(self, _lang: str | None = None) -> None:
        with self._event_lock:
            if not self._machine.release():
                return
            try:
                audio = self._recorder.stop()
            except Exception:
                log.exception("Recording stop failed")
                self._token.set()
                self._end_use()
                self._machine.finish("error")
                return
            if audio.size < MIN_SAMPLES:
                log.info("Audio too short (%d samples) -- discarded", audio.size)
                self._token.set()
                self._end_use()
                self._machine.finish("too_short")
                return
            self._submit(self._run, (audio, self._machine.lang, self._token), self._token)
            self._end_use()

    def on_cancel(self) -> None:
        with self._event_lock:
            if self._token is not None:
                self._token.set()
            prev = self._machine.cancel()
            if prev is State.RECORDING:
                try:
                    self._recorder.stop()
                except Exception:
                    log.exception("Recording cancel failed")
                finally:
                    self._end_use()
                log.info("Recording cancelled")
            elif prev is State.PROCESSING and self._token is not None:
                log.info("Processing cancelled -- result will be discarded")

    def stop(self) -> None:
        with self._event_lock:
            self._stopped = True
            self.on_cancel()

    # --- worker thread ---

    def _submit(self, callback, args, token):
        self._begin_use()
        self._jobs.put((callback, args, token))

    def _work(self) -> None:
        while True:
            callback, args, token = self._jobs.get()
            try:
                if not token.is_set():
                    callback(*args)
            finally:
                self._end_use()
                self._jobs.task_done()

    def _preload(self) -> None:
        try:
            self._transcription.preload()
            self._cleanup.preload()
        except Exception:
            log.exception("Preload failed")

    def _run(self, audio: np.ndarray, lang: str, token: threading.Event) -> None:
        try:
            t0 = time.monotonic()
            raw = self._transcription.transcribe(audio, language=lang)
            stt_ms = int((time.monotonic() - t0) * 1000)
            if token.is_set():
                log.info("Cancelled after STT -- discarded: %s", raw)
                return
            log.info("STT [%s] %dms: %s", lang, stt_ms, raw)

            t1 = time.monotonic()
            cleaned = self._cleanup.cleanup(raw, language=lang)
            llm_ms = int((time.monotonic() - t1) * 1000)
            if token.is_set():
                log.info("Cancelled after LLM -- discarded: %s", cleaned)
                return
            log.info("LLM %dms: %s", llm_ms, cleaned)

            with self._event_lock:
                if token.is_set():
                    return
                self._paste.paste(cleaned)
            if raw:
                save_transcription(raw, cleaned, stt_ms=stt_ms, llm_ms=llm_ms)
        except Exception:
            log.exception("Pipeline failed")
            with self._event_lock:
                if not token.is_set():
                    self._machine.finish("error")
        else:
            with self._event_lock:
                if not token.is_set():
                    self._machine.finish("done")
