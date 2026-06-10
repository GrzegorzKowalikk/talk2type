import sys

import pytest


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def win(qt_app):
    from talk2type.ui.main_window import MainWindow

    w = MainWindow()
    yield w
    if w.isVisible():
        w.close()


# --- Structure ---

def test_window_title(win):
    assert win.windowTitle() == "Talk2Type"


def test_sidebar_has_five_buttons(win):
    sidebar = win.findChild(object, "sidebar")
    buttons = [b for b in sidebar.children() if b.objectName().startswith("nav_")]
    assert len(buttons) == 5


def test_stacked_widget_has_five_pages(win):
    stack = win.findChild(object, "pages")
    assert stack.count() == 5


def test_sidebar_width(win):
    sidebar = win.findChild(object, "sidebar")
    assert sidebar.width() == 200


# --- Page switching ---

def test_switch_page_on_button_click(win, qt_app):
    buttons = win.findChild(object, "sidebar").findChildren(object)
    nav_buttons = [b for b in buttons if b.objectName().startswith("nav_")]
    history_btn = next(b for b in nav_buttons if "history" in b.objectName())

    history_btn.click()
    qt_app.processEvents()

    stack = win.findChild(object, "pages")
    assert stack.currentIndex() == nav_buttons.index(history_btn)


def test_active_button_highlight(win, qt_app):
    buttons = win.findChild(object, "sidebar").findChildren(object)
    nav_buttons = [b for b in buttons if b.objectName().startswith("nav_")]
    history_btn = next(b for b in nav_buttons if "history" in b.objectName())

    history_btn.click()
    qt_app.processEvents()

    assert history_btn.property("active") is True
    for b in nav_buttons:
        if b is not history_btn:
            assert b.property("active") is not True


# --- Dark theme colors ---

def test_window_dark_background(win):
    ss = win.styleSheet()
    assert "#1e1e2e" in ss


def test_sidebar_dark_background(win):
    ss = win.styleSheet()
    assert "#11111b" in ss or "#1e1e2e" in ss


def test_text_color_light(win):
    ss = win.styleSheet()
    assert "#cdd6f4" in ss
