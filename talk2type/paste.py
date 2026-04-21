import time
import pyperclip
from pynput.keyboard import Controller, Key

_kb = Controller()


def paste_text(text: str):
    if not text:
        return
    pyperclip.copy(text)
    time.sleep(0.05)
    with _kb.pressed(Key.ctrl):
        _kb.press("v")
        _kb.release("v")
