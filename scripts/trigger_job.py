#!/usr/bin/env python3
"""Manual job trigger script - manually enqueue a PR review job."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging import setup_logging
from app.db.connection import close_db_pool, get_db_pool
from app.db.redis_client import close_redis, get_redis
from app.queue.producer import enqueue_review_job
from app.services.webhook_service import WebhookService

setup_logging()


async def trigger_job(repo_full_name: str, pr_number: int):
    """Manually trigger a review job for a PR."""
    print(f"\n{'='*60}")
    print(f"🚀 Manual Job Trigger: {repo_full_name} PR #{pr_number}")
    print(f"{'='*60}\n")

    try:
        # Step 1: Initialize connections
        print("Step 1: Connecting to database and Redis...")
        pool = await get_db_pool()
        redis = await get_redis()
        await redis.ping()
        print("  ✅ Connected to database and Redis")

        # Step 2: Store or get PR metadata
        print(f"\nStep 2: Creating/updating PR record in database...")
        pr_id = await WebhookService._store_pr_metadata(
            pr_number=pr_number,
            repo_full_name=repo_full_name,
        )
        print(f"  ✅ PR record: ID={pr_id}, Number={pr_number}, Repo={repo_full_name}")

        # Step 3: Enqueue job
        print(f"\nStep 3: Enqueueing review job to Redis Streams...")
        job_id = await enqueue_review_job(
            pr_id=pr_id,
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            metadata={
                "manual_trigger": True,
                "triggered_by": "manual_script",
            },
        )
        print(f"  ✅ Job enqueued: {job_id}")

        # Step 4: Update PR with job_id
        print(f"\nStep 4: Updating PR record with job_id...")
        await WebhookService._update_pr_with_job(pr_id, job_id)
        print(f"  ✅ PR record updated")

        print(f"\n{'='*60}")
        print(f"✅ Job successfully enqueued!")
        print(f"{'='*60}\n")
        print(f"📋 Summary:")
        print(f"   - PR ID: {pr_id}")
        print(f"   - PR Number: {pr_number}")
        print(f"   - Repository: {repo_full_name}")
        print(f"   - Job ID: {job_id}")
        print(f"\n⏳ Worker will process this job automatically.")
        print(f"   Check worker logs to see processing status.\n")

        return True

    except Exception as e:
        print(f"\n❌ Failed to trigger job: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await close_db_pool()
        await close_redis()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/trigger_job.py <repo_full_name> <pr_number>")
        print("Example: python scripts/trigger_job.py kaitlynmi/pr-review-demo 1")
        print("\nThis script will:")
        print("  1. Create/update PR record in database")
        print("  2. Enqueue review job to Redis Streams")
        print("  3. Worker will automatically process the job")
        sys.exit(1)

    repo_full_name = sys.argv[1]
    try:
        pr_number = int(sys.argv[2])
    except ValueError:
        print(f"❌ Invalid PR number: {sys.argv[2]}")
        sys.exit(1)

    success = asyncio.run(trigger_job(repo_full_name, pr_number))
    sys.exit(0 if success else 1)

