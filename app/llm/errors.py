"""Custom exceptions for LLM providers."""


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class RateLimitError(LLMProviderError):
    """Raised when LLM API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class QuotaExceededError(LLMProviderError):
    """Raised when LLM API quota is exceeded."""

    pass


class InvalidResponseError(LLMProviderError):
    """Raised when LLM returns an unparseable response."""

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class APIError(LLMProviderError):
    """Raised when LLM API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TimeoutError(LLMProviderError):
    """Raised when LLM API request times out."""

    pass

