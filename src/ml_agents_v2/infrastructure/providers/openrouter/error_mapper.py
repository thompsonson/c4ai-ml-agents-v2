"""Error mapping from OpenRouter API errors to domain FailureReason."""

import json
from datetime import datetime

import httpx

from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason


class OpenRouterErrorMapper:
    """Maps OpenRouter API errors to domain FailureReason value objects.

    Provides consistent error categorization for different types of
    failures that can occur when communicating with OpenRouter.
    """

    @staticmethod
    def map_to_failure_reason(error: Exception) -> FailureReason:
        """Map OpenRouter/HTTP errors to domain FailureReason.

        Args:
            error: Exception raised by OpenRouter client

        Returns:
            FailureReason with appropriate category and details
        """
        occurred_at = datetime.now()

        # Handle HTTP status errors from OpenRouter
        if isinstance(error, httpx.HTTPStatusError):
            return OpenRouterErrorMapper._map_http_status_error(error, occurred_at)

        # Handle network timeout errors
        if isinstance(error, httpx.TimeoutException):
            return FailureReason(
                category="network_timeout",
                description="Request to OpenRouter API timed out",
                technical_details=str(error),
                occurred_at=occurred_at,
                recoverable=True,
            )

        # Handle other network/request errors
        if isinstance(error, httpx.RequestError):
            return FailureReason(
                category="network_timeout",
                description="Network error communicating with OpenRouter API",
                technical_details=str(error),
                occurred_at=occurred_at,
                recoverable=True,
            )

        # Handle parsing errors (JSON decode errors, etc.)
        if isinstance(error, (json.JSONDecodeError, ValueError)):
            return FailureReason(
                category="parsing_error",
                description="Failed to parse response from OpenRouter API",
                technical_details=str(error),
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Default case for unknown errors
        return FailureReason(
            category="unknown",
            description="Unknown error occurred during OpenRouter API call",
            technical_details=f"{type(error).__name__}: {str(error)}",
            occurred_at=occurred_at,
            recoverable=False,
        )

    @staticmethod
    def _map_http_status_error(
        error: httpx.HTTPStatusError, occurred_at: datetime
    ) -> FailureReason:
        """Map HTTP status errors to specific failure categories.

        Args:
            error: HTTP status error from OpenRouter API
            occurred_at: Timestamp when error occurred

        Returns:
            FailureReason with category based on HTTP status and error details
        """
        status_code = error.response.status_code
        error_message = str(error)
        technical_details = f"HTTP {status_code}: {error_message}"

        # Try to extract error details from response body
        error_details = OpenRouterErrorMapper._extract_error_details(error.response)
        if error_details:
            technical_details += f" | API Error: {error_details}"

        # Rate limiting (429)
        if status_code == 429:
            return FailureReason(
                category="rate_limit_exceeded",
                description="OpenRouter API rate limit exceeded",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=True,
            )

        # Authentication errors (401)
        if status_code == 401:
            return FailureReason(
                category="authentication_error",
                description="OpenRouter API authentication failed",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Payment/credit errors (402)
        if status_code == 402:
            return FailureReason(
                category="credit_limit_exceeded",
                description="Insufficient OpenRouter API credits",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Bad request errors (400) - need to analyze the specific error type
        if status_code == 400:
            return OpenRouterErrorMapper._map_bad_request_error(
                error_details, technical_details, occurred_at
            )

        # Server errors (5xx)
        if 500 <= status_code < 600:
            return FailureReason(
                category="unknown",
                description="OpenRouter API server error",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=True,  # Server errors might be temporary
            )

        # Other client errors (4xx)
        if 400 <= status_code < 500:
            return FailureReason(
                category="unknown",
                description="OpenRouter API client error",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Other status codes
        return FailureReason(
            category="unknown",
            description="Unexpected HTTP status code from OpenRouter API",
            technical_details=technical_details,
            occurred_at=occurred_at,
            recoverable=False,
        )

    @staticmethod
    def _extract_error_details(response: httpx.Response) -> str:
        """Extract error details from OpenRouter API response.

        Args:
            response: HTTP response from OpenRouter API

        Returns:
            String with error details, or empty string if not extractable
        """
        try:
            response_data = response.json()
            if isinstance(response_data, dict) and "error" in response_data:
                error_info = response_data["error"]
                if isinstance(error_info, dict):
                    error_type = error_info.get("type", "")
                    error_message = error_info.get("message", "")
                    return f"{error_type}: {error_message}".strip(": ")
                elif isinstance(error_info, str):
                    return error_info
        except (json.JSONDecodeError, AttributeError):
            pass

        return ""

    @staticmethod
    def _map_bad_request_error(
        error_details: str, technical_details: str, occurred_at: datetime
    ) -> FailureReason:
        """Map 400 Bad Request errors to specific categories.

        Args:
            error_details: Extracted error details from API response
            technical_details: Full technical error details
            occurred_at: Timestamp when error occurred

        Returns:
            FailureReason with appropriate category
        """
        error_lower = error_details.lower()

        # Token limit errors
        if any(
            phrase in error_lower
            for phrase in [
                "token",
                "context length",
                "maximum context",
                "context window",
                "too long",
            ]
        ):
            return FailureReason(
                category="token_limit_exceeded",
                description="Request exceeded model's token limit",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Content filtering/safety errors
        if any(
            phrase in error_lower
            for phrase in [
                "content filter",
                "safety",
                "policy",
                "guideline",
                "inappropriate",
                "blocked",
            ]
        ):
            return FailureReason(
                category="content_guardrail",
                description="Content blocked by safety filters",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Model refusal (when model explicitly refuses)
        if any(
            phrase in error_lower
            for phrase in [
                "cannot provide",
                "unable to assist",
                "cannot help",
                "refuse",
                "decline",
                "won't",
            ]
        ):
            return FailureReason(
                category="model_refusal",
                description="Model refused to answer the question",
                technical_details=technical_details,
                occurred_at=occurred_at,
                recoverable=False,
            )

        # Default for other 400 errors
        return FailureReason(
            category="unknown",
            description="Invalid request to OpenRouter API",
            technical_details=technical_details,
            occurred_at=occurred_at,
            recoverable=False,
        )
