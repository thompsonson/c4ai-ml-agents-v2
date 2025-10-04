"""Parsing strategy wrappers for structured output extraction.

This package contains parsing strategies that wrap base LLM clients to add
structured output capabilities through different approaches (Marvin post-processing,
Outlines constrained generation, native structured output).
"""

from .marvin_parser import MarvinParsingClient
from .native_parser import NativeParsingClient
from .outlines_parser import OutlinesParsingClient

__all__ = [
    "MarvinParsingClient",
    "NativeParsingClient",
    "OutlinesParsingClient",
]
