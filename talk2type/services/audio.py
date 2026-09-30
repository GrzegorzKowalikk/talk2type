import queue

import numpy as np
import sounddevice as sd

from talk2type.config import SAMPLE_RATE, CHANNELS, DTYPE


class AudioRecorder:
    def __init__(self):
        self._q: queue.Queue | None = None
        self._stream = None

    def start(self, level_callback=None):
        self._q = queue.Queue()
        q = self._q

        def _cb(indata, frames, t, status):
            q.put(indata.copy())
            if level_callback:
                level_callback(float(np.sqrt(np.mean(indata ** 2))))

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=_cb,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        assert self._q is not None
        chunks = []
        while True:
            try:
                chunks.append(self._q.get_nowait())
            except queue.Empty:
                break
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()
