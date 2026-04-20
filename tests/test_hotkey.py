import pytest
from unittest.mock import MagicMock
from pynput.keyboard import Key


@pytest.fixture
def callbacks():
    return {
        "pl_start": MagicMock(),
        "pl_stop": MagicMock(),
        "en_start": MagicMock(),
        "en_stop": MagicMock(),
    }


@pytest.fixture
def listener(callbacks):
    from wisprflow.hotkey import HotkeyListener

    hl = HotkeyListener(
        on_pl_start=callbacks["pl_start"],
        on_pl_stop=callbacks["pl_stop"],
        on_en_start=callbacks["en_start"],
        on_en_stop=callbacks["en_stop"],
    )
    return hl


def test_f9_triggers_pl_callbacks(listener, callbacks):
    listener._on_press(Key.f9)
    callbacks["pl_start"].assert_called_once()

    listener._on_release(Key.f9)
    callbacks["pl_stop"].assert_called_once()


def test_f10_triggers_en_callbacks(listener, callbacks):
    listener._on_press(Key.f10)
    callbacks["en_start"].assert_called_once()

    listener._on_release(Key.f10)
    callbacks["en_stop"].assert_called_once()


def test_repeated_press_ignored(listener, callbacks):
    """OS auto-repeat: holding a key fires multiple press events."""
    listener._on_press(Key.f9)
    callbacks["pl_start"].assert_called_once()

    # Auto-repeat — should not trigger again
    listener._on_press(Key.f9)
    assert callbacks["pl_start"].call_count == 1

    # Release
    listener._on_release(Key.f9)
    callbacks["pl_stop"].assert_called_once()
