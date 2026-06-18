"""Data access for the `stage_chat_messages` collection."""

from beanie import PydanticObjectId

from app.models.enums import Stage
from app.models.stage_chat import StageChatMessage
from app.repositories.base import BaseRepo


class StageChatRepo(BaseRepo[StageChatMessage]):
    def __init__(self) -> None:
        super().__init__(StageChatMessage)

    async def list_for_stage(
        self, analysis_id: PydanticObjectId, stage: Stage
    ) -> list[StageChatMessage]:
        """Get all chat messages for a stage, ordered oldest first."""
        return await self.model.find(
            self.model.analysis_id == analysis_id,
            self.model.stage == stage,
        ).sort(self.model.created_at).to_list()
