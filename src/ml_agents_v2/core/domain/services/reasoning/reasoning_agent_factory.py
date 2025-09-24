"""Factory for creating reasoning agent services."""

from ...value_objects.validation_result import ValidationResult
from .chain_of_thought_agent_service import ChainOfThoughtAgentService
from .none_agent_service import NoneAgentService
from .reasoning_agent_service import ReasoningAgentService


class ReasoningAgentServiceFactory:
    """Factory for creating reasoning agent services."""

    def __init__(self) -> None:
        self._services = {
            "none": NoneAgentService,
            "chain_of_thought": ChainOfThoughtAgentService,
        }

    def create_service(self, agent_type: str) -> ReasoningAgentService:
        """Create service instance by agent type."""
        if agent_type not in self._services:
            raise ValueError(f"Unknown agent type: {agent_type}")

        service_class = self._services[agent_type]
        return service_class()

    def get_supported_types(self) -> list[str]:
        """Return list of supported agent types."""
        return list(self._services.keys())

    def register_service(
        self, agent_type: str, service_class: type[ReasoningAgentService]
    ) -> None:
        """Register new reasoning service type."""
        self._services[agent_type] = service_class

    def create_registry(self) -> dict[str, ReasoningAgentService]:
        """Create registry dictionary for EvaluationOrchestrator."""
        return {
            agent_type: self.create_service(agent_type)
            for agent_type in self._services.keys()
        }

    def validate_agent_type(self, agent_type: str) -> ValidationResult:
        """Validate that agent type is supported."""
        if agent_type in self._services:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        else:
            supported_types = list(self._services.keys())
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Unsupported agent type '{agent_type}'. "
                    f"Supported types: {supported_types}"
                ],
                warnings=[],
            )
