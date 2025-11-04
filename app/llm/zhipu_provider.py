"""Zhipu GLM provider implementation (for development/testing)."""

import httpx

from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import APIError, InvalidResponseError, RateLimitError
from app.llm.models import DiffContext, ReviewResult
from app.llm.parser import parse_review_response

logger = get_logger(__name__)

# Zhipu pricing (as of 2025-01, check https://open.bigmodel.cn/)
# GLM-4: Much cheaper than Claude/OpenAI, good for development
# Pricing: approximately $0.10 per 1M input tokens, $0.40 per 1M output tokens
ZHIPU_INPUT_COST_PER_1M = 0.10
ZHIPU_OUTPUT_COST_PER_1M = 0.40

ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


class ZhipuProvider(BaseLLMProvider):
    """Zhipu GLM provider for code review (development/testing)."""

    def __init__(self, model: str, api_key: str):
        """
        Initialize Zhipu provider.

        Args:
            model: Model identifier (e.g., "glm-4")
            api_key: Zhipu API key
        """
        super().__init__(model, api_key)
        self.api_key = api_key
        self.provider_name = "zhipu"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def analyze_diff(
        self, diff_text: str, context: DiffContext | None = None
    ) -> ReviewResult:
        """
        Analyze a code diff using Zhipu GLM.

        Args:
            diff_text: Unified diff text to analyze
            context: Optional context about the PR

        Returns:
            ReviewResult with comments and metadata

        Raises:
            RateLimitError: If rate limit is exceeded
            APIError: If API call fails
            InvalidResponseError: If response cannot be parsed
        """
        try:
            # Build prompt
            prompt = self.build_prompt(diff_text, context)

            logger.info(
                f"Calling Zhipu API with model {self.model}, "
                f"diff length: {len(diff_text)} chars"
            )

            # Call Zhipu API
            result, execution_time = await self._time_execution(
                self._call_zhipu(prompt)
            )

            # Extract usage info
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            cost = self.get_cost_estimate(input_tokens, output_tokens)

            logger.info(
                f"Zhipu API call completed: {total_tokens} tokens, "
                f"cost: ${cost:.4f}, time: {execution_time:.2f}s"
            )

            # Parse response
            choices = result.get("choices", [])
            if not choices:
                raise InvalidResponseError("Empty response from Zhipu")

            response_text = choices[0].get("message", {}).get("content", "")
            if not response_text:
                raise InvalidResponseError("Empty content in Zhipu response")

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

        except httpx.HTTPStatusError as e:
            logger.error(f"Zhipu API HTTP error: {e}")
            if e.response.status_code == 429:
                raise RateLimitError(f"Zhipu rate limit: {e}") from e
            else:
                raise APIError(
                    f"Zhipu API error: {e}",
                    status_code=e.response.status_code,
                ) from e
        except httpx.RequestError as e:
            logger.error(f"Zhipu API request error: {e}")
            raise APIError(f"Zhipu request error: {e}") from e
        except InvalidResponseError:
            # Re-raise parsing errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Zhipu provider: {e}", exc_info=True)
            raise APIError(f"Unexpected error: {e}") from e

    async def _call_zhipu(self, prompt: str) -> dict:
        """Make async call to Zhipu API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert code reviewer. Analyze code changes and provide constructive feedback.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "max_tokens": 4096,
            "temperature": 0.3,
        }

        response = await self.client.post(
            ZHIPU_API_BASE,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for Zhipu token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * ZHIPU_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * ZHIPU_OUTPUT_COST_PER_1M
        return input_cost + output_cost

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

