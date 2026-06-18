"""Data access for business dictionary collections."""

from app.models.dictionaries import CuratedDictionaryEntry, VendorDictionaryEntry
from app.repositories.base import BaseRepo


class CuratedDictionaryRepo(BaseRepo[CuratedDictionaryEntry]):
    def __init__(self) -> None:
        super().__init__(CuratedDictionaryEntry)

    async def list_by_tables(self, table_names: list[str]) -> list[CuratedDictionaryEntry]:
        """Get all entries for specified tables."""
        if not table_names:
            return []
        return await self.model.find(
            self.model.table_name.in_(table_names),
        ).to_list()

    async def list_all_tables(self) -> list[str]:
        """Get distinct table names."""
        tables = await self.model.distinct(self.model.table_name)
        return sorted(tables) if tables else []


class VendorDictionaryRepo(BaseRepo[VendorDictionaryEntry]):
    def __init__(self) -> None:
        super().__init__(VendorDictionaryEntry)

    async def list_by_vendor_and_layouts(
        self, vendor_name: str, layouts: list[str]
    ) -> list[VendorDictionaryEntry]:
        """Get all entries for a vendor and specified layouts."""
        if not layouts:
            return []
        return await self.model.find(
            self.model.vendor_name == vendor_name,
            self.model.file_category.in_(layouts),
        ).to_list()
