import numpy as np
import pytest

pytestmark = pytest.mark.integration


def test_real_pl_transcription():
    from talk2type.services.transcription import TranscriptionService

    stt = TranscriptionService()
    # Load a pre-recorded fixture or generate silence for smoke test
    # For now, use a fixture WAV if available
    try:
        import wave

        with wave.open("tests/fixtures/sample_pl.wav", "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    except FileNotFoundError:
        pytest.skip("fixtures/sample_pl.wav not found — generate with: python -c ...")

    result = stt.transcribe(audio, language="pl")
    assert "test" in result.lower()
    stt.unload()
