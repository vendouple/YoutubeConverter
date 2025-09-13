from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

# Defaults (ms)
INFO_DURATION = 30_000
SUCCESS_DURATION = 10_000
FAIL_DURATION = 60_000  # sticky candidate


@dataclass
class Notification:
    category: str  # info|success|fail
    message: str
    duration_ms: int
    sticky: bool = False


class NotificationDispatcher:
    """Lightweight pub-sub dispatcher; UI layer can subscribe.

    Implementation intentionally minimal; expanded features (queueing, coalescing) can be added later.
    """

    def __init__(self):
        self._subscribers: list[Callable[[Notification], None]] = []

    def subscribe(self, cb: Callable[[Notification], None]) -> None:
        if cb not in self._subscribers:
            self._subscribers.append(cb)

    def unsubscribe(self, cb: Callable[[Notification], None]) -> None:
        if cb in self._subscribers:
            self._subscribers.remove(cb)

    def emit(
        self,
        category: str,
        message: str,
        *,
        sticky: Optional[bool] = None,
        override_duration: Optional[int] = None,
    ):
        if category not in ("info", "success", "fail"):
            raise ValueError(f"Unknown category {category}")
        if override_duration is not None:
            duration = override_duration
        else:
            if category == "info":
                duration = INFO_DURATION
            elif category == "success":
                duration = SUCCESS_DURATION
            else:
                duration = FAIL_DURATION
        if sticky is None:
            sticky = category == "fail"
        note = Notification(category, message, duration, sticky)
        for cb in list(self._subscribers):
            try:
                cb(note)
            except Exception:
                # Best effort; ignore subscriber errors
                pass
