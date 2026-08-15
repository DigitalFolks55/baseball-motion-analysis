# 2026-08-14 Swing Evaluation Metric Filter

## Context

DEV004-05 UI update 2 adds a focused replay-control change for swing evaluation v2.
Users need to isolate one metric's evaluation lines when the full overlay is visually
busy.

## Changes

* Added a `Metric` select between `Evaluation Lines` and `Speed` in the replay toolbar.
* Populated metric options from the current analysis result's returned
  `evaluation_overlay.metric_name` values.
* Kept `All metrics` as the default and reset state when analysis is cleared or replay
  selection changes.
* Filtered browser-rendered evaluation lines by selected `metric_name` before frame/event
  applicability checks.
* Kept the service/API contract unchanged; metric calculations and overlay geometry stay
  outside browser JavaScript.

## Verification

* Added static integration coverage for toolbar order, dropdown option behavior,
  selected-metric filtering, `All metrics`, the `Evaluation Lines` master toggle path,
  and metric-change redraw behavior without analysis reruns or speed changes.
* `node --check src/baseball_motion_analysis/ui/web/static/app.js` passed.
* `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, and
  `uv run pytest` passed.
* No release or deployment was created.
