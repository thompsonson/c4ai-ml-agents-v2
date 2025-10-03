# Architecture Decision Record: Marvin vs Outlines Clients for Structured Output

## Status
Implemented

## Context
We need to replace the manual JSON schema approach with proper structured output libraries while maintaining our domain interface boundaries. Two promising alternatives have emerged:

1. **Marvin**: Post-processing approach using utility functions
2. **Outlines**: Constrained generation during LLM inference

Both libraries offer different trade-offs for structured output generation while respecting our `LLMClient` domain interface.

## Decision

Implement **both** MarvinClient and OutlinesClient as parallel LLMClient implementations, allowing users to choose based on their specific needs.

## Rationale

### MarvinClient (Post-Processing Approach)
**Use Case**: When external prompts must remain unchanged
- Preserves domain prompts exactly as written
- Works with any LLM response quality
- Clean separation between domain logic and structured output
- Fault-tolerant to LLM schema violations

**Trade-offs**:
- Requires additional LLM call for post-processing
- Higher latency and cost (2 API calls)
- May lose context from original generation

### OutlinesClient (Constrained Generation Approach)
**Use Case**: When generation efficiency and schema guarantees are priority
- Guarantees structured output during generation
- Single LLM call (lower cost/latency)
- Prevents invalid outputs at token level
- Better for high-volume scenarios

**Trade-offs**:
- May modify prompts to add schema constraints
- Less flexible with non-conforming responses
- Requires schema to be known at generation time

## Implementation Architecture

```
Factory Pattern Selection:
┌─────────────────────────┐
│  OutputParserFactory    │
├─────────────────────────┤
│ create_client(model)    │
│ + strategy: str         │
└─────────────────────────┘
           │
           ▼
┌─────────────────┐  OR  ┌─────────────────┐
│  MarvinClient   │      │ OutlinesClient  │
│                 │      │                 │
│ Post-process    │      │ Constrained     │
│ any response    │      │ generation      │
└─────────────────┘      └─────────────────┘
```

## BDD Test Coverage

### Existing BDD Tests That Apply to Both:

✅ **TestParserSelection**:
- Both clients will be selected based on model capabilities + strategy
- No contention - factory pattern handles routing

✅ **TestACLTranslation**:
- Both clients must translate library exceptions to `ParserException`
- No contention - same domain boundary requirements

### Client-Specific BDD Test Requirements:

#### MarvinClient BDD Tests:
```gherkin
Scenario: MarvinClient preserves external prompts unchanged
  Given a MarvinClient instance
  And an external domain prompt
  When I call chat_completion
  Then the prompt sent to LLM is unchanged
  And post-processing extracts structured data

Scenario: MarvinClient handles non-conforming responses
  Given a MarvinClient instance
  And an LLM response that doesn't follow schema
  When I parse the response
  Then Marvin extracts structured data anyway
  And returns valid Pydantic object
```

#### OutlinesClient BDD Tests:
```gherkin
Scenario: OutlinesClient guarantees schema compliance
  Given an OutlinesClient instance
  And a JSON schema requirement
  When I generate structured output
  Then the output is guaranteed to match schema
  And generation happens in single LLM call

Scenario: OutlinesClient adds schema constraints to prompts
  Given an OutlinesClient instance
  When I call chat_completion with response_model
  Then schema constraints are added to the prompt
  And generation is constrained to valid tokens
```

## Test Contention and Inconsistencies

### 🚨 **Major Contention**: Prompt Modification Expectations

**Existing BDD Test Expectation**:
```python
# From test_instructor_parser_uses_instructor_library_for_structured_output
assert "You must respond with valid JSON matching this exact schema" not in prompt_content
```

**Contention**:
- ✅ **MarvinClient**: Will pass - never modifies prompts
- ❌ **OutlinesClient**: May fail - might add schema constraints to prompts

**Resolution Strategy**:
Update BDD tests to be **client-aware**:

```python
@pytest.mark.parametrize("client_type", ["marvin", "outlines"])
async def test_structured_output_behavior(client_type, ...):
    if client_type == "marvin":
        # Test post-processing behavior
        assert prompt_unchanged
        assert post_processing_applied
    elif client_type == "outlines":
        # Test constrained generation behavior
        assert schema_constraints_applied
        assert single_generation_call
```

### 🚨 **Confidence Scores Inconsistency**

**Current BDD Expectation**:
```python
assert result["confidence_scores"] is not None
assert isinstance(result["confidence_scores"], dict)
```

**Contention**:
- ❌ **MarvinClient**: Cannot provide meaningful confidence scores (post-processing)
- ❌ **OutlinesClient**: Limited confidence score capabilities
- ✅ **StructuredLogProbsClient**: Only this provides real confidence scores

**Resolution**:
Update BDD tests to expect confidence scores only from StructuredLogProbsClient:

```python
def test_confidence_scores(parser_type, ...):
    if parser_type == "StructuredLogProbsParser":
        assert result["confidence_scores"] is not None
    else:
        assert result["confidence_scores"] is None  # MarvinClient, OutlinesClient
```

### 🚨 **Performance/Cost Expectations**

**New BDD Requirements**:
```gherkin
Scenario: MarvinClient makes two LLM calls
  When using MarvinClient for structured output
  Then exactly 2 API calls are made
  And total cost is approximately doubled

Scenario: OutlinesClient makes one LLM call
  When using OutlinesClient for structured output
  Then exactly 1 API call is made
  And generation includes schema constraints
```

## Updated Factory Selection Logic

```python
def create_client(self, model_name: str, strategy: str = "auto") -> LLMClient:
    if strategy == "marvin":
        return MarvinClient(self.api_key, self.base_url)
    elif strategy == "outlines":
        return OutlinesClient(self.api_key, self.base_url)
    elif strategy == "auto":
        if ModelCapabilitiesRegistry.supports_logprobs(model_name):
            return StructuredLogProbsClient(self.api_key, self.base_url)
        else:
            return MarvinClient(self.api_key, self.base_url)  # Default to prompt preservation
```

## Consequences

### Positive:
- Flexibility to choose approach based on use case
- Both libraries properly integrated while respecting domain boundaries
- Clear separation of concerns between different structured output strategies

### Negative:
- Increased complexity in testing and client selection
- Need to update existing BDD tests to handle multiple client behaviors
- Additional dependencies and maintenance overhead

### Neutral:
- Users must understand trade-offs to choose appropriate client
- Factory pattern requires strategy parameter for explicit selection

## Implementation Priority

1. ✅ **MarvinClient** (easier integration, preserves external prompts)
2. ✅ **Update BDD tests** to handle multiple client strategies
3. ✅ **OutlinesClient** (more complex integration)
4. ✅ **Enhanced factory selection** with strategy parameter

## Implementation Details

### Files Created/Modified

**New Clients:**
- `src/ml_agents_v2/infrastructure/marvin/client.py` - MarvinClient implementation
- `src/ml_agents_v2/infrastructure/outlines/client.py` - OutlinesClient implementation

**Updated Files:**
- `src/ml_agents_v2/infrastructure/structured_logprobs/client.py` - Updated to use `_internal_agent_type`
- `src/ml_agents_v2/infrastructure/parsing_factory.py` - Added strategy-based client selection
- `src/ml_agents_v2/infrastructure/reasoning_service.py` - Integrated factory with strategy support
- `src/ml_agents_v2/infrastructure/container.py` - Added parsing_strategy configuration
- `src/ml_agents_v2/config/application_config.py` - Added PARSING_STRATEGY environment variable
- `tests/bdd/fixtures/structured_output_fixtures.py` - Updated mocks to auto-parse JSON
- `tests/bdd/unit/infrastructure/test_structured_output_bdd.py` - Updated tests for new architecture

### Key Architectural Changes

1. **Domain Boundary Preservation**: Changed from `response_model` (Pydantic type) to `_internal_agent_type` (string)
2. **No Fallback Parsing**: All clients must return `structured_data` or raise exceptions
3. **Internal Schema Mapping**: Infrastructure maps agent type strings to Pydantic schemas internally

### Dependencies Added

```toml
marvin = ">=2.3.0"
outlines = ">=0.0.44"
```

## Testing the Implementation

### Environment Configuration

Use the `PARSING_STRATEGY` environment variable to select which client to use:

```bash
# Test with Marvin (2 API calls: generation + Marvin extraction)
export PARSING_STRATEGY="marvin"

# Test with Outlines (1 API call with JSON schema constraints)
export PARSING_STRATEGY="outlines"

# Auto-select based on model capabilities (default)
export PARSING_STRATEGY="auto"
```

### Complete Test Workflow

#### 1. Set Up Environment

```bash
export OPENROUTER_API_KEY="your-api-key-here"
export PARSING_STRATEGY="marvin"  # or "outlines" or "auto"
```

#### 2. Create Test Benchmark

```bash
cat > test_benchmark.csv << 'EOF'
INPUT,OUTPUT
"What is 2+2?","4"
"What is the capital of France?","Paris"
"Is the sky blue?","Yes"
EOF
```

#### 3. Import Benchmark

```bash
uv run ml-agents benchmark import test_benchmark.csv \
  --name "SimpleTest" \
  --description "Test benchmark for Marvin/Outlines"
```

#### 4. Test with Marvin

```bash
export PARSING_STRATEGY="marvin"
uv run ml-agents evaluate create \
  --agent none \
  --model anthropic/claude-3-haiku \
  --benchmark SimpleTest

# Note the evaluation ID, then run it
uv run ml-agents evaluate run <EVAL_ID_1>
```

#### 5. Test with Outlines

```bash
export PARSING_STRATEGY="outlines"
uv run ml-agents evaluate create \
  --agent none \
  --model anthropic/claude-3-haiku \
  --benchmark SimpleTest

uv run ml-agents evaluate run <EVAL_ID_2>
```

#### 6. Test with Auto Selection

```bash
export PARSING_STRATEGY="auto"

# Uses StructuredLogProbs for OpenAI models
uv run ml-agents evaluate create \
  --agent none \
  --model openai/gpt-4o-mini \
  --benchmark SimpleTest

uv run ml-agents evaluate run <EVAL_ID_3>

# Uses Marvin for Anthropic models
uv run ml-agents evaluate create \
  --agent none \
  --model anthropic/claude-3-haiku \
  --benchmark SimpleTest

uv run ml-agents evaluate run <EVAL_ID_4>
```

#### 7. Compare Results

```bash
uv run ml-agents evaluate show <EVAL_ID_1>
uv run ml-agents evaluate show <EVAL_ID_2>
uv run ml-agents evaluate show <EVAL_ID_3>
uv run ml-agents evaluate show <EVAL_ID_4>
```

### Strategy Comparison

| Strategy | Description | API Calls | Best For | Models |
|----------|-------------|-----------|----------|--------|
| `marvin` | Marvin post-processing extraction | 2 (generate + extract) | Testing Marvin library, preserving prompts | All models |
| `outlines` | OpenAI structured outputs with JSON schema | 1 (constrained) | Testing constrained generation | All models |
| `auto` | Auto-selects based on model:<br>- OpenAI → StructuredLogProbs<br>- Others → Marvin | Varies | Production use | All models |

### Debugging and Verification

To see detailed information about which client is being used:

```bash
export LOG_LEVEL="DEBUG"
export DEBUG_MODE="true"
uv run ml-agents evaluate run <EVAL_ID>
```

This will show:
- Which parsing strategy is active
- Client initialization details
- API call traces
- Structured output extraction process

### Test Different Agent Types

```bash
# Direct answer (no reasoning)
uv run ml-agents evaluate create \
  --agent none \
  --model anthropic/claude-3-haiku \
  --benchmark SimpleTest

# Chain of thought reasoning
uv run ml-agents evaluate create \
  --agent cot \
  --model anthropic/claude-3-haiku \
  --benchmark SimpleTest
```

### Quality Gates

All tests pass:
```bash
make quality-gates  # Runs tests, type check, format check, lint
make bdd-tests      # Runs BDD tests (16/16 passing)
```