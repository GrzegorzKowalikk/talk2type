from unittest.mock import patch


@patch("talk2type.paste.pyperclip")
@patch("talk2type.paste._kb")
def test_paste_copies_then_ctrl_v(mock_kb, mock_pyperclip):
    from talk2type.paste import paste_text

    paste_text("hello")

    mock_pyperclip.copy.assert_called_once_with("hello")

    # Verify Ctrl+V sequence: pressed(Key.ctrl), press('v'), release('v'), release ctrl
    mock_kb.pressed.assert_called_once()
    mock_kb.press.assert_called_with("v")
    mock_kb.release.assert_any_call("v")


@patch("talk2type.paste.pyperclip")
def test_paste_empty_noop(mock_pyperclip):
    from talk2type.paste import paste_text

    paste_text("")
    mock_pyperclip.copy.assert_not_called()

    paste_text(None)
    mock_pyperclip.copy.assert_not_called()
