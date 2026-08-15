# DEV004-05 Swing Evaluation v2 UI Update 2

## Goal

Update the local browser swing replay UI so users can select one swing v2 metric and see
only that metric's relevant evaluation lines on the video.

This is a focused UI follow-up to the existing `Poses` and `Evaluation Lines` overlay
controls. It is not a release or deployment task.

## Requested Changes

Implement these product changes:

1. Add a dropdown/select control for choosing a swing v2 metric.
2. When a metric is selected, overlay only the evaluation lines relevant to that metric
   on the replay video.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/99_prompts/DEV004-02_Swing_evaluation_v2_overlay_evaluation_lines.md`
* `docs/99_prompts/DEV004-03_Swing_evaluation_v2_UI_update.md`
* `docs/99_prompts/DEV004-04_Swing_evaluation_v2_aspect_issue.md`
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

After stored-video swing analysis completes:

* The replay toolbar has independent `Poses` and `Evaluation Lines` toggles.
* `Poses` controls pose skeleton/keypoint display.
* `Evaluation Lines` controls all returned evaluation-line primitives together.
* Evaluation-line primitives include a `metric_name` and concise label such as
  `Stance width`, `Torso tilt`, `Lead block`, `Head drift`, or `Grip path`.
* The browser draws evaluation lines only when `Evaluation Lines` is enabled and the
  line applies to the current replay frame or event frame.

The current UI does not let users isolate one metric's guide lines. This can make frames
with multiple evidence lines crowded and can make it hard to inspect one metric.

## Required Outcomes

### 1. Metric Select Dropdown

Add a dropdown/select control for selecting a metric whose evaluation lines should be
displayed.

Required behavior:

* The control should be visible near the replay overlay controls.
* Use a normal select/dropdown control, not a custom rule-calculation widget.
* The control should be disabled or visually de-emphasized until analysis returns
  evaluation-line data.
* The control should include an all-metrics option, such as `All metrics`, so existing
  behavior remains available.
* The control should include only metrics that have returned evaluation-line data for the
  current analysis result.
* User-facing option labels should be readable metric labels, not only internal snake-case
  names.
* Changing the selected metric must redraw the overlay canvas immediately.
* Changing the selected metric must not rerun analysis, change replay selection, clear
  results, delete media, or change playback speed.

### 2. Evaluation-Line Filtering

Filter the displayed evaluation lines by selected metric.

Required behavior:

* When `All metrics` is selected, all applicable evaluation lines are drawn, preserving
  the current behavior.
* When a specific metric is selected, only evaluation lines with that `metric_name` are
  drawn.
* Filtering should apply before frame/event applicability checks, so the replay still
  shows only lines relevant to the current frame or event frame.
* The `Evaluation Lines` toggle remains the master on/off control for evaluation lines.
* If `Evaluation Lines` is off, no evaluation lines should be drawn even when a metric is
  selected.
* The `Poses` toggle remains independent and should not be affected by metric selection.
* Pose keypoint text tags must remain disabled by default.
* Event labels may remain visible according to the existing overlay behavior.

### 3. Dropdown State Management

Keep dropdown state predictable across analysis, clear, replay, and upload workflows.

Required behavior:

* After a new analysis result arrives, populate metric options from that result's
  `evaluation_overlay` data.
* Default to `All metrics` after analysis completes unless the implementation can safely
  preserve a previous selection that still exists in the new result.
* When analysis is cleared, reset the dropdown to `All metrics` and disable it.
* When another video is selected before analysis exists, reset or disable the dropdown so
  stale metric filters do not apply to a different video.
* If the selected metric has no lines on the current replay frame, the canvas should not
  show unrelated metric lines.
* The overlay status text should stay concise and should not cover the video.

### 4. Metric Option Labels

Use concise labels for metric options.

Required metric label examples:

* `All metrics`
* `Stance width`
* `Torso tilt`
* `Tilt hold`
* `Grip load`
* `Rear knee sway`
* `Head drift`
* `Connection`
* `Lead block`
* `Hip/shoulder timing`
* `Attack angle`
* `Follow-through`

The exact label may be derived from returned evaluation-line labels or a UI-local display
mapping, but the browser must not calculate baseball scoring rules or thresholds.

### 5. Tests

Add or update deterministic tests.

Required test coverage:

* Static/UI test that the metric select control exists near overlay controls.
* Static/UI test that `Poses`, `Evaluation Lines`, metric select, and `Speed` preserve a
  sensible toolbar order and do not remove existing controls.
* JavaScript/static or integration test that metric options are populated from returned
  evaluation-line data.
* JavaScript/static or integration test that selecting one metric filters evaluation
  lines by `metric_name`.
* Test that `All metrics` preserves existing all-line behavior.
* Test that turning `Evaluation Lines` off hides lines regardless of selected metric.
* Test that changing metric selection redraws the canvas without rerunning analysis or
  changing playback speed.
* Existing service/API tests for evaluation-line generation and serialization must still
  pass.

Tests must not require real user videos, network access, external credentials, model
downloads, large media, or generated reports in git.

## Architecture Requirements

Keep existing boundaries:

* `app` owns browser-neutral evaluation-line primitives and metric names.
* `api` serializes returned primitives only.
* `ui` owns the metric dropdown, selected metric state, filtering of already-returned
  primitives, canvas redraws, and concise labels.
* `ui` may filter lines by returned `metric_name`, but it must not calculate swing
  metrics, thresholds, deductions, drills, or baseball scoring rules.
* `motion`, `analysis`, and `feedback` should not change unless a data-contract issue is
  discovered.
* `video`, `storage`, and `sequence` must not contain swing overlay filtering rules.

An ADR is required only if this task changes the evaluation-overlay service/API contract.
If filtering is implemented entirely in the UI over existing returned primitives, update
the existing architecture docs and development log instead of adding a new ADR.

## UI Requirements

### Replay Toolbar

The replay toolbar should keep overlay controls grouped and predictable. Recommended
order:

```text
Poses | Evaluation Lines | Metric | Speed
```

On narrow screens, controls may wrap, but they must preserve order and avoid overlap with
the video, frame-step buttons, status text, or each other.

### Canvas Rendering

Required behavior:

* `Poses` controls pose skeleton lines and pose keypoints.
* `Evaluation Lines` controls evaluation-line primitives.
* The metric dropdown filters evaluation-line primitives only.
* The same letterbox-aware coordinate mapping should remain shared for pose points and
  evaluation lines.
* Evaluation-line labels should remain visible for the selected metric's displayed lines.
* Low-confidence and fallback styling should remain unchanged.
* Raw/stabilized pose overlay source behavior must remain available for pose overlay
  data.

## Documentation Requirements

Update documentation where behavior changes:

* `PLANS.md` with DEV004-05 planning and final-review notes.
* `docs/01_product/feature_catalog.md` if overlay behavior is described there.
* `docs/05_manuals/swing_motion_analysis_ui.md` to describe metric-selective
  evaluation-line overlays.
* `docs/02_architecture/system_overview.md` if UI data flow is updated.
* `docs/03_development_log/` with an Obsidian-compatible development log entry.

Do not create release notes, version bumps, changelog release entries, tags, Docker
deployment, hosted deployment, or PyPI packaging for this task.

## Acceptance Criteria

The task is complete only when:

* A metric dropdown/select control exists near the replay overlay controls.
* The dropdown is populated from metrics that have returned evaluation-line data.
* `All metrics` preserves current all-line overlay behavior.
* Selecting one metric displays only that metric's evaluation lines on the video.
* `Evaluation Lines` remains the master visibility toggle for evaluation lines.
* `Poses` remains independent.
* Pose keypoint text tags remain disabled by default.
* Metric selection redraws the canvas without rerunning analysis or changing replay
  speed.
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

## Final Review Checklist

Before final response, confirm:

* The implementation followed `planning -> architecture -> coding -> quality-assurance ->
  final-review-planning`.
* Metric filtering is UI-only unless a contract issue required service/API changes.
* The dropdown filters by returned `metric_name`, not by recalculating baseball rules.
* All overlay controls remain accessible and do not overlap at common desktop/mobile
  widths.
* Existing pose/evaluation-line toggles were not regressed.
* Documentation was updated.
* Required quality commands passed, or any failure is clearly reported with the reason.
* No release or deployment work was performed.
