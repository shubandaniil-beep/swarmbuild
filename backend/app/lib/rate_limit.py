"""In-process sliding-window limiter for login brute-force protection.

Keyed by (bucket, identity); tracks recent failed attempts and blocks once a
threshold is exceeded within the window. A successful login clears the key.
State is per-process — fine for the single-worker MVP; move to Redis if the
backend is ever scaled horizontally.
"""
import threading
import time
from collections import defaultdict, deque

_LOCK = threading.Lock()
_ATTEMPTS: dict[tuple[str, str], deque] = defaultdict(deque)


def _prune(dq: deque, window_seconds: float) -> None:
    cutoff = time.time() - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()


def check(bucket: str, identity: str, max_attempts: int, window_seconds: float) -> bool:
    """Return True if the identity is currently allowed (under the limit)."""
    if max_attempts <= 0:
        return True
    with _LOCK:
        dq = _ATTEMPTS[(bucket, identity)]
        _prune(dq, window_seconds)
        return len(dq) < max_attempts


def record_failure(bucket: str, identity: str, window_seconds: float) -> None:
    with _LOCK:
        dq = _ATTEMPTS[(bucket, identity)]
        _prune(dq, window_seconds)
        dq.append(time.time())


def clear(bucket: str, identity: str) -> None:
    with _LOCK:
        _ATTEMPTS.pop((bucket, identity), None)
