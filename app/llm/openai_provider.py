"""OpenAI GPT provider implementation."""

from openai import OpenAI
from openai import APIError as OpenAIAPIError
from openai import RateLimitError as OpenAIRateLimitError

from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import APIError, InvalidResponseError, QuotaExceededError, RateLimitError
from app.llm.models import DiffContext, ReviewResult
from app.llm.parser import parse_review_response

logger = get_logger(__name__)

# OpenAI pricing (as of 2025-01, check https://openai.com/pricing)
# GPT-4: $30 per 1M input tokens, $60 per 1M output tokens
# GPT-4-turbo: $10 per 1M input tokens, $30 per 1M output tokens
# GPT-3.5-turbo: $0.50 per 1M input tokens, $1.50 per 1M output tokens
OPENAI_PRICING = {
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-16k": {"input": 0.50, "output": 1.50},
}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider for code review."""

    def __init__(self, model: str, api_key: str):
        """
        Initialize OpenAI provider.

        Args:
            model: Model identifier (e.g., "gpt-4", "gpt-4-turbo")
            api_key: OpenAI API key
        """
        super().__init__(model, api_key)
        self.client = OpenAI(api_key=api_key)
        self.provider_name = "openai"

    async def analyze_diff(
        self, diff_text: str, context: DiffContext | None = None
    ) -> ReviewResult:
        """
        Analyze a code diff using OpenAI GPT.

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
                f"Calling OpenAI API with model {self.model}, "
                f"diff length: {len(diff_text)} chars"
            )

            # Call OpenAI API
            result, execution_time = await self._time_execution(
                self._call_openai(prompt)
            )

            # Extract usage info
            input_tokens = result.usage.prompt_tokens
            output_tokens = result.usage.completion_tokens
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            cost = self.get_cost_estimate(input_tokens, output_tokens)

            logger.info(
                f"OpenAI API call completed: {total_tokens} tokens, "
                f"cost: ${cost:.4f}, time: {execution_time:.2f}s"
            )

            # Parse response
            response_text = result.choices[0].message.content
            if not response_text:
                raise InvalidResponseError("Empty response from OpenAI")

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

        except OpenAIRateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RateLimitError(f"OpenAI rate limit exceeded: {e}") from e
        except OpenAIAPIError as e:
            logger.error(f"OpenAI API error: {e}")
            if "quota" in str(e).lower() or "insufficient" in str(e).lower():
                raise QuotaExceededError(f"OpenAI quota exceeded: {e}") from e
            elif e.status_code == 429:
                raise RateLimitError(f"OpenAI rate limit: {e}") from e
            else:
                raise APIError(
                    f"OpenAI API error: {e}",
                    status_code=getattr(e, "status_code", None),
                ) from e
        except InvalidResponseError:
            # Re-raise parsing errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}", exc_info=True)
            raise APIError(f"Unexpected error: {e}") from e

    async def _call_openai(self, prompt: str):
        """Make async call to OpenAI API."""
        import asyncio

        def _sync_call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Analyze code changes and provide constructive feedback.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=4096,
                temperature=0.3,  # Lower temperature for more consistent output
            )

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for OpenAI token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Get pricing for this model, default to GPT-4 if unknown
        pricing = OPENAI_PRICING.get(self.model, OPENAI_PRICING["gpt-4"])

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

