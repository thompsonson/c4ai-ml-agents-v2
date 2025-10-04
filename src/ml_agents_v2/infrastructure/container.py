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
    ReasoningAgentServiceFactory,
)
from ml_agents_v2.infrastructure.csv.evaluation_results_csv_writer import (
    EvaluationResultsCsvWriter,
)
from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
    BenchmarkRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.repositories.evaluation_question_result_repository_impl import (
    EvaluationQuestionResultRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.repositories.evaluation_repository_impl import (
    EvaluationRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager
from ml_agents_v2.infrastructure.health import HealthChecker
from ml_agents_v2.infrastructure.logging_config import configure_logging
from ml_agents_v2.infrastructure.openrouter.client import OpenRouterClient
from ml_agents_v2.infrastructure.openrouter.error_mapper import OpenRouterErrorMapper
from ml_agents_v2.infrastructure.parsing_factory import LLMClientFactory
from ml_agents_v2.infrastructure.reasoning_service import ReasoningInfrastructureService


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

    evaluation_question_result_repository = providers.Singleton(
        EvaluationQuestionResultRepositoryImpl,
        session_manager=database_session_manager,
    )

    # Domain Layer - Service Factory for Phase 6
    reasoning_agent_service_factory = providers.Singleton(
        ReasoningAgentServiceFactory,
    )

    # Domain service registry created via factory
    domain_service_registry = providers.Singleton(
        lambda factory: factory.create_registry(),
        factory=reasoning_agent_service_factory,
    )

    # Infrastructure Services
    openrouter_error_mapper = providers.Singleton(
        OpenRouterErrorMapper,
    )

    llm_client_factory = providers.Singleton(
        LLMClientFactory,
        api_key=config.provided.openrouter_api_key,
        base_url=config.provided.openrouter_base_url,
    )

    reasoning_infrastructure_service = providers.Singleton(
        ReasoningInfrastructureService,
        llm_client_factory=llm_client_factory,
        error_mapper=openrouter_error_mapper,
        parsing_strategy=config.provided.parsing_strategy,
    )

    health_checker = providers.Singleton(
        HealthChecker,
        database_session_manager=database_session_manager,
        openrouter_client=openrouter_client,
    )

    # Export Service
    export_service = providers.Singleton(
        EvaluationResultsCsvWriter,
    )

    # Application Services
    evaluation_orchestrator = providers.Factory(
        EvaluationOrchestrator,
        evaluation_repository=evaluation_repository,
        evaluation_question_result_repository=evaluation_question_result_repository,
        benchmark_repository=benchmark_repository,
        reasoning_infrastructure_service=reasoning_infrastructure_service,
        domain_service_registry=domain_service_registry,
        export_service=export_service,
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
