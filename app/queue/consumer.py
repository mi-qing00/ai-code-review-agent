"""Job consumer - process jobs from Redis Streams."""

import asyncio
import json
import os
import signal
import sys
from datetime import UTC, datetime

# Force unbuffered output for Railway logging
# Set PYTHONUNBUFFERED in environment or use flush() calls
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        # Fallback: ensure unbuffered via environment
        os.environ.setdefault('PYTHONUNBUFFERED', '1')
else:
    # Fallback for older Python versions
    os.environ.setdefault('PYTHONUNBUFFERED', '1')

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

# Health check server (global for cleanup)
_health_runner = None


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
        print(
            f"\n{'='*60}",
            file=sys.stderr
        )
        print(
            f"🔄 Processing job {job_data.job_id} for PR #{job_data.pr_number} "
            f"from {job_data.repo_full_name} (attempt {job_data.attempt_count + 1})",
            file=sys.stderr
        )
        print(f"{'='*60}", file=sys.stderr)
        sys.stderr.flush()
        logger.info(
            f"Processing job {job_data.job_id} for PR #{job_data.pr_number} "
            f"from {job_data.repo_full_name} (attempt {job_data.attempt_count + 1})"
        )
        
        # Update status to processing
        # Convert UTC-aware datetime to naive UTC for TIMESTAMP column
        processing_time = datetime.now(UTC).replace(tzinfo=None)
        await update_job_status(
            job_data.pr_id,
            job_data.job_id,
            "processing",
            processing_started_at=processing_time,
        )
        
        # Initialize GitHub client (use App auth if available, otherwise fallback to PAT)
        from app.core.config import settings

        print("[INIT] Initializing GitHub client...", file=sys.stderr)
        sys.stderr.flush()
        if (
            settings.github_app_id
            and settings.github_app_private_key_path
            and settings.github_app_installation_id
        ):
            print(f"[INIT] Using GitHub App auth (App ID: {settings.github_app_id})", file=sys.stderr)
            sys.stderr.flush()
            github_client = GitHubClient(
                app_id=settings.github_app_id,
                private_key_path=settings.github_app_private_key_path,
                installation_id=settings.github_app_installation_id,
            )
        else:
            print("[INIT] Using Personal Access Token (PAT)", file=sys.stderr)
            sys.stderr.flush()
            logger.warning(
                "GitHub App credentials not configured, using PAT (not recommended)"
            )
            github_client = GitHubClient(token=settings.github_token)
        
        print("[INIT] ✅ GitHub client initialized successfully", file=sys.stderr)
        sys.stderr.flush()
        
        # Step 1: Fetch PR diff from GitHub
        print(f"[STEP 1] Fetching diff for PR #{job_data.pr_number} from {job_data.repo_full_name}", file=sys.stderr)
        sys.stderr.flush()
        logger.info(
            f"[STEP 1] Fetching diff for PR #{job_data.pr_number} from {job_data.repo_full_name}",
            step="fetching_diff",
            pr_number=job_data.pr_number,
            repo=job_data.repo_full_name,
        )
        try:
            diff_context = await github_client.fetch_pr_diff(
                repo_full_name=job_data.repo_full_name,
                pr_number=job_data.pr_number,
            )
            print(
                f"[STEP 1] ✅ Fetched diff: {len(diff_context.changed_files)} files, "
                f"+{diff_context.additions}/-{diff_context.deletions}, "
                f"size: {len(diff_context.diff_text)} chars",
                file=sys.stderr
            )
            sys.stderr.flush()
            logger.info(
                f"[STEP 1] Fetched diff successfully",
                step="fetching_diff",
                files_changed=len(diff_context.changed_files),
                additions=diff_context.additions,
                deletions=diff_context.deletions,
                diff_size=len(diff_context.diff_text),
            )
        except Exception as e:
            print(f"[STEP 1] ❌ Failed to fetch diff: {e}", file=sys.stderr)
            sys.stderr.flush()
            logger.error(
                f"[STEP 1] Failed to fetch diff: {e}",
                step="fetching_diff",
                error=str(e),
                exc_info=True,
            )
            raise
        
        # Step 2: Get LLM provider
        print("[STEP 2] Getting LLM provider", file=sys.stderr)
        sys.stderr.flush()
        logger.info(
            "[STEP 2] Getting LLM provider",
            step="initializing_llm",
        )
        try:
            llm_provider = get_llm_provider()
            print(
                f"[STEP 2] ✅ LLM provider initialized: {llm_provider.provider_name} ({llm_provider.model})",
                file=sys.stderr
            )
            sys.stderr.flush()
            logger.info(
                f"[STEP 2] LLM provider initialized",
                step="initializing_llm",
                provider=llm_provider.provider_name,
                model=llm_provider.model,
            )
        except Exception as e:
            print(f"[STEP 2] ❌ Failed to initialize LLM provider: {e}", file=sys.stderr)
            sys.stderr.flush()
            logger.error(
                f"[STEP 2] Failed to initialize LLM provider: {e}",
                step="initializing_llm",
                error=str(e),
                exc_info=True,
            )
            raise
        
        # Step 3: Analyze diff with LLM
        print(f"[STEP 3] Starting LLM analysis (diff length: {len(diff_context.diff_text)} chars)", file=sys.stderr)
        sys.stderr.flush()
        logger.info(
            "[STEP 3] Starting LLM analysis",
            step="calling_llm",
            diff_length=len(diff_context.diff_text),
        )
        try:
            review_result = await llm_provider.analyze_diff(
                diff_text=diff_context.diff_text,
                context=diff_context,
            )
            print(
                f"[STEP 3] ✅ LLM analysis completed: {len(review_result.comments)} comments, "
                f"{review_result.tokens_used} tokens, ${review_result.cost:.4f}, "
                f"{review_result.processing_time:.2f}s",
                file=sys.stderr
            )
            sys.stderr.flush()
            logger.info(
                f"[STEP 3] LLM analysis completed",
                step="calling_llm",
                comments_count=len(review_result.comments),
                tokens_used=review_result.tokens_used,
                cost=review_result.cost,
                processing_time=review_result.processing_time,
            )
        except Exception as e:
            print(f"[STEP 3] ❌ LLM analysis failed: {e}", file=sys.stderr)
            sys.stderr.flush()
            logger.error(
                f"[STEP 3] LLM analysis failed: {e}",
                step="calling_llm",
                error=str(e),
                exc_info=True,
            )
            raise
        
        # Step 4: Parse comments (if needed)
        print(f"[STEP 4] Parsing review comments: {len(review_result.comments)} comments", file=sys.stderr)
        sys.stderr.flush()
        logger.info(
            "[STEP 4] Parsing review comments",
            step="parsed_comments",
            comments_count=len(review_result.comments),
        )
        
        # Step 5: Post comments to GitHub
        if review_result.comments:
            print(f"[STEP 5] Posting {len(review_result.comments)} review comments to GitHub", file=sys.stderr)
            sys.stderr.flush()
            logger.info(
                f"[STEP 5] Posting {len(review_result.comments)} review comments to GitHub",
                step="posting_comments",
                comments_count=len(review_result.comments),
            )
            try:
                post_result = await github_client.post_review_comments(
                    repo_full_name=job_data.repo_full_name,
                    pr_number=job_data.pr_number,
                    comments=review_result.comments,
                )
                posted_count = post_result.get('posted_count', 0)
                print(
                    f"[STEP 5] ✅ Posted {posted_count}/{len(review_result.comments)} comments to PR #{job_data.pr_number}",
                    file=sys.stderr
                )
                sys.stderr.flush()
                logger.info(
                    f"[STEP 5] Posted comments successfully",
                    step="posting_comments",
                    posted_count=posted_count,
                    total_comments=len(review_result.comments),
                )
            except Exception as e:
                print(f"[STEP 5] ❌ Failed to post comments: {e}", file=sys.stderr)
                sys.stderr.flush()
                logger.error(
                    f"[STEP 5] Failed to post comments: {e}",
                    step="posting_comments",
                    error=str(e),
                    exc_info=True,
                )
                raise
        else:
            print("[STEP 5] No comments to post (LLM found no issues)", file=sys.stderr)
            sys.stderr.flush()
            logger.info(
                "[STEP 5] No comments to post (LLM found no issues)",
                step="posting_comments",
                comments_count=0,
            )
        
        print(
            f"✅ Job {job_data.job_id} completed successfully for PR #{job_data.pr_number}",
            file=sys.stderr
        )
        sys.stderr.flush()
        logger.info(
            f"Job {job_data.job_id} completed successfully for PR #{job_data.pr_number}"
        )
        
        # Update status to completed
        # Convert UTC-aware datetime to naive UTC for TIMESTAMP column
        completed_time = datetime.now(UTC).replace(tzinfo=None)
        await update_job_status(
            job_data.pr_id,
            job_data.job_id,
            "completed",
            completed_at=completed_time,
        )
        
        return True
        
    except Exception as e:
        # Print error to console with full traceback
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"❌ ERROR processing job {job_data.job_id}: {e}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        sys.stderr.flush()
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        
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
            # Convert to timezone-naive UTC datetime for TIMESTAMP column
            if processing_started_at.tzinfo is not None:
                # If timezone-aware, convert to UTC then remove timezone info
                processing_started_at = processing_started_at.astimezone(UTC).replace(tzinfo=None)
            # If already naive, assume it's UTC and use as-is
            update_fields.append(f"processing_started_at = ${param_idx}")
            params.append(processing_started_at)
            param_idx += 1
        
        if completed_at:
            # Convert to timezone-naive UTC datetime for TIMESTAMP column
            if completed_at.tzinfo is not None:
                # If timezone-aware, convert to UTC then remove timezone info
                completed_at = completed_at.astimezone(UTC).replace(tzinfo=None)
            # If already naive, assume it's UTC and use as-is
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
    
    # Immediately signal that worker is ready (for Railway health checks)
    print("✅ Worker initialized and ready", file=sys.stderr)
    print("✅ Worker initialized and ready", file=sys.stdout)
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("🔌 Connecting to Redis...", file=sys.stderr)
    sys.stderr.flush()
    try:
        redis = await get_redis()
        print("✅ Redis connection established", file=sys.stderr)
        print("✅ Redis connection established", file=sys.stdout)
        sys.stdout.flush()
        sys.stderr.flush()
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
    print(f"👷 Consumer {CONSUMER_NAME} started in group {CONSUMER_GROUP}", file=sys.stderr)
    print(f"👷 Consumer {CONSUMER_NAME} started in group {CONSUMER_GROUP}", file=sys.stdout)
    print(f"📋 Waiting for jobs from stream: {STREAM_NAME}", file=sys.stderr)
    print(f"🔄 Blocking for up to {BLOCK_TIME}ms when no messages...", file=sys.stderr)
    print("🚀 Worker is running and ready to process jobs", file=sys.stdout)
    print("=" * 60, file=sys.stdout)
    print("✅ Worker is fully operational", file=sys.stdout)
    sys.stdout.flush()
    sys.stderr.flush()
    
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


async def start_health_server():
    """Start minimal HTTP server for health checks."""
    global _health_runner
    
    # Only start health server if PORT is set (Railway provides this)
    port_str = os.getenv('PORT')
    if not port_str:
        logger.info("PORT not set, skipping health check server")
        print("ℹ️  PORT not set, health check server disabled", file=sys.stderr)
        sys.stderr.flush()
        return None
    
    try:
        from aiohttp import web
        
        port = int(port_str)
        
        async def health_check(request):
            """Simple health check endpoint for Railway"""
            return web.Response(text="OK", status=200)
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)  # Railway might check root too
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        _health_runner = runner
        logger.info("Health check server started", port=port)
        print(f"✅ Health check server started on port {port}", file=sys.stderr)
        sys.stderr.flush()
        return runner
    except ImportError:
        logger.warning("aiohttp not available, health check server disabled")
        print("⚠️  aiohttp not available, health check server disabled", file=sys.stderr)
        sys.stderr.flush()
        return None
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}", exc_info=True)
        print(f"⚠️  Failed to start health check server: {e}", file=sys.stderr)
        sys.stderr.flush()
        return None


async def run_worker() -> None:
    """Run the worker process."""
    global _health_runner
    
    # Early output to ensure Railway sees logs
    print("=" * 60, file=sys.stdout)
    print("🚀 Worker process starting...", file=sys.stdout)
    print("=" * 60, file=sys.stdout)
    sys.stdout.flush()
    
    print("=" * 60, file=sys.stderr)
    print("🔧 run_worker() called", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.stderr.flush()
    
    # Setup signal handlers
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        print("✅ Signal handlers registered", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        print(f"⚠️  Signal handler setup warning: {e}", file=sys.stderr)
        sys.stderr.flush()
    
    # Start health check server if PORT is set
    health_runner = await start_health_server()
    
    logger.info("Starting review worker...")
    print("🚀 Review worker starting...", file=sys.stderr)
    print("🚀 Review worker starting...", file=sys.stdout)
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        print("📞 Calling consume_jobs()...", file=sys.stderr)
        sys.stderr.flush()
        await consume_jobs()
        print("⚠️  consume_jobs() returned (unexpected)", file=sys.stderr)
        sys.stderr.flush()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        print("⚠️  Worker interrupted by user", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        print(f"❌ Worker error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
    finally:
        # Cleanup health server
        if health_runner:
            try:
                print("🛑 Stopping health check server...", file=sys.stderr)
                sys.stderr.flush()
                await health_runner.cleanup()
                logger.info("Health check server stopped")
                print("✅ Health check server stopped", file=sys.stderr)
                sys.stderr.flush()
            except Exception as e:
                logger.warning(f"Error stopping health server: {e}")
                print(f"⚠️  Error stopping health server: {e}", file=sys.stderr)
                sys.stderr.flush()
        
        logger.info("Worker stopped")
        print("🛑 Worker stopped", file=sys.stderr)
        sys.stderr.flush()


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

