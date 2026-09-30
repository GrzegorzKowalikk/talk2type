"""Tests for HistoryPage widget — searchable transcription list."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from talk2type.db.model import Transcription  # noqa: F401 — registers metadata


@pytest.fixture(scope="session")
def qt_app():
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def history_with_data(qt_app):
    """HistoryPage loaded with 3 transcriptions: today, yesterday, older."""
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    now = datetime.now()

    with Session(e) as s:
        s.add(
            Transcription(
                raw="hello",
                cleaned="Hello world",
                ts=now,
                stt_ms=1000,
                llm_ms=500,
            )
        )
        s.add(
            Transcription(
                raw="test",
                cleaned="Test yesterday",
                ts=now - timedelta(days=1),
                stt_ms=1000,
                llm_ms=500,
            )
        )
        s.add(
            Transcription(
                raw="old",
                cleaned="Old transcription",
                ts=now - timedelta(days=5),
                stt_ms=1000,
                llm_ms=500,
            )
        )
        s.commit()

    from talk2type.ui.pages.history import HistoryPage

    w = HistoryPage()

    @contextmanager
    def _sess():
        with Session(e) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    with patch("talk2type.ui.pages.history.get_session", side_effect=_sess):
        w.refresh_data()
        yield w
    w.close()


# --- 1. Full transcription list displayed ---


def test_all_transcriptions_displayed(history_with_data):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")
    # 3 transcription items + date group headers (TODAY, YESTERDAY, date header)
    assert list_widget.count() >= 3


def test_transcription_text_displayed(history_with_data):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")
    texts = [list_widget.item(i).text() for i in range(list_widget.count())]
    joined = " ".join(texts)
    assert "Hello world" in joined
    assert "Test yesterday" in joined
    assert "Old transcription" in joined


# --- 2. Live search/filter by text ---


def test_search_filters_items(history_with_data, qt_app):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")

    w._filter("Hello")
    qt_app.processEvents()

    visible_count = sum(
        1 for i in range(list_widget.count()) if not list_widget.item(i).isHidden()
    )
    # At least "Hello world" item + some header(s)
    assert visible_count >= 1

    joined_visible = " ".join(
        list_widget.item(i).text()
        for i in range(list_widget.count())
        if not list_widget.item(i).isHidden()
    )
    assert "Hello world" in joined_visible
    assert "Test yesterday" not in joined_visible
    assert "Old transcription" not in joined_visible


def test_search_clear_shows_all(history_with_data, qt_app):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")

    w._filter("Hello")
    qt_app.processEvents()

    w._filter("")
    qt_app.processEvents()

    visible_count = sum(
        1 for i in range(list_widget.count()) if not list_widget.item(i).isHidden()
    )
    assert visible_count == list_widget.count()


# --- 3. Date grouping (TODAY / YESTERDAY / older) ---


def test_today_header_present(history_with_data):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")
    texts = [list_widget.item(i).text() for i in range(list_widget.count())]
    assert any("TODAY" in t for t in texts)


def test_yesterday_header_present(history_with_data):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")
    texts = [list_widget.item(i).text() for i in range(list_widget.count())]
    assert any("YESTERDAY" in t for t in texts)


def test_older_date_header_present(history_with_data):
    w = history_with_data
    list_widget = w.findChild(object, "transcription_list")
    texts = [list_widget.item(i).text() for i in range(list_widget.count())]
    # The older item (5 days ago) should produce a date-formatted header
    # that is neither "TODAY" nor "YESTERDAY"
    non_standard_headers = [
        t for t in texts
        if "TODAY" not in t and "YESTERDAY" not in t
        and "Hello world" not in t
        and "Test yesterday" not in t
        and "Old transcription" not in t
    ]
    assert len(non_standard_headers) >= 1


# --- 4. Context menu: Copy ---


def test_context_menu_copy_action(qt_app):

    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)

    with Session(e) as s:
        s.add(
            Transcription(
                raw="copy me",
                cleaned="Copy me text",
                ts=datetime.now(),
                stt_ms=100,
                llm_ms=50,
            )
        )
        s.commit()

    from talk2type.ui.pages.history import HistoryPage

    w = HistoryPage()

    @contextmanager
    def _sess():
        with Session(e) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    with patch("talk2type.ui.pages.history.get_session", side_effect=_sess):
        w.refresh_data()

    list_widget = w.findChild(object, "transcription_list")
    # Find an item that contains "Copy me text"
    target_item = None
    for i in range(list_widget.count()):
        if "Copy me text" in list_widget.item(i).text():
            target_item = list_widget.item(i)
            break
    assert target_item is not None

    # Trigger context menu
    menu = w._build_context_menu(target_item)
    actions = menu.actions()
    action_texts = [a.text() for a in actions]
    assert "Copy" in action_texts

    # Execute copy action
    copy_action = next(a for a in actions if a.text() == "Copy")
    copy_action.trigger()

    from PySide6.QtWidgets import QApplication

    clipboard = QApplication.clipboard()
    assert "Copy me text" in clipboard.text()
    w.close()


# --- 5. Context menu: Delete ---


def test_context_menu_delete_action(qt_app):
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)

    with Session(e) as s:
        s.add(
            Transcription(
                raw="delete me",
                cleaned="Delete me text",
                ts=datetime.now(),
                stt_ms=100,
                llm_ms=50,
            )
        )
        s.commit()

    from talk2type.ui.pages.history import HistoryPage

    w = HistoryPage()

    @contextmanager
    def _sess():
        with Session(e) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    with patch("talk2type.ui.pages.history.get_session", side_effect=_sess):
        w.refresh_data()

        list_widget = w.findChild(object, "transcription_list")

        # Find an item that contains "Delete me text"
        target_item = None
        for i in range(list_widget.count()):
            if "Delete me text" in list_widget.item(i).text():
                target_item = list_widget.item(i)
                break
        assert target_item is not None

        # Count items before delete
        count_before = list_widget.count()

        # Trigger delete via context menu
        menu = w._build_context_menu(target_item)
        actions = menu.actions()
        action_texts = [a.text() for a in actions]
        assert "Delete" in action_texts

        delete_action = next(a for a in actions if a.text() == "Delete")
        delete_action.trigger()

        # After delete, the list should have fewer items
        assert list_widget.count() < count_before

    # Verify it's gone from DB too
    with Session(e) as s:
        remaining = s.exec(select(Transcription)).all()
        assert len(remaining) == 0
    w.close()


def test_history_loads_pages_and_searches_beyond_first_page(qt_app):
    from PySide6.QtWidgets import QLineEdit, QListWidget, QPushButton
    from talk2type.ui.pages.history import HistoryPage

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for i in range(55):
            session.add(Transcription(raw="raw", cleaned=f"entry {i}", ts=datetime(2026, 1, 1)))
        session.commit()

    @contextmanager
    def session_scope():
        with Session(engine) as session:
            yield session

    page = HistoryPage()
    with patch("talk2type.ui.pages.history.get_session", session_scope):
        page.refresh_data()
        items = page.findChild(QListWidget, "transcription_list")
        more = page.findChild(QPushButton, "load_more_btn")
        assert items.count() == 51  # 50 entries and a single date heading
        more.click()
        assert items.count() == 56
        assert more.isHidden()
        search = page.findChild(QLineEdit, "search_bar")
        search.setText("entry 0")
        search.textEdited.emit("entry 0")
        assert items.count() == 2
        assert "entry 0" in items.item(1).text()
        page.refresh_data()
        assert items.count() == 2
        page.findChild(QPushButton, "clear_btn").click()
        assert items.count() == 51
    page.close()
