"""
Redis cache tool — stores and retrieves generated hints so the LLM
is only called once per problem per user session.
"""
import json
import logging
import redis as redis_lib
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCacheTool:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        return self._client

    def _hint_key(self, user_id: str, problem_slug: str) -> str:
        return f"hints:{user_id}:{problem_slug}"

    def get_hints(self, user_id: str, problem_slug: str) -> list[str] | None:
        try:
            raw = self._get_client().get(self._hint_key(user_id, problem_slug))
            if raw:
                logger.info(f"Cache HIT for hints:{user_id}:{problem_slug}")
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        return None

    def set_hints(self, user_id: str, problem_slug: str, hints: list[str]) -> None:
        try:
            self._get_client().setex(
                self._hint_key(user_id, problem_slug),
                settings.HINT_CACHE_TTL,
                json.dumps(hints)
            )
            logger.info(f"Cached {len(hints)} hints for {user_id}:{problem_slug}")
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    def get_solve_count(self, user_id: str) -> int:
        try:
            val = self._get_client().get(f"solves:{user_id}")
            return int(val) if val else 0
        except Exception:
            return 0

    def increment_solve(self, user_id: str) -> None:
        try:
            self._get_client().incr(f"solves:{user_id}")
        except Exception as e:
            logger.warning(f"Redis incr failed: {e}")

    def rate_limit_check(self, user_id: str, window: int = 60, max_requests: int = 10) -> bool:
        """Returns True if allowed, False if rate limited."""
        try:
            key = f"ratelimit:{user_id}"
            pipe = self._get_client().pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            count = results[0]
            return count <= max_requests
        except Exception:
            return True  # Fail open


redis_cache = RedisCacheTool()
