# talk2type — overlay UI (plan testów)

> Testy dla overlay.py, level_callback w audio.py oraz zaktualizowanego main.py.
> Uzupełnienie istniejącego `docs/plans/talk2type-core/tests.md`.

---

## Naprawy istniejących testów (broken patch paths)

Wszystkie istniejące testy patchowały `wisprflow.*` zamiast `talk2type.*`.
Poprawione ścieżki per plik:

| Plik | Stara ścieżka | Nowa ścieżka |
|------|---------------|--------------|
| `test_audio.py` | `wisprflow.audio.sd` | `talk2type.audio.sd` |
| `test_stt.py` | `wisprflow.stt.WhisperModel` | `talk2type.stt.WhisperModel` |
| `test_llm.py` | `wisprflow.llm.chat` | `talk2type.llm.chat` |
| `test_resource_mgr.py` | `wisprflow.resource_mgr.*` | `talk2type.resource_mgr.*` |
| `test_paste.py` | `wisprflow.paste.*` | `talk2type.paste.*` |
| `test_main.py` | brak `_overlay` mocka | dodać `app._overlay = MagicMock()` |
| `test_main.py` | `app._unload_all()` | `app.unload_all()` (usunięto underscore) |

---

## Nowe testy — `tests/test_audio.py` (dodane)

### `test_level_callback_receives_rms`
- Recorder.start z `level_callback=mock_fn`.
- Symuluj callback z `indata` shape `(512, 1)` float32.
- `mock_fn` zawołany z wartością float między 0 a 1.

---

## Nowe testy — `tests/test_overlay.py`

### Fixture `qt_app` (scope=session)
```python
QApplication.instance() or QApplication(sys.argv)
```
Jedna instancja Qt na cały test run.

### Fixture `overlay`
```python
OverlayWindow() + yield + hide()
```
Świeży widget na każdy test.

### `test_push_rms_scale_and_clamp`
- `push_rms(0.05)` → `_rms[-1] == 0.5` (×10)
- `push_rms(0.15)` → `_rms[-1] == 1.0` (clamp do 1.0)
- `push_rms(0.0)` → `_rms[-1] == 0.0`

### `test_request_recording_sets_state`
- `request_recording("pl")` → `processEvents()` → `_state == "recording"`, `_lang == "PL"`, widoczny, timery active.

### `test_request_recording_en`
- `request_recording("en")` → `_lang == "EN"`.

### `test_request_processing_changes_state`
- recording → `request_processing()` → `_state == "processing"`, wave/dot timery zatrzymane.

### `test_request_hide_starts_fade_timer`
- recording → `request_hide()` → `_fade_timer.isActive()`, wave timer zatrzymany.

### `test_fade_step_decrements_alpha`
- Po recording (alpha=255): `_fade_step()` → `_alpha == 235`.

### `test_fade_step_hides_at_zero`
- `_alpha = 20` → `_fade_step()` → `_alpha == 0`, widget ukryty, `_fade_timer` zatrzymany.

### `test_toggle_dot`
- `_toggle_dot()` neguje `_dot_on`. Drugi call wraca do oryginału.

---

## Uruchomienie

```bash
# Wszystkie unity:
uv run pytest -q

# Tylko overlay:
uv run pytest tests/test_overlay.py -v

# Z coverage:
uv run pytest --cov=talk2type --cov-report=term-missing
```

---

## Coverage target

- `overlay.py`: ≥70% (paintEvent pomijalne — czysty render, brak logiki biznesowej)
- `audio.py` (z level_callback): ≥90%
- `main.py`: ≥60% (glue + Qt event loop trudny do unit testowania)
