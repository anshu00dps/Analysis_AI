"""The `agent_runs` collection — audit log of every LLM execution (for cost/compliance)."""

from datetime import datetime

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.models.analysis import utcnow
from app.models.enums import Stage


class AgentRun(Document):
    analysis_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    agent: Stage
    model_used: str
    input_text: str = ""
    output_text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "agent_runs"
