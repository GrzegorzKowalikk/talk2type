# Test plan — Anti-hallucination cleanup pipeline

Framework: pytest (`uv run pytest`). LLM (`ollama.chat`) mockowane — testy nie
trafiają do realnego modelu. Pliki testowe: rozszerz istniejące testy
`CleanupService`.

## `strip_fillers(text)` — regex nie-słów

| # | wejście | oczekiwane | uzasadnienie |
|---|---------|-----------|--------------|
| 1 | `"dzisiaj eee pojechałem yyy do sklepu"` | `"dzisiaj pojechałem do sklepu"` | tnie dźwięki, kolaps spacji |
| 2 | `"mmm aaa hhh"` | `""` (lub po stripie) | same dźwięki |
| 3 | `"eeee yyyyy"` | `""` | rozciągnięte warianty |
| 4 | `"Mam dwa psy"` | `"Mam dwa psy"` | NIE tnie "Mam" (M+a+m to słowo, ale to nie `[eyahm]{2,}`) |
| 5 | `" to jest hej"` | `"to jest hej"` | "hej" zostaje — `h` tak, ale "hej" ma `j` poza klasą |
| 6 | `"Eee no właśnie"` | `"no właśnie"` | case-insensitive, początek zdania |
| 7 | `""` | `""` | pusty |
| 8 | `"yyy"` | `""` | samo filler |

Uwaga ryzyka: klasa `[eyahm]{2,}` może złapać realne słowa złożone tylko z tych
liter (np. "ma" = `m`+`a`? → tak, `[eyahm]{2,}` matchuje "ma"!). **Test 4 musi to
wyłapać** — jeśli regex tnie "ma"/"he"/"ej", trzeba przejść z klasy znaków na
jawną listę powtórzonego pojedynczego znaku: `\b([eyahm])\1+\b` (ten sam znak ≥2×),
co matchuje "eee"/"yy"/"mm" ale NIE "ma"/"hej". **To jest preferowana implementacja.**

Po tej korekcie:
| # | wejście | oczekiwane |
|---|---------|-----------|
| 4 | `"Mam dwa psy"` | `"Mam dwa psy"` (bez zmian) |
| 9 | `"ma eee sens"` | `"ma sens"` ("ma" nietknięte, "eee" wycięte) |

## `is_safe(before, after, threshold=0.70)` — strażnik diff

| # | before | after | wynik | uzasadnienie |
|---|--------|-------|-------|--------------|
| 1 | `"ala ma kota"` | `"Ala Ma Kota"` | True | różni się tylko wielkością liter — `.lower()` zbija do ratio=1.0 (edycja czysto formatująca przechodzi strażnika) |
| 2 | `"ala ma kota"` | `"Ala ma psa."` | False | jedno słowo zmienione, ratio≈0.66 → poniżej 0.7 |
| 3 | „Ogólnie rozkminiam sobie teraz takie coś jak można" | „Rozumiem sobie teraz tak jak można by lepiej" | False | realny case parafrazy, ratio<0.7 |
| 4 | `"a b c d e f g h"` | `"a b c d e f g h"` | True | identyczne, ratio=1.0 |
| 5 | `"a b c d e f g h i j"` | `"a b c d X Y Z Q i j"` | False | 4/10 słów zmienione → ratio=0.6 |
| 6 | `""` | `""` | True | pusty = bezpieczny |

Metryka: `SequenceMatcher(None, before.lower().split(), after.lower().split()).ratio()`.

## `cleanup()` — integracja (LLM mockowany)

| # | scenariusz | mock LLM zwraca | oczekiwane wyjście |
|---|-----------|-----------------|-------------------|
| 1 | LLM zachowawczy | tekst ≈ wejściu (ratio>0.7) | wyjście LLM |
| 2 | LLM halucynuje | tekst całkiem inny (ratio<0.7) | **tekst po regexie** (fallback) |
| 3 | LLM rzuca wyjątek | `raise Exception` | tekst po regexie (nie surowy raw) |
| 4 | pusty `raw` | — (LLM nie wołany) | `raw` |
| 5 | wejście z fillerem `"eee no test"` + LLM zachowawczy | `"No test"` | `"No test"` (regex wyciął eee, LLM przeszedł strażnika) |
| 6 | fallback loguje | ratio<0.7 | `log.info` z wartością ratio (assert na caplog) |

## Quality gate (ręczny, nieautomatyzowalny)
- 5 dłuższych dyktowań PL na żywo.
- Odczyt logu: ile razy strażnik odrzucił (fallback). Wysoki odsetek → sygnał do 8B
  (podbicie modelu). Niski → 2b wystarcza.
