"""Data access for the `agent_prompts` collection."""

from beanie import PydanticObjectId

from app.models.agent_prompt import AgentPrompt
from app.repositories.base import BaseRepo


class AgentPromptRepo(BaseRepo[AgentPrompt]):
    def __init__(self) -> None:
        super().__init__(AgentPrompt)

    async def get_active(self, agent: str) -> AgentPrompt | None:
        """Get the active prompt for an agent."""
        return await self.model.find_one(
            self.model.agent == agent,
            self.model.active == True,
        )

    async def deactivate_all(self, agent: str) -> None:
        """Deactivate all prompts for an agent."""
        await self.model.find(self.model.agent == agent).update(
            {"$set": {self.model.active: False}}
        )

    async def list_for_agent(self, agent: str) -> list[AgentPrompt]:
        """List all prompts for an agent, newest first."""
        return await self.model.find(
            self.model.agent == agent,
        ).sort(-self.model.created_at).to_list()
