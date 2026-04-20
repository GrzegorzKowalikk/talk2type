from pynput import keyboard
from pynput.keyboard import Key

from .config import HOTKEY_EN, HOTKEY_PL

_KEYS = {"pl": getattr(Key, HOTKEY_PL), "en": getattr(Key, HOTKEY_EN)}


class HotkeyListener:
    def __init__(self, on_pl_start, on_pl_stop, on_en_start, on_en_stop):
        self._cb = {
            "pl_start": on_pl_start,
            "pl_stop": on_pl_stop,
            "en_start": on_en_start,
            "en_stop": on_en_stop,
        }
        self._down = {"pl": False, "en": False}
        self._listener = None

    def _on_press(self, key, injected=None):
        for lang, bound in _KEYS.items():
            if key == bound and not self._down[lang]:
                self._down[lang] = True
                self._cb[f"{lang}_start"]()

    def _on_release(self, key, injected=None):
        for lang, bound in _KEYS.items():
            if key == bound and self._down[lang]:
                self._down[lang] = False
                self._cb[f"{lang}_stop"]()

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
