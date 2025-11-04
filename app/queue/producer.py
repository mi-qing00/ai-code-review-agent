"""Job producer - enqueue jobs to Redis Streams."""

import json
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.db.redis_client import get_redis
from app.models.job import JobData

logger = get_logger(__name__)

STREAM_NAME = "review_jobs"
MAX_STREAM_LENGTH = 10000  # Prevent unbounded growth


async def enqueue_review_job(
    pr_id: int,
    pr_number: int,
    repo_full_name: str,
    metadata: dict | None = None,
) -> str:
    """
    Enqueue a PR review job to Redis Streams.
    
    Args:
        pr_id: Database ID of the pull request
        pr_number: GitHub PR number
        repo_full_name: Repository full name (owner/repo)
        metadata: Optional metadata dictionary
        
    Returns:
        Job ID (UUID string)
        
    Raises:
        Exception: If Redis connection fails or enqueue fails
    """
    try:
        redis = await get_redis()
        
        # Create job data
        job_data = JobData(
            pr_id=pr_id,
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            metadata=metadata or {},
        )
        
        # Add metadata
        if "webhook_received_at" not in job_data.metadata:
            job_data.metadata["webhook_received_at"] = datetime.now(UTC).isoformat()
        
        # Serialize job data to JSON
        job_dict = job_data.model_dump()
        job_dict["enqueued_at"] = datetime.now(UTC).isoformat()
        
        # Add to Redis Stream using XADD
        # MAXLEN to prevent unbounded growth
        message_id = await redis.xadd(
            STREAM_NAME,
            {
                "job_data": json.dumps(job_dict),
                "pr_id": str(pr_id),
                "pr_number": str(pr_number),
                "repo": repo_full_name,
            },
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,  # Approximate trimming for better performance
        )
        
        logger.info(
            f"Enqueued job {job_data.job_id} for PR #{pr_number} "
            f"from {repo_full_name} (message_id: {message_id})"
        )
        
        return job_data.job_id
        
    except Exception as e:
        logger.error(
            f"Failed to enqueue job for PR #{pr_number} from {repo_full_name}: {e}",
            exc_info=True,
        )
        raise

