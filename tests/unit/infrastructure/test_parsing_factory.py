"""Tests for structured output parsing factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ml_agents_v2.infrastructure.structured_output.models import (
    ChainOfThoughtOutput,
    DirectAnswerOutput,
)
from ml_agents_v2.infrastructure.structured_output.parsing_factory import (
    InstructorParser,
    OutputParserFactory,
    StructuredLogProbsParser,
)


class TestOutputParserFactory:
    """Test OutputParserFactory functionality."""

    @pytest.fixture
    def mock_openrouter_client(self):
        """Mock OpenRouter client."""
        return AsyncMock()

    @pytest.fixture
    def factory(self, mock_openrouter_client):
        """Create OutputParserFactory instance."""
        return OutputParserFactory(mock_openrouter_client)

    def test_factory_initialization(self, mock_openrouter_client):
        """Test factory initialization."""
        factory = OutputParserFactory(mock_openrouter_client)
        assert factory.openrouter_client == mock_openrouter_client

    def test_create_parser_for_openai_models(self, factory):
        """Test parser creation for OpenAI models that support logprobs."""
        # Test GPT-4
        parser = factory.create_parser("gpt-4")
        assert isinstance(parser, StructuredLogProbsParser)

        # Test GPT-3.5
        parser = factory.create_parser("gpt-3.5-turbo")
        assert isinstance(parser, StructuredLogProbsParser)

        # Test GPT-4 Turbo
        parser = factory.create_parser("gpt-4-turbo")
        assert isinstance(parser, StructuredLogProbsParser)

    def test_create_parser_for_non_openai_models(self, factory):
        """Test parser creation for models without logprobs support."""
        # Test Claude
        parser = factory.create_parser("claude-3-opus")
        assert isinstance(parser, InstructorParser)

        # Test Llama
        parser = factory.create_parser("meta-llama/llama-3.1-8b-instruct")
        assert isinstance(parser, InstructorParser)

        # Test Gemini
        parser = factory.create_parser("google/gemini-pro")
        assert isinstance(parser, InstructorParser)

        # Test unknown model
        parser = factory.create_parser("unknown-model")
        assert isinstance(parser, InstructorParser)

    def test_get_output_model_for_agent_types(self, factory):
        """Test output model mapping for different agent types."""
        # Test None agent
        model = factory.get_output_model("none")
        assert model == DirectAnswerOutput

        # Test Chain of Thought agent
        model = factory.get_output_model("chain_of_thought")
        assert model == ChainOfThoughtOutput

        # Test unknown agent type (should default to DirectAnswerOutput)
        model = factory.get_output_model("unknown_agent")
        assert model == DirectAnswerOutput


class TestStructuredLogProbsParser:
    """Test StructuredLogProbsParser functionality."""

    @pytest.fixture
    def mock_openrouter_client(self):
        """Mock OpenRouter client."""
        return AsyncMock()

    @pytest.fixture
    def mock_structured_client(self):
        """Mock StructuredLogProbsClient."""
        return AsyncMock()

    @pytest.fixture
    def parser(self, mock_openrouter_client):
        """Create StructuredLogProbsParser instance."""
        return StructuredLogProbsParser(mock_openrouter_client)

    def test_parser_initialization(self, mock_openrouter_client):
        """Test parser initialization."""
        parser = StructuredLogProbsParser(mock_openrouter_client)
        assert parser.openrouter_client == mock_openrouter_client

    def test_pydantic_to_json_schema_conversion(self, parser):
        """Test Pydantic to JSON schema conversion."""
        schema = parser._pydantic_to_json_schema(DirectAnswerOutput)

        assert schema["type"] == "json_schema"
        assert "json_schema" in schema
        assert "name" in schema["json_schema"]
        assert "description" in schema["json_schema"]
        assert "schema" in schema["json_schema"]
        assert schema["json_schema"]["strict"] is True

    async def test_parse_method(self, parser):
        """Test parse method with mocked response."""
        # Mock OpenAI response
        mock_choice = MagicMock()
        mock_choice.message.parsed = {"answer": "42"}
        mock_choice.logprobs = {"token_logprobs": [-0.1, -0.2]}

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = {"total_tokens": 50}

        parser.openrouter_client.chat.completions.create.return_value = mock_response

        # Mock structured_logprobs.add_logprobs
        mock_enhanced_response = MagicMock()
        mock_enhanced_response.log_probs = {"enhanced_logprobs": "data"}

        with patch(
            "ml_agents_v2.infrastructure.structured_output.parsing_factory.structured_logprobs.add_logprobs"
        ) as mock_add_logprobs:
            mock_add_logprobs.return_value = mock_enhanced_response

            # Mock AgentConfig
            mock_config = MagicMock()
            mock_config.model_name = "gpt-4"
            mock_config.model_parameters = {"temperature": 0.7}

            result = await parser.parse(DirectAnswerOutput, "Test prompt", mock_config)

            # Verify client was called correctly
            parser.openrouter_client.chat.completions.create.assert_called_once()
            call_args = parser.openrouter_client.chat.completions.create.call_args

            assert call_args[1]["model"] == "gpt-4"
            assert call_args[1]["messages"] == [
                {"role": "user", "content": "Test prompt"}
            ]
            assert "response_format" in call_args[1]
            assert call_args[1]["logprobs"] is True
            assert call_args[1]["temperature"] == 0.7

            # Verify structured_logprobs was called
            mock_add_logprobs.assert_called_once_with(mock_response)

            # Verify result structure
            assert "parsed_data" in result
            assert "confidence_scores" in result
            assert "token_usage" in result
            assert result["confidence_scores"] == {"enhanced_logprobs": "data"}
            assert result["token_usage"] == {"total_tokens": 50}


class TestInstructorParser:
    """Test InstructorParser functionality."""

    @pytest.fixture
    def mock_openrouter_client(self):
        """Mock OpenRouter client."""
        return AsyncMock()

    @pytest.fixture
    def mock_instructor_client(self):
        """Mock instructor client."""
        return AsyncMock()

    @pytest.fixture
    def parser(self, mock_openrouter_client, mock_instructor_client):
        """Create InstructorParser instance with mocked client."""
        with patch(
            "ml_agents_v2.infrastructure.structured_output.parsing_factory.instructor.from_openai"
        ) as mock_from_openai:
            mock_from_openai.return_value = mock_instructor_client
            parser = InstructorParser(mock_openrouter_client)
            parser.client = mock_instructor_client
            return parser

    def test_parser_initialization(self, mock_openrouter_client):
        """Test parser initialization."""
        with patch(
            "ml_agents_v2.infrastructure.structured_output.parsing_factory.instructor.from_openai"
        ) as mock_from_openai:
            mock_client = AsyncMock()
            mock_from_openai.return_value = mock_client

            InstructorParser(mock_openrouter_client)
            mock_from_openai.assert_called_once_with(mock_openrouter_client)

    async def test_parse_method(self, parser):
        """Test parse method with mocked response."""
        # Create mock response from instructor
        mock_response = MagicMock()
        mock_response.answer = "42"
        mock_response._raw_response = {"usage": {"total_tokens": 30}}

        parser.client.chat.completions.create.return_value = mock_response

        # Mock AgentConfig
        mock_config = MagicMock()
        mock_config.model_name = "claude-3-opus"
        mock_config.model_parameters = {"temperature": 0.5}

        result = await parser.parse(DirectAnswerOutput, "Test prompt", mock_config)

        # Verify client was called correctly
        parser.client.chat.completions.create.assert_called_once_with(
            model="claude-3-opus",
            messages=[{"role": "user", "content": "Test prompt"}],
            response_model=DirectAnswerOutput,
            temperature=0.5,
        )

        # Verify result structure
        assert "parsed_data" in result
        assert "confidence_scores" in result
        assert "token_usage" in result
        assert result["parsed_data"] == mock_response
        assert result["confidence_scores"] is None
        assert result["token_usage"] == {"total_tokens": 30}

    async def test_parse_method_no_raw_response(self, parser):
        """Test parse method when _raw_response is not available."""
        # Create mock response without _raw_response
        mock_response = MagicMock()
        mock_response.answer = "42"
        del mock_response._raw_response  # Remove attribute

        parser.client.chat.completions.create.return_value = mock_response

        # Mock AgentConfig
        mock_config = MagicMock()
        mock_config.model_name = "claude-3-opus"
        mock_config.model_parameters = {}

        result = await parser.parse(DirectAnswerOutput, "Test prompt", mock_config)

        # Verify result structure when no raw response
        assert "parsed_data" in result
        assert "confidence_scores" in result
        assert "token_usage" in result
        assert result["parsed_data"] == mock_response
        assert result["confidence_scores"] is None
        assert result["token_usage"] is None


class TestParserIntegration:
    """Integration tests for parser selection and usage."""

    @pytest.fixture
    def mock_openrouter_client(self):
        """Mock OpenRouter client."""
        return AsyncMock()

    @pytest.fixture
    def factory(self, mock_openrouter_client):
        """Create OutputParserFactory instance."""
        return OutputParserFactory(mock_openrouter_client)

    def test_parser_type_selection_consistency(self, factory):
        """Test that parser selection is consistent with model capabilities."""
        # Models that should use StructuredLogProbsParser
        logprobs_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]

        for model in logprobs_models:
            parser = factory.create_parser(model)
            assert isinstance(
                parser, StructuredLogProbsParser
            ), f"Model {model} should use StructuredLogProbsParser"

        # Models that should use InstructorParser
        instructor_models = [
            "claude-3-opus",
            "meta-llama/llama-3.1-8b-instruct",
            "google/gemini-pro",
            "unknown-model",
        ]

        for model in instructor_models:
            parser = factory.create_parser(model)
            assert isinstance(
                parser, InstructorParser
            ), f"Model {model} should use InstructorParser"

    def test_agent_type_output_model_mapping(self, factory):
        """Test that agent types map to correct output models."""
        test_cases = [
            ("none", DirectAnswerOutput),
            ("chain_of_thought", ChainOfThoughtOutput),
            ("unknown_type", DirectAnswerOutput),  # Should default
        ]

        for agent_type, expected_model in test_cases:
            output_model = factory.get_output_model(agent_type)
            assert (
                output_model == expected_model
            ), f"Agent type {agent_type} should map to {expected_model.__name__}"
