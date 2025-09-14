import time
import os
import redis
from fastapi import Request, Response


class SimpleRateLimiter:
    def __init__(self, redis_url: str | None = None, window_sec: int = 60, max_requests: int = 30):
        self.redis = redis.from_url(redis_url or os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
        self.window = window_sec
        self.max_requests = max_requests

    def allow(self, key: str) -> bool:
        now = int(time.time())
        window_key = f"rl:{key}:{now // self.window}"
        pipe = self.redis.pipeline()
        pipe.incr(window_key, 1)
        pipe.expire(window_key, self.window)
        count, _ = pipe.execute()
        return int(count) <= self.max_requests


