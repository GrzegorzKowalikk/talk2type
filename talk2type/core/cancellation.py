import threading


class CancellationToken:
    """Thread-safe one-way cancel flag shared between UI events and pipeline thread."""

    def __init__(self):
        self._evt = threading.Event()

    def cancel(self) -> None:
        self._evt.set()

    @property
    def cancelled(self) -> bool:
        return self._evt.is_set()
