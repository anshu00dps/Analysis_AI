"""The `stage_chat_messages` collection — chat history per stage.

Each message stores the role (user/agent/system), the text content, what action it
came from (a chat turn or a manual edit), and optionally the document it produced.
"""

from datetime import datetime

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.models.analysis import utcnow
from app.models.enums import ChatRole, Stage


class StageChatMessage(Document):
    analysis_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    stage: Stage
    role: ChatRole
    content: str
    action: str = "chat"  # "chat" | "manual_edit"
    document_id: PydanticObjectId | None = None  # the StageDocument this turn created
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "stage_chat_messages"
