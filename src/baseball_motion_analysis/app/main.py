"""Application factory and command-line entrypoint."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from baseball_motion_analysis.api.router import build_api_router
from baseball_motion_analysis.app.media_services import (
    VideoLibraryApplicationService,
)
from baseball_motion_analysis.core.config import AppSettings, load_settings
from baseball_motion_analysis.storage.local_file_store import LocalMediaFileStore
from baseball_motion_analysis.storage.repository import MediaRepository
from baseball_motion_analysis.ui.web.router import router as web_router


def create_app(
    *,
    settings: AppSettings | None = None,
    media_repository: MediaRepository | None = None,
    media_file_store: LocalMediaFileStore | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    resolved_settings = settings or load_settings()
    video_library_service: VideoLibraryApplicationService | None = None
    if media_repository is not None or media_file_store is not None:
        file_store = media_file_store or LocalMediaFileStore(resolved_settings.media_root)
        if media_repository is None:
            msg = "media_repository is required when media_file_store is provided"
            raise ValueError(msg)
        video_library_service = VideoLibraryApplicationService(
            repository=media_repository,
            file_store=file_store,
        )

    app = FastAPI(
        title="baseball_motion_analysis",
        version="0.1.0",
        description="Local-PC-first foundation for baseball motion analysis.",
    )
    app.state.settings = resolved_settings
    app.state.video_library_service = video_library_service
    app.include_router(web_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parents[1] / "ui" / "web" / "static"),
        name="static",
    )
    app.include_router(build_api_router(), prefix="/api/v1")
    return app


app = create_app()


def main() -> None:
    """Run the development API server."""
    settings = load_settings()
    uvicorn.run(
        "baseball_motion_analysis.app.main:app",
        host=settings.host,
        port=settings.port,
    )
