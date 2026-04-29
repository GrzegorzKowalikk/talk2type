# Features / Pomysły

## Formatowanie tekstu (kontekstowe tryby dyktowania)

**Kontekst:** Wispr Flow oferuje "Flow Styles" — automatyczne dopasowanie formatu do aktywnej aplikacji (np. bullet points w Notion, komentarze kodu w VS Code). Osiągają to przez wysyłanie screenshota ekranu do chmury i decydowanie o formacie po stronie serwera.

**Nasze podejście — bez chmury, bez screenshotów:**

### Opcja A: Oddzielne hotkleje per tryb

Każdy klawisz = inny prompt systemowy, model ten sam (qwen3.5:2b).

| Klawisz | Tryb |
|---------|------|
| F9 | Transkrypcja PL (aktualnie) |
| F10 | Transkrypcja EN (aktualnie) |
| F11 | Bullet points PL |
| F12 | Format email PL |

Implementacja: nowe wpisy `SYSTEM_BULLETS_PL`, `SYSTEM_EMAIL_PL` w `prompts.py`, nowe hotkleje w `config.py`.

### Opcja B: Przełącznik trybu w tray menu (pomysł)

Zamiast mnożyć hotkleje — jedno menu w ikonie tray z listą trybów. Użytkownik klika tryb → aktywny prompt się zmienia → ten sam hotkey F9 używa wybranego formatu. Coś w stylu:

```
[✓] Normalny
[ ] Bullet points
[ ] Email
[ ] Formalny
```

Zmiana trybu bez restartu, wizualne potwierdzenie w ikoncie tray (np. zmiana etykiety tooltip).

---

**Uwagi:**
- qwen3.5:2b wystarczy do prostego formatowania (listy, email, akapity)
- Context-aware jak Wispr Flow (auto-detekcja aplikacji) poza zakresem bez większego modelu lub dodatkowej logiki detekcji okna
- Opcja B bardziej UX-friendly, opcja A prostsza do implementacji
