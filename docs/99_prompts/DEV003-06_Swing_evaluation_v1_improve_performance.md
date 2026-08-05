# DEV003-06 Swing Evaluation v1 Pose Performance Improvements

## Goal

Improve the practical accuracy and reliability of video-driven swing evaluation after
DEV003-05 MediaPipe integration.

The current app uses real MediaPipe body landmarks, but sample testing through
`notebooks/media_input.ipynb` and the application path shows that relevant body pose can
be detected while the app's displayed overlay and swing evaluation can still be poor.
This task should improve the pose-estimation pipeline, overlay alignment, phase
detection, and diagnostic reporting before expanding to other motion types.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-01_Swing_evaluation_v1.md`
* `docs/99_prompts/DEV003-02_Swing_evaluation_v1_UI.md`
* `docs/99_prompts/DEV003-03_Swing_evalutation_v1_UI_revise.md`
* `docs/99_prompts/DEV003-04_Swing_evaluation_v1_update_core_algo.md`
* `docs/99_prompts/DEV003-05_Swing_evaluation_v1_pose_esimatoer.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0007-mediapipe-pose-estimator.md`
* Existing manuals under `docs/05_manuals/`
* `notebooks/media_input.ipynb`
* Existing implementation:
  * `src/baseball_motion_analysis/video/`
  * `src/baseball_motion_analysis/pose/`
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/analysis/swing.py`
  * `src/baseball_motion_analysis/feedback/swing.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/unit/test_pose_estimation.py`
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`

## Current Implementation Findings

The current implementation has several opportunities to improve results:

1. `MediaPipePoseEstimator` runs on sampled frames only. The current default
   `SwingVideoSamplingOptions` is `target_fps=12.0` and `max_frame_count=60`, which can
   miss baseball swing events, especially impact and foot strike.
2. `detect_swing_phases` still uses an evenly spread fallback when explicit phase frames
   are not provided. This means swing phase selection can be wrong even when MediaPipe
   landmarks are good.
3. The estimator uses fixed MediaPipe thresholds:
   `min_pose_detection_confidence=0.5`, `min_pose_presence_confidence=0.5`, and
   `min_tracking_confidence=0.5`. These are not configurable through settings, API, or
   UI.
4. The estimator uses `num_poses=1`, so it cannot choose the correct player when more
   than one person is visible. The existing best-pose selector only helps if MediaPipe
   returns multiple poses.
5. Landmark coordinates are clamped to `[0, 1]` during mapping. Out-of-frame or unstable
   landmarks can be pinned to the image edge, which can make overlay points and metrics
   look incorrectly placed.
6. There is no temporal smoothing, outlier rejection, short-gap interpolation, or
   per-track continuity logic. A single bad frame can affect overlay quality, phase
   detection, and metrics.
7. There is no player region-of-interest strategy. Full-frame detection can be weaker
   when the player is small, off-center, partly occluded, or surrounded by background.
8. The replay overlay maps normalized pose coordinates directly to the canvas. It should
   verify alignment against the actual rendered video content rectangle, including
   `object-fit: contain`, intrinsic video dimensions, and any letterboxing.
9. The app does not expose enough pose diagnostics to explain poor results. Users need
   to know if low confidence, sparse sampling, missing landmarks, wrong phase detection,
   camera angle, or missing bat/ball detection caused the poor evaluation.
10. MediaPipe Pose does not detect bat tip, bat barrel, or ball position. Current attack
    angle remains a wrist/grip fallback and must stay low confidence until bat tracking
    is implemented separately.

## Required Outcomes

Implement improvements that make swing evaluation depend on higher-quality pose
observations and motion-aware phase detection.

Required outcomes:

1. Improve frame coverage for fast swings.
2. Improve pose stability across sampled frames.
3. Improve player selection when multiple people or background figures are visible.
4. Improve overlay alignment with the replayed video.
5. Replace evenly spread automatic swing phases with motion-aware automatic phase
   detection.
6. Surface diagnostics that explain why a result is low quality.
7. Keep all processing local. Do not upload video frames, images, landmarks, or model
   data externally.

## Pose Estimator Requirements

Add a configuration object for MediaPipe pose estimation, recommended name:

```text
MediaPipePoseEstimatorConfig
```

It should support at least:

* `num_poses`
* `min_pose_detection_confidence`
* `min_pose_presence_confidence`
* `min_tracking_confidence`
* `min_landmark_confidence`
* `smoothing_window`
* `max_interpolation_gap_frames`
* `outlier_distance_ratio`
* `player_selection_strategy`
* `enable_segmentation_mask` if supported by the selected MediaPipe API path

Expose safe defaults through application settings and `.env.example`. Do not hard-code
all tuning values inside `MediaPipePoseEstimator`.

Required behavior:

* Keep `MediaPipePoseEstimator` behind the `pose` module boundary.
* Continue returning internal `PoseFrame` objects, not MediaPipe objects.
* Preserve raw normalized landmark positions for analysis where practical.
* Clamp coordinates only for overlay rendering or output safety, not before quality
  evaluation.
* Track per-landmark confidence, missing landmarks, and out-of-frame landmarks.
* Select the best player using a documented strategy:
  * prefer track continuity from the previous frame,
  * then visible landmark confidence,
  * then body bounding-box size,
  * then a configurable batter-area preference if available.
* Add smoothing for visible landmarks across nearby frames.
* Add short-gap interpolation for temporarily missing landmarks when surrounding frames
  are reliable.
* Mark interpolated landmarks with lower confidence or a diagnostic flag if the current
  data model supports it. If the current data model does not support this, add a clear
  limitation message.
* Reject obvious outlier jumps relative to body scale and previous/next frames.
* Add pose-quality summaries:
  * detected pose frame ratio,
  * required landmark coverage,
  * mean/min confidence,
  * smoothed frame count,
  * interpolated frame count,
  * rejected outlier count.

Do not reintroduce the heuristic estimator as a silent fallback for user-selected
videos.

## MediaPipe Runtime Reliability Requirements

Review MediaPipe runtime setup for local macOS and CPU/GPU behavior.

Required behavior:

* Make the delegate/runtime choice explicit where MediaPipe supports it.
* Prefer stable local execution over faster but fragile GPU initialization.
* Return clear structured errors for missing model, missing dependency, unsupported
  runtime, or MediaPipe tracking failure.
* Document that MediaPipe native failures may terminate the process if they occur below
  Python exception handling. If practical, isolate MediaPipe execution in a worker
  boundary or add a startup smoke check that fails before user analysis begins.

## Video Sampling Requirements

Baseball swing timing is fast, so the current `12 fps` default is not enough for
reliable phase detection.

Required behavior:

* Add an analysis-quality sampling mode for swing videos.
* For short clips, support processing every original frame when the frame count is under
  a safe cap.
* Increase the high-accuracy default for swing analysis to preserve fast motion events,
  with a configurable cap to protect local runtime.
* Keep API and service support for explicit sampling overrides.
* Return limitations when the requested sampling is reduced by a cap.
* Include sampled frame count, source FPS, effective FPS, and cap status in diagnostics.

Suggested starting point:

* Use full-frame sampling for clips up to roughly 180 frames.
* Otherwise target at least `24 fps` for swing analysis.
* Keep the cap configurable rather than hard-coded.

## Motion-Aware Phase Detection Requirements

Replace the evenly spread automatic phase fallback with motion-aware detection based on
pose trajectories.

Required behavior:

* Detect setup, stride/load, foot strike, impact, and follow-through from pose-derived
  time series rather than fixed positions in the sampled sequence.
* Use smoothed pose landmarks for phase detection.
* Use wrist/grip velocity, lead/rear ankle or foot movement, hip/shoulder rotation
  change, and body-scale-normalized movement where useful.
* Report confidence for each phase, not just one sequence-level confidence.
* Return limitations when phase detection falls back to a conservative approximation.
* Keep provided phase frames supported for tests and future expert workflows.

Do not claim exact ball impact unless ball or bat contact is detected. For now, impact
should be treated as an estimated impact window based on motion cues.

## Overlay Alignment Requirements

Improve browser overlay placement so keypoints line up with the replayed video.

Required behavior:

* Compute the rendered video content rectangle, not just the canvas rectangle.
* Account for intrinsic video dimensions, CSS sizing, `object-fit: contain`, and
  letterboxing.
* Draw pose keypoints using the content rectangle.
* Keep labels readable and avoid overlapping the video controls.
* Show whether the overlay frame is exact, nearest sampled frame, or interpolated.
* Consider overlay interpolation between pose frames when playback time falls between
  sampled frames.

## Swing Evaluation Requirements

Update swing evaluation to consume improved pose data and diagnostics.

Required behavior:

* Use smoothed/interpolated pose frames for phase detection and metrics when confidence
  is high enough.
* Preserve original pose frames or diagnostics for debug output if needed.
* Lower confidence when key metrics depend on interpolated or low-confidence landmarks.
* Keep attack angle explicitly low-confidence until bat tip/barrel tracking exists.
* Add limitations for:
  * sparse frame sampling,
  * low pose coverage,
  * phase fallback,
  * interpolated landmarks,
  * rejected outliers,
  * missing bat/ball data,
  * poor camera angle or small player size when detectable.

## UI Requirements

Keep the existing DEV003-04/DEV003-05 workflow and layout unless an adjustment is needed
for diagnostics.

Required behavior:

* Add a compact pose-quality section to Motion Analysis results.
* Show effective FPS, sampled frame count, pose detection ratio, required landmark
  coverage, and phase confidence.
* Let users choose a practical quality mode:
  * faster analysis,
  * balanced analysis,
  * higher accuracy.
* Keep `Clear Analysis` clearing results, diagnostics, and overlays.
* Keep unsupported motion-type behavior for throwing, pitching, and fielding unchanged.

## API Requirements

Keep:

```text
POST /api/v1/analysis/swing/video
```

Extend the response with pose-quality diagnostics and improved phase metadata.

Required response behavior:

* Return the existing analysis, feedback, events, pose frames, overlay frames, and
  limitations.
* Add pose diagnostics without exposing absolute local file paths.
* Add per-phase confidence and detection method where practical.
* Add sampling diagnostics:
  * source FPS,
  * effective sampled FPS,
  * sampled frame count,
  * total frame count,
  * cap applied.
* Add clear structured error codes for runtime and quality failures.

## Testing Requirements

Add deterministic tests without requiring private or large videos.

Required tests:

* Unit tests for pose landmark mapping without premature clamping.
* Unit tests for best-player selection across multiple MediaPipe pose candidates.
* Unit tests for smoothing, interpolation, and outlier rejection.
* Unit tests for pose-quality diagnostic aggregation.
* Unit tests for motion-aware swing phase detection using fixed pose fixtures.
* Integration tests for `SwingVideoAnalysisApplicationService` with an injected fake
  estimator that simulates jitter, missing frames, low confidence, and multiple players.
* API tests for the extended diagnostics response.
* UI JavaScript syntax check and, where practical, browser overlay tests for content
  rectangle mapping.

No test should require real user videos, network access, external credentials, or large
model files.

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

* Pose quality modes.
* Why faster analysis mode can reduce accuracy.
* Why 2D pose cannot perfectly evaluate all swing mechanics.
* Why bat/ball-dependent metrics remain limited without bat/ball detection.
* How to configure MediaPipe model path and pose-estimator tuning.

## Quality Gates

After implementation, run:

```bash
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

* `node --check src/baseball_motion_analysis/ui/web/static/app.js`
* Local app starts without a release or deployment.
* Swing analysis returns useful diagnostics when pose quality is poor.
* Overlay alignment is correct for at least one landscape and one portrait or
  letterboxed fixture if such fixtures are available.

## Acceptance Criteria

The task is complete when:

* Swing video analysis no longer relies on evenly spread phase selection as the normal
  automatic path.
* The app can run higher-accuracy sampling for short swing clips.
* Pose landmarks are smoothed or stabilized before phase detection and metric
  evaluation.
* Multiple-pose frames select a consistent player when possible.
* Overlay coordinates align to the visible video content rectangle.
* Poor-quality analysis results explain the likely cause through diagnostics and
  limitations.
* Tests cover the new pose-quality and phase-detection behavior.
* Required docs are updated.
* Required quality gates pass.

## Non-Goals

* Do not implement throwing, pitching, or fielding evaluation.
* Do not add hosted services, release packaging, Docker deployment, or production
  deployment.
* Do not upload videos or frames externally.
* Do not commit model files, local videos, generated reports, `.env`, or other local
  artifacts.
* Do not implement full bat or ball detection in this task unless it is explicitly
  approved as an added scope. Keep bat/ball work as a clearly documented future task.
