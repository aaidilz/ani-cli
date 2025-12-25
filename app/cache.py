"""Tiny in-process TTL cache.

Useful to reduce repeated fan-out to upstream providers for hot endpoints.
This is best-effort and resets when the process restarts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Dict, Generic, Hashable, Optional, Tuple, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class _Entry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, maxsize: int = 512):
        self._ttl = float(ttl_seconds)
        self._maxsize = int(maxsize)
        self._lock = RLock()
        self._data: Dict[Hashable, _Entry[T]] = {}

    def get(self, key: Hashable) -> Optional[T]:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._data.pop(key, None)
                return None
            return entry.value

    def set(self, key: Hashable, value: T) -> None:
        now = time.monotonic()
        with self._lock:
            # purge expired
            expired_keys = [k for k, v in self._data.items() if v.expires_at <= now]
            for k in expired_keys:
                self._data.pop(k, None)

            # simple size cap
            while len(self._data) >= self._maxsize:
                self._data.pop(next(iter(self._data)))

            self._data[key] = _Entry(expires_at=now + self._ttl, value=value)

    def get_or_set(self, key: Hashable, factory: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value)
        return value


# Default caches used by routes
SEARCH_CACHE: TTLCache = TTLCache(ttl_seconds=60, maxsize=512)
BROWSE_CACHE: TTLCache = TTLCache(ttl_seconds=60, maxsize=256)
