import numpy as np
import pytest
from unittest.mock import MagicMock, patch


class FakeStream:
    """Minimal mock of sd.InputStream."""

    def __init__(self, callback):
        self._cb = callback
        self._started = False

    def start(self):
        self._started = True

    def stop(self):
        self._started = False

    def close(self):
        pass

    def push_chunk(self, frames=512):
        """Simulate the callback firing with a chunk of audio."""
        indata = np.random.randn(frames, 1).astype(np.float32)
        self._cb(indata, frames, None, None)


@pytest.fixture
def mock_sd():
    with patch("wisprflow.audio.sd") as sd_mod:
        stream_holder = {}

        def make_stream(*a, **kw):
            cb = kw.get("callback") or (a[3] if len(a) > 3 else None)
            s = FakeStream(cb)
            stream_holder["stream"] = s
            return s

        sd_mod.InputStream = MagicMock(side_effect=make_stream)
        yield sd_mod, stream_holder


def test_recorder_start_stop_returns_float32_mono(mock_sd):
    from talk2type.audio import Recorder

    sd_mod, holder = mock_sd
    rec = Recorder()
    rec.start()
    stream = holder["stream"]

    # Simulate 3 callbacks of 512 frames each
    for _ in range(3):
        stream.push_chunk(512)

    result = rec.stop()

    assert result.dtype == np.float32
    assert result.ndim == 1
    assert result.shape[0] == 512 * 3


def test_recorder_stop_without_start_returns_empty(mock_sd):
    from talk2type.audio import Recorder

    rec = Recorder()
    # Call stop without ever calling start — should return empty, not crash
    # But we need a stream to stop. Since _stream is None, stop() must handle that.
    result = rec.stop()
    assert result.dtype == np.float32
    assert result.size == 0


def test_recorder_second_start_resets_queue(mock_sd):
    from talk2type.audio import Recorder

    sd_mod, holder = mock_sd
    rec = Recorder()

    # First recording session
    rec.start()
    stream = holder["stream"]
    stream.push_chunk(512)
    audio1 = rec.stop()
    assert audio1.shape[0] == 512  # got the chunk

    # Second recording session — no chunks pushed
    rec.start()
    holder["stream"]
    audio2 = rec.stop()
    assert audio2.size == 0  # empty, not stale data from first session
