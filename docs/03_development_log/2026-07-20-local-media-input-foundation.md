# 2026-07-20 Local Media Input Foundation

## Summary

Implemented DEV001-01 local media input foundation for the local-PC application direction.

## Phase Results

- Phase 1 planning: Updated `PLANS.md` with scope, non-goals, acceptance criteria, and risks.
- Phase 2 architecture: Updated architecture docs and added ADR-0003 for local media input.
- Phase 3 coding: Implemented local video input modules for models, validators, recorded video loading, image sequence loading, camera stream interface, optional local copy behavior, and service coordination.
- Phase 4 quality assurance: Added fixture-generated and mocked unit tests. Required quality commands passed.
- Phase 5 final review: Confirmed the implementation remains input-layer only and local-PC-first.

## Implemented

- Recorded local video validation, OpenCV metadata extraction, and frame sampling.
- Image sequence validation, request-order sorting by default, filename and modified-time sorting, and dimension mismatch rejection.
- Common `FrameSequence` and `FrameData` models for future pose estimation and replay.
- Local camera stream interface with `open()`, `read_frame()`, `close()`, and context manager support.
- Optional local media copy behavior under a configurable media root.

## Non-Goals Preserved

- No pose estimation.
- No swing, fielding, pitching, or throwing analysis.
- No replay UI.
- No production media storage index.
- No browser upload endpoint.
- No browser WebSocket streaming.
- No MediaPipe integration.

## Quality Results

- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run mypy src` passed.
- `uv run pytest` passed with 21 tests and one existing FastAPI/Starlette deprecation warning.

## Remaining Risks

- OpenCV codec behavior may vary by local machine.
- Camera stream behavior is interface foundation only and not tested against real hardware.
- Production media indexing and replay-library persistence remain future work.
