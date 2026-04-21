import numpy as np
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_whisper_model():
    with patch("talk2type.stt.WhisperModel") as WM:
        yield WM


def test_lazy_load(mock_whisper_model):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    # Constructor does NOT call WhisperModel
    mock_whisper_model.assert_not_called()
    assert stt._model is None

    # Prepare mock transcribe
    instance = mock_whisper_model.return_value
    seg1 = MagicMock(text=" hello")
    seg2 = MagicMock(text=" world")
    instance.transcribe.return_value = iter([seg1, seg2]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)
    stt.transcribe(audio, language="pl")

    # Now WhisperModel was called exactly once
    mock_whisper_model.assert_called_once_with(
        "turbo", device="cuda", compute_type="int8_float16"
    )

    # Second transcribe does NOT create another model
    stt.transcribe(audio, language="en")
    assert mock_whisper_model.call_count == 1


def test_transcribe_passes_language(mock_whisper_model):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    instance = mock_whisper_model.return_value
    instance.transcribe.return_value = iter([]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)

    # PL
    stt.transcribe(audio, language="pl")
    instance.transcribe.assert_called_with(
        audio, language="pl", beam_size=5, vad_filter=True
    )

    # EN
    stt.transcribe(audio, language="en")
    instance.transcribe.assert_called_with(
        audio, language="en", beam_size=5, vad_filter=True
    )


def test_transcribe_concatenates_segments(mock_whisper_model):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    instance = mock_whisper_model.return_value
    seg1 = MagicMock(text=" hello")
    seg2 = MagicMock(text=" world")
    instance.transcribe.return_value = iter([seg1, seg2]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)
    result = stt.transcribe(audio, language="pl")

    assert result == "hello world"


def test_unload_releases_model(mock_whisper_model):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    instance = mock_whisper_model.return_value
    instance.transcribe.return_value = iter([]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)
    stt.transcribe(audio, language="pl")
    assert stt._model is not None

    stt.unload()
    assert stt._model is None

    # Next transcribe should re-load model
    stt.transcribe(audio, language="pl")
    assert mock_whisper_model.call_count == 2


def test_unload_when_not_loaded_is_noop(mock_whisper_model):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    # unload on fresh instance should not raise
    stt.unload()
    assert stt._model is None
