import os

from talk2type.db.engine import get_session
from talk2type.db.model import Transcription


def _get_active_app() -> str | None:
    try:
        import win32api
        import win32con
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
        exe = win32process.GetModuleFileNameEx(handle, 0)
        return os.path.basename(exe) if exe else None
    except Exception:
        return None


def save_transcription(raw: str, cleaned: str, stt_ms: int, llm_ms: int) -> None:
    app = _get_active_app()
    record = Transcription(raw=raw, cleaned=cleaned, app=app, stt_ms=stt_ms, llm_ms=llm_ms)
    with get_session() as session:
        session.add(record)
