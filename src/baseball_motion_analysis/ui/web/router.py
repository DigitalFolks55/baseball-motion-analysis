"""Browser UI routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from baseball_motion_analysis.core.config import AppSettings

_TEMPLATE_DIR = Path(__file__).parent / "templates"

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the browser video upload and replay UI."""
    settings: AppSettings = request.app.state.settings
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "runtime_mode": settings.runtime_mode.value,
            "max_upload_mb": settings.max_upload_mb,
            "privacy_storage_label": settings.privacy_storage_label,
            "server_mode_warning": (
                "This MVP does not include authentication or multi-user authorization. "
                "Do not expose sensitive videos through an unrestricted public deployment."
            ),
        },
    )
