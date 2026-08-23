# 2026-08-22 Enhanced Pose Estimation V6

## Summary

DEV006-06 restores body-pose estimated impact as the normal local browser workflow and
removes the visible impact-off selector introduced in the previous no-ball iteration.
The backend/API still accepts skipped or contact-required impact policies for
compatibility, but normal browser analysis now always sends `body_pose_estimated`.

## Changes

- Removed the normal browser `Impact Detection` off/on control.
- Kept impact visible as an estimated event row and replay overlay in normal browser
  results.
- Refined estimated impact selection in the motion domain after foot strike instead of
  relying on the initial active-window impact estimate.
- Added impact candidate scoring cues for wrist/grip motion transition, contact-zone
  hand position, lead-side bracing, rotation, and post-foot-strike ordering.
- Penalized early pre-contact candidates and late finish-only candidates.
- Preserved explicit skipped-impact API compatibility and event visibility metadata.
- Updated unit, API, app-service, static UI tests, product documentation, architecture
  notes, swing motion knowledge, and the swing UI manual.

## Verification

Focused verification before full quality gates:

- `uv run pytest tests/unit/test_swing_motion_metrics.py`
- `uv run pytest tests/integration/test_web_video_upload_replay_api.py`
- `uv run pytest tests/integration/test_swing_video_analysis_api.py tests/integration/test_swing_application_service.py`

Full repository quality gates are tracked in `PLANS.md`.
