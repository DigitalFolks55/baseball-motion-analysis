# 2026-08-17: UI Japanese Localization

## Summary

Implemented DEV005-01 Japanese UI localization for the local browser interface.

English remains the default language. The header now includes an `English / 日本語`
selector that switches visible UI labels, status messages, overlay copy, and rendered
swing-analysis result text in the same UI.

## Implementation Notes

- Added browser-side localization dictionaries in the web UI JavaScript.
- Added localization keys to server-rendered UI text in the main template.
- Re-rendered the latest structured swing-analysis result from browser state when the
  language changes, so switching language does not rerun analysis.
- Added Japanese labels for known swing metrics, phases, severity values, common
  feedback templates, drills, faults, diagnostics, and common limitations.
- Kept API responses, application services, storage, video handling, pose estimation,
  analysis rules, and scoring language-independent.

## Verification

- `node --check src/baseball_motion_analysis/ui/web/static/app.js`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest tests/integration/test_web_video_upload_replay_api.py`
- `uv run pytest`

Result: all checks passed. Full pytest passed with 94 tests and one existing
Starlette/httpx deprecation warning from FastAPI's test client import path.
