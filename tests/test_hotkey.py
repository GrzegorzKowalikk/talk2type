# tests/test_hotkey.py
from unittest.mock import MagicMock

from pynput.keyboard import Key

from talk2type.hotkey import HotkeyListener


def _listener():
    cbs = {"start": MagicMock(), "stop": MagicMock(), "cancel": MagicMock()}
    hl = HotkeyListener(on_start=cbs["start"], on_stop=cbs["stop"], on_cancel=cbs["cancel"])
    return hl, cbs


def test_f9_press_starts_pl_once():
    hl, cbs = _listener()
    hl._on_press(Key.f9)
    hl._on_press(Key.f9)  # auto-repeat while held
    cbs["start"].assert_called_once_with("pl")


def test_f9_release_stops_pl():
    hl, cbs = _listener()
    hl._on_press(Key.f9)
    hl._on_release(Key.f9)
    cbs["stop"].assert_called_once_with("pl")


def test_f10_maps_to_en():
    hl, cbs = _listener()
    hl._on_press(Key.f10)
    cbs["start"].assert_called_once_with("en")


def test_esc_triggers_cancel():
    hl, cbs = _listener()
    hl._on_press(Key.esc)
    cbs["cancel"].assert_called_once_with()
    cbs["start"].assert_not_called()


def test_other_keys_ignored():
    hl, cbs = _listener()
    hl._on_press(Key.space)
    hl._on_release(Key.space)
    assert not any(m.called for m in cbs.values())
