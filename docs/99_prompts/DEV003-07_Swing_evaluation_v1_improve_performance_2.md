# DEV003-07 Swing Evaluation v1 Pose Performance Improvements 2

## Goal

Fix the remaining pose-estimation quality gap observed after DEV003-06.

`data/test.png` shows poor pose overlay quality in the application path, while manual
testing in `notebooks/media_input.ipynb` can produce acceptable MediaPipe landmarks on a
similar cluttered baseball swing image. This task should make the app's MediaPipe path
match the notebook baseline first, then reintroduce quality improvements only when they
are proven not to degrade the detected pose.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-04_Swing_evaluation_v1_update_core_algo.md`
* `docs/99_prompts/DEV003-05_Swing_evaluation_v1_pose_estimator.md`
* `docs/99_prompts/DEV003-06_Swing_evaluation_v1_improve_performance.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0007-mediapipe-pose-estimator.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* Existing manuals under `docs/05_manuals/`
* `notebooks/media_input.ipynb`
* The image or source frame used for local diagnosis:
  * `data/test.png`
  * the original unannotated frame if available
* Existing implementation:
  * `src/baseball_motion_analysis/pose/`
  * `src/baseball_motion_analysis/video/`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/unit/test_pose_estimation.py`
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`

## Current Findings

The immediate finding is that notebook MediaPipe output and app overlay output can differ
even on visually similar frames.

Likely causes to investigate:

1. `notebooks/media_input.ipynb` uses MediaPipe image mode:
   `detector.detect(image)`.
2. The app uses MediaPipe video mode:
   `detect_for_video(image, timestamp_ms)`.
3. The notebook likely uses MediaPipe's default single-pose behavior.
4. DEV003-06 defaults the app to `num_poses=2`; in a cluttered scene this can introduce
   a false background candidate and make app-side best-player selection worse.
5. The app applies temporal smoothing, short-gap interpolation, and outlier rejection.
   These are useful across video but can degrade very fast wrist, foot, or bat-adjacent
   movement if applied too aggressively.
6. The app overlay may show the nearest sampled frame rather than the exact frame visible
   in replay.
7. `data/test.png` appears to be an annotated screenshot. Pose estimation must run on the
   original unannotated frame, not on an image that already contains overlay markers,
   labels, lines, or UI controls.

## Required Outcomes

Implement a reproducible notebook-parity diagnosis and fix path.

Required outcomes:

1. Add a way to compare raw MediaPipe image-mode output and app video-mode output for the
   same frame.
2. Add a "notebook parity" or equivalent debug quality mode that uses:
   * one pose,
   * no smoothing,
   * no interpolation,
   * no outlier rejection,
   * raw MediaPipe coordinates,
   * no silent heuristic fallback.
3. Make the default app behavior avoid multi-pose degradation on ordinary single-player
   swing clips.
4. Preserve DEV003-06 diagnostics, but make diagnostics reveal whether poor overlay came
   from:
   * raw MediaPipe output,
   * multi-pose candidate selection,
   * temporal post-processing,
   * sampled-frame mismatch,
   * overlay mapping,
   * annotated or otherwise invalid source images.
5. Keep all processing local. Do not upload frames, images, landmarks, model data, or
   user media externally.

## Pose Estimator Requirements

### Notebook-Parity Mode

Add an explicit pose-estimation configuration mode for diagnosis.

Recommended name:

```text
notebook_parity
```

Required behavior:

* Use `num_poses=1`.
* Disable smoothing by using `smoothing_window=1`.
* Disable interpolation by using `max_interpolation_gap_frames=0`.
* Disable outlier rejection by using a documented no-op value or explicit flag.
* Preserve raw normalized landmark coordinates.
* Return the same internal `PoseFrame` schema as normal app analysis.
* Add a clear limitation or diagnostic flag that this mode is for detector parity, not
  final stabilized analysis.

### Image-Mode Smoke Check

Add a local diagnostic utility or test-only service path that can run MediaPipe image
mode on one decoded frame and map the result to the internal `PoseFrame` model.

Required behavior:

* Keep MediaPipe objects inside the `pose` module.
* Do not add a public hosted upload or external processing path.
* Compare image-mode and video-mode landmark coordinates for the same frame in tests
  using fake MediaPipe result objects where full MediaPipe runtime/model assets are too
  heavy for CI.
* Document any differences between image mode and video mode.

### Multi-Pose Handling

The app should not request multiple poses by default unless doing so improves a tested
case.

Required behavior:

* Change the default `num_poses` to `1`, or make `num_poses=2` apply only when a
  multi-person mode is explicitly selected.
* Keep multi-pose support available for future crowded scenes.
* Improve candidate selection if `num_poses > 1`:
  * prefer continuity only after a reliable previous player track exists,
  * prefer plausible body size and center/batter-area position on the first detected
    frame,
  * reject candidates with implausible body proportions or too many landmarks outside
    the visible frame,
  * report selected candidate diagnostics.

### Temporal Post-Processing

Temporal stabilization must be safe for baseball swing motion.

Required behavior:

* Do not smooth or interpolate high-velocity wrist/ankle movement so aggressively that
  the overlay no longer matches the visible frame.
* Track raw and post-processed pose diagnostics separately.
* Return both raw and stabilized overlay data when debug mode is enabled, or expose a
  switch to draw raw versus stabilized landmarks.
* Add limitations when stabilization changes keypoints by more than a body-scale-normalized
  threshold.

## Overlay Requirements

Improve debug visibility for overlay quality.

Required behavior:

* Show exact frame, nearest sampled frame, or interpolated frame status.
* Include frame offset in milliseconds when the overlay is not exact.
* Support drawing raw MediaPipe landmarks versus stabilized landmarks in a debug mode.
* Keep normal user overlay simple by default.
* Continue mapping coordinates into the rendered video content rectangle, including
  `object-fit: contain` and letterboxing.
* Avoid running pose estimation on annotated screenshots. If practical, detect or warn
  when the selected source appears to be an already annotated UI screenshot.

## UI Requirements

Keep the existing DEV003-06 workflow and layout unless a compact debug control is needed.

Required behavior:

* Keep `Run Swing Analysis` video-driven.
* Keep `Clear Analysis` clearing results, diagnostics, and overlays.
* Keep unsupported motion-type behavior for throwing, pitching, and fielding unchanged.
* Add a compact advanced/debug control only if needed, such as:
  * pose mode: `normal`, `notebook parity`, `raw overlay`
  * overlay source: `stabilized`, `raw`
* Do not expose baseball coaching thresholds in UI code.

## API Requirements

Keep:

```text
POST /api/v1/analysis/swing/video
```

Extend only as needed for local diagnostics.

Required response behavior:

* Return existing analysis, feedback, events, pose frames, overlay frames, limitations,
  pose diagnostics, and sampling diagnostics.
* Add diagnostics for:
  * MediaPipe running mode,
  * requested `num_poses`,
  * selected candidate index or selection strategy when available,
  * raw versus stabilized landmark delta when debug mode is enabled,
  * overlay frame offset from replay frame when available.
* Do not expose absolute local filesystem paths.

## Testing Requirements

Add deterministic tests without requiring private videos, network access, external
credentials, or large model files.

Required tests:

* Unit tests for notebook-parity config defaults.
* Unit tests proving default app pose config uses one pose unless multi-person mode is
  explicitly requested.
* Unit tests for image-mode and video-mode MediaPipe result mapping using fake result
  objects.
* Unit tests for first-frame best-player selection in a cluttered/multi-candidate case.
* Unit tests that temporal smoothing does not over-smooth high-velocity wrist movement.
* Integration tests for `SwingVideoAnalysisApplicationService` using an injected fake
  estimator that returns both raw and stabilized frames or equivalent diagnostics.
* API tests for extended diagnostics.
* UI/static tests for any added debug controls and for exact/nearest frame-offset copy.

## Documentation Requirements

Update:

* `PLANS.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* Add or update an ADR under `docs/02_architecture/adr/`
* `docs/04_motion_knowledge/swing.md`
* Existing relevant manuals under `docs/05_manuals/`
* Add a development log under `docs/03_development_log/`

Documentation must clearly explain:

* The difference between notebook image-mode testing and app video-mode analysis.
* Why multi-pose detection can be worse than single-pose detection in cluttered
  single-player scenes.
* Why pose estimation should use original unannotated frames.
* How to use notebook-parity/debug mode.
* Why bat/ball-dependent metrics remain limited without bat/ball detection.

## Quality Gates

After implementation, run:

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

Also verify:

* Local app starts without a release or deployment.
* App pose output in notebook-parity mode is close to notebook image-mode output for the
  same unannotated frame.
* Normal mode does not regress from notebook-parity mode on `data/test.png` or the
  original source frame, if that frame is available.

## Acceptance Criteria

The task is complete when:

* The app can reproduce the notebook MediaPipe baseline through a documented parity mode.
* Default single-player swing analysis no longer gets worse because of unnecessary
  multi-pose candidate selection.
* Poor pose overlays can be attributed to raw detector output, candidate selection,
  temporal post-processing, frame mismatch, overlay mapping, or invalid annotated input.
* Debug diagnostics make the bad `data/test.png` case explainable and actionable.
* Tests cover parity config, candidate selection, post-processing safety, API diagnostics,
  and UI/static behavior.
* Required docs are updated.
* Required quality gates pass.

## Non-Goals

* Do not implement throwing, pitching, or fielding evaluation.
* Do not add hosted services, release packaging, Docker deployment, or production
  deployment.
* Do not upload videos or frames externally.
* Do not commit model files, local videos, generated reports, `.env`, or other local
  artifacts.
* Do not implement full bat or ball detection in this task. Keep bat/ball work as a
  clearly documented future task.
