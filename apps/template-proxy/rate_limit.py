from __future__ import annotations

import threading
import time
from collections import deque


RATE_LIMIT_PER_HOUR = 100
WINDOW_SECONDS = 3600
GLOBAL_RATE_LIMIT_PER_DAY = 5000
GLOBAL_WINDOW_SECONDS = 86400

_counters: dict[str, deque[float]] = {}
_counters_lock = threading.Lock()
_global_counter: deque[float] = deque()
_global_lock = threading.Lock()


def check(sandbox_id: str) -> int | None:
    """Return retry_after_seconds when the sandbox-specific limit is full."""
    now = time.time()
    with _counters_lock:
        timestamps = _counters.setdefault(sandbox_id, deque())
        while timestamps and timestamps[0] < now - WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT_PER_HOUR:
            return int(timestamps[0] + WINDOW_SECONDS - now) + 1
        timestamps.append(now)
        return None


def check_global() -> int | None:
    """Return retry_after_seconds when the global pilot limit is full."""
    now = time.time()
    with _global_lock:
        while _global_counter and _global_counter[0] < now - GLOBAL_WINDOW_SECONDS:
            _global_counter.popleft()
        if len(_global_counter) >= GLOBAL_RATE_LIMIT_PER_DAY:
            return int(_global_counter[0] + GLOBAL_WINDOW_SECONDS - now) + 1
        _global_counter.append(now)
        return None
