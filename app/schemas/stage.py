"""Stage/document request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.enums import ChatRole, DocumentAuthor, Stage
from app.schemas.common import BaseSchema


class PostStageRequest(BaseSchema):
    """Post to a stage: either chat or manual edit."""

    new_chat: Optional[str] = None
    new_text: Optional[str] = None


class ChatMessageView(BaseSchema):
    """One message in stage chat history."""

    id: str = Field(alias="_id")
    role: ChatRole
    content: str
    action: str
    document_id: Optional[str] = None
    created_at: datetime


class StageDocumentView(BaseSchema):
    """The latest document for a stage."""

    id: str = Field(alias="_id")
    stage: Stage
    content: str
    created_by: DocumentAuthor
    notebook_status: Optional[str]
    model_used: Optional[str]
    created_at: datetime


class StageResponse(BaseSchema):
    """Stage response: document + chat history."""

    document: Optional[StageDocumentView]
    messages: list[ChatMessageView]
