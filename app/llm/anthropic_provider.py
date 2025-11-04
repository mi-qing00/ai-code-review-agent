"""Anthropic Claude provider implementation."""

from anthropic import Anthropic
from anthropic import APIError as AnthropicAPIError
from anthropic import RateLimitError as AnthropicRateLimitError

from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import APIError, InvalidResponseError, QuotaExceededError, RateLimitError
from app.llm.models import DiffContext, ReviewComment, ReviewResult
from app.llm.parser import parse_review_response

logger = get_logger(__name__)

# Claude pricing (as of 2025-01, check https://www.anthropic.com/pricing)
# Claude Sonnet 4.5: $3 per 1M input tokens, $15 per 1M output tokens
CLAUDE_INPUT_COST_PER_1M = 3.0
CLAUDE_OUTPUT_COST_PER_1M = 15.0


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider for code review."""

    def __init__(self, model: str, api_key: str):
        """
        Initialize Anthropic provider.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-5-20250929")
            api_key: Anthropic API key
        """
        super().__init__(model, api_key)
        self.client = Anthropic(api_key=api_key)
        self.provider_name = "anthropic"

    async def analyze_diff(
        self, diff_text: str, context: DiffContext | None = None
    ) -> ReviewResult:
        """
        Analyze a code diff using Claude.

        Args:
            diff_text: Unified diff text to analyze
            context: Optional context about the PR

        Returns:
            ReviewResult with comments and metadata

        Raises:
            RateLimitError: If rate limit is exceeded
            QuotaExceededError: If quota is exceeded
            APIError: If API call fails
            InvalidResponseError: If response cannot be parsed
        """
        try:
            # Build prompt
            prompt = self.build_prompt(diff_text, context)

            logger.info(
                f"Calling Claude API with model {self.model}, "
                f"diff length: {len(diff_text)} chars"
            )

            # Call Claude API
            result, execution_time = await self._time_execution(
                self._call_claude(prompt)
            )

            # Extract usage info
            input_tokens = result.usage.input_tokens
            output_tokens = result.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            cost = self.get_cost_estimate(input_tokens, output_tokens)

            logger.info(
                f"Claude API call completed: {total_tokens} tokens, "
                f"cost: ${cost:.4f}, time: {execution_time:.2f}s"
            )

            # Parse response
            response_text = result.content[0].text
            comments = parse_review_response(response_text)

            return ReviewResult(
                comments=comments,
                model_used=self.model,
                provider=self.provider_name,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                processing_time=execution_time,
            )

        except AnthropicRateLimitError as e:
            logger.error(f"Claude rate limit exceeded: {e}")
            retry_after = getattr(e, "retry_after", None)
            raise RateLimitError(
                f"Claude rate limit exceeded: {e}",
                retry_after=retry_after,
            ) from e
        except AnthropicAPIError as e:
            logger.error(f"Claude API error: {e}")
            if e.status_code == 429:
                raise RateLimitError(f"Claude rate limit: {e}") from e
            elif e.status_code == 402:
                raise QuotaExceededError(f"Claude quota exceeded: {e}") from e
            else:
                raise APIError(
                    f"Claude API error: {e}",
                    status_code=e.status_code,
                ) from e
        except InvalidResponseError:
            # Re-raise parsing errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Claude provider: {e}", exc_info=True)
            raise APIError(f"Unexpected error: {e}") from e

    async def _call_claude(self, prompt: str):
        """Make async call to Claude API."""
        # Note: Anthropic SDK doesn't have async support in all versions
        # We'll use sync call but wrap it in a thread if needed
        # For now, using the sync client (will be improved with async support)
        import asyncio

        def _sync_call():
            return self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for Claude token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * CLAUDE_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * CLAUDE_OUTPUT_COST_PER_1M
        return input_cost + output_cost

