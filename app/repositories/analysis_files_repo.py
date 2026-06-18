"""Data access for the `analysis_files` collection."""

from beanie import PydanticObjectId

from app.models.analysis_file import AnalysisFile
from app.repositories.base import BaseRepo


class AnalysisFilesRepo(BaseRepo[AnalysisFile]):
    def __init__(self) -> None:
        super().__init__(AnalysisFile)

    async def list_for_analysis(self, analysis_id: PydanticObjectId) -> list[AnalysisFile]:
        return await self.model.find(self.model.analysis_id == analysis_id).to_list()
