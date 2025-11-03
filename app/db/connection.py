"""PostgreSQL database connection."""

import asyncpg
from asyncpg import Pool

from app.core.config import settings

_pool: Pool | None = None


async def get_db_pool() -> Pool:
    """Get database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
    return _pool


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

