"""GitHub API client using App authentication."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import List, Optional

import httpx
import jwt

from app.core.logging import get_logger
from app.llm.models import DiffContext, ReviewComment

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
MAX_DIFF_SIZE = 1_000_000  # 1MB max diff size


class GitHubClient:
    """Client for interacting with GitHub API using App authentication."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        private_key_path: Optional[str] = None,
        installation_id: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        Initialize GitHub client.

        Args:
            app_id: GitHub App ID (if None, will try to load from settings)
            private_key_path: Path to GitHub App private key file (if None, will try to load from settings)
            installation_id: GitHub App installation ID (if None, will try to load from settings)
            token: Personal access token (fallback, not recommended)
        """
        from app.core.config import settings

        # Use provided values or fall back to settings
        app_id = app_id or settings.github_app_id
        private_key_path = private_key_path or settings.github_app_private_key_path
        installation_id = installation_id or settings.github_app_installation_id

        # Use App authentication if all App credentials are available
        if app_id and private_key_path and installation_id:
            self.app_id = app_id
            self.installation_id = installation_id
            self.private_key_path = Path(private_key_path)

            # Resolve relative paths relative to project root
            if not self.private_key_path.is_absolute():
                project_root = Path(__file__).parent.parent.parent
                self.private_key_path = project_root / self.private_key_path

            # Read private key
            if not self.private_key_path.exists():
                raise FileNotFoundError(
                    f"GitHub App private key not found: {self.private_key_path}. "
                    f"Check GITHUB_APP_PRIVATE_KEY_PATH setting."
                )

            with open(self.private_key_path, "r") as f:
                self.private_key = f.read()

            self._installation_token: Optional[str] = None
            self._token_expires_at: Optional[datetime] = None
            self.use_app_auth = True
            logger.info(
                "Using GitHub App authentication",
                app_id=self.app_id,
                installation_id=self.installation_id,
            )
        else:
            # Fallback to PAT (for backward compatibility)
            self.token = token or settings.github_token
            self.use_app_auth = False
            missing = []
            if not app_id:
                missing.append("GITHUB_APP_ID")
            if not private_key_path:
                missing.append("GITHUB_APP_PRIVATE_KEY_PATH")
            if not installation_id:
                missing.append("GITHUB_APP_INSTALLATION_ID")
            logger.warning(
                "Using Personal Access Token (consider using GitHub App). "
                f"Missing config: {', '.join(missing)}"
            )

        self.client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            timeout=30.0,
        )

    def _generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        now = int(datetime.now(UTC).timestamp())
        payload = {
            "iat": now - 60,  # Issued at time (60 seconds ago to account for clock skew)
            "exp": now + 600,  # Expires in 10 minutes
            "iss": self.app_id,
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def _get_installation_token(self) -> str:
        """Get or refresh installation access token."""
        # Check if we have a valid token
        if self._installation_token and self._token_expires_at:
            # Use UTC-aware datetime for comparison
            now = datetime.now(UTC)
            if now < self._token_expires_at - timedelta(minutes=5):
                return self._installation_token

        # Generate new token
        jwt_token = self._generate_jwt()

        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        response = await self.client.post(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        self._installation_token = data["token"]
        # Ensure timezone-aware datetime
        expires_at_str = data["expires_at"].replace("Z", "+00:00")
        self._token_expires_at = datetime.fromisoformat(expires_at_str)
        # Ensure it's UTC-aware
        if self._token_expires_at.tzinfo is None:
            self._token_expires_at = self._token_expires_at.replace(tzinfo=UTC)

        logger.info(
            "GitHub installation token refreshed",
            expires_at=self._token_expires_at.isoformat(),
        )

        return self._installation_token

    async def _get_headers(self) -> dict:
        """Get headers with authentication token."""
        if self.use_app_auth:
            token = await self._get_installation_token()
        else:
            token = self.token

        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AI-Code-Review-Agent/1.0",
        }

    async def fetch_pr_diff(
        self, repo_full_name: str, pr_number: int
    ) -> DiffContext:
        """
        Fetch PR diff from GitHub.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            DiffContext with diff text and metadata

        Raises:
            httpx.HTTPError: If API call fails
            ValueError: If diff is too large or invalid
        """
        try:
            # First, get PR info
            headers = await self._get_headers()
            headers["Accept"] = "application/vnd.github+json"

            pr_response = await self.client.get(
                f"/repos/{repo_full_name}/pulls/{pr_number}",
                headers=headers,
            )
            pr_response.raise_for_status()
            pr_data = pr_response.json()

            # Get diff
            diff_headers = await self._get_headers()
            diff_headers["Accept"] = "application/vnd.github.v3.diff"

            diff_response = await self.client.get(
                f"/repos/{repo_full_name}/pulls/{pr_number}",
                headers=diff_headers,
            )
            diff_response.raise_for_status()
            diff_text = diff_response.text

            # Check diff size
            if len(diff_text) > MAX_DIFF_SIZE:
                raise ValueError(
                    f"Diff too large: {len(diff_text)} bytes (max: {MAX_DIFF_SIZE})"
                )

            # Parse diff to extract file list and stats
            changed_files = self._extract_changed_files(diff_text)
            additions, deletions = self._count_diff_stats(diff_text)

            # Preprocess diff (remove binary files, etc.)
            diff_text = self._preprocess_diff(diff_text)

            return DiffContext(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                diff_text=diff_text,
                changed_files=changed_files,
                additions=additions,
                deletions=deletions,
                pr_title=pr_data.get("title"),
                pr_description=pr_data.get("body"),
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"PR #{pr_number} not found in {repo_full_name}"
                ) from e
            elif e.response.status_code == 403:
                raise ValueError(
                    f"Access denied to {repo_full_name}. "
                    "Check GitHub App permissions or token permissions."
                ) from e
            else:
                logger.error("GitHub API error", status_code=e.response.status_code)
                raise
        except httpx.RequestError as e:
            logger.error("GitHub API request error", error=str(e))
            raise

    def _extract_changed_files(self, diff_text: str) -> List[str]:
        """Extract list of changed files from diff."""
        files = []
        # Pattern: "+++ b/path/to/file" or "--- a/path/to/file"
        pattern = re.compile(r"^[+-]{3}\s+[ab]/(.+)$", re.MULTILINE)
        for match in pattern.finditer(diff_text):
            file_path = match.group(1)
            if file_path not in files:
                files.append(file_path)
        return files

    def _count_diff_stats(self, diff_text: str) -> tuple[int, int]:
        """Count additions and deletions in diff."""
        additions = 0
        deletions = 0
        for line in diff_text.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
        return additions, deletions

    def _preprocess_diff(self, diff_text: str) -> str:
        """
        Preprocess diff to remove binary files and clean up.

        Args:
            diff_text: Raw diff text

        Returns:
            Preprocessed diff text
        """
        lines = diff_text.split("\n")
        processed_lines = []
        skip_file = False

        for line in lines:
            # Skip binary files
            if "Binary files differ" in line or "GIT binary patch" in line:
                skip_file = True
                continue

            # Reset skip flag when we hit a new file header
            if line.startswith("diff --git"):
                skip_file = False

            if not skip_file:
                processed_lines.append(line)

        return "\n".join(processed_lines)

    async def post_review_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        comments: List[ReviewComment],
    ) -> dict:
        """
        Post review comments to a GitHub PR using review API.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            comments: List of review comments to post

        Returns:
            API response data

        Raises:
            httpx.HTTPError: If API call fails
            PermissionError: If GitHub App lacks required permissions
        """
        if not comments:
            logger.warning("No comments to post")
            return {"posted_count": 0, "total_comments": 0}

        try:
            # Get PR files to map line numbers to positions
            headers = await self._get_headers()
            files_response = await self.client.get(
                f"/repos/{repo_full_name}/pulls/{pr_number}/files",
                headers=headers,
            )
            files_response.raise_for_status()
            pr_files = files_response.json()

            # Build review comments
            review_comments = []
            files_by_path = {f["filename"]: f for f in pr_files}

            for comment in comments:
                file_info = files_by_path.get(comment.file_path)
                if not file_info:
                    logger.warning(
                        f"File {comment.file_path} not found in PR, skipping comment"
                    )
                    continue

                # Get patch for this file
                patch = file_info.get("patch", "")
                if not patch:
                    logger.warning(
                        f"No patch for {comment.file_path}, skipping comment"
                    )
                    continue

                # Calculate position in diff
                position = self._calculate_position_from_patch(
                    patch, comment.line_number
                )
                if position is None:
                    logger.warning(
                        f"Could not find position for {comment.file_path}:{comment.line_number}, skipping"
                    )
                    continue

                # Build comment body with severity, category, and optional code snippet
                comment_body = self._format_comment_body(comment)
                
                review_comments.append(
                    {
                        "path": comment.file_path,
                        "position": position,
                        "body": comment_body,
                    }
                )

            if not review_comments:
                logger.warning("No valid review comments to post after filtering")
                return {"posted_count": 0, "total_comments": len(comments)}

            # Limit to 100 comments (GitHub API limit)
            if len(review_comments) > 100:
                logger.warning(
                    f"Too many comments ({len(review_comments)}), limiting to 100"
                )
                # Sort by severity (critical > high > medium > low)
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                comments_with_severity = [
                    (c, severity_order.get(com.severity.lower(), 99))
                    for c, com in zip(review_comments, comments)
                ]
                comments_with_severity.sort(key=lambda x: x[1])
                review_comments = [c[0] for c in comments_with_severity[:100]]

            # Create review with comments
            review_url = (
                f"/repos/{repo_full_name}/pulls/{pr_number}/reviews"
            )
            review_headers = await self._get_headers()

            payload = {
                "body": "🤖 AI Code Review",
                "event": "COMMENT",
                "comments": review_comments,
            }

            response = await self.client.post(
                review_url,
                headers=review_headers,
                json=payload,
            )

            if response.status_code == 403:
                error_msg = (
                    "GitHub App lacks 'Pull requests: Write' permission. "
                    "Update permissions in GitHub App settings at: "
                    f"https://github.com/settings/apps/{self.app_id if self.use_app_auth else 'YOUR_APP'}"
                )
                logger.error("GitHub permission denied", status=403, error=error_msg)
                raise PermissionError(error_msg)

            response.raise_for_status()

            result = response.json()
            posted_count = len(review_comments)

            logger.info(
                f"Posted {posted_count} review comments to PR #{pr_number}",
                review_id=result.get("id"),
            )

            return {
                "posted_count": posted_count,
                "total_comments": len(comments),
                "review_id": result.get("id"),
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitHub API error posting comments",
                status_code=e.response.status_code,
                response=e.response.text[:200],
            )
            if e.response.status_code == 403:
                raise PermissionError(
                    "GitHub API permission denied. Check App permissions."
                ) from e
            raise
        except Exception as e:
            logger.error("Error posting comments", error=str(e), exc_info=True)
            raise

    def _format_comment_body(self, comment: ReviewComment) -> str:
        """
        Format comment body with severity, category, and optional code snippet.

        Args:
            comment: ReviewComment object

        Returns:
            Formatted comment body for GitHub
        """
        parts = []
        
        # Add severity and category badges
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        emoji = severity_emoji.get(comment.severity.lower(), "🟡")
        
        if comment.category:
            parts.append(f"{emoji} **{comment.severity.upper()}** - *{comment.category}*")
        else:
            parts.append(f"{emoji} **{comment.severity.upper()}**")
        
        parts.append("")  # Empty line
        parts.append(comment.comment_text)
        
        # Add code snippet if available
        if comment.code_snippet:
            parts.append("")
            parts.append("**Suggested fix:**")
            parts.append("```python")
            parts.append(comment.code_snippet)
            parts.append("```")
        
        return "\n".join(parts)

    def _calculate_position_from_patch(self, patch: str, line_number: int) -> Optional[int]:
        """
        Calculate GitHub position for a line number in a patch.

        GitHub uses "position" (line index in diff, excluding header lines) 
        not "line number" (line in file).

        Args:
            patch: Unified diff patch for the file
            line_number: Line number in the file (1-indexed)

        Returns:
            Position in diff (1-indexed for GitHub API), or None if not found
        """
        lines = patch.split("\n")
        position = 0
        new_file_line = 0  # Track line number in the new file

        for line in lines:
            # Skip header lines - these don't count toward position
            if line.startswith("---") or line.startswith("+++") or line.startswith("diff"):
                continue

            # Parse hunk header to get starting line number
            if line.startswith("@@"):
                # Extract line number from hunk header: @@ -old_start,old_count +new_start,new_count @@
                match = re.search(r"\+(\d+)", line)
                if match:
                    new_file_line = int(match.group(1)) - 1  # Convert to 0-indexed
                position = 0  # Reset position at start of new hunk
                continue

            # Count all lines in diff (except deleted-only lines)
            if line.startswith("+"):
                # Added line
                new_file_line += 1
                position += 1
                if new_file_line == line_number:
                    return position
            elif line.startswith("-"):
                # Deleted line - counts toward position but not new file line number
                position += 1
            elif line.startswith(" "):
                # Context line (unchanged)
                new_file_line += 1
                position += 1
                if new_file_line == line_number:
                    return position

        return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
