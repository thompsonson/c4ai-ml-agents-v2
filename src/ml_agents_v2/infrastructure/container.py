"""Dependency injection container for ML Agents v2."""

from dependency_injector import containers, providers

from ml_agents_v2.config.application_config import get_config
from ml_agents_v2.core.application.services.benchmark_processor import (
    BenchmarkProcessor,
)
from ml_agents_v2.core.application.services.evaluation_orchestrator import (
    EvaluationOrchestrator,
)
from ml_agents_v2.core.application.services.results_analyzer import (
    ResultsAnalyzer,
)
from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_factory import (
    ReasoningAgentFactory,
)
from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
    BenchmarkRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.repositories.evaluation_repository_impl import (
    EvaluationRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager
from ml_agents_v2.infrastructure.health import HealthChecker
from ml_agents_v2.infrastructure.logging_config import configure_logging
from ml_agents_v2.infrastructure.openrouter.client import OpenRouterClient


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the application.

    Configures all dependencies following the clean architecture pattern
    with proper separation between layers.
    """

    # Configuration
    config = providers.Singleton(get_config)

    # Logging configuration (called for side effects)
    logging_setup = providers.Resource(
        configure_logging,
        config=config,
    )

    # Infrastructure Layer - Database
    database_session_manager = providers.Singleton(
        DatabaseSessionManager,
        database_url=config.provided.database_url,
        echo=config.provided.database_echo,
    )

    # Infrastructure Layer - External APIs
    openrouter_client = providers.Singleton(
        OpenRouterClient,
        api_key=config.provided.openrouter_api_key,
        base_url=config.provided.openrouter_base_url,
        timeout=config.provided.openrouter_timeout,
        max_retries=config.provided.openrouter_max_retries,
    )

    # Infrastructure Layer - Repository Implementations
    benchmark_repository = providers.Singleton(
        BenchmarkRepositoryImpl,
        session_manager=database_session_manager,
    )

    evaluation_repository = providers.Singleton(
        EvaluationRepositoryImpl,
        session_manager=database_session_manager,
    )

    # Domain Layer - Service Factory
    reasoning_agent_factory = providers.Singleton(
        ReasoningAgentFactory,
    )

    # Infrastructure Services
    health_checker = providers.Singleton(
        HealthChecker,
        database_session_manager=database_session_manager,
        openrouter_client=openrouter_client,
    )

    # Application Services
    evaluation_orchestrator = providers.Factory(
        EvaluationOrchestrator,
        evaluation_repository=evaluation_repository,
        benchmark_repository=benchmark_repository,
        reasoning_agent_factory=reasoning_agent_factory,
    )

    benchmark_processor = providers.Factory(
        BenchmarkProcessor,
        benchmark_repository=benchmark_repository,
    )

    results_analyzer = providers.Factory(
        ResultsAnalyzer,
        evaluation_repository=evaluation_repository,
        benchmark_repository=benchmark_repository,
    )
