"""Repository interfaces for data persistence."""

from .evaluation_repository import EvaluationRepository
from .exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryConnectionError,
    RepositoryError,
    RepositoryTransactionError,
)
from .preprocessed_benchmark_repository import PreprocessedBenchmarkRepository

__all__ = [
    "EvaluationRepository",
    "PreprocessedBenchmarkRepository",
    "RepositoryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "RepositoryConnectionError",
    "RepositoryTransactionError",
]
