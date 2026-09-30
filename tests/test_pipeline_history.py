import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from talk2type.core.pipeline import DictationPipeline
from talk2type.core.states import DictationStateMachine, State


@pytest.fixture
def deps():
    return {
        "machine": DictationStateMachine(),
        "recorder": MagicMock(),
        "transcription": MagicMock(),
        "cleanup": MagicMock(),
        "paste": MagicMock(),
        "level_callback": MagicMock(),
    }


@pytest.fixture
def pipeline(deps):
    return DictationPipeline(**deps)


def _wait_idle(machine, timeout=2.0):
    deadline = time.monotonic() + timeout
    while machine.state is not State.IDLE and time.monotonic() < deadline:
        time.sleep(0.01)
    assert machine.state is State.IDLE


def _dictate(pipeline, deps):
    deps["recorder"].stop.return_value = np.random.randn(16000).astype(np.float32)
    pipeline.on_press("pl")
    pipeline.on_release()
    _wait_idle(deps["machine"])


def test_pipeline_calls_save_on_success(pipeline, deps):
    deps["transcription"].transcribe.return_value = "raw text"
    deps["cleanup"].cleanup.return_value = "Clean."

    with patch("talk2type.core.pipeline.save_transcription") as mock_save:
        _dictate(pipeline, deps)

    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args == ("raw text", "Clean.")
    assert kwargs["stt_ms"] >= 0
    assert kwargs["llm_ms"] >= 0


def test_pipeline_no_save_on_empty_transcription(pipeline, deps):
    deps["transcription"].transcribe.return_value = ""
    deps["cleanup"].cleanup.return_value = ""

    with patch("talk2type.core.pipeline.save_transcription") as mock_save:
        _dictate(pipeline, deps)

    mock_save.assert_not_called()


def test_pipeline_save_captures_timing(pipeline, deps):
    deps["transcription"].transcribe.return_value = "something"
    deps["cleanup"].cleanup.return_value = "Something."

    with patch("talk2type.core.pipeline.save_transcription") as mock_save:
        _dictate(pipeline, deps)

    _, kwargs = mock_save.call_args
    assert isinstance(kwargs["stt_ms"], int)
    assert isinstance(kwargs["llm_ms"], int)
