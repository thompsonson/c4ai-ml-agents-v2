"""Application configuration using 12-factor app principles."""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationConfig(BaseSettings):
    """12-Factor App configuration using environment variables.

    Loads configuration from environment variables with sensible defaults
    for development. Supports .env file loading for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///data/ml_agents_v2.db", description="Database connection URL"
    )
    database_echo: bool = Field(
        default=False, description="Enable SQLAlchemy query logging"
    )

    # Multi-Provider Configuration
    default_llm_provider: str = Field(
        default="openrouter",
        description="Default LLM provider (openrouter, openai, anthropic, litellm)",
    )

    # OpenRouter Configuration
    openrouter_api_key: str = Field(..., description="OpenRouter API key (required)")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter API base URL"
    )
    openrouter_timeout: int = Field(
        default=60, description="OpenRouter request timeout in seconds"
    )
    openrouter_max_retries: int = Field(
        default=3, description="Maximum retry attempts for OpenRouter requests"
    )

    # OpenAI Configuration (optional)
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key (optional)"
    )
    openai_timeout: int = Field(
        default=60, description="OpenAI request timeout in seconds"
    )
    openai_max_retries: int = Field(
        default=3, description="Maximum retry attempts for OpenAI requests"
    )

    # Anthropic Configuration (optional)
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key (optional)"
    )
    anthropic_timeout: int = Field(
        default=60, description="Anthropic request timeout in seconds"
    )

    # LiteLLM Configuration (optional, JSON format)
    litellm_config: dict[str, Any] | None = Field(
        default=None, description="LiteLLM configuration dictionary"
    )

    # Application Settings
    app_name: str = Field(
        default="ML-Agents-v2",
        description="Application name for OpenRouter attribution",
    )
    app_url: str | None = Field(
        default=None, description="Application URL for OpenRouter attribution"
    )
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Performance Settings
    max_concurrent_evaluations: int = Field(
        default=1, description="Maximum concurrent evaluation executions"
    )
    question_timeout_seconds: int = Field(
        default=30, description="Timeout for individual question processing"
    )

    # Development Settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")

    # Parsing Strategy
    parsing_strategy: str = Field(
        default="auto",
        description="Structured output parsing strategy: 'auto', 'marvin', 'outlines'",
    )

    # Agent Default Parameters
    none_agent_defaults: dict[str, Any] = Field(
        default_factory=lambda: {"temperature": 0.1, "max_tokens": 800},
        description="Default parameters for None reasoning agent",
    )
    cot_agent_defaults: dict[str, Any] = Field(
        default_factory=lambda: {"temperature": 0.8, "max_tokens": 1000},
        description="Default parameters for Chain of Thought agent",
    )
    tot_agent_defaults: dict[str, Any] = Field(
        default_factory=lambda: {
            "temperature": 0.9,
            "max_tokens": 1500,
            "tree_depth": 3,
            "branches_per_step": 4,
            "evaluation_method": "vote",
            "pruning_threshold": 0.3,
            "backtrack_on_failure": True,
            "max_evaluations": 20,
        },
        description="Default parameters for Tree of Thought agent",
    )


def get_config() -> ApplicationConfig:
    """Load and return application configuration.

    Returns:
        ApplicationConfig instance with values loaded from environment

    Raises:
        ValidationError: If required environment variables are missing
    """
    return ApplicationConfig()  # type: ignore[call-arg]
