# tests/core/test_pipeline.py
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from talk2type.core.pipeline import MIN_SAMPLES, DictationPipeline
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
        "on_activity": MagicMock(),
    }


@pytest.fixture
def pipeline(deps):
    return DictationPipeline(**deps)


def _wait_idle(machine, timeout=2.0):
    deadline = time.monotonic() + timeout
    while machine.state is not State.IDLE and time.monotonic() < deadline:
        time.sleep(0.01)
    assert machine.state is State.IDLE


def test_happy_path(pipeline, deps):
    audio = np.zeros(16000, dtype=np.float32)
    deps["recorder"].stop.return_value = audio
    deps["transcription"].transcribe.return_value = "raw"
    deps["cleanup"].cleanup.return_value = "cleaned"
    with patch("talk2type.core.pipeline.save_transcription") as save:
        pipeline.on_press("pl")
        pipeline.on_release()
        _wait_idle(deps["machine"])
        deps["paste"].paste.assert_called_once_with("cleaned")
        save.assert_called_once()


def test_press_starts_recorder_and_preloads(pipeline, deps):
    pipeline.on_press("pl")
    deps["recorder"].start.assert_called_once_with(level_callback=deps["level_callback"])
    deps["on_activity"].assert_called_once()
    deadline = time.monotonic() + 2.0
    while not deps["transcription"].preload.called and time.monotonic() < deadline:
        time.sleep(0.01)
    deps["transcription"].preload.assert_called_once()
    deps["cleanup"].preload.assert_called_once()


def test_press_when_busy_does_not_start_recorder(pipeline, deps):
    pipeline.on_press("pl")
    deps["recorder"].start.reset_mock()
    pipeline.on_press("en")
    deps["recorder"].start.assert_not_called()


def test_short_audio_cancels_silently(pipeline, deps):
    deps["recorder"].stop.return_value = np.zeros(MIN_SAMPLES - 1, dtype=np.float32)
    pipeline.on_press("pl")
    pipeline.on_release()
    _wait_idle(deps["machine"])
    deps["transcription"].transcribe.assert_not_called()


def test_cancel_while_recording_discards_audio(pipeline, deps):
    pipeline.on_press("pl")
    pipeline.on_cancel()
    deps["recorder"].stop.assert_called_once()
    deps["transcription"].transcribe.assert_not_called()
    assert deps["machine"].state is State.IDLE


def test_cancel_during_processing_discards_result(pipeline, deps):
    gate = threading.Event()
    deps["recorder"].stop.return_value = np.zeros(16000, dtype=np.float32)

    def slow_transcribe(*a, **k):
        gate.wait(2.0)
        return "raw"

    deps["transcription"].transcribe.side_effect = slow_transcribe
    with patch("talk2type.core.pipeline.save_transcription") as save:
        pipeline.on_press("pl")
        pipeline.on_release()
        pipeline.on_cancel()          # cancels token, machine -> IDLE
        gate.set()                    # let STT "finish"
        time.sleep(0.2)
        deps["paste"].paste.assert_not_called()
        save.assert_not_called()


def test_stale_thread_does_not_kill_new_recording(pipeline, deps):
    gate = threading.Event()
    deps["recorder"].stop.return_value = np.zeros(16000, dtype=np.float32)
    deps["transcription"].transcribe.side_effect = lambda *a, **k: (gate.wait(2.0), "raw")[1]
    pipeline.on_press("pl")
    pipeline.on_release()
    pipeline.on_cancel()
    pipeline.on_press("en")           # new recording starts
    gate.set()                        # stale worker finishes now
    time.sleep(0.2)
    assert deps["machine"].state is State.RECORDING


def test_error_in_stt_returns_to_idle(pipeline, deps):
    deps["recorder"].stop.return_value = np.zeros(16000, dtype=np.float32)
    deps["transcription"].transcribe.side_effect = RuntimeError("boom")
    pipeline.on_press("pl")
    pipeline.on_release()
    _wait_idle(deps["machine"])
    deps["paste"].paste.assert_not_called()


def test_empty_raw_not_saved(pipeline, deps):
    deps["recorder"].stop.return_value = np.zeros(16000, dtype=np.float32)
    deps["transcription"].transcribe.return_value = ""
    deps["cleanup"].cleanup.return_value = ""
    with patch("talk2type.core.pipeline.save_transcription") as save:
        pipeline.on_press("pl")
        pipeline.on_release()
        _wait_idle(deps["machine"])
        save.assert_not_called()
