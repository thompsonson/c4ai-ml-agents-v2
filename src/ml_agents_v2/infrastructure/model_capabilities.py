"""Model capabilities registry for determining parser selection.

This module determines which structured output approach to use based on
model capabilities.
"""


class ModelCapabilitiesRegistry:
    """Registry for determining model capabilities."""

    # Models that support logprobs (OpenAI models)
    LOGPROBS_MODELS = {
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "o1",
        "o1-mini",
        "o1-preview",
    }

    @classmethod
    def supports_logprobs(cls, model_name: str) -> bool:
        """Check if a model supports logprobs.

        Args:
            model_name: Name of the model to check

        Returns:
            True if the model supports logprobs, False otherwise
        """
        # Extract base model name (remove provider prefix if present)
        base_model = model_name.split("/")[-1] if "/" in model_name else model_name

        # Check if base model supports logprobs
        return any(
            logprobs_model in base_model for logprobs_model in cls.LOGPROBS_MODELS
        )
