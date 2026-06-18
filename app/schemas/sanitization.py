"""Sanitization request/response schemas."""

from pydantic import Field

from app.schemas.analysis import AnalysisFileView
from app.schemas.common import BaseSchema


class UpdateSanitizationRequest(BaseSchema):
    """Update sanitized text for a file."""

    file_id: str = Field(..., alias="fileId")
    sanitised_text: str


class SanitizationResponse(BaseSchema):
    """Sanitization view response."""

    files: list[AnalysisFileView]
