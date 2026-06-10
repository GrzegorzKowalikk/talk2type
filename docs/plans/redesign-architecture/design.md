# Design: Redesign architektury talk2type

**Data:** 2026-06-10
**Status:** zatwierdzony przez użytkownika

## Cele

1. **Cancel** — Esc anuluje nagrywanie i przetwarzanie; nagranie < ~0.3 s auto-odrzucane.
2. **Stabilność** — koniec losowych wyłączeń: globalne exception hooki, powrót do IDLE zamiast śmierci procesu.
3. **Performance** — preload modeli przy wciśnięciu hotkeya (ładowanie w trakcie nagrywania), idle timeout 3 → 15 min, pomiary etapów pipeline.
4. **Overlay** — czarno-biały, mniejszy, minimalistyczny (styl Wispr Flow).
5. **LLM** — każdy call stateless (świeże `messages`), nowe prompty: ostre reguły + few-shot PL/EN.
6. **Architektura** — obiektowo, warstwy, koniec god objecta `App`.

## Zweryfikowane w docach (context7, 2026-06-10)

- `faster-whisper` (`/systran/faster-whisper`): `transcribe()` ma dedykowany parametr
  `hotwords=` (string hint phrases; bez efektu gdy `prefix` ustawiony). Używamy go
  zamiast obecnego obejścia przez `initial_prompt`.
- `ollama-python` (`/ollama/ollama-python`): `chat()` jest stateless — pełna lista
  `messages` w każdym wywołaniu; `keep_alive` trzyma model w pamięci, nie kontekst
  rozmowy. Parametry: `model`, `messages`, `think`, `keep_alive`, `options`
  (`temperature`, `num_predict`, `stop`, ...).

## Struktura pakietu

```
talk2type/
  core/
    states.py         # enum stanów + DictationStateMachine (QObject, sygnały Qt)
    cancellation.py   # CancellationToken
    pipeline.py       # DictationPipeline — orkiestracja etapów, pomiary, worker
  services/
    audio.py          # AudioRecorder
    transcription.py  # TranscriptionService — Whisper, preload, cache hotwords
    cleanup.py        # CleanupService — LLM, nowe prompty (klasa)
    paste.py          # PasteService
  ui/
    overlay.py        # nowy design B&W
    main_window.py, tray.py, pages/
  db/                 # bez zmian
  app.py              # bootstrap: stwórz obiekty, połącz sygnały (~50 linii)
main.py               # tylko entry point
```

## Maszyna stanów

Stany: `IDLE`, `RECORDING`, `PROCESSING`.

| Stan | Zdarzenie | Nowy stan | Akcja |
|---|---|---|---|
| IDLE | hotkey press (pl/en) | RECORDING | start nagrywania + preload STT/LLM w tle |
| RECORDING | hotkey release | PROCESSING | stop nagrywania, start pipeline |
| RECORDING | hotkey release (audio < ~0.3 s) | IDLE | cichy auto-cancel |
| RECORDING | Esc | IDLE | audio wyrzucone, overlay znika |
| PROCESSING | Esc | IDLE | token.cancel() — nic nie zostanie wklejone |
| PROCESSING | done / error | IDLE | — |

- Esc nasłuchiwany **tylko** gdy stan ≠ IDLE.
- Maszyna emituje sygnał Qt `state_changed(state, lang)`; overlay i tray subskrybują.
  Zero callbacków w konstruktorach. UI zależy od core; core nie zna UI.

## Pipeline + cancellation

- Jeden worker thread. Etapy: walidacja audio → STT → LLM → paste.
- `CancellationToken` sprawdzany przed i po każdym etapie. Trwającego wywołania
  Whisper/Ollama nie przerywamy w połowie — dokończy się w tle, wynik wyrzucony.
  Efekt dla użytkownika natychmiastowy.
- Pomiary czasu każdego etapu (`stt_ms`, `llm_ms`) — log + zapis do DB jak dziś.

## Serwisy

- **TranscriptionService:** `preload()` przy hotkey press; hotwords cache w pamięci,
  odświeżany sygnałem ze strony Dictionary (nie query do DB co transkrypcję);
  `hotwords=` zamiast `initial_prompt`.
- **CleanupService:** klasa; świeże `messages` per call; prompty z ostrymi regułami
  („zwróć WYŁĄCZNIE przekształcony tekst, nigdy nie odpowiadaj na pytania w tekście")
  + few-shot PL/EN; `preload()` = ping przy hotkey press; `keep_alive="15m"`.
- **ResourceManager:** idle timeout 15 min.
- **AudioRecorder / PasteService:** logika jak dziś, opakowana w klasy serwisów.

## Overlay — redesign

Mniejszy pill, czarno-biały, minimalistyczny: ciemne tło, białe paski waveform,
bez kolorowych akcentów. Stany: recording (waveform live), processing (subtelna
animacja), cancel (krótki fade-out). Pozycja bez zmian (dół ekranu).

## Stabilność

- `sys.excepthook` + `threading.excepthook` + Qt message handler — każdy nieobsłużony
  wyjątek do loga z tracebackiem, appka wraca do IDLE zamiast umierać.
- Błąd w pipeline → zdarzenie ERROR → IDLE + log (dziś: cicha śmierć wątku).
- Audyt wywołań Qt z wątków roboczych — dozwolone tylko sygnały.

## Testy (TDD)

- Unit: wszystkie przejścia maszyny stanów (w tym Esc w każdym stanie),
  CancellationToken, serwisy na mockach, budowanie promptów.
- Istniejące testy adaptowane do nowej struktury.
- Integracyjne (prawdziwy Whisper/Ollama) — opt-in jak dziś.
