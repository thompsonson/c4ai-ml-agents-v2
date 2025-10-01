"""Tests for LLMClient domain interface contract.

These tests validate the domain interface contract that all LLM client
implementations must follow. They test the domain abstraction, not
implementation details.
"""

from typing import Protocol
from unittest.mock import AsyncMock

import pytest

from ml_agents_v2.core.domain.services.llm_client import LLMClient, ParsedResponse


class MockLLMClient(LLMClient):
    """Test implementation of LLMClient interface."""

    def __init__(self):
        self.mock_response = AsyncMock()

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs
    ) -> ParsedResponse:
        """Mock implementation for testing."""
        return await self.mock_response(model, messages, **kwargs)


class TestLLMClientInterface:
    """Test LLMClient domain interface contract."""

    @pytest.fixture
    def llm_client(self):
        """Create mock LLM client for testing."""
        return MockLLMClient()

    async def test_chat_completion_returns_parsed_response(self, llm_client):
        """Test that chat_completion returns ParsedResponse domain object."""
        # Arrange
        expected_response = ParsedResponse(
            content="Test response",
            structured_data={"answer": "42"},
        )
        llm_client.mock_response.return_value = expected_response

        # Act
        result = await llm_client.chat_completion(
            model="test-model", messages=[{"role": "user", "content": "Test question"}]
        )

        # Assert
        assert isinstance(result, ParsedResponse)
        assert result.content == "Test response"
        assert result.structured_data == {"answer": "42"}

    async def test_chat_completion_with_minimal_response(self, llm_client):
        """Test ParsedResponse with minimal required fields."""
        # Arrange
        minimal_response = ParsedResponse(content="Minimal response")
        llm_client.mock_response.return_value = minimal_response

        # Act
        result = await llm_client.chat_completion(
            model="test-model", messages=[{"role": "user", "content": "Test"}]
        )

        # Assert
        assert isinstance(result, ParsedResponse)
        assert result.content == "Minimal response"
        assert result.structured_data is None

    async def test_chat_completion_interface_signature(self, llm_client):
        """Test that LLMClient interface has correct method signature."""
        # This test will fail until we create the actual interface
        assert hasattr(llm_client, "chat_completion")
        assert callable(llm_client.chat_completion)

    def test_llm_client_is_protocol(self):
        """Test that LLMClient is a Protocol for type checking."""
        # This test will fail until we create the LLMClient protocol
        assert issubclass(LLMClient, Protocol)

    def test_parsed_response_domain_object_exists(self):
        """Test that ParsedResponse domain value object exists."""
        # This test will fail until we create ParsedResponse
        response = ParsedResponse(content="test")
        assert response.content == "test"
        assert response.structured_data is None


class TestParsedResponseValueObject:
    """Test ParsedResponse domain value object."""

    def test_parsed_response_creation_with_content_only(self):
        """Test creating ParsedResponse with content only."""
        response = ParsedResponse(content="Test content")

        assert response.content == "Test content"
        assert response.structured_data is None

    def test_parsed_response_creation_with_all_fields(self):
        """Test creating ParsedResponse with all fields."""
        response = ParsedResponse(
            content="Full response",
            structured_data={"result": "success"},
        )

        assert response.content == "Full response"
        assert response.structured_data == {"result": "success"}

    def test_parsed_response_business_methods(self):
        """Test ParsedResponse business methods."""
        # Test has_structured_data method
        response_with_data = ParsedResponse(
            content="test", structured_data={"key": "value"}
        )
        response_without_data = ParsedResponse(content="test")

        assert response_with_data.has_structured_data() is True
        assert response_without_data.has_structured_data() is False

    def test_parsed_response_validation(self):
        """Test ParsedResponse domain validation."""
        # Empty content should raise ValueError
        with pytest.raises(ValueError, match="Response content cannot be empty"):
            ParsedResponse(content="")

        with pytest.raises(ValueError, match="Response content cannot be empty"):
            ParsedResponse(content="   ")  # Only whitespace


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
