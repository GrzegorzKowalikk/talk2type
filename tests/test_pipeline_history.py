import numpy as np
from contextlib import ExitStack
from unittest.mock import patch, MagicMock


def _make_app():
    with ExitStack() as stack:
        stack.enter_context(patch("main.Recorder"))
        stack.enter_context(patch("main.WhisperSTT"))
        stack.enter_context(patch("main.cleanup_text"))
        stack.enter_context(patch("main.paste_text"))
        stack.enter_context(patch("main.Tray"))
        stack.enter_context(patch("main.ResourceManager"))
        stack.enter_context(patch("main.HotkeyListener"))
        stack.enter_context(patch("main.OverlayWindow"))
        from main import App
        app = App.__new__(App)
        app.recorder = MagicMock()
        app.stt = MagicMock()
        app.tray = MagicMock()
        app.resmgr = MagicMock()
        app.hotkey = MagicMock()
        app._overlay = MagicMock()
        app._busy = False
        app._lang = "pl"
        return app


def test_pipeline_calls_save_on_success():
    audio = np.random.randn(16000).astype(np.float32)
    app = _make_app()
    app.stt.transcribe.return_value = "raw text"

    with patch("main.cleanup_text", return_value="Clean."), \
         patch("main.paste_text"), \
         patch("main.save_transcription") as mock_save:
        app._run_pipeline(audio=audio, lang="pl")

    mock_save.assert_called_once()
    _, kwargs = mock_save.call_args
    assert kwargs["stt_ms"] >= 0
    assert kwargs["llm_ms"] >= 0


def test_pipeline_no_save_on_empty_transcription():
    audio = np.random.randn(16000).astype(np.float32)
    app = _make_app()
    app.stt.transcribe.return_value = ""

    with patch("main.cleanup_text"), \
         patch("main.paste_text"), \
         patch("main.save_transcription") as mock_save:
        app._run_pipeline(audio=audio, lang="pl")

    mock_save.assert_not_called()


def test_pipeline_save_captures_timing():
    audio = np.random.randn(16000).astype(np.float32)
    app = _make_app()
    app.stt.transcribe.return_value = "something"

    with patch("main.cleanup_text", return_value="Something."), \
         patch("main.paste_text"), \
         patch("main.save_transcription") as mock_save:
        app._run_pipeline(audio=audio, lang="pl")

    _, kwargs = mock_save.call_args
    assert isinstance(kwargs["stt_ms"], int)
    assert isinstance(kwargs["llm_ms"], int)
