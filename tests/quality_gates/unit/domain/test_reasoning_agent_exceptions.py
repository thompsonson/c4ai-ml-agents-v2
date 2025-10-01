"""Tests for reasoning agent service exceptions."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.exceptions import (
    InvalidConfigurationError,
    ModelProviderError,
    QuestionProcessingError,
    ReasoningAgentError,
    TimeoutError,
)


class TestReasoningAgentError:
    """Test suite for ReasoningAgentError base exception."""

    def test_reasoning_agent_error_creation(self) -> None:
        """Test ReasoningAgentError can be created with message."""
        error = ReasoningAgentError("Test error message")

        assert str(error) == "Test error message"
        assert error.cause is None

    def test_reasoning_agent_error_with_cause(self) -> None:
        """Test ReasoningAgentError can be created with underlying cause."""
        original_error = ValueError("Original error")
        error = ReasoningAgentError("Wrapped error", cause=original_error)

        assert str(error) == "Wrapped error"
        assert error.cause is original_error

    def test_reasoning_agent_error_inheritance(self) -> None:
        """Test ReasoningAgentError inherits from Exception."""
        error = ReasoningAgentError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, ReasoningAgentError)


class TestInvalidConfigurationError:
    """Test suite for InvalidConfigurationError."""

    def test_invalid_configuration_error_creation(self) -> None:
        """Test InvalidConfigurationError formats message correctly."""
        error = InvalidConfigurationError(
            "Temperature must be between 0 and 2", "chain_of_thought"
        )

        expected_msg = "Invalid configuration for chain_of_thought: Temperature must be between 0 and 2"
        assert str(error) == expected_msg
        assert error.config_issue == "Temperature must be between 0 and 2"
        assert error.agent_type == "chain_of_thought"

    def test_invalid_configuration_error_inheritance(self) -> None:
        """Test InvalidConfigurationError inherits from ReasoningAgentError."""
        error = InvalidConfigurationError("Test issue", "none")

        assert isinstance(error, ReasoningAgentError)
        assert isinstance(error, InvalidConfigurationError)

    def test_invalid_configuration_error_different_agents(self) -> None:
        """Test InvalidConfigurationError works with different agent types."""
        none_error = InvalidConfigurationError("Invalid parameter", "none")
        cot_error = InvalidConfigurationError(
            "Missing required config", "chain_of_thought"
        )

        assert "none" in str(none_error)
        assert "Invalid parameter" in str(none_error)
        assert "chain_of_thought" in str(cot_error)
        assert "Missing required config" in str(cot_error)


class TestModelProviderError:
    """Test suite for ModelProviderError."""

    def test_model_provider_error_creation(self) -> None:
        """Test ModelProviderError formats message correctly."""
        error = ModelProviderError("openai", "API key is invalid")

        expected_msg = "Model provider 'openai' error: API key is invalid"
        assert str(error) == expected_msg
        assert error.provider == "openai"
        assert error.error_details == "API key is invalid"

    def test_model_provider_error_inheritance(self) -> None:
        """Test ModelProviderError inherits from ReasoningAgentError."""
        error = ModelProviderError("test", "test error")

        assert isinstance(error, ReasoningAgentError)
        assert isinstance(error, ModelProviderError)

    def test_model_provider_error_different_providers(self) -> None:
        """Test ModelProviderError works with different providers."""
        openai_error = ModelProviderError("openai", "Rate limit exceeded")
        anthropic_error = ModelProviderError("anthropic", "Authentication failed")
        mock_error = ModelProviderError("mock", "Connection timeout")

        assert "openai" in str(openai_error)
        assert "Rate limit exceeded" in str(openai_error)
        assert "anthropic" in str(anthropic_error)
        assert "Authentication failed" in str(anthropic_error)
        assert "mock" in str(mock_error)
        assert "Connection timeout" in str(mock_error)


class TestQuestionProcessingError:
    """Test suite for QuestionProcessingError."""

    def test_question_processing_error_creation(self) -> None:
        """Test QuestionProcessingError formats message correctly."""
        error = QuestionProcessingError(
            "q123", "reasoning_generation", "Failed to generate reasoning"
        )

        expected_msg = "Failed to process question 'q123' at reasoning_generation: Failed to generate reasoning"
        assert str(error) == expected_msg
        assert error.question_id == "q123"
        assert error.processing_stage == "reasoning_generation"
        assert error.details == "Failed to generate reasoning"

    def test_question_processing_error_inheritance(self) -> None:
        """Test QuestionProcessingError inherits from ReasoningAgentError."""
        error = QuestionProcessingError("q1", "stage", "details")

        assert isinstance(error, ReasoningAgentError)
        assert isinstance(error, QuestionProcessingError)

    def test_question_processing_error_different_stages(self) -> None:
        """Test QuestionProcessingError works with different processing stages."""
        parsing_error = QuestionProcessingError(
            "q1", "question_parsing", "Invalid question format"
        )
        reasoning_error = QuestionProcessingError(
            "q2", "reasoning_generation", "Reasoning failed"
        )
        answer_error = QuestionProcessingError(
            "q3", "answer_extraction", "Could not extract answer"
        )
        validation_error = QuestionProcessingError(
            "q4", "response_validation", "Response invalid"
        )

        assert "question_parsing" in str(parsing_error)
        assert "Invalid question format" in str(parsing_error)
        assert "reasoning_generation" in str(reasoning_error)
        assert "Reasoning failed" in str(reasoning_error)
        assert "answer_extraction" in str(answer_error)
        assert "Could not extract answer" in str(answer_error)
        assert "response_validation" in str(validation_error)
        assert "Response invalid" in str(validation_error)


class TestTimeoutError:
    """Test suite for TimeoutError."""

    def test_timeout_error_creation(self) -> None:
        """Test TimeoutError formats message correctly."""
        error = TimeoutError(30.0)

        expected_msg = "Reasoning operation timed out after 30.0 seconds"
        assert str(error) == expected_msg
        assert error.timeout_seconds == 30.0

    def test_timeout_error_inheritance(self) -> None:
        """Test TimeoutError inherits from ReasoningAgentError."""
        error = TimeoutError(10.0)

        assert isinstance(error, ReasoningAgentError)
        assert isinstance(error, TimeoutError)

    def test_timeout_error_different_durations(self) -> None:
        """Test TimeoutError works with different timeout durations."""
        short_timeout = TimeoutError(5.0)
        long_timeout = TimeoutError(120.5)
        immediate_timeout = TimeoutError(0.1)

        assert "5.0 seconds" in str(short_timeout)
        assert short_timeout.timeout_seconds == 5.0
        assert "120.5 seconds" in str(long_timeout)
        assert long_timeout.timeout_seconds == 120.5
        assert "0.1 seconds" in str(immediate_timeout)
        assert immediate_timeout.timeout_seconds == 0.1


class TestExceptionHierarchy:
    """Test suite for exception hierarchy relationships."""

    def test_all_reasoning_agent_exceptions_inherit_from_base(self) -> None:
        """Test all reasoning agent exceptions inherit from ReasoningAgentError."""
        exceptions = [
            InvalidConfigurationError("test", "none"),
            ModelProviderError("test", "test"),
            QuestionProcessingError("q1", "stage", "details"),
            TimeoutError(10.0),
        ]

        for exc in exceptions:
            assert isinstance(exc, ReasoningAgentError)
            assert isinstance(exc, Exception)

    def test_exception_raising_and_catching(self) -> None:
        """Test exceptions can be raised and caught properly."""
        # Test InvalidConfigurationError
        with pytest.raises(InvalidConfigurationError) as exc_info:
            raise InvalidConfigurationError("Invalid config", "test_agent")
        assert exc_info.value.config_issue == "Invalid config"
        assert exc_info.value.agent_type == "test_agent"

        # Test ModelProviderError
        with pytest.raises(ModelProviderError) as exc_info:
            raise ModelProviderError("test_provider", "connection failed")
        assert exc_info.value.provider == "test_provider"
        assert exc_info.value.error_details == "connection failed"

        # Test QuestionProcessingError
        with pytest.raises(QuestionProcessingError) as exc_info:
            raise QuestionProcessingError("q123", "parsing", "parse error")
        assert exc_info.value.question_id == "q123"
        assert exc_info.value.processing_stage == "parsing"
        assert exc_info.value.details == "parse error"

        # Test TimeoutError
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError(15.0)
        assert exc_info.value.timeout_seconds == 15.0

        # Test catching by base class
        with pytest.raises(ReasoningAgentError):
            raise ModelProviderError("test", "error")

    def test_exception_chaining_with_cause(self) -> None:
        """Test exception chaining works correctly."""
        original = ConnectionError("Network unreachable")
        wrapped = ReasoningAgentError(
            "Failed to connect to model provider", cause=original
        )

        assert wrapped.cause is original
        assert str(wrapped) == "Failed to connect to model provider"
        assert str(wrapped.cause) == "Network unreachable"

    def test_nested_exception_handling(self) -> None:
        """Test handling nested exceptions in reasoning workflow."""
        # Simulate a nested error scenario
        try:
            try:
                # Simulate network error
                raise ConnectionError("Connection refused")
            except ConnectionError as conn_err:
                # Wrap in model provider error
                raise ModelProviderError("openai", "Connection failed") from conn_err
        except ModelProviderError as model_err:
            # Wrap in question processing error
            final_error = QuestionProcessingError(
                "q456", "api_call", f"Model provider failed: {model_err}"
            )

            assert isinstance(final_error, QuestionProcessingError)
            assert isinstance(final_error, ReasoningAgentError)
            assert "Model provider failed" in final_error.details
            assert final_error.question_id == "q456"
            assert final_error.processing_stage == "api_call"

    def test_exception_attributes_immutability(self) -> None:
        """Test that exception attributes are properly set and accessible."""
        # InvalidConfigurationError
        config_error = InvalidConfigurationError("bad config", "test_type")
        assert hasattr(config_error, "config_issue")
        assert hasattr(config_error, "agent_type")

        # ModelProviderError
        provider_error = ModelProviderError("test_provider", "test_details")
        assert hasattr(provider_error, "provider")
        assert hasattr(provider_error, "error_details")

        # QuestionProcessingError
        processing_error = QuestionProcessingError("q1", "test_stage", "test_details")
        assert hasattr(processing_error, "question_id")
        assert hasattr(processing_error, "processing_stage")
        assert hasattr(processing_error, "details")

        # TimeoutError
        timeout_error = TimeoutError(25.0)
        assert hasattr(timeout_error, "timeout_seconds")
        assert timeout_error.timeout_seconds == 25.0
