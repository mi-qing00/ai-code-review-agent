"""Factory for creating LLM provider instances."""

from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.errors import LLMProviderError

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)

# Cache for provider instance (singleton pattern)
_provider_instance: "BaseLLMProvider | None" = None


def get_llm_provider() -> "BaseLLMProvider":
    """
    Get the configured LLM provider instance.

    Uses singleton pattern to reuse the same provider instance.

    Returns:
        Configured LLM provider instance

    Raises:
        LLMProviderError: If provider configuration is invalid
        ValueError: If API key is missing
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    try:
        config = settings.get_llm_config()
        provider_name = config["provider"]
        model = config["model"]
        api_key = config["api_key"]

        logger.info(f"Initializing LLM provider: {provider_name} with model: {model}")

        if provider_name == "anthropic":
            from app.llm.anthropic_provider import AnthropicProvider

            _provider_instance = AnthropicProvider(model=model, api_key=api_key)
        elif provider_name == "openai":
            from app.llm.openai_provider import OpenAIProvider

            _provider_instance = OpenAIProvider(model=model, api_key=api_key)
        elif provider_name == "zhipu":
            from app.llm.zhipu_provider import ZhipuProvider

            _provider_instance = ZhipuProvider(model=model, api_key=api_key)
        else:
            raise LLMProviderError(f"Unknown provider: {provider_name}")

        logger.info(f"LLM provider {provider_name} initialized successfully")
        return _provider_instance

    except ValueError as e:
        logger.error(f"LLM provider configuration error: {e}")
        raise LLMProviderError(f"Configuration error: {e}") from e
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider: {e}", exc_info=True)
        raise LLMProviderError(f"Failed to initialize provider: {e}") from e


def reset_provider() -> None:
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None

