"""The `stage_documents` collection — versioned outputs for each stage.

We never overwrite a stage document; every agent generation or manual edit inserts a
NEW row. The "current" document for a stage is simply the most recent one. This gives
you a free version history and audit trail.
"""

from datetime import datetime

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.analysis import utcnow
from app.models.enums import DocumentAuthor, Stage


class CuratedContext(BaseModel):
    tables: list[str] = Field(default_factory=list)
    version: str | None = None


class VendorContextItem(BaseModel):
    name: str
    layouts: list[str] = Field(default_factory=list)


class DictionaryContext(BaseModel):
    curated: CuratedContext | None = None
    vendor: list[VendorContextItem] | None = None


class StageDocument(Document):
    analysis_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    stage: Stage
    content: str  # markdown for brd/prompt/planning; .ipynb JSON for notebook
    created_by: DocumentAuthor = DocumentAuthor.AGENT
    notebook_status: str | None = None  # draft | final | running | error (notebook only)
    dictionary_context: DictionaryContext | None = None
    model_used: str | None = None  # which LLM produced this (audit)
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "stage_documents"
