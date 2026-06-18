"""Agent prompt loading and seeding.

Prompts are versioned and stored in MongoDB. One per agent is `active` at a time.
The `load_active_prompt` function retrieves the current system/user prompt for a stage.
The `seed_prompts_from_json` function populates the DB from the JSON seed file.
"""

import json
from pathlib import Path

from app.core.logging import get_logger
from app.models.agent_prompt import AgentPrompt
from app.models.enums import Stage

log = get_logger(__name__)


async def load_active_prompt(stage: Stage) -> AgentPrompt | None:
    """Load the active prompt for a stage.

    Returns None if no prompt exists (e.g., before seeding).
    """
    return await AgentPrompt.find_one(
        AgentPrompt.agent == stage.value,
        AgentPrompt.active == True,
    )


async def seed_prompts_from_json(path: str | Path) -> None:
    """Populate the agent_prompts collection from a JSON seed file.

    Expected JSON format (MongoDB extended JSON):
    [
        {
            "_id": {...},
            "agent": "brd",
            "systemPrompt": "...",
            "userPrompt": "...",
            "active": true,
            ...
        },
        ...
    ]

    Maps `systemPrompt` → `system_prompt`, `userPrompt` → `user_prompt`.
    Upserts by agent name (does not insert if already exists).
    """
    path = Path(path)
    if not path.exists():
        log.warning("Prompt seed file not found: %s", path)
        return

    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        log.error("Prompt seed file must be a JSON array")
        return

    for item in data:
        agent = item.get("agent")
        if not agent:
            log.warning("Skipping prompt item with no agent field")
            continue

        existing = await AgentPrompt.find_one(AgentPrompt.agent == agent)
        if existing:
            log.debug("Prompt for agent %s already exists; skipping", agent)
            continue

        prompt = AgentPrompt(
            agent=agent,
            system_prompt=item.get("systemPrompt", ""),
            user_prompt=item.get("userPrompt"),
            active=item.get("active", False),
        )
        await prompt.insert()
        log.info("Seeded prompt for agent %s", agent)
