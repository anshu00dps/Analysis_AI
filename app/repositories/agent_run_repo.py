"""Data access for the `agent_runs` collection."""

from beanie import PydanticObjectId

from app.models.agent_run import AgentRun
from app.repositories.base import BaseRepo


class AgentRunRepo(BaseRepo[AgentRun]):
    def __init__(self) -> None:
        super().__init__(AgentRun)

    async def list_for_analysis(self, analysis_id: PydanticObjectId) -> list[AgentRun]:
        """Get all agent runs for an analysis, ordered oldest first."""
        return await self.model.find(
            self.model.analysis_id == analysis_id,
        ).sort(self.model.created_at).to_list()
