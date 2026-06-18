"""LangGraph state definition.

`StageState` holds the full context for one agent turn: the analysis, stage, system
prompt, prior context, messages, and the final structured result.
"""

from typing import Annotated, TypedDict

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

from app.agents.outputs import StageResult
from app.models.enums import Stage


class StageState(TypedDict):
    """State passed through the per-stage LangGraph agent graph."""

    stage: Stage
    analysis_id: str
    system_prompt: str
    prior_context: str
    dictionary_text: str
    current_draft: str | None
    messages: Annotated[list[BaseMessage], add_messages]
    result: StageResult | None
