"""
Async Redis client for Upstash.
Provides graceful fallback — if Redis is unavailable, the app still works
(just without caching, hitting the LLM every time).
"""

import logging
import redis.asyncio as aioredis

from app.core.config import settings

_log = logging.getLogger(__name__)
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a connected Redis client, or None if unavailable."""
    global _redis_client

    if not settings.redis_url:
        return None

    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    try:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _redis_client.ping()
        _log.info("Redis connected: %s", settings.redis_url[:30] + "...")
        return _redis_client
    except Exception as exc:
        _log.warning("Redis unavailable, running without cache: %s", exc)
        _redis_client = None
        return None


async def cache_get(key: str) -> dict | list | None:
    """Safely get and deserialize JSON from Redis."""
    try:
        redis = await get_redis()
        if not redis:
            return None
        
        data = await redis.get(key)
        if data:
            import json
            return json.loads(data)
    except Exception as exc:
        _log.warning("Cache GET failed for %s: %s", key, exc)
    return None


async def cache_set(key: str, data: dict | list, expire_seconds: int = 300) -> bool:
    """Safely serialize and save JSON to Redis with an expiration."""
    try:
        redis = await get_redis()
        if not redis:
            return False
            
        import json
        await redis.set(key, json.dumps(data), ex=expire_seconds)
        return True
    except Exception as exc:
        _log.warning("Cache SET failed for %s: %s", key, exc)
        return False
