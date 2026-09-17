import logging

from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
QUEUE_KEY = "judge:submissions"


class SubmissionQueue:
    def __init__(self, client, key=None):
        self.client = client
        self.key = key or QUEUE_KEY

    def enqueue(self, submission_id: int) -> bool:
        try:
            # A sorted set deduplicates redispatch, and BZPOPMIN hands out oldest IDs.
            self.client.zadd(self.key, {str(submission_id): submission_id})
            return True
        except RedisError:
            logger.warning(
                "Redis enqueue failed; submission %s awaits reconciliation",
                submission_id,
            )
            return False

    def take(self):
        item = self.client.bzpopmin(self.key, timeout=2)
        return int(item[1]) if item else None
