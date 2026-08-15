# DEV004-07 Swing Evaluation v2 UI Update 4

## Goal

Update the local browser swing evaluation UI so the `Metric` control looks and behaves
like a compact dropdown beside `Speed`, while preserving multi-metric overlay filtering
from DEV004-06. Also tighten evidence-heavy table columns and make any oversized table
content scrollable without expanding the page layout.

This is a focused UI follow-up to DEV004-06. It is not a release or deployment task.

## Requested Changes

Implement these product changes:

1. Make the `Metric` control a compact dropdown-box style control similar to the `Speed`
   select in the replay toolbar.
2. Make the `Evidence` column in the `Metrics` table narrower, sized to display about
   five frame numbers before scrolling or wrapping.
3. If any tables contain huge content, constrain that content and enable scrolling so the
   table remains usable.

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
* `docs/99_prompts/DEV004-06_Swing_evaluation_v2_UI_update_3.md`
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

After DEV004-06:

* The replay toolbar order is `Poses`, `Evaluation Lines`, `Metric`, then `Speed`.
* `Metric` is a native multi-select list with multiple rows visible.
* `All metrics` or no specific metric selection displays all returned evaluation lines.
* Selecting one or more metric options displays only evaluation lines whose returned
  `metric_name` is in the selected set.
* `Evaluation Lines` remains the master on/off control.
* `Poses` remains independent.
* Metric evidence frames and detected-fault evidence text have bounded scrollable
  wrappers.

The visible multi-row `Metric` select takes more toolbar height than desired. The UI
should instead present a compact dropdown-box style control like `Speed`, while still
allowing multiple metric selections. The `Metrics` table evidence column can also consume
too much width when evidence frame lists grow.

## Required Outcomes

### 1. Compact Dropdown-Style Metric Control

Replace or restyle the current visible multi-row metric selector so it appears as a
compact dropdown-box style control in the replay toolbar.

Required behavior:

* The visible control should be similar in height and visual weight to the `Speed`
  dropdown.
* The toolbar order must remain:

```text
Poses | Evaluation Lines | Metric | Speed
```

* The control must still support selecting multiple metrics.
* `All metrics` must remain available as the default behavior.
* It should be disabled or visually de-emphasized until analysis returns evaluation-line
  data.
* It should include only metrics that have returned evaluation-line data for the current
  analysis result.
* User-facing option labels should remain readable, such as `Stance width`, `Torso tilt`,
  `Tilt hold`, `Grip load`, `Rear knee sway`, `Head drift`, `Connection`, `Lead block`,
  `Hip/shoulder timing`, `Attack angle`, and `Follow-through`.
* Changing selected metrics must redraw the overlay canvas immediately.
* Changing selected metrics must not rerun analysis, change replay selection, clear
  results, delete media, or change playback speed.

Acceptable implementation approaches:

* A native dropdown-like button that opens a small checkbox menu for metrics.
* A compact native select if the implementation can preserve multi-selection without
  exposing a tall list.
* Another accessible compact control that clearly behaves as a dropdown and supports
  multiple selected metrics.

Avoid building baseball rule calculation or threshold logic in the browser.

### 2. Multi-Metric Filtering Must Remain Correct

Preserve DEV004-06 filtering behavior.

Required behavior:

* When `All metrics` is active, all applicable returned evaluation lines are drawn.
* When one or more specific metrics are selected, draw only lines whose returned
  `metric_name` is in the selected set.
* Filtering must apply before frame/event applicability checks.
* If no specific metric is selected after user interaction, return to the all-metrics
  behavior rather than hiding everything unexpectedly.
* The `Evaluation Lines` toggle remains the master on/off control.
* The `Poses` toggle remains independent.
* Pose keypoint text tags must remain disabled by default.

### 3. Narrow Metrics Evidence Column

Make the `Evidence` column in the `Metrics` table narrower.

Required behavior:

* The column should be sized for approximately five frame numbers, for example a compact
  width that can comfortably show values like `12, 24, 36, 48, 60`.
* Longer evidence frame lists should wrap or vertically scroll inside the cell instead of
  widening the table or page.
* Normal short evidence frame lists should remain compact and readable.
* The metrics table should still allow users to compare metric name, value, unit, target,
  severity, deduction, and evidence without horizontal layout blowout.

### 4. Scroll Huge Table Content

Audit result tables and table-like sections for cells that can contain huge content.

Required behavior:

* Constrain oversized table cell content with bounded height and scrolling where
  appropriate.
* Apply this to any relevant table, including `Metrics`, phase-score rows if future
  content grows, diagnostics tables/lists if they contain long values, and any table-like
  result areas touched by this task.
* Do not make every table row unnecessarily tall.
* Do not hide content permanently; users must be able to scroll or otherwise access the
  full content.
* Avoid horizontal page scrolling for ordinary values.
* Preserve keyboard and pointer accessibility for scrollable content.
* Keep styling restrained and consistent with the current local analysis UI.

### 5. Tests

Add or update deterministic tests.

Required test coverage:

* Static/UI test that the `Metric` control is compact/dropdown-style and remains near
  overlay controls.
* Static/UI test that `Poses`, `Evaluation Lines`, `Metric`, and `Speed` preserve the
  expected toolbar order.
* JavaScript/static or integration test that the compact metric control still supports
  multiple selected metrics.
* JavaScript/static or integration test that metric options are populated from returned
  evaluation-line data.
* JavaScript/static or integration test that selected metric sets filter evaluation lines
  by `metric_name`.
* Test that `All metrics` preserves existing all-line behavior.
* Test that turning `Evaluation Lines` off hides lines regardless of selected metrics.
* Test that changing metric selection redraws the canvas without rerunning analysis or
  changing playback speed.
* Static/UI or rendering-oriented test that the `Metrics` table evidence column is
  compact, bounded, and scrollable.
* Static/UI or rendering-oriented test that huge table content uses bounded scrollable
  styling.
* Existing service/API tests for evaluation-line generation and serialization must still
  pass.

Tests must not require real user videos, network access, external credentials, model
downloads, large media, or generated reports in git.

## Architecture Requirements

Keep existing boundaries:

* `app` owns browser-neutral evaluation-line primitives and metric names.
* `api` serializes returned primitives only.
* `ui` owns the compact metric dropdown presentation, multi-selected metric state,
  filtering of already-returned primitives, canvas redraws, concise labels, and table
  layout behavior.
* `ui` may filter lines by returned `metric_name`, but it must not calculate swing
  metrics, thresholds, deductions, drills, or baseball scoring rules.
* `motion`, `analysis`, and `feedback` should not change unless a data-contract issue is
  discovered.
* `video`, `storage`, and `sequence` must not contain swing overlay filtering rules.

An ADR is required only if this task changes the evaluation-overlay service/API contract.
If this is implemented entirely in the UI over existing returned data, update the
existing architecture docs and development log instead of adding a new ADR.

## UI Requirements

### Replay Toolbar

The replay toolbar should keep overlay controls grouped and predictable:

```text
Poses | Evaluation Lines | Metric | Speed
```

The `Metric` control should look like a dropdown box, not a tall list. On narrow screens,
controls may wrap, but they must preserve order and avoid overlap with the video,
frame-step buttons, status text, or each other.

### Canvas Rendering

Required behavior:

* `Poses` controls pose skeleton lines and pose keypoints.
* `Evaluation Lines` controls evaluation-line primitives.
* The metric dropdown filters evaluation-line primitives only.
* Multiple selected metrics should render all matching evaluation lines for those
  metrics.
* The same letterbox-aware coordinate mapping should remain shared for pose points and
  evaluation lines.
* Evaluation-line labels should remain visible for displayed lines.
* Low-confidence and fallback styling should remain unchanged.
* Raw/stabilized pose overlay source behavior must remain available for pose overlay
  data.

### Table Layout

Required behavior:

* The `Metrics` table evidence column should be compact and visibly narrower than wide
  text columns.
* Evidence frame lists should wrap or scroll inside a bounded cell.
* Huge content in any table should have a bounded scrollable area.
* The table should remain readable on desktop and narrow screens.
* The styling should avoid large decorative cards or unrelated visual redesign.

## Documentation Requirements

Update documentation where behavior changes:

* `PLANS.md` with DEV004-07 planning and final-review notes.
* `docs/01_product/feature_catalog.md` if overlay behavior or table evidence behavior is
  described there.
* `docs/05_manuals/swing_motion_analysis_ui.md` to describe the compact multi-metric
  dropdown and table scrolling behavior.
* `docs/02_architecture/system_overview.md` if UI data flow is updated.
* `docs/03_development_log/` with an Obsidian-compatible development log entry.

Do not create release notes, version bumps, changelog release entries, tags, Docker
deployment, hosted deployment, or PyPI packaging for this task.

## Acceptance Criteria

The task is complete only when:

* The `Metric` control appears as a compact dropdown-box style control like `Speed`.
* The `Metric` control still supports selecting multiple metrics.
* The control is populated from metrics that have returned evaluation-line data.
* `All metrics` preserves current all-line overlay behavior.
* Selecting multiple metrics displays only those metrics' evaluation lines on the video.
* `Evaluation Lines` remains the master visibility toggle for evaluation lines.
* `Poses` remains independent.
* Pose keypoint text tags remain disabled by default.
* Metric selection redraws the canvas without rerunning analysis or changing replay
  speed.
* The `Metrics` table evidence column is narrower and sized for about five frame numbers.
* Huge table content is bounded and scrollable without causing broad layout overflow.
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
