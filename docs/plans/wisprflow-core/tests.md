# own_wisprflow — plan testów (TDD driver)

> Per CLAUDE.md Phase 2 — piszemy testy PRZED implementacją. Ten dokument pilotuje RED→GREEN→REFACTOR.

---

## Stack testowy

- `pytest` + `pytest-mock` (z `dependency-groups.dev`)
- Fixtures: małe WAV-y (5 s PL, 5 s EN) w `tests/fixtures/`
- Nie testujemy faster-whisper/ollama/pynput pod spodem — mockujemy boundary.
- Integration testy (wymagają GPU + Ollamy) w `tests/integration/` — oznaczone `@pytest.mark.integration`, domyślnie pomijane.

```toml
# pyproject.toml [tool.pytest.ini_options]
markers = ["integration: wymaga GPU+Ollama, pomijany w CI"]
addopts = "-m 'not integration'"
```

---

## Phase 2 — audio

### `test_audio.py::test_recorder_start_stop_returns_float32_mono`
- Mockuj `sd.InputStream` (zwraca obiekt z `.start()`, `.stop()`, `.close()`).
- Symuluj 3 callbacki z `indata` shape `(512, 1)` float32.
- Po `start()` → `stop()` wynik: shape `(1536,)` dtype `float32`.

### `test_audio.py::test_recorder_stop_without_start_raises_or_returns_empty`
- Wołaj `stop()` bez `start()` → zwróć `np.zeros(0, dtype=float32)` bez crasha (edge: skasowany shortcut).

### `test_audio.py::test_recorder_second_start_resets_queue`
- `start` → 1 chunk → `stop` (dostałeś chunk) → `start` → 0 chunków → `stop` (dostałeś pustą tablicę, nie stary chunk).

---

## Phase 3 — stt

### `test_stt.py::test_lazy_load`
- Mockuj `WhisperModel`. Po `WhisperSTT()` konstruktor **nie** woła `WhisperModel(...)`.
- Po pierwszym `transcribe(...)` → jedno wołanie `WhisperModel("turbo", device="cuda", compute_type="int8_float16")`.
- Po drugim `transcribe(...)` → **wciąż tylko jedno** (cache).

### `test_stt.py::test_transcribe_passes_language`
- `transcribe(audio, language="pl")` → `model.transcribe` zawołane z `language="pl", beam_size=5, vad_filter=True`.
- `transcribe(audio, language="en")` → `language="en"`.

### `test_stt.py::test_transcribe_concatenates_segments`
- Mock `model.transcribe` zwraca generator segmentów z `.text = [" hello", " world"]`.
- Output: `"hello world"` (trim, pojedyncze spacje).

### `test_stt.py::test_unload_releases_model`
- Po `unload()` → `self._model is None`.
- Kolejne `transcribe(...)` → `WhisperModel(...)` zawołany **drugi raz** (re-load).

### `test_stt.py::test_unload_when_not_loaded_is_noop`
- `WhisperSTT().unload()` — nie rzuca.

### [integration] `test_stt_integration.py::test_real_pl_transcription`
- `audio = load_wav("fixtures/sample_pl.wav")` (5s "to jest test z polskimi znakami")
- Wynik zawiera "test" (case-insensitive).

---

## Phase 4 — llm

### `test_llm.py::test_cleanup_calls_chat_with_think_false_and_keep_alive_3m`
- Mockuj `ollama.chat`. Sprawdź że kwargs zawierają: `think=False`, `keep_alive="3m"`, `model="qwen3.5:2b"`.
- **Krytyczne:** `think` i `keep_alive` są **top-level**, nie w `options`. Test sprawdza `call.kwargs["think"] == False` (a nie `call.kwargs["options"]["think"]`).

### `test_llm.py::test_cleanup_uses_correct_prompt_per_language`
- `cleanup_text(..., "pl")` → system message == SYSTEM_PL.
- `cleanup_text(..., "en")` → system message == SYSTEM_EN.

### `test_llm.py::test_cleanup_returns_raw_on_exception`
- Mock `ollama.chat` rzuca `ConnectionError`.
- `cleanup_text("abc", "pl")` → `"abc"` (fallback, nie rzuca).

### `test_llm.py::test_cleanup_empty_input_short_circuits`
- `cleanup_text("", "pl")` → `""`. `ollama.chat` **nie** zawołane.
- `cleanup_text("   ", "pl")` → `"   "`. `ollama.chat` **nie** zawołane.

### `test_llm.py::test_cleanup_strips_quotes_from_response`
- Mock response `.message.content = '"Dzisiaj byłem w sklepie."'` → output `"Dzisiaj byłem w sklepie."`.

### `test_llm.py::test_unload_calls_chat_with_keep_alive_zero`
- Mockuj `ollama.chat`. `unload()` → sprawdź `keep_alive == 0` i `model == "qwen3.5:2b"`.

### `test_llm.py::test_unload_swallows_exception`
- Mock `ollama.chat` rzuca `ConnectionError`. `unload()` nie rzuca.

### [integration] `test_llm_integration.py::test_real_cleanup_removes_fillers`
- Wymaga działającej Ollamy + pobranego `qwen3.5:2b`.
- `cleanup_text("dzisiaj eeee byłem yyyy w sklepie", "pl")` → nie zawiera "eeee" ani "yyyy".
- Latency: <2 s (cold), <1 s (warm — drugi call w tym samym teście).

---

## Phase 5 — hotkey + paste

### `test_hotkey.py::test_f9_triggers_pl_callbacks`
- Mockuj callbacki. Symuluj `listener._on_press(Key.f9)` → `on_pl_start` zawołany raz.
- `listener._on_release(Key.f9)` → `on_pl_stop` zawołany raz.

### `test_hotkey.py::test_f10_triggers_en_callbacks`
- Analogicznie dla `Key.f10`.

### `test_hotkey.py::test_repeated_press_ignored`
- Hold F9: `_on_press(Key.f9)` → start (1×). Dwa kolejne `_on_press(Key.f9)` → nic (auto-repeat OS-level).

### `test_paste.py::test_paste_copies_then_ctrl_v`
- Mockuj `pyperclip.copy` i `Controller`. `paste_text("hello")` → `pyperclip.copy("hello")` + `Key.ctrl` wciśnięty + 'v' press/release + Ctrl zwolniony.

### `test_paste.py::test_paste_empty_noop`
- `paste_text("")` → `pyperclip.copy` **nie** zawołany.

---

## Phase 6 — resource_mgr + orchestrator

### `test_resource_mgr.py::test_fullscreen_detection_normal_window`
- Mockuj `win32gui.GetWindowRect` zwraca `(100, 100, 900, 700)` i `SM_CXSCREEN=1920`. → `is_fullscreen()` == False.

### `test_resource_mgr.py::test_fullscreen_detection_true_fullscreen`
- `GetWindowRect` `(0, 0, 1920, 1080)`, screen 1920×1080, title="Counter-Strike", class="ApplicationFrameWindow". → True.

### `test_resource_mgr.py::test_fullscreen_skips_shell_classes`
- `GetClassName` zwraca `"Progman"` → False niezależnie od rect.

### `test_resource_mgr.py::test_idle_triggers_unload`
- `ResourceManager(on_unload=mock, idle_timeout_sec=0.2, poll_sec=0.05)`.
- `mark_activity()`, sleep 0.3 → `on_unload` zawołany raz.
- Kolejny sleep 0.3 (wciąż idle) → `on_unload` **nie** zawołany drugi raz (guard `_unloaded`).

### `test_resource_mgr.py::test_fullscreen_triggers_unload`
- Mock `is_fullscreen` → True. `mark_activity()`, sleep 0.1 (< idle timeout). → `on_unload` zawołany.

### `test_main.py::test_orchestrator_pipeline` (integration-lite, heavy mocking)
- Mockuj recorder, stt, llm, paste. Zawołaj `app._start("pl")` + `app._stop("pl")` z fake audio.
- Kolejność: `recorder.start` → `recorder.stop` → `stt.transcribe(..., "pl")` → `cleanup_text(..., "pl")` → `paste_text(...)`.
- Tray przeszedł `idle → recording → processing → idle`.

### `test_main.py::test_short_audio_skips_transcription`
- Audio shape `(800,)` (<0.1 s dla 16kHz). `_stop` nie woła `stt.transcribe`.

### `test_main.py::test_busy_guard`
- Podczas `_stop` (busy=True), kolejny `_start` jest ignorowany.

### `test_main.py::test_unload_all_calls_both`
- `_unload_all()` → `stt.unload` zawołany + `unload_llm` zawołany (oba raz).

---

## Phase 7 — autostart (smoke only, nie unit)

### `test_install_autostart.py::test_install_creates_lnk` (smoke, Windows-only)
- Mockuj `pythoncom.CoCreateInstance` + `shell.SHGetFolderPath` → tmpdir.
- `install()` → plik `own_wisprflow.lnk` istnieje w tmpdir (via `persist_file.Save` mock assert).

### `test_install_autostart.py::test_uninstall_removes_lnk`
- Utwórz fake `.lnk` w tmpdir, mockuj `SHGetFolderPath` → tmpdir, `uninstall()` → plik usunięty.

---

## Benchmarks (Phase 8, nie pytest)

### `bench/latency.py`
- Nagraj 10× 3 s audio (pre-recorded WAV, nie push-to-talk).
- Mierz: `t_stt`, `t_llm`, `t_paste`, `t_total`.
- Raport: średnia + p95.
- Target: total <1.2 s warm, <3 s cold (first call).

### `bench/vram.py`
- Przed / w trakcie / po 3 min idle: `nvidia-smi --query-gpu=memory.used --format=csv`.
- Oczekiwane: ~2.7 GB w trakcie, <300 MB (baseline driver) po idle.

---

## Coverage target

- Phase 2–5: ≥85% per module (pure logic, łatwe do mockowania).
- Phase 6 (main.py): ≥60% (glue, część testowana ręcznie E2E).
- Phase 7 (install): ≥50% (smoke only, reszta wymaga prawdziwego Windows registry/shell).

Overall target: ≥75%.

---

## Uruchomienie

```bash
# Wszystkie unity (domyślnie pomija integration):
uv run pytest -q

# Z integration (wymaga GPU + Ollama + qwen3.5:2b pulled):
uv run pytest -q -m "integration or not integration"

# Pojedyncza faza:
uv run pytest tests/test_stt.py -v

# Coverage:
uv run pytest --cov=wisprflow --cov-report=term-missing
```
