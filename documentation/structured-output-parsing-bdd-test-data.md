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


# ============================================================================
# API Call Verification Data - For Testing Instruction Formatting
# ============================================================================

DOMAIN_PROMPTS = {
    # From NONE_STRATEGY
    "direct_simple": "Answer the following question directly:\n\nQuestion: What is 2+2?",
    "direct_complex": "Answer the following question directly:\n\nQuestion: Explain quantum computing.",

    # From CHAIN_OF_THOUGHT_STRATEGY
    "cot_simple": "Think step by step about this question:\n\nQuestion: What is 2+2?",
    "cot_complex": "Think step by step about this question:\n\nQuestion: How does photosynthesis work?",
}

EXPECTED_ENHANCED_PROMPTS = {
    # What InstructorParser should produce
    "direct_simple_enhanced": '''Answer the following question directly:

Question: What is 2+2?

You must respond with valid JSON matching this exact schema:
{
  "type": "object",
  "properties": {
    "answer": {"type": "string"}
  },
  "required": ["answer"],
  "additionalProperties": false
}

Do not include any text outside the JSON structure.
Your entire response must be valid JSON only.''',
}

API_CALL_PARAMETERS = {
    # Expected parameters for InstructorParser calls
    "instructor_call": {
        "model": "anthropic/claude-3-sonnet",  # With provider prefix
        "messages": [{"role": "user", "content": "enhanced_prompt_here"}],
        "temperature": 1.0,
        "max_tokens": 1000,
        # Note: NO response_format parameter
    },

    # Expected parameters for StructuredLogProbsParser calls
    "structured_logprobs_call": {
        "model": "openai/gpt-4",  # With provider prefix
        "messages": [{"role": "user", "content": "original_prompt_here"}],
        "response_format": {"type": "json_schema", "json_schema": {...}},
        "logprobs": True,
        "temperature": 0.7,
    },
}

# ============================================================================
# Mock Call Verification Helpers
# ============================================================================

def verify_instructor_call_args(mock_call_args, expected_domain_prompt: str):
    """Helper to verify InstructorParser call arguments."""
    assert mock_call_args.kwargs["model"].count("/") == 1  # Has provider

    messages = mock_call_args.kwargs["messages"]
    actual_prompt = messages[0]["content"]

    assert expected_domain_prompt in actual_prompt
    assert "You must respond with valid JSON" in actual_prompt
    assert "response_format" not in mock_call_args.kwargs

def verify_structured_logprobs_call_args(mock_call_args, expected_schema: dict):
    """Helper to verify StructuredLogProbsParser call arguments."""
    assert mock_call_args.kwargs["model"].count("/") == 1  # Has provider
    assert "response_format" in mock_call_args.kwargs
    assert mock_call_args.kwargs["logprobs"] is True

    response_format = mock_call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema"


# ============================================================================
# Production Integration Test Data - Real API Testing
# ============================================================================

REAL_MODEL_CONFIGS = {
    # Models for testing InstructorParser integration
    "instructor_models": [
        {"provider": "anthropic", "name": "claude-3-sonnet"},
        {"provider": "anthropic", "name": "claude-3-haiku"},
        {"provider": "meta", "name": "llama-3.1-8b-instruct"},
    ],

    # Models for testing StructuredLogProbsParser integration
    "structured_output_models": [
        {"provider": "openai", "name": "gpt-4"},
        {"provider": "openai", "name": "gpt-3.5-turbo"},
    ],
}

INTEGRATION_TEST_QUESTIONS = {
    # Simple questions for real API testing
    "basic_math": {
        "question": "What is 5 + 3?",
        "expected_answer": "8",
        "schema": "DirectAnswerOutput",
        "timeout": 30,
    },
    "basic_reasoning": {
        "question": "Why is the sky blue?",
        "expected_answer": "Light scattering",
        "schema": "ChainOfThoughtOutput",
        "timeout": 60,
    },
    "simple_factual": {
        "question": "What is the capital of Japan?",
        "expected_answer": "Tokyo",
        "schema": "DirectAnswerOutput",
        "timeout": 30,
    },
}

PRODUCTION_TEST_SCENARIOS = {
    # Test real instruction formatting with actual models
    "instructor_with_real_model": {
        "description": "Verify InstructorParser works with real Anthropic model",
        "model": "anthropic/claude-3-haiku",
        "parser_type": "InstructorParser",
        "expected_behavior": "Adds JSON schema instructions to prompt",
        "success_criteria": "Returns valid structured JSON matching schema",
    },
    "structured_output_with_real_model": {
        "description": "Verify StructuredLogProbsParser works with real OpenAI model",
        "model": "openai/gpt-3.5-turbo",
        "parser_type": "StructuredLogProbsParser",
        "expected_behavior": "Uses response_format parameter",
        "success_criteria": "Returns structured data from API",
    },
}


# ============================================================================
# ACL Boundary Protection Test Data
# ============================================================================

BOUNDARY_VIOLATION_SCENARIOS = {
    # Test cases that verify proper exception translation
    "openrouter_error_mapper_fallback": {
        "description": "ValueError caught by OpenRouter error mapper instead of ACL",
        "exception_type": "ValueError",
        "exception_message": "Empty response",
        "should_be_caught_by": "ReasoningInfrastructureService._translate_parser_exception",
        "should_not_be_caught_by": "OpenRouterErrorMapper.map_to_failure_reason",
        "expected_failure_reason": {
            "category": "parsing_error",
            "description": "InstructorParser failed at response_empty",
            "contains_technical_details": ["Parser: InstructorParser", "Stage: response_empty"],
        },
        "incorrect_failure_reason": {
            "category": "parsing_error",
            "description": "Failed to parse response from OpenRouter API",
            "technical_details": "Empty response",
        },
    },

    "application_layer_isolation": {
        "description": "Application layer should never see ParserException",
        "exception_raised": "ParserException",
        "application_layer_should_receive": "FailureReason",
        "application_layer_should_not_import": "ParserException",
        "test_modules": [
            "ml_agents_v2.core.application.services.evaluation_orchestrator",
            "ml_agents_v2.core.application.services.results_analyzer",
        ],
    },

    "proper_acl_translation": {
        "description": "ParserException properly translates to FailureReason at ACL boundary",
        "parser_exceptions": {
            "instructor_empty_response": {
                "parser_type": "InstructorParser",
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "stage": "response_empty",
                "content": "",
                "error": "ValueError('Empty response')",
            },
            "instructor_json_parse": {
                "parser_type": "InstructorParser",
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "stage": "json_parse",
                "content": '{"answer": incomplete',
                "error": "json.JSONDecodeError('Expecting ...')",
            },
            "structured_logprobs_schema": {
                "parser_type": "StructuredLogProbsParser",
                "model": "gpt-4",
                "provider": "openai",
                "stage": "schema_validation",
                "content": '{"wrong_field": "value"}',
                "error": "ValidationError('Field required')",
            },
        },
        "expected_failure_reasons": {
            "instructor_empty_response": {
                "category": "parsing_error",
                "description": "InstructorParser failed at response_empty",
                "technical_details_contains": [
                    "Parser: InstructorParser",
                    "Model: claude-3-sonnet",
                    "Provider: anthropic",
                    "Stage: response_empty",
                    "Original Error: Empty response",
                ],
                "recoverable": False,
            },
        },
    },
}

ERROR_MAPPER_BOUNDARY_TESTS = {
    # Scenarios to test that OpenRouter error mapper doesn't interfere
    "should_not_catch_parser_exceptions": [
        "ValueError('Empty response')",  # From ParserException
        "json.JSONDecodeError('Expecting ...')",  # From JSON parsing
        "ValidationError('Field required')",  # From schema validation
    ],

    "should_catch_openrouter_errors": [
        "httpx.HTTPStatusError(400, 'Bad Request')",  # OpenRouter API errors
        "httpx.TimeoutException('Request timeout')",  # Network timeouts
        "httpx.RequestError('Connection failed')",  # Network failures
    ],
}

def verify_acl_boundary_protection(reasoning_service, parser_exception):
    """Helper to verify ACL boundary is properly maintained."""
    # Should translate ParserException to FailureReason
    failure_reason = reasoning_service._translate_parser_exception(parser_exception)

    assert isinstance(failure_reason, FailureReason)
    assert failure_reason.category == "parsing_error"
    assert parser_exception.parser_type in failure_reason.description
    assert parser_exception.stage in failure_reason.description

    # Should include rich technical details
    tech_details = failure_reason.technical_details
    assert f"Parser: {parser_exception.parser_type}" in tech_details
    assert f"Model: {parser_exception.model}" in tech_details
    assert f"Provider: {parser_exception.provider}" in tech_details
    assert f"Stage: {parser_exception.stage}" in tech_details

    return failure_reason

def verify_application_layer_isolation(application_module):
    """Helper to verify application layer doesn't import infrastructure exceptions."""
    import ast
    import inspect

    # Get module source code
    source = inspect.getsource(application_module)
    tree = ast.parse(source)

    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if "ParserException" in [alias.name for alias in node.names]:
                raise AssertionError(f"Application module {application_module.__name__} imports ParserException")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "ParserException" in alias.name:
                    raise AssertionError(f"Application module {application_module.__name__} imports ParserException")

    return True