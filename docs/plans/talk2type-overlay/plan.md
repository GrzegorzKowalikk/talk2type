# talk2type — overlay UI (plan implementacji)

> Dodanie floating overlay w PySide6 + integracja z Qt event loop w main.py.
> Zbudowane 2026-04-21.

---

## Cel

Wizualne potwierdzenie nagrywania i przetwarzania: pill-shaped overlay na dole ekranu pokazuje waveform podczas nagrywania i "Processing..." podczas STT/LLM.

---

## Zaimplementowane ✅

### `talk2type/overlay.py` (nowy plik)

`OverlayWindow(QWidget)` — pill-shaped floating overlay, 420×76 px, pozycja bottom-center.

**Stany:**
- `hidden` — niewidoczny (domyślny)
- `recording` — waveform (44 bary RMS), blinkujący czerwony dot, label języka (PL/EN)
- `processing` — tekst "Processing..."

**Thread-safe API (thread → Qt signal → main thread):**
```python
overlay.request_recording("pl")   # hotkey thread → slot _on_recording
overlay.request_processing()       # hotkey thread → slot _on_processing
overlay.request_hide()             # hotkey thread → slot _on_hide (fade)
overlay.push_rms(0.08)             # sounddevice callback → deque
```

**Animacje:**
- Waveform: `_wave_timer` co 50 ms → `update()`
- Dot blink: `_dot_timer` co 600 ms
- Fade-out: `_fade_timer` co 16 ms, alpha -= 20 (255 → 0 w ~200 ms)

**DWM workaround** (`_setup_dwm` w `showEvent`):
- Wyłącza Windows border glow (DWMWA_NCRENDERING_POLICY)
- Windows 11: brak zaokrąglania narożników (DWMWA_WINDOW_CORNER_PREFERENCE)
- Windows 11: brak 1px accent border (DWMWA_BORDER_COLOR = 0xFFFFFFFE)

**Przezroczystość:** `WA_TranslucentBackground` + `CompositionMode_Clear` czyści margines 12px (pochłania DWM shadow).

---

### `talk2type/audio.py` — `level_callback`

```python
def start(self, level_callback=None):
```

Jeśli podany, callback dostaje RMS każdej klatki: `float(np.sqrt(np.mean(indata ** 2)))`.  
Główny kod: `overlay.push_rms` przekazywany przez `App._start()`.

---

### `main.py` — integracja Qt

- `QApplication(sys.argv)` tworzony w `App.__init__`
- `OverlayWindow()` tworzony raz w `App.__init__`
- `_start()`:
  ```python
  self._overlay.request_recording(lang)
  self.recorder.start(level_callback=self._overlay.push_rms)
  ```
- `_stop()`:
  ```python
  self._overlay.request_processing()
  # ... pipeline ...
  self._overlay.request_hide()
  ```
- `run()` → `self._qt.exec()` (Qt event loop) zamiast `time.sleep(1e9)`
- SIGINT workaround: `QTimer` co 200 ms żeby Qt nie blokował Ctrl+C

---

## Otwarte problemy ⚠️

| # | Problem | Plik:linia | Opis |
|---|---------|------------|------|
| 1 | `sys.exit(0)` w pystray callback | `main.py:94` | `shutdown()` woła `sys.exit(0)` po `_qt.quit()` — `SystemExit` rzucony w środku pystray message handler (`_dispatcher → _on_notify → callback`). Naprawić: nie robić `sys.exit` wewnątrz callbacka pystray. |
| 2 | `set_state()` jest `pass` | `tray.py:20` | Ikona trayu nie zmienia koloru. Zaimplementować: `self._icon.icon = _img(self.COLORS.get(state, "gray"))`. |

---

## Zależności

```
talk2type/audio.py (level_callback)
         │
         ▼
talk2type/overlay.py ──────────────────> main.py
(OverlayWindow, QWidget)                  │
                                          ▼
                                    talk2type/tray.py
                                    (set_state — TODO)
```

---

## Weryfikacja manualna

- [ ] F9 trzymany → overlay pojawia się z waveformem, dot mruga
- [ ] F9 puszczony → overlay przechodzi w "Processing...", po chwili znika (fade)
- [ ] F10 trzymany → overlay z labelką "EN"
- [ ] Tray: ikona NIE zmienia koloru (bug #2 otwarty)
- [ ] Quit z trayu → SystemExit w logach (bug #1 otwarty), ale app zamyka się
