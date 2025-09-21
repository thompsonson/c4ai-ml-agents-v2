"""Structured logging configuration for ML Agents v2."""

import logging
import sys
from typing import Any

import structlog

from ml_agents_v2.config.application_config import ApplicationConfig


def configure_logging(config: ApplicationConfig) -> None:
    """Configure structured logging for the application.

    Sets up both standard library logging and structlog with appropriate
    processors for development and production environments.

    Args:
        config: Application configuration containing log level and debug mode
    """
    log_level = getattr(logging, config.log_level.upper())

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure structlog processors based on environment
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
    ]

    # Choose renderer based on debug mode
    if config.debug_mode:
        # Development: human-readable console output
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Production: structured JSON output
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)
