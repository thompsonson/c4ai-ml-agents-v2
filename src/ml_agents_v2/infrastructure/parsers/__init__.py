"""Parsing strategy wrappers for structured output extraction.

This package contains parsing strategies that wrap base LLM clients to add
structured output capabilities through different approaches (Marvin post-processing,
Outlines constrained generation, native structured output).

Note: LangChain and Instructor parsers are placeholders (deferred in Phase 9).
"""

from .instructor import InstructorParsingClient
from .langchain import LangChainParsingClient
from .marvin import MarvinParsingClient
from .native import NativeParsingClient
from .outlines import OutlinesParsingClient

__all__ = [
    "MarvinParsingClient",
    "NativeParsingClient",
    "OutlinesParsingClient",
    "LangChainParsingClient",
    "InstructorParsingClient",
]
