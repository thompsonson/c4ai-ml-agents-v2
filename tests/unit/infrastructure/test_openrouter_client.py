"""Tests for OpenRouter client implementation."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ml_agents_v2.infrastructure.openrouter.client import OpenRouterClient
from ml_agents_v2.infrastructure.openrouter.error_mapper import OpenRouterErrorMapper


class TestOpenRouterClient:
    """Test OpenRouter client implementation."""

    @pytest.fixture
    def client_config(self):
        """Create OpenRouter client configuration."""
        return {
            "api_key": "sk-test-key",
            "base_url": "https://openrouter.ai/api/v1",
            "timeout": 60,
            "max_retries": 3,
        }

    @pytest.fixture
    def client(self, client_config):
        """Create OpenRouter client instance."""
        return OpenRouterClient(**client_config)

    def test_client_initialization(self, client, client_config):
        """Test that OpenRouter client initializes correctly."""
        assert client.api_key == client_config["api_key"]
        assert client.base_url == client_config["base_url"]
        assert client.timeout == client_config["timeout"]
        assert client.max_retries == client_config["max_retries"]

    @patch("httpx.post")
    def test_chat_completion_success(self, mock_post, client):
        """Test successful chat completion request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "meta-llama/llama-3.1-8b-instruct",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "The answer is 4."},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_post.return_value = mock_response

        # Execute chat completion
        response = client.chat_completion(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "What is 2+2?"}],
            temperature=0.7,
            max_tokens=100,
        )

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args[1]["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test-key"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["timeout"] == 60

        # Verify request body
        request_data = json.loads(call_args[1]["content"])
        assert request_data["model"] == "meta-llama/llama-3.1-8b-instruct"
        assert request_data["messages"] == [{"role": "user", "content": "What is 2+2?"}]
        assert request_data["temperature"] == 0.7
        assert request_data["max_tokens"] == 100

        # Verify response
        assert response == mock_response.json.return_value

    @patch("httpx.post")
    def test_chat_completion_rate_limit_error(self, mock_post, client):
        """Test handling of rate limit errors."""
        # Mock rate limit error response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {"type": "rate_limit_exceeded", "message": "Rate limit exceeded"}
        }
        # Make raise_for_status() raise the appropriate exception
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit exceeded", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        # Should raise HTTPStatusError
        with pytest.raises(httpx.HTTPStatusError):
            client.chat_completion(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": "test"}],
            )

    @patch("httpx.post")
    def test_chat_completion_authentication_error(self, mock_post, client):
        """Test handling of authentication errors."""
        # Mock authentication error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"type": "authentication_error", "message": "Invalid API key"}
        }
        # Make raise_for_status() raise the appropriate exception
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Invalid API key", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        # Should raise HTTPStatusError
        with pytest.raises(httpx.HTTPStatusError):
            client.chat_completion(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": "test"}],
            )

    @patch("httpx.post")
    def test_chat_completion_network_error(self, mock_post, client):
        """Test handling of network errors."""
        # Mock network timeout
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        # Should raise TimeoutException
        with pytest.raises(httpx.TimeoutException):
            client.chat_completion(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": "test"}],
            )

    def test_get_headers(self, client):
        """Test header generation for requests."""
        headers = client.get_headers()

        assert headers["Authorization"] == "Bearer sk-test-key"
        assert headers["Content-Type"] == "application/json"
        assert "HTTP-Referer" in headers
        assert "X-Title" in headers


class TestOpenRouterErrorMapper:
    """Test OpenRouter error mapping to domain FailureReason."""

    def test_map_rate_limit_error(self):
        """Test mapping of rate limit errors."""
        error = httpx.HTTPStatusError(
            "Rate limit exceeded",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "rate_limit_exceeded"
        assert failure_reason.recoverable is True
        assert "rate limit" in failure_reason.description.lower()
        assert isinstance(failure_reason.occurred_at, datetime)

    def test_map_authentication_error(self):
        """Test mapping of authentication errors."""
        error = httpx.HTTPStatusError(
            "Invalid API key", request=MagicMock(), response=MagicMock(status_code=401)
        )

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "authentication_error"
        assert failure_reason.recoverable is False
        assert "authentication" in failure_reason.description.lower()

    def test_map_credit_limit_error(self):
        """Test mapping of credit limit errors."""
        error = httpx.HTTPStatusError(
            "Insufficient credits",
            request=MagicMock(),
            response=MagicMock(status_code=402),
        )

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "credit_limit_exceeded"
        assert failure_reason.recoverable is False
        assert "credit" in failure_reason.description.lower()

    def test_map_timeout_error(self):
        """Test mapping of timeout errors."""
        error = httpx.TimeoutException("Request timeout")

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "network_timeout"
        assert failure_reason.recoverable is True
        assert "timed out" in failure_reason.description.lower()

    def test_map_content_filter_error(self):
        """Test mapping of content filter errors."""
        error = httpx.HTTPStatusError(
            "Content filtered", request=MagicMock(), response=MagicMock(status_code=400)
        )
        error.response.json.return_value = {
            "error": {
                "type": "content_filter",
                "message": "Content violates safety guidelines",
            }
        }

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "content_guardrail"
        assert failure_reason.recoverable is False

    def test_map_token_limit_error(self):
        """Test mapping of token limit errors."""
        error = httpx.HTTPStatusError(
            "Token limit exceeded",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
        error.response.json.return_value = {
            "error": {
                "type": "invalid_request_error",
                "message": "This model's maximum context length is 4096 tokens",
            }
        }

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "token_limit_exceeded"
        assert failure_reason.recoverable is False

    def test_map_unknown_error(self):
        """Test mapping of unknown errors."""
        error = Exception("Unknown error occurred")

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "unknown"
        assert failure_reason.recoverable is False
        assert "unknown error" in failure_reason.description.lower()

    def test_map_model_refusal_error(self):
        """Test mapping of model refusal errors."""
        error = httpx.HTTPStatusError(
            "Model refused", request=MagicMock(), response=MagicMock(status_code=400)
        )
        error.response.json.return_value = {
            "error": {
                "type": "model_error",
                "message": "I cannot provide that information",
            }
        }

        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)

        assert failure_reason.category == "model_refusal"
        assert failure_reason.recoverable is False
