"""MongoDB connection lifecycle.

`init_db()` opens an async connection and registers our Beanie models against a
database. `close_db()` tears it down. The FastAPI app calls these on startup/shutdown
(see app/main.py), so the connection is opened once and shared across all requests.

Beanie 2.x uses PyMongo's native async client (`AsyncMongoClient`) directly — the older
`motor` library is no longer needed.
"""

from pymongo import AsyncMongoClient

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import ALL_MODELS

log = get_logger(__name__)

# Module-level handle so other code (and tests) can reach the live client if needed.
_client: AsyncMongoClient | None = None


async def init_db() -> None:
    global _client
    from beanie import init_beanie  # imported here to keep import cost off cold paths

    settings = get_settings()
    _client = AsyncMongoClient(settings.mongodb_uri)
    database = _client[settings.db_name]
    await init_beanie(database=database, document_models=ALL_MODELS)
    log.info("MongoDB connected: db=%s", settings.db_name)


async def close_db() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        log.info("MongoDB connection closed")
