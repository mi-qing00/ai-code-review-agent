"""Database migration utilities."""

from pathlib import Path

from asyncpg import Pool

from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_migrations(pool: Pool) -> None:
    """Run database migrations in order."""
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    
    # Get all migration files sorted by name
    migration_files = sorted(
        [f for f in migrations_dir.glob("*.sql")],
        key=lambda x: x.name
    )
    
    if not migration_files:
        logger.warning("No migration files found")
        return
    
    logger.info(f"Found {len(migration_files)} migration file(s)")
    
    async with pool.acquire() as conn:
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            try:
                sql = migration_file.read_text()
                # Execute migration within a transaction
                async with conn.transaction():
                    await conn.execute(sql)
                logger.info(f"✅ Migration {migration_file.name} completed successfully")
            except Exception as e:
                logger.error(f"❌ Migration {migration_file.name} failed: {e}")
                raise


async def check_migration_status(pool: Pool) -> bool:
    """Check if migrations have been run by checking if pull_requests table exists."""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pull_requests'
                );
            """)
            return result is True
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False

