import logging
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "history.db"

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
ICON_ICO = IMAGES_DIR / "icon.ico"
APP_ID = "talk2type"

WHISPER_MODEL = "large-v3"
WHISPER_COMPUTE = "float16"
WHISPER_DEVICE = "cuda"

# Words Whisper often mishears — listed here so beam search favours correct spelling.
WHISPER_HOTWORDS = [
    "Claude",
    "Claude Code",
    "Anthropic",
    "Talk2Type",
    "CLAUDE.md",
    "claude-mem",
    "Terragrunt",
    "Obsidian",
    "Graphify",
    "eval",
    "Matt Pocock",
    "Bedrock",
    "GenAI",
]

OLLAMA_MODEL = "qwen3.5:2b"

# Whisper alone is usually enough; flip to True to run LLM cleanup on top.
USE_LLM = False

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"

HOTKEY_PL = "f9"
HOTKEY_EN = "f10"

IDLE_TIMEOUT_SEC = 900
FULLSCREEN_POLL_SEC = 5


def setup_logging():
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    file_handler = logging.FileHandler(log_dir / "wisprflow.log")
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
    )
