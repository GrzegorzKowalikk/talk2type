# talk2type/hotkey.py
from pynput import keyboard
from pynput.keyboard import Key

from .config import HOTKEY_EN, HOTKEY_PL

_KEYS = {"pl": getattr(Key, HOTKEY_PL), "en": getattr(Key, HOTKEY_EN)}


class HotkeyListener:
    def __init__(self, on_start, on_stop, on_cancel):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_cancel = on_cancel
        self._down = {"pl": False, "en": False}
        self._listener = None

    def _on_press(self, key, injected=None):
        if key == Key.esc:
            self._on_cancel()
            return
        for lang, bound in _KEYS.items():
            if key == bound and not self._down[lang]:
                self._down[lang] = True
                self._on_start(lang)

    def _on_release(self, key, injected=None):
        for lang, bound in _KEYS.items():
            if key == bound and self._down[lang]:
                self._down[lang] = False
                self._on_stop(lang)

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
