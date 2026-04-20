import queue

import numpy as np
import sounddevice as sd

from .config import SAMPLE_RATE, CHANNELS, DTYPE


class Recorder:
    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._q: queue.Queue | None = None
        self._stream = None

    def start(self):
        self._q = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=lambda indata, frames, t, status: self._q.put(indata.copy()),
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        chunks = []
        while True:
            try:
                chunks.append(self._q.get_nowait())
            except queue.Empty:
                break
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()
