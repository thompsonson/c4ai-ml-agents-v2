# Reasoning Agent Domain Logic

**Version:** 1.0  
**Date:** 2025-09-23  
**Purpose:** Define domain logic boundaries for reasoning agent implementations

## Overview

Reasoning agents implement domain-specific business logic for different AI reasoning approaches. This document establishes clear boundaries between domain logic (prompt strategies, response processing) and infrastructure concerns (API calls, network handling).

## Domain Boundaries

### Domain Layer Responsibilities

**Core Business Logic:**

- Prompt engineering templates and construction rules
- Response parsing and answer extraction patterns
- Reasoning trace construction and validation
- Agent-specific configuration validation
- Output structure definition

### Infrastructure Layer Responsibilities

**External System Integration:**

- LLM API communication and error handling
- Token usage tracking and performance metrics
- Network timeout and retry logic
- Authentication and authorization
- Rate limiting and cost management

## Domain Value Objects

### PromptStrategy

Encapsulates prompt engineering business rules for each reasoning approach.

```python
@dataclass(frozen=True)
class PromptStrategy:
    """Domain value object defining prompt engineering strategy."""

    system_prompt: str
    user_prompt_template: str

    def build_prompt(self, question: Question) -> str:
        """Apply reasoning-specific prompt engineering rules."""
        return self.user_prompt_template.format(question_text=question.text)

    def validate_requirements(self, config: AgentConfig) -> ValidationResult:
        """Validate configuration supports this strategy."""
        # Implementation varies by strategy
        pass

# Strategy implementations
NONE_STRATEGY = PromptStrategy(
    system_prompt="You are a helpful assistant that provides direct, concise answers.",
    user_prompt_template="Answer the following question directly:\n\nQuestion: {question_text}"
)

CHAIN_OF_THOUGHT_STRATEGY = PromptStrategy(
    system_prompt="You are a helpful assistant that thinks step by step.",
    user_prompt_template="Think through this question step by step, then provide your answer:\n\nQuestion: {question_text}"
)
```

### ReasoningResult

Domain representation of processed reasoning output.

```python
@dataclass(frozen=True)
class ReasoningResult:
    """Domain result after applying reasoning strategy."""

    final_answer: str
    reasoning_text: str
    execution_metadata: Dict[str, Any]

    def get_answer(self) -> str:
        """Extract final answer using domain rules."""
        return self.final_answer.strip()

    def get_reasoning_trace(self) -> ReasoningTrace:
        """Convert to domain reasoning trace."""
        approach_type = self._determine_approach_type()
        return ReasoningTrace(
            approach_type=approach_type,
            reasoning_text=self.reasoning_text,
            metadata=self.execution_metadata
        )

    def _determine_approach_type(self) -> str:
        """Domain logic to determine reasoning approach from content."""
        return "chain_of_thought" if self.reasoning_text else "none"
```

## Domain Service Interface

### ReasoningAgentService

Core domain service defining reasoning strategy business logic.

```python
class ReasoningAgentService:
    """Domain service implementing specific reasoning approach."""

    def get_prompt_strategy(self) -> PromptStrategy:
        """Return prompt engineering strategy for this approach."""
        pass

    def process_question(self, question: Question, config: AgentConfig) -> str:
        """Generate prompt using domain strategy."""
        strategy = self.get_prompt_strategy()
        return strategy.build_prompt(question)

    def process_response(self, raw_response: str, context: Dict[str, Any]) -> ReasoningResult:
        """Apply domain parsing rules to extract structured result."""
        pass

    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate configuration against domain requirements."""
        pass

    def get_agent_type(self) -> str:
        """Return unique identifier for this reasoning approach."""
        pass
```

## Agent Implementations

### NoneAgentService

Direct prompting without reasoning steps.

```python
class NoneAgentService(ReasoningAgentService):
    """Domain service for direct prompting approach."""

    def get_prompt_strategy(self) -> PromptStrategy:
        """Business rule: Direct prompting without reasoning scaffolding."""
        return NONE_STRATEGY

    def process_response(self, raw_response: str, context: Dict[str, Any]) -> ReasoningResult:
        """Business rule: Extract direct answer, no reasoning trace."""
        cleaned_answer = self._clean_answer(raw_response)
        return ReasoningResult(
            final_answer=cleaned_answer,
            reasoning_text="",  # No reasoning for direct approach
            execution_metadata=context
        )

    def _clean_answer(self, response: str) -> str:
        """Domain logic for answer extraction and cleaning."""
        # Remove common prefixes/suffixes
        answer = response.strip()
        prefixes = ["Answer:", "The answer is:", "Final answer:"]
        for prefix in prefixes:
            if answer.startswith(prefix):
                answer = answer[len(prefix):].strip()
        return answer

    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate None agent configuration rules."""
        errors = []
        if config.agent_type != "none":
            errors.append("Agent type must be 'none' for None agent")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[]
        )

    def get_agent_type(self) -> str:
        return "none"
```

### ChainOfThoughtAgentService

Step-by-step reasoning approach.

```python
class ChainOfThoughtAgentService(ReasoningAgentService):
    """Domain service for Chain of Thought reasoning."""

    def get_prompt_strategy(self) -> PromptStrategy:
        """Business rule: Step-by-step reasoning strategy."""
        return CHAIN_OF_THOUGHT_STRATEGY

    def process_response(self, raw_response: str, context: Dict[str, Any]) -> ReasoningResult:
        """Business rule: Separate reasoning from final answer."""
        reasoning, answer = self._parse_reasoning_response(raw_response)

        return ReasoningResult(
            final_answer=answer,
            reasoning_text=reasoning,
            execution_metadata=context
        )

    def _parse_reasoning_response(self, response: str) -> Tuple[str, str]:
        """Domain logic for separating reasoning from answer."""
        # Look for answer indicators
        answer_markers = ["Final answer:", "Answer:", "Therefore:", "So the answer is:"]

        for marker in answer_markers:
            if marker in response:
                parts = response.split(marker, 1)
                reasoning = parts[0].strip()
                answer = parts[1].strip() if len(parts) > 1 else ""
                return reasoning, answer

        # Fallback: treat entire response as reasoning, extract last sentence as answer
        sentences = response.split('. ')
        if len(sentences) > 1:
            reasoning = '. '.join(sentences[:-1]) + '.'
            answer = sentences[-1].strip()
        else:
            reasoning = response
            answer = response

        return reasoning, answer

    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate Chain of Thought configuration rules."""
        errors = []
        warnings = []

        if config.agent_type != "chain_of_thought":
            errors.append("Agent type must be 'chain_of_thought' for Chain of Thought agent")

        # Business rule: Sufficient tokens for reasoning
        max_tokens = config.model_parameters.get("max_tokens", 1000)
        if max_tokens < 200:
            errors.append("Chain of Thought requires at least 200 max_tokens for reasoning steps")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_agent_type(self) -> str:
        return "chain_of_thought"
```

## Domain Service Factory

```python
class ReasoningAgentServiceFactory:
    """Factory for creating reasoning agent services."""

    def __init__(self):
        self._services = {
            "none": NoneAgentService,
            "chain_of_thought": ChainOfThoughtAgentService
        }

    def create_service(self, agent_type: str) -> ReasoningAgentService:
        """Create service instance by agent type."""
        if agent_type not in self._services:
            raise ValueError(f"Unknown agent type: {agent_type}")

        service_class = self._services[agent_type]
        return service_class()

    def get_supported_types(self) -> List[str]:
        """Return list of supported agent types."""
        return list(self._services.keys())

    def register_service(self, agent_type: str, service_class: Type[ReasoningAgentService]):
        """Register new reasoning service type."""
        self._services[agent_type] = service_class
```

## Infrastructure Integration

Infrastructure layer handles external API communication and structured output parsing using either:

- **Structured LogProbs** - For models supporting logprobs confidence scoring
- **Instructor** - Fallback for models without logprobs support

Domain services provide prompt strategies and response processing rules. Infrastructure services execute API calls and convert results back to domain objects.

See `v2-infrastructure-requirements.md` for complete integration patterns and parsing strategy implementation.

```



## Implementation Checklist

- [x] Define domain service interface
- [x] Implement None agent domain logic
- [x] Implement Chain of Thought agent domain logic
- [x] Create factory for service creation
- [x] Establish infrastructure integration pattern
- [x] Define testing strategy for domain logic
- [ ] Add Tree of Thought agent implementation
- [ ] Add Program of Thought agent implementation
- [ ] Implement validation pipeline integration
- [ ] Create domain event patterns (future)

## See Also

- **[Domain Model](v2-domain-model.md)** - Core entities and value objects used by reasoning agents
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service coordination using reasoning agents
- **[Infrastructure Requirements](v2-infrastructure-requirements.md)** - External API integration for reasoning execution
- **[Project Structure](v2-project-structure.md)** - Organization of reasoning agent implementations
- **[Testing Strategy](v2-testing-strategy.md)** - Testing patterns for domain logic validation
```
