# 2026-07-29 Web Video Upload Replay UI

## Summary

Implemented DEV002-01 dual-mode web video upload and replay UI.

## Scope Completed

- Added FastAPI browser UI routes for `/`.
- Added plain HTML, CSS, and JavaScript for video upload, library browsing, replay, playback speed, and approximate frame stepping.
- Added streamed multipart upload endpoint at `/api/v1/media/videos`.
- Added SQLite metadata repository and local filesystem file store.
- Added `VideoLibraryApplicationService` so UI and API routes call application services instead of low-level video validation, OpenCV, SQL, or file-copy behavior.
- Reused `MediaInputService` with bounded frame sampling for video validation and metadata extraction.
- Added replay manifest and media-ID-based content endpoint with HTTP byte-range support.
- Added local and server runtime configuration through `BMA_*` environment variables.
- Added media-ID-based uploaded-video deletion from the browser library, including stored file and metadata record cleanup.

## Non-Goals Confirmed

- No pose estimation.
- No swing, pitching, throwing, or fielding analysis.
- No feedback reports.
- No image-sequence browser upload.
- No camera streaming or WebSocket video streaming.
- No automatic transcoding or FFmpeg dependency.
- No authentication, authorization, Docker, production deployment, release publishing, or version bump.

## Quality

Required checks passed:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Pytest result after the deletion update: 41 passed.

## Risks

- Browser replay depends on browser/container/codec support. MP4 and WebM are documented as the most reliable direct replay formats.
- Frame stepping uses approximate `1 / fps` seeking and is not frame-exact.
- Deletion is intentionally destructive for local stored media and requires explicit user action in the UI.
- Server mode does not include authentication or multi-user authorization and must not be exposed publicly with sensitive videos.
- SQLite concurrency is acceptable for the local MVP but needs review before multi-user server usage.
