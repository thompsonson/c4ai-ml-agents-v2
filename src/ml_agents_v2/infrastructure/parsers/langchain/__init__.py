"""LangChain parsing strategy implementation (deferred).

This parser was deferred in Phase 9 as lower priority.
The Marvin parser covers the same use case.
"""

from .client import LangChainParsingClient

__all__ = ["LangChainParsingClient"]
