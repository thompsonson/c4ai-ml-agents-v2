"""LangChain parsing client (placeholder - deferred in Phase 9).

This parser was deferred in Phase 9 as lower priority.
The Marvin parser provides equivalent post-processing functionality.
"""

from typing import Any

from ....core.domain.services.llm_client import LLMClient
from ....core.domain.value_objects.answer import ParsedResponse


class LangChainParsingClient(LLMClient):
    """Placeholder for LangChain parsing strategy.

    This parser was deferred in Phase 9. Use MarvinParsingClient instead,
    which provides equivalent post-processing functionality.
    """

    def __init__(self, base_client: LLMClient):
        """Initialize placeholder client."""
        self.base_client = base_client
        raise NotImplementedError(
            "LangChain parser was deferred in Phase 9. "
            "Use MarvinParsingClient for post-processing structured output extraction."
        )

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Not implemented."""
        raise NotImplementedError("LangChain parser was deferred in Phase 9")
