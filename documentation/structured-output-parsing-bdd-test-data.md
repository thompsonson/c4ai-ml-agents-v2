"""Mock response fixtures for structured output parser testing.

These fixtures provide deterministic test data covering all parsing scenarios:
- Valid responses matching expected schemas
- Malformed JSON at various stages
- Schema validation failures
- Empty/whitespace responses
- Natural language responses

Usage in tests:
    from tests.fixtures.mock_responses import VALID_RESPONSES, INVALID_JSON, SCHEMA_MISMATCHES
"""

# ============================================================================
# Valid Responses - Should Parse Successfully
# ============================================================================

VALID_RESPONSES = {
    # DirectAnswerOutput: {"answer": "string"}
    "direct_simple": '{"answer": "4"}',
    "direct_long": '{"answer": "The answer is 4 because 2+2 equals 4"}',
    "direct_numeric": '{"answer": "42"}',
    
    # ChainOfThoughtOutput: {"answer": "string", "reasoning": "string"}
    "cot_simple": '{"answer": "4", "reasoning": "2+2 equals 4"}',
    "cot_detailed": '''{
        "answer": "4",
        "reasoning": "Step 1: Start with 2. Step 2: Add 2 more. Step 3: Result is 4."
    }''',
    "cot_multiline": '''{
        "answer": "Paris",
        "reasoning": "France is a country in Europe.\\nThe capital of France is Paris.\\nTherefore, the answer is Paris."
    }''',
}

# ============================================================================
# Invalid JSON - Should Fail at json_parse Stage
# ============================================================================

INVALID_JSON = {
    # Missing closing brace
    "missing_brace": '{"answer": "4"',
    
    # Missing quotes on value
    "missing_value_quotes": '{"answer": 4}',
    
    # Missing quotes on key
    "missing_key_quotes": '{answer: "4"}',
    
    # Trailing comma
    "trailing_comma": '{"answer": "4",}',
    
    # Single quotes instead of double
    "single_quotes": "{'answer': '4'}",
    
    # Incomplete nested object
    "incomplete_nested": '{"answer": "4", "reasoning": "step',
    
    # JavaScript-style comments (invalid in JSON)
    "with_comments": '{"answer": "4" /* this is the answer */}',
    
    # Unescaped newlines
    "unescaped_newlines": '{"answer": "line1\nline2"}',
}

# ============================================================================
# Schema Validation Failures - Valid JSON, Wrong Structure
# ============================================================================

SCHEMA_MISMATCHES = {
    # Missing required field
    "missing_answer": '{"reasoning": "I thought about it"}',
    
    # Wrong field names
    "wrong_field_name": '{"response": "4"}',
    "wrong_nested_field": '{"answer": "4", "thinking": "steps"}',
    
    # Extra fields not in schema
    "extra_fields": '{"answer": "4", "confidence": 0.9, "source": "calculation"}',
    
    # Wrong type (number instead of string)
    "wrong_type": '{"answer": 4}',
    
    # Null value for required field
    "null_value": '{"answer": null}',
    
    # Empty string (might be invalid depending on schema)
    "empty_answer": '{"answer": ""}',
    
    # Array instead of object
    "array_root": '[{"answer": "4"}]',
}

# ============================================================================
# Empty/Whitespace Responses - Should Fail at response_empty Stage
# ============================================================================

EMPTY_RESPONSES = {
    "completely_empty": "",
    "whitespace_only": "   \n  \t  ",
    "newlines_only": "\n\n\n",
    "tabs_only": "\t\t\t",
}

# ============================================================================
# Natural Language Responses - No JSON Structure
# ============================================================================

NATURAL_LANGUAGE = {
    "simple_text": "The answer is 4",
    "conversational": "Well, if you add 2 and 2 together, you get 4.",
    "with_reasoning": "Let me think about this. First, I have 2. Then I add another 2. That gives me 4 total. So the answer is 4.",
    "markdown": "## Answer\n\nThe answer is **4**.\n\n### Reasoning\n- Start with 2\n- Add 2\n- Result: 4",
    "code_block": "```python\nresult = 2 + 2\nprint(result)  # 4\n```",
}

# ============================================================================
# Edge Cases - Unusual but Potentially Valid
# ============================================================================

EDGE_CASES = {
    # Unicode characters
    "unicode": '{"answer": "¼ + ¼ = ½"}',
    
    # Very long answer
    "very_long": '{"answer": "' + "4 " * 1000 + '"}',
    
    # Escaped quotes
    "escaped_quotes": '{"answer": "The answer is \\"4\\""}',
    
    # Special characters
    "special_chars": '{"answer": "2+2=4 (100%)"}',
    
    # Whitespace in JSON
    "extra_whitespace": '''{
        
        "answer"  :   "4"  ,
        
        "reasoning"  :  "steps"
        
    }''',
}

# ============================================================================
# Structured Output Responses - From Native Structured Output API
# ============================================================================

STRUCTURED_OUTPUT_RESPONSES = {
    # What StructuredLogProbsParser receives with structured_data field
    "with_structured_data": {
        "content": '{"answer": "4"}',
        "structured_data": {"answer": "4"},
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    },
    
    # Fallback when only content is available
    "content_only": {
        "content": '{"answer": "4", "reasoning": "steps"}',
        "structured_data": None,
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
    },
    
    # With logprobs data
    "with_logprobs": {
        "content": '{"answer": "4"}',
        "structured_data": {"answer": "4"},
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "logprobs": {"content": [{"token": "{", "logprob": -0.1}]}
    },
}

# ============================================================================
# Helper Functions for Test Data Generation
# ============================================================================

def get_all_valid_responses() -> dict[str, str]:
    """Return all responses that should parse successfully."""
    return VALID_RESPONSES

def get_all_invalid_responses() -> dict[str, str]:
    """Return all responses that should fail parsing."""
    return {
        **INVALID_JSON,
        **SCHEMA_MISMATCHES,
        **EMPTY_RESPONSES,
        **NATURAL_LANGUAGE,
    }

def get_responses_by_failure_stage() -> dict[str, dict[str, str]]:
    """Organize responses by expected failure stage."""
    return {
        "json_parse": INVALID_JSON,
        "schema_validation": SCHEMA_MISMATCHES,
        "response_empty": EMPTY_RESPONSES,
    }