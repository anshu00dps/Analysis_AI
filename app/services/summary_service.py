"""Build summary of all stages for an analysis."""

from beanie import PydanticObjectId

from app.models.enums import Stage
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.stage_documents_repo import StageDocumentsRepo


async def build_summary(analysis_id: str | PydanticObjectId) -> dict:
    """Build a summary of all stage outputs for an analysis.

    Args:
        analysis_id: The analysis ID.

    Returns:
        Dict with analysis metadata and per-stage content.
    """
    analyses_repo = AnalysesRepo()
    stage_docs_repo = StageDocumentsRepo()

    analysis = await analyses_repo.get(analysis_id)
    if not analysis:
        return {}

    summary = {
        "analysis_id": str(analysis.id),
        "analysis_info": analysis.analysis_info.dict(),
        "analysis_goals": analysis.analysis_goals.dict(),
        "analysis_type": analysis.analysis_type.value,
        "status": analysis.status.value,
        "stage": analysis.stage.value if analysis.stage else None,
        "created_at": analysis.created_at.isoformat(),
        "stages": {},
    }

    for stage in Stage:
        doc = await stage_docs_repo.latest_for_stage(analysis.id, stage)
        summary["stages"][stage.value] = {
            "content": doc.content if doc else None,
            "created_by": doc.created_by.value if doc else None,
            "created_at": doc.created_at.isoformat() if doc else None,
        }

    return summary
