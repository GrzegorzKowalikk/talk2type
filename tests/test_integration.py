"""Integration tests: MainWindow wired to real pages, tray lifecycle."""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# --- Tray → MainWindow lifecycle ---


def test_tray_open_shows_main_window(qt_app):
    """Simulating the tray 'Open' callback invokes window.show()."""
    from talk2type.ui.tray import Tray

    shown = MagicMock()

    tray = Tray(on_quit=MagicMock(), on_open=shown)
    tray._icon.contextMenu().actions()[0].trigger()
    shown.assert_called_once()
    tray._icon.hide()


def test_main_window_has_real_page_widgets(qt_app):
    """All five pages are real page classes, not bare QWidgets."""
    from talk2type.ui.pages.dictionary import DictionaryPage
    from talk2type.ui.pages.history import HistoryPage
    from talk2type.ui.pages.home import HomePage
    from talk2type.ui.pages.notes import NotesPage
    from talk2type.ui.pages.snippets import SnippetsPage
    from talk2type.ui.main_window import MainWindow

    w = MainWindow()
    assert isinstance(w.home_page, HomePage)
    assert isinstance(w.history_page, HistoryPage)
    assert isinstance(w.dictionary_page, DictionaryPage)
    assert isinstance(w.snippets_page, SnippetsPage)
    assert isinstance(w.notes_page, NotesPage)
    w.close()


def test_switch_to_history_calls_refresh(qt_app):
    """Clicking the History nav button triggers refresh_data on that page."""
    from talk2type.ui.main_window import MainWindow

    w = MainWindow()
    refreshed = MagicMock()
    w.history_page.refresh_data = refreshed

    # Click the History nav button
    sidebar = w.findChild(object, "sidebar")
    nav_buttons = [b for b in sidebar.children() if b.objectName().startswith("nav_")]
    history_btn = next(b for b in nav_buttons if "history" in b.objectName())
    history_btn.click()
    qt_app.processEvents()

    refreshed.assert_called_once()
    w.close()


def test_refresh_current_page_delegates_to_active_page(qt_app):
    """refresh_current_page() calls refresh_data on the visible page."""
    from talk2type.ui.main_window import MainWindow

    w = MainWindow()
    # Home is the default active page
    home_refresh = MagicMock()
    w.home_page.refresh_data = home_refresh
    w.refresh_current_page()
    home_refresh.assert_called_once()
    w.close()


def test_window_close_and_reopen(qt_app):
    """Closing and re-showing the window does not crash."""
    from talk2type.ui.main_window import MainWindow

    w = MainWindow()
    w.show()
    qt_app.processEvents()
    assert w.isVisible()

    w.close()
    qt_app.processEvents()
    assert not w.isVisible()

    w.show()
    qt_app.processEvents()
    assert w.isVisible()
    w.close()
