"""TTL disk cache backed by JSON files.

Each cache entry is stored as a JSON file keyed by an MD5 hash of the
request arguments.  Entries older than TTL seconds are considered stale.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import config


class DiskCache:
    """Simple key-value TTL cache persisted to JSON files."""

    def __init__(self, cache_dir: Path = config.CACHE_DIR, ttl: int = config.CACHE_TTL):
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl

    # ── Public API ─────────────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if missing/stale."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            if time.time() - payload["ts"] > self._ttl:
                path.unlink(missing_ok=True)
                return None
            return payload["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, value: Any) -> None:
        """Persist value to disk under *key*."""
        path = self._path(key)
        try:
            path.write_text(json.dumps({"ts": time.time(), "data": value}))
        except (OSError, TypeError):
            pass  # cache write failures are non-fatal

    def clear(self) -> None:
        """Delete all cache files."""
        for p in self._dir.glob("*.json"):
            p.unlink(missing_ok=True)

    # ── Internals ──────────────────────────────────────────────────────────────────

    def _path(self, key: str) -> Path:
        digest = hashlib.md5(key.encode()).hexdigest()
        return self._dir / f"{digest}.json"


# Module-level singleton so all callers share one cache dir
_cache = DiskCache()


def get(key: str) -> Optional[Any]:
    return _cache.get(key)


def set(key: str, value: Any) -> None:  # noqa: A001
    _cache.set(key, value)


def clear() -> None:
    _cache.clear()
