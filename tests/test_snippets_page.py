import sys
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Snippet  # noqa: F401 — registers metadata


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def snippets_page(qt_app):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    from talk2type.ui.pages.snippets import SnippetsPage

    @contextmanager
    def _sess():
        with Session(engine) as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    with patch("talk2type.ui.pages.snippets.get_session", side_effect=_sess):
        w = SnippetsPage()
        w._test_engine = engine
        w.show()
        yield w
    w.close()


def _seed(engine, *snippets: Snippet):
    with Session(engine) as s:
        for sn in snippets:
            s.add(sn)
        s.commit()


# ---------------------------------------------------------------------------
# 1. List snippets from DB
# ---------------------------------------------------------------------------


def test_lists_snippets_from_db(snippets_page, qt_app):
    _seed(
        snippets_page._test_engine,
        Snippet(name="Greeting", body="Hello there"),
        Snippet(name="Bug Report", body="Steps: 1."),
    )
    snippets_page.refresh_data()
    qt_app.processEvents()

    assert snippets_page.list_widget.count() == 2


def test_shows_name_and_body_preview(snippets_page, qt_app):
    _seed(
        snippets_page._test_engine,
        Snippet(name="Greeting", body="Hello there\nSecond line"),
    )
    snippets_page.refresh_data()
    qt_app.processEvents()

    item = snippets_page.list_widget.item(0)
    widget = snippets_page.list_widget.itemWidget(item)
    assert "Greeting" in widget.findChild(object, "snippet_name").text()
    assert "Hello there" in widget.findChild(object, "snippet_preview").text()


# ---------------------------------------------------------------------------
# 2. Add snippet via UI
# ---------------------------------------------------------------------------


def test_add_snippet_via_form(snippets_page, qt_app):
    snippets_page.new_btn.click()
    qt_app.processEvents()

    snippets_page.form_name.setText("Sign-off")
    snippets_page.form_body.setPlainText("Best regards")
    snippets_page.save_btn.click()
    qt_app.processEvents()

    assert snippets_page.list_widget.count() == 1
    item = snippets_page.list_widget.item(0)
    widget = snippets_page.list_widget.itemWidget(item)
    assert "Sign-off" in widget.findChild(object, "snippet_name").text()


def test_form_hidden_after_save(snippets_page, qt_app):
    snippets_page.new_btn.click()
    qt_app.processEvents()
    assert snippets_page.form_container.isVisible()

    snippets_page.form_name.setText("X")
    snippets_page.form_body.setPlainText("Y")
    snippets_page.save_btn.click()
    qt_app.processEvents()

    assert not snippets_page.form_container.isVisible()


# ---------------------------------------------------------------------------
# 3. Delete snippet
# ---------------------------------------------------------------------------


def test_delete_snippet(snippets_page, qt_app):
    _seed(
        snippets_page._test_engine,
        Snippet(name="To Delete", body="gone"),
    )
    snippets_page.refresh_data()
    qt_app.processEvents()
    assert snippets_page.list_widget.count() == 1

    item = snippets_page.list_widget.item(0)
    widget = snippets_page.list_widget.itemWidget(item)
    del_btn = widget.findChild(object, "delete_btn")
    del_btn.click()
    qt_app.processEvents()

    assert snippets_page.list_widget.count() == 0


# ---------------------------------------------------------------------------
# 4. Click to copy body to clipboard
# ---------------------------------------------------------------------------


def test_click_copies_body_to_clipboard(snippets_page, qt_app):
    _seed(
        snippets_page._test_engine,
        Snippet(name="Greeting", body="Hello, clipboard!"),
    )
    snippets_page.refresh_data()
    qt_app.processEvents()


    idx = snippets_page.list_widget.model().index(0, 0)
    snippets_page.list_widget.clicked.emit(idx)
    qt_app.processEvents()

    from PySide6.QtWidgets import QApplication

    clipboard = QApplication.clipboard()
    assert clipboard.text() == "Hello, clipboard!"


# ---------------------------------------------------------------------------
# 5. Search / filter by name
# ---------------------------------------------------------------------------


def test_search_filters_by_name(snippets_page, qt_app):
    _seed(
        snippets_page._test_engine,
        Snippet(name="Greeting", body="Hi"),
        Snippet(name="Bug Report", body="Steps"),
    )
    snippets_page.refresh_data()
    qt_app.processEvents()
    assert snippets_page.list_widget.count() == 2

    snippets_page.search_input.setText("greet")
    qt_app.processEvents()

    visible = sum(
        1
        for i in range(snippets_page.list_widget.count())
        if not snippets_page.list_widget.item(i).isHidden()
    )
    assert visible == 1
