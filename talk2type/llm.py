from ollama import chat

from .config import OLLAMA_MODEL
from .prompts import SYSTEM_EN, SYSTEM_PL

_PROMPTS = {"pl": SYSTEM_PL, "en": SYSTEM_EN}
_LABELS = {"pl": ("Tekst", "Odpowiedź"), "en": ("Text", "Response")}


def cleanup_text(raw: str, language: str = "pl") -> str:
    if not raw.strip():
        return raw
    label_text, label_resp = _LABELS[language]
    try:
        response = chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": _PROMPTS[language]},
                {
                    "role": "user",
                    "content": f"{label_text}: \u0022{raw}\u0022\n{label_resp}:",
                },
            ],
            think=False,
            keep_alive="3m",
            options={"temperature": 0.1, "num_predict": 256},
        )
        return response.message.content.strip().strip('"')
    except Exception:
        return raw


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
