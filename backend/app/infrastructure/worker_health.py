from __future__ import annotations

from redis.exceptions import RedisError


def heartbeat(client, worker_name: str, ttl_seconds: int = 30) -> bool:
    try:
        client.set(f"health:worker:{worker_name}", "1", ex=ttl_seconds)
        return True
    except RedisError:
        return False