"""The `analysis_files` collection — one uploaded file, with original + sanitized text."""

from datetime import datetime

from beanie import Document, Indexed
from pydantic import Field

from app.models.analysis import utcnow
from beanie import PydanticObjectId


class AnalysisFile(Document):
    # `Indexed[...]` tells Mongo to build an index on this field — we query files by
    # analysis_id constantly, so indexing keeps those lookups fast.
    analysis_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    filename: str
    original_text: str
    sanitised_text: str = ""
    issues_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "analysis_files"
