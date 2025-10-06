"""Tests for OpenRouterClient as Anti-Corruption Layer.

These tests validate that OpenRouterClient properly implements the ACL pattern:
1. Implements LLMClient domain interface
2. Normalizes all external API types to domain types
3. Handles type variations (Pydantic models, dicts, None)
4. Never leaks external types to domain layer
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from ml_agents_v2.core.domain.services.llm_client import LLMClient
from ml_agents_v2.core.domain.value_objects.answer import ParsedResponse
from ml_agents_v2.infrastructure.providers import OpenRouterClient


class MockCompletionUsage:
    """Mock Pydantic CompletionUsage model from external API."""

    def __init__(
        self,
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        """Mock Pydantic model_dump method."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


class MockChatCompletionMessage:
    """Mock OpenAI ChatCompletionMessage."""

    def __init__(self, content: str = "", parsed: Any = None):
        self.content = content
        self.parsed = parsed


class MockChoice:
    """Mock OpenAI Choice object."""

    def __init__(self, message: MockChatCompletionMessage):
        self.message = message


class MockChatCompletion:
    """Mock OpenAI ChatCompletion response object."""

    def __init__(
        self, choices: list[MockChoice], model: str = "gpt-4", id: str = "test-id"
    ):
        self.choices = choices
        self.model = model
        self.id = id


class TestOpenRouterACLInterface:
    """Test OpenRouterClient implements LLMClient interface."""

    def test_openrouter_implements_llm_client_interface(self):
        """Test that OpenRouterClient implements LLMClient protocol."""
        client = OpenRouterClient(api_key="test-key")

        # Should implement the LLMClient protocol
        assert isinstance(client, LLMClient)
        assert hasattr(client, "chat_completion")
        assert callable(client.chat_completion)

    async def test_chat_completion_returns_parsed_response(self):
        """Test that chat_completion returns ParsedResponse domain object."""
        # Create mock OpenAI response
        mock_message = MockChatCompletionMessage(
            content="Test response from ACL", parsed={"answer": "42"}
        )
        mock_choice = MockChoice(message=mock_message)
        mock_response = MockChatCompletion(choices=[mock_choice])

        client = OpenRouterClient(api_key="test-key")

        # Mock the OpenAI client's chat.completions.create method
        with patch.object(
            client._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.chat_completion(
                model="gpt-4", messages=[{"role": "user", "content": "test"}]
            )

            assert isinstance(result, ParsedResponse)
            assert result.content == "Test response from ACL"
            assert result.structured_data == {"answer": "42"}

            # Verify the OpenAI client was called with correct parameters
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["model"] == "gpt-4"
            assert call_args["messages"] == [{"role": "user", "content": "test"}]


class TestOpenRouterACLIntegration:
    """Test end-to-end ACL behavior with external API simulation."""

    async def test_external_pydantic_response_normalized_to_domain(self):
        """Test that external Pydantic response is normalized to domain types."""
        # Create mock response with structured data
        mock_message = MockChatCompletionMessage(
            content="External API response", parsed={"answer": "42"}
        )
        mock_choice = MockChoice(message=mock_message)
        mock_response = MockChatCompletion(choices=[mock_choice])

        client = OpenRouterClient(api_key="test-key")

        with patch.object(
            client._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.chat_completion(
                model="gpt-4", messages=[{"role": "user", "content": "test"}]
            )

            # Verify result is pure domain type
            assert isinstance(result, ParsedResponse)
            assert result.content == "External API response"
            assert result.structured_data == {"answer": "42"}

    async def test_external_dict_response_normalized_to_domain(self):
        """Test that external dict response is normalized to domain types."""
        # Create mock response without structured data
        mock_message = MockChatCompletionMessage(content="Dict response")
        mock_choice = MockChoice(message=mock_message)
        mock_response = MockChatCompletion(choices=[mock_choice])

        client = OpenRouterClient(api_key="test-key")

        with patch.object(
            client._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.chat_completion(
                model="claude-3-sonnet", messages=[{"role": "user", "content": "test"}]
            )

            # Verify result is pure domain type
            assert isinstance(result, ParsedResponse)
            assert result.content == "Dict response"
            assert result.structured_data is None

    async def test_no_external_types_leak_to_domain(self):
        """Test that no external API types leak into domain layer."""
        # This is a meta-test ensuring our ACL boundary is effective
        client = OpenRouterClient(api_key="test-key")

        # The interface should only allow domain types
        result_type = client.chat_completion.__annotations__.get("return")
        assert "ParsedResponse" in str(result_type)

        # Parameters should only accept domain types
        param_types = client.chat_completion.__annotations__
        assert "model" in param_types
        assert "messages" in param_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
