from unittest.mock import MagicMock, patch

import pytest

from talk2type.prompts import SYSTEM_EN, SYSTEM_PL
from talk2type.services.cleanup import CleanupService, strip_fillers


def _mock_response(content: str):
    resp = MagicMock()
    resp.message.content = content
    return resp


def test_cleanup_empty_input_short_circuits():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        service = CleanupService()
        assert service.cleanup("", "pl") == ""
        assert service.cleanup("   ", "pl") == "   "
        mock_chat.assert_not_called()


def test_cleanup_builds_fresh_pl_messages_and_kwargs():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        mock_chat.return_value = _mock_response("Tekst.")
        service = CleanupService()

        service.cleanup("tekst", "pl")

        mock_chat.assert_called_once()
        kwargs = mock_chat.call_args.kwargs
        messages = kwargs["messages"]
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": SYSTEM_PL}
        assert messages[1]["content"] == 'Tekst: "tekst"\nOdpowiedź:'
        assert kwargs["keep_alive"] == "15m"
        assert kwargs["think"] is False
        assert kwargs["options"] == {"temperature": 0.1, "num_predict": -1}


def test_cleanup_uses_english_prompt_and_labels():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        mock_chat.return_value = _mock_response("Text.")
        service = CleanupService()

        service.cleanup("text", "en")

        messages = mock_chat.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": SYSTEM_EN}
        assert messages[1]["content"] == 'Text: "text"\nResponse:'


def test_cleanup_strips_whitespace_and_surrounding_quotes():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        mock_chat.return_value = _mock_response('  "Dzisiaj byłem w sklepie."  ')
        service = CleanupService()

        result = service.cleanup("dzisiaj byłem w sklepie", "pl")

        assert result == "Dzisiaj byłem w sklepie."


def test_cleanup_returns_raw_on_exception():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        mock_chat.side_effect = ConnectionError("no ollama")
        service = CleanupService()

        assert service.cleanup("abc", "pl") == "abc"


def test_preload_calls_chat_with_minimal_options():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        service = CleanupService()

        service.preload()

        mock_chat.assert_called_once()
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["options"] == {"num_predict": 1}
        assert kwargs["keep_alive"] == "15m"


def test_unload_calls_chat_with_keep_alive_zero():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        service = CleanupService()

        service.unload()

        mock_chat.assert_called_once()
        assert mock_chat.call_args.kwargs["keep_alive"] == 0


def test_unload_swallows_exception():
    with patch("talk2type.services.cleanup.chat") as mock_chat:
        mock_chat.side_effect = ConnectionError("no ollama")
        service = CleanupService()

        service.unload()  # should not raise


def test_prompt_content_sanity():
    assert "NIGDY nie odpowiadaj" in SYSTEM_PL
    assert SYSTEM_PL.count("Tekst:") >= 3
    assert "NEVER answer" in SYSTEM_EN
    assert SYSTEM_EN.count("Input:") >= 3


@pytest.mark.parametrize(
    "text, expected",
    [
        ("dzisiaj eee pojechałem yyy do sklepu", "dzisiaj pojechałem do sklepu"),
        ("mmm aaa hhh", ""),
        ("eeee yyyyy", ""),
        ("Mam dwa psy", "Mam dwa psy"),
        (" to jest hej", "to jest hej"),
        ("Eee no właśnie", "no właśnie"),
        ("", ""),
        ("yyy", ""),
        ("ma eee sens", "ma sens"),
    ],
)
def test_strip_fillers(text, expected):
    assert strip_fillers(text) == expected
