"""Unit tests for evaluate command utilities."""

from ml_agents_v2.cli.commands.evaluate import _map_agent_type, _parse_model_string


class TestEvaluateUtilities:
    """Test utility functions for evaluate commands."""

    def test_map_agent_type_cot(self):
        """Test agent type mapping for Chain of Thought."""
        result = _map_agent_type("cot")
        assert result == "chain_of_thought"

    def test_map_agent_type_none(self):
        """Test agent type mapping for none (direct prompting)."""
        result = _map_agent_type("none")
        assert result == "none"

    def test_map_agent_type_unknown(self):
        """Test agent type mapping for unknown type returns original."""
        result = _map_agent_type("unknown")
        assert result == "unknown"

    def test_parse_model_string_with_provider(self):
        """Test parsing model string with provider."""
        provider, name = _parse_model_string("anthropic/claude-3-sonnet")
        assert provider == "anthropic"
        assert name == "claude-3-sonnet"

    def test_parse_model_string_openai(self):
        """Test parsing OpenAI model string."""
        provider, name = _parse_model_string("openai/gpt-4")
        assert provider == "openai"
        assert name == "gpt-4"

    def test_parse_model_string_without_provider(self):
        """Test parsing model string without provider defaults to anthropic."""
        provider, name = _parse_model_string("claude-3-sonnet")
        assert provider == "anthropic"
        assert name == "claude-3-sonnet"

    def test_parse_model_string_complex_name(self):
        """Test parsing model string with complex name containing slashes."""
        provider, name = _parse_model_string("provider/model/with/slashes")
        assert provider == "provider"
        assert name == "model/with/slashes"
