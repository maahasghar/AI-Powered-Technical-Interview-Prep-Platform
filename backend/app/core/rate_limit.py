from __future__ import annotations

import hashlib
import time

from fastapi import HTTPException, Request
from redis.exceptions import RedisError


class RedisRateLimiter:
    def __init__(self, client):
        self.client = client

    def check(self, key: str, limit: int, window_seconds: int):
        bucket = int(time.time() // window_seconds)
        redis_key = f"rate:{key}:{bucket}"
        try:
            count = self.client.incr(redis_key)
            if count == 1:
                self.client.expire(redis_key, window_seconds)
        except RedisError:
            return
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )


def client_identity(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    return hashlib.sha256(host.encode()).hexdigest()[:24]
