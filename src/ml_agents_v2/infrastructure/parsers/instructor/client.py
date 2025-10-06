"""Instructor parsing client (placeholder - deferred in Phase 9).

This parser was deferred in Phase 9 as lower priority.
The Marvin and Native parsers provide equivalent functionality.
"""

from typing import Any

from ....core.domain.services.llm_client import LLMClient
from ....core.domain.value_objects.answer import ParsedResponse


class InstructorParsingClient(LLMClient):
    """Placeholder for Instructor parsing strategy.

    This parser was deferred in Phase 9. Use MarvinParsingClient for
    post-processing or NativeParsingClient for OpenAI native structured output.
    """

    def __init__(self, base_client: LLMClient):
        """Initialize placeholder client."""
        self.base_client = base_client
        raise NotImplementedError(
            "Instructor parser was deferred in Phase 9. "
            "Use MarvinParsingClient for post-processing or "
            "NativeParsingClient for OpenAI native structured output."
        )

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Not implemented."""
        raise NotImplementedError("Instructor parser was deferred in Phase 9")
