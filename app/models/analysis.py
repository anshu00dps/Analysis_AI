"""The `analyses` collection — the central record for one analysis run.

Beanie `Document` = a MongoDB collection. Plain `BaseModel` classes used as fields
become *embedded sub-documents* (nested objects), not separate collections.
"""

from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, Field

from app.models.enums import AnalysisStatus, AnalysisType, Stage


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisInfo(BaseModel):
    name: str
    description: str = ""


class AnalysisGoals(BaseModel):
    primary: str
    secondary: str | None = None
    additional: str | None = None


class VendorDetail(BaseModel):
    vendor_name: str
    layout: list[str] = Field(default_factory=list)


class Analysis(Document):
    analysis_info: AnalysisInfo
    analysis_goals: AnalysisGoals
    analysis_type: AnalysisType
    status: AnalysisStatus = AnalysisStatus.CREATED
    stage: Stage | None = None

    # Dictionary context — which vendor layouts or curated tables this analysis uses.
    vendor_details: list[VendorDetail] = Field(default_factory=list)
    curated_tables: list[str] = Field(default_factory=list)

    analysis_summary: str | None = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "analyses"  # the MongoDB collection name
