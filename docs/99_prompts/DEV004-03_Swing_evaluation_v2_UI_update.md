# DEV004-03 Swing Evaluation v2 UI Update

## Goal

Update the local browser swing replay UI after DEV004-02 so overlay controls are clearer,
the video library remains usable with many uploaded videos, and all required swing v2
evaluation lines are visible when returned by analysis.

This task is a UI and verification update for the existing swing evaluation v2 workflow.
It is not a release or deployment task.

## Requested Changes

Implement these product changes:

1. Make the `Video Library` panel scrollable.
2. Add a separate `Poses` button immediately in front of `Evaluation Lines` in the replay
   toolbar to enable or disable the pose overlay.
3. Disable pose tags/labels so pose keypoint text such as `Head`, `L Wrist`, or
   `R Wrist` does not clutter the video.
4. Check why some evaluation lines may not be displayed, then update the implementation
   so all required DEV004-02 evaluation-line types are generated, returned, and rendered
   when evidence exists.
5. Improve labeling so the user can distinguish pose overlays from evaluation lines.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/99_prompts/DEV004-02_Swing_evaluation_v2_overlay_evaluation_lines.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
* `docs/02_architecture/adr/ADR-0010-swing-evaluation-overlay-lines.md`
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

## Current Findings

The current replay UI has:

* A `Video Library` list rendered in the left column without an explicit scrollable
  viewport for long libraries.
* A single `Evaluation Lines` replay-toolbar toggle immediately before `Speed`.
* Pose skeleton lines and pose keypoints drawn whenever pose overlay frames exist.
* Pose keypoint labels drawn on event frames for selected keypoints such as head and
  wrists.
* Evaluation lines drawn only when `evaluationLinesEnabled` is on and the line
  `frame_index` exactly matches the nearest overlay frame.

The DEV004-02 app service has a first implementation of `build_evaluation_overlay_lines`
that should produce lines for all swing v2 metrics when evidence exists. DEV004-03 must
verify this against the required metric list instead of assuming the existing output is
complete.

## Required Outcomes

### 1. Scrollable Video Library

Make the `Video Library` list scrollable when there are many videos.

Required behavior:

* The upload panel and replay panel should not be pushed far down by a long library.
* The library should have a sensible max height on desktop and narrow screens.
* Library item buttons must remain reachable by keyboard and mouse.
* The layout must not introduce horizontal scrolling for ordinary video names.
* Empty, loading, error, and one-item library states should still look normal.

### 2. `Poses` Toggle Button

Add a `Poses` toggle button immediately before `Evaluation Lines` in the replay toolbar:

```text
Poses | Evaluation Lines | Speed
```

Required behavior:

* Visible button text: `Poses`.
* Use `aria-pressed` for toggle state.
* Default to on after pose overlay data exists.
* Disable or visually de-emphasize before analysis overlay data exists.
* Toggling `Poses` must redraw the canvas immediately.
* Toggling `Poses` must not rerun analysis, change replay selection, clear results,
  delete media, or change playback speed.
* `Evaluation Lines` should remain independently toggleable.
* Users should be able to show:
  * poses only
  * evaluation lines only
  * both
  * neither

### 3. Disable Pose Tags

Remove or disable pose keypoint text tags from the replay overlay.

Required behavior:

* Do not draw pose keypoint text labels such as `Head`, `L Wrist`, `R Wrist`, or `Bat`
  on the video during normal replay.
* Keep pose circles and skeleton lines available when `Poses` is enabled.
* Keep event-frame highlighting available without pose text tags.
* Do not remove evaluation-line labels.
* If a future debug mode needs pose labels, it should be controlled separately and remain
  off by default. Do not add that debug mode unless needed for this task.

### 4. Display All Required Evaluation Lines

Audit and fix evaluation-line construction and rendering so all required DEV004-02 line
types appear when their evidence exists:

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

Required investigation:

* Confirm that service output includes line primitives for every metric whose required
  evidence is available.
* Confirm the API serializes all returned lines.
* Confirm the browser can render lines whose evidence frame differs from the current
  nearest pose frame when appropriate for the selected event or evidence frame.
* Confirm lines with multi-frame evidence are visible on the intended evidence frame(s),
  not silently hidden because the exact current frame does not match.
* Confirm missing keypoints still skip or lower confidence without crashing.
* Confirm bat/ball evidence is not fabricated. MediaPipe body pose still does not detect
  bat tip, bat barrel, or ball position unless those keypoints are supplied by another
  source.

Do not change v2 scoring thresholds, deductions, drill mapping, or fault logic unless a
line cannot be produced due to an actual data-contract bug.

### 5. Labeling For Pose And Evaluation Line Overlays

Improve overlay labeling so users can distinguish `Poses` from `Evaluation Lines`.

Required behavior:

* The replay toolbar button labels should be the primary labels:
  * `Poses`
  * `Evaluation Lines`
* Evaluation-line labels should remain concise and visually distinct from event labels.
* Evaluation-line labels should identify what the line represents, for example
  `Stance width`, `Torso tilt`, `Lead block`, `Head drift`, or `Grip path`.
* Pose overlays should not use per-keypoint text tags after this task.
* The overlay status line should summarize active overlay modes without becoming long or
  covering the video.
* Event labels such as `Setup`, `Impact`, or `Follow-through` may remain, but they should
  not be confused with evaluation-line labels.

## Architecture Requirements

Keep existing boundaries:

* `app` owns browser-neutral evaluation-line primitives and any fixes to line
  construction from analysis evidence and pose frames.
* `api` serializes returned primitives only.
* `ui` owns local display controls, scroll behavior, toggle state, canvas drawing, and
  concise UI labels.
* `ui` and `api` must not calculate v2 thresholds, scoring deductions, drill mapping, or
  baseball coaching rules.
* `video`, `storage`, and `sequence` must not contain swing overlay rules.

An ADR is required only if this task materially changes the evaluation-overlay service
contract beyond adding UI controls and fixing completeness bugs.

## UI Requirements

### Replay Toolbar

The replay toolbar should use this order:

```text
Poses | Evaluation Lines | Speed
```

On narrow screens, controls may wrap, but they must preserve order and avoid overlap with
the video, frame-step buttons, status text, or each other.

### Canvas Rendering

Required behavior:

* `Poses` controls pose skeleton lines and pose keypoints.
* `Evaluation Lines` controls evaluation-line primitives only.
* Event labels and event highlighting should still work when either overlay mode is on.
* The canvas should be cleared and redrawn when either toggle changes.
* Letterbox-aware coordinate mapping must remain shared for pose points and evaluation
  lines.
* Raw/stabilized overlay source behavior must remain available for pose overlay data.
* Evaluation lines should not disappear solely because raw pose source is selected if
  the line geometry is service-returned and frame-aligned to the analyzed evidence.

## Testing Requirements

Add or update deterministic tests without private videos, network access, external
credentials, model downloads, large media, or generated reports in git.

Required tests:

* UI/static test that `Video Library` has scrollable styling and does not remove existing
  upload/library/replay behavior.
* UI/static test that `Poses` appears immediately before `Evaluation Lines`, and
  `Evaluation Lines` remains immediately before `Speed`.
* JavaScript/static or integration test that `Poses` and `Evaluation Lines` have
  independent toggle state and redraw behavior.
* JavaScript/static or integration test that toggling `Poses` does not change playback
  speed or rerun analysis.
* Test that pose keypoint text tags are disabled while pose circles/skeleton rendering
  remains available when `Poses` is enabled.
* Unit test that evaluation-line construction returns all required line categories for a
  deterministic synthetic swing with complete evidence.
* Unit or integration test that missing keypoints skip or lower confidence for affected
  lines without preventing other required lines from being returned.
* API test that `/api/v1/analysis/swing/video` serializes all returned evaluation line
  primitives and does not expose absolute paths.
* Regression tests for existing replay speed, frame stepping, clear analysis,
  raw/stabilized overlay source, event highlighting, upload, library, and replay
  behavior where practical.

## Documentation Requirements

Update:

* `PLANS.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md` if behavior or service contract changes
* `docs/05_manuals/swing_motion_analysis_ui.md`
* `docs/03_development_log/`

Documentation must explain:

* The `Video Library` is scrollable when many videos exist.
* `Poses` toggles pose overlay visibility.
* `Evaluation Lines` toggles service-returned evaluation-line visibility.
* Pose keypoint text tags are disabled by default to reduce clutter.
* Evaluation-line labels identify metric evidence and are distinct from pose overlays.
* MediaPipe still detects body landmarks only; bat/ball-specific evidence remains
  limited unless future detectors add those keypoints.

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

* `Video Library` scrolls without breaking upload/library/replay behavior.
* `Poses` is immediately before `Evaluation Lines`, and `Evaluation Lines` is before
  `Speed`.
* `Poses` and `Evaluation Lines` toggles are independent.
* Pose tags are disabled.
* All required DEV004-02 evaluation-line types display when evidence exists.
* UI/API adapters do not compute baseball rules.
* Tests cover UI/static behavior, JavaScript toggle behavior, service/API line
  completeness, and regressions.
* Docs and `PLANS.md` are updated.
* No release or deployment was created.
