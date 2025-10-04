"""AgentConfig value object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .validation_result import ValidationResult


@dataclass(frozen=True)
class AgentConfig:
    """Configuration that determines which ReasoningAgent to use and how.

    This is a value object because configurations are reusable and shareable
    across evaluations. Two AgentConfig instances with identical attributes
    represent the same conceptual configuration.
    """

    agent_type: str
    model_provider: str
    model_name: str
    model_parameters: Mapping[str, Any]
    agent_parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Convert mutable dicts to immutable mappings for true immutability."""
        # Convert to frozendict-like behavior using types.MappingProxyType
        from types import MappingProxyType

        object.__setattr__(
            self, "model_parameters", MappingProxyType(dict(self.model_parameters))
        )
        object.__setattr__(
            self, "agent_parameters", MappingProxyType(dict(self.agent_parameters))
        )

    def equals(self, other: object) -> bool:
        """Value-based equality comparison."""
        if not isinstance(other, AgentConfig):
            return False

        return (
            self.agent_type == other.agent_type
            and self.model_provider == other.model_provider
            and self.model_name == other.model_name
            and self.model_parameters == other.model_parameters
            and self.agent_parameters == other.agent_parameters
        )

    def validate_configuration(self) -> ValidationResult:
        """Ensure configuration is valid."""
        errors: list[str] = []
        warnings: list[str] = []

        # Valid agent types (from Phase 1 specifications)
        valid_agent_types = {"none", "chain_of_thought"}
        if self.agent_type not in valid_agent_types:
            errors.append(
                f"Invalid agent_type '{self.agent_type}'. Must be one of: {valid_agent_types}"
            )

        # Valid model providers (Phase 9 multi-provider support)
        valid_providers = {"openrouter", "openai", "anthropic", "litellm"}
        if self.model_provider not in valid_providers:
            errors.append(
                f"Invalid model_provider '{self.model_provider}'. "
                f"Must be one of: {', '.join(sorted(valid_providers))}"
            )

        # Validate model parameters
        if "temperature" in self.model_parameters:
            temp = self.model_parameters["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0.0 or temp > 2.0:
                errors.append("temperature must be a number between 0.0 and 2.0")

        if "max_tokens" in self.model_parameters:
            max_tokens = self.model_parameters["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                errors.append("max_tokens must be a positive integer")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage/comparison."""
        return {
            "agent_type": self.agent_type,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "model_parameters": dict(self.model_parameters),
            "agent_parameters": dict(self.agent_parameters),
        }
