from contextlib import contextmanager
from unittest.mock import patch

from sqlmodel import Session, select

import talk2type.db.service as svc
from talk2type.db.model import Transcription


def _fake_session(engine):
    @contextmanager
    def _inner():
        with Session(engine) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
    return _inner


def test_save_writes_row(engine):
    with patch("talk2type.db.service.get_session", _fake_session(engine)), \
         patch("talk2type.db.service._get_active_app", return_value="notepad.exe"):
        svc.save_transcription("raw text", "Clean text.", 400, 200)

    with Session(engine) as s:
        rows = s.exec(select(Transcription)).all()
    assert len(rows) == 1
    assert rows[0].app == "notepad.exe"
    assert rows[0].stt_ms == 400


def test_save_sets_app_from_active_window(engine):
    with patch("talk2type.db.service.get_session", _fake_session(engine)), \
         patch("talk2type.db.service._get_active_app", return_value="chrome.exe"):
        svc.save_transcription("r", "c", 100, 50)

    with Session(engine) as s:
        row = s.exec(select(Transcription)).first()
    assert row.app == "chrome.exe"


def test_get_active_app_returns_none_on_exception():
    with patch.dict("sys.modules", {"win32gui": None, "win32process": None, "win32api": None, "win32con": None}):
        result = svc._get_active_app()
    assert result is None
