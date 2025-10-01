"""Pytest configuration and shared fixtures."""

from typing import Any

import pytest


@pytest.fixture
def mock_openrouter_responses() -> dict[str, Any]:
    """Mock responses from OpenRouter API."""
    return {
        "2+2": {
            "choices": [
                {
                    "message": {
                        "content": "Let me think step by step. 2 + 2 = 4. Therefore, the answer is 4."
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15},
        },
        "capital_france": {
            "choices": [{"message": {"content": "The capital of France is Paris."}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        },
    }
