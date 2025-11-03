"""Redis client connection."""

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

_redis: Redis | None = None
_pool: ConnectionPool | None = None


async def get_redis() -> Redis:
    """Get Redis client."""
    global _redis, _pool
    if _redis is None:
        _pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)
        _redis = Redis(connection_pool=_pool)
    return _redis


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis, _pool
    if _redis:
        await _redis.close()
        _redis = None
    if _pool:
        await _pool.disconnect()
        _pool = None

