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

## Anti-Corruption Layer for LLM Integration

### Overview

The infrastructure layer implements an Anti-Corruption Layer (ACL) that protects the domain from external LLM API complexity and type variations. This layer ensures consistent domain types regardless of underlying provider differences (OpenRouter, OpenAI, Anthropic, LiteLLM) and parsing strategies (Marvin, Outlines, LangChain, Instructor).

**Key Principles:**
- **Immediate Translation**: Convert external API responses to domain types at the boundary
- **Type Isolation**: Domain and application layers never import external API types
- **Consistent Interface**: All LLM providers return standardized domain `ParsedResponse` objects
- **Error Translation**: Map external API errors to domain `FailureReason` objects

### Domain Interface Implementation

```python
# infrastructure/llm/openrouter_client.py
from core.domain.services.llm_client import LLMClient
from core.domain.value_objects.parsed_response import ParsedResponse
from openai import AsyncOpenAI
from typing import List, Dict, Any
import warnings

class OpenRouterClient(LLMClient):
    """Anti-Corruption Layer implementing domain LLMClient interface.

    Protects domain from OpenRouter/OpenAI API implementation details by
    translating all external types to domain value objects immediately.
    """

    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries
        )

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ParsedResponse:
        """Execute chat completion and return domain ParsedResponse.

        This method acts as the Anti-Corruption Layer boundary - it handles
        all external API complexity and returns only domain types.
        """
        try:
            # External API call (infrastructure concern)
            api_response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                extra_headers=self._get_headers(),
                **kwargs
            )

            # Immediate translation to domain types (ACL responsibility)
            return self._translate_to_domain(api_response)

        except Exception as e:
            # Map external exceptions to domain failures
            raise self._map_external_error(e)

    def _translate_to_domain(self, api_response) -> ParsedResponse:
        """Convert external API response to domain ParsedResponse.

        Handles all external API response format variations and normalizes
        to consistent domain representation.
        """
        # Extract content (handling different response formats)
        content = api_response.choices[0].message.content or ""

        # Extract structured data if available
        structured_data = getattr(
            api_response.choices[0].message, 'parsed', None
        )

        return ParsedResponse(
            content=content,
            structured_data=structured_data
        )

    def _map_external_error(self, error: Exception) -> Exception:
        """Map external API errors to domain exceptions."""
        # This would map to domain exception types
        # Implementation depends on domain error hierarchy
        raise error  # Placeholder - should map to domain exceptions
```

### Model Capability-Based Parsing Strategy

```python
# infrastructure/structured_output/parsing_factory.py
from core.domain.value_objects.parsed_response import ParsedResponse
from typing import Type
from pydantic import BaseModel

class StructuredOutputParsingService:
    """Service that handles structured output parsing with capability detection.

    Uses Anti-Corruption Layer principle - returns domain types only.
    All type normalization happens in LLMClient implementation, not here.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client  # Domain interface - ACL boundary already handled

    async def parse_with_structure(
        self,
        model: str,
        messages: List[Dict[str, str]],
        output_schema: Type[BaseModel],
        **kwargs
    ) -> ParsedResponse:
        """Parse LLM response with structured output constraints.

        Returns domain ParsedResponse regardless of underlying parsing strategy.
        """
        # Determine parsing strategy based on model capabilities
        if self._supports_native_structured_output(model):
            return await self._parse_with_structured_output(
                model, messages, output_schema, **kwargs
            )
        else:
            return await self._parse_with_instructor(
                model, messages, output_schema, **kwargs
            )

    async def _parse_with_structured_output(
        self,
        model: str,
        messages: List[Dict[str, str]],
        output_schema: Type[BaseModel],
        **kwargs
    ) -> ParsedResponse:
        """Use native structured output (OpenAI models)."""
        json_schema = self._pydantic_to_json_schema(output_schema)
        kwargs['response_format'] = json_schema
        kwargs['logprobs'] = True  # Enable confidence scoring

        # Call through domain interface - returns domain ParsedResponse
        return await self.llm_client.chat_completion(model, messages, **kwargs)

    async def _parse_with_instructor(
        self,
        model: str,
        messages: List[Dict[str, str]],
        output_schema: Type[BaseModel],
        **kwargs
    ) -> ParsedResponse:
        """Use instructor library (non-OpenAI models)."""
        # Implementation would use instructor but still return domain ParsedResponse
        # This maintains the Anti-Corruption Layer principle
        pass

    def _supports_native_structured_output(self, model: str) -> bool:
        """Check if model supports native structured output."""
        # OpenAI models support structured output
        return model.startswith(('gpt-', 'openai/gpt-'))

    def _pydantic_to_json_schema(self, model: Type[BaseModel]) -> dict:
        """Convert Pydantic model to OpenAI structured output format."""
        schema = model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__.lower(),
                "description": model.__doc__ or f"Schema for {model.__name__}",
                "schema": schema,
                "strict": True,
            },
        }
```

### Infrastructure Output Models

```python
# infrastructure/structured_output/models.py
from pydantic import BaseModel, Field, ConfigDict

class BaseReasoningOutput(BaseModel):
    """Infrastructure Pydantic model for LLM structured output parsing.

    These models are used only within the infrastructure layer for
    parsing external API responses. They are converted to domain
    types before crossing layer boundaries.
    """

    model_config = ConfigDict(
        json_schema_extra={"required": ["answer"], "additionalProperties": False}
    )

    answer: str = Field(description="Final answer from reasoning process")

class DirectAnswerOutput(BaseReasoningOutput):
    """Infrastructure model for None agent structured output."""
    pass

class ChainOfThoughtOutput(BaseReasoningOutput):
    """Infrastructure model for Chain of Thought structured output."""
    reasoning: str = Field(description="Step-by-step reasoning process")
```

### Integration with Domain Services

```python
# infrastructure/reasoning_service.py
from core.domain.services.llm_client import LLMClient
from core.domain.value_objects.parsed_response import ParsedResponse

class ReasoningInfrastructureService:
    """Infrastructure service that coordinates domain reasoning with LLM calls.

    Follows Anti-Corruption Layer principle by depending ONLY on domain interfaces.
    Never imports or depends on concrete infrastructure implementations.
    """

    def __init__(
        self,
        llm_client: LLMClient,  # Domain interface - ACL boundary handled in implementation
        error_mapper: DomainErrorMapper  # Domain interface for error translation
    ):
        self.llm_client = llm_client  # Domain interface only
        self.error_mapper = error_mapper  # Domain interface only
        self.parsing_service = StructuredOutputParsingService(llm_client)

    async def execute_reasoning(
        self,
        domain_service: ReasoningAgentService,
        question: Question,
        config: AgentConfig
    ) -> Answer | FailureReason:
        """Execute domain reasoning strategy with LLM integration.

        All external API complexity is handled by the Anti-Corruption Layer.
        This service works only with domain types.
        """
        try:
            # Domain: Generate prompt using domain logic
            prompt = domain_service.process_question(question, config)
            messages = [{"role": "user", "content": prompt}]

            # Infrastructure: Get output schema for structured parsing
            output_schema = self._get_output_schema(domain_service.get_agent_type())

            # Infrastructure: Execute LLM call through ACL
            start_time = time.time()
            parsed_response = await self.parsing_service.parse_with_structure(
                model=config.model_name,
                messages=messages,
                output_schema=output_schema,
                **config.model_parameters
            )
            execution_time = time.time() - start_time

            # Domain: Process response using domain logic
            processing_metadata = {
                "execution_time": execution_time,
            }

            reasoning_result = domain_service.process_response(
                parsed_response.content, processing_metadata
            )

            # Infrastructure: Convert to domain Answer
            return self._convert_to_answer(reasoning_result, execution_time)

        except Exception as e:
            # Infrastructure: Map external errors to domain failures using domain interface
            return self.error_mapper.map_to_failure_reason(e)

    def _get_output_schema(self, agent_type: str) -> Type[BaseReasoningOutput]:
        """Map domain agent type to infrastructure output schema."""
        mapping = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput,
        }
        return mapping.get(agent_type, DirectAnswerOutput)

    def _convert_to_answer(
        self,
        reasoning_result: Any,
        execution_time: float
    ) -> Answer:
        """Convert domain reasoning result to Answer value object."""
        return Answer(
            extracted_answer=reasoning_result.get_answer(),
            reasoning_trace=reasoning_result.get_reasoning_trace(),
            confidence=None,  # TODO: Add confidence extraction from logprobs
            execution_time=execution_time,
            raw_response=str(reasoning_result.final_answer),
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
            headers["HTTP-Referer"] = self.config.app_url or "https://github.com/thompsonson/ml-agents-v2"
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

### Anti-Corruption Layer Error Mapping

The error mapping component protects the domain from external API error variations by translating all external exceptions to domain `FailureReason` objects. This prevents external error types from leaking into domain or application layers.

```python
# infrastructure/error_mapping.py
from core.domain.value_objects.failure_reason import FailureReason, FailureCategory
from openai import APIError, RateLimitError, APITimeoutError
import structlog

class OpenRouterErrorMapper:
    """Anti-Corruption Layer for external API error translation.

    Maps all external API errors to domain FailureReason objects,
    ensuring no external exception types escape the infrastructure boundary.
    """

    @staticmethod
    def map_to_failure_reason(error: Exception) -> FailureReason:
        """Translate external API errors to domain FailureReason.

        This method acts as an Anti-Corruption Layer for error handling,
        ensuring domain and application layers never see external API
        exception types.

        Args:
            error: Any external API exception

        Returns:
            FailureReason: Domain representation of the failure
        """

        # OpenAI/OpenRouter specific error mappings
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

        # Generic error fallback - ensures no external exceptions escape
        return FailureReason(
            category=FailureCategory.UNKNOWN,
            description="Unexpected error",
            technical_details=str(error),
            recoverable=False
        )

    @staticmethod
    def is_recoverable_error(error: Exception) -> bool:
        """Determine if external error might succeed on retry.

        Uses domain logic to categorize external errors without
        exposing external error types to calling code.
        """
        failure_reason = OpenRouterErrorMapper.map_to_failure_reason(error)
        return failure_reason.recoverable
```

## Configuration Management

### 12-Factor App Configuration

```python
# config/application_config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, Any

class ApplicationConfig(BaseSettings):
    """12-Factor App configuration using environment variables for multi-provider support"""

    # Database Configuration
    database_url: str = Field(default="sqlite:///ml_agents_v2.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Multi-Provider LLM Configuration
    default_llm_provider: str = Field(default="openrouter", env="DEFAULT_LLM_PROVIDER")
    parsing_strategy: str = Field(default="auto", env="PARSING_STRATEGY")

    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    openrouter_timeout: int = Field(default=60, env="OPENROUTER_TIMEOUT")
    openrouter_max_retries: int = Field(default=3, env="OPENROUTER_MAX_RETRIES")

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_timeout: int = Field(default=60, env="OPENAI_TIMEOUT")

    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_timeout: int = Field(default=60, env="ANTHROPIC_TIMEOUT")

    # LiteLLM Configuration (can be complex JSON)
    litellm_config: Optional[Dict[str, Any]] = Field(default=None, env="LITELLM_CONFIG")

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
# Multi-Provider Configuration
DEFAULT_LLM_PROVIDER=openrouter
PARSING_STRATEGY=auto

# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT=60

# OpenAI API Configuration (optional)
# OPENAI_API_KEY=sk-your-openai-key-here
# OPENAI_TIMEOUT=60

# Anthropic API Configuration (optional)
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
# ANTHROPIC_TIMEOUT=60

# LiteLLM Configuration (optional, JSON format)
# LITELLM_CONFIG={"model": "ollama/llama2", "api_base": "http://localhost:11434"}

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

## Multi-Provider Factory Pattern

### Overview

To support multiple LLM providers (OpenRouter, OpenAI, Anthropic, LiteLLM) and multiple parsing strategies (Marvin, Outlines, LangChain, Instructor), the infrastructure implements a composite factory pattern that creates appropriate clients dynamically based on configuration.

### LLMClientFactory Implementation

```python
# infrastructure/factories/llm_client_factory.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.domain.services.llm_client import LLMClient, LLMClientFactory

class LLMClientFactoryImpl(LLMClientFactory):
    """Concrete implementation of LLMClientFactory for multi-provider support."""

    def __init__(
        self,
        provider_configs: Dict[str, Dict[str, Any]],
        default_provider: str = "openrouter",
        default_parsing_strategy: str = "auto"
    ):
        self.provider_configs = provider_configs
        self.default_provider = default_provider
        self.default_parsing_strategy = default_parsing_strategy

    def create_client(
        self,
        model_name: str,
        provider: str = None,
        parsing_strategy: str = "auto"
    ) -> LLMClient:
        """Create appropriate client for model and strategy combination."""
        # Auto-detect provider from model name if not specified
        if provider is None:
            provider = self._detect_provider(model_name)

        # Create base provider client
        base_client = self._create_provider_client(provider)

        # Wrap with parsing strategy
        return self._create_parsing_client(base_client, parsing_strategy, model_name)

    def _detect_provider(self, model_name: str) -> str:
        """Auto-detect provider from model name."""
        if model_name.startswith(("gpt-", "o1-")):
            return "openai"
        elif model_name.startswith(("claude-",)):
            return "anthropic"
        elif model_name.startswith(("llama-", "mixtral-")):
            return "openrouter"  # Default for open source models
        else:
            return self.default_provider

    def _create_provider_client(self, provider: str) -> LLMClient:
        """Create base LLM client for provider."""
        config = self.provider_configs[provider]

        if provider == "openrouter":
            return OpenRouterClient(
                api_key=config["api_key"],
                base_url=config["base_url"],
                timeout=config.get("timeout", 60),
                max_retries=config.get("max_retries", 3)
            )
        elif provider == "openai":
            return OpenAIClient(
                api_key=config["api_key"],
                timeout=config.get("timeout", 60)
            )
        elif provider == "anthropic":
            return AnthropicClient(
                api_key=config["api_key"],
                timeout=config.get("timeout", 60)
            )
        elif provider == "litellm":
            return LiteLLMClient(config)
        else:
            raise UnsupportedProviderError(f"Provider {provider} not supported")

    def _create_parsing_client(
        self, base_client: LLMClient, strategy: str, model_name: str
    ) -> LLMClient:
        """Wrap base client with parsing strategy."""
        if strategy == "auto":
            strategy = self._select_optimal_strategy(model_name)

        if strategy == "marvin":
            return MarvinParsingClient(base_client)
        elif strategy == "outlines":
            return OutlinesParsingClient(base_client)
        elif strategy == "langchain":
            return LangChainParsingClient(base_client)
        elif strategy == "instructor":
            return InstructorParsingClient(base_client)
        elif strategy == "native":
            return base_client  # Use provider's native structured output
        else:
            raise UnsupportedStrategyError(f"Strategy {strategy} not supported")

    def _select_optimal_strategy(self, model_name: str) -> str:
        """Select optimal parsing strategy based on model capabilities."""
        # OpenAI models support native structured output
        if model_name.startswith(("gpt-4", "gpt-3.5-turbo")):
            return "native"
        # Anthropic models work well with Marvin
        elif model_name.startswith("claude-"):
            return "marvin"
        # Open source models benefit from constrained generation
        else:
            return "outlines"
```

### Provider Client Implementations

Each provider implements the same domain interface while handling provider-specific details:

```python
# infrastructure/providers/openai_client.py
from openai import AsyncOpenAI
from core.domain.services.llm_client import LLMClient
from core.domain.value_objects.parsed_response import ParsedResponse

class OpenAIClient(LLMClient):
    """OpenAI provider implementation with native structured output support."""

    def __init__(self, api_key: str, timeout: int = 60):
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def chat_completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> ParsedResponse:
        """Execute OpenAI chat completion."""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return self._translate_to_domain(response)
        except Exception as e:
            raise self._map_provider_error(e)

# infrastructure/providers/anthropic_client.py
class AnthropicClient(LLMClient):
    """Anthropic provider implementation."""
    # Similar structure with Anthropic SDK

# infrastructure/providers/litellm_client.py
class LiteLLMClient(LLMClient):
    """LiteLLM provider for accessing 100+ models."""
    # Implements unified interface to multiple providers
```

### Parsing Strategy Implementations

Parsing strategies wrap base clients to add structured output capabilities:

```python
# infrastructure/parsers/marvin_client.py
import marvin
from core.domain.services.llm_client import LLMClient

class MarvinParsingClient(LLMClient):
    """Marvin post-processing parsing strategy."""

    def __init__(self, base_client: LLMClient):
        self.base_client = base_client

    async def chat_completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> ParsedResponse:
        """Execute completion with Marvin post-processing."""
        # Extract parsing context from kwargs
        agent_type = kwargs.pop("_internal_agent_type", "none")

        # Get natural language response
        response = await self.base_client.chat_completion(model, messages, **kwargs)

        # Post-process with Marvin to extract structured data
        try:
            output_schema = self._get_output_schema(agent_type)
            structured_data = await marvin.extract_async(
                response.content, target=output_schema
            )

            return ParsedResponse(
                content=response.content,
                structured_data=structured_data.model_dump(),
                token_usage=response.token_usage
            )
        except Exception:
            # Return original response if parsing fails
            return response
```

## Service Container and Dependency Injection

### Container Configuration

```python
# infrastructure/container.py
from dependency_injector import containers, providers
from config.application_config import ApplicationConfig, get_config
from infrastructure.database import DatabaseManager
from infrastructure.factories.llm_client_factory import LLMClientFactoryImpl
from infrastructure.reasoning_service import ReasoningInfrastructureService
from application.services import EvaluationOrchestrator, BenchmarkProcessor
from domain.services import ReasoningAgentServiceFactory

class Container(containers.DeclarativeContainer):
    """Dependency injection container with multi-provider factory pattern"""

    # Configuration
    config = providers.Singleton(get_config)

    # Infrastructure
    database = providers.Singleton(
        DatabaseManager,
        config=config
    )

    # Multi-provider LLM client factory
    llm_client_factory = providers.Singleton(
        LLMClientFactoryImpl,
        provider_configs=providers.Dict(
            openrouter=providers.Dict(
                api_key=config.provided.openrouter_api_key,
                base_url=config.provided.openrouter_base_url,
                timeout=config.provided.openrouter_timeout,
                max_retries=config.provided.openrouter_max_retries
            ),
            openai=providers.Dict(
                api_key=config.provided.openai_api_key,
                timeout=config.provided.openai_timeout.provided.or_(60)
            ),
            anthropic=providers.Dict(
                api_key=config.provided.anthropic_api_key,
                timeout=config.provided.anthropic_timeout.provided.or_(60)
            ),
            litellm=providers.Dict(
                # LiteLLM configuration can be complex, use provider configs
                config=config.provided.litellm_config.provided.or_({})
            )
        ),
        default_provider=config.provided.default_llm_provider.provided.or_("openrouter"),
        default_parsing_strategy=config.provided.parsing_strategy.provided.or_("auto")
    )

    reasoning_infrastructure_service = providers.Singleton(
        ReasoningInfrastructureService,
        llm_client_factory=llm_client_factory,
        error_mapper=providers.Factory(OpenRouterErrorMapper),
        parsing_strategy=config.provided.parsing_strategy.provided.or_("auto")
    )

    # Domain Services
    reasoning_service_factory = providers.Singleton(
        ReasoningAgentServiceFactory
    )

    # Application Services
    evaluation_orchestrator = providers.Factory(
        EvaluationOrchestrator,
        llm_client_factory=llm_client_factory,
        evaluation_repo=database.provided.evaluation_repository,
        question_result_repo=database.provided.question_result_repository,
        benchmark_repo=database.provided.benchmark_repository,
        reasoning_service_factory=reasoning_service_factory,
        config=config
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
