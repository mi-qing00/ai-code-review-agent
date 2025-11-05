"""Application configuration."""

import base64
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # GitHub
    github_webhook_secret: str = "your_webhook_secret_here"
    github_token: str = "your_github_token_here"  # Fallback, not recommended

    # GitHub App (recommended)
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_private_key_base64: Optional[str] = None  # For Railway deployment
    github_app_installation_id: str = ""

    # LLM Provider Selection
    llm_provider: str = "zhipu"  # Options: anthropic, openai, zhipu

    # Anthropic (Claude)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # Zhipu (GLM-4)
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4.6"

    # App Settings
    log_level: str = "INFO"
    environment: str = "development"
    app_url: str = "https://web-production-4a236.up.railway.app"  # Railway deployment URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_llm_config(self) -> dict:
        """
        Get LLM configuration based on selected provider.

        Returns:
            Dictionary with provider, model, and api_key

        Raises:
            ValueError: If provider is invalid or API key is missing
        """
        provider = self.llm_provider.lower()

        if provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
            return {
                "provider": "anthropic",
                "model": self.anthropic_model,
                "api_key": self.anthropic_api_key,
            }
        elif provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            return {
                "provider": "openai",
                "model": self.openai_model,
                "api_key": self.openai_api_key,
            }
        elif provider == "zhipu":
            if not self.zhipu_api_key:
                raise ValueError("ZHIPU_API_KEY is required when LLM_PROVIDER=zhipu")
            return {
                "provider": "zhipu",
                "model": self.zhipu_model,
                "api_key": self.zhipu_api_key,
            }
        else:
            raise ValueError(
                f"Invalid LLM_PROVIDER: {provider}. "
                "Must be one of: anthropic, openai, zhipu"
            )

    def get_github_app_private_key(self) -> str:
        """
        Get GitHub App private key, handling both file and base64 env var.

        Returns:
            Private key content as string

        Raises:
            ValueError: If no private key is configured
        """
        # Priority 1: Base64 encoded (for Railway/deployment)
        if self.github_app_private_key_base64:
            try:
                return base64.b64decode(self.github_app_private_key_base64).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Failed to decode base64 private key: {e}")

        # Priority 2: File path (for local development)
        if self.github_app_private_key_path:
            key_path = Path(self.github_app_private_key_path)
            # Resolve relative paths relative to project root
            if not key_path.is_absolute():
                project_root = Path(__file__).parent.parent.parent
                key_path = project_root / key_path

            if not key_path.exists():
                raise FileNotFoundError(
                    f"GitHub App private key not found: {key_path}. "
                    f"Check GITHUB_APP_PRIVATE_KEY_PATH setting."
                )

            with open(key_path, "r", encoding="utf-8") as f:
                return f.read()

        raise ValueError(
            "No GitHub App private key configured. "
            "Set either GITHUB_APP_PRIVATE_KEY_PATH or GITHUB_APP_PRIVATE_KEY_BASE64"
        )


settings = Settings()

