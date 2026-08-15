# 2026-08-14 Swing Evaluation Multi-Metric Filter

## Context

DEV004-06 extends the DEV004-05 metric filter so coaches and players can compare more
than one metric's evaluation lines at the same time. It also keeps evidence-heavy result
content from expanding the analysis layout.

## Changes

* Converted the replay-toolbar `Metric` control to a native multi-select.
* Kept `All metrics` as the default state and used an empty selected-metric set as the
  browser-side all-lines behavior.
* Filtered already-returned evaluation-line primitives by selected `metric_name` values
  before frame/event applicability checks.
* Kept `Evaluation Lines` as the master visibility toggle and `Poses` independent.
* Wrapped metric evidence frame lists and detected-fault evidence text in bounded,
  focusable, vertically scrollable cells.

## Architecture

No service/API contract changed. The `app` layer still owns evaluation-line geometry and
metric names, the `api` layer serializes returned primitives, and the `ui` layer owns
selection state, filtering, canvas redraws, labels, and evidence-cell layout.

## Verification

* Added static integration coverage for multi-select markup, toolbar order, metric option
  population, selected-set filtering, `All metrics`, master-toggle behavior,
  metric-change redraw behavior, and scrollable evidence styling.
* `node --check src/baseball_motion_analysis/ui/web/static/app.js` passed.
* `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, and
  `uv run pytest` passed.
* No release or deployment was created.
