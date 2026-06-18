"""Analyses API endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId

from app.core.logging import get_logger
from app.models.enums import AnalysisStatus, Stage, STAGE_ORDER
from app.repositories.analyses_repo import AnalysesRepo
from app.schemas.analysis import (
    CreateAnalysisRequest,
    AnalysisResponse,
    ListAnalysesResponse,
)
from app.services.analysis_service import (
    create_analysis,
    get_analysis,
    list_analyses,
    start_analysis,
)
from app.models.analysis import utcnow

log = get_logger(__name__)

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisResponse, status_code=201)
async def post_analyses(req: CreateAnalysisRequest) -> AnalysisResponse:
    """Create a new analysis."""
    analysis = await create_analysis(req)
    return AnalysisResponse(
        **analysis.dict(by_alias=False),
        id=str(analysis.id),
    )


@router.get("", response_model=ListAnalysesResponse)
async def get_analyses_list(
    limit: int = 20,
    cursor: datetime | None = None,
    status: AnalysisStatus | None = None,
    stage: Stage | None = None,
) -> ListAnalysesResponse:
    """List analyses with cursor-based pagination."""
    items, next_cursor = await list_analyses(
        limit=limit, cursor=cursor, status=status, stage=stage
    )
    return ListAnalysesResponse(
        items=[
            AnalysisResponse(
                **item.dict(by_alias=False),
                id=str(item.id),
            )
            for item in items
        ],
        next_cursor=next_cursor,
    )


@router.get("/{id}", response_model=AnalysisResponse)
async def get_analyses_by_id(id: str) -> AnalysisResponse:
    """Get analysis metadata."""
    analysis = await get_analysis(id)
    return AnalysisResponse(
        **analysis.dict(by_alias=False),
        id=str(analysis.id),
    )


@router.post("/{id}/start", response_model=AnalysisResponse)
async def post_analyses_start(id: str) -> AnalysisResponse:
    """Start an analysis (move from sanitization to running)."""
    analysis = await get_analysis(id)
    analysis = await start_analysis(analysis)
    return AnalysisResponse(
        **analysis.dict(by_alias=False),
        id=str(analysis.id),
    )


@router.post("/{id}/next", response_model=AnalysisResponse)
async def post_analyses_next(id: str) -> AnalysisResponse:
    """Advance to the next stage."""
    analysis = await get_analysis(id)

    if not analysis.stage:
        raise HTTPException(
            status_code=400,
            detail="Analysis has no current stage",
        )

    try:
        current_idx = STAGE_ORDER.index(analysis.stage)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stage: {analysis.stage}",
        )

    if current_idx >= len(STAGE_ORDER) - 1:
        next_status = AnalysisStatus.COMPLETED
        next_stage = None
    else:
        next_stage = STAGE_ORDER[current_idx + 1]
        next_status = AnalysisStatus.RUNNING

    repo = AnalysesRepo()
    analysis = await repo.update_status(
        analysis,
        status=next_status,
        stage=next_stage,
    )

    return AnalysisResponse(
        **analysis.dict(by_alias=False),
        id=str(analysis.id),
    )
