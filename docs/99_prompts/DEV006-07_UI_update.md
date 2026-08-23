# DEV006-07 UI Update

## Objective

Update the local browser swing analysis result layout so `Detected Faults` is displayed
between `Feedback` and `Detected Events And Phase Scores`.

This is a focused UI ordering task. It must not change swing scoring, pose estimation,
event detection, detected-fault generation, API schemas, or feedback content unless a
small adapter/template adjustment is strictly required to support the display order.

Preserve the local-PC-first, service-oriented architecture. Complete implementation,
tests, documentation, and verification. Do not create a release or deployment.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Do not stop after planning.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Review relevant implementation and tests:

- `src/baseball_motion_analysis/ui/web/templates/index.html`
- `src/baseball_motion_analysis/ui/web/static/app.js`
- `src/baseball_motion_analysis/ui/web/static/styles.css`
- `tests/integration/test_web_video_upload_replay_api.py`

## Current Behavior

The swing analysis result panel currently displays result sections in an order where
`Detected Faults` appears after `Detected Events And Phase Scores`.

The requested product order is:

```text
Feedback
Detected Faults
Detected Events And Phase Scores
```

## Scope

### Reorder Result Sections

Required behavior:

- Move the visible `Detected Faults` result section so it appears immediately after the
  `Feedback` section.
- Keep `Detected Events And Phase Scores` after `Detected Faults`.
- Preserve all existing content, labels, localization keys, rendering behavior, table
  structure, empty states, and styling unless the move requires minimal layout cleanup.
- Preserve the existing diagnostics, metrics, pose quality, replay overlay, and analysis
  controls behavior.
- Do not change fault detection logic or phase-score logic.
- Do not change API response shape.

### Documentation

Update user-facing or product documentation if it describes the result section order.
At minimum, review:

- `docs/05_manuals/swing_motion_analysis_ui.md`
- `docs/01_product/feature_catalog.md`

### Tests

Add or update deterministic tests to verify the new section order.

Required coverage:

- Static web UI test confirms `Detected Faults` appears after `Feedback`.
- Static web UI test confirms `Detected Events And Phase Scores` appears after
  `Detected Faults`.
- Existing assertions for result labels, metrics, event rows, diagnostics, and
  localization remain valid.

Prefer updating `tests/integration/test_web_video_upload_replay_api.py` unless another
existing UI/static test is a better fit.

## Non-Goals

- No pose-estimation changes.
- No swing event-detection changes.
- No scoring, fault-threshold, confidence, or feedback-generation changes.
- No API schema changes.
- No replay overlay changes.
- No Japanese localization expansion beyond preserving existing localized labels.
- No release, deployment, Docker setup, hosted web service, package publishing, version
  tag, or changelog release entry.

## Acceptance Criteria

- In the browser result layout, `Detected Faults` is visually ordered between `Feedback`
  and `Detected Events And Phase Scores`.
- The existing `Detected Faults` content still renders with the same data and empty
  state behavior.
- The existing `Detected Events And Phase Scores` content still renders with the same
  event/phase-score data and confidence labels.
- No domain, analysis, pose, storage, or API logic is changed for this UI-only request.
- Relevant docs and `PLANS.md` are updated.
- Required quality commands pass:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Final Review Notes To Capture

During final-review-planning, confirm:

- The result section order matches the user request.
- The implementation remained UI-only except for tests/docs/planning updates.
- Existing result rendering behavior is preserved.
- All required quality gates passed.
- No release or deployment was created.
