"""Data access for the `stage_documents` collection."""

from beanie import PydanticObjectId

from app.models.enums import Stage
from app.models.stage_document import StageDocument
from app.repositories.base import BaseRepo


class StageDocumentsRepo(BaseRepo[StageDocument]):
    def __init__(self) -> None:
        super().__init__(StageDocument)

    async def latest_for_stage(
        self, analysis_id: PydanticObjectId, stage: Stage
    ) -> StageDocument | None:
        """Get the most recent document for a stage."""
        return await self.model.find(
            self.model.analysis_id == analysis_id,
            self.model.stage == stage,
        ).sort(-self.model.created_at).first_or_none()

    async def list_for_stage(
        self, analysis_id: PydanticObjectId, stage: Stage
    ) -> list[StageDocument]:
        """Get all documents for a stage, ordered newest first."""
        return await self.model.find(
            self.model.analysis_id == analysis_id,
            self.model.stage == stage,
        ).sort(-self.model.created_at).to_list()
