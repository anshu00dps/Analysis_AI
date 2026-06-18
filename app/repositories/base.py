"""Base repository.

The repository pattern puts all data-access logic in one place per collection, so
services and API routes never touch Beanie/Mongo directly. That keeps business logic
testable and lets us swap storage later without rewriting callers.

`BaseRepo` provides the generic CRUD that every collection needs; subclasses add
collection-specific queries.
"""

from typing import Generic, TypeVar

from beanie import Document, PydanticObjectId

ModelT = TypeVar("ModelT", bound=Document)


class BaseRepo(Generic[ModelT]):
    def __init__(self, model: type[ModelT]):
        self.model = model

    async def create(self, doc: ModelT) -> ModelT:
        return await doc.insert()

    async def get(self, doc_id: PydanticObjectId | str) -> ModelT | None:
        return await self.model.get(doc_id)

    async def save(self, doc: ModelT) -> ModelT:
        return await doc.save()

    async def delete(self, doc: ModelT) -> None:
        await doc.delete()
