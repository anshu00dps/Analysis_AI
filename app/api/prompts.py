"""Agent prompts API endpoints."""

from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId

from app.models.agent_prompt import AgentPrompt
from app.models.enums import Stage
from app.repositories.agent_prompt_repo import AgentPromptRepo
from app.agents.prompts import seed_prompts_from_json
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("")
async def get_prompts_list() -> list[dict]:
    """List all prompts."""
    prompts = await AgentPrompt.find_all().to_list()
    return [
        {
            "id": str(p.id),
            "agent": p.agent,
            "active": p.active,
            "created_at": p.created_at.isoformat(),
        }
        for p in prompts
    ]


@router.get("/{stage}")
async def get_prompts_for_stage(stage: str) -> list[dict]:
    """List all prompts for a stage."""
    repo = AgentPromptRepo()
    prompts = await repo.list_for_agent(stage)
    return [
        {
            "id": str(p.id),
            "agent": p.agent,
            "system_prompt": p.system_prompt,
            "user_prompt": p.user_prompt,
            "active": p.active,
            "created_at": p.created_at.isoformat(),
        }
        for p in prompts
    ]


@router.post("/{stage}")
async def post_prompt(stage: str, request: dict) -> dict:
    """Create a new prompt (inactive by default)."""
    prompt = AgentPrompt(
        agent=stage,
        system_prompt=request.get("system_prompt", ""),
        user_prompt=request.get("user_prompt"),
        active=False,
    )
    prompt = await prompt.insert()
    return {
        "id": str(prompt.id),
        "agent": prompt.agent,
        "active": prompt.active,
        "created_at": prompt.created_at.isoformat(),
    }


@router.post("/{stage}/activate/{prompt_id}")
async def post_activate_prompt(stage: str, prompt_id: str) -> dict:
    """Activate a prompt (deactivates all others for the stage)."""
    repo = AgentPromptRepo()

    prompt = await repo.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if prompt.agent != stage:
        raise HTTPException(status_code=400, detail="Prompt does not belong to this stage")

    await repo.deactivate_all(stage)

    prompt.active = True
    prompt = await repo.save(prompt)

    return {
        "id": str(prompt.id),
        "agent": prompt.agent,
        "active": prompt.active,
    }


@router.post("/seed")
async def post_seed_prompts(file_path: str = "analysisai.agent_prompts.json") -> dict:
    """Seed prompts from JSON file."""
    await seed_prompts_from_json(file_path)
    return {"status": "seeded", "file": file_path}
