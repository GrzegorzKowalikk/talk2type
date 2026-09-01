import gc
import importlib.util
import logging
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from sqlmodel import select

from talk2type.config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_MODEL
from talk2type.db.engine import get_session
from talk2type.db.model import Hotword

log = logging.getLogger(__name__)


def _add_cuda_dll_dirs() -> None:
    """ctranslate2 loads cublas64_12/cudnn64_9 at runtime via PATH search on
    Windows; the nvidia-*-cu12 wheels ship DLLs a CUDA 13 toolkit doesn't have."""
    if sys.platform != "win32":
        return
    for pkg in ("cublas", "cudnn"):
        spec = importlib.util.find_spec(f"nvidia.{pkg}")
        if spec is None or not spec.submodule_search_locations:
            continue
        bin_dir = Path(spec.submodule_search_locations[0]) / "bin"
        if bin_dir.is_dir():
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


_add_cuda_dll_dirs()


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
        self._get_model()

    def _get_model(self) -> WhisperModel:
        """Load-and-return under one lock so a concurrent unload() can't
        null the model between loading it and using it."""
        with self._load_lock:
            if self._model is None:
                t0 = time.monotonic()
                self._model = WhisperModel(
                    WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
                )
                log.info(
                    "Whisper loaded (%s, %s) in %.1fs",
                    WHISPER_MODEL, WHISPER_COMPUTE, time.monotonic() - t0,
                )
            return self._model

    def transcribe(self, audio: np.ndarray, language: str = "pl") -> str:
        model = self._get_model()
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            hotwords=self._hotwords,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.4,
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
