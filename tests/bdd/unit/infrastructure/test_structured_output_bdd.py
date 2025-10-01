"""BDD tests for structured output parsing system.

This module implements the BDD scenarios defined in the structured output parsing plan:
- Parser selection based on model capabilities
- InstructorParser behavior and exception handling
- StructuredLogProbsParser behavior and exception handling
- ACL translation from ParserException to FailureReason

All tests use deterministic mock data for fast, repeatable testing.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason
from ml_agents_v2.infrastructure.reasoning_service import ReasoningInfrastructureService
from ml_agents_v2.infrastructure.structured_output.exceptions import ParserException
from ml_agents_v2.infrastructure.structured_output.models import (
    ChainOfThoughtOutput,
    DirectAnswerOutput,
)
from ml_agents_v2.infrastructure.structured_output.parsing_factory import (
    InstructorParser,
    OutputParserFactory,
    StructuredLogProbsParser,
)
from tests.bdd.fixtures.structured_output_fixtures import (
    EMPTY_RESPONSES,
    INVALID_JSON,
    SCHEMA_MISMATCHES,
    VALID_RESPONSES,
)


class TestParserSelection:
    """BDD tests for parser selection logic based on model capabilities."""

    def test_selects_structured_logprobs_parser_for_logprobs_models(
        self, mock_llm_client
    ):
        """Given model supports logprobs, when creating parser, then returns StructuredLogProbsParser"""
        # Arrange
        factory = OutputParserFactory(mock_llm_client)
        logprobs_model = "gpt-4"  # Known to support logprobs

        # Act
        parser = factory.create_parser(logprobs_model)

        # Assert
        assert isinstance(parser, StructuredLogProbsParser)

    def test_selects_instructor_parser_for_non_logprobs_models(self, mock_llm_client):
        """Given model doesn't support logprobs, when creating parser, then returns InstructorParser"""
        # Arrange
        factory = OutputParserFactory(mock_llm_client)
        non_logprobs_model = "claude-3-sonnet"  # Known to not support logprobs

        # Act
        parser = factory.create_parser(non_logprobs_model)

        # Assert
        assert isinstance(parser, InstructorParser)

    def test_output_model_mapping_for_agent_types(self, mock_llm_client):
        """Given agent type, when getting output model, then returns correct schema"""
        # Arrange
        factory = OutputParserFactory(mock_llm_client)

        # Act & Assert
        assert factory.get_output_model("none") == DirectAnswerOutput
        assert factory.get_output_model("chain_of_thought") == ChainOfThoughtOutput
        assert factory.get_output_model("unknown_type") == DirectAnswerOutput  # Default


class TestInstructorParser:
    """BDD tests for InstructorParser behavior and exception handling."""

    @pytest.fixture
    def instructor_parser(self, mock_llm_client):
        """Create InstructorParser instance for testing."""
        return InstructorParser(mock_llm_client)

    @pytest.fixture
    def sample_config(self):
        """Sample agent configuration for testing."""
        return AgentConfig(
            agent_type="none",
            model_provider="anthropic",
            model_name="claude-3-sonnet",
            model_parameters={"temperature": 1.0},
            agent_parameters={},
        )

    async def test_instructor_parser_successfully_parses_valid_json(
        self, instructor_parser, sample_config, mock_parsed_response_factory
    ):
        """Given valid JSON response, when parsing, then returns structured data"""
        # Arrange
        valid_json = VALID_RESPONSES["direct_simple"]
        mock_response = mock_parsed_response_factory(valid_json)
        instructor_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act
        result = await instructor_parser.parse(
            DirectAnswerOutput, "test prompt", sample_config
        )

        # Assert
        assert "parsed_data" in result
        assert result["parsed_data"].answer == "4"
        assert result["confidence_scores"] is None

    async def test_instructor_parser_raises_exception_on_malformed_json(
        self, instructor_parser, sample_config, mock_parsed_response_factory
    ):
        """Given malformed JSON, when parsing, then raises ParserException with stage='json_parse'"""
        # Arrange
        malformed_json = INVALID_JSON["missing_brace"]
        mock_response = mock_parsed_response_factory(malformed_json)
        instructor_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act & Assert
        with pytest.raises(ParserException) as exc_info:
            await instructor_parser.parse(
                DirectAnswerOutput, "test prompt", sample_config
            )

        exception = exc_info.value
        assert exception.parser_type == "InstructorParser"
        assert exception.stage == "json_parse"
        assert exception.model == "claude-3-sonnet"
        assert exception.provider == "anthropic"
        assert malformed_json in exception.content

    async def test_instructor_parser_raises_exception_on_schema_mismatch(
        self, instructor_parser, sample_config, mock_parsed_response_factory
    ):
        """Given valid JSON that doesn't match schema, when parsing, then raises ParserException with stage='schema_validation'"""
        # Arrange
        schema_mismatch = SCHEMA_MISMATCHES["wrong_field_name"]
        mock_response = mock_parsed_response_factory(schema_mismatch)
        instructor_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act & Assert
        with pytest.raises(ParserException) as exc_info:
            await instructor_parser.parse(
                DirectAnswerOutput, "test prompt", sample_config
            )

        exception = exc_info.value
        assert exception.parser_type == "InstructorParser"
        assert exception.stage == "schema_validation"
        assert exception.model == "claude-3-sonnet"
        assert exception.provider == "anthropic"

    async def test_instructor_parser_raises_exception_on_empty_response(
        self, instructor_parser, sample_config, mock_parsed_response_factory
    ):
        """Given empty response, when parsing, then raises ParserException with stage='response_empty'"""
        # Arrange
        empty_response = EMPTY_RESPONSES["completely_empty"]
        mock_response = mock_parsed_response_factory(empty_response)
        instructor_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act & Assert
        with pytest.raises(ParserException) as exc_info:
            await instructor_parser.parse(
                DirectAnswerOutput, "test prompt", sample_config
            )

        exception = exc_info.value
        assert exception.parser_type == "InstructorParser"
        assert exception.stage == "response_empty"
        assert exception.model == "claude-3-sonnet"
        assert exception.provider == "anthropic"

    def test_parser_exception_contains_full_context(self):
        """Given parsing failure, when exception raised, then contains parser_type, model, stage, content, error"""
        # Arrange
        original_error = ValueError("Test error")
        content = "test content"

        # Act
        exception = ParserException(
            parser_type="InstructorParser",
            model="test-model",
            provider="test",
            stage="json_parse",
            content=content,
            error=original_error,
        )

        # Assert
        assert exception.parser_type == "InstructorParser"
        assert exception.model == "test-model"
        assert exception.provider == "test"
        assert exception.stage == "json_parse"
        assert exception.content == content
        assert exception.original_error == original_error

        # Test helper methods
        assert exception.get_truncated_content(10) == "test conte..."
        exception_dict = exception.to_dict()
        assert exception_dict["parser_type"] == "InstructorParser"
        assert exception_dict["original_error_type"] == "ValueError"


class TestStructuredLogProbsParser:
    """BDD tests for StructuredLogProbsParser behavior and exception handling."""

    @pytest.fixture
    def structured_parser(self, mock_llm_client):
        """Create StructuredLogProbsParser instance for testing."""
        return StructuredLogProbsParser(mock_llm_client)

    @pytest.fixture
    def sample_config(self):
        """Sample agent configuration for testing."""
        return AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7},
            agent_parameters={},
        )

    async def test_structured_logprobs_uses_response_format(
        self, structured_parser, sample_config, mock_parsed_response_factory
    ):
        """Given schema, when parsing, then request includes response_format parameter"""
        # Arrange
        valid_json = VALID_RESPONSES["cot_simple"]
        mock_response = mock_parsed_response_factory(valid_json)
        structured_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act
        await structured_parser.parse(
            ChainOfThoughtOutput, "test prompt", sample_config
        )

        # Assert
        call_args = structured_parser.llm_client.chat_completion.call_args
        assert "response_format" in call_args.kwargs
        assert "logprobs" in call_args.kwargs
        assert call_args.kwargs["logprobs"] is True

        response_format = call_args.kwargs["response_format"]
        assert response_format["type"] == "json_schema"
        assert "json_schema" in response_format

    async def test_structured_logprobs_uses_structured_data_when_available(
        self, structured_parser, sample_config, mock_parsed_response_factory
    ):
        """Given response with structured_data, when parsing, then uses structured_data"""
        # Arrange
        structured_data = {"answer": "4", "reasoning": "2+2=4"}
        mock_response = mock_parsed_response_factory(
            content='{"answer": "4", "reasoning": "2+2=4"}',
            structured_data=structured_data,
        )
        structured_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act
        result = await structured_parser.parse(
            ChainOfThoughtOutput, "test prompt", sample_config
        )

        # Assert
        assert result["parsed_data"].answer == "4"
        assert result["parsed_data"].reasoning == "2+2=4"

    async def test_structured_logprobs_parses_content_as_json_fallback(
        self, structured_parser, sample_config, mock_parsed_response_factory
    ):
        """Given response with only content, when parsing, then parses content as JSON"""
        # Arrange
        valid_json = VALID_RESPONSES["cot_simple"]
        mock_response = mock_parsed_response_factory(
            content=valid_json, structured_data=None  # No structured data available
        )
        structured_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act
        result = await structured_parser.parse(
            ChainOfThoughtOutput, "test prompt", sample_config
        )

        # Assert
        assert result["parsed_data"].answer == "4"
        assert result["parsed_data"].reasoning == "2+2 equals 4"

    async def test_structured_logprobs_raises_exception_on_failure(
        self, structured_parser, sample_config, mock_parsed_response_factory
    ):
        """Given parsing failure, when error occurs, then raises ParserException with parser_type='StructuredLogProbsParser'"""
        # Arrange
        empty_response = EMPTY_RESPONSES["completely_empty"]
        mock_response = mock_parsed_response_factory(empty_response)
        structured_parser.llm_client.chat_completion = AsyncMock(
            return_value=mock_response
        )

        # Act & Assert
        with pytest.raises(ParserException) as exc_info:
            await structured_parser.parse(
                ChainOfThoughtOutput, "test prompt", sample_config
            )

        exception = exc_info.value
        assert exception.parser_type == "StructuredLogProbsParser"
        assert exception.model == "gpt-4"


class TestACLTranslation:
    """BDD tests for exception translation at ACL boundary."""

    @pytest.fixture
    def reasoning_service(self, mock_llm_client):
        """Create ReasoningInfrastructureService for testing."""
        mock_error_mapper = Mock()
        return ReasoningInfrastructureService(mock_llm_client, mock_error_mapper)

    def test_parser_exception_translates_to_failure_reason(self, reasoning_service):
        """Given ParserException in infrastructure, when caught by service, then returns FailureReason"""
        # Arrange
        parser_exception = ParserException(
            parser_type="InstructorParser",
            model="claude-3-sonnet",
            provider="anthropic",
            stage="json_parse",
            content="malformed json",
            error=ValueError("Invalid JSON"),
        )

        # Act
        failure_reason = reasoning_service._translate_parser_exception(parser_exception)

        # Assert
        assert isinstance(failure_reason, FailureReason)
        assert failure_reason.category == "parsing_error"
        assert "InstructorParser failed at json_parse" in failure_reason.description
        assert "claude-3-sonnet" in failure_reason.technical_details
        assert "json_parse" in failure_reason.technical_details
        assert failure_reason.recoverable is False

    def test_failure_reason_contains_parser_context(self, reasoning_service):
        """Given translated FailureReason, when inspected, then contains parser_type and stage in description"""
        # Arrange
        parser_exception = ParserException(
            parser_type="StructuredLogProbsParser",
            model="gpt-4",
            provider="openai",
            stage="schema_validation",
            content="test content",
            error=ValueError("Schema mismatch"),
        )

        # Act
        failure_reason = reasoning_service._translate_parser_exception(parser_exception)

        # Assert
        assert "StructuredLogProbsParser" in failure_reason.description
        assert "schema_validation" in failure_reason.description
        assert "StructuredLogProbsParser" in failure_reason.technical_details
        assert "gpt-4" in failure_reason.technical_details
