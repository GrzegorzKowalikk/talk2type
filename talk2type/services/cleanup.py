import logging
import re

from ollama import chat

from talk2type.config import OLLAMA_MODEL
from talk2type.prompts import SYSTEM_EN, SYSTEM_PL

log = logging.getLogger(__name__)

_PROMPTS = {"pl": SYSTEM_PL, "en": SYSTEM_EN}
_LABELS = {"pl": ("Tekst", "Odpowiedź"), "en": ("Text", "Response")}

_FILLER_RE = re.compile(r"\b([eyahm])\1+\b", re.IGNORECASE)


def strip_fillers(text: str) -> str:
    if not text.strip():
        return text
    stripped = _FILLER_RE.sub("", text)
    return re.sub(r" {2,}", " ", stripped).strip()


class CleanupService:
    """LLM text cleanup. Every call builds a fresh message list — no chat history."""

    def __init__(self, model: str = OLLAMA_MODEL, keep_alive: str = "15m"):
        self._model = model
        self._keep_alive = keep_alive

    def cleanup(self, raw: str, language: str = "pl") -> str:
        if not raw.strip():
            return raw
        cleaned = strip_fillers(raw)
        label_text, label_resp = _LABELS[language]
        try:
            response = chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": _PROMPTS[language]},
                    {"role": "user", "content": f'{label_text}: "{cleaned}"\n{label_resp}:'},
                ],
                think=False,
                keep_alive=self._keep_alive,
                options={"temperature": 0.1, "num_predict": -1},
            )
            return response.message.content.strip().strip('"')
        except Exception:
            log.exception("LLM cleanup failed -- returning raw text")
            return raw

    def preload(self) -> None:
        try:
            chat(
                model=self._model,
                messages=[{"role": "user", "content": "x"}],
                think=False,
                keep_alive=self._keep_alive,
                options={"num_predict": 1},
            )
        except Exception:
            log.exception("LLM preload failed")

    def unload(self) -> None:
        try:
            chat(
                model=self._model,
                messages=[{"role": "user", "content": "x"}],
                think=False,
                keep_alive=0,
                options={"num_predict": 1},
            )
            log.info("LLM (%s) unloaded from Ollama", self._model)
        except Exception:
            pass
