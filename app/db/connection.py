"""PostgreSQL database connection."""

import asyncio

import asyncpg
from asyncpg import Pool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_pool: Pool | None = None


async def get_db_pool() -> Pool:
    """Get database connection pool with retry logic."""
    global _pool
    if _pool is None:
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to database (attempt {attempt + 1}/{max_retries})...")
                _pool = await asyncpg.create_pool(
                    settings.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                )
                # Test connection
                async with _pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                logger.info("Database connection pool created successfully")
                break
            except Exception as e:
                logger.warning(f"Database connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to database after all retries")
                    raise
    return _pool


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

