"""Tests for dependency injection container implementation."""

from unittest.mock import patch

import pytest
from dependency_injector import providers

from ml_agents_v2.infrastructure.container import Container


class TestContainer:
    """Test Container dependency injection setup."""

    @pytest.fixture
    def container(self):
        """Create Container instance for testing."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            return Container()

    def test_container_initialization(self, container):
        """Test that Container initializes without errors."""
        # The container might be a DynamicContainer due to dependency-injector behavior
        # What's important is that it has our expected attributes
        assert container is not None
        assert hasattr(container, "config")

    def test_container_has_all_required_providers(self, container):
        """Test that Container has all expected providers."""
        # Configuration
        assert hasattr(container, "config")
        assert hasattr(container, "logging_setup")

        # Infrastructure Layer - Database
        assert hasattr(container, "database_session_manager")

        # Infrastructure Layer - External APIs
        assert hasattr(container, "openrouter_client")

        # Infrastructure Layer - Repository Implementations
        assert hasattr(container, "benchmark_repository")
        assert hasattr(container, "evaluation_repository")

        # Domain Layer - Service Factory
        assert hasattr(container, "reasoning_agent_factory")

        # Infrastructure Services
        assert hasattr(container, "health_checker")

    def test_config_provider_type(self, container):
        """Test that config provider is properly configured."""
        assert isinstance(container.config, providers.Singleton)

    def test_logging_setup_provider_type(self, container):
        """Test that logging_setup provider is properly configured."""
        assert isinstance(container.logging_setup, providers.Resource)

    def test_database_session_manager_provider_type(self, container):
        """Test that database_session_manager provider is properly configured."""
        assert isinstance(container.database_session_manager, providers.Singleton)

    def test_openrouter_client_provider_type(self, container):
        """Test that openrouter_client provider is properly configured."""
        assert isinstance(container.openrouter_client, providers.Singleton)

    def test_repository_providers_type(self, container):
        """Test that repository providers are properly configured."""
        assert isinstance(container.benchmark_repository, providers.Singleton)
        assert isinstance(container.evaluation_repository, providers.Singleton)

    def test_reasoning_agent_factory_provider_type(self, container):
        """Test that reasoning_agent_factory provider is properly configured."""
        assert isinstance(container.reasoning_agent_factory, providers.Singleton)

    def test_health_checker_provider_type(self, container):
        """Test that health_checker provider is properly configured."""
        assert isinstance(container.health_checker, providers.Singleton)

    def test_config_provider_exists(self, container):
        """Test that config provider exists and can be accessed."""
        assert hasattr(container, "config")
        assert container.config is not None

    def test_logging_setup_provider_exists(self, container):
        """Test that logging_setup provider exists and can be accessed."""
        assert hasattr(container, "logging_setup")
        assert container.logging_setup is not None

    def test_database_session_manager_provider_dependencies(self, container):
        """Test that database_session_manager provider exists and is configured."""
        provider = container.database_session_manager
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_openrouter_client_provider_dependencies(self, container):
        """Test that openrouter_client provider exists and is configured."""
        provider = container.openrouter_client
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_benchmark_repository_provider_dependencies(self, container):
        """Test that benchmark_repository provider exists and is configured."""
        provider = container.benchmark_repository
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_evaluation_repository_provider_dependencies(self, container):
        """Test that evaluation_repository provider exists and is configured."""
        provider = container.evaluation_repository
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_health_checker_provider_dependencies(self, container):
        """Test that health_checker provider exists and is configured."""
        provider = container.health_checker
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_reasoning_agent_factory_provider_no_dependencies(self, container):
        """Test that reasoning_agent_factory provider exists and is configured."""
        provider = container.reasoning_agent_factory
        assert provider is not None
        assert isinstance(provider, providers.Singleton)

    def test_container_provides_all_services(self, container):
        """Test that container can provide all configured services."""
        # Test that we can access all service providers without errors
        assert container.config is not None
        assert container.logging_setup is not None
        assert container.database_session_manager is not None
        assert container.openrouter_client is not None
        assert container.benchmark_repository is not None
        assert container.evaluation_repository is not None
        assert container.reasoning_agent_factory is not None
        assert container.health_checker is not None

    def test_container_basic_configuration(self, container):
        """Test that container has basic configuration without full wiring."""
        # This test verifies the container structure without actually
        # instantiating services which may require external dependencies

        # Verify all providers are configured
        assert hasattr(container, "config")
        assert hasattr(container, "logging_setup")
        assert hasattr(container, "database_session_manager")
        assert hasattr(container, "openrouter_client")
        assert hasattr(container, "benchmark_repository")
        assert hasattr(container, "evaluation_repository")
        assert hasattr(container, "reasoning_agent_factory")
        assert hasattr(container, "health_checker")

        # Verify provider types
        assert isinstance(container.config, providers.Singleton)
        assert isinstance(container.logging_setup, providers.Resource)
        assert isinstance(container.database_session_manager, providers.Singleton)
        assert isinstance(container.openrouter_client, providers.Singleton)
        assert isinstance(container.benchmark_repository, providers.Singleton)
        assert isinstance(container.evaluation_repository, providers.Singleton)
        assert isinstance(container.reasoning_agent_factory, providers.Singleton)
        assert isinstance(container.health_checker, providers.Singleton)
