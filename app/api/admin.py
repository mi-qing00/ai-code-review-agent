"""Admin dashboard and management endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.logging import get_logger
from app.db.connection import get_db_pool
from app.db.redis_client import get_redis
from app.models.schemas import PullRequest

logger = get_logger(__name__)
router = APIRouter()

STREAM_NAME = "review_jobs"
CONSUMER_GROUP = "review_workers"


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """Admin dashboard HTML page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Code Review Agent - Admin Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #333; margin-bottom: 30px; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat-card h3 {
                font-size: 14px;
                color: #666;
                margin-bottom: 10px;
                text-transform: uppercase;
            }
            .stat-card .value {
                font-size: 32px;
                font-weight: bold;
                color: #333;
            }
            .stat-card.queued .value { color: #ff9800; }
            .stat-card.processing .value { color: #2196f3; }
            .stat-card.completed .value { color: #4caf50; }
            .stat-card.failed .value { color: #f44336; }
            .table-container {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow-x: auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            th {
                background: #f8f9fa;
                font-weight: 600;
                color: #333;
            }
            tr:hover { background: #f8f9fa; }
            .status-badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            .status-queued { background: #fff3e0; color: #e65100; }
            .status-processing { background: #e3f2fd; color: #1976d2; }
            .status-completed { background: #e8f5e9; color: #388e3c; }
            .status-failed { background: #ffebee; color: #c62828; }
            .status-dead_letter { background: #f3e5f5; color: #7b1fa2; }
            .btn {
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                margin-right: 5px;
            }
            .btn-retry { background: #2196f3; color: white; }
            .btn-retry:hover { background: #1976d2; }
            .btn-view { background: #4caf50; color: white; }
            .btn-view:hover { background: #45a049; }
            .refresh-btn {
                background: #2196f3;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .refresh-btn:hover { background: #1976d2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Code Review Agent - Admin Dashboard</h1>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            
            <div class="stats-grid" id="stats"></div>
            
            <div class="table-container">
                <h2 style="padding: 20px 20px 10px;">Recent Jobs</h2>
                <table id="jobs-table">
                    <thead>
                        <tr>
                            <th>PR #</th>
                            <th>Repository</th>
                            <th>Status</th>
                            <th>Job ID</th>
                            <th>Enqueued</th>
                            <th>Started</th>
                            <th>Completed</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="jobs-tbody"></tbody>
                </table>
            </div>
        </div>
        
        <script>
            async function loadDashboard() {
                try {
                    // Load stats
                    const statsRes = await fetch('/api/admin/stats');
                    const stats = await statsRes.json();
                    
                    const statsHtml = `
                        <div class="stat-card">
                            <h3>Total PRs</h3>
                            <div class="value">${stats.database.total_prs || 0}</div>
                        </div>
                        <div class="stat-card queued">
                            <h3>Queued</h3>
                            <div class="value">${stats.database.queued || 0}</div>
                        </div>
                        <div class="stat-card processing">
                            <h3>Processing</h3>
                            <div class="value">${stats.database.processing || 0}</div>
                        </div>
                        <div class="stat-card completed">
                            <h3>Completed</h3>
                            <div class="value">${stats.database.completed || 0}</div>
                        </div>
                        <div class="stat-card failed">
                            <h3>Failed</h3>
                            <div class="value">${stats.database.failed || 0}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Queue Length</h3>
                            <div class="value">${stats.queue.stream_length || 0}</div>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;
                    
                    // Load jobs
                    const jobsRes = await fetch('/api/admin/jobs?limit=50');
                    const jobs = await jobsRes.json();
                    
                    const tbody = document.getElementById('jobs-tbody');
                    tbody.innerHTML = jobs.map(job => `
                        <tr>
                            <td>#${job.pr_number}</td>
                            <td>${job.repo_full_name}</td>
                            <td><span class="status-badge status-${job.status}">${job.status}</span></td>
                            <td style="font-size: 11px; font-family: monospace;">${job.job_id || 'N/A'}</td>
                            <td>${job.enqueued_at ? new Date(job.enqueued_at).toLocaleString() : '-'}</td>
                            <td>${job.processing_started_at ? new Date(job.processing_started_at).toLocaleString() : '-'}</td>
                            <td>${job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}</td>
                            <td>
                                ${job.status === 'failed' || job.status === 'dead_letter' ? 
                                    `<button class="btn btn-retry" onclick="retryJob(${job.id})">Retry</button>` : ''}
                                <button class="btn btn-view" onclick="viewJob(${job.id})">View</button>
                            </td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                }
            }
            
            async function retryJob(jobId) {
                if (!confirm('Retry this job?')) return;
                try {
                    const res = await fetch(`/api/admin/jobs/${jobId}/retry`, { method: 'POST' });
                    const result = await res.json();
                    alert(result.message || 'Job retried');
                    loadDashboard();
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            async function viewJob(jobId) {
                try {
                    const res = await fetch(`/api/admin/jobs/${jobId}`);
                    const job = await res.json();
                    alert(JSON.stringify(job, null, 2));
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            // Load on page load
            loadDashboard();
            // Auto-refresh every 10 seconds
            setInterval(loadDashboard, 10000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/admin/stats")
async def get_admin_stats():
    """Get comprehensive admin statistics."""
    try:
        redis = await get_redis()
        pool = await get_db_pool()
        
        # Queue metrics
        queue_length = await redis.xlen(STREAM_NAME)
        
        # Consumer group info
        try:
            group_info = await redis.xinfo_groups(STREAM_NAME)
        except Exception:
            group_info = []
        
        pending_count = 0
        if group_info:
            try:
                pending_info = await redis.xpending(STREAM_NAME, CONSUMER_GROUP)
                if pending_info:
                    pending_count = pending_info.get("pending", 0)
            except Exception:
                pass
        
        # Database statistics
        async with pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_prs,
                    COUNT(*) FILTER (WHERE status = 'queued') as queued,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'dead_letter') as dead_letter,
                    AVG(EXTRACT(EPOCH FROM (completed_at - processing_started_at))) as avg_processing_time,
                    MAX(completed_at) as last_completed_at
                FROM pull_requests
                """
            )
            
            # Recent activity (last hour)
            recent = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as prs_last_hour,
                    COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '1 hour') as completed_last_hour
                FROM pull_requests
                """
            )
        
        return {
            "queue": {
                "stream_length": queue_length,
                "pending_messages": pending_count,
                "consumer_groups": len(group_info),
            },
            "database": {
                "total_prs": stats["total_prs"],
                "queued": stats["queued"],
                "processing": stats["processing"],
                "completed": stats["completed"],
                "failed": stats["failed"],
                "dead_letter": stats["dead_letter"],
                "avg_processing_time_seconds": float(stats["avg_processing_time"] or 0),
                "last_completed_at": stats["last_completed_at"].isoformat() if stats["last_completed_at"] else None,
            },
            "recent_activity": {
                "prs_last_hour": recent["prs_last_hour"],
                "completed_last_hour": recent["completed_last_hour"],
            },
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List jobs with optional filtering."""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            if status:
                jobs = await conn.fetch(
                    """
                    SELECT 
                        id, pr_number, repo_full_name, status, job_id,
                        enqueued_at, processing_started_at, completed_at,
                        attempt_count, created_at, updated_at
                    FROM pull_requests
                    WHERE status = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    status,
                    limit,
                    offset,
                )
            else:
                jobs = await conn.fetch(
                    """
                    SELECT 
                        id, pr_number, repo_full_name, status, job_id,
                        enqueued_at, processing_started_at, completed_at,
                        attempt_count, created_at, updated_at
                    FROM pull_requests
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
            
            return [
                {
                    "id": job["id"],
                    "pr_number": job["pr_number"],
                    "repo_full_name": job["repo_full_name"],
                    "status": job["status"],
                    "job_id": job["job_id"],
                    "enqueued_at": job["enqueued_at"].isoformat() if job["enqueued_at"] else None,
                    "processing_started_at": job["processing_started_at"].isoformat() if job["processing_started_at"] else None,
                    "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
                    "attempt_count": job["attempt_count"],
                    "created_at": job["created_at"].isoformat(),
                    "updated_at": job["updated_at"].isoformat(),
                }
                for job in jobs
            ]
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/jobs/{job_id}")
async def get_job(job_id: int):
    """Get detailed information about a specific job."""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            job = await conn.fetchrow(
                """
                SELECT 
                    id, pr_number, repo_full_name, status, job_id,
                    enqueued_at, processing_started_at, completed_at,
                    attempt_count, created_at, updated_at
                FROM pull_requests
                WHERE id = $1
                """,
                job_id,
            )
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Get reviews for this PR
            reviews = await conn.fetch(
                """
                SELECT id, file_path, line_number, comment_text, posted_at
                FROM reviews
                WHERE pr_id = $1
                ORDER BY posted_at DESC
                """,
                job_id,
            )
            
            return {
                "id": job["id"],
                "pr_number": job["pr_number"],
                "repo_full_name": job["repo_full_name"],
                "status": job["status"],
                "job_id": job["job_id"],
                "enqueued_at": job["enqueued_at"].isoformat() if job["enqueued_at"] else None,
                "processing_started_at": job["processing_started_at"].isoformat() if job["processing_started_at"] else None,
                "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
                "attempt_count": job["attempt_count"],
                "created_at": job["created_at"].isoformat(),
                "updated_at": job["updated_at"].isoformat(),
                "reviews": [
                    {
                        "id": r["id"],
                        "file_path": r["file_path"],
                        "line_number": r["line_number"],
                        "comment_text": r["comment_text"],
                        "posted_at": r["posted_at"].isoformat(),
                    }
                    for r in reviews
                ],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/jobs/{job_id}/retry")
async def retry_job(job_id: int):
    """Retry a failed or dead letter job."""
    try:
        from app.queue.producer import enqueue_review_job
        
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get job details
            job = await conn.fetchrow(
                """
                SELECT id, pr_number, repo_full_name, status, job_id
                FROM pull_requests
                WHERE id = $1
                """,
                job_id,
            )
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            if job["status"] not in ["failed", "dead_letter"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot retry job with status: {job['status']}"
                )
            
            # Re-enqueue the job
            new_job_id = await enqueue_review_job(
                pr_id=job["id"],
                pr_number=job["pr_number"],
                repo_full_name=job["repo_full_name"],
                metadata={"retry_from": job["job_id"]},
            )
            
            # Update status
            await conn.execute(
                """
                UPDATE pull_requests
                SET status = 'queued', job_id = $1, enqueued_at = NOW(), attempt_count = attempt_count + 1
                WHERE id = $2
                """,
                new_job_id,
                job_id,
            )
            
            logger.info(f"Retried job {job_id} with new job_id {new_job_id}")
            
            return {
                "message": "Job retried successfully",
                "job_id": job_id,
                "new_job_id": new_job_id,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/failed-jobs")
async def get_failed_jobs(limit: int = Query(50, ge=1, le=1000)):
    """Get list of failed and dead letter jobs."""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            jobs = await conn.fetch(
                """
                SELECT 
                    id, pr_number, repo_full_name, status, job_id,
                    enqueued_at, processing_started_at, completed_at,
                    attempt_count, created_at, updated_at
                FROM pull_requests
                WHERE status IN ('failed', 'dead_letter')
                ORDER BY updated_at DESC
                LIMIT $1
                """,
                limit,
            )
            
            return [
                {
                    "id": job["id"],
                    "pr_number": job["pr_number"],
                    "repo_full_name": job["repo_full_name"],
                    "status": job["status"],
                    "job_id": job["job_id"],
                    "attempt_count": job["attempt_count"],
                    "updated_at": job["updated_at"].isoformat(),
                }
                for job in jobs
            ]
    except Exception as e:
        logger.error(f"Error getting failed jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/jobs/{job_id}")
async def delete_job(job_id: int):
    """Delete a job (use with caution)."""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM pull_requests WHERE id = $1",
                job_id,
            )
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Job not found")
            
            logger.warning(f"Job {job_id} deleted by admin")
            
            return {"message": "Job deleted successfully", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

