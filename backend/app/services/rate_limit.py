from collections import defaultdict, deque
from time import time
from app.core.config import settings

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str, limit: int | None = None, window_seconds: int | None = None) -> bool:
    limit = limit or settings.login_rate_limit
    window_seconds = window_seconds or settings.rate_limit_window_seconds
    now = time()
    bucket = _BUCKETS[key]
    while bucket and bucket[0] < now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def reset_buckets():
    _BUCKETS.clear()
