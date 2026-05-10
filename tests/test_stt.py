import numpy as np
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Hotword  # noqa: F401 -- registers metadata


def _hotword_engine(words=None):
    if words is None:
        words = ["Claude", "Claude Code", "Anthropic"]
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    with Session(e) as s:
        for w in words:
            s.add(Hotword(word=w))
        s.commit()
    return e


@pytest.fixture
def mock_whisper_model():
    with patch("talk2type.stt.WhisperModel") as WM:
        yield WM


@pytest.fixture
def mock_db():
    """Provide an in-memory DB with default hotwords, patched into stt."""
    e = _hotword_engine()

    @contextmanager
    def _sess():
        with Session(e) as s:
            yield s

    with patch("talk2type.stt.get_session", side_effect=_sess):
        yield e


def test_lazy_load(mock_whisper_model, mock_db):
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


def test_transcribe_passes_language(mock_whisper_model, mock_db):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    instance = mock_whisper_model.return_value
    instance.transcribe.return_value = iter([]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)

    # PL
    stt.transcribe(audio, language="pl")
    instance.transcribe.assert_called_with(
        audio, language="pl", beam_size=5, vad_filter=True,
        initial_prompt="Claude, Claude Code, Anthropic",
    )

    # EN
    stt.transcribe(audio, language="en")
    instance.transcribe.assert_called_with(
        audio, language="en", beam_size=5, vad_filter=True,
        initial_prompt="Claude, Claude Code, Anthropic",
    )


def test_transcribe_concatenates_segments(mock_whisper_model, mock_db):
    from talk2type.stt import WhisperSTT

    stt = WhisperSTT()
    instance = mock_whisper_model.return_value
    seg1 = MagicMock(text=" hello")
    seg2 = MagicMock(text=" world")
    instance.transcribe.return_value = iter([seg1, seg2]), MagicMock()

    audio = np.zeros(16000, dtype=np.float32)
    result = stt.transcribe(audio, language="pl")

    assert result == "hello world"


def test_unload_releases_model(mock_whisper_model, mock_db):
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
