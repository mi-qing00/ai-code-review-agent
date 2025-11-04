"""Job consumer - process jobs from Redis Streams."""

import asyncio
import json
import signal
import sys
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.db.connection import get_db_pool
from app.db.redis_client import get_redis
from app.models.job import JobData

logger = get_logger(__name__)

STREAM_NAME = "review_jobs"
CONSUMER_GROUP = "review_workers"
CONSUMER_NAME = "worker-1"  # Can be made configurable
BLOCK_TIME = 5000  # 5 seconds in milliseconds
MAX_RETRIES = 3

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def process_job(job_data: JobData) -> bool:
    """
    Process a single review job.
    
    This function:
    1. Fetches PR diff from GitHub
    2. Analyzes diff with LLM
    3. Posts review comments to GitHub
    4. Updates job status
    
    Args:
        job_data: Job data from queue
        
    Returns:
        True if successful, False if failed
    """
    from app.github.client import GitHubClient
    from app.llm.factory import get_llm_provider

    github_client = None
    try:
        logger.info(
            f"Processing job {job_data.job_id} for PR #{job_data.pr_number} "
            f"from {job_data.repo_full_name} (attempt {job_data.attempt_count + 1})"
        )
        
        # Update status to processing
        await update_job_status(
            job_data.pr_id,
            job_data.job_id,
            "processing",
            processing_started_at=datetime.now(UTC),
        )
        
        # Initialize GitHub client (use App auth if available, otherwise fallback to PAT)
        from app.core.config import settings

        if (
            settings.github_app_id
            and settings.github_app_private_key_path
            and settings.github_app_installation_id
        ):
            github_client = GitHubClient(
                app_id=settings.github_app_id,
                private_key_path=settings.github_app_private_key_path,
                installation_id=settings.github_app_installation_id,
            )
        else:
            logger.warning(
                "GitHub App credentials not configured, using PAT (not recommended)"
            )
            github_client = GitHubClient(token=settings.github_token)
        
        # Step 1: Fetch PR diff from GitHub
        logger.info(f"Fetching diff for PR #{job_data.pr_number} from {job_data.repo_full_name}")
        diff_context = await github_client.fetch_pr_diff(
            repo_full_name=job_data.repo_full_name,
            pr_number=job_data.pr_number,
        )
        logger.info(
            f"Fetched diff: {len(diff_context.changed_files)} files changed, "
            f"{diff_context.additions} additions, {diff_context.deletions} deletions"
        )
        
        # Step 2: Get LLM provider
        llm_provider = get_llm_provider()
        logger.info(f"Using LLM provider: {llm_provider.provider_name} ({llm_provider.model})")
        
        # Step 3: Analyze diff with LLM
        logger.info("Analyzing diff with LLM...")
        review_result = await llm_provider.analyze_diff(
            diff_text=diff_context.diff_text,
            context=diff_context,
        )
        logger.info(
            f"LLM analysis completed: {len(review_result.comments)} comments, "
            f"{review_result.tokens_used} tokens, ${review_result.cost:.4f} cost, "
            f"{review_result.processing_time:.2f}s"
        )
        
        # Step 4: Post comments to GitHub
        if review_result.comments:
            logger.info(f"Posting {len(review_result.comments)} review comments to GitHub...")
            post_result = await github_client.post_review_comments(
                repo_full_name=job_data.repo_full_name,
                pr_number=job_data.pr_number,
                comments=review_result.comments,
            )
            logger.info(
                f"Posted {post_result.get('posted_count', 0)} comments to PR #{job_data.pr_number}"
            )
        else:
            logger.info("No comments to post (LLM found no issues)")
        
        logger.info(
            f"Job {job_data.job_id} completed successfully for PR #{job_data.pr_number}"
        )
        
        # Update status to completed
        await update_job_status(
            job_data.pr_id,
            job_data.job_id,
            "completed",
            completed_at=datetime.now(UTC),
        )
        
        return True
        
    except Exception as e:
        logger.error(
            f"Error processing job {job_data.job_id}: {e}",
            exc_info=True,
        )
        
        # Update status to failed
        await update_job_status(
            job_data.pr_id,
            job_data.job_id,
            "failed",
            error_message=str(e),
        )
        
        return False
        
    finally:
        # Clean up GitHub client
        if github_client:
            try:
                await github_client.close()
            except Exception as e:
                logger.warning(f"Error closing GitHub client: {e}")


async def update_job_status(
    pr_id: int,
    job_id: str,
    status: str,
    processing_started_at: datetime | None = None,
    completed_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    """Update job status in database."""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Build dynamic UPDATE query
        update_fields = ["status = $1", "updated_at = NOW()"]
        params = [status]
        param_idx = 2
        
        if processing_started_at:
            update_fields.append(f"processing_started_at = ${param_idx}")
            params.append(processing_started_at)
            param_idx += 1
        
        if completed_at:
            update_fields.append(f"completed_at = ${param_idx}")
            params.append(completed_at)
            param_idx += 1
        
        # Add WHERE clause parameters
        params.append(pr_id)
        params.append(job_id)
        
        query = f"""
            UPDATE pull_requests
            SET {', '.join(update_fields)}
            WHERE id = ${param_idx} AND job_id = ${param_idx + 1}
        """
        
        await conn.execute(query, *params)


async def consume_jobs() -> None:
    """Main consumer loop - reads jobs from Redis Streams and processes them."""
    global shutdown_requested
    
    print("=" * 60, file=sys.stderr)
    print("📥 consume_jobs() called", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    print("🔌 Connecting to Redis...", file=sys.stderr)
    try:
        redis = await get_redis()
        print("✅ Redis connection established", file=sys.stderr)
    except Exception as e:
        print(f"❌ Redis connection failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise
    
    # Create consumer group if it doesn't exist
    try:
        await redis.xgroup_create(
            STREAM_NAME,
            CONSUMER_GROUP,
            id="0",  # Start from beginning
            mkstream=True,  # Create stream if it doesn't exist
        )
        logger.info(f"Created consumer group {CONSUMER_GROUP}")
    except Exception as e:
        # Group might already exist, that's okay
        if "BUSYGROUP" not in str(e):
            logger.warning(f"Error creating consumer group: {e}")
    
    logger.info(f"Starting consumer {CONSUMER_NAME} in group {CONSUMER_GROUP}")
    print(f"👷 Consumer {CONSUMER_NAME} started in group {CONSUMER_GROUP}")
    print(f"📋 Waiting for jobs from stream: {STREAM_NAME}")
    print(f"🔄 Blocking for up to {BLOCK_TIME}ms when no messages...")
    
    current_job = None
    
    try:
        while not shutdown_requested:
            try:
                # Read messages from stream using XREADGROUP
                # Use ">" to read new messages, or "0" to read from beginning
                # We prefer ">" for new messages, but also handle existing ones
                messages = await redis.xreadgroup(
                    CONSUMER_GROUP,
                    CONSUMER_NAME,
                    {STREAM_NAME: ">"},  # Read new messages (not yet delivered to any consumer)
                    count=1,
                    block=BLOCK_TIME,
                )
                
                # If no new messages, check for pending messages for this consumer
                if not messages:
                    try:
                        pending = await redis.xpending_range(
                            STREAM_NAME,
                            CONSUMER_GROUP,
                            min="-",
                            max="+",
                            count=10,
                            consumername=CONSUMER_NAME,
                        )
                        if pending:
                            logger.info(f"Found {len(pending)} pending messages, claiming them...")
                            # Claim pending messages
                            pending_ids = [msg["message_id"] for msg in pending]
                            claimed = await redis.xclaim(
                                STREAM_NAME,
                                CONSUMER_GROUP,
                                CONSUMER_NAME,
                                min_idle_time=0,
                                message_ids=pending_ids,
                            )
                            if claimed:
                                # Convert claimed messages to same format as xreadgroup
                                messages = [(STREAM_NAME, claimed)]
                    except Exception as e:
                        logger.debug(f"No pending messages or error checking pending: {e}")
                
                if not messages:
                    # No messages, continue waiting
                    # This is normal - we're blocking, so we'll wait for new messages
                    continue
                
                # Process each message
                for stream, msg_list in messages:
                    for msg_id, data in msg_list:
                        try:
                            # Parse job data
                            job_json = data.get("job_data", "{}")
                            job_dict = json.loads(job_json)
                            job_data = JobData(**job_dict)
                            
                            current_job = job_data
                            
                            # Process the job
                            success = await process_job(job_data)
                            
                            if success:
                                # Acknowledge the message
                                await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                                logger.debug(f"Acknowledged message {msg_id}")
                            else:
                                # Check retry count
                                if job_data.attempt_count < MAX_RETRIES:
                                    # Re-enqueue with incremented attempt count
                                    job_data.attempt_count += 1
                                    job_data.status = "queued"
                                    
                                    # Add back to stream
                                    await redis.xadd(
                                        STREAM_NAME,
                                        {
                                            "job_data": json.dumps(job_data.model_dump()),
                                            "pr_id": str(job_data.pr_id),
                                            "pr_number": str(job_data.pr_number),
                                            "repo": job_data.repo_full_name,
                                        },
                                    )
                                    
                                    # Acknowledge original message
                                    await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                                    
                                    logger.info(
                                        f"Re-enqueued job {job_data.job_id} "
                                        f"(attempt {job_data.attempt_count})"
                                    )
                                else:
                                    # Max retries reached, move to dead letter
                                    await move_to_dead_letter(job_data)
                                    await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                                    
                                    logger.error(
                                        f"Job {job_data.job_id} failed after "
                                        f"{MAX_RETRIES} attempts, moved to dead letter"
                                    )
                            
                            current_job = None
                            
                        except Exception as e:
                            logger.error(
                                f"Error processing message {msg_id}: {e}",
                                exc_info=True,
                            )
                            # Acknowledge to avoid reprocessing broken messages
                            try:
                                await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                            except Exception:
                                pass
                            
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                print("⚠️  Consumer loop cancelled", file=sys.stderr)
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                print(f"❌ Error in consumer loop: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)  # Brief pause before retrying
    
    finally:
        # Wait for current job to finish if shutting down
        if current_job:
            logger.info(f"Waiting for current job {current_job.job_id} to finish...")
            # Give it some time, but don't wait forever
            await asyncio.sleep(10)
        
        logger.info("Consumer stopped")


async def move_to_dead_letter(job_data: JobData) -> None:
    """Move failed job to dead letter queue."""
    redis = await get_redis()
    
    dead_letter_stream = f"{STREAM_NAME}:dead_letter"
    
    await redis.xadd(
        dead_letter_stream,
        {
            "job_data": json.dumps(job_data.model_dump()),
            "pr_id": str(job_data.pr_id),
            "pr_number": str(job_data.pr_number),
            "repo": job_data.repo_full_name,
            "failed_at": datetime.now(UTC).isoformat(),
        },
    )
    
    # Update database status
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE pull_requests
            SET status = 'dead_letter', updated_at = NOW()
            WHERE id = $1 AND job_id = $2
            """,
            job_data.pr_id,
            job_data.job_id,
        )


async def run_worker() -> None:
    """Run the worker process."""
    print("=" * 60, file=sys.stderr)
    print("🔧 run_worker() called", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Setup signal handlers
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        print("✅ Signal handlers registered", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Signal handler setup warning: {e}", file=sys.stderr)
    
    logger.info("Starting review worker...")
    print("🚀 Review worker starting...", file=sys.stderr)
    print("🚀 Review worker starting...", file=sys.stdout)
    
    try:
        print("📞 Calling consume_jobs()...", file=sys.stderr)
        await consume_jobs()
        print("⚠️  consume_jobs() returned (unexpected)", file=sys.stderr)
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        print("⚠️  Worker interrupted by user", file=sys.stderr)
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        print(f"❌ Worker error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Worker stopped")
        print("🛑 Worker stopped", file=sys.stderr)


# Worker can be run as:
# python -m app.queue.consumer
# or
# ./scripts/start-worker.sh

if __name__ == "__main__":
    # This allows running: python -m app.queue.consumer
    # or directly: python app/queue/consumer.py
    import asyncio
    from app.core.logging import setup_logging
    
    setup_logging()
    print("🚀 Starting worker from consumer.py...", file=sys.stderr)
    
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n⚠️  Worker stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"❌ Worker error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

