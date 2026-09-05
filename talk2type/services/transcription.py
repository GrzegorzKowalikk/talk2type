import gc
import importlib.util
import logging
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.utils import _MODELS
from huggingface_hub import model_info, try_to_load_from_cache
from huggingface_hub.constants import HF_HUB_CACHE
from sqlmodel import select
from tqdm.auto import tqdm as _tqdm_base

from talk2type.config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_MODEL
from talk2type.db.engine import get_session
from talk2type.db.model import Hotword

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str], None]  # label, detail

# Files that faster-whisper downloads for a model
_MODEL_FILES = ("config.json", "model.bin", "tokenizer.json")

# Expected time (seconds) for loading large-v3 onto GPU.
_EXPECTED_LOAD_SEC = 6.0


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


def _is_model_cached(model_name: str) -> bool:
    """Check if model files are already in the HuggingFace cache."""
    repo_id = _MODELS.get(model_name, model_name)
    for fname in _MODEL_FILES:
        result = try_to_load_from_cache(repo_id, fname)
        if result is None or isinstance(result, type(None)):
            return False
    return True


def _get_repo_size(repo_id: str) -> int:
    """Fetch total size of model files from HuggingFace Hub."""
    try:
        info = model_info(repo_id, files_metadata=True)
        return sum(s.size for s in info.siblings if s.size)
    except Exception:
        return 0


def _scan_dir_size(path: Path) -> int:
    """Recursively sum file sizes including .incomplete partials."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _fmt_gb(b: int) -> str:
    return f"{b / 1_073_741_824:.1f}"


def _make_progress_tqdm(label: str, cb: ProgressCallback):
    """Create a tqdm subclass that forwards progress to *cb* without console output."""

    class _ProgressTqdm(_tqdm_base):
        def __init__(self, *args, **kwargs):
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)
            self._progress_total = kwargs.get("total") or (args[0] if args else None)
            self._progress_n = 0.0

        def update(self, n=1):
            super().update(n)
            self._progress_n += n
            if self._progress_total and self._progress_total > 0:
                pct = min(int(self._progress_n / self._progress_total * 100), 99)
                cb(label, f"{pct}%")

        def close(self):
            super().close()

    return _ProgressTqdm


_add_cuda_dll_dirs()


class TranscriptionService:
    """Whisper STT with background preload and in-memory hotword cache."""

    def __init__(self):
        self._model: WhisperModel | None = None
        self._load_lock = threading.Lock()
        self._hotwords: str | None = None
        self._progress_cb: ProgressCallback | None = None
        self.refresh_hotwords()

    def set_progress_callback(self, cb: ProgressCallback | None) -> None:
        self._progress_cb = cb

    def refresh_hotwords(self) -> None:
        with get_session() as s:
            words = [h.word for h in s.exec(select(Hotword)).all()]
        self._hotwords = ", ".join(words) if words else None

    def preload(self) -> None:
        self._get_model()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _get_model(self) -> WhisperModel:
        """Load-and-return under one lock so a concurrent unload() can't
        null the model between loading it and using it."""
        with self._load_lock:
            if self._model is None:
                cb = self._progress_cb
                needs_download = not _is_model_cached(WHISPER_MODEL)

                if needs_download:
                    self._model = self._download_and_load(cb)
                else:
                    self._model = self._load_into_memory(cb)
            return self._model

    def _download_and_load(self, cb: ProgressCallback | None) -> WhisperModel:
        """Download model files with directory-size monitoring for progress."""
        repo_id = _MODELS.get(WHISPER_MODEL, WHISPER_MODEL)
        total_bytes = _get_repo_size(repo_id)
        total_gb = _fmt_gb(total_bytes) if total_bytes else "?"

        # HuggingFace cache directory for this repo
        cache_dir = Path(HF_HUB_CACHE) / f"models--{repo_id.replace('/', '--')}"

        if cb:
            cb("Pobieram...", f"0.0/{total_gb} GB")

        done = threading.Event()

        def _monitor():
            while not done.wait(0.3):
                downloaded = _scan_dir_size(cache_dir)
                dl_gb = _fmt_gb(downloaded)
                if cb:
                    cb("Pobieram...", f"{dl_gb}/{total_gb} GB")

        if cb and total_bytes:
            threading.Thread(target=_monitor, daemon=True).start()

        t0 = time.monotonic()
        model = WhisperModel(
            WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
        )
        done.set()

        if cb:
            cb("Pobieram...", f"{total_gb}/{total_gb} GB")
        log.info(
            "Whisper downloaded+loaded (%s, %s) in %.1fs",
            WHISPER_MODEL, WHISPER_COMPUTE, time.monotonic() - t0,
        )
        return model

    def _load_into_memory(self, cb: ProgressCallback | None) -> WhisperModel:
        """Load cached model into GPU memory with timer-based progress."""
        if cb:
            cb("Ładuję model do pamięci...", "0%")

        done = threading.Event()

        def _estimate_progress():
            t0 = time.monotonic()
            while not done.wait(0.15):
                elapsed = time.monotonic() - t0
                frac = 1.0 - math.exp(-1.5 * elapsed / _EXPECTED_LOAD_SEC)
                pct = min(int(frac * 95), 95)
                if cb:
                    cb("Ładuję model do pamięci...", f"{pct}%")

        if cb:
            threading.Thread(target=_estimate_progress, daemon=True).start()

        t0 = time.monotonic()
        model = WhisperModel(
            WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE
        )
        done.set()

        if cb:
            cb("Ładuję model do pamięci...", "100%")
        log.info(
            "Whisper loaded (%s, %s) in %.1fs",
            WHISPER_MODEL, WHISPER_COMPUTE, time.monotonic() - t0,
        )
        return model

    def transcribe(self, audio: np.ndarray, language: str = "pl") -> str:
        model = self._get_model()
        cb = self._progress_cb

        # Monkey-patch tqdm in faster_whisper.transcribe to capture STT progress
        import faster_whisper.transcribe as _fw_transcribe

        orig_tqdm = _fw_transcribe.tqdm
        if cb:
            _fw_transcribe.tqdm = _make_progress_tqdm("Przetwarzam...", cb)

        try:
            segments, _info = model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                log_progress=bool(cb),
                hotwords=self._hotwords,
                condition_on_previous_text=False,
                temperature=0.0,
                no_speech_threshold=0.4,
            )
            text = "".join(seg.text for seg in segments).strip()
        finally:
            _fw_transcribe.tqdm = orig_tqdm

        if cb:
            cb("Przetwarzam...", "100%")
        return text

    def unload(self) -> None:
        with self._load_lock:
            if self._model is None:
                return
            del self._model
            self._model = None
        gc.collect()
        log.info("Whisper unloaded")


