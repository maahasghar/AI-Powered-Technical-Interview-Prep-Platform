import json

import pytest
from fastapi import HTTPException

from app.audit import _safe_metadata
from app.core.rate_limit import RedisRateLimiter
from app.infrastructure.worker_health import heartbeat


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expiries = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.expiries[key] = seconds

    def set(self, key, value, ex=None):
        self.values[key] = value
        if ex is not None:
            self.expiries[key] = ex


def test_rate_limiter_allows_limit_then_returns_429():
    limiter = RedisRateLimiter(FakeRedis())
    limiter.check("user:1", 2, 60)
    limiter.check("user:1", 2, 60)
    with pytest.raises(HTTPException) as error:
        limiter.check("user:1", 2, 60)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"


def test_rate_limiter_scopes_users_independently():
    limiter = RedisRateLimiter(FakeRedis())
    limiter.check("user:1", 1, 60)
    limiter.check("user:2", 1, 60)


def test_audit_metadata_drops_sensitive_values():
    safe = _safe_metadata({"password": "secret", "code": "source", "screen": "login"})
    assert safe == {"screen": "login"}
    assert "secret" not in json.dumps(safe)


def test_worker_heartbeat_sets_a_ttl_key():
    redis = FakeRedis()

    assert heartbeat(redis, "judge") is True
    assert redis.values[next(iter(redis.values))] == "1"
    assert redis.expiries[next(iter(redis.expiries))] == 30