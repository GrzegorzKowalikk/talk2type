# Test Plan: Redesign architektury talk2type

Konwencje (z istniejących testów):
- `uv run pytest` (marker `integration` wykluczony domyślnie przez `addopts`).
- Qt: fixture `qt_app` (session-scoped `QApplication.instance()` lub nowa) + `qt_app.processEvents()` po emisji sygnałów.
- Mocki: `unittest.mock.patch` / `pytest-mock`.
- DB: fixture z `tests/db/conftest.py` (in-memory engine).

## tests/core/test_cancellation.py

- [x] nowy token → `cancelled is False`
- [x] po `cancel()` → `cancelled is True`
- [x] podwójny `cancel()` → bez błędu, dalej `True`

## tests/core/test_states.py

- [x] stan początkowy `IDLE`
- [x] `press("pl")` z IDLE → RECORDING, zwraca `True`, emituje `recording_started("pl")`, `lang == "pl"`
- [x] `press` w RECORDING → `False`, bez sygnału, stan bez zmian
- [x] `press` w PROCESSING → `False`
- [x] `release()` z RECORDING → PROCESSING, `True`, emituje `processing_started`
- [x] `release()` z IDLE → `False`, bez sygnału
- [x] `cancel()` z RECORDING → IDLE, zwraca `State.RECORDING`, emituje `returned_to_idle("cancelled")`
- [x] `cancel()` z PROCESSING → IDLE, zwraca `State.PROCESSING`
- [x] `cancel()` z IDLE → zwraca `None`, bez sygnału
- [x] `finish("done")` z PROCESSING → IDLE, emituje `returned_to_idle("done")`
- [x] `finish` z RECORDING → no-op (guard: stary wątek pipeline nie może zabić nowego nagrania)
- [x] `finish` z IDLE → no-op, bez sygnału

## tests/services/test_cleanup.py

- [x] pusty / sam whitespace `raw` → zwrócony bez zmian, `chat` NIE wywołany
- [x] `cleanup("tekst", "pl")` → `chat` dostaje świeże 2 messages: system=`SYSTEM_PL`, user w formacie `Tekst: "..."\nOdpowiedź:`
- [x] język "en" → `SYSTEM_EN` + `Text:`/`Response:`
- [x] wynik: `.strip()` + zdjęte otaczające `"`
- [x] `chat` rzuca wyjątek → zwraca `raw` (bez wyjątku na zewnątrz)
- [x] `preload()` → `chat` z `options={"num_predict": 1}`, `keep_alive="15m"`
- [x] `unload()` → `chat` z `keep_alive=0`; wyjątek połknięty
- [x] prompty: `SYSTEM_PL` zawiera regułę o nieodpowiadaniu na pytania ("NIGDY nie odpowiadaj") i ≥3 przykłady (`Tekst:`); analogicznie `SYSTEM_EN`

## tests/services/test_transcription.py

(mock `faster_whisper.WhisperModel` przez `patch("talk2type.services.transcription.WhisperModel")`; DB fixture in-memory)

- [x] `refresh_hotwords()` przy pustej tabeli → `_hotwords is None`
- [x] po dodaniu Hotword("Claude"), Hotword("Anthropic") → `_hotwords == "Anthropic, Claude"` (kolejność wg zapytania) lub zawiera oba słowa
- [x] `transcribe(audio, "pl")` → `model.transcribe` wywołany z `hotwords=<cache>`, `language="pl"`, `beam_size=5`, `vad_filter=True`; wynik = sklejone `seg.text`, strip
- [x] `preload()` ładuje model raz; drugi `preload()` nie tworzy drugiego `WhisperModel`
- [x] dwa równoległe `preload()` (wątki) → `WhisperModel` skonstruowany dokładnie raz
- [x] `unload()` → `_model is None`; `transcribe` po unload ładuje ponownie
- [x] `transcribe` NIE odpytuje DB (brak `get_session` w ścieżce transcribe — hotwords z cache)

## tests/services/test_audio.py

(port z tests/test_audio.py — zmiana importu na `talk2type.services.audio.AudioRecorder`)

- [x] `stop()` bez `start()` → pusty `np.ndarray` float32
- [x] start → callback strumienia wrzuca chunki → `stop()` zwraca konkatenację spłaszczoną
- [x] `level_callback` dostaje RMS float

## tests/services/test_paste.py

(port z tests/test_paste.py — klasa `PasteService`)

- [x] `paste("")` → `pyperclip.copy` NIE wywołany
- [x] `paste("tekst")` → `pyperclip.copy("tekst")` + ctrl+v na mocku `Controller`

## tests/test_hotkey.py (rozszerzenie)

- [x] F9 press → `on_start("pl")` raz; trzymanie (powtórny press) → bez drugiego wywołania
- [x] F9 release → `on_stop("pl")`
- [x] F10 → para "en"
- [x] **Esc press → `on_cancel()`** (nowe)
- [x] inny klawisz → nic

## tests/ui/test_overlay.py

(adaptacja tests/test_overlay.py do nowych slotów; sygnały wywoływane bezpośrednio jako metody + `processEvents`)

- [x] `push_rms` skala ×10 i clamp do 1.0 (bez zmian)
- [x] `on_recording("pl")` → widoczny, `_state == "recording"`, `_lang == "PL"`, timery aktywne
- [x] `on_processing()` → `_state == "processing"`, wave timer stop
- [x] `on_idle("done")` → fade timer startuje; po fade → `isVisible() is False`
- [x] `on_idle("cancelled")` → też chowa (każdy powód chowa)
- [x] geometria: `_W <= 300` i `_H <= 56` (mniejszy pill — strażnik regresji rozmiaru)

## tests/ui/test_dictionary_page.py (rozszerzenie istniejącego)

- [x] `add_word()` (niepusty, nowy) → emituje `hotwords_changed`
- [x] `remove_word(id)` → emituje `hotwords_changed`
- [x] duplikat / pusty input → BEZ emisji

## tests/core/test_pipeline.py

(wszystkie zależności jako mocki: machine prawdziwy `DictationStateMachine`, recorder/transcription/cleanup/paste — mocki; wątki pipeline joinowane w teście)

- [x] `on_press("pl")`: recorder.start z `level_callback`, preload obu serwisów (w wątku — join przez polling/mock event), `on_activity` wywołane
- [x] `on_press` gdy nie-IDLE → recorder.start NIE wywołany
- [x] happy path `on_release`: transcribe → cleanup → paste → `save_transcription(raw, cleaned, stt_ms=..., llm_ms=...)`; maszyna wraca do IDLE z "done"
- [x] audio krótsze niż `MIN_SAMPLES` (4800) → transcribe NIE wywołany, IDLE z "too_short"
- [x] `on_cancel()` w RECORDING → `recorder.stop()` wywołany, pipeline NIE startuje
- [x] `on_cancel()` w PROCESSING (token cancelled po STT) → paste NIE wywołany, save NIE wywołany
- [x] cancel po LLM (token cancelled między cleanup a paste) → paste NIE wywołany
- [x] wyjątek w transcribe → IDLE z "error", paste NIE wywołany, wyjątek nie propaguje
- [x] po cancelu stary wątek NIE woła `finish` (maszyna w nowym RECORDING nie zostaje zresetowana — test: cancel, press ponownie, dokończ stary wątek, stan dalej RECORDING)
- [x] pusty `raw` ("") → save_transcription NIE wywołany (jak dziś)

## tests/test_diagnostics.py

- [x] `install_crash_hooks()` → `sys.excepthook` i `threading.excepthook` podmienione (nie domyślne)
- [x] wywołanie hooka z fake wyjątkiem → `log.critical` z `exc_info` (caplog)

## tests/test_app.py (zastępuje tests/test_main.py)

(wzorzec `App.__new__(App)` + mocki jak w starym test_main.py)

- [x] `_unload_models()` → `transcription.unload()` + `cleanup.unload()`
- [x] `shutdown()` → hotkey.stop, resmgr.stop, unload, qt.quit
- [x] config: `IDLE_TIMEOUT_SEC == 900`

## Adaptacje istniejących

- [x] `tests/test_main.py` → usunięty (zastąpiony test_app.py + test_pipeline.py)
- [x] `tests/test_integration.py`, `tests/test_pipeline_history.py` → importy/orkiestracja na nowe klasy, asercje bez zmian merytorycznych
- [x] `tests/integration/test_stt_integration.py` → `TranscriptionService`
- [x] `tests/integration/test_llm_integration.py` → `CleanupService`
- [x] `tests/test_tray.py` → bez `set_state` (metoda usuwana — martwa)
- [x] reszta stron UI: tylko zmiany importów jeśli pliki przeniesione

## Kryterium końcowe

- [x] `uv run pytest` — komplet zielony, zero warningów o brakujących importach
- [x] grep-strażnicy (anty-wzorce):
  - `initial_prompt` nie występuje w `talk2type/` (zastąpione `hotwords=`)
  - `from main import` nie występuje w `tests/`
  - `set_state` nie występuje w `talk2type/`
  - `threading.Thread(target=self._run_pipeline` (stary wzorzec) nie występuje
