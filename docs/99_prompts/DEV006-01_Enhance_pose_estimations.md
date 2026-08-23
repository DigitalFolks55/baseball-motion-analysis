# DEV006-01 Enhance Pose Estimations

## Goal

Improve the reliability of pose estimation and swing event alignment for video-driven
swing analysis.

The current app already uses MediaPipe body landmarks, raw and stabilized pose outputs,
quality-mode sampling, and motion-aware swing phase detection. However, some real swing
videos still produce poor overlays or poor evaluation quality. This task should harden
the existing local pose pipeline before adding new motion types or larger model
dependencies.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-06_Swing_evaluation_v1_improve_performance.md`
* `docs/99_prompts/DEV003-07_Swing_evaluation_v1_improve_performance_2.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/99_prompts/DEV004-04_Swing_evaluation_v2_aspect_issue.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0007-mediapipe-pose-estimator.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
* `docs/02_architecture/adr/ADR-0011-swing-aspect-aware-measurement-space.md`
* Existing manuals under `docs/05_manuals/`
* Existing implementation:
  * `src/baseball_motion_analysis/pose/`
  * `src/baseball_motion_analysis/video/`
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/analysis/swing.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/unit/test_pose_estimation.py`
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_evaluation_overlay_lines.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * `tests/integration/test_swing_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`

## Current Implementation Summary

The current stored-video swing flow is:

```text
stored video
  -> sampled frames
  -> MediaPipePoseEstimator
  -> raw PoseFrame sequence
  -> stabilized PoseFrame sequence
  -> automatic swing phase/event selection
  -> swing v2 metric evaluation
  -> feedback, diagnostics, pose overlay, and evaluation lines
```

Important current behavior:

* MediaPipe Pose detects body landmarks only. It does not detect bat tip, bat barrel,
  ball position, or true contact.
* Normal video analysis uses stabilized pose frames for scoring.
* Raw pose frames are returned for diagnostics and overlay comparison.
* Phase detection uses wrist/grip velocity, ankle movement, and hip/shoulder rotation
  cues.
* Impact is an estimated impact window from body-pose motion cues, not confirmed
  bat-ball contact.
* Sampling defaults to higher-accuracy mode, with faster and balanced modes available.
* Pose diagnostics report detection coverage, required landmark coverage, confidence,
  smoothing, interpolation, outlier rejection, and out-of-frame landmarks.

## Problem Statement

Some videos can still produce poor pose/evaluation quality because:

1. Weak body frames can still influence phase detection and scoring.
2. Player tracking can switch or lock onto background people in cluttered clips.
3. Videos may contain long pre-swing, post-swing, or unrelated motion windows.
4. Wrist-speed-only impact estimation can pick the wrong high-motion frame.
5. Stabilization can help torso landmarks but may distort high-speed wrists or ankles.
6. Diagnostic output reports quality, but it does not always explain which frames or
   landmarks caused the poor result.
7. There are not enough calibrated tiny fixtures or annotated pose JSON examples to tune
   thresholds against repeatable failure cases.

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

## Scope

Implement a focused pose-quality enhancement for stored-video swing analysis.

Required scope:

1. Add pose-quality filtering before phase detection and scoring.
2. Improve player tracking and candidate-switch rejection.
3. Add swing-active-window detection before selecting phase frames.
4. Improve estimated impact selection using additional body-motion constraints.
5. Make stabilization safer for high-speed swing landmarks.
6. Improve diagnostics so poor results can be traced to sampling, raw pose quality,
   player selection, stabilization, phase detection, or missing bat/ball evidence.
7. Add deterministic tests and tiny synthetic fixtures where practical.

## Non-Goals

* Do not add hosted services, cloud uploads, external frame processing, or telemetry.
* Do not commit videos, large fixtures, MediaPipe model weights, generated reports, or
  local user data.
* Do not silently fall back to `HeuristicPoseEstimator` for user-selected videos.
* Do not implement full bat, barrel, or ball detection in this task.
* Do not claim exact ball impact without bat/ball contact evidence.
* Do not add throwing, pitching, or fielding analysis behavior.
* Do not move baseball scoring rules into UI, API, storage, video, or pose modules.
* Do not change swing v2 scoring concepts unless required to handle improved confidence
  or skipped evidence.

## Architecture Requirements

Preserve existing boundaries:

* `video` owns frame loading, metadata, and sampling.
* `pose` owns body keypoint extraction, candidate selection, raw/stabilized pose
  post-processing, and pose-quality diagnostics.
* `motion` owns swing phase/event semantics and pose-derived movement cues.
* `analysis` owns rule evaluation, scoring, confidence, and metric limitations.
* `app` orchestrates video lookup, frame sampling, pose estimation, swing phase
  selection, analysis, feedback, and browser-neutral overlay data.
* `api` serializes request/response models and structured errors.
* `ui` displays controls, results, overlays, and diagnostics without owning baseball
  thresholds or pose-estimator internals.

Prefer small typed data objects for new diagnostics and filtering decisions. Avoid
passing loosely structured dictionaries through service boundaries when stable dataclasses
or schemas would be clearer.

## Pose-Quality Filtering Requirements

Add a filtering or weighting layer before automatic phase detection.

Required behavior:

* Identify frames with weak pose evidence before they affect phase detection.
* Consider at least:
  * required landmark coverage,
  * mean or minimum landmark confidence,
  * missing torso scale landmarks,
  * missing wrists, ankles, knees, hips, or shoulders needed by swing phases,
  * excessive out-of-frame landmarks,
  * implausible body scale jumps,
  * implausible body-box size changes,
  * interpolated landmark dependency.
* Do not simply delete frames in a way that breaks replay alignment. Preserve original
  frame indexes and timestamps.
* Prefer marking frames as usable, weak, or rejected-for-phase-detection with explicit
  reasons.
* Phase detection should ignore or down-weight weak frames where possible.
* Scoring should lower confidence or skip metrics when the selected evidence frame
  depends on weak landmarks.
* Return diagnostics summarizing how many frames were used, down-weighted, or rejected
  for phase detection.

## Player Tracking Requirements

Improve player identity stability across frames.

Required behavior:

* Keep default single-pose behavior for ordinary single-player clips unless settings
  explicitly request multiple poses.
* When multiple pose candidates are available, select the hitter using a documented
  score that includes:
  * track continuity after a reliable previous frame exists,
  * visible landmark confidence,
  * plausible body-box size,
  * in-frame landmark ratio,
  * center or batter-area preference only as a weak cue.
* Add candidate-switch rejection. Do not switch to another candidate unless the new
  candidate is clearly better than the current track.
* Report selected candidate indexes and switch counts.
* Report candidate ambiguity when the best and second-best candidates are close.
* Add tests for crowded-scene candidate selection using fake MediaPipe results.

## Active Swing Window Requirements

Detect the active swing window before assigning the five swing phase frames.

Required behavior:

* Build a body-scale-normalized motion time series from wrists/grip, ankles/feet,
  hip/shoulder rotation, and head/torso movement.
* Smooth the motion time series enough to avoid isolated one-frame noise, without hiding
  real swing acceleration.
* Detect the likely start and end of the active swing window.
* Ignore long idle sections before setup and after follow-through when selecting phases.
* Keep original frame indexes in returned phases and overlay events.
* Return window diagnostics:
  * start frame,
  * end frame,
  * peak motion frame,
  * active-window confidence,
  * fallback reason if no clear window is found.
* If no clear active window exists, fall back conservatively and report a limitation.

## Improved Impact Estimation Requirements

Improve estimated impact selection while keeping clear limitations.

Required behavior:

* Keep impact as an estimated body-motion event until bat/ball evidence exists.
* Use more than wrist velocity when selecting impact. Consider:
  * wrist/grip velocity,
  * wrist/grip acceleration,
  * hand path crossing or approaching the lead-side/front-torso region,
  * lead-leg blocking evidence,
  * hip/shoulder rotation timing,
  * follow-through onset constraints.
* Avoid picking early load/stride hand movement as impact.
* Avoid picking late follow-through-only movement as impact.
* Report impact detection method and confidence separately from overall analysis
  confidence.
* Add tests where peak wrist velocity alone would choose the wrong frame.

## Stabilization Requirements

Make stabilization safer for baseball swing motion.

Required behavior:

* Keep raw and stabilized pose outputs available.
* Avoid smoothing high-velocity wrists and ankles when motion is likely real swing
  movement.
* Consider per-keypoint stabilization policies:
  * torso/head/hips may tolerate smoothing,
  * wrists/ankles may require stricter high-velocity preservation,
  * knees and elbows may need moderate smoothing.
* Lower confidence for interpolated landmarks.
* Track whether selected phase evidence uses interpolated or heavily stabilized
  landmarks.
* Add limitations when stabilization changes a selected evidence landmark by more than a
  body-scale-normalized threshold.
* Add tests that prove high-speed wrist and ankle movement is not over-smoothed.

## Diagnostics Requirements

Improve diagnostics so users and developers can understand poor results.

Required response diagnostics should include, where applicable:

* Sampling:
  * source FPS,
  * target FPS,
  * effective sampled FPS,
  * sampled frame count,
  * total frame count,
  * frame cap status.
* Raw pose quality:
  * detected pose frame ratio,
  * required landmark coverage,
  * mean/min confidence,
  * out-of-frame landmark count.
* Stabilized pose quality:
  * smoothed frame count,
  * interpolated frame count,
  * rejected outlier count,
  * stabilization delta summary.
* Player tracking:
  * requested pose count,
  * selection strategy,
  * selected candidate indexes,
  * candidate switch count,
  * ambiguity count.
* Phase detection:
  * active window start/end,
  * per-phase frame index,
  * per-phase confidence,
  * per-phase detection method,
  * per-phase fallback reason.
* Scoring evidence:
  * metrics affected by weak, missing, interpolated, or heavily stabilized landmarks.

UI labels should remain compact. Detailed diagnostics may stay behind an expandable
diagnostics area.

## API Requirements

Keep the existing endpoint:

```text
POST /api/v1/analysis/swing/video
```

Required behavior:

* Preserve backward-compatible response fields where practical.
* Add new diagnostic fields through explicit schemas.
* Do not expose absolute filesystem paths.
* Do not expose local model paths.
* Return structured errors for invalid configuration or unusable pose data.
* Keep `pose_mode` and `overlay_source` behavior compatible with the existing UI.

## UI Requirements

Keep the current local browser workflow unless a compact diagnostic control is needed.

Required behavior:

* Keep `Run Swing Analysis` and `Clear Analysis` behavior.
* Keep unsupported throwing, pitching, and fielding states unchanged.
* Keep pose and evaluation-line toggles independent.
* Keep raw versus stabilized overlay debugging available.
* Add or revise compact diagnostics for:
  * active swing window,
  * phase confidence,
  * rejected/down-weighted pose frames,
  * player tracking ambiguity.
* Do not display large technical dumps by default.
* Do not hard-code baseball thresholds in UI JavaScript.

## Testing Requirements

Add deterministic tests without requiring private videos, network access, external
credentials, or large model files.

Required tests:

* Unit tests for pose-quality frame classification or weighting.
* Unit tests proving weak frames are ignored or down-weighted during phase detection.
* Unit tests for active swing window detection with long idle lead-in and post-swing
  sections.
* Unit tests for improved impact estimation where wrist velocity alone would fail.
* Unit tests for candidate-switch rejection with fake multi-pose MediaPipe results.
* Unit tests for candidate ambiguity diagnostics.
* Unit tests proving high-speed wrist/ankle movement is not over-smoothed.
* Unit tests for confidence/limitations when selected evidence uses interpolated,
  missing, low-confidence, or heavily stabilized landmarks.
* Integration tests for `SwingVideoAnalysisApplicationService` using injected fake
  estimators.
* API tests proving new diagnostics serialize without exposing local file paths.
* UI/static tests for any new diagnostic controls or rendering changes.

Use tiny synthetic frames, fake estimators, and deterministic pose fixtures. Do not add
real user videos or large binary fixtures.

## Documentation Requirements

Update documentation where behavior or architecture changes:

* `PLANS.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* Add or update an ADR under `docs/02_architecture/adr/` if active-window detection,
  pose-quality filtering, or tracking diagnostics become durable service contracts.
* `docs/04_motion_knowledge/swing.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Add a development log under `docs/03_development_log/`

Documentation must explain:

* The difference between body landmark quality and swing event quality.
* Why active swing window detection is used.
* Why impact is still estimated without bat/ball contact.
* How raw and stabilized overlays should be interpreted.
* How pose-quality diagnostics should be read by coaches, parents, and developers.
* Current limitations for cluttered scenes, camera angle, occlusion, small player size,
  bat visibility, and ball/contact detection.

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

* No user videos, large binary files, model weights, generated reports, `.env` files, or
  credentials are added.
* Media and model paths are not exposed in API responses or UI diagnostics.
* Existing stored-video upload, replay, delete, and swing-analysis workflows still work.
* Existing pose overlay and evaluation-line toggles still work independently.

## Acceptance Criteria

The task is complete only when:

* Pose-quality filtering or weighting is implemented before automatic phase detection.
* Active swing window detection narrows phase selection for videos with idle lead-in or
  post-swing frames.
* Player tracking reports candidate switches and ambiguity when multiple candidates are
  available.
* Improved impact estimation uses additional constraints beyond raw wrist velocity.
* Stabilization preserves high-speed wrist and ankle motion better than the previous
  behavior.
* The API returns structured diagnostics for pose quality, player tracking, active
  window detection, phase confidence, and evidence limitations.
* UI diagnostics remain compact and do not contain baseball rule thresholds.
* Deterministic unit and integration tests cover the new behavior.
* Product, architecture, motion-knowledge, manual, development-log, and planning docs are
  updated where behavior changes.
* Required quality commands pass.
* Final-review-planning finds no blocking issue.

## Follow-Up Candidates

These are useful but should remain separate tasks unless explicitly pulled into scope:

* Bat tip, bat barrel, and ball/contact detection.
* Persistent pose/result caching across app restarts.
* Calibrated annotated swing-fixture dataset.
* Camera-angle classification and side-view suitability scoring.
* Region-of-interest controls for expert users.
* Future throwing, pitching, and fielding pose-quality profiles.
