"""Health-check router.

A FastAPI `APIRouter` is a group of related endpoints. We register routers onto the
main app in `main.py`. This one exposes a trivial liveness probe used by Docker /
load balancers (and by you, to confirm the server is up).
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }
