# 2026-08-14 Swing Evaluation Compact Metric Dropdown

## Context

DEV004-07 refines the DEV004-06 metric filter. The multi-row metric selector consumed
too much replay toolbar height, and long evidence content could still dominate result
tables.

## Changes

* Replaced the visible multi-row metric selector with a compact dropdown button and
  checkbox menu.
* Preserved multi-metric filtering over returned `evaluation_overlay.metric_name` values.
* Kept `All metrics` as the default and empty-selection behavior.
* Narrowed the `Metrics` evidence column for short frame-number lists.
* Added bounded table-cell wrappers so unusually large table values can scroll without
  expanding the page layout.

## Architecture

No service/API contract changed. Evaluation-line geometry and metric names remain owned
by the application-service response, while browser JavaScript owns only dropdown state,
filtering, canvas redraws, labels, and table layout.

## Verification

* Added static integration coverage for compact dropdown markup, checkbox menu
  population, selected-set filtering, no-rerun redraw behavior, compact metrics evidence
  width, and bounded table content styling.
* `node --check src/baseball_motion_analysis/ui/web/static/app.js` passed.
* `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, and
  `uv run pytest` passed.
* No release or deployment was created.
