# Structured Output Parsing Types

**Version:** 2.0
**Date:** 2025-09-28
**Purpose:** Simple type standardization at API boundary

## Problem

External APIs return inconsistent types:

```python
# OpenAI SDK: Pydantic model with .model_dump()
response.usage: openai.types.CompletionUsage

# OpenRouter passthrough: Plain dictionary
response.usage: dict

# Some providers: No usage data
response.usage: None
```

This forces conditional type handling throughout the codebase.

## Solution

**Standardize at the infrastructure boundary.** Convert all external API responses to consistent internal types immediately upon receipt.

## Domain Value Objects

**Note**: These are proper domain value objects with business logic, not simple dataclasses. See [v2-domain-model.md](v2-domain-model.md) for complete specifications.

```python
@dataclass(frozen=True)
class TokenUsage:
    """Domain value object with validation and business methods."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        # Business rule validation
        if self.prompt_tokens < 0 or self.completion_tokens < 0 or self.total_tokens < 0:
            raise ValueError("Token counts cannot be negative")
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")

    def to_dict(self) -> dict[str, int]:
        """Serialize for storage and reporting."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> 'TokenUsage | None':
        """Factory method for creating from various input formats."""
        if data is None:
            return None
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )

@dataclass(frozen=True)
class ParsedResponse:
    """Domain value object with business methods."""
    content: str
    structured_data: dict | None = None
    token_usage: TokenUsage | None = None

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("Response content cannot be empty")

    def has_structured_data(self) -> bool:
        """Check if response includes parsed structured output."""
        return self.structured_data is not None

    def get_token_count(self) -> int:
        """Extract total tokens, handling None gracefully."""
        if self.token_usage is None:
            return 0
        return self.token_usage.total_tokens
```

## Implementation

### OpenRouterClient: The ONLY Normalization Point

**Critical**: ALL type normalization happens here and ONLY here. No other components perform type conversion.

```python
class OpenRouterClient(LLMClient):  # Implements domain interface
    """Anti-Corruption Layer - the ONLY point where external types are normalized."""

    async def chat_completion(self, model: str, messages: list, **kwargs) -> ParsedResponse:
        """THE boundary where external API chaos becomes domain order."""
        # External API call (last place external types exist)
        api_response = await self.client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )

        # IMMEDIATELY normalize to domain types - external types die here
        return ParsedResponse(
            content=api_response.choices[0].message.content or "",
            structured_data=getattr(api_response.choices[0].message, 'parsed', None),
            token_usage=self._normalize_usage(api_response.usage)
        )

    def _normalize_usage(self, usage_data) -> TokenUsage | None:
        """THE method that handles ALL external token usage formats.

        This is the ONLY place in the system that deals with external usage types.
        """
        if not usage_data:
            return None

        # Handle external type variations
        if hasattr(usage_data, 'model_dump'):
            # OpenAI SDK Pydantic model
            data = usage_data.model_dump(mode='json')
        elif isinstance(usage_data, dict):
            # OpenRouter passthrough dict
            data = usage_data
        else:
            # Unknown format - log warning but don't crash
            import warnings
            warnings.warn(f"Unexpected token usage type: {type(usage_data)}")
            return None

        # Use domain factory method for creation
        return TokenUsage.from_dict(data)
```

### Parser Layer: No Normalization Needed

**Key**: Parsers now work with pure domain types since OpenRouterClient handles ALL normalization.

```python
class StructuredOutputParsingService:
    """Clean parser - works only with domain types from LLMClient."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client  # Domain interface - already normalized

    async def parse_with_structure(
        self,
        model: str,
        messages: list,
        output_schema: Type[BaseModel],
        **kwargs
    ) -> ParsedResponse:
        """Parse using structured output - returns clean domain types.

        NO normalization logic here - that's handled by LLMClient implementation.
        """
        # Add structured output parameters if model supports it
        if self._supports_structured_output(model):
            kwargs['response_format'] = self._pydantic_to_json_schema(output_schema)
            kwargs['logprobs'] = True

        # Call through domain interface - gets normalized ParsedResponse
        parsed_response = await self.llm_client.chat_completion(model, messages, **kwargs)

        # Validate structured data if present
        if parsed_response.has_structured_data():
            validated_data = output_schema.model_validate(parsed_response.structured_data)
            # Return new ParsedResponse with validated data
            return ParsedResponse(
                content=parsed_response.content,
                structured_data=validated_data.model_dump(),
                token_usage=parsed_response.token_usage  # Already domain TokenUsage
            )

        return parsed_response  # Already normalized by LLMClient

    def _supports_structured_output(self, model: str) -> bool:
        """Check if model supports native structured output."""
        return model.startswith(('gpt-', 'openai/gpt-'))

    def _pydantic_to_json_schema(self, model: Type[BaseModel]) -> dict:
        """Convert Pydantic model to structured output format."""
        schema = model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__.lower(),
                "description": model.__doc__ or f"Schema for {model.__name__}",
                "schema": schema,
                "strict": True,
            },
        }
```

## Benefits

- **Single source of truth**: ALL type conversion happens ONLY in OpenRouterClient
- **Consistent downstream types**: Parsers and services work with predictable domain interfaces
- **Zero conditional type handling**: Eliminates ALL `hasattr(usage, 'model_dump')` checks throughout system
- **Perfect domain isolation**: Domain and application layers never see external API types
- **Simplified testing**: Mock domain interfaces with known domain types
- **Future-proof**: External API changes isolated to one translation point

## Migration Strategy

### Phase 1: Consolidate Normalization
1. ✅ Move ALL normalization logic to OpenRouterClient._normalize_usage()
2. ✅ Remove normalization from all parser classes
3. ✅ Remove utility functions like `safe_model_dump()` and scattered `normalize_token_usage()`

### Phase 2: Domain Interface Consistency
4. ✅ Update OpenRouterClient to implement LLMClient domain interface
5. ✅ Update all application services to depend ONLY on LLMClient interface
6. ✅ Remove direct OpenRouterClient imports from application layer

### Phase 3: Rich Domain Value Objects
7. ✅ Implement full TokenUsage and ParsedResponse with business methods
8. ✅ Use domain factory methods (TokenUsage.from_dict()) instead of constructors
9. ✅ Add domain validation and business rules to value objects

### Phase 4: Test Cleanup
10. Delete complex mock scenarios testing type variations
11. Create simple domain interface mocks returning known domain types
12. Verify no external API types leak into domain/application tests

This approach eliminates external API type chaos through a single, well-defined Anti-Corruption Layer boundary.
