from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tray_deps():
    """Patch heavy deps so Tray can be instantiated without a display."""
    with (
        patch("talk2type.ui.tray.Image") as mock_img,
        patch("talk2type.ui.tray.Icon") as mock_icon_cls,
        patch("talk2type.ui.tray.Menu") as mock_menu_cls,
        patch("talk2type.ui.tray.MenuItem") as mock_menuitem_cls,
    ):
        yield {
            "Image": mock_img,
            "Icon": mock_icon_cls,
            "Menu": mock_menu_cls,
            "MenuItem": mock_menuitem_cls,
        }


def test_tray_accepts_on_open(tray_deps):
    from talk2type.ui.tray import Tray

    on_open = MagicMock()
    on_quit = MagicMock()
    Tray(on_quit=on_quit, on_open=on_open)

    # MenuItem was called at least once with "Open"
    calls = [c.args[0] for c in tray_deps["MenuItem"].call_args_list]
    assert "Open" in calls


def test_open_callback_wired(tray_deps):
    from talk2type.ui.tray import Tray

    on_open = MagicMock()
    on_quit = MagicMock()
    Tray(on_quit=on_quit, on_open=on_open)

    # Find the MenuItem("Open", ...) call and invoke its callback
    open_call = None
    for c in tray_deps["MenuItem"].call_args_list:
        if c.args[0] == "Open":
            open_call = c
            break
    assert open_call is not None, "No 'Open' MenuItem found"

    callback = open_call.args[1]
    icon_stub = MagicMock()
    callback(icon_stub, None)
    on_open.assert_called_once()


def test_quit_callback_still_works(tray_deps):
    from talk2type.ui.tray import Tray

    on_quit = MagicMock()
    Tray(on_quit=on_quit, on_open=MagicMock())

    quit_call = None
    for c in tray_deps["MenuItem"].call_args_list:
        if c.args[0] == "Quit":
            quit_call = c
            break
    assert quit_call is not None, "No 'Quit' MenuItem found"

    callback = quit_call.args[1]
    icon_stub = MagicMock()
    callback(icon_stub, None)
    on_quit.assert_called_once()


def test_menu_has_both_items(tray_deps):
    from talk2type.ui.tray import Tray

    Tray(on_quit=MagicMock(), on_open=MagicMock())

    item_names = [c.args[0] for c in tray_deps["MenuItem"].call_args_list]
    assert "Open" in item_names
    assert "Quit" in item_names
    # Open should appear before Quit in the call list
    assert item_names.index("Open") < item_names.index("Quit")
