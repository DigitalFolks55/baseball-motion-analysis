"""API router composition."""

from fastapi import APIRouter

from baseball_motion_analysis.api.health import router as health_router
from baseball_motion_analysis.api.media_router import router as media_router
from baseball_motion_analysis.api.swing_router import router as swing_router


def build_api_router() -> APIRouter:
    """Build the public API router from feature routers."""
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(media_router)
    router.include_router(swing_router)
    return router
