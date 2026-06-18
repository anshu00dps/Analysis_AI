"""The `agent_prompts` collection — versioned system/user prompts per stage.

Only one prompt per agent is `active` at a time. Creating a new active prompt
deactivates the previous one (handled in the repository). This lets you iterate on
prompts without losing history.
"""

from datetime import datetime

from beanie import Document, Indexed
from pydantic import Field

from app.models.analysis import utcnow


class AgentPrompt(Document):
    # agent is a stage value plus "summary"; kept as str to allow the extra value.
    agent: Indexed(str)  # type: ignore[valid-type]
    system_prompt: str
    user_prompt: str | None = None
    active: bool = False
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "agent_prompts"
