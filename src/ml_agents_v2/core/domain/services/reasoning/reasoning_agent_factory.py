"""Factory for creating reasoning agent services."""

from __future__ import annotations

from ...value_objects.agent_config import AgentConfig
from .exceptions import InvalidConfigurationError
from .reasoning_agent_service import ReasoningAgentService


class ReasoningAgentFactory:
    """Factory for creating appropriate reasoning agent services.

    Maintains a registry of available reasoning agent services and creates
    instances based on agent configuration.
    """

    def __init__(self) -> None:
        """Initialize the factory with empty registry."""
        self._services: dict[str, type[ReasoningAgentService]] = {}

    def register_service(
        self, agent_type: str, service_class: type[ReasoningAgentService]
    ) -> None:
        """Register a reasoning agent service for a specific agent type.

        Args:
            agent_type: Agent type this service handles (e.g., "none", "chain_of_thought")
            service_class: Service class to instantiate for this agent type

        Raises:
            ValueError: If agent_type is already registered
        """
        if agent_type in self._services:
            raise ValueError(
                f"Service for agent type '{agent_type}' already registered"
            )

        self._services[agent_type] = service_class

    def create_service(self, agent_config: AgentConfig) -> ReasoningAgentService:
        """Create a reasoning agent service for the given configuration.

        Args:
            agent_config: Configuration specifying agent type and parameters

        Returns:
            Configured reasoning agent service

        Raises:
            InvalidConfigurationError: If agent type is not supported
        """
        agent_type = agent_config.agent_type

        if agent_type not in self._services:
            available_types = list(self._services.keys())
            raise InvalidConfigurationError(
                f"Unsupported agent type '{agent_type}'. "
                f"Available types: {available_types}",
                agent_type,
            )

        service_class = self._services[agent_type]
        service = service_class()

        # Validate configuration against the service
        if not service.validate_config(agent_config):
            raise InvalidConfigurationError(
                f"Configuration validation failed for agent type '{agent_type}'",
                agent_type,
            )

        return service

    def get_supported_agent_types(self) -> list[str]:
        """Get list of supported agent types.

        Returns:
            List of registered agent type names
        """
        return list(self._services.keys())

    def is_agent_type_supported(self, agent_type: str) -> bool:
        """Check if an agent type is supported.

        Args:
            agent_type: Agent type to check

        Returns:
            True if agent type is registered, False otherwise
        """
        return agent_type in self._services

    def unregister_service(self, agent_type: str) -> bool:
        """Unregister a service for an agent type.

        Args:
            agent_type: Agent type to unregister

        Returns:
            True if service was unregistered, False if it wasn't registered
        """
        if agent_type in self._services:
            del self._services[agent_type]
            return True
        return False
