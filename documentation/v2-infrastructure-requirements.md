# Infrastructure Requirements

**Version:** 1.0
**Date:** 2025-09-17
**Purpose:** Define external dependencies, configuration, and deployment infrastructure

## Overview

Infrastructure components supporting the ML Agents v2 research platform, designed for 12-factor app principles with externalized configuration and modular API integration.

## Development Environment

### Python Environment Management

```bash
# Using uv for fast, reliable dependency management
uv venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install -r requirements.txt
```

### Core Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "python-dotenv>=1.0.0",      # Environment variable management
    "openai>=1.51.0",            # OpenRouter compatible async client
    "httpx>=0.25.0",             # Async HTTP client for direct API calls
    "pydantic>=2.5.0",           # Configuration validation and structured output
    "instructor>=1.3.0",         # Structured output parsing
    "structured-logprobs>=0.1.0", # Confidence scoring with logprobs
    "sqlalchemy>=2.0.0",         # Database ORM
    "alembic>=1.13.0",           # Database migrations
    "structlog>=23.2.0",         # Structured logging
    "click>=8.1.0",              # CLI framework
    "rich>=13.7.0",              # CLI formatting and progress bars
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "black>=23.12.0",
    "ruff>=0.1.8",
    "mypy>=1.8.0",
]
```

## Structured Output Parsing Strategy

### Overview

The infrastructure layer uses two parsing strategies depending on model capabilities:

- **Structured LogProbs**: For models supporting logprobs (OpenAI models)
- **Instructor**: For models without logprobs support (Anthropic, etc.) 

### Model Capability Detection

```python
# infrastructure/model_capabilities.py
@dataclass
class ModelCapabilities:
    supports_logprobs: bool
    supports_streaming: bool
    supports_function_calling: bool
    max_tokens: int
    provider: str

MODEL_CAPABILITIES = {
    "openai/gpt-4o": ModelCapabilities(
        supports_logprobs=True,
        supports_streaming=True,
        supports_function_calling=True,
        max_tokens=128000,
        provider="openai"
    ),
    "anthropic/claude-3-5-sonnet-20241022": ModelCapabilities(
        supports_logprobs=False,
        supports_streaming=True,
        supports_function_calling=True,
        max_tokens=200000,
        provider="anthropic"
    ),
}
```

### Parsing Strategy Implementation

```python
# infrastructure/structured_output/parsing_factory.py
from typing import Union, Type
from pydantic import BaseModel
from structured_logprobs import StructuredLogProbsClient
import instructor

class StructuredLogProbsParser:
    """Use structured-logprobs for models supporting logprobs."""

    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = StructuredLogProbsClient(openrouter_client)

    def _pydantic_to_json_schema(self, model: Type[BaseModel]) -> dict:
        """Convert Pydantic model to structured-logprobs format."""
        schema = model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__.lower(),
                "description": model.__doc__ or f"Schema for {model.__name__}",
                "schema": schema,
                "strict": True
            }
        }

    async def parse(
        self,
        model: Type[BaseModel],
        prompt: str,
        config: AgentConfig
    ) -> dict:
        """Parse using structured-logprobs with confidence scoring."""
        json_schema = self._pydantic_to_json_schema(model)

        response = await self.client.create(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=json_schema,
            **config.model_parameters
        )

        # Extract structured data with confidence scores
        return {
            "parsed_data": model.model_validate(response.choices[0].message.parsed),
            "confidence_scores": response.choices[0].logprobs,
            "token_usage": response.usage
        }

class InstructorParser:
    """Use instructor for models without logprobs support."""

    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = instructor.from_openai(openrouter_client.client)

    async def parse(
        self,
        model: Type[BaseModel],
        prompt: str,
        config: AgentConfig
    ) -> dict:
        """Parse using instructor with Pydantic model directly."""
        response = await self.client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_model=model,
            **config.model_parameters
        )

        return {
            "parsed_data": response,
            "confidence_scores": None,  # Not available without logprobs
            "token_usage": getattr(response, '_raw_response', {}).get('usage')
        }

class OutputParserFactory:
    """Factory for creating appropriate parser based on model capabilities."""

    def __init__(self, openrouter_client: OpenRouterClient):
        self.openrouter_client = openrouter_client

    def create_parser(self, model_name: str) -> Union[StructuredLogProbsParser, InstructorParser]:
        """Create parser based on model capabilities."""
        capabilities = MODEL_CAPABILITIES.get(model_name)

        if capabilities and capabilities.supports_logprobs:
            return StructuredLogProbsParser(self.openrouter_client)
        else:
            return InstructorParser(self.openrouter_client)
```

### Infrastructure Output Models

```python
# infrastructure/structured_output/models.py
from pydantic import BaseModel, Field
from typing import Optional

class BaseReasoningOutput(BaseModel):
    """Base class for all reasoning approach output models."""
    answer: str = Field(description="Final answer from reasoning process")

    class Config:
        schema_extra = {
            "required": ["answer"],
            "additionalProperties": False
        }

class DirectAnswerOutput(BaseReasoningOutput):
    """Infrastructure model for None agent structured output."""
    pass

class ChainOfThoughtOutput(BaseReasoningOutput):
    """Infrastructure model for Chain of Thought structured output."""
    reasoning: str = Field(description="Step-by-step reasoning process")
```

### ReasoningInfrastructureService Integration

```python
# infrastructure/reasoning_service.py
class ReasoningInfrastructureService:
    """Infrastructure service executing domain reasoning strategies."""

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        error_mapper: OpenRouterErrorMapper
    ):
        self.openrouter_client = openrouter_client
        self.error_mapper = error_mapper
        self.parser_factory = OutputParserFactory(openrouter_client)

    async def execute_reasoning(
        self,
        domain_service: ReasoningAgentService,
        question: Question,
        config: AgentConfig
    ) -> Union[Answer, FailureReason]:
        """Execute domain reasoning strategy with structured output parsing."""
        try:
            # Domain: Get prompt strategy and output model mapping
            prompt_strategy = domain_service.get_prompt_strategy()
            output_model = self._get_output_model(domain_service.get_agent_type())

            # Domain: Build base prompt
            base_prompt = prompt_strategy.build_prompt(question)

            # Infrastructure: Get model-specific parser
            parser = self.parser_factory.create_parser(config.model_name)

            # Infrastructure: Parse with structured output
            start_time = time.time()
            parse_result = await parser.parse(output_model, base_prompt, config)
            execution_time = time.time() - start_time

            # Domain: Process structured data into domain result
            processing_metadata = {
                "execution_time": execution_time,
                "token_usage": parse_result.get("token_usage")
            }

            reasoning_result = domain_service.process_result(
                self._convert_to_domain_format(parse_result["parsed_data"]),
                processing_metadata
            )

            # Infrastructure: Convert to Answer value object
            return self._convert_to_answer(reasoning_result)

        except Exception as e:
            # Infrastructure: Map external errors to domain failures
            return self.error_mapper.map_to_failure_reason(e)

    def _get_output_model(self, agent_type: str) -> Type[BaseReasoningOutput]:
        """Map domain agent type to infrastructure output model."""
        mapping = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput
        }
        return mapping.get(agent_type, DirectAnswerOutput)

    def _convert_to_domain_format(self, pydantic_output: BaseReasoningOutput) -> dict:
        """Convert infrastructure Pydantic model to domain-compatible format."""
        return {
            "final_answer": pydantic_output.answer,
            "reasoning_text": getattr(pydantic_output, 'reasoning', ''),
        }

    def _convert_to_answer(self, result: ReasoningResult) -> Answer:
        """Convert domain result to Answer value object."""
        return Answer(
            extracted_answer=result.get_answer(),
            reasoning_trace=result.get_reasoning_trace(),
            execution_time=result.execution_metadata.get("execution_time", 0.0),
            token_usage=result.execution_metadata.get("token_usage"),
            raw_response=str(result.final_answer)
        )
```

## DET-Inspired Infrastructure Patterns

### Configuration Externalization

```python
# infrastructure/prompt_config.py (Future Enhancement)
{
    "none": {
        "system_prompt": "You are a helpful assistant that provides direct, concise answers.",
        "user_prompt_template": "Answer the following question directly:\n{question_text}",
        "output_model": "DirectAnswerOutput",
        "model_defaults": {"temperature": 0.1, "max_tokens": 800}
    },
    "chain_of_thought": {
        "system_prompt": "You are a helpful assistant that thinks step by step.",
        "user_prompt_template": "Think through this question step by step:\n{question_text}",
        "output_model": "ChainOfThoughtOutput",
        "model_defaults": {"temperature": 0.8, "max_tokens": 1000}
    }
}
```

### Enhanced Error Handling

```python
# infrastructure/error_handling.py
class ResponseGenerationError(Exception):
    """Enhanced error for response generation failures."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

class RetryManager:
    """Retry logic for API failures."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except (RateLimitError, APITimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise ResponseGenerationError(f"Max retries exceeded: {e}")

                wait_time = self.backoff_factor ** attempt
                await asyncio.sleep(wait_time)
```

### Dynamic Model Loading

```python
# infrastructure/dynamic_import.py (Future Enhancement)
def dynamic_import(module_path: str):
    """Dynamically import class from string path."""
    module_name, class_name = module_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

class EnhancedReasoningAgentFactory:
    """Enhanced factory with dynamic loading capability."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._load_agent_configs()

    def _load_agent_configs(self):
        """Load agent configurations from external file."""
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.agent_configs = json.load(f)

    def create_service(self, agent_type: str) -> ReasoningAgentService:
        """Create service with dynamic loading support."""
        config = self.agent_configs.get(agent_type)
        if config and 'service_class' in config:
            service_class = dynamic_import(config['service_class'])
            return service_class()

        # Fallback to hardcoded factory
        return super().create_service(agent_type)
```

## OpenRouter Integration

### API Client Configuration

OpenRouter provides a unified API compatible with OpenAI SDK, using Bearer token authentication and base URL https://openrouter.ai/api/v1.

```python
# infrastructure/openrouter_client.py
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Optional, Dict, Any
import structlog
import httpx

class OpenRouterConfig(BaseModel):
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 60
    max_retries: int = 3
    app_name: Optional[str] = "ML-Agents-v2"
    app_url: Optional[str] = None

class OpenRouterClient:
    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries
        )
        self.http_client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
            headers={"Authorization": f"Bearer {config.api_key}"}
        )
        self.logger = structlog.get_logger()

    def get_headers(self) -> Dict[str, str]:
        """OpenRouter-specific headers for app attribution"""
        headers = {}
        if self.config.app_name:
            headers["HTTP-Referer"] = self.config.app_url or "https://github.com/your-org/ml-agents-v2"
            headers["X-Title"] = self.config.app_name
        return headers

    async def chat_completion(
        self,
        model: str,
        messages: list,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute chat completion with OpenRouter"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                extra_headers=self.get_headers(),
                **kwargs
            )
            return response
        except Exception as e:
            self.logger.error("OpenRouter API error", error=str(e), model=model)
            raise

    async def get_generation_details(self, generation_id: str) -> Dict[str, Any]:
        """Retrieve detailed token usage and cost information"""
        response = await self.http_client.get(f"{self.config.base_url}/generation/{generation_id}")
        return response.json()

    async def close(self):
        """Clean up async resources"""
        await self.client.close()
        await self.http_client.aclose()
```

### Error Mapping

OpenRouter normalizes errors and provides specific error codes including 402 for credit balance issues and rate limiting controls.

```python
# infrastructure/error_mapping.py
from domain.value_objects import FailureReason, FailureCategory
from openai import APIError, RateLimitError, APITimeoutError
import structlog

class OpenRouterErrorMapper:
    @staticmethod
    def map_to_failure_reason(error: Exception) -> FailureReason:
        """Map OpenRouter/OpenAI errors to domain FailureReason"""

        if isinstance(error, RateLimitError):
            return FailureReason(
                category=FailureCategory.RATE_LIMIT_EXCEEDED,
                description="Rate limit exceeded",
                technical_details=str(error),
                recoverable=True
            )

        if isinstance(error, APITimeoutError):
            return FailureReason(
                category=FailureCategory.NETWORK_TIMEOUT,
                description="Request timed out",
                technical_details=str(error),
                recoverable=True
            )

        if isinstance(error, APIError):
            if error.status_code == 402:
                return FailureReason(
                    category=FailureCategory.CREDIT_LIMIT_EXCEEDED,
                    description="Insufficient credits",
                    technical_details=str(error),
                    recoverable=False
                )
            elif error.status_code == 400:
                return FailureReason(
                    category=FailureCategory.PARSING_ERROR,
                    description="Invalid request format",
                    technical_details=str(error),
                    recoverable=False
                )
            elif error.status_code in [401, 403]:
                return FailureReason(
                    category=FailureCategory.AUTHENTICATION_ERROR,
                    description="Authentication failed",
                    technical_details=str(error),
                    recoverable=False
                )

        return FailureReason(
            category=FailureCategory.UNKNOWN,
            description="Unexpected error",
            technical_details=str(error),
            recoverable=False
        )
```

## Configuration Management

### 12-Factor App Configuration

```python
# config/application_config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, Any

class ApplicationConfig(BaseSettings):
    """12-Factor App configuration using environment variables"""

    # Database Configuration
    database_url: str = Field(default="sqlite:///ml_agents_v2.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # OpenRouter Configuration
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    openrouter_timeout: int = Field(default=60, env="OPENROUTER_TIMEOUT")
    openrouter_max_retries: int = Field(default=3, env="OPENROUTER_MAX_RETRIES")

    # Application Settings
    app_name: str = Field(default="ML-Agents-v2", env="APP_NAME")
    app_url: Optional[str] = Field(default=None, env="APP_URL")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Performance Settings
    max_concurrent_evaluations: int = Field(default=1, env="MAX_CONCURRENT_EVALUATIONS")
    question_timeout_seconds: int = Field(default=30, env="QUESTION_TIMEOUT")

    # Development Settings
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Load configuration
def get_config() -> ApplicationConfig:
    return ApplicationConfig()
```

### Environment Configuration Files

**.env.example**

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT=60

# Database Configuration
DATABASE_URL=sqlite:///ml_agents_v2.db
DATABASE_ECHO=false

# Application Settings
APP_NAME=ML-Agents-v2
LOG_LEVEL=INFO
DEBUG_MODE=false

# Performance Tuning
MAX_CONCURRENT_EVALUATIONS=1
QUESTION_TIMEOUT=30
```

**.env.development**

```bash
DATABASE_URL=sqlite:///ml_agents_v2_dev.db
DATABASE_ECHO=true
LOG_LEVEL=DEBUG
DEBUG_MODE=true
```

**.env.production**

```bash
DATABASE_URL=postgresql://user:pass@prod-host:5432/ml_agents_v2
LOG_LEVEL=INFO
DEBUG_MODE=false
MAX_CONCURRENT_EVALUATIONS=3
```

## Database Infrastructure

### SQLite Development Setup

```python
# infrastructure/database.py
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config.application_config import ApplicationConfig
import structlog

class DatabaseManager:
    def __init__(self, config: ApplicationConfig):
        self.config = config
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.logger = structlog.get_logger()

    def _create_engine(self) -> Engine:
        """Create database engine with appropriate settings"""
        engine_kwargs = {
            "echo": self.config.database_echo,
        }

        # SQLite-specific optimizations
        if self.config.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "pool_pre_ping": True,
                "connect_args": {"check_same_thread": False}
            })

        return create_engine(self.config.database_url, **engine_kwargs)

    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all database tables"""
        from domain.models import Base
        Base.metadata.create_all(self.engine)
```

### Migration Management

```bash
# Initialize Alembic for migrations
uv run alembic init migrations

# Generate migration
uv run alembic revision --autogenerate -m "Initial schema"

# Apply migrations
uv run alembic upgrade head
```

## Logging Infrastructure

### Structured Logging Configuration

```python
# infrastructure/logging_config.py
import structlog
import logging
from config.application_config import ApplicationConfig

def configure_logging(config: ApplicationConfig):
    """Configure structured logging for the application"""

    log_level = getattr(logging, config.log_level.upper())

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s"
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer() if config.debug_mode
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

## Service Container and Dependency Injection

### Container Configuration

```python
# infrastructure/container.py
from dependency_injector import containers, providers
from config.application_config import ApplicationConfig, get_config
from infrastructure.database import DatabaseManager
from infrastructure.openrouter_client import OpenRouterClient, OpenRouterConfig
from infrastructure.reasoning_service import ReasoningInfrastructureService
from application.services import EvaluationOrchestrator, BenchmarkProcessor
from domain.services import ReasoningAgentServiceFactory

class Container(containers.DeclarativeContainer):
    """Dependency injection container"""

    # Configuration
    config = providers.Singleton(get_config)

    # Infrastructure
    database = providers.Singleton(
        DatabaseManager,
        config=config
    )

    openrouter_client = providers.Singleton(
        OpenRouterClient,
        config=providers.Factory(
            OpenRouterConfig,
            api_key=config.provided.openrouter_api_key,
            base_url=config.provided.openrouter_base_url,
            timeout_seconds=config.provided.openrouter_timeout,
            max_retries=config.provided.openrouter_max_retries,
            app_name=config.provided.app_name,
            app_url=config.provided.app_url
        )
    )

    reasoning_infrastructure_service = providers.Singleton(
        ReasoningInfrastructureService,
        openrouter_client=openrouter_client,
        error_mapper=providers.Factory(OpenRouterErrorMapper)
    )

    # Domain Services
    reasoning_service_factory = providers.Singleton(
        ReasoningAgentServiceFactory
    )

    # Application Services
    evaluation_orchestrator = providers.Factory(
        EvaluationOrchestrator,
        config=config,
        database=database,
        reasoning_service_factory=reasoning_service_factory,
        reasoning_infrastructure_service=reasoning_infrastructure_service
    )

    benchmark_processor = providers.Factory(
        BenchmarkProcessor,
        config=config,
        database=database
    )
```

## Model Access and Capabilities

### Available Models Discovery

OpenRouter provides endpoints to list available models and their supported parameters.

```python
# infrastructure/model_registry.py
from typing import List, Dict, Any
import structlog

class ModelRegistry:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client
        self.logger = structlog.get_logger()
        self._model_cache = {}

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenRouter"""
        try:
            response = await self.client.get("/models")
            models = response.json()["data"]
            self._model_cache = {model["id"]: model for model in models}
            return models
        except Exception as e:
            self.logger.error("Failed to fetch models", error=str(e))
            raise

    def supports_structured_output(self, model_id: str) -> bool:
        """Check if model supports structured output"""
        model = self._model_cache.get(model_id)
        if not model:
            return False
        return "response_format" in model.get("supported_parameters", [])

    def get_context_length(self, model_id: str) -> int:
        """Get model context length"""
        model = self._model_cache.get(model_id)
        return model.get("context_length", 4096) if model else 4096
```

## Monitoring and Health Checks

### Health Check Endpoints

```python
# infrastructure/health.py
from pydantic import BaseModel
from typing import Dict, Any
import structlog

class HealthStatus(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, Any]

class HealthChecker:
    def __init__(self, container: Container):
        self.container = container
        self.logger = structlog.get_logger()

    async def check_health(self) -> HealthStatus:
        """Perform comprehensive health check"""
        checks = {}

        # Database connectivity
        try:
            with self.container.database().get_session() as session:
                session.execute("SELECT 1")
            checks["database"] = {"status": "healthy"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}

        # OpenRouter connectivity
        try:
            response = await self.container.openrouter_client().client.get("/key")
            checks["openrouter"] = {"status": "healthy", "credits": response.get("credit_left")}
        except Exception as e:
            checks["openrouter"] = {"status": "unhealthy", "error": str(e)}

        # Determine overall status
        all_healthy = all(check["status"] == "healthy" for check in checks.values())
        overall_status = "healthy" if all_healthy else "unhealthy"

        return HealthStatus(status=overall_status, checks=checks)
```

## Security Considerations

### API Key Management

- Store API keys in environment variables only
- Use different keys for development/staging/production
- Implement key rotation procedures
- Monitor for key exposure in logs

### Benchmark Registry

The benchmark naming system uses a hardcoded registry for mapping user-friendly names to dataset files.

```python
# infrastructure/database/repositories/benchmark_repository_impl.py
BENCHMARK_REGISTRY = {
    "GPQA": "BENCHMARK-01-GPQA.csv",
    "FOLIO": "BENCHMARK-05-FOLIO.csv",
    "BBEH": "BENCHMARK-06-BBEH.csv",
    "MATH3": "BENCHMARK-07-MATH3.csv",
    "LeetCode_Python_Easy": "BENCHMARK-08-LeetCode_Python_Easy.csv"
}

class BenchmarkRepositoryImpl:
    def get_by_name(self, name: str) -> PreprocessedBenchmark:
        """Map short name to filename, fallback to name if not found"""
        filename = BENCHMARK_REGISTRY.get(name, name)
        # Load from filesystem/database using filename
        return self._load_benchmark(filename)

    def list_available_names(self) -> List[str]:
        """Return list of user-friendly benchmark names"""
        return list(BENCHMARK_REGISTRY.keys())
```

**Design Rationale:**

- **Simple for v2**: No database complexity for mapping table
- **Easy to extend**: Add new benchmarks by updating the constant
- **Clear error handling**: Fallback to name if not in registry
- **User-friendly**: CLI accepts short names like "GPQA" instead of full filenames

### Data Privacy

OpenRouter supports data collection policies and provider filtering to comply with privacy requirements.

```python
# Configure data privacy settings
openrouter_privacy_config = {
    "provider": {
        "data_collection": "deny",  # Exclude providers that store data
        "require_parameters": True   # Only use providers supporting all parameters
    }
}
```

## Performance Optimizations

### Connection Pooling

- SQLite: Use WAL mode for concurrent reads
- PostgreSQL: Configure connection pool size
- OpenRouter: Reuse HTTP connections

### Caching Strategy

- Model metadata caching (24 hours)
- Configuration caching at startup
- Results caching for completed evaluations

---

## See Also

- **[Data Model](v2-data-model.md)** - Database schema requiring these infrastructure components
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service patterns using these infrastructure integrations
- **[Project Structure](v2-project-structure.md)** - Infrastructure layer organization and dependency injection
- **[CLI Design](v2-cli-design.md)** - CLI framework and user interface dependencies
- **[Reasoning Domain Logic](v2-reasoning-domain-logic.md)** - Domain logic patterns integrated with infrastructure parsing strategies
