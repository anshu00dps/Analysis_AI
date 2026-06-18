"""Structured output schemas for agent stages.

Each stage's agent must produce a `StageResult` — the LLM output is coerced to this
shape via `model.with_structured_output(StageResult)` in the graph's finalize node.
"""

from pydantic import BaseModel


class StageResult(BaseModel):
    """The structured output of running a stage agent."""

    content: str
    create_document: bool = False
    message_to_user: str = ""
