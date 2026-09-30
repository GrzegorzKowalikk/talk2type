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


@pytest.fixture
def make_tray(qt_app):
    from talk2type.ui.tray import Tray

    trays = []

    def _make(**kw):
        t = Tray(**kw)
        trays.append(t)
        return t

    yield _make
    for t in trays:
        t._icon.hide()


def _actions(tray):
    return {a.text(): a for a in tray._icon.contextMenu().actions()}


def test_menu_has_open_then_quit(make_tray):
    tray = make_tray(on_quit=MagicMock(), on_open=MagicMock())
    assert list(_actions(tray)) == ["Open", "Quit"]


def test_open_action_calls_on_open(make_tray):
    on_open = MagicMock()
    tray = make_tray(on_quit=MagicMock(), on_open=on_open)
    _actions(tray)["Open"].trigger()
    on_open.assert_called_once()


def test_quit_action_calls_on_quit(make_tray):
    on_quit = MagicMock()
    tray = make_tray(on_quit=on_quit, on_open=MagicMock())
    _actions(tray)["Quit"].trigger()
    on_quit.assert_called_once()


def test_left_click_opens_context_does_not(make_tray):
    from PySide6.QtWidgets import QSystemTrayIcon

    on_open = MagicMock()
    tray = make_tray(on_quit=MagicMock(), on_open=on_open)
    tray._icon.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    tray._icon.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    on_open.assert_called_once()
