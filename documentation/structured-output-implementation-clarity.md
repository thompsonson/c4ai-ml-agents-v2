# Structured Output Implementation - Clarified Requirements

**Date:** 2025-10-03  
**Status:** Requirements Clarification  
**Purpose:** Understand the actual goal - replacing Instructor with Marvin/Outlines

## Corrected Understanding

### The Problem with Current Implementation

**Current (Instructor-based):**
```python
# PROBLEM: response_model parameter breaks domain boundary
response = await llm_client.chat_completion(
    model="anthropic/claude-3-sonnet",
    messages=[{"role": "user", "content": prompt}],
    response_model=DirectAnswerOutput,  # ❌ Infrastructure type leaking to domain interface
    **kwargs
)
```

**Why this is wrong:**
- `response_model` is a **Pydantic infrastructure type** (DirectAnswerOutput)
- Domain layer calls `llm_client.chat_completion()` which is a **domain interface**
- Domain should never pass infrastructure types through its own interfaces
- This violates the Anti-Corruption Layer principle

### The ADR's Actual Goal

**Replace Instructor with Marvin/Outlines to preserve domain boundaries:**

```python
# GOAL: Clean domain interface - no infrastructure types
response = await llm_client.chat_completion(
    model="anthropic/claude-3-sonnet",
    messages=[{"role": "user", "content": prompt}],  # ✅ Pure domain types only
    **kwargs  # ✅ No response_model parameter
)
# Infrastructure handles structured output parsing internally
```

### Why Marvin and Outlines?

**MarvinClient Approach (Post-Processing):**
- Domain calls LLM with clean prompts → gets text response
- Infrastructure uses Marvin to **post-process** the text into structured output
- Domain never knows about Pydantic models
- Clean separation of concerns

**OutlinesClient Approach (Constrained Generation):**
- Infrastructure configures Outlines to constrain token generation
- Domain calls LLM with clean prompts → gets guaranteed-structured text
- Infrastructure parses the structured text
- Domain never knows about schemas

## Current State Analysis

### What's Actually Implemented

**InstructorClient (src/ml_agents_v2/infrastructure/instructor/client.py):**
```python
# BREAKS DOMAIN BOUNDARY
async def chat_completion(
    self, model: str, messages: list[dict[str, str]], **kwargs: Any
) -> ParsedResponse:
    response_model = kwargs.pop("response_model", None)  # ❌ Infrastructure type in kwargs
    
    if response_model:
        result = self.instructor_client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=response_model,  # ❌ Pydantic model
            **kwargs
        )
```

**This is the problem the ADR aims to solve.**

### What Should Be Implemented

**MarvinClient (Post-Processing Approach):**
```python
# src/ml_agents_v2/infrastructure/marvin/client.py

import marvin  # type: ignore

class MarvinClient:
    """LLM client using Marvin for post-processing structured output extraction."""
    
    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion and post-process with Marvin.
        
        Domain calls this with clean prompts. Infrastructure handles
        structured output extraction transparently using Marvin.
        """
        # NO response_model parameter - domain boundary preserved
        
        # Call 1: Get natural language response from LLM
        response = await self.base_client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        
        content = response.choices[0].message.content
        
        # Call 2: Use Marvin to extract structured data from text
        # This happens INSIDE infrastructure - domain never sees it
        try:
            structured_data = marvin.extract(
                content,
                target=self._determine_output_schema(kwargs.get("_internal_agent_type"))
            )
            
            return ParsedResponse(
                content=content,
                structured_data=structured_data.model_dump()
            )
        except Exception:
            # Fallback to text-only response
            return ParsedResponse(content=content)
    
    def _determine_output_schema(self, agent_type: str) -> type:
        """Internal infrastructure logic to map agent type to schema.
        
        This is INSIDE infrastructure - domain never knows about it.
        """
        mapping = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput
        }
        return mapping.get(agent_type, DirectAnswerOutput)
```

**OutlinesClient (Constrained Generation Approach):**
```python
# src/ml_agents_v2/infrastructure/outlines/client.py

import outlines  # type: ignore

class OutlinesClient:
    """LLM client using Outlines for constrained generation."""
    
    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute constrained generation using Outlines.
        
        Domain provides clean prompt. Infrastructure configures
        Outlines to constrain generation to valid JSON structure.
        """
        # NO response_model parameter
        
        # Determine schema internally (infrastructure concern)
        schema = self._determine_output_schema(kwargs.get("_internal_agent_type"))
        
        # Configure Outlines generator with schema constraints
        generator = outlines.generate.json(
            self.llm_model,
            schema.model_json_schema()
        )
        
        # Generate with constraints - guaranteed valid structure
        prompt_text = self._format_messages(messages)
        result = generator(prompt_text)
        
        return ParsedResponse(
            content=result,
            structured_data=schema.model_validate_json(result).model_dump()
        )
```

## BDD Test Expectations - Now They Make Sense!

### Test: `test_instructor_parser_uses_instructor_library_for_structured_output`

```python
# This test is CORRECTLY asserting that domain boundary is preserved
assert "response_model" not in call_args.kwargs  # ✅ CORRECT
assert "You must respond with valid JSON..." not in prompt  # ✅ CORRECT
```

**What it's testing:**
- Domain interface should NOT have infrastructure types (response_model)
- Domain prompts should NOT have manual JSON schema instructions
- Infrastructure handles structured output **internally**

**This test currently fails because Instructor breaks the domain boundary.**

### Test: `test_structured_logprobs_uses_response_format`

```python
# For models supporting native structured output
assert "response_format" in call_args.kwargs
```

**This is different:** Some models (OpenAI) support native structured output via `response_format`. This is an LLM provider feature, not a domain type leak, so it's acceptable to pass through the domain interface.

**Key distinction:**
- `response_model=DirectAnswerOutput` ❌ Infrastructure Pydantic type crossing domain boundary
- `response_format={"type": "json_schema", ...}` ✅ LLM provider API parameter

## BDD Plan - Now It Makes Sense!

### Section 7.1: "InstructorParser adds schema instructions to API call"

```gherkin
Scenario: InstructorParser adds schema instructions to API call
  Then the LLM client should receive enhanced prompt
  And the prompt should contain "You must respond with valid JSON"
```

**This is describing the OLD instructor approach that should be REPLACED.**

The BDD plan is documenting what currently exists (Instructor with manual prompts) so we can test that the NEW approach (Marvin/Outlines) is different.

### The Test That Confused Me

```python
# Test line 222-225
assert "You must respond with valid JSON matching this exact schema" not in prompt_content
```

**This is the GOAL:** After implementing Marvin/Outlines, prompts should NOT contain manual JSON schema instructions because:
- **MarvinClient:** Gets natural language, post-processes into structure
- **OutlinesClient:** Constrains generation without prompt manipulation

## Corrected Implementation Plan

### Phase 1: Implement MarvinClient (Preserves Domain Boundary)

```python
# src/ml_agents_v2/infrastructure/marvin/client.py

class MarvinClient(LLMClient):  # Implements domain interface
    """Post-processing approach - preserves external prompts."""
    
    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        # Step 1: Normal LLM call - domain prompt unchanged
        response = await self._call_llm(model, messages, **kwargs)
        content = response.choices[0].message.content
        
        # Step 2: Post-process with Marvin (infrastructure-only)
        try:
            # Internal: Determine what structure we need
            agent_type = self._extract_internal_context(kwargs)
            target_schema = self._get_schema_for_agent(agent_type)
            
            # Marvin extracts structure from natural language
            structured = await marvin.extract_async(content, target=target_schema)
            
            return ParsedResponse(
                content=content,
                structured_data=structured.model_dump()
            )
        except Exception as e:
            # Parsing failure - return as text
            return ParsedResponse(content=content)
```

### Phase 2: Implement OutlinesClient (Constrained Generation)

```python
# src/ml_agents_v2/infrastructure/outlines/client.py

class OutlinesClient(LLMClient):  # Implements domain interface
    """Constrained generation - guarantees schema compliance."""
    
    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        # Internal: Determine schema
        agent_type = self._extract_internal_context(kwargs)
        schema = self._get_schema_for_agent(agent_type)
        
        # Configure Outlines for constrained generation
        generator = outlines.generate.json(
            self.model_instance,
            schema.model_json_schema()
        )
        
        # Generate - automatically constrained to valid JSON
        prompt = self._format_messages(messages)
        result = await generator(prompt)
        
        return ParsedResponse(
            content=result,
            structured_data=json.loads(result)
        )
```

### Phase 3: Update Factory Selection

```python
# src/ml_agents_v2/infrastructure/parsing_factory.py

class OutputParserFactory:
    def create_client(self, model_name: str, strategy: str = "auto") -> LLMClient:
        """Create client based on model capabilities and strategy preference."""
        
        if strategy == "marvin":
            return MarvinClient(self.api_key, self.base_url)
        elif strategy == "outlines":
            return OutlinesClient(self.api_key, self.base_url)
        elif strategy == "auto":
            if ModelCapabilitiesRegistry.supports_logprobs(model_name):
                # Use native structured output with confidence scores
                return StructuredLogProbsClient(self.api_key, self.base_url)
            elif ModelCapabilitiesRegistry.supports_constrained_generation(model_name):
                # Prefer constrained generation for efficiency
                return OutlinesClient(self.api_key, self.base_url)
            else:
                # Fallback to post-processing
                return MarvinClient(self.api_key, self.base_url)
```

## How to Pass Internal Context Without Breaking Domain Boundary

### The Problem
Infrastructure needs to know what schema to use (DirectAnswerOutput vs ChainOfThoughtOutput), but domain shouldn't pass infrastructure types.

### Solution: Internal Context Passing Pattern

```python
# Domain layer calls (in ReasoningInfrastructureService)
response = await self.llm_client.chat_completion(
    model=f"{config.model_provider}/{config.model_name}",
    messages=[{"role": "user", "content": domain_prompt}],
    _internal_agent_type=config.agent_type,  # String, not Pydantic type
    **config.model_parameters
)
```

**Key points:**
- `_internal_agent_type="chain_of_thought"` is a **string** (domain type)
- Infrastructure maps string → Pydantic schema internally
- Domain never imports or references DirectAnswerOutput or ChainOfThoughtOutput
- Underscore prefix signals "infrastructure internal use only"

### Inside Infrastructure

```python
# Infrastructure layer (MarvinClient)
def _get_schema_for_agent(self, agent_type: str) -> type[BaseModel]:
    """Map domain agent type to infrastructure schema.
    
    This is pure infrastructure logic - domain never sees it.
    """
    from ml_agents_v2.infrastructure.models import (
        DirectAnswerOutput,
        ChainOfThoughtOutput
    )
    
    mapping = {
        "none": DirectAnswerOutput,
        "chain_of_thought": ChainOfThoughtOutput
    }
    return mapping.get(agent_type, DirectAnswerOutput)
```

## Summary of Corrected Understanding

### What We're Removing
- ❌ InstructorClient (breaks domain boundary with `response_model` parameter)
- ❌ Manual JSON schema prompt injection
- ❌ Infrastructure types crossing domain interface

### What We're Adding
- ✅ MarvinClient (post-processing, preserves domain prompts)
- ✅ OutlinesClient (constrained generation, efficient)
- ✅ Clean domain interface with no infrastructure type leakage
- ✅ Internal context passing pattern (`_internal_agent_type`)

### BDD Tests Status
- **Currently failing:** ✅ This is expected! They test for the GOAL state
- **After Marvin/Outlines:** Tests should pass
- **Test expectations are correct:** They verify domain boundary preservation

## Next Steps

1. ✅ **Implement MarvinClient** - Post-processing approach, simpler to start
2. ✅ **Update BDD tests** to work with new client architecture
3. ✅ **Implement OutlinesClient** - Constrained generation for efficiency
4. ✅ **Update factory logic** - Select appropriate client by model capabilities
5. ✅ **Remove InstructorClient** - No longer needed, breaks boundaries
6. ✅ **Update documentation** - ADR is now correctly describing what to implement

**The ADR is correct. The BDD plan is correct. The failing tests are correct. The implementation is wrong (uses Instructor).**

Now we need to implement what the ADR specifies: Marvin and Outlines clients that preserve domain boundaries.
