"""Data models for LLM providers."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewComment(BaseModel):
    """A single review comment on a specific line of code."""

    file_path: str = Field(..., description="Path to the file being reviewed")
    line_number: int = Field(..., description="Line number in the file (1-indexed)")
    comment_text: str = Field(..., description="The review comment text")
    severity: str = Field(
        default="medium",
        description="Severity level: critical, high, medium, low",
    )
    code_snippet: Optional[str] = Field(
        default=None,
        description="Optional code snippet showing the issue or suggested fix",
    )
    category: Optional[str] = Field(
        default=None,
        description="Issue category: security, performance, bug, style, etc.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/utils.py",
                "line_number": 42,
                "comment_text": "Consider using context manager for file handling",
                "severity": "warning",
            }
        }


class ReviewResult(BaseModel):
    """Result of LLM code review analysis."""

    comments: List[ReviewComment] = Field(
        default_factory=list,
        description="List of review comments",
    )
    model_used: str = Field(..., description="Identifier of the LLM model used")
    provider: str = Field(..., description="LLM provider name (anthropic, openai, zhipu)")
    tokens_used: int = Field(..., description="Total tokens used (input + output)")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    cost: float = Field(default=0.0, description="Estimated cost in USD")
    processing_time: float = Field(default=0.0, description="Processing time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "comments": [
                    {
                        "file_path": "src/utils.py",
                        "line_number": 42,
                        "comment_text": "Consider using context manager",
                        "severity": "warning",
                    }
                ],
                "model_used": "claude-sonnet-4-5-20250929",
                "provider": "anthropic",
                "tokens_used": 1250,
                "input_tokens": 1000,
                "output_tokens": 250,
                "cost": 0.015,
                "processing_time": 2.3,
            }
        }


class DiffContext(BaseModel):
    """Structured diff data for better prompt context."""

    repo_full_name: str = Field(..., description="Repository full name (owner/repo)")
    pr_number: int = Field(..., description="Pull request number")
    diff_text: str = Field(..., description="Unified diff text")
    changed_files: List[str] = Field(
        default_factory=list,
        description="List of changed file paths",
    )
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    pr_title: Optional[str] = Field(None, description="PR title")
    pr_description: Optional[str] = Field(None, description="PR description")

    class Config:
        json_schema_extra = {
            "example": {
                "repo_full_name": "owner/repo",
                "pr_number": 123,
                "diff_text": "--- a/src/utils.py\n+++ b/src/utils.py\n...",
                "changed_files": ["src/utils.py"],
                "additions": 10,
                "deletions": 5,
                "pr_title": "Add error handling",
                "pr_description": "Improve error handling in utils",
            }
        }

