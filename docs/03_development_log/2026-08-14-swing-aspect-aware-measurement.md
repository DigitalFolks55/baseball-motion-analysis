# 2026-08-14 Swing Aspect-Aware Measurement

## Summary

DEV004-04 fixed swing evaluation v2 geometry for non-square video sources.

## Changes

* Added a `SwingMeasurementSpace` domain helper for aspect-aware distance, horizontal
  displacement, vector-angle, and joint-angle math.
* Passed stored-video source width and height from application-service media metadata
  into phase detection, v2 metric calculation, scoring, and secondary fault evidence.
* Added optional `frame_width` and `frame_height` fields for direct pose-sequence swing
  analysis requests.
* Preserved normalized evaluation-overlay points for browser rendering, so existing
  `Poses` and `Evaluation Lines` overlay controls remain compatible.
* Added non-square-frame regression tests for stance width, torso tilt, head drift,
  attack angle, app-service dimension plumbing, and API request dimension plumbing.

## Verification

Focused verification completed:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit/test_swing_motion_metrics.py tests/unit/test_swing_evaluation_overlay_lines.py tests/integration/test_swing_application_service.py tests/integration/test_swing_analysis_api.py tests/integration/test_swing_video_analysis_api.py
```

Required verification passed:

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run mypy src
UV_CACHE_DIR=.uv-cache uv run pytest
```

## Notes

Corrected metrics may differ from earlier raw-normalized results for the same video.
This is expected because previous calculations mixed `x` units normalized by image width
with `y` units normalized by image height.
