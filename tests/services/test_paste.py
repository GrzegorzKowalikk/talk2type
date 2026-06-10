from unittest.mock import MagicMock, patch

from talk2type.services.paste import PasteService


def test_paste_empty_is_noop():
    with patch("talk2type.services.paste.pyperclip") as clip:
        with patch("talk2type.services.paste.Controller"):
            PasteService().paste("")
        clip.copy.assert_not_called()


def test_paste_copies_and_sends_ctrl_v():
    with patch("talk2type.services.paste.pyperclip") as clip, \
         patch("talk2type.services.paste.Controller") as Ctrl:
        svc = PasteService()
        svc.paste("hello")
        clip.copy.assert_called_once_with("hello")
        Ctrl.return_value.pressed.assert_called_once()
        Ctrl.return_value.press.assert_called_once_with("v")
        Ctrl.return_value.release.assert_called_once_with("v")
