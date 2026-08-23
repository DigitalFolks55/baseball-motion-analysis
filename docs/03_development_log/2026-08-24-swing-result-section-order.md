# 2026-08-24 Swing Result Section Order

## Summary

DEV006-07 updates the local browser swing result layout so `Detected Faults` appears
immediately after `Feedback` and before `Detected Events And Phase Scores`.

## Changes

- Reordered existing result sections in the browser template.
- Preserved existing section IDs, localization keys, rendering functions, empty states,
  API payloads, scoring, event detection, replay overlays, and diagnostics.
- Updated the static UI test to verify the visible order.
- Updated the swing UI manual and feature catalog to describe the new result order.

## Verification

Focused verification:

- `uv run pytest tests/integration/test_web_video_upload_replay_api.py`

Full repository quality gates are tracked in `PLANS.md`.
