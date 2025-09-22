"""Data transfer objects for application layer."""

from .benchmark_info import BenchmarkInfo
from .evaluation_info import EvaluationInfo
from .evaluation_summary import EvaluationSummary
from .progress_info import ProgressInfo
from .validation_result import ValidationResult

__all__ = [
    "BenchmarkInfo",
    "EvaluationInfo",
    "EvaluationSummary",
    "ProgressInfo",
    "ValidationResult",
]
