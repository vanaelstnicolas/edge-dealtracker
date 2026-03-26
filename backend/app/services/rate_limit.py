from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
import time

from fastapi import HTTPException, status


@dataclass(frozen=True)
class RateLimitState:
    limit: int
    remaining: int
    retry_after_seconds: int


_LOCK = Lock()
_HITS: dict[str, deque[float]] = defaultdict(deque)


def _bucket_key(bucket: str, key: str) -> str:
    return f"{bucket}:{key}"


def _check_rate_limit(*, bucket: str, key: str, limit: int, window_seconds: int) -> RateLimitState:
    if limit <= 0 or window_seconds <= 0:
        return RateLimitState(limit=limit, remaining=max(0, limit), retry_after_seconds=0)

    now = time.time()
    window_start = now - window_seconds
    storage_key = _bucket_key(bucket, key)

    with _LOCK:
        hits = _HITS[storage_key]
        while hits and hits[0] <= window_start:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(hits[0] + window_seconds - now))
            return RateLimitState(limit=limit, remaining=0, retry_after_seconds=retry_after)

        hits.append(now)
        remaining = max(0, limit - len(hits))
        return RateLimitState(limit=limit, remaining=remaining, retry_after_seconds=0)


def enforce_rate_limit(*, bucket: str, key: str, limit: int, window_seconds: int) -> None:
    state = _check_rate_limit(bucket=bucket, key=key, limit=limit, window_seconds=window_seconds)
    if state.retry_after_seconds > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {state.retry_after_seconds}s",
        )


def reset_rate_limits() -> None:
    with _LOCK:
        _HITS.clear()
