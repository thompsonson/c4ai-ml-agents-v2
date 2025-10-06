"""Error mapper for LiteLLM provider.

Currently delegates to shared OpenRouterErrorMapper implementation.
Provider-specific error mapping can be added here in the future.
"""

from ..openrouter.error_mapper import OpenRouterErrorMapper

# Re-export for consistency
__all__ = ["OpenRouterErrorMapper"]
