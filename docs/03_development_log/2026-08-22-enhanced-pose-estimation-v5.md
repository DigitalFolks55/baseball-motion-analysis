# 2026-08-22 Enhanced Pose Estimation v5

## Context

User review after DEV006-04 found that no-ball impact handling was still confusing:
turning impact detection off left impact visible in evaluation, skipped impact appeared
like low confidence, follow-through could show 0% confidence, and several useful metrics
were no longer evaluated.

## Changes

- Added explicit event display metadata so skipped or unavailable impact can remain in
  phase metadata without appearing as a normal browser event row or replay event label.
- Updated overlay frame generation to mark only visible/overlay-enabled events as event
  frames.
- Restored no-ball fallback evaluation for selected non-contact metrics:
  - `HEAD_TRANSLATION_RATIO` uses setup-to-foot-strike evidence when impact is skipped.
  - `FOLLOW_THROUGH_POSTURE_BALANCE` uses foot-strike-to-finish evidence when impact is
    skipped.
- Kept contact-specific metrics and impact-phase faults suppressed when impact is
  skipped or unavailable.
- Reduced the no-leg-lift stride fallback penalty so valid no-stride swings are limited
  without being automatically pinned near poor confidence.
- Updated browser rendering to filter hidden events and avoid showing skipped impact as a
  percentage confidence event.

## Verification

- Focused swing motion, analysis, app-service, API, and static UI tests passed during
  implementation.
- Required quality gates passed:
  - `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src`
  - `uv run pytest`
- Full pytest passed with 113 tests and one existing Starlette/httpx deprecation
  warning.

## Remaining Limitations

- No bat, barrel, ball, or contact detector was added.
- Body-pose estimated impact remains an approximate event when users choose impact
  detection on.
- No-ball fallback metrics are lower-confidence approximations and should not be
  described as contact-frame measurements.
