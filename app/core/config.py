"""Application configuration."""

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


settings = Settings()

