import enum
import threading

from PySide6.QtCore import QObject, Signal


class State(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"


class DictationStateMachine(QObject):
    """Single source of truth for dictation state.

    Event methods are thread-safe (called from pynput and pipeline threads);
    Qt delivers cross-thread signal emissions as queued calls to subscribers
    living in the GUI thread.
    """

    recording_started = Signal(str)   # lang
    processing_started = Signal()
    processing_progress = Signal(str, str)  # label, detail (e.g. "45%" or "1.2/3.1 GB")
    returned_to_idle = Signal(str)    # reason: done | cancelled | error | too_short

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._state = State.IDLE
        self._lang = ""

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    @property
    def lang(self) -> str:
        with self._lock:
            return self._lang

    def press(self, lang: str) -> bool:
        with self._lock:
            if self._state is not State.IDLE:
                return False
            self._state = State.RECORDING
            self._lang = lang
        self.recording_started.emit(lang)
        return True

    def release(self) -> bool:
        with self._lock:
            if self._state is not State.RECORDING:
                return False
            self._state = State.PROCESSING
        self.processing_started.emit()
        return True

    def cancel(self) -> State | None:
        """Esc pressed. Returns the state that was cancelled, None when idle."""
        with self._lock:
            if self._state is State.IDLE:
                return None
            prev = self._state
            self._state = State.IDLE
        self.returned_to_idle.emit("cancelled")
        return prev

    def finish(self, reason: str) -> None:
        """Pipeline ended. Acts only in PROCESSING so a stale worker can't
        reset a recording the user already restarted."""
        with self._lock:
            if self._state is not State.PROCESSING:
                return
            self._state = State.IDLE
        self.returned_to_idle.emit(reason)
