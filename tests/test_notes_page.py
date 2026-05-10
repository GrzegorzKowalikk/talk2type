import sys
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Note  # noqa: F401 — registers metadata


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def notes_page(qt_app):
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)

    from talk2type.ui.pages.notes import NotesPage

    @contextmanager
    def _sess():
        with Session(e) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    with patch("talk2type.ui.pages.notes.get_session", side_effect=_sess):
        w = NotesPage()
        w._test_engine = e
        w.show()
        yield w
    w.close()


def _seed(notes_page, titles_bodies):
    """Insert notes directly into DB, then refresh the widget."""
    engine = notes_page._test_engine
    with Session(engine) as s:
        for title, body in titles_bodies:
            s.add(Note(title=title, body=body))
        s.commit()
    notes_page.refresh_data()


# --- Structure ---


def test_split_panel_has_list_and_editor(notes_page):
    """Left panel has QListWidget, right panel has QPlainTextEdit."""
    assert notes_page.note_list is not None
    assert notes_page.editor is not None


def test_title_editor_exists(notes_page):
    assert notes_page.title_edit is not None


def test_new_note_button_exists(notes_page):
    assert notes_page.new_btn is not None


def test_delete_button_exists(notes_page):
    assert notes_page.delete_btn is not None


def test_search_input_exists(notes_page):
    assert notes_page.search_edit is not None


# --- List notes ---


def test_refresh_populates_list(notes_page):
    _seed(notes_page, [("Meeting notes", "discuss roadmap"), ("Todo", "buy milk")])
    assert notes_page.note_list.count() == 2


def test_list_shows_note_titles(notes_page):
    _seed(notes_page, [("Meeting notes", ""), ("Ideas", "")])
    titles = [
        notes_page.note_list.item(i).text()
        for i in range(notes_page.note_list.count())
    ]
    assert "Meeting notes" in titles
    assert "Ideas" in titles


# --- Select note loads editor ---


def test_select_note_loads_body(notes_page):
    _seed(notes_page, [("Meeting", "discuss roadmap"), ("Todo", "buy milk")])
    # Click the first item
    notes_page.note_list.setCurrentRow(0)
    assert "discuss roadmap" in notes_page.editor.toPlainText() or "buy milk" in notes_page.editor.toPlainText()


def test_select_note_loads_title(notes_page):
    _seed(notes_page, [("Meeting", "discuss roadmap")])
    notes_page.note_list.setCurrentRow(0)
    assert notes_page.title_edit.text() == "Meeting"


# --- Create new note ---


def test_create_note_adds_to_list(notes_page, qt_app):
    notes_page.create_note()
    qt_app.processEvents()
    assert notes_page.note_list.count() == 1


def test_create_note_default_title(notes_page, qt_app):
    notes_page.create_note()
    qt_app.processEvents()
    assert notes_page.title_edit.text() == "New Note"


# --- Delete note ---


def test_delete_note_removes_from_list(notes_page, qt_app):
    _seed(notes_page, [("A", "a"), ("B", "b")])
    assert notes_page.note_list.count() == 2

    notes_page.note_list.setCurrentRow(0)
    notes_page.delete_note()
    qt_app.processEvents()
    assert notes_page.note_list.count() == 1


# --- Search ---


def test_search_filters_by_title(notes_page, qt_app):
    _seed(notes_page, [("Meeting notes", "m"), ("Todo list", "t"), ("Ideas", "i")])
    assert notes_page.note_list.count() == 3

    notes_page.search_edit.setText("meet")
    qt_app.processEvents()
    visible = 0
    for i in range(notes_page.note_list.count()):
        if not notes_page.note_list.item(i).isHidden():
            visible += 1
    assert visible == 1


def test_search_clear_shows_all(notes_page, qt_app):
    _seed(notes_page, [("Meeting", "m"), ("Todo", "t")])
    notes_page.search_edit.setText("xyz")
    qt_app.processEvents()

    notes_page.search_edit.setText("")
    qt_app.processEvents()
    visible = sum(
        1
        for i in range(notes_page.note_list.count())
        if not notes_page.note_list.item(i).isHidden()
    )
    assert visible == 2


# --- Auto-save ---


def test_auto_save_persists_edits(notes_page, qt_app):
    _seed(notes_page, [("Test", "original")])
    notes_page.note_list.setCurrentRow(0)
    qt_app.processEvents()

    # Simulate edit
    notes_page.editor.setPlainText("modified content")
    qt_app.processEvents()

    # Trigger the save (normally debounced, call directly)
    notes_page._save_current()

    # Verify in DB
    engine = notes_page._test_engine
    with Session(engine) as s:
        from sqlmodel import select

        notes = list(s.exec(select(Note)).all())
    assert any(n.body == "modified content" for n in notes)


def test_auto_save_persists_title_edit(notes_page, qt_app):
    _seed(notes_page, [("Old title", "body")])
    notes_page.note_list.setCurrentRow(0)
    qt_app.processEvents()

    notes_page.title_edit.setText("New title")
    qt_app.processEvents()
    notes_page._save_current()

    engine = notes_page._test_engine
    with Session(engine) as s:
        from sqlmodel import select

        notes = list(s.exec(select(Note)).all())
    assert any(n.title == "New title" for n in notes)
