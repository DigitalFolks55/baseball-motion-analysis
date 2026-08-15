# DEV004-02 Swing Evaluation v2 Overlay Evaluation Lines

## Goal

Add optional evaluation-line overlays to the video replay canvas for swing evaluation v2.

After a stored-video swing analysis completes, the replay overlay should be able to draw
evaluation-specific guide lines in addition to the existing pose keypoints and event
metadata. Users should be able to turn these evaluation lines on or off with a toggle
button located immediately to the left of the existing `Speed` control in the replay
toolbar.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Existing implementation:
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/analysis/swing.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_analysis_api.py`
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
web service, PyPI package, or version tag.

## Current Findings

The browser replay panel already has:

* An HTML5 video player.
* A `poseOverlayCanvas` canvas over the rendered video content.
* Existing overlay drawing for pose keypoints, event frames, labels, low-confidence
  points, raw/stabilized overlay sources, and replay-to-pose-frame offset.
* A replay toolbar with previous-frame, next-frame, and `Speed` controls.

DEV004-01 made swing v2 the normal analysis methodology and added metric units and
methodology metadata. The current UI renders metric tables and detected faults, but it
does not draw metric-specific evaluation lines on the replay video.

## Required Outcomes

Implement optional evaluation-line overlays:

1. Add a toggle button immediately to the left of the `Speed` control in the replay
   toolbar.
2. The button should turn evaluation lines on and off without rerunning analysis.
3. Evaluation lines should be hidden by default before analysis results exist.
4. After analysis completes, the button should allow the user to show or hide returned
   evaluation lines.
5. The replay overlay should continue to draw pose keypoints and event metadata as it
   does now.
6. Evaluation-line geometry must come from application/domain data returned by the
   analysis service, not from baseball-rule calculations inside browser JavaScript.

## Scope

In scope:

* Add typed evaluation-line overlay models to the application/API response.
* Generate evaluation-line primitives from v2 analysis evidence and pose frames.
* Render returned line primitives on the existing `poseOverlayCanvas`.
* Add the replay-toolbar toggle button next to the `Speed` control.
* Add tests for service output, API serialization, UI/static markup, and JavaScript
  rendering behavior.
* Update product, architecture, manual, development-log, and planning docs where
  behavior changes.

Out of scope:

* New swing scoring rules or threshold changes.
* New pose-estimation model behavior.
* Bat tip, bat barrel, or ball detector implementation.
* Report persistence.
* Throwing, pitching, or fielding analysis.
* Hosted services, authentication, deployment, packaging, version bump, release notes, or
  changelog release work.

## Architecture Requirements

Keep the existing boundaries:

* `motion` and `analysis` may identify which v2 metric evidence should be visualized.
* `app` should build browser-neutral evaluation overlay primitives from analysis results
  and pose frames.
* `api` should serialize returned primitives without computing baseball rules.
* `ui` should only toggle and draw returned primitives.
* `video`, `storage`, and `sequence` must not contain baseball overlay rules.

Do not calculate v2 thresholds, deductions, or drill logic in `ui` or `api`.

## Data Model Requirements

Add typed models for evaluation overlays. Suggested shape:

```text
EvaluationOverlayLine
  metric_name: str
  phase: str
  frame_index: int
  start_keypoint_name: str | None
  end_keypoint_name: str | None
  start: normalized point
  end: normalized point
  label: str
  severity: str
  confidence: float
  style: solid | dashed | reference
  color_role: good | warning | severe | neutral | low_confidence
```

If a line is derived from a midpoint or virtual point, `start_keypoint_name` or
`end_keypoint_name` may be `None`, but the normalized point coordinates must still be
returned explicitly.

Return evaluation lines separately from pose keypoints so the UI can toggle them without
affecting the normal pose overlay.

## Evaluation Lines To Support

Implement a practical first set tied to DEV004-01 metrics:

* Normalized stance width:
  * line between lead and rear ankles on setup frame
* Torso forward tilt:
  * line from hip midpoint to shoulder midpoint on setup frame
* Torso tilt preservation:
  * torso line on setup and impact frames
* Grip loading vector:
  * line or marker from grip proxy to rear-foot support reference on setup/loading frame
* Rear knee sway:
  * line from setup rear ankle boundary to stride rear knee
* Head translation ratio:
  * line from setup head proxy to impact head proxy
* Early connection angle:
  * line from lead shoulder to lead wrist at foot strike or rotation start
* Lead knee blocking index:
  * lead hip-knee and knee-ankle segments at foot strike and impact
* Hip-shoulder separation timing:
  * hip axis and shoulder axis lines on evidence frames
* Estimated attack angle:
  * grip or bat trajectory line around impact, using lower-confidence styling when bat
    keypoints are missing
* Follow-through posture/balance:
  * torso or head stability line from impact to follow-through

When required keypoints are missing or low confidence, skip the affected line or return
it with low-confidence styling and a limitation. Do not fabricate bat or ball evidence.

## UI Requirements

### Toggle Button

Add a toggle button immediately to the left of the existing `Speed` control in the replay
toolbar.

Required behavior:

* Use visible button text such as `Evaluation Lines`.
* Use `aria-pressed` to expose the toggle state.
* Default to off.
* Disable or visually de-emphasize the button until analysis overlay data is available.
* Toggling should redraw the canvas immediately.
* Toggling should not rerun analysis, change replay selection, clear results, delete
  media, or change playback speed.
* On mobile, the button must not overlap the speed selector, frame-step buttons, video,
  or status text.

### Canvas Rendering

Required behavior:

* Evaluation lines should map normalized coordinates into the rendered video content
  rectangle, using the same letterbox-aware mapping as pose keypoints.
* Lines should remain aligned during playback, frame stepping, resizing, and raw vs
  stabilized overlay source changes.
* Lines should be drawn only when their frame evidence applies to the currently selected
  nearest overlay frame or event frame.
* Severity should be visually distinguishable with line style or color role.
* Labels should be concise and should not cover key video controls.
* Low-confidence or fallback lines should be visually distinct.

Do not add explanatory in-app text about how evaluation lines work beyond the button
label and existing result sections.

## API And Service Requirements

Preserve:

* `POST /api/v1/analysis/swing`
* `POST /api/v1/analysis/swing/video`
* Existing pose overlay response fields
* Existing raw/stabilized overlay behavior
* Existing event metadata

For stored-video analysis, add evaluation lines to the response. Prefer a field name such
as:

```text
evaluation_overlay
```

or:

```text
evaluation_lines
```

The response must remain browser-safe and must not expose absolute file paths.

## Testing Requirements

Add or update deterministic tests without private videos, network access, external
credentials, model downloads, large media, or generated reports in git.

Required tests:

* Unit test that evaluation-line construction returns expected line primitives for a
  deterministic v2 synthetic swing.
* Unit or integration test that missing keypoints skip or lower confidence for the
  affected evaluation line without crashing.
* Application-service test that stored-video swing analysis returns evaluation overlay
  lines with metric names, frame indexes, normalized coordinates, severity, and
  confidence.
* API test that `/api/v1/analysis/swing/video` serializes evaluation overlay lines and
  does not expose absolute paths.
* UI/static test that the `Evaluation Lines` toggle button appears immediately before
  the `Speed` control.
* JavaScript/static or integration test that toggling evaluation lines updates canvas
  state without changing playback speed or rerunning analysis.
* Regression tests for existing pose overlay, raw/stabilized overlay source, event
  highlighting, replay speed, frame stepping, clear analysis, and upload/library/replay
  behavior where practical.

## Documentation Requirements

Update:

* `PLANS.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* `docs/03_development_log/`

Update ADRs only if the implementation changes service/API semantics beyond adding
browser-safe overlay primitives. If evaluation-line generation introduces a reusable
domain/service contract, add an ADR.

Documentation must explain:

* Evaluation lines are optional visual aids over returned analysis evidence.
* The `Evaluation Lines` button toggles those lines without rerunning analysis.
* Evaluation-line geometry is returned by the analysis service and rendered by the UI.
* MediaPipe still detects body landmarks only; bat/ball evidence remains limited unless
  future detectors are added.

## Quality Gates

After code changes, run:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed, run:

```bash
uv run ruff format .
```

Final review should confirm:

* Evaluation-line overlays are optional and toggleable.
* The toggle button is immediately left of `Speed`.
* UI/API adapters do not compute baseball rules.
* Tests cover service, API, UI/static, and JavaScript behavior.
* Existing replay, pose overlay, raw/stabilized overlay, speed, and frame-step behavior
  still works.
* Docs and `PLANS.md` are updated.
* No release or deployment was created.
