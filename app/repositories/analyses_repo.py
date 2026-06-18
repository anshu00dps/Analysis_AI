"""Data access for the `analyses` collection."""

from datetime import datetime

from beanie import PydanticObjectId
from beanie.operators import LT

from app.models.analysis import Analysis, utcnow
from app.models.enums import AnalysisStatus, Stage
from app.repositories.base import BaseRepo


class AnalysesRepo(BaseRepo[Analysis]):
    def __init__(self) -> None:
        super().__init__(Analysis)

    async def update_status(
        self,
        analysis: Analysis,
        *,
        status: AnalysisStatus | None = None,
        stage: Stage | None = None,
    ) -> Analysis:
        if status is not None:
            analysis.status = status
        if stage is not None or status == AnalysisStatus.COMPLETED:
            analysis.stage = stage
        analysis.updated_at = utcnow()
        return await analysis.save()

    async def list_paginated(
        self,
        *,
        limit: int = 20,
        cursor: datetime | None = None,
        status: AnalysisStatus | None = None,
        stage: Stage | None = None,
    ) -> tuple[list[Analysis], datetime | None]:
        """Cursor-based pagination ordered by newest first.

        We page by `created_at` (the cursor) rather than skip/offset, which stays fast
        as the collection grows. Returns (items, next_cursor).
        """
        query = self.model.find()
        if status is not None:
            query = query.find(self.model.status == status)
        if stage is not None:
            query = query.find(self.model.stage == stage)
        if cursor is not None:
            query = query.find(LT(self.model.created_at, cursor))

        # Fetch one extra row to detect whether another page exists.
        items = await query.sort(-self.model.created_at).limit(limit + 1).to_list()
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = items[-1].created_at
        return items, next_cursor
