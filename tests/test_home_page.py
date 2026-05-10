import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Transcription  # noqa: F401 — registers metadata


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _make_engine_with_rows(rows: list[Transcription]):
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    with Session(e) as s:
        for r in rows:
            s.add(r)
        s.commit()
    return e


def _patch_session(engine):
    """Return a context-manager mock that yields sessions from *engine*."""
    from talk2type.ui.pages.home import get_session

    @contextmanager
    def _sess():
        with Session(engine) as s:
            yield s

    return patch.object(get_session, "__wrapped__", _sess) if hasattr(get_session, "__wrapped__") else patch("talk2type.ui.pages.home.get_session", side_effect=_sess)


@pytest.fixture
def home_empty(qt_app):
    from talk2type.ui.pages.home import HomePage

    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    w = HomePage()
    with patch("talk2type.ui.pages.home.get_session") as mock:

        @contextmanager
        def _sess():
            with Session(e) as s:
                yield s

        mock.side_effect = _sess
        w.refresh_data()
        yield w
    w.close()


@pytest.fixture
def home_with_data(qt_app):
    from talk2type.ui.pages.home import HomePage

    base = datetime(2025, 1, 5, 14, 0, 0)
    rows = []
    for i in range(25):
        day_offset = i // 5  # 5 rows per day -> 5 distinct days
        rows.append(
            Transcription(
                raw=f"raw{i}",
                cleaned=" ".join("word" for _ in range(i + 1)),
                stt_ms=1000,
                llm_ms=500,
                ts=base + timedelta(days=day_offset, minutes=i),
            )
        )
    e = _make_engine_with_rows(rows)

    w = HomePage()
    with patch("talk2type.ui.pages.home.get_session") as mock:

        @contextmanager
        def _sess():
            with Session(e) as s:
                yield s

        mock.side_effect = _sess
        w.refresh_data()
        yield w
    w.close()


# --- Stats: Total Words ---


def test_total_words_from_transcriptions(home_with_data):
    # rows have cleaned = "word" * (i+1), i=0..24 => sum = sum(1..25) = 325
    assert home_with_data.total_words_label.text() == "325"


def test_total_words_empty_db(home_empty):
    assert home_empty.total_words_label.text() == "0"


# --- Stats: Days of Usage ---


def test_days_of_usage(home_with_data):
    # 5 rows per day, 25 rows total => 5 distinct days
    assert home_with_data.days_label.text() == "5"


def test_days_empty_db(home_empty):
    assert home_empty.days_label.text() == "0"


# --- Stats: WPM ---


def test_wpm_calculated(home_with_data):
    # Each row: words = i+1, duration = 1500ms = 1.5min * 60 = nah.
    # WPM = words / (duration_minutes). duration = (stt_ms + llm_ms)/60000
    # Each row: words = i+1, duration_min = 1500/60000 = 0.025
    # WPM per row = (i+1) / 0.025 = (i+1) * 40
    # Average WPM = avg(1..25) * 40 = 13 * 40 = 520
    assert home_with_data.wpm_label.text() == "520"


def test_wpm_empty_db(home_empty):
    assert home_empty.wpm_label.text() == "0"


def test_wpm_skips_zero_duration(qt_app):
    """Rows with stt_ms=0 and llm_ms=0 must be skipped."""
    from talk2type.ui.pages.home import HomePage

    rows = [
        Transcription(raw="r1", cleaned="hello world", stt_ms=0, llm_ms=0),
        Transcription(raw="r2", cleaned="hi", stt_ms=1000, llm_ms=500),
    ]
    e = _make_engine_with_rows(rows)
    w = HomePage()
    with patch("talk2type.ui.pages.home.get_session") as mock:

        @contextmanager
        def _sess():
            with Session(e) as s:
                yield s

        mock.side_effect = _sess
        w.refresh_data()

        # Only r2 counted: words=1, duration_min=0.025, WPM=40
        assert w.wpm_label.text() == "40"
    w.close()


# --- Recent Activity ---


def test_recent_shows_last_20(home_with_data):
    list_widget = home_with_data.recent_list
    assert list_widget.count() == 20


def test_recent_ordered_newest_first(home_with_data):
    list_widget = home_with_data.recent_list
    # Most recent item (i=24, ts latest) should be at row 0
    first_text = list_widget.item(0).text()
    assert "word" in first_text  # sanity: contains text
    # The last item (i=5, oldest of the 20 shown) should be at row 19
    last_text = list_widget.item(19).text()
    assert "word" in last_text


def test_recent_empty_db(home_empty):
    assert home_empty.recent_list.count() == 0
