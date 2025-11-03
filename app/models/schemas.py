"""Pydantic schemas for request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PullRequestBase(BaseModel):
    """Base pull request schema."""

    pr_number: int
    repo_full_name: str
    status: str = "pending"


class PullRequestCreate(PullRequestBase):
    """Schema for creating a pull request."""

    pass


class PullRequest(PullRequestBase):
    """Pull request schema with ID and timestamps."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewBase(BaseModel):
    """Base review schema."""

    file_path: Optional[str] = None
    line_number: Optional[int] = None
    comment_text: str


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""

    pr_id: int


class Review(ReviewBase):
    """Review schema with ID and timestamp."""

    id: int
    pr_id: int
    posted_at: datetime

    class Config:
        from_attributes = True


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload schema."""

    action: str
    pull_request: dict = Field(..., alias="pull_request")
    repository: dict = Field(..., alias="repository")

    class Config:
        populate_by_name = True

