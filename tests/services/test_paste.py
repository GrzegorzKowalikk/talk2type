from unittest.mock import patch

from talk2type.services.paste import PasteService


def test_paste_empty_is_noop():
    with patch("talk2type.services.paste.win32clipboard") as clip:
        with patch("talk2type.services.paste.Controller"):
            PasteService().paste("")
        clip.SetClipboardText.assert_not_called()


def test_paste_copies_and_sends_ctrl_v():
    with patch("talk2type.services.paste.win32clipboard") as clip, \
         patch("talk2type.services.paste.Controller") as Ctrl:
        svc = PasteService()
        svc.paste("hello")
        assert clip.SetClipboardText.call_args.args[0] == "hello"
        clip.CloseClipboard.assert_called_once()
        Ctrl.return_value.pressed.assert_called_once()
        Ctrl.return_value.press.assert_called_once_with("v")
        Ctrl.return_value.release.assert_called_once_with("v")
