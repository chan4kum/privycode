import time
import logging
from typing import Optional
import redis.asyncio as redis
from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger("rate-limiter")

class TokenBucketRateLimiter:
    """Redis-backed Token Bucket rate limiter to protect GPU workers from request flooding."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis rate limiter unavailable ({e}). Running in fallback pass-through mode.")
                self._redis = None
        return self._redis

    async def check_rate_limit(self, user_id: str, endpoint: str, capacity: int = 60, refill_rate_per_sec: float = 1.0) -> dict:
        """
        Consumes a token from the bucket.
        Returns: { 'allowed': bool, 'remaining': int, 'reset_in_seconds': int }
        """
        r = await self.get_redis()
        if not r:
            # Fallback if Redis is down
            return {"allowed": True, "remaining": capacity, "reset_in_seconds": 0}

        key = f"ratelimit:{user_id}:{endpoint}"
        now = time.time()

        try:
            pipe = r.pipeline()
            pipe.hgetall(key)
            results = await pipe.execute()
            data = results[0]

            if not data:
                tokens = capacity - 1
                last_refill = now
            else:
                last_tokens = float(data.get("tokens", capacity))
                last_refill = float(data.get("last_refill", now))

                # Refill tokens based on elapsed time
                elapsed = max(0.0, now - last_refill)
                tokens = min(capacity, last_tokens + elapsed * refill_rate_per_sec)

                if tokens < 1.0:
                    wait_time = int((1.0 - tokens) / refill_rate_per_sec) + 1
                    return {"allowed": False, "remaining": 0, "reset_in_seconds": wait_time}

                tokens -= 1.0
                last_refill = now

            # Save updated bucket
            pipe = r.pipeline()
            pipe.hset(key, mapping={"tokens": str(tokens), "last_refill": str(last_refill)})
            pipe.expire(key, 3600)  # 1 hour TTL
            await pipe.execute()

            return {"allowed": True, "remaining": int(tokens), "reset_in_seconds": 0}
        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}")
            return {"allowed": True, "remaining": capacity, "reset_in_seconds": 0}

rate_limiter = TokenBucketRateLimiter(settings.redis_url)
