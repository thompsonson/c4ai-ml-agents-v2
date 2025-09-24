"""Model capabilities detection and registry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapabilities:
    """Model capability information for parser selection."""

    supports_structured_output: bool
    supports_logprobs: bool
    provider: str
    model_family: str


class ModelCapabilitiesRegistry:
    """Registry for model capabilities and parser selection."""

    _capabilities = {
        # OpenAI models - support both structured output and logprobs
        "gpt-4": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=True,
            provider="openai",
            model_family="gpt-4",
        ),
        "gpt-4-turbo": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=True,
            provider="openai",
            model_family="gpt-4",
        ),
        "gpt-3.5-turbo": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=True,
            provider="openai",
            model_family="gpt-3.5",
        ),
        # Claude models - structured output only via Instructor
        "claude-3-opus": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="anthropic",
            model_family="claude-3",
        ),
        "claude-3-sonnet": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="anthropic",
            model_family="claude-3",
        ),
        "claude-3-haiku": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="anthropic",
            model_family="claude-3",
        ),
        # Meta Llama models - structured output via Instructor only
        "meta-llama/llama-3.1-8b-instruct": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="meta",
            model_family="llama-3.1",
        ),
        "meta-llama/llama-3.1-70b-instruct": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="meta",
            model_family="llama-3.1",
        ),
        # Google models - structured output via Instructor only
        "google/gemini-pro": ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="google",
            model_family="gemini",
        ),
    }

    @classmethod
    def get_capabilities(cls, model_name: str) -> ModelCapabilities:
        """Get capabilities for a model, with fallback for unknown models."""
        # Try exact match first
        if model_name in cls._capabilities:
            return cls._capabilities[model_name]

        # Try partial matches for model families
        for registered_model, capabilities in cls._capabilities.items():
            if model_name.startswith(registered_model.split("/")[-1].split("-")[0]):
                return capabilities

        # Default fallback - assume Instructor-only support
        return ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="unknown",
            model_family="unknown",
        )

    @classmethod
    def supports_logprobs(cls, model_name: str) -> bool:
        """Check if a model supports logprobs extraction."""
        return cls.get_capabilities(model_name).supports_logprobs

    @classmethod
    def supports_structured_output(cls, model_name: str) -> bool:
        """Check if a model supports structured output."""
        return cls.get_capabilities(model_name).supports_structured_output
