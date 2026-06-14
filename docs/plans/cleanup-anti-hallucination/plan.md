# Plan — Anti-hallucination cleanup pipeline

## Problem

`CleanupService` (model `qwen3.5:2b`) przepisuje długi tekst od nowa zamiast tylko
usuwać filler. Tryb awarii niespójny: parafraza, halucynacja, skracanie, czasem
odpowiadanie na tekst. Przyczyny:

1. **LLM dubluje robotę Whispera.** `WHISPER_MODEL = "turbo"` sam stawia
   interpunkcję i wielkie litery. LLM dostaje już-zinterpunkcjonowany tekst i mimo
   to go przepisuje.
2. **Few-shot uczy przepisywania.** Przykłady w `prompts.py` mają wejście bez
   interpunkcji → wyjście z interpunkcją. To kłamie o tym, co model realnie dostaje,
   i uczy go mocnych transformacji.
3. **Brak bezpiecznika.** Nic nie łapie, gdy 2b zignoruje "nie parafrazuj".

Przykład: wejście „Ogólnie rozkminiam sobie teraz takie coś..." → wyjście
„Rozumiem sobie teraz tak..." (≈40% wspólnych słów).

## Rozwiązanie (Droga 3B)

Pipeline: **Whisper (interpunkcja) → regex (filler-dźwięki) → LLM fenced
(przejęzyczenia + filler kontekstowy) → strażnik diff → paste.**

Podział odpowiedzialności:
- **Whisper** — interpunkcja, wielkie litery (już działa, nie ruszamy).
- **regex** — tnie tylko nie-słowa: `e/y/a/h/m` i ich rozciągnięcia. Zero ryzyka.
- **LLM** — tylko kontekstowe wypełniacze ("no więc", "jakby") i oczywiste
  przejęzyczenia. Wąski prompt + przykłady near-identity.
- **strażnik** — `difflib.SequenceMatcher.ratio()` na słowach (case-insensitive)
  między wejściem LLM (tekst po regexie) a wyjściem LLM. `< 0.70` → odrzuć wyjście
  LLM, wklej tekst po regexie. Loguj odrzucenie (metryka do decyzji o podbiciu modelu).

Decyzje (z grill-me):
- 3B (LLM zostaje, zabetonowany) — nie 3A (regex-only) ani 1/2.
- Strażnik diff, próg 0.70, fallback na tekst po regexie (nie surowy Whisper).
- Metryka: `SequenceMatcher` na słowach, case-insensitive.
- Regex tylko nie-słowa `e/y/a/h/m`; kontekstowe zostają LLM-owi.
- Prompt 7A: wąski + przykłady near-identity z już-interpunkcją; osobne PL/EN.
- Model: zostań na 2b, zmierz odsetek fallbacków (8A).
- Cały tekst jednym wywołaniem (9A), nie dzielenie na zdania.
- `temperature: 0` zamiast 0.1 dla determinizmu.

## Allowed APIs (docs-first)

Brak nowych zewnętrznych bibliotek.
- `difflib.SequenceMatcher(None, a, b).ratio()` — stdlib.
- `re` — stdlib.
- `ollama.chat(...)` — już używane w `cleanup.py`, bez zmian w sygnaturze poza `options`.

## Fazy

### Faza 1 — regex filler (RED→GREEN)
- [x] `tests.md` → testy `strip_fillers()` (patrz tests.md).
- [x] Funkcja `strip_fillers(text: str) -> str` w `cleanup.py`. Regex
      `\b([eyahm])\1+\b` case-insensitive (ten sam znak powtórzony ≥2×), plus
      kolaps powstałych podwójnych spacji. NIE `[eyahm]{2,}` — to tnie "ma"/"hej".
- [x] Weryfikacja: nie tnie prawdziwych słów (dlatego powtórzenie tego samego znaku + `\b`).

### Faza 2 — strażnik diff (RED→GREEN)
- [x] Testy `is_safe(before, after, threshold=0.70) -> bool`.
- [x] Funkcja licząca `SequenceMatcher` na `.lower().split()` obu tekstów.
- [x] Próg jako stała modułowa `GUARD_THRESHOLD = 0.70` (łatwe strojenie).

### Faza 3 — przepisanie promptów (7A)
- [x] `prompts.py`: nowe SYSTEM_PL / SYSTEM_EN — zakres zawężony do filler
      kontekstowy + przejęzyczenia; explicite "interpunkcja i wielkie litery są
      już poprawne — NIE ruszaj".
- [x] Przykłady few-shot: wejście **z** interpunkcją, wyjście różniące się o 1-2
      słowa (głównie tożsamość). Min. 1 przykład czysto-tożsamościowy.

### Faza 4 — integracja w `cleanup()` (RED→GREEN)
- [x] `cleanup()`: `raw` → `strip_fillers` → `regexed`; LLM dostaje `regexed`;
      wynik LLM → `is_safe(regexed, llm_out)`? tak: zwróć `llm_out`; nie: zwróć
      `regexed` + `log.info("guard rejected: ratio=%.2f", r)`.
- [x] `temperature: 0`.
- [x] Istniejący `try/except` → przy błędzie LLM zwróć `regexed` (nie surowy `raw`).
- [x] Pusty/whitespace `raw` → zwróć `raw` (jak teraz).

### Faza 5 — quality gate
- [x] `uv run pytest` zielony (188 passed).
- [ ] `lint-and-validate` (ruff nie zainstalowany w venv — pominięte).
- [ ] Ręczny test: 5 dłuższych dyktowań, sprawdź log odsetka fallbacków (metryka 8A) — **brama ludzka przed mergem**.

## Out of scope (świadomie odłożone)
- Podbicie modelu do 7b (8B) — tylko jeśli metryka pokaże wysoki fallback.
- Dzielenie na zdania (9B) — tylko jeśli długie teksty zdominują odrzucenia.
- Rozszerzanie regexa o kontekstowe wypełniacze (6B) — odrzucone, psuje treść.
