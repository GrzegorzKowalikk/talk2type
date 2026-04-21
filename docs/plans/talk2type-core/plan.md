# talk2type — plan implementacji (core)

> Python-owy klon Wispr Flow dla Windows. Push-to-talk → Whisper → qwen3.5:2b → paste.
> Stack zablokowany 2026-04-20. Plan tworzony per CLAUDE.md (docs-first, make-plan).
> **Paczka przemianowana z `wisprflow` na `talk2type` (commit 2026-04-20).**

---

## Cel

Aplikacja trayowa, która przy trzymaniu F9/F10 nagrywa głos, transkrybuje przez Whisper, czyści przez LLM i wkleja wynik w aktywne pole. Dwa języki: **F9 = PL**, **F10 = EN**.

**Target latency (warm):** 1.0–1.2 s = ~300 ms Whisper + ~700 ms LLM + ~50 ms paste.
**Peak VRAM:** ~2.7 GB aktywnie (sekwencyjnie — Whisper i LLM nie siedzą razem). **0 GB idle/gaming.**

---

## Phase 0 — Documentation Discovery (DONE)

Zweryfikowane przez subagenty + context7 2026-04-20. Zapisane jako "Allowed APIs" poniżej. **Nie używaj niczego spoza tej listy bez ponownej weryfikacji w context7.**

### ✅ Allowed APIs (zweryfikowane)

#### faster-whisper (`/systran/faster-whisper`)
```python
from faster_whisper import WhisperModel
model = WhisperModel("turbo", device="cuda", compute_type="int8_float16")
segments, info = model.transcribe(audio, language="pl", beam_size=5, vad_filter=True)
full_text = "".join(seg.text for seg in segments)
# unload: del model; gc.collect()  — BRAK oficjalnego API .close()/.unload()
```
- Model string: **`"turbo"`** (alias). `"large-v3-turbo"` nie jest literalnie w docs — używaj `"turbo"`.
- `language`: `"pl"` / `"en"` (kody Whispera).
- `segments` to lazy generator — iterowanie wykonuje transkrypcję.
- `segment.text` ma zwykle leading space → `"".join(...)` czystsze niż `" ".join(...)`.
- **BRAK** `.unload()` / `.close()`. Zwolnienie VRAM: `del model; gc.collect()` (CTranslate2 zwolni w destruktorze).

#### ollama (Python SDK, `/ollama/ollama-python`)
```python
from ollama import chat
response = chat(
    model='qwen3.5:2b',
    messages=[{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': text}],
    think=False,          # ← top-level kwarg, NIE w options
    keep_alive=0,         # ← top-level, 0 = unload natychmiast
    options={'temperature': 0.1, 'num_predict': 128},
)
text = response.message.content   # albo response['message']['content']
```
- `think`, `keep_alive` → **top-level parametry `chat()`**, nie w `options`.
- `keep_alive=0` (int) → auto-unload po odpowiedzi = **brak potrzeby ręcznego `ollama stop`**.
- Import: `from ollama import chat` (idiomatycznie).

#### sounddevice (`/spatialaudio/python-sounddevice`)
```python
import sounddevice as sd
import queue, numpy as np

q = queue.Queue()
def cb(indata, frames, time, status):
    q.put(indata.copy())

stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', callback=cb)
stream.start()
# ... key trzymany ...
stream.stop(); stream.close()
audio = np.concatenate(list(q.queue), axis=0).flatten()   # (N,) float32 dla Whispera
```
- Wyjście: shape `(frames, channels)` → `.flatten()` dla mono.
- `dtype='float32'` (domyślny).

#### pynput (`/moses-palmer/pynput`)
```python
from pynput import keyboard

def on_press(key, injected=None):
    if key == keyboard.Key.f9: ...   # PL
    if key == keyboard.Key.f10: ...  # EN

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()   # non-blocking; listener.stop() żeby zatrzymać

# Paste (Ctrl+V):
from pynput.keyboard import Controller, Key
kb = Controller()
with kb.pressed(Key.ctrl):
    kb.press('v'); kb.release('v')
```
- **`Key.alt_r`** ✅ istnieje, ale odrzucona z powodu AltGr conflict na PL layout (emituje Ctrl_L+Alt_R razem).
- **`Key.f9`** / **`Key.f10`** ✅ używane jako hotkeys — niezawodne, bezkolizyjne.
- `Key.alt_gr` **NIE istnieje** w pynput enum.
- Callback może mieć `injected` kwarg (nowsze pynput).

#### pyperclip (`/asweigart/pyperclip`)
```python
import pyperclip
pyperclip.copy("tekst z polskimi ąęść")   # Win32 clipboard via ctypes, UTF-16
```
- Plaintext only (nie rich text). Polskie znaki działają w praktyce.

#### pystray (`/moses-palmer/pystray`)
```python
from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading

img = Image.new("RGB", (64, 64), "gray")
icon = Icon("wisprflow", img, "own_wisprflow", Menu(
    MenuItem("Quit", lambda i, _: i.stop()),
))
threading.Thread(target=icon.run, daemon=True).start()   # icon.run() BLOKUJE
icon.icon = Image.new("RGB", (64, 64), "red")   # update: reassign .icon
```
- `icon.run()` blokuje → **zawsze w osobnym wątku**.
- Update ikony: `icon.icon = new_image`.

#### pywin32 (win32gui / win32api)
```python
import win32gui, win32api, win32con

def is_fullscreen() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd: return False
    if win32gui.GetClassName(hwnd) in ("Progman", "WorkerW", "Shell_TrayWnd", "Button"):
        return False
    if not win32gui.GetWindowText(hwnd): return False
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return l == 0 and t == 0 \
        and (r - l) == win32api.GetSystemMetrics(win32con.SM_CXSCREEN) \
        and (b - t) == win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
```

#### Windows Startup folder (pywin32 IShellLink)
```python
import os, pythoncom
from win32com.shell import shell, shellcon

link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
link.SetPath(r"C:\path\to\pythonw.exe")
link.SetArguments(r"C:\path\to\main.py")
link.SetWorkingDirectory(r"C:\path\to")
startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
link.QueryInterface(pythoncom.IID_IPersistFile).Save(
    os.path.join(startup, "own_wisprflow.lnk"), 0)
```
- `pythonw.exe` (nie `python.exe`) — brak okna konsoli.

### 🚫 Anti-patterns (NIE używaj)
- `WhisperModel("large-v3-turbo", ...)` — użyj `"turbo"`.
- `WhisperModel(...).unload()` / `.close()` / `.to("cpu")` — **nie istnieje**.
- `torch.cuda.empty_cache()` po usunięciu Whispera — **nic nie robi** (CT2 nie jest torch).
- `ollama.chat(..., options={'think': False})` — `think` jest **top-level**, nie w options.
- `ollama.chat(..., options={'keep_alive': 0})` — `keep_alive` jest **top-level**.
- `Key.alt_gr` — **nie istnieje** w pynput. `Key.alt_r` istnieje, ale odrzucona — używaj `Key.f9`/`Key.f10`.
- `icon.run()` w głównym wątku — **blokuje** całą apkę.
- `python.exe` w skrócie Startup — pokazuje okno konsoli. Użyj `pythonw.exe`.

---

## Struktura projektu

```
own_wisprflow/
├── main.py                      # orchestrator (glue)
├── pyproject.toml               # deps
├── images/
│   └── icon.png                 # tray icon (PNG)
├── talk2type/
│   ├── __init__.py
│   ├── config.py                # stałe: modele, hotkeys, timeouts + setup_logging()
│   ├── audio.py                 # Recorder (push-to-talk) + level_callback
│   ├── stt.py                   # WhisperSTT (load/transcribe/unload) + logging
│   ├── llm.py                   # cleanup_text (ollama chat) + timing log
│   ├── paste.py                 # clipboard + Ctrl+V
│   ├── hotkey.py                # pynput listener
│   ├── tray.py                  # pystray icon + menu (real PNG, set_state stub)
│   ├── resource_mgr.py          # idle timer + fullscreen detector + logging
│   ├── overlay.py               # PySide6 floating pill UI (recording/processing)
│   └── prompts.py               # system prompts PL/EN
├── scripts/
│   └── install_autostart.py     # tworzy .lnk w Startup
├── tests/
│   ├── test_audio.py
│   ├── test_stt.py
│   ├── test_llm.py
│   ├── test_resource_mgr.py
│   ├── test_overlay.py
│   └── fixtures/sample_pl.wav
└── docs/plans/talk2type-core/{plan.md,tests.md}
```

---

## Phase 1 — Scaffolding + dependencies ✅ DONE

**Cel:** działający `uv sync` + importy wszystkich libów.

1. **`pyproject.toml`** — deps (PySide6 dodane dla overlay):
   ```toml
   [project]
   name = "own_wisprflow"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = [
       "faster-whisper>=1.0.3",
       "ollama>=0.3.0",
       "sounddevice>=0.4.6",
       "numpy>=1.26",
       "pynput>=1.7.7",
       "pyperclip>=1.9.0",
       "pystray>=0.19.5",
       "Pillow>=10.0",
       "pywin32>=306",
       "PySide6",
   ]

   [dependency-groups]
   dev = ["pytest>=8", "pytest-mock>=3.12"]
   ```
2. **Utwórz puste moduły** (`talk2type/*.py` z `# TODO`, tylko żeby importy przeszły).
3. **`talk2type/config.py`** — stałe:
   ```python
   WHISPER_MODEL = "turbo"
   WHISPER_COMPUTE = "int8_float16"
   WHISPER_DEVICE = "cuda"

   OLLAMA_MODEL = "qwen3.5:2b"

   SAMPLE_RATE = 16000
   CHANNELS = 1
   DTYPE = "float32"

   HOTKEY_PL = "f9"         # pynput Key name
   HOTKEY_EN = "f10"

   IDLE_TIMEOUT_SEC = 180   # 3 min
   FULLSCREEN_POLL_SEC = 5
   ```

**Weryfikacja:**
- [x] `uv sync` przechodzi bez błędów
- [x] `uv run python -c "import faster_whisper, ollama, sounddevice, pynput, pyperclip, pystray, win32gui, PySide6"` → brak błędów
- [x] `uv run pytest --collect-only` → testy zbierane, 0 errors

---

## Phase 2 — Audio capture (push-to-talk) ✅ DONE

**Cel:** klasa `Recorder` która startuje/stopuje nagrywanie i zwraca `np.float32` mono 16 kHz.

**Implementacja (`talk2type/audio.py`):**
```python
import sounddevice as sd
import numpy as np
import queue

class Recorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._q: queue.Queue = queue.Queue()
        self._stream = None

    def start(self):
        self._q = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=lambda indata, frames, t, status: self._q.put(indata.copy()),
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        self._stream.stop(); self._stream.close()
        self._stream = None
        chunks = []
        while not self._q.empty():
            chunks.append(self._q.get_nowait())
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()   # (N,) float32
```

**Weryfikacja:**
- [x] `tests/test_audio.py`: mock `sd.InputStream`, sprawdź że start/stop poprawnie kolejkują chunki i zwracają płaską tablicę float32.
- [x] Ręczny smoke: `python -c "from talk2type.audio import Recorder; r=Recorder(); r.start(); import time; time.sleep(2); a=r.stop(); print(a.shape, a.dtype)"` → shape ok 32000, dtype float32.

**Anti-patterns:**
- Nie używaj `sd.rec(duration, ...)` — wymaga znanej długości, nie pasuje do push-to-talk.
- Nie używaj `stream.read()` w pętli — callback jest prostszy i bezpieczniejszy.

---

## Phase 3 — STT wrapper (lazy load + explicit unload) ✅ DONE

**Cel:** `WhisperSTT` ładuje model przy pierwszym użyciu, trzyma w VRAM do `unload()`.

**Implementacja (`talk2type/stt.py`):**
```python
import gc
import numpy as np
from faster_whisper import WhisperModel
from .config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE

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
```

**Weryfikacja:**
- [x] Unit test z mockowanym `WhisperModel` — sprawdź lazy-load (model None przed wołaniem `transcribe`), unload (None po wołaniu `unload`).
- [x] Smoke test na pliku WAV: nagraj 5s "to jest test", `transcribe(audio, "pl")` → coś sensownego. Target latency na RTX 2060 Super: <500 ms po pierwszym warm-upie dla 5s audio.

**Anti-patterns:**
- Nie ładuj modelu w `__init__` — to blokuje start aplikacji na kilka sekund.
- Nie wywołuj `torch.cuda.empty_cache()` — faster-whisper nie używa torch dla modelu (tylko CTranslate2).

---

## Phase 4 — LLM cleanup (ollama + think=False + keep_alive="3m") ✅ DONE

**Cel:** `cleanup_text(raw, language)` zwraca oczyszczony tekst; model trzyma się w pamięci 3 min (keep_alive="3m"), dopasowując się do cyklu ResourceManager. Funkcja `unload()` wymusza zwolnienie (keep_alive=0) — wołana przez ResourceManager przy idle/fullscreen.

**Implementacja (`talk2type/prompts.py`):**
```python
SYSTEM_PL = """Poprawiasz transkrypcje mowy. Zwracasz TYLKO poprawiony tekst.

Reguły:
- Usuń wypełniacze: eee, yyy, mmm, aaa, hhh i ich wielokrotne wersje (eeee, yyyyy itd.)
- Popraw wielkie litery i interpunkcję
- NIE dodawaj komentarzy, nie streszczaj

Tekst: "dzisiaj eee pojechałem yyy do sklepu i kupiłem chleb"
Odpowiedź: Dzisiaj pojechałem do sklepu i kupiłem chleb."""

SYSTEM_EN = """You clean up speech transcriptions. Return ONLY the cleaned text.

Rules:
- Remove filler sounds: uh, um, er, ah, hmm (and their multi-letter variants)
- Fix capitalization and punctuation
- DO NOT add comments, do not summarize

Input: "today uh i went umm to the store and bought bread"
Output: Today I went to the store and bought bread."""
```

**Implementacja (`talk2type/llm.py`):**
```python
from ollama import chat
from .config import OLLAMA_MODEL
from .prompts import SYSTEM_PL, SYSTEM_EN

_PROMPTS = {"pl": SYSTEM_PL, "en": SYSTEM_EN}
_LABELS = {"pl": ("Tekst", "Odpowiedź"), "en": ("Text", "Response")}

def cleanup_text(raw: str, language: str = "pl") -> str:
    if not raw.strip():
        return raw
    try:
        label_text, label_resp = _LABELS[language]
        response = chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": _PROMPTS[language]},
                {"role": "user", "content": f'{label_text}: "{raw}"\n{label_resp}:'},
            ],
            think=False,
            keep_alive="3m",
            options={"temperature": 0.1, "num_predict": 256},
        )
        return response.message.content.strip().strip('"')
    except Exception:
        return raw   # fallback — lepiej wkleić surowy niż nic


def unload():
    try:
        chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": "x"}],
            think=False,
            keep_alive=0,
            options={"num_predict": 1},
        )
    except Exception:
        pass
```

**Weryfikacja:**
- [x] Unit test z mockowanym `ollama.chat` — sprawdź że `think=False` i `keep_alive="3m"` są w kwargs.
- [x] Unit test że `unload()` woła `chat` z `keep_alive=0`.
- [x] Integration test (wymaga działającej Ollamy): `cleanup_text("dzisiaj eee byłem w sklepie")` → coś zbliżonego do "Dzisiaj byłem w sklepie.".
- [ ] Latency test: drugi call po pierwszym → <1s (warm).

**Anti-patterns:**
- Nie przekazuj `think`/`keep_alive` w `options` — muszą być top-level.
- Nie raise'uj jeśli LLM zawiedzie — zwróć raw (user woli wkleić surowy niż stracić transkrypcję).

---

## Phase 5 — Hotkey listener + paste ✅ DONE

**DECISION RESOLVED:** Wybrano `F9` = PL, `F10` = EN. Oryginalny design (Alt_R/Ctrl_R) miał AltGr conflict na polskiej klawiaturze — AltGr emituje Ctrl_L+Alt_R razem. F9/F10 jest niezawodne i bezkolizyjne.

**Implementacja (`talk2type/hotkey.py`):**
```python
from pynput import keyboard
from pynput.keyboard import Key
from .config import HOTKEY_PL, HOTKEY_EN

_KEYS = {"pl": getattr(Key, HOTKEY_PL), "en": getattr(Key, HOTKEY_EN)}

class HotkeyListener:
    def __init__(self, on_pl_start, on_pl_stop, on_en_start, on_en_stop):
        self._cb = {
            "pl_start": on_pl_start, "pl_stop": on_pl_stop,
            "en_start": on_en_start, "en_stop": on_en_stop,
        }
        self._down = {"pl": False, "en": False}
        self._listener = None

    def _on_press(self, key, injected=None):
        for lang in ("pl", "en"):
            if key == _KEYS[lang] and not self._down[lang]:
                self._down[lang] = True
                self._cb[f"{lang}_start"]()

    def _on_release(self, key, injected=None):
        for lang in ("pl", "en"):
            if key == _KEYS[lang] and self._down[lang]:
                self._down[lang] = False
                self._cb[f"{lang}_stop"]()

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
```

**Implementacja (`talk2type/paste.py`):**
```python
import pyperclip
from pynput.keyboard import Controller, Key

_kb = Controller()

def paste_text(text: str):
    if not text:
        return
    pyperclip.copy(text)
    with _kb.pressed(Key.ctrl):
        _kb.press('v'); _kb.release('v')
```

**Weryfikacja:**
- [x] Smoke test hotkey: trzymaj F9 2s → odpali pl_start, po puszczeniu pl_stop. Analogicznie F10 = EN.
- [x] Paste test: `paste_text("test ąęść")` w otwartym Notatniku → poprawne polskie znaki.

**Anti-patterns:**
- Nie rób paste'a przez `pynput.Controller().type(text)` — znacząco wolniejsze dla długich tekstów niż Ctrl+V.
- Nie trzymaj `Controller()` jako local var w funkcji — globalna instancja szybsza.

---

## Phase 6 — Orchestrator + tray + resource manager ✅ DONE

**Cel:** wszystko sklejone. Overlay pokazuje stan nagrywania (PySide6 pill widget). Po 3 min bez aktywności LUB gdy wykryto fullscreen → unload STT+LLM przez `unload_all`.

**Implementacja (`talk2type/tray.py`) — aktualna:**
```python
import threading
from pathlib import Path
from pystray import Icon, Menu, MenuItem
from PIL import Image

_IMAGES_DIR = Path(__file__).parent.parent / "images"

class Tray:
    def __init__(self, on_quit):
        self._icon = Icon(
            "Talk2Type",
            Image.open(_IMAGES_DIR / "icon.png"),
            "Talk2Type",
            Menu(MenuItem("Quit", lambda i, _: (on_quit(), i.stop()))),
        )

    def set_state(self, state: str):
        pass   # stub — stan wizualny obsługuje overlay

    def run(self):
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self):
        self._icon.stop()
```
> **Uwaga:** `set_state` jest stubem — overlay.py przejął odpowiedzialność za stan wizualny.

**Implementacja (`talk2type/resource_mgr.py`):**
```python
import threading, time
import win32gui, win32api, win32con

def is_fullscreen() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd: return False
    if win32gui.GetClassName(hwnd) in ("Progman", "WorkerW", "Shell_TrayWnd", "Button"):
        return False
    if not win32gui.GetWindowText(hwnd): return False
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return (l == 0 and t == 0
            and (r - l) == win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            and (b - t) == win32api.GetSystemMetrics(win32con.SM_CYSCREEN))

class ResourceManager:
    def __init__(self, on_unload, idle_timeout_sec=180, poll_sec=5):
        self._on_unload = on_unload
        self._idle_timeout = idle_timeout_sec
        self._poll = poll_sec
        self._last_activity = time.monotonic()
        self._stop_evt = threading.Event()
        self._unloaded = True   # nothing loaded at start

    def mark_activity(self):
        self._last_activity = time.monotonic()
        self._unloaded = False

    def _loop(self):
        while not self._stop_evt.wait(self._poll):
            if self._unloaded:
                continue
            idle = time.monotonic() - self._last_activity
            if idle > self._idle_timeout or is_fullscreen():
                self._on_unload()
                self._unloaded = True

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop_evt.set()
```

**Implementacja (`main.py`) — aktualna:**
```python
import logging, signal, sys, time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from talk2type.audio import Recorder
from talk2type.config import setup_logging
from talk2type.hotkey import HotkeyListener
from talk2type.llm import cleanup_text, unload as unload_llm
from talk2type.overlay import OverlayWindow
from talk2type.paste import paste_text
from talk2type.resource_mgr import ResourceManager
from talk2type.stt import WhisperSTT
from talk2type.tray import Tray

class App:
    def __init__(self):
        setup_logging()
        self._qt = QApplication(sys.argv)
        self._overlay = OverlayWindow()
        self.recorder = Recorder()
        self.stt = WhisperSTT()
        self.tray = Tray(on_quit=self.shutdown)
        self.resmgr = ResourceManager(on_unload=self.unload_all)
        self.hotkey = HotkeyListener(
            on_pl_start=lambda: self._start("pl"), on_pl_stop=lambda: self._stop("pl"),
            on_en_start=lambda: self._start("en"), on_en_stop=lambda: self._stop("en"),
        )
        self._busy = False

    def unload_all(self):          # public — wołane przez ResourceManager i shutdown
        self.stt.unload(); unload_llm()

    def _start(self, lang):
        if self._busy: return
        self.tray.set_state("recording")
        self._overlay.request_recording(lang)
        self.recorder.start(level_callback=self._overlay.push_rms)
        self._lang = lang

    def _stop(self, lang):
        if self._busy: return
        self._busy = True
        audio = self.recorder.stop()
        self.tray.set_state("processing")
        self._overlay.request_processing()
        try:
            if audio.size < 1600: return
            raw = self.stt.transcribe(audio, language=lang)
            self.resmgr.mark_activity()
            cleaned = cleanup_text(raw, language=lang)
            paste_text(cleaned)
        finally:
            self.tray.set_state("idle")
            self._overlay.request_hide()
            self._busy = False

    def run(self):
        self.tray.run(); self.resmgr.start(); self.hotkey.start()
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        sigint_timer = QTimer(); sigint_timer.start(200)
        sigint_timer.timeout.connect(lambda: None)
        self._qt.exec(); sys.exit(0)

    def shutdown(self):
        self.hotkey.stop(); self.resmgr.stop(); self.unload_all()
        self._qt.quit(); sys.exit(0)
```
> **Kluczowe zmiany vs. plan:** `QApplication.exec()` zamiast `time.sleep(1e9)` (Windows nie ma `signal.pause()`); `unload_all` publiczna; overlay zintegrowany z `_start`/`_stop`; `level_callback` do waveform.

**Weryfikacja:**
- [x] E2E manual: `uv run python main.py` → tray widoczny, overlay pojawia się przy nagrywaniu, PL i EN wkleja.
- [ ] Idle test: zostaw 3+ min bez aktywności → sprawdź `nvidia-smi` że Whisper zwolnił VRAM.
- [ ] Fullscreen test: uruchom grę / F11 w Chrome → unload odpali w <10s.
- [x] Quit z trayu → proces kończy się czysto (brak zombie ollama keep_alive).

**Anti-patterns:**
- Nie blokuj głównego wątku na `icon.run()`.
- `signal.pause()` nie istnieje na Windows — Qt event loop (`self._qt.exec()`) jest właściwym rozwiązaniem.
- Nie rób `_unload_all` prywatnej — ResourceManager musi ją wołać przez `on_unload` callback.

---

## Phase 6b — Overlay UI (PySide6 pill widget) ✅ DONE

**Cel:** floating pill widget na dole ekranu, pokazuje stan nagrywania (waveform bars) i processing.

**Implementacja (`talk2type/overlay.py`)** — PySide6 `QWidget` z:
- `FramelessWindowHint | Tool | WA_TranslucentBackground` → brak obramowania, przezroczyste tło
- DWM attributes via `ctypes.windll.dwmapi` → usunięcie Windows shadow/border (Windows 11)
- Wewnętrzne Signals (`_Signals(QObject)`) → thread-safe API (`request_recording`, `request_processing`, `request_hide`)
- `push_rms(float)` → aktualizuje waveform deque (44 bary × 50ms refresh)
- Fade-out animacja przy ukrywaniu (16ms timer, alpha -= 20)

**Public API (thread-safe, wołane z wątku hotkey):**
```python
overlay.request_recording(lang: str)   # pokazuje pill + waveform
overlay.request_processing()            # przechodzi do "Processing..."
overlay.request_hide()                  # fade-out i ukrycie
overlay.push_rms(rms: float)           # aktualizuje waveform (z audio callback)
```

**Weryfikacja:**
- [x] Overlay pojawia się przy F9/F10 na dole ekranu
- [x] Waveform reaguje na głos (bars ruszają się)
- [x] "Processing..." wyświetla się między stop a paste
- [x] Fade-out po wklejeniu

---

## Phase 7 — Auto-start (Windows Startup folder) ✅ DONE

**Cel:** script `scripts/install_autostart.py` → tworzy `.lnk` w Startup folderze.

**Implementacja (`scripts/install_autostart.py`):**
```python
import os, sys
from pathlib import Path
import pythoncom
from win32com.shell import shell, shellcon

def install():
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise RuntimeError(f"pythonw.exe not found next to {sys.executable}")

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.SetPath(str(pythonw))
    link.SetArguments(f'"{main_py}"')
    link.SetWorkingDirectory(str(project_root))
    link.SetDescription("own_wisprflow autostart")

    startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    target = os.path.join(startup, "own_wisprflow.lnk")
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(target, 0)
    print(f"Installed: {target}")

def uninstall():
    startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    target = os.path.join(startup, "own_wisprflow.lnk")
    if os.path.exists(target):
        os.remove(target); print(f"Removed: {target}")
    else:
        print("Not installed.")

if __name__ == "__main__":
    (uninstall if "--uninstall" in sys.argv else install)()
```

**Weryfikacja:**
- [ ] `uv run python scripts/install_autostart.py` → skrót pojawia się w `Win+R → shell:startup`.
- [ ] Restart Windows → apka startuje sama (sprawdź Task Manager → Startup tab).
- [ ] `uv run python scripts/install_autostart.py --uninstall` → skrót znika.

**Anti-patterns:**
- Nie używaj `python.exe` → okno konsoli na starcie.
- Nie zapisuj w `CSIDL_COMMON_STARTUP` → wymaga admina.

---

## Phase 8 — Final verification

1. **Grep anti-patterns:**
   ```bash
   grep -rn "large-v3-turbo" talk2type/    # powinno być puste
   grep -rn "empty_cache" talk2type/       # powinno być puste
   grep -rn "Key.alt_gr" talk2type/        # powinno być puste
   grep -rn "options.*think" talk2type/    # powinno być puste
   grep -rn "alt_r\|ctrl_r" talk2type/hotkey.py  # powinno być puste (F9/F10)
   ```
2. **Latency benchmark:** 10× push-to-talk 3s audio → zmierz średni czas end-to-end. Target: <1.2 s warm.
3. **VRAM benchmark:** `nvidia-smi` przed/po nagrywaniu; po 3 min idle → powinno wrócić do bazowego.
4. **Polish quality spot-check:** 5 próbek z wypełniaczami → LLM powinien usunąć eeee/yyyy/aaaa w każdej.
5. **Full `pytest` pass:**
   ```bash
   uv run pytest -q --cov=talk2type
   ```
6. **`lint-and-validate` skill** — po całości.

---

## Zależności między fazami

```
Phase 1 (scaffold) ── Phase 2 (audio) ── Phase 3 (stt) ─┐
                       │                                 ├── Phase 6 (orchestrator)
                       │                  Phase 4 (llm) ─┤
                       └── Phase 5 (hotkey+paste) ───────┘
                                                          │
                                                          └── Phase 7 (autostart) ── Phase 8 (verify)
```

Fazy 2–5 mogą iść **równolegle** (niezależne moduły), Faza 6 je skleja.

---

## Resolved decisions

1. **AltGr conflict** → **F9/F10** (opcja B). Alt_R/Ctrl_R odrzucone z powodu AltGr conflict na PL layout.
2. **Autostart** → osobny `scripts/install_autostart.py` do ręcznego wywołania.
3. **Logging** → plik `logs/wisprflow.log` (obok pakietu), przez `setup_logging()` w `config.py`.
