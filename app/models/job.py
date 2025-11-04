"""Job data models for queue system."""

import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobData(BaseModel):
    """Job data structure stored in Redis Stream."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pr_id: int
    pr_number: int
    repo_full_name: str
    enqueued_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    attempt_count: int = 0
    status: str = "queued"
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "pr_id": 1,
                "pr_number": 123,
                "repo_full_name": "owner/repo",
                "enqueued_at": "2025-11-03T23:00:00Z",
                "attempt_count": 0,
                "status": "queued",
                "metadata": {
                    "webhook_received_at": "2025-11-03T23:00:00Z"
                }
            }
        }


class JobStatus(BaseModel):
    """Job status for tracking."""

    job_id: str
    pr_id: int
    status: str  # pending, queued, processing, completed, failed, dead_letter
    attempt_count: int
    enqueued_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

