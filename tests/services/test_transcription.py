import threading
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlmodel import Session, SQLModel, create_engine

from talk2type.db.model import Hotword


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    yield e
    SQLModel.metadata.drop_all(e)


@pytest.fixture
def fake_get_session(engine):
    @contextmanager
    def _get_session():
        with Session(engine) as s:
            yield s
            s.commit()

    return _get_session


def _seg(text):
    s = MagicMock()
    s.text = text
    return s


def test_refresh_hotwords_empty_table(fake_get_session):
    with patch("talk2type.services.transcription.get_session", fake_get_session):
        from talk2type.services.transcription import TranscriptionService

        svc = TranscriptionService()
        assert svc._hotwords is None


def test_refresh_hotwords_with_rows(engine, fake_get_session):
    with Session(engine) as s:
        s.add(Hotword(word="Claude"))
        s.add(Hotword(word="Anthropic"))
        s.commit()
    with patch("talk2type.services.transcription.get_session", fake_get_session):
        from talk2type.services.transcription import TranscriptionService

        svc = TranscriptionService()
        assert "Claude" in svc._hotwords
        assert "Anthropic" in svc._hotwords
        assert svc._hotwords == "Claude, Anthropic"


def test_transcribe_passes_hotwords_and_params(engine, fake_get_session):
    with Session(engine) as s:
        s.add(Hotword(word="Claude"))
        s.commit()
    with patch("talk2type.services.transcription.WhisperModel") as WM, patch(
        "talk2type.services.transcription.get_session", fake_get_session
    ):
        from talk2type.services.transcription import TranscriptionService

        model = WM.return_value
        model.transcribe.return_value = ([_seg(" hello"), _seg(" world")], None)
        svc = TranscriptionService()
        audio = np.zeros(16000, dtype=np.float32)

        result = svc.transcribe(audio, language="pl")

        assert result == "hello world"
        _args, kwargs = model.transcribe.call_args
        assert kwargs["hotwords"] == "Claude"
        assert kwargs["language"] == "pl"
        assert kwargs["beam_size"] == 5
        assert kwargs["vad_filter"] is True


def test_preload_loads_model_once():
    from talk2type.services.transcription import TranscriptionService

    with patch("talk2type.services.transcription.WhisperModel") as WM, patch.object(
        TranscriptionService, "refresh_hotwords"
    ):
        svc = TranscriptionService()
        svc.preload()
        svc.preload()
        assert WM.call_count == 1


def test_concurrent_preload_loads_once():
    from talk2type.services.transcription import TranscriptionService

    with patch("talk2type.services.transcription.WhisperModel") as WM, patch.object(
        TranscriptionService, "refresh_hotwords"
    ):
        svc = TranscriptionService()
        threads = [threading.Thread(target=svc.preload) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert WM.call_count == 1


def test_unload_then_transcribe_reloads():
    from talk2type.services.transcription import TranscriptionService

    with patch("talk2type.services.transcription.WhisperModel") as WM, patch.object(
        TranscriptionService, "refresh_hotwords"
    ):
        WM.return_value.transcribe.return_value = ([_seg(" ok")], None)
        svc = TranscriptionService()
        svc._hotwords = None
        svc.preload()
        svc.unload()
        assert svc._model is None

        result = svc.transcribe(np.zeros(16000, dtype=np.float32))

        assert result == "ok"
        assert WM.call_count == 2


def test_cuda_dll_dirs_prepended_to_path(monkeypatch):
    from talk2type.services import transcription

    monkeypatch.setenv("PATH", r"C:\existing")
    transcription._add_cuda_dll_dirs()
    import os

    head = os.environ["PATH"].split(os.pathsep)[:-1]
    assert any("cublas" in p for p in head)
    assert any("cudnn" in p for p in head)
    assert os.environ["PATH"].endswith(r"C:\existing")


def test_transcribe_does_not_hit_db():
    from talk2type.services.transcription import TranscriptionService

    with patch("talk2type.services.transcription.WhisperModel") as WM, patch.object(
        TranscriptionService, "refresh_hotwords"
    ):
        WM.return_value.transcribe.return_value = ([_seg(" hi")], None)
        svc = TranscriptionService()
        svc._hotwords = "Claude"
        with patch("talk2type.services.transcription.get_session") as gs:
            svc.transcribe(np.zeros(16000, dtype=np.float32))
            gs.assert_not_called()
