import redis
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get(self, key: str):
        return self.client.get(key)

    def set(self, key: str, value: str, ex: int = None):
        self.client.set(key, value, ex=ex)

    def delete(self, key: str):
        self.client.delete(key)

    def exists(self, key: str):
        return self.client.exists(key)

    def close(self):
        self.client.close()
