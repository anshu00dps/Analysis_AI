"""Summary API endpoints."""

from fastapi import APIRouter

from app.services.analysis_service import get_analysis
from app.services.summary_service import build_summary

router = APIRouter(tags=["summary"])


@router.get("/analyses/{analysis_id}/summary")
async def get_summary(analysis_id: str) -> dict:
    """Get a summary of all stages for an analysis."""
    await get_analysis(analysis_id)
    return await build_summary(analysis_id)
