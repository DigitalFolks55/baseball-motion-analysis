"""Application factory and command-line entrypoint."""

import uvicorn
from fastapi import FastAPI

from baseball_motion_analysis.api.router import build_api_router


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="baseball_motion_analysis",
        version="0.1.0",
        description="API-first foundation for baseball motion analysis.",
    )
    app.include_router(build_api_router(), prefix="/api/v1")
    return app


app = create_app()


def main() -> None:
    """Run the development API server."""
    uvicorn.run("baseball_motion_analysis.app.main:app", host="127.0.0.1", port=8000)
