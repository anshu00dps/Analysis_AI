"""Common schemas and utilities for API DTOs."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from datetime import datetime


def model_config() -> ConfigDict:
    """Standard Pydantic config for API DTOs.

    Enables camelCase aliases (e.g., analysisInfo) while accepting both camelCase and
    snake_case in requests. Excludes None values from responses for cleaner JSON.
    """
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        exclude_none=True,
    )


class BaseSchema(BaseModel):
    """Base schema with standard config applied."""

    model_config = model_config()


class ListResponse(BaseSchema):
    """Paginated list envelope.

    Cursor is the created_at timestamp of the last item (for cursor-based pagination).
    """

    items: list = Field(default_factory=list)
    next_cursor: datetime | None = None
