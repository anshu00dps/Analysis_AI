"""FastAPI application entrypoint.

`create_app()` builds and configures the app (the "application factory" pattern, which
keeps the app testable). Run it locally with:

    uvicorn app.main:app --reload --port 3000

Then open http://localhost:3000/docs for the auto-generated Swagger UI.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.mongo import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hook.

    Code before `yield` runs once on startup (open the DB connection); code after runs
    on shutdown (close it). This is FastAPI's modern replacement for on_event handlers.
    """
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    log = get_logger(__name__)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="LLM-powered document analysis platform.",
        lifespan=lifespan,
    )

    # CORS: allow the frontend (different origin/port) to call this API from the browser.
    # Wide-open for development; tighten `allow_origins` before production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers. Each phase adds more (analyses, stages, etc.).
    app.include_router(health.router)

    log.info("%s starting in %s mode", settings.app_name, settings.environment)
    return app


app = create_app()
