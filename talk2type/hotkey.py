# talk2type/hotkey.py
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


def _parse_key(k: str):
    """Parse a string like 'f9' or 'a' into a pynput key."""
    if hasattr(Key, k):
        return getattr(Key, k)
    return KeyCode.from_char(k)


class HotkeyListener:
    def __init__(self, on_start, on_stop, on_cancel, init_pl="f9", init_en="f10"):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_cancel = on_cancel
        self._down = {"pl": False, "en": False}
        self._keys = {}
        self._listener = None
        self.update_keys(init_pl, init_en)

    def update_keys(self, pl_key: str, en_key: str):
        self._keys = {
            "pl": _parse_key(pl_key),
            "en": _parse_key(en_key),
        }

    def _on_press(self, key, injected=None):
        if key == Key.esc:
            self._on_cancel()
            return
        for lang, bound in self._keys.items():
            if key == bound and not self._down[lang]:
                self._down[lang] = True
                self._on_start(lang)

    def _on_release(self, key, injected=None):
        for lang, bound in self._keys.items():
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
