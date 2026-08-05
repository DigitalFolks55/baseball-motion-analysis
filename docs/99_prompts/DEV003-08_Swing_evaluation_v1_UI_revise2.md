# DEV003-08 Swing Evaluation v1 UI Revision 2

## Goal

Make a small UI revision to the video-driven swing analysis screen after DEV003-07.

The changes should improve clarity for normal users by renaming the debug pose mode from
`notebook parity` to `single pose`, reorganizing the review layout so replay is wider,
moving lower-priority diagnostic detail under a foldable section, and resolving confusing
confidence values in the detected-event display.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-06_Swing_evaluation_v1_improve_performance.md`
* `docs/99_prompts/DEV003-07_Swing_evaluation_v1_improve_performance_2.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Existing implementation:
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/motion/swing.py`
* Existing tests:
  * `tests/integration/test_web_video_upload_replay_api.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/unit/test_swing_motion_metrics.py`

## Required Agent Workflow

Follow the repository workflow in order:

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
```

Do not run the release agent. Do not create a release or deployment.

## Current Findings

DEV003-07 added an advanced pose debug mode named `notebook parity`. That name is useful
for engineering diagnosis, but it is too implementation-specific for the local browser UI.
The user-facing label should describe the behavior: single-pose MediaPipe detection
without temporal stabilization.

The current review layout also leaves the replay/video area too narrow relative to the
analysis controls. For visual pose review, the video should be the dominant element.

The `Motion Analysis` panel currently exposes limitations and pose-quality diagnostics as
normal top-level result sections. These are useful, but they are secondary and should be
available under a foldable area near the bottom of the motion-analysis panel.

The `Detected Events And Phase Scores` area can show confidence values in more than one
place. Investigate why the event description confidence and the phase-score table
confidence can differ, and make the UI copy or data display clear and internally
consistent.

## Required Outcomes

Implement these UI revisions:

1. Change the visible menu option name from `Notebook parity` to `Single pose`.
2. Change the pose mode label and visible copy to use:
   * `Normal`
   * `Single pose`
3. Revise the main UI layout to:

   ```text
   | Video upload  | Video (wider) |
   | Video library | Video (wider) |
   |        Motion analysis       |
   ```

4. Move the following result areas under a foldable box located at the bottom of
   `Motion Analysis`:
   * `Limitations`
   * `Pose Quality`
5. Investigate why confidence values differ between the detected-event descriptions and
   the phase-score table in `Detected Events And Phase Scores`, then fix the UI or data
   presentation so the difference is clear and not misleading.

## Scope

In scope:

* Browser template, CSS, and JavaScript changes needed for the revised layout.
* UI/API label changes from `notebook parity` to `single pose`.
* Backward-compatible request handling if the internal API value remains
  `notebook_parity`.
* Tests for visible UI labels, layout markers, foldable diagnostics, and confidence
  display behavior.
* Documentation updates for the renamed pose mode and revised UI layout.

Out of scope:

* New pose-estimation algorithms.
* New baseball swing scoring rules unless the confidence mismatch is caused by a bug.
* Bat, barrel, or ball detection.
* Throwing, pitching, or fielding implementation.
* Report persistence.
* Release notes, version bump, packaging, hosted deployment, Docker, or production
  deployment.

## UI Requirements

### Pose Mode Naming

The user-facing UI must not show `Notebook parity` as a menu option.

Use:

```text
Normal
Single pose
```

Implementation guidance:

* It is acceptable to keep the internal API value `notebook_parity` if that avoids
  breaking DEV003-07 diagnostics.
* If adding a new public API value `single_pose`, keep `notebook_parity` as a deprecated
  backward-compatible alias unless there is a clear reason not to.
* User-facing documentation and UI copy should describe the mode as single-pose raw
  MediaPipe diagnostics, not notebook implementation parity.

### Layout

Revise the browser review layout so the video is wider and occupies the right side of the
top two rows:

```text
| Video upload  | Video (wider) |
| Video library | Video (wider) |
|        Motion analysis       |
```

Required behavior:

* The video/replay panel should be visually dominant on desktop.
* Upload and library should remain usable on the left.
* Motion analysis should span the lower area below upload/library and video.
* Mobile layout should remain readable, stacked, and free of overlapping text or controls.
* Existing upload, library, replay, delete, frame-step, playback speed, run analysis, and
  clear analysis behavior must continue to work.

### Foldable Result Sections

Move the following under one foldable box at the bottom of `Motion Analysis`:

* `Limitations`
* `Pose Quality`

Required behavior:

* The foldable box should be available after analysis results render.
* The default open/closed state should favor the normal user workflow. Prefer closed by
  default unless tests or design constraints indicate otherwise.
* Good points, improvement points, drills, detected events, phase scores, metrics, and
  detected faults should remain visible outside this foldable diagnostics box.
* The limitations content must not be removed from the API or service response.

### Confidence Display Investigation

Investigate the confidence mismatch in `Detected Events And Phase Scores`.

Likely explanation to verify:

* Event description confidence may come from swing event/phase detection confidence.
* Phase-score table confidence may come from the confidence of that phase's scoring
  evidence or from the analysis phase score model.

Required behavior:

* If the two confidence values intentionally mean different things, label them clearly in
  the UI. Example labels:
  * `Event confidence`
  * `Score confidence`
* If the two values are unintentionally different due to adapter or rendering mismatch,
  fix the source of truth so the values are consistent.
* Add tests that prevent the confusing display from returning.
* Do not hide confidence values entirely; confidence is part of the product's uncertainty
  explanation.

## API And Service Requirements

Avoid API changes unless they are needed to make the confidence display unambiguous or to
support the `Single pose` naming cleanly.

If API changes are needed:

* Keep `POST /api/v1/analysis/swing/video`.
* Keep existing DEV003-07 response fields backward-compatible.
* Do not expose absolute filesystem paths.
* Preserve local-only processing.

## Testing Requirements

Add or update deterministic tests without private videos, network access, external
credentials, or large model files.

Required tests:

* UI/static test that `Single pose` appears and `Notebook parity` does not appear in the
  browser page.
* UI/static test that the revised layout exposes upload/library on the left, wider video
  replay on the right, and motion analysis below.
* UI/static test that `Limitations` and `Pose Quality` are inside a foldable diagnostics
  area at the bottom of motion analysis.
* JS/static or integration test that the API request still sends the correct internal
  pose-mode value when `Single pose` is selected.
* Test for the detected-event confidence display:
  * either labels event confidence and score confidence distinctly,
  * or proves the displayed values use the same intended source.
* Regression tests for existing upload, library, replay, video analysis, raw/stabilized
  overlay, clear analysis, and unsupported motion-type behavior where practical.

## Documentation Requirements

Update:

* `PLANS.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* `docs/03_development_log/`

Update ADRs only if the implementation changes API/service semantics or architectural
boundaries. A pure UI layout/label change does not require a new ADR.

Documentation must explain:

* `Single pose` is the user-facing name for the raw single-pose diagnostic mode.
* Normal users should generally use `Normal`.
* Limitations and pose-quality diagnostics are still available, but grouped under
  diagnostics.
* The confidence display distinction or fix for detected events and phase scores.

## Quality Gates

After implementation, run:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

Also run a local app startup smoke check and confirm the root page returns HTTP 200.

## Acceptance Criteria

The task is complete only when:

* The visible UI uses `Single pose`, not `Notebook parity`.
* The pose mode choices are `Normal` and `Single pose`.
* The desktop layout matches the requested upload/library-left, wider-video-right,
  motion-analysis-bottom structure.
* The mobile layout remains readable with no overlapping controls or text.
* Limitations and pose quality are under a foldable diagnostics box at the bottom of
  motion analysis.
* Event confidence versus phase-score confidence is investigated and either fixed or
  clearly labeled.
* Existing video-driven swing analysis behavior still works.
* Tests and documentation are updated.
* Required quality gates pass.
* Final planning review has no blocking issue.
* No release or deployment is created.
