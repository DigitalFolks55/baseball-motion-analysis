"""API router composition."""

from fastapi import APIRouter

from baseball_motion_analysis.api.health import router as health_router


def build_api_router() -> APIRouter:
    """Build the public API router from feature routers."""
    router = APIRouter()
    router.include_router(health_router)
    return router
