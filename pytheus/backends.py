from threading import Lock


class LockedValue:
    """Provides a value protected by a threading Lock."""

    def __init__(self) -> None:
        self._value = 0.0
        self._lock = Lock()

    def inc(self, value: float) -> None:
        with self._lock:
            self._value += value

    def get(self) -> float:
        with self._lock:
            return self._value
