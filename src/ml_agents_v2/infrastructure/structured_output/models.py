"""Infrastructure output models for structured parsing."""

from pydantic import BaseModel, Field


class BaseReasoningOutput(BaseModel):
    """Base class for all reasoning approach output models."""

    answer: str = Field(description="Final answer from reasoning process")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {"required": ["answer"], "additionalProperties": False}


class DirectAnswerOutput(BaseReasoningOutput):
    """Infrastructure model for None agent structured output."""

    pass


class ChainOfThoughtOutput(BaseReasoningOutput):
    """Infrastructure model for Chain of Thought structured output."""

    reasoning: str = Field(description="Step-by-step reasoning process")
