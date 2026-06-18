"""Pipeline orchestration for running stages."""

from beanie import PydanticObjectId
from fastapi import HTTPException
from langchain_core.messages import HumanMessage

from app.agents.outputs import StageResult
from app.agents.prompts import load_active_prompt
from app.core.logging import get_logger
from app.graph.stage_graph import stage_graph
from app.graph.state import StageState
from app.models.agent_run import AgentRun
from app.models.enums import ChatRole, DocumentAuthor, Stage
from app.models.stage_chat import StageChatMessage
from app.models.stage_document import StageDocument
from app.repositories.agent_prompt_repo import AgentPromptRepo
from app.repositories.agent_run_repo import AgentRunRepo
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.stage_chat_repo import StageChatRepo
from app.repositories.stage_documents_repo import StageDocumentsRepo
from app.services.dictionary_service import build_context_text
from app.services.analysis_service import get_analysis

log = get_logger(__name__)


async def run_stage(
    analysis_id: str | PydanticObjectId,
    stage: Stage,
    user_message: str | None = None,
    new_text: str | None = None,
) -> StageResult:
    """Run a stage for an analysis.

    Args:
        analysis_id: The analysis ID.
        stage: The stage to run.
        user_message: User chat input (if any).
        new_text: Manual edit content (if any).

    Returns:
        The StageResult (structured output from the agent or manual edit).

    Raises:
        HTTPException: If analysis not found, wrong status, or other errors.
    """
    analysis = await get_analysis(analysis_id)

    if analysis.status.value != "running":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot run stage with analysis status {analysis.status}",
        )

    stage_docs_repo = StageDocumentsRepo()
    stage_chat_repo = StageChatRepo()
    agent_prompt_repo = AgentPromptRepo()
    agent_run_repo = AgentRunRepo()

    if new_text is not None:
        doc = StageDocument(
            analysis_id=analysis.id,
            stage=stage,
            content=new_text,
            created_by=DocumentAuthor.MANUAL_EDIT,
        )
        await stage_docs_repo.create(doc)

        msg = StageChatMessage(
            analysis_id=analysis.id,
            stage=stage,
            role=ChatRole.USER,
            content=f"[Manual edit]",
            action="manual_edit",
            document_id=doc.id,
        )
        await stage_chat_repo.create(msg)

        return StageResult(
            content=new_text,
            create_document=True,
            message_to_user="Document updated manually.",
        )

    prompt = await agent_prompt_repo.get_active(stage.value)
    if not prompt:
        log.warning("No active prompt for stage %s", stage)
        raise HTTPException(
            status_code=500,
            detail=f"No active prompt configured for stage {stage}",
        )

    current_draft = await stage_docs_repo.latest_for_stage(analysis.id, stage)
    prior_context = await _build_prior_context(stage, analysis.id, stage_docs_repo)
    dictionary_text = await build_context_text(analysis)

    state: StageState = {
        "stage": stage,
        "analysis_id": str(analysis.id),
        "system_prompt": prompt.system_prompt,
        "prior_context": prior_context,
        "dictionary_text": dictionary_text,
        "current_draft": current_draft.content if current_draft else None,
        "messages": [HumanMessage(content=user_message or "Continue with the next step.")],
        "result": None,
    }

    try:
        output = stage_graph.invoke(state)
        result: StageResult = output.get("result")
    except Exception as e:
        log.error("Graph invocation failed for stage %s: %s", stage, e)
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {e}",
        ) from e

    if result.create_document:
        doc = StageDocument(
            analysis_id=analysis.id,
            stage=stage,
            content=result.content,
            created_by=DocumentAuthor.AGENT,
            model_used=prompt.agent if hasattr(prompt, "agent") else stage.value,
        )
        await stage_docs_repo.create(doc)

        user_msg = StageChatMessage(
            analysis_id=analysis.id,
            stage=stage,
            role=ChatRole.USER,
            content=user_message or "(auto-run)",
            action="chat",
        )
        await stage_chat_repo.create(user_msg)

        agent_msg = StageChatMessage(
            analysis_id=analysis.id,
            stage=stage,
            role=ChatRole.AGENT,
            content=result.message_to_user or result.content[:200],
            action="chat",
            document_id=doc.id,
        )
        await stage_chat_repo.create(agent_msg)

        agent_run = AgentRun(
            analysis_id=analysis.id,
            agent=stage,
            model_used=prompt.agent if hasattr(prompt, "agent") else stage.value,
            input_text=user_message or "(auto-run)",
            output_text=result.content[:500],
        )
        await agent_run_repo.create(agent_run)

    return result


async def _build_prior_context(
    stage: Stage,
    analysis_id: PydanticObjectId,
    repo: StageDocumentsRepo,
) -> str:
    """Build context from previous stages.

    BRD gets nothing. Prompt gets BRD. Planning gets BRD+Prompt. Notebook gets all.
    """
    if stage == Stage.BRD:
        return ""

    prior_stages = []
    if stage in (Stage.PROMPT, Stage.PLANNING, Stage.NOTEBOOK):
        prior_stages.append(Stage.BRD)
    if stage in (Stage.PLANNING, Stage.NOTEBOOK):
        prior_stages.append(Stage.PROMPT)
    if stage == Stage.NOTEBOOK:
        prior_stages.append(Stage.PLANNING)

    context_parts = []
    for prior_stage in prior_stages:
        doc = await repo.latest_for_stage(analysis_id, prior_stage)
        if doc:
            context_parts.append(f"## {prior_stage.value.upper()}\n{doc.content}\n")

    return "\n".join(context_parts)
