import time

import win32clipboard
import win32con
from pynput.keyboard import Controller, Key


class PasteService:
    def __init__(self):
        self._kb = Controller()

    def paste(self, text: str) -> None:
        if not text:
            return
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
        time.sleep(0.05)
        with self._kb.pressed(Key.ctrl):
            self._kb.press("v")
            self._kb.release("v")
