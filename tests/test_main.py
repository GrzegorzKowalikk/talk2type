import numpy as np
import pytest
from contextlib import ExitStack
from unittest.mock import patch

mock_unload_llm = patch("main.unload_llm")


@pytest.fixture
def app_with_mocks():
    with ExitStack() as stack:
        MockRecorder = stack.enter_context(patch("main.Recorder"))
        MockSTT = stack.enter_context(patch("main.WhisperSTT"))
        mock_cleanup = stack.enter_context(patch("main.cleanup_text"))
        mock_paste = stack.enter_context(patch("main.paste_text"))
        MockTray = stack.enter_context(patch("main.Tray"))
        MockResMgr = stack.enter_context(patch("main.ResourceManager"))
        MockHotkey = stack.enter_context(patch("main.HotkeyListener"))

        from main import App

        app = App.__new__(App)
        app.recorder = MockRecorder.return_value
        app.stt = MockSTT.return_value
        app.tray = MockTray.return_value
        app.resmgr = MockResMgr.return_value
        app.hotkey = MockHotkey.return_value
        app._overlay = stack.enter_context(patch("main.OverlayWindow")).return_value
        app._busy = False
        app._lang = "pl"

        yield (
            app,
            {
                "recorder": app.recorder,
                "stt": app.stt,
                "cleanup": mock_cleanup,
                "paste": mock_paste,
                "tray": app.tray,
            },
        )


def test_orchestrator_pipeline(app_with_mocks):
    app, mocks = app_with_mocks

    audio = np.random.randn(16000).astype(np.float32)
    mocks["recorder"].stop.return_value = audio
    mocks["stt"].transcribe.return_value = "raw text"
    mocks["cleanup"].return_value = "cleaned text"

    app._start("pl")
    app._stop("pl")

    mocks["recorder"].start.assert_called_once()
    mocks["recorder"].stop.assert_called_once()
    mocks["stt"].transcribe.assert_called_once_with(audio, language="pl")
    mocks["cleanup"].assert_called_once_with("raw text", language="pl")
    mocks["paste"].assert_called_once_with("cleaned text")

    state_calls = [c[0][0] for c in mocks["tray"].set_state.call_args_list]
    assert state_calls == ["recording", "processing", "idle"]


def test_short_audio_skips_transcription(app_with_mocks):
    app, mocks = app_with_mocks

    short_audio = np.zeros(800, dtype=np.float32)
    mocks["recorder"].stop.return_value = short_audio

    app._start("pl")
    app._stop("pl")

    mocks["stt"].transcribe.assert_not_called()
    mocks["paste"].assert_not_called()


def test_busy_guard(app_with_mocks):
    app, mocks = app_with_mocks

    app._busy = True
    app._start("pl")
    mocks["recorder"].start.assert_not_called()

    app._stop("pl")
    mocks["recorder"].stop.assert_not_called()


def test_unload_all_calls_both(app_with_mocks):
    app, mocks = app_with_mocks

    with patch("main.unload_llm") as mock_unload_llm:
        app.unload_all()

    mocks["stt"].unload.assert_called_once()
    mock_unload_llm.assert_called_once()
