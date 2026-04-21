import gc
import logging
import time

import numpy as np
from faster_whisper import WhisperModel

from .config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_MODEL

log = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(self):
        self._model: WhisperModel | None = None

    def _ensure_loaded(self):
        if self._model is None:
            t0 = time.monotonic()
            self._model = WhisperModel(
                WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
            )
            log.info("Whisper loaded (%s, %s) in %.1fs", WHISPER_MODEL, WHISPER_COMPUTE, time.monotonic() - t0)

    def transcribe(self, audio: np.ndarray, language: str = "pl") -> str:
        self._ensure_loaded()
        segments, _info = self._model.transcribe(
            audio, language=language, beam_size=5, vad_filter=True
        )
        return "".join(seg.text for seg in segments).strip()

    def unload(self):
        if self._model is not None:
            del self._model
            self._model = None
            gc.collect()
            log.info("Whisper unloaded")
