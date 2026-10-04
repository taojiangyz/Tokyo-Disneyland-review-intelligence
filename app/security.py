from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    retry_after_seconds: int = 0
    reason: str | None = None


class DemoUsageGuard:
    """In-memory protection for a single-process interview demo."""

    def __init__(self, requests_per_minute: int = 0, generations_per_day: int = 0):
        self.requests_per_minute = max(0, requests_per_minute)
        self.generations_per_day = max(0, generations_per_day)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._generation_day = date.today()
        self._generation_count = 0
        self._lock = Lock()

    def check_request(self, client_key: str, now: float | None = None) -> LimitDecision:
        if not self.requests_per_minute:
            return LimitDecision(True)
        current = monotonic() if now is None else now
        cutoff = current - 60
        with self._lock:
            history = self._requests[client_key]
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= self.requests_per_minute:
                retry_after = max(1, int(60 - (current - history[0])))
                return LimitDecision(False, retry_after, "rate_limit")
            history.append(current)
        return LimitDecision(True)

    def reserve_generation(self, today: date | None = None) -> LimitDecision:
        if not self.generations_per_day:
            return LimitDecision(True)
        current_day = today or date.today()
        with self._lock:
            if current_day != self._generation_day:
                self._generation_day = current_day
                self._generation_count = 0
            if self._generation_count >= self.generations_per_day:
                return LimitDecision(False, reason="daily_generation_limit")
            self._generation_count += 1
        return LimitDecision(True)

    @property
    def generation_count(self) -> int:
        return self._generation_count
