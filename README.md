# talk2type

Push-to-talk voice dictation for Windows. Hold a hotkey → speak → release → transcribed text is pasted at your cursor. Supports Polish and English. All processing runs locally.

**Pipeline:** microphone → faster-whisper (GPU) → Ollama LLM cleanup → clipboard paste

---

## Requirements

### Hardware
- **GPU**: NVIDIA with CUDA support (RTX 2060 or newer recommended)
- **VRAM**: ~2 GB for Whisper turbo + ~3 GB for the LLM (models unload automatically when idle)
- **RAM**: 8 GB+

### Software
- **Windows 10/11** (64-bit)
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[Ollama](https://ollama.com/)** — local LLM runtime
- **NVIDIA driver** (up to date) — no CUDA Toolkit needed; cuBLAS/cuDNN for CUDA 12 install automatically with `uv sync`

---

## Installation

### 1. Install uv

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install Ollama

Download from [ollama.com](https://ollama.com/) and run the installer. After installation, Ollama runs as a background service automatically.

### 3. Pull the LLM model

```powershell
ollama pull qwen3.5:2b
```

> Default model is `qwen3.5:2b`. To use a different one, change `OLLAMA_MODEL` in `talk2type/config.py`.

### 4. Clone the repo

```powershell
git clone https://github.com/Dziadek/talk2type.git
cd talk2type
```

### 5. Create virtual environment and install dependencies

```powershell
uv sync
```

This installs all dependencies including `faster-whisper`, `PySide6`, `pystray`, `pynput`, `sounddevice`, and `pywin32`.

### 6. Verify CUDA is available

```powershell
uv run python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"
```

If the output is `1` or more, CUDA is available. If `0`, check that your NVIDIA driver is up to date. faster-whisper uses CTranslate2 (not PyTorch); the CUDA 12 runtime libraries it needs (cuBLAS, cuDNN 9) are installed by `uv sync` via the `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` packages — no system CUDA Toolkit required.

---

## Running

```powershell
uv run python main.py
```

A tray icon appears in the system notification area. The app runs silently in the background.

---

## Usage

| Action | Result |
|---|---|
| Hold **F9** | Record audio — Polish transcription |
| Hold **F10** | Record audio — English transcription |
| Release hotkey | Stops recording, transcribes, cleans up text, pastes at cursor |
| Right-click tray icon → Quit | Graceful shutdown (unloads models from VRAM) |

The overlay window appears while recording and shows a real-time audio level visualizer.

### First use
Whisper model (`turbo`) downloads from HuggingFace on first run (~1.5 GB). Subsequent starts load from the local cache.

---

## Configuration

Edit `talk2type/config.py`:

```python
WHISPER_MODEL   = "turbo"          # Whisper model size: tiny / base / small / medium / large-v3 / turbo
WHISPER_COMPUTE = "int8_float16"   # Quantization: int8 / int8_float16 / float16
WHISPER_DEVICE  = "cuda"           # "cuda" or "cpu"

OLLAMA_MODEL = "qwen3.5:2b"        # Any model available in your Ollama installation

HOTKEY_PL = "f9"                   # Polish dictation hotkey
HOTKEY_EN = "f10"                  # English dictation hotkey

IDLE_TIMEOUT_SEC  = 180            # Unload Whisper after N seconds of inactivity
FULLSCREEN_POLL_SEC = 5            # How often to check for fullscreen apps (seconds)
```

### Changing the LLM model

```powershell
ollama pull bielik-11b-v2.3-instruct:Q8_0   # example heavier Polish-tuned model
```

Then update `OLLAMA_MODEL` in `config.py`.

---

## Autostart on Windows login

Registers a Windows Task Scheduler task that launches talk2type **30 seconds after logon** — the delay lets Windows finish loading first, which keeps boot fast.

The installer also adds a branded **talk2type** profile to Windows Terminal (microphone icon, blue tab) and the task opens that profile, so the app runs in a clearly labelled terminal. A single-instance lock guarantees only one copy ever runs, even if Windows reopens a previous terminal.

**Install:**

```powershell
uv run python scripts/install_autostart.py
```

**Uninstall:**

```powershell
uv run python scripts/install_autostart.py --uninstall
```

To adjust the delay, change `DELAY` in `scripts/install_autostart.py` (ISO 8601 duration, e.g. `PT60S` for 60 seconds), then reinstall.

> The task uses `MultipleInstancesPolicy=IgnoreNew`, so triggering it manually while it is already running has no effect.

---

## Resource management

talk2type automatically manages VRAM:

- **Whisper** unloads after `IDLE_TIMEOUT_SEC` (default 3 min) of no recordings
- **Whisper** also unloads when a fullscreen application is detected (games, video)
- **LLM** keeps alive for 3 minutes after the last call, then Ollama evicts it
- Both models unload cleanly on quit

---

## Logs

Logs are written to `logs/wisprflow.log` and also printed to the console. Each transcription shows timing:

```
14:32:01 INFO talk2type.stt: Whisper loaded (turbo, int8_float16) in 2.3s
14:32:04 INFO talk2type.llm: LLM call: 0.84s
```

---

## Running tests

Unit tests (no GPU/Ollama required):

```powershell
uv run pytest
```

Integration tests (requires running Ollama + CUDA GPU):

```powershell
uv run pytest -m integration
```

---

## Project structure

```
talk2type/
  audio.py        — microphone recording (sounddevice, queue-based)
  stt.py          — Whisper STT wrapper (lazy load/unload)
  llm.py          — Ollama LLM cleanup call
  prompts.py      — system prompts for PL/EN cleanup
  hotkey.py       — F9/F10 push-to-talk listener (pynput)
  paste.py        — clipboard write + Ctrl+V paste
  overlay.py      — Qt recording indicator with audio visualizer
  tray.py         — system tray icon (pystray)
  resource_mgr.py — idle/fullscreen detection, model unload scheduling
  config.py       — all tuneable constants

scripts/
  install_autostart.py  — Task Scheduler autostart manager (30s delay after logon)

tests/            — unit tests (pytest + pytest-mock)
tests/integration/— integration tests (real GPU + Ollama)
```

---

## Troubleshooting

**No audio recorded / silent transcription**
- Check that your microphone is set as the default recording device in Windows Sound settings.
- `sounddevice` uses the Windows default input device. Change it in Control Panel → Sound → Recording.

**`CUDA error: no kernel image is available for execution on the device`**
- Your GPU driver is too old. Update to the latest NVIDIA driver from [nvidia.com](https://www.nvidia.com/drivers).

**`RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`**
- CTranslate2 needs the CUDA **12** runtime DLLs; a system CUDA 13 toolkit only ships `cublas64_13.dll`, which does not satisfy it.
- Run `uv sync` — the `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` packages provide the DLLs and the app adds them to `PATH` at startup.

**Ollama not reachable**
- Make sure Ollama is running: `ollama serve` or check the system tray for the Ollama icon.
- Default endpoint is `http://localhost:11434`. Ollama auto-starts on login after installation.

**Hotkeys conflict with another app**
- Change `HOTKEY_PL` / `HOTKEY_EN` in `config.py` to any `pynput` key name (e.g. `"f7"`, `"f8"`).

**LLM returns garbage / wrong language cleanup**
- Try a stronger model: `ollama pull qwen3:8b` and update `OLLAMA_MODEL`.
- Or set `OLLAMA_MODEL = ""` equivalent by bypassing `llm.cleanup_text` — edit `main.py` to skip the LLM step.
