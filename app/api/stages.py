"""Stages API endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.enums import Stage
from app.repositories.stage_chat_repo import StageChatRepo
from app.repositories.stage_documents_repo import StageDocumentsRepo
from app.schemas.stage import PostStageRequest, StageResponse, StageDocumentView, ChatMessageView
from app.services.analysis_service import get_analysis
from app.services.pipeline_service import run_stage

router = APIRouter(tags=["stages"])


@router.get("/analyses/{analysis_id}/stages/{stage}")
async def get_stage(analysis_id: str, stage: str) -> StageResponse:
    """Get the latest document and chat history for a stage."""
    await get_analysis(analysis_id)

    try:
        stage_enum = Stage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    stage_docs_repo = StageDocumentsRepo()
    stage_chat_repo = StageChatRepo()

    doc = await stage_docs_repo.latest_for_stage(analysis_id, stage_enum)
    messages = await stage_chat_repo.list_for_stage(analysis_id, stage_enum)

    doc_view = None
    if doc:
        doc_view = StageDocumentView(
            id=str(doc.id),
            stage=doc.stage,
            content=doc.content,
            created_by=doc.created_by,
            notebook_status=doc.notebook_status,
            model_used=doc.model_used,
            created_at=doc.created_at,
        )

    message_views = [
        ChatMessageView(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            action=msg.action,
            document_id=str(msg.document_id) if msg.document_id else None,
            created_at=msg.created_at,
        )
        for msg in messages
    ]

    return StageResponse(document=doc_view, messages=message_views)


@router.post("/analyses/{analysis_id}/stages/{stage}")
async def post_stage(
    analysis_id: str, stage: str, req: PostStageRequest
) -> StageResponse:
    """Run a stage: either chat or manual edit."""
    await get_analysis(analysis_id)

    try:
        stage_enum = Stage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    if not req.new_chat and not req.new_text:
        raise HTTPException(
            status_code=400,
            detail="Either newChat or newText must be provided",
        )

    if req.new_chat and req.new_text:
        raise HTTPException(
            status_code=400,
            detail="Cannot provide both newChat and newText",
        )

    await run_stage(
        analysis_id,
        stage_enum,
        user_message=req.new_chat,
        new_text=req.new_text,
    )

    stage_docs_repo = StageDocumentsRepo()
    stage_chat_repo = StageChatRepo()

    doc = await stage_docs_repo.latest_for_stage(analysis_id, stage_enum)
    messages = await stage_chat_repo.list_for_stage(analysis_id, stage_enum)

    doc_view = None
    if doc:
        doc_view = StageDocumentView(
            id=str(doc.id),
            stage=doc.stage,
            content=doc.content,
            created_by=doc.created_by,
            notebook_status=doc.notebook_status,
            model_used=doc.model_used,
            created_at=doc.created_at,
        )

    message_views = [
        ChatMessageView(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            action=msg.action,
            document_id=str(msg.document_id) if msg.document_id else None,
            created_at=msg.created_at,
        )
        for msg in messages
    ]

    return StageResponse(document=doc_view, messages=message_views)
