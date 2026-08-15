# DEV004-06 Swing Evaluation v2 UI Update 3

## Goal

Update the local browser swing replay UI so users can select multiple swing v2 metrics
for evaluation-line overlays, and keep evidence-heavy result columns usable when many
evidence frames are returned.

This is a focused UI follow-up to DEV004-05. It is not a release or deployment task.

## Requested Changes

Implement these product changes:

1. Enable multiple selection for the `Metric` dropdown/select control.
2. If an evidence column has many frame values or long evidence content, make that column
   scrollable so the results table remains readable.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/99_prompts/DEV004-02_Swing_evaluation_v2_overlay_evaluation_lines.md`
* `docs/99_prompts/DEV004-03_Swing_evaluation_v2_UI_update.md`
* `docs/99_prompts/DEV004-04_Swing_evaluation_v2_aspect_issue.md`
* `docs/99_prompts/DEV004-05_Swing_evaluation_v2_UI_update_2.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
* `docs/02_architecture/adr/ADR-0010-swing-evaluation-overlay-lines.md`
* `docs/02_architecture/adr/ADR-0011-swing-aspect-aware-measurement-space.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Existing implementation:
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/unit/test_swing_evaluation_overlay_lines.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`

## Required Agent Workflow

Follow the repository workflow in order:

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
```

Do not run the release agent. Do not create a release, deployment, Docker setup, hosted
web service, PyPI package, version tag, or changelog release entry.

## Current Behavior

After DEV004-05:

* The replay toolbar order is `Poses`, `Evaluation Lines`, `Metric`, then `Speed`.
* The `Metric` control is a single-select dropdown.
* `All metrics` displays all returned evaluation-line primitives.
* Selecting one metric displays only evaluation lines whose returned `metric_name`
  matches the selected value.
* The `Evaluation Lines` toggle remains the master on/off control.
* `Poses` remains independent.
* Pose keypoint text tags remain disabled.

The single-select control is useful for isolating one metric, but users may need to
compare two or more metrics at the same time. Also, some results can contain many
evidence frame values, which can make a table row or evidence column too tall or too wide
for comfortable scanning.

## Required Outcomes

### 1. Multi-Select Metric Control

Update the existing `Metric` control so users can select multiple metrics.

Required behavior:

* The control should remain near the replay overlay controls.
* The toolbar order should remain:

```text
Poses | Evaluation Lines | Metric | Speed
```

* Use an accessible browser control or a small accessible UI pattern that supports
  selecting multiple metrics.
* The control should be disabled or visually de-emphasized until analysis returns
  evaluation-line data.
* It should still provide a clear all-metrics/default behavior.
* It should include only metrics that have returned evaluation-line data for the current
  analysis result.
* User-facing option labels should stay readable, such as `Stance width`, `Torso tilt`,
  `Tilt hold`, `Grip load`, `Rear knee sway`, `Head drift`, `Connection`, `Lead block`,
  `Hip/shoulder timing`, `Attack angle`, and `Follow-through`.
* Changing selected metrics must redraw the overlay canvas immediately.
* Changing selected metrics must not rerun analysis, change replay selection, clear
  results, delete media, or change playback speed.

### 2. Multi-Metric Evaluation-Line Filtering

Filter displayed evaluation lines by the selected metric set.

Required behavior:

* When the all-metrics/default option is active, all applicable evaluation lines are
  drawn, preserving the current behavior.
* When one or more specific metrics are selected, draw only lines whose returned
  `metric_name` is in the selected metric set.
* Filtering should apply before frame/event applicability checks.
* If no specific metric is selected after user interaction, return to the all-metrics
  behavior rather than hiding everything unexpectedly.
* The `Evaluation Lines` toggle remains the master on/off control for evaluation lines.
* If `Evaluation Lines` is off, no evaluation lines should be drawn even when metrics are
  selected.
* The `Poses` toggle remains independent and should not be affected by metric selection.
* Pose keypoint text tags must remain disabled by default.
* Event labels may remain visible according to the existing overlay behavior.

### 3. Multi-Select State Management

Keep metric selection predictable across analysis, clear, replay, and upload workflows.

Required behavior:

* After a new analysis result arrives, populate metric options from that result's
  `evaluation_overlay` data.
* Default to all metrics after analysis completes unless the implementation can safely
  preserve a previous selected set that still exists in the new result.
* When analysis is cleared, reset to all metrics and disable the control.
* When another video is selected before analysis exists, reset or disable the control so
  stale metric selections do not apply to a different video.
* If selected metrics have no lines on the current replay frame, the canvas should not
  show unrelated metric lines.
* The overlay status text should stay concise and should not cover the video. If multiple
  metrics are selected, use concise text such as `2 metric groups` instead of listing
  every selected metric.

### 4. Scrollable Evidence Columns

Make evidence-heavy columns scrollable where long evidence content or many evidence frame
values can expand the results layout.

Required behavior:

* Identify result table/list columns that display evidence content or evidence frames,
  including the `Metrics` evidence frames column and detected-fault evidence text/frames
  if applicable.
* Constrain only the evidence-heavy cell content, not the full page or full result
  section, so users can still compare rows.
* Use vertical scrolling for long multi-line evidence content.
* Avoid horizontal page scrolling for ordinary result values.
* Preserve keyboard and pointer accessibility for scrollable evidence cells.
* Empty, short, and normal evidence values should still look compact.
* The replay video, overlay controls, and analysis action buttons must not be pushed out
  of reach by long evidence content.

### 5. Tests

Add or update deterministic tests.

Required test coverage:

* Static/UI test that the metric control supports multiple selection and remains near
  overlay controls.
* Static/UI test that `Poses`, `Evaluation Lines`, metric control, and `Speed` preserve
  the expected toolbar order.
* JavaScript/static or integration test that metric options are populated from returned
  evaluation-line data.
* JavaScript/static or integration test that selecting multiple metrics filters
  evaluation lines by `metric_name`.
* Test that all-metrics/default behavior preserves existing all-line behavior.
* Test that turning `Evaluation Lines` off hides lines regardless of selected metrics.
* Test that changing metric selection redraws the canvas without rerunning analysis or
  changing playback speed.
* Static/UI or rendering-oriented test that evidence-heavy cells use bounded,
  scrollable styling.
* Existing service/API tests for evaluation-line generation and serialization must still
  pass.

Tests must not require real user videos, network access, external credentials, model
downloads, large media, or generated reports in git.

## Architecture Requirements

Keep existing boundaries:

* `app` owns browser-neutral evaluation-line primitives and metric names.
* `api` serializes returned primitives only.
* `ui` owns the multi-select metric state, filtering of already-returned primitives,
  canvas redraws, concise labels, and evidence-cell layout behavior.
* `ui` may filter lines by returned `metric_name`, but it must not calculate swing
  metrics, thresholds, deductions, drills, or baseball scoring rules.
* `motion`, `analysis`, and `feedback` should not change unless a data-contract issue is
  discovered.
* `video`, `storage`, and `sequence` must not contain swing overlay filtering rules.

An ADR is required only if this task changes the evaluation-overlay service/API contract.
If filtering and evidence scrolling are implemented entirely in the UI over existing
returned data, update the existing architecture docs and development log instead of
adding a new ADR.

## UI Requirements

### Replay Toolbar

The replay toolbar should keep overlay controls grouped and predictable:

```text
Poses | Evaluation Lines | Metric | Speed
```

On narrow screens, controls may wrap, but they must preserve order and avoid overlap with
the video, frame-step buttons, status text, or each other.

### Canvas Rendering

Required behavior:

* `Poses` controls pose skeleton lines and pose keypoints.
* `Evaluation Lines` controls evaluation-line primitives.
* The metric control filters evaluation-line primitives only.
* Multiple selected metrics should render all matching evaluation lines for those
  metrics.
* The same letterbox-aware coordinate mapping should remain shared for pose points and
  evaluation lines.
* Evaluation-line labels should remain visible for displayed lines.
* Low-confidence and fallback styling should remain unchanged.
* Raw/stabilized pose overlay source behavior must remain available for pose overlay
  data.

### Evidence Cell Layout

Required behavior:

* Evidence-heavy table cells should have a bounded max height with `overflow-y: auto`.
* Long evidence text should wrap inside the cell.
* Long frame lists should not force the whole page or table to become horizontally
  scrollable.
* The styling should be visually restrained and consistent with the existing local
  analysis UI.

## Documentation Requirements

Update documentation where behavior changes:

* `PLANS.md` with DEV004-06 planning and final-review notes.
* `docs/01_product/feature_catalog.md` if overlay behavior or evidence display behavior
  is described there.
* `docs/05_manuals/swing_motion_analysis_ui.md` to describe multi-metric evaluation-line
  overlays and scrollable evidence cells.
* `docs/02_architecture/system_overview.md` if UI data flow is updated.
* `docs/03_development_log/` with an Obsidian-compatible development log entry.

Do not create release notes, version bumps, changelog release entries, tags, Docker
deployment, hosted deployment, or PyPI packaging for this task.

## Acceptance Criteria

The task is complete only when:

* The metric control supports selecting multiple metrics.
* The control is populated from metrics that have returned evaluation-line data.
* The all-metrics/default behavior preserves current all-line overlay behavior.
* Selecting multiple metrics displays only those metrics' evaluation lines on the video.
* `Evaluation Lines` remains the master visibility toggle for evaluation lines.
* `Poses` remains independent.
* Pose keypoint text tags remain disabled by default.
* Metric selection redraws the canvas without rerunning analysis or changing replay
  speed.
* Evidence-heavy result cells are bounded and scrollable without causing broad layout
  overflow.
* Existing evaluation-line API/service contracts remain compatible unless a documented
  contract change is intentionally made.
* Tests and documentation are updated.
* Required quality commands pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

* Final-review-planning confirms acceptance criteria and unresolved risks.
* No release or deployment is created.
