import gc
import logging
import threading
import time

import numpy as np
from faster_whisper import WhisperModel
from sqlmodel import select

from talk2type.config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_MODEL
from talk2type.db.engine import get_session
from talk2type.db.model import Hotword

log = logging.getLogger(__name__)


class TranscriptionService:
    """Whisper STT with background preload and in-memory hotword cache."""

    def __init__(self):
        self._model: WhisperModel | None = None
        self._load_lock = threading.Lock()
        self._hotwords: str | None = None
        self.refresh_hotwords()

    def refresh_hotwords(self) -> None:
        with get_session() as s:
            words = [h.word for h in s.exec(select(Hotword)).all()]
        self._hotwords = ", ".join(words) if words else None

    def preload(self) -> None:
        with self._load_lock:
            if self._model is not None:
                return
            t0 = time.monotonic()
            self._model = WhisperModel(
                WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
            )
            log.info(
                "Whisper loaded (%s, %s) in %.1fs",
                WHISPER_MODEL, WHISPER_COMPUTE, time.monotonic() - t0,
            )

    def transcribe(self, audio: np.ndarray, language: str = "pl") -> str:
        self.preload()
        with self._load_lock:
            # local ref: ResourceManager may unload() concurrently mid-transcription
            model = self._model
        assert model is not None
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            hotwords=self._hotwords,
        )
        return "".join(seg.text for seg in segments).strip()

    def unload(self) -> None:
        with self._load_lock:
            if self._model is None:
                return
            del self._model
            self._model = None
        gc.collect()
        log.info("Whisper unloaded")
