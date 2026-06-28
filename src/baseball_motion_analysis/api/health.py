"""Health and readiness endpoints."""

from fastapi import APIRouter

from baseball_motion_analysis.app.services import ApplicationStatusService

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return basic application health without invoking analysis logic."""
    return ApplicationStatusService().health()
