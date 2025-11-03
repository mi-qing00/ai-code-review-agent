"""Redis client connection."""

import asyncio

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None
_pool: ConnectionPool | None = None


async def get_redis() -> Redis:
    """Get Redis client with retry logic."""
    global _redis, _pool
    if _redis is None:
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Redis (attempt {attempt + 1}/{max_retries})...")
                _pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)
                _redis = Redis(connection_pool=_pool)
                # Test connection
                await _redis.ping()
                logger.info("Redis connection established successfully")
                break
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Redis after all retries")
                    raise
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

