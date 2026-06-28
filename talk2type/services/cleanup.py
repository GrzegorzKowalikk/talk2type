import difflib
import logging
import re

from ollama import chat

from talk2type.config import OLLAMA_MODEL, USE_LLM
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


GUARD_THRESHOLD = 0.70


def is_safe(before: str, after: str, threshold: float = GUARD_THRESHOLD) -> bool:
    return _guard_ratio(before, after) >= threshold


def _guard_ratio(before: str, after: str) -> float:
    return difflib.SequenceMatcher(
        None, before.lower().split(), after.lower().split()
    ).ratio()


class CleanupService:
    """LLM text cleanup. Every call builds a fresh message list — no chat history."""

    def __init__(self, model: str = OLLAMA_MODEL, keep_alive: str = "15m",
                 enabled: bool = USE_LLM):
        self._model = model
        self._keep_alive = keep_alive
        self._enabled = enabled

    def cleanup(self, raw: str, language: str = "pl") -> str:
        if not raw.strip():
            return raw
        cleaned = strip_fillers(raw)
        if not self._enabled:
            return cleaned
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
                options={"temperature": 0, "num_predict": -1},
            )
            llm_out = response.message.content.strip().strip('"')
        except Exception:
            log.exception("LLM cleanup failed -- returning regex-cleaned text")
            return cleaned

        if is_safe(cleaned, llm_out):
            return llm_out
        log.info("guard rejected: ratio=%.2f", _guard_ratio(cleaned, llm_out))
        return cleaned

    def preload(self) -> None:
        if not self._enabled:
            return
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
        if not self._enabled:
            return
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
