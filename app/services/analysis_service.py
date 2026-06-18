"""Business logic for analyses."""

import base64
from datetime import datetime

from beanie import PydanticObjectId
from fastapi import HTTPException

from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisInfo, AnalysisGoals, VendorDetail, utcnow
from app.models.analysis_file import AnalysisFile
from app.models.enums import AnalysisStatus, AnalysisType, Stage
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.analysis_files_repo import AnalysisFilesRepo
from app.schemas.analysis import CreateAnalysisRequest
from app.services.file_extractor import extract_text
from app.services.sanitizer_client import SanitizerClient

log = get_logger(__name__)


async def create_analysis(req: CreateAnalysisRequest) -> Analysis:
    """Create a new analysis and extract+sanitize files.

    Args:
        req: CreateAnalysisRequest with analysis metadata and files.

    Returns:
        The created Analysis document.

    Raises:
        ValueError: If file extraction fails.
    """
    analyses_repo = AnalysesRepo()
    files_repo = AnalysisFilesRepo()
    sanitizer = SanitizerClient()

    analysis_info = AnalysisInfo(**req.analysis_info)
    analysis_goals = AnalysisGoals(**req.analysis_goals)
    vendor_details = [VendorDetail(**v) for v in req.vendor_details]

    analysis = Analysis(
        analysis_info=analysis_info,
        analysis_goals=analysis_goals,
        analysis_type=req.analysis_type,
        status=AnalysisStatus.SANITIZATION,
        vendor_details=vendor_details,
        curated_tables=req.curated_tables,
    )
    analysis = await analyses_repo.create(analysis)

    for file_item in req.files:
        try:
            file_bytes = base64.b64decode(file_item.content)
            original_text = extract_text(file_item.filename, file_bytes)

            try:
                sanitised_text, issues_count = await sanitizer.sanitize_to_text(
                    original_text
                )
            except Exception as e:
                log.warning(
                    "Sanitization failed for file %s in analysis %s: %s",
                    file_item.filename,
                    analysis.id,
                    e,
                )
                sanitised_text = original_text
                issues_count = 0

            analysis_file = AnalysisFile(
                analysis_id=analysis.id,
                filename=file_item.filename,
                original_text=original_text,
                sanitised_text=sanitised_text,
                issues_count=issues_count,
            )
            await files_repo.create(analysis_file)

        except Exception as e:
            log.error("Error processing file %s: %s", file_item.filename, e)
            raise ValueError(f"Failed to process file {file_item.filename}: {e}") from e

    return analysis


async def list_analyses(
    *,
    limit: int = 20,
    cursor: datetime | None = None,
    status: AnalysisStatus | None = None,
    stage: Stage | None = None,
) -> tuple[list[Analysis], datetime | None]:
    """List analyses with cursor-based pagination.

    Args:
        limit: Maximum number of items to return.
        cursor: Pagination cursor (created_at timestamp of last item).
        status: Filter by status.
        stage: Filter by stage.

    Returns:
        Tuple of (items, next_cursor).
    """
    repo = AnalysesRepo()
    return await repo.list_paginated(
        limit=limit, cursor=cursor, status=status, stage=stage
    )


async def get_analysis(analysis_id: str | PydanticObjectId) -> Analysis:
    """Get an analysis by ID.

    Args:
        analysis_id: The analysis ID.

    Returns:
        The Analysis document.

    Raises:
        HTTPException(404): If not found.
    """
    repo = AnalysesRepo()
    analysis = await repo.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


async def start_analysis(analysis: Analysis) -> Analysis:
    """Start an analysis (move from sanitization to running).

    Args:
        analysis: The Analysis document to start.

    Returns:
        Updated Analysis.

    Raises:
        HTTPException(409): If not in sanitization status.
    """
    if analysis.status != AnalysisStatus.SANITIZATION:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start analysis with status {analysis.status}",
        )

    repo = AnalysesRepo()
    return await repo.update_status(
        analysis,
        status=AnalysisStatus.RUNNING,
        stage=Stage.BRD,
    )
