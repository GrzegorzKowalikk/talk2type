import logging
from pathlib import Path

WHISPER_MODEL = "turbo"
WHISPER_COMPUTE = "int8_float16"
WHISPER_DEVICE = "cuda"

OLLAMA_MODEL = "qwen3.5:2b"

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"

HOTKEY_PL = "f9"
HOTKEY_EN = "f10"

IDLE_TIMEOUT_SEC = 180
FULLSCREEN_POLL_SEC = 5


def setup_logging():
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "wisprflow.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
