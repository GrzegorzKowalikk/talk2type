# Test Plan: Redesign architektury talk2type

Konwencje (z istniejących testów):
- `uv run pytest` (marker `integration` wykluczony domyślnie przez `addopts`).
- Qt: fixture `qt_app` (session-scoped `QApplication.instance()` lub nowa) + `qt_app.processEvents()` po emisji sygnałów.
- Mocki: `unittest.mock.patch` / `pytest-mock`.
- DB: fixture z `tests/db/conftest.py` (in-memory engine).

## tests/core/test_cancellation.py

- [ ] nowy token → `cancelled is False`
- [ ] po `cancel()` → `cancelled is True`
- [ ] podwójny `cancel()` → bez błędu, dalej `True`

## tests/core/test_states.py

- [ ] stan początkowy `IDLE`
- [ ] `press("pl")` z IDLE → RECORDING, zwraca `True`, emituje `recording_started("pl")`, `lang == "pl"`
- [ ] `press` w RECORDING → `False`, bez sygnału, stan bez zmian
- [ ] `press` w PROCESSING → `False`
- [ ] `release()` z RECORDING → PROCESSING, `True`, emituje `processing_started`
- [ ] `release()` z IDLE → `False`, bez sygnału
- [ ] `cancel()` z RECORDING → IDLE, zwraca `State.RECORDING`, emituje `returned_to_idle("cancelled")`
- [ ] `cancel()` z PROCESSING → IDLE, zwraca `State.PROCESSING`
- [ ] `cancel()` z IDLE → zwraca `None`, bez sygnału
- [ ] `finish("done")` z PROCESSING → IDLE, emituje `returned_to_idle("done")`
- [ ] `finish` z RECORDING → no-op (guard: stary wątek pipeline nie może zabić nowego nagrania)
- [ ] `finish` z IDLE → no-op, bez sygnału

## tests/services/test_cleanup.py

- [ ] pusty / sam whitespace `raw` → zwrócony bez zmian, `chat` NIE wywołany
- [ ] `cleanup("tekst", "pl")` → `chat` dostaje świeże 2 messages: system=`SYSTEM_PL`, user w formacie `Tekst: "..."\nOdpowiedź:`
- [ ] język "en" → `SYSTEM_EN` + `Text:`/`Response:`
- [ ] wynik: `.strip()` + zdjęte otaczające `"`
- [ ] `chat` rzuca wyjątek → zwraca `raw` (bez wyjątku na zewnątrz)
- [ ] `preload()` → `chat` z `options={"num_predict": 1}`, `keep_alive="15m"`
- [ ] `unload()` → `chat` z `keep_alive=0`; wyjątek połknięty
- [ ] prompty: `SYSTEM_PL` zawiera regułę o nieodpowiadaniu na pytania ("NIGDY nie odpowiadaj") i ≥3 przykłady (`Tekst:`); analogicznie `SYSTEM_EN`

## tests/services/test_transcription.py

(mock `faster_whisper.WhisperModel` przez `patch("talk2type.services.transcription.WhisperModel")`; DB fixture in-memory)

- [ ] `refresh_hotwords()` przy pustej tabeli → `_hotwords is None`
- [ ] po dodaniu Hotword("Claude"), Hotword("Anthropic") → `_hotwords == "Anthropic, Claude"` (kolejność wg zapytania) lub zawiera oba słowa
- [ ] `transcribe(audio, "pl")` → `model.transcribe` wywołany z `hotwords=<cache>`, `language="pl"`, `beam_size=5`, `vad_filter=True`; wynik = sklejone `seg.text`, strip
- [ ] `preload()` ładuje model raz; drugi `preload()` nie tworzy drugiego `WhisperModel`
- [ ] dwa równoległe `preload()` (wątki) → `WhisperModel` skonstruowany dokładnie raz
- [ ] `unload()` → `_model is None`; `transcribe` po unload ładuje ponownie
- [ ] `transcribe` NIE odpytuje DB (brak `get_session` w ścieżce transcribe — hotwords z cache)

## tests/services/test_audio.py

(port z tests/test_audio.py — zmiana importu na `talk2type.services.audio.AudioRecorder`)

- [ ] `stop()` bez `start()` → pusty `np.ndarray` float32
- [ ] start → callback strumienia wrzuca chunki → `stop()` zwraca konkatenację spłaszczoną
- [ ] `level_callback` dostaje RMS float

## tests/services/test_paste.py

(port z tests/test_paste.py — klasa `PasteService`)

- [ ] `paste("")` → `pyperclip.copy` NIE wywołany
- [ ] `paste("tekst")` → `pyperclip.copy("tekst")` + ctrl+v na mocku `Controller`

## tests/test_hotkey.py (rozszerzenie)

- [ ] F9 press → `on_start("pl")` raz; trzymanie (powtórny press) → bez drugiego wywołania
- [ ] F9 release → `on_stop("pl")`
- [ ] F10 → para "en"
- [ ] **Esc press → `on_cancel()`** (nowe)
- [ ] inny klawisz → nic

## tests/ui/test_overlay.py

(adaptacja tests/test_overlay.py do nowych slotów; sygnały wywoływane bezpośrednio jako metody + `processEvents`)

- [ ] `push_rms` skala ×10 i clamp do 1.0 (bez zmian)
- [ ] `on_recording("pl")` → widoczny, `_state == "recording"`, `_lang == "PL"`, timery aktywne
- [ ] `on_processing()` → `_state == "processing"`, wave timer stop
- [ ] `on_idle("done")` → fade timer startuje; po fade → `isVisible() is False`
- [ ] `on_idle("cancelled")` → też chowa (każdy powód chowa)
- [ ] geometria: `_W <= 300` i `_H <= 56` (mniejszy pill — strażnik regresji rozmiaru)

## tests/ui/test_dictionary_page.py (rozszerzenie istniejącego)

- [ ] `add_word()` (niepusty, nowy) → emituje `hotwords_changed`
- [ ] `remove_word(id)` → emituje `hotwords_changed`
- [ ] duplikat / pusty input → BEZ emisji

## tests/core/test_pipeline.py

(wszystkie zależności jako mocki: machine prawdziwy `DictationStateMachine`, recorder/transcription/cleanup/paste — mocki; wątki pipeline joinowane w teście)

- [ ] `on_press("pl")`: recorder.start z `level_callback`, preload obu serwisów (w wątku — join przez polling/mock event), `on_activity` wywołane
- [ ] `on_press` gdy nie-IDLE → recorder.start NIE wywołany
- [ ] happy path `on_release`: transcribe → cleanup → paste → `save_transcription(raw, cleaned, stt_ms=..., llm_ms=...)`; maszyna wraca do IDLE z "done"
- [ ] audio krótsze niż `MIN_SAMPLES` (4800) → transcribe NIE wywołany, IDLE z "too_short"
- [ ] `on_cancel()` w RECORDING → `recorder.stop()` wywołany, pipeline NIE startuje
- [ ] `on_cancel()` w PROCESSING (token cancelled po STT) → paste NIE wywołany, save NIE wywołany
- [ ] cancel po LLM (token cancelled między cleanup a paste) → paste NIE wywołany
- [ ] wyjątek w transcribe → IDLE z "error", paste NIE wywołany, wyjątek nie propaguje
- [ ] po cancelu stary wątek NIE woła `finish` (maszyna w nowym RECORDING nie zostaje zresetowana — test: cancel, press ponownie, dokończ stary wątek, stan dalej RECORDING)
- [ ] pusty `raw` ("") → save_transcription NIE wywołany (jak dziś)

## tests/test_diagnostics.py

- [ ] `install_crash_hooks()` → `sys.excepthook` i `threading.excepthook` podmienione (nie domyślne)
- [ ] wywołanie hooka z fake wyjątkiem → `log.critical` z `exc_info` (caplog)

## tests/test_app.py (zastępuje tests/test_main.py)

(wzorzec `App.__new__(App)` + mocki jak w starym test_main.py)

- [ ] `_unload_models()` → `transcription.unload()` + `cleanup.unload()`
- [ ] `shutdown()` → hotkey.stop, resmgr.stop, unload, qt.quit
- [ ] config: `IDLE_TIMEOUT_SEC == 900`

## Adaptacje istniejących

- [ ] `tests/test_main.py` → usunięty (zastąpiony test_app.py + test_pipeline.py)
- [ ] `tests/test_integration.py`, `tests/test_pipeline_history.py` → importy/orkiestracja na nowe klasy, asercje bez zmian merytorycznych
- [ ] `tests/integration/test_stt_integration.py` → `TranscriptionService`
- [ ] `tests/integration/test_llm_integration.py` → `CleanupService`
- [ ] `tests/test_tray.py` → bez `set_state` (metoda usuwana — martwa)
- [ ] reszta stron UI: tylko zmiany importów jeśli pliki przeniesione

## Kryterium końcowe

- [ ] `uv run pytest` — komplet zielony, zero warningów o brakujących importach
- [ ] grep-strażnicy (anty-wzorce):
  - `initial_prompt` nie występuje w `talk2type/` (zastąpione `hotwords=`)
  - `from main import` nie występuje w `tests/`
  - `set_state` nie występuje w `talk2type/`
  - `threading.Thread(target=self._run_pipeline` (stary wzorzec) nie występuje
