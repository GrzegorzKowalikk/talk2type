import time

import pyperclip
from pynput.keyboard import Controller, Key


class PasteService:
    def __init__(self):
        self._kb = Controller()

    def paste(self, text: str) -> None:
        if not text:
            return
        pyperclip.copy(text)
        time.sleep(0.05)
        with self._kb.pressed(Key.ctrl):
            self._kb.press("v")
            self._kb.release("v")
