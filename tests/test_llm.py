import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ollama_chat():
    with patch("wisprflow.llm.chat") as mock_chat:
        response = MagicMock()
        response.message.content = "Dzisiaj byłem w sklepie."
        mock_chat.return_value = response
        yield mock_chat


def test_cleanup_calls_chat_with_think_false_and_keep_alive_3m(mock_ollama_chat):
    from wisprflow.llm import cleanup_text

    cleanup_text("dzisiaj byłem w sklepie", "pl")

    mock_ollama_chat.assert_called_once()
    kwargs = mock_ollama_chat.call_args.kwargs
    assert kwargs["think"] is False
    assert kwargs["keep_alive"] == "3m"
    assert kwargs["model"] == "qwen3.5:2b"


def test_cleanup_uses_correct_prompt_per_language(mock_ollama_chat):
    from wisprflow.llm import cleanup_text
    from wisprflow.prompts import SYSTEM_PL, SYSTEM_EN

    cleanup_text("test", "pl")
    messages_pl = mock_ollama_chat.call_args.kwargs["messages"]
    assert messages_pl[0]["content"] == SYSTEM_PL

    cleanup_text("test", "en")
    messages_en = mock_ollama_chat.call_args.kwargs["messages"]
    assert messages_en[0]["content"] == SYSTEM_EN


def test_cleanup_returns_raw_on_exception(mock_ollama_chat):
    from wisprflow.llm import cleanup_text

    mock_ollama_chat.side_effect = ConnectionError("no ollama")
    result = cleanup_text("abc", "pl")
    assert result == "abc"


def test_cleanup_empty_input_short_circuits(mock_ollama_chat):
    from wisprflow.llm import cleanup_text

    # Empty string
    cleanup_text("", "pl")
    mock_ollama_chat.assert_not_called()

    # Whitespace only
    cleanup_text("   ", "pl")
    mock_ollama_chat.assert_not_called()


def test_cleanup_strips_quotes_from_response(mock_ollama_chat):
    from wisprflow.llm import cleanup_text

    mock_ollama_chat.return_value.message.content = '"Dzisiaj byłem w sklepie."'
    result = cleanup_text("test", "pl")
    assert result == "Dzisiaj byłem w sklepie."


def test_unload_calls_chat_with_keep_alive_zero(mock_ollama_chat):
    from wisprflow.llm import unload

    unload()

    mock_ollama_chat.assert_called_once()
    kwargs = mock_ollama_chat.call_args.kwargs
    assert kwargs["keep_alive"] == 0
    assert kwargs["model"] == "qwen3.5:2b"


def test_unload_swallows_exception(mock_ollama_chat):
    from wisprflow.llm import unload

    mock_ollama_chat.side_effect = ConnectionError("no ollama")
    unload()  # should not raise
