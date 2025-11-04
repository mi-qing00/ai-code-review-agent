"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.connection import close_db_pool, get_db_pool
from app.db.redis_client import close_redis, get_redis

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting application...")
    await get_db_pool()
    await get_redis()
    logger.info("Application started")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await close_db_pool()
    await close_redis()
    logger.info("Application shut down")


app = FastAPI(
    title="AI Code Review Agent",
    description="Event-driven code review system using GitHub webhooks",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via CORS_ORIGINS env var for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Code Review Agent API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Database and Redis connections are checked during startup
    try:
        pool = await get_db_pool()
        redis = await get_redis()
        # Quick connection test
        await redis.ping()
        return {
            "status": "healthy",
            "postgres": "connected",
            "redis": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# Webhook routes
from app.api import webhooks
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Metrics routes
from app.api import metrics
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# Admin dashboard routes
from app.api import admin
app.include_router(admin.router, prefix="/api", tags=["admin"])

