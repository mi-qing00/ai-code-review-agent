"""Base abstract class for LLM providers."""

import time
from abc import ABC, abstractmethod
from typing import Optional

from app.core.logging import get_logger
from app.llm.errors import LLMProviderError
from app.llm.models import DiffContext, ReviewResult

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: str):
        """
        Initialize LLM provider.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-5-20250929")
            api_key: API key for the provider
        """
        self.model = model
        self.api_key = api_key
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    async def analyze_diff(
        self, diff_text: str, context: Optional[DiffContext] = None
    ) -> ReviewResult:
        """
        Analyze a code diff and return review comments.

        Args:
            diff_text: Unified diff text to analyze
            context: Optional context about the PR

        Returns:
            ReviewResult with comments and metadata

        Raises:
            LLMProviderError: If analysis fails
        """
        pass

    @abstractmethod
    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pass

    def build_prompt(self, diff_text: str, context: Optional[DiffContext] = None) -> str:
        """
        Build the prompt for code review.

        This is a shared implementation that can be overridden by providers
        if they need provider-specific prompt formatting.

        Args:
            diff_text: Unified diff text
            context: Optional PR context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are an expert code reviewer. Analyze the following code changes "
            "and provide constructive feedback.",
            "",
            "## Review Guidelines:",
            "",
            "### High Priority Checks:",
            "",
            "1. **Network Request Timeouts**:",
            "   - Check for network requests (requests.get, httpx.get, urllib, etc.) without timeout parameters",
            "   - Recommend setting timeout=30 or similar",
            "   - Example issue: 'httpx.get(url)' → 'httpx.get(url, timeout=30.0)'",
            "",
            "2. **Database Resource Leaks**:",
            "   - Check for database connections (sqlite3.connect, asyncpg.connect, psycopg2.connect) that aren't closed",
            "   - Check for connections not used in context managers (with/as)",
            "   - Recommend using context managers or ensure proper cleanup",
            "",
            "3. **Code Quality Improvements**:",
            "   - When you see 'for loop appending to list' → suggest list comprehension",
            "   - When you see nested if statements → suggest merging conditions",
            "   - When you see repetitive code → suggest extracting to functions",
            "   - Include improved code snippet when suggesting fixes",
            "",
            "### Security Checks:",
            "   - SQL injection vulnerabilities (string formatting in queries)",
            "   - XSS vulnerabilities (unsanitized user input)",
            "   - Hardcoded secrets or credentials",
            "   - Missing input validation",
            "",
            "### Other Checks:",
            "   - Bugs and logical errors",
            "   - Performance issues (inefficient algorithms, N+1 queries)",
            "   - Error handling missing or incomplete",
            "   - Code style and maintainability",
            "",
            "### Output Format:",
            "",
            "For each issue, provide:",
            "file_path:line_number [severity] [category] - comment_text",
            "",
            "Severity levels:",
            "  - critical: Security vulnerabilities, data loss risks, system crashes",
            "  - high: Bugs that will cause errors, resource leaks, incorrect behavior",
            "  - medium: Code quality issues, potential bugs, performance concerns",
            "  - low: Style improvements, suggestions, minor optimizations",
            "",
            "Categories: security, performance, bug, resource-leak, code-quality, style",
            "",
            "If suggesting code improvements, include the improved code snippet:",
            "file_path:line_number [severity] [category] - comment_text",
            "  Code:",
            "  ```python",
            "  # Improved code here",
            "  ```",
            "",
            "Group related issues when possible (e.g., '3 SQL injection vulnerabilities found').",
            "",
            "Maximum 15 comments per file. Prioritize critical and high severity issues.",
            "",
        ]

        if context:
            if context.pr_title:
                prompt_parts.append(f"PR Title: {context.pr_title}")
            if context.pr_description:
                prompt_parts.append(f"PR Description: {context.pr_description}")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "## Code Changes:",
                "```diff",
                diff_text,
                "```",
                "",
                "## Example Output Format:",
                "",
                "src/utils.py:42 [high] [resource-leak] - Database connection not closed. Use context manager:",
                "  Code:",
                "  ```python",
                "  with asyncpg.connect(db_url) as conn:",
                "      # ...",
                "  ```",
                "",
                "src/api.py:15 [critical] [security] - SQL injection vulnerability. Use parameterized queries",
                "",
                "src/process.py:30 [medium] [code-quality] - Consider using list comprehension:",
                "  Code:",
                "  ```python",
                "  results = [process(x) for x in items if x.is_valid()]",
                "  ```",
                "",
                "Now provide your review:",
            ]
        )

        return "\n".join(prompt_parts)

    async def _time_execution(self, coro):
        """
        Execute a coroutine and measure execution time.

        Args:
            coro: Coroutine to execute

        Returns:
            Tuple of (result, execution_time_in_seconds)
        """
        start_time = time.time()
        result = await coro
        execution_time = time.time() - start_time
        return result, execution_time

