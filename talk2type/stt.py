import gc

import numpy as np
from faster_whisper import WhisperModel

from .config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_MODEL


class WhisperSTT:
    def __init__(self):
        self._model: WhisperModel | None = None

    def _ensure_loaded(self):
        if self._model is None:
            self._model = WhisperModel(
                WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
            )

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
