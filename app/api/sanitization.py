"""Sanitization API endpoints."""

from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId

from app.models.enums import AnalysisStatus
from app.repositories.analysis_files_repo import AnalysisFilesRepo
from app.schemas.analysis import AnalysisFileView
from app.schemas.sanitization import SanitizationResponse, UpdateSanitizationRequest
from app.services.analysis_service import get_analysis

router = APIRouter(tags=["sanitization"])


@router.get("/analyses/{analysis_id}/sanitization")
async def get_sanitization(analysis_id: str) -> SanitizationResponse:
    """Get sanitization view (original + sanitized text per file)."""
    analysis = await get_analysis(analysis_id)

    repo = AnalysisFilesRepo()
    files = await repo.list_for_analysis(analysis.id)

    file_views = [
        AnalysisFileView(
            id=str(f.id),
            filename=f.filename,
            original_text=f.original_text,
            sanitised_text=f.sanitised_text,
            issues_count=f.issues_count,
        )
        for f in files
    ]

    return SanitizationResponse(files=file_views)


@router.post("/analyses/{analysis_id}/sanitization")
async def post_sanitization(
    analysis_id: str, req: UpdateSanitizationRequest
) -> SanitizationResponse:
    """Update sanitized text for a file (only while in sanitization status)."""
    analysis = await get_analysis(analysis_id)

    if analysis.status != AnalysisStatus.SANITIZATION:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot update sanitization with status {analysis.status}",
        )

    repo = AnalysisFilesRepo()
    file = await repo.get(req.file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.analysis_id != analysis.id:
        raise HTTPException(status_code=403, detail="File does not belong to this analysis")

    file.sanitised_text = req.sanitised_text
    await repo.save(file)

    files = await repo.list_for_analysis(analysis.id)
    file_views = [
        AnalysisFileView(
            id=str(f.id),
            filename=f.filename,
            original_text=f.original_text,
            sanitised_text=f.sanitised_text,
            issues_count=f.issues_count,
        )
        for f in files
    ]

    return SanitizationResponse(files=file_views)
