import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float   # Unix timestamp


class BriefCache:
    """
    In-memory TTL cache keyed by company domain.

    Why in-memory (not Redis/Postgres):
    - Zero dependencies for a demo project
    - Research briefs are valid for hours, not days
    - Cache resets on restart, which is acceptable

    TTL default is 4 hours — enough to cover a workday's meetings
    without serving stale news.
    """

    def __init__(self, ttl_seconds: int = 4 * 3600):
        self._store: dict[str, _CacheEntry] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            # Expired — remove and return None (lazy eviction)
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.time() + ttl,
        )

    def delete(self, key: str) -> None:
        """Explicit invalidation — used by POST /meetings/{id}/refresh."""
        self._store.pop(key, None)

    def size(self) -> int:
        return len(self._store)


# Module-level singleton — one cache shared across all requests
brief_cache = BriefCache()
