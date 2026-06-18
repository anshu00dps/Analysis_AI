"""Analysis request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import AnalysisStatus, AnalysisType, Stage
from app.schemas.common import BaseSchema, ListResponse


class FileUploadItem(BaseSchema):
    """One file to upload, with content as base64."""

    filename: str
    content: str  # base64-encoded


class CreateAnalysisRequest(BaseSchema):
    """Create a new analysis."""

    analysis_info: dict = Field(
        ..., description="Object with 'name' and 'description' keys"
    )
    analysis_goals: dict = Field(
        ..., description="Object with 'primary', optional 'secondary', 'additional' keys"
    )
    analysis_type: AnalysisType
    vendor_details: list[dict] = Field(
        default_factory=list, description="List of {vendorName, layout}"
    )
    curated_tables: list[str] = Field(default_factory=list)
    files: list[FileUploadItem]


class AnalysisFileView(BaseSchema):
    """File within an analysis (for sanitization view)."""

    id: str = Field(alias="_id")
    filename: str
    original_text: str
    sanitised_text: str
    issues_count: int


class AnalysisResponse(BaseSchema):
    """Analysis metadata."""

    id: str = Field(alias="_id")
    analysis_info: dict
    analysis_goals: dict
    analysis_type: AnalysisType
    status: AnalysisStatus
    stage: Optional[Stage]
    vendor_details: list[dict]
    curated_tables: list[str]
    analysis_summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class ListAnalysesResponse(ListResponse):
    """Paginated list of analyses."""

    items: list[AnalysisResponse]
