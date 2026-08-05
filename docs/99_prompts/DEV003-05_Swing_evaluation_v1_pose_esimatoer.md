# DEV003-05 Swing Evaluation v1 Pose Estimator

## Goal

Replace the DEV003-04 deterministic heuristic pose placeholder with actual local player
body pose detection using MediaPipe.

The swing evaluation workflow must analyze evaluated player poses extracted from the
actual video frames, not synthetic swing-like coordinates.

Required outcomes:

1. Detect the actual player body pose in the selected video using MediaPipe.
2. Track pose landmarks for every frame used by the swing analysis workflow.
3. Convert MediaPipe landmarks into the existing internal `PoseFrame` model.
4. Run swing phase/event detection, scoring, feedback, and replay overlay from the
   MediaPipe-derived poses.
5. Keep the workflow local-PC-first. Do not upload video frames or media externally.

This is a major accuracy update. It should not create a release or deployment.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-01_Swing_evaluation_v1.md`
* `docs/99_prompts/DEV003-02_Swing_evaluation_v1_UI.md`
* `docs/99_prompts/DEV003-03_Swing_evalutation_v1_UI_revise.md`
* `docs/99_prompts/DEV003-04_Swing_evaluation_v1_update_core_algo.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md`
* `docs/02_architecture/adr/ADR-0006-video-driven-swing-pose-estimation.md`
* Existing manuals under `docs/05_manuals/`
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
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_motion_metrics.py`
  * video and media input tests under `tests/unit/`

## Current Implementation Context

DEV003-04 added a video-driven swing workflow, but the current concrete pose estimator is
`HeuristicPoseEstimator`. It creates deterministic synthetic pose coordinates from frame
progress and does not inspect the actual video image.

This is useful for service/API/UI wiring tests only. It is not acceptable for real video
analysis because overlay positions and swing metrics are not based on the player's body.

DEV003-05 must make `SwingVideoAnalysisApplicationService` use a real pose estimator for
normal video analysis.

## Dependency Decision

Use MediaPipe Pose Landmarker as the first real local pose backend.

Rationale:

* MediaPipe runs locally and matches the local-PC-first product direction.
* MediaPipe Pose Landmarker supports image, video, and live-stream running modes.
* MediaPipe returns normalized landmarks and confidence/presence values that can map to
  the app's existing normalized `PoseFrame` model.
* MediaPipe provides more body landmarks than COCO-17 pose models, including foot
  landmarks that may help side-view swing phase detection.
* MediaPipe is lighter to integrate than MMPose for the current MVP.

Alternatives considered:

* Ultralytics YOLO Pose:
  * Good detection and future custom training path.
  * Heavier runtime stack and fewer default body keypoints.
* MMPose:
  * Most flexible research framework.
  * Too heavy and complex for the current local MVP unless advanced model
    experimentation becomes the goal.

Dependency requirements:

* Add MediaPipe through `uv add mediapipe` only if compatible with the current Python and
  platform constraints.
* Do not edit `uv.lock` manually.
* If MediaPipe installation is not compatible, document the blocker and implement the
  adapter behind an optional import boundary with tests that mock MediaPipe.
* Keep `HeuristicPoseEstimator` available only as test/fallback behavior, not as the
  default video-analysis estimator when MediaPipe is available.

## MediaPipe Pose Estimator Requirements

Add a concrete estimator, recommended name:

```text
MediaPipePoseEstimator
```

Required behavior:

* Implement the existing `PoseEstimator` interface.
* Accept decoded `FrameData` instances from the existing video sampling pipeline.
* Run MediaPipe Pose Landmarker in video mode for each sampled frame.
* Provide monotonically increasing frame timestamps to MediaPipe.
* Convert detected body landmarks to internal `PoseFrame` objects.
* Preserve original `frame_index` and `timestamp_seconds`.
* Return keypoint confidence values.
* If MediaPipe detects no player on a frame, return a `PoseFrame` with missing keypoints
  or skip that frame according to a documented policy.
* A missing or low-confidence frame must reduce confidence and add limitations, not crash
  the whole analysis.
* Select the best player if multiple poses are detected. For the first version, prefer
  the largest/most confident visible pose.
* Do not expose MediaPipe objects outside the `pose` module boundary.

Required landmark mapping:

* `NOSE`
* `LEFT_SHOULDER`
* `RIGHT_SHOULDER`
* `LEFT_ELBOW`
* `RIGHT_ELBOW`
* `LEFT_WRIST`
* `RIGHT_WRIST`
* `LEFT_HIP`
* `RIGHT_HIP`
* `LEFT_KNEE`
* `RIGHT_KNEE`
* `LEFT_ANKLE`
* `RIGHT_ANKLE`

Optional landmark mapping:

* `LEFT_HEEL`
* `RIGHT_HEEL`
* `LEFT_FOOT_INDEX`
* `RIGHT_FOOT_INDEX`
* hand landmarks if the MediaPipe result or a future hand model provides them.

Bat keypoints:

* MediaPipe Pose does not detect bat tip or barrel.
* Do not fake bat tip or barrel positions as if they were detected.
* When bat keypoints are unavailable, attack-angle metrics should use existing
  fallback logic and lower confidence with a clear limitation.
* Bat detection should remain a separate future task unless explicitly requested.

## Pose Tracking Requirements

Pose tracking is required for every frame used by analysis.

Required behavior:

* Use MediaPipe video running mode so temporal tracking can stabilize landmark output.
* Keep frame order deterministic.
* Process all frames in the sampled `FrameSequence`.
* Output one internal pose result per sampled frame when possible.
* Record per-frame limitations for frames where no body pose is detected or landmark
  confidence is too low.
* Analysis should use the MediaPipe-derived pose sequence only.
* Do not fall back to synthetic heuristic pose for user-selected videos unless explicitly
  configured as a test/fallback mode and clearly reported in limitations.

Sampling policy:

* Keep DEV003-04 sampling options initially: default target FPS `12.0`, maximum sampled
  frame count `60`.
* Tiny test videos should be fully sampled when the cap allows it.
* Preserve the API ability to override sampling values.
* Document that MediaPipe runs on sampled frames, not necessarily every original video
  frame, unless sampling options are configured for full-frame processing.

## Swing Evaluation Requirements

Swing evaluation must be performed using the evaluated MediaPipe poses.

Required behavior:

* `SwingVideoAnalysisApplicationService` should use `MediaPipePoseEstimator` by default
  for stored-video analysis when MediaPipe is installed and configured.
* `detect_swing_phases` should receive the MediaPipe-derived `PoseFrame` sequence.
* `SwingAnalysisApplicationService.analyze_pose_sequence` should receive the same
  MediaPipe-derived sequence.
* Overlay data should be generated from the MediaPipe-derived pose frames.
* Feedback limitations should explicitly mention:
  * no body detected,
  * low landmark confidence,
  * sampled-frame analysis,
  * missing bat keypoints,
  * 2D camera-angle limitations.
* Existing pose-JSON endpoint may remain for internal/debug use.

## UI Requirements

Keep the DEV003-04 layout and workflow:

```text
|          Replay video           |
| Upload Video  | Motion Analysis |
| Video Library | Motion Analysis |
```

Required behavior:

* User selects a stored video.
* User selects `Swing`.
* User selects handedness.
* User clicks `Run Swing Analysis`.
* UI shows status while MediaPipe pose tracking and swing analysis run.
* Replay overlay draws actual detected player body landmarks returned by the API.
* `Clear Analysis` clears results and overlays.
* If MediaPipe cannot detect a player, show a clear user-facing error or limitation.

Do not reintroduce required pose JSON input or manual phase frame inputs in the primary
UI workflow.

## API Requirements

Keep the DEV003-04 endpoint:

```text
POST /api/v1/analysis/swing/video
```

Required response behavior:

* Return analysis and feedback based on MediaPipe-derived poses.
* Return pose frames and overlay frames derived from MediaPipe landmarks.
* Return event frames selected from MediaPipe-derived poses.
* Return limitations for missing/low-confidence landmarks and missing bat keypoints.
* Return structured errors for:
  * missing MediaPipe dependency when required,
  * missing model/task asset,
  * no detectable player pose,
  * invalid sampling options,
  * invalid media ID.

Do not expose absolute local file paths in API responses.

## Architecture And Documentation Requirements

Update architecture docs:

* `docs/02_architecture/system_overview.md`
* New ADR under `docs/02_architecture/adr/` for adopting MediaPipe as the first real
  local pose backend.

Update product and user docs:

* `docs/01_product/feature_catalog.md`
* `docs/04_motion_knowledge/swing.md`
* Existing relevant manual under `docs/05_manuals/`, or create a new one if needed.
* Add a development log under `docs/03_development_log/`.
* Update `PLANS.md` with planning, architecture, coding, QA, and final-review statuses.

Document clearly:

* MediaPipe detects body landmarks, not bat landmarks.
* Analysis currently runs on sampled frames by default.
* Confidence and limitations must be shown for poor detections.
* The app remains local; no video frames are sent externally.

## Testing Requirements

Add or update tests without requiring large user videos.

Minimum required tests:

* Unit tests for MediaPipe landmark-to-`PoseFrame` mapping using fake MediaPipe result
  objects or adapter-level fixtures.
* Unit tests for missing-landmark and low-confidence behavior.
* Unit tests proving `HeuristicPoseEstimator` is not the default production estimator
  when MediaPipe is available.
* Application-service integration tests showing video analysis uses an injected
  MediaPipe-compatible estimator and evaluates those returned poses.
* API integration tests showing `/api/v1/analysis/swing/video` returns pose, overlay,
  event, analysis, feedback, and limitation fields from detected poses.
* UI/static tests confirming the primary workflow remains video-driven and does not
  require pose JSON or manual phase frame entry.

Testing constraints:

* Do not commit large videos or model weights.
* Use tiny generated video fixtures.
* Mock or fake MediaPipe where full MediaPipe runtime/model assets are too heavy for CI.
* Keep tests deterministic.

## Required Quality Commands

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

## Acceptance Criteria

DEV003-05 is complete only when:

* Actual player body pose is detected from video frames using MediaPipe.
* The primary video-analysis workflow does not use synthetic heuristic pose coordinates.
* Pose tracking runs for every sampled frame used by analysis.
* MediaPipe landmarks are converted into internal `PoseFrame` objects.
* Swing event detection, scoring, feedback, and overlay generation use MediaPipe-derived
  poses.
* Missing or low-confidence detections lower confidence and add limitations.
* Bat keypoints are not faked; missing bat data is reported as a limitation.
* The replay overlay draws the detected player body pose, not placeholder coordinates.
* The UI remains video-driven and includes clear analysis behavior.
* Tests cover mapping, service behavior, API behavior, UI/static behavior, and failure
  cases.
* Required quality commands pass.
* Documentation and `PLANS.md` are updated.
* No release or deployment is created.

## Non-Goals

* Bat tip/barrel detection.
* Ball tracking.
* 3D swing biomechanics.
* Hosted video upload or external pose service.
* Throwing, pitching, or fielding implementation.
* Report persistence.
* Release, deployment, packaging, or version bump.
