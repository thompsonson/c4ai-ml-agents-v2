"""Infrastructure output models for structured parsing."""

from pydantic import BaseModel, ConfigDict, Field


class BaseReasoningOutput(BaseModel):
    """Base class for all reasoning approach output models."""

    model_config = ConfigDict(
        json_schema_extra={"required": ["answer"], "additionalProperties": False}
    )

    answer: str = Field(description="Final answer from reasoning process")


class DirectAnswerOutput(BaseReasoningOutput):
    """Infrastructure model for None agent structured output."""

    pass


class ChainOfThoughtOutput(BaseReasoningOutput):
    """Infrastructure model for Chain of Thought structured output."""

    reasoning: str = Field(description="Step-by-step reasoning process")
