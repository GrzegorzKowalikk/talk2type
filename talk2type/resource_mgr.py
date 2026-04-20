import threading
import time

import win32api
import win32con
import win32gui

from .config import FULLSCREEN_POLL_SEC, IDLE_TIMEOUT_SEC

_SHELL_CLASSES = frozenset(("Progman", "WorkerW", "Shell_TrayWnd", "Button"))


def is_fullscreen() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    if win32gui.GetClassName(hwnd) in _SHELL_CLASSES:
        return False
    if not win32gui.GetWindowText(hwnd):
        return False
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return (
        left == 0
        and top == 0
        and (right - left) == win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        and (bottom - top) == win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    )


class ResourceManager:
    def __init__(
        self, on_unload, idle_timeout_sec=IDLE_TIMEOUT_SEC, poll_sec=FULLSCREEN_POLL_SEC
    ):
        self._on_unload = on_unload
        self._idle_timeout = idle_timeout_sec
        self._poll = poll_sec
        self._last_activity = time.monotonic()
        self._stop_evt = threading.Event()
        self._unloaded = True

    def mark_activity(self):
        self._last_activity = time.monotonic()
        self._unloaded = False

    def _loop(self):
        while not self._stop_evt.wait(self._poll):
            if self._unloaded:
                continue
            idle = time.monotonic() - self._last_activity
            if idle > self._idle_timeout or is_fullscreen():
                self._on_unload()
                self._unloaded = True

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop_evt.set()
