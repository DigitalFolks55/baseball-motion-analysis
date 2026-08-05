# DEV003-04 Swing Evaluation v1 Core Algorithm Update

## Goal

Update the swing evaluation workflow from pose-JSON/demo-data analysis to a local
video-driven workflow:

1. Automatically detect pose from every sampled video frame.
2. Overlay detected pose keypoints with labels on the replay video.
3. Stop requiring the user to assign one frame per swing phase.
4. Analyze the swing continuously across the pose sequence, or automatically detect the
   representative phase/event frames.
5. Revise the UI layout so replay is the top row and upload/library/analysis sit below.
6. Add an explicit button to clear analysis results and overlays.

This is a major algorithm and workflow update. It should remain local-PC-first and must
not create a release or deployment.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-01_Swing_evaluation_v1.md`
* `docs/99_prompts/DEV003-02_Swing_evaluation_v1_UI.md`
* `docs/99_prompts/DEV003-03_Swing_evalutation_v1_UI_revise.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md`
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
  * `tests/integration/test_swing_analysis_api.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_web_video_upload_replay_api.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/unit/test_web_video_library_storage.py`
  * video and media input tests under `tests/unit/`

## Current Implementation Context

DEV003-01 implemented swing analysis from already-available `PoseFrame` sequences.

DEV003-02 exposed that service through `/api/v1/analysis/swing` and a browser UI that
accepts pose JSON or demo pose data.

DEV003-03 revised the UI into a local review workspace and added a replay overlay that
draws points from current pose JSON or demo pose data.

Current limitations to address:

* Uploaded videos are not automatically converted into pose observations.
* Overlay points come from pose JSON/demo data, not detected video pose.
* The user can still provide phase frame indexes.
* The current swing metrics mostly use representative phase frames rather than fully
  continuous pose-sequence analysis.
* The current UI layout still needs to prioritize replay as the main first-row visual
  surface.

## Required UI Layout

Revise the browser UI to this structure:

```text
|          Replay video           |
| Upload video  | Motion analysis |
| Video library | Motion analysis |
```

Interpretation:

* Top row: full-width replay video panel.
* Lower left: upload video and video library stacked vertically.
* Lower right: motion analysis panel spanning the same lower-row height as upload plus
  library.

Required behavior:

* Replay video remains the primary first-viewport element.
* Upload and library remain on the left below replay.
* Motion analysis remains on the right below replay.
* Existing upload, library, delete, replay, speed, and frame-step behavior must remain
  intact.
* Keep the UI responsive. On narrow screens, stack in this logical order:
  1. Replay
  2. Upload Video
  3. Video Library
  4. Motion Analysis

## Auto Pose Detection Requirements

Implement automatic pose detection from video frames.

Required behavior:

* A user selects or uploads a stored video.
* The analysis workflow samples frames from that video.
* The pose layer runs pose detection on every sampled frame used for analysis.
* Pose results are converted into the existing internal `PoseFrame` model.
* Pose results include keypoint confidence values.
* Pose detection failures for individual frames should not crash the whole workflow.
* Low-confidence or missing keypoints should lower analysis confidence and add
  limitations.
* The browser should show progress/status while pose extraction and swing analysis run.

Frame handling:

* Define a configurable sampling policy.
* Recommended first policy:
  * Sample all frames for very short/tiny videos used in tests.
  * For normal videos, sample at a capped maximum frame count or target FPS to avoid
    blocking the local app.
* Preserve original frame indexes and timestamps when possible.
* Document the sampling policy in architecture and manuals.

Pose implementation:

* Prefer an explicit `PoseEstimator` interface if one is not already present.
* The concrete implementation may be:
  * a lightweight local pose estimator if dependency and packaging impact is acceptable,
  * an optional adapter behind a feature boundary,
  * or a deterministic/test estimator for this task if production pose dependency choice
    is not yet accepted.
* Before adding a production dependency, follow the dependency policy:
  * explain why it is needed,
  * compare alternatives,
  * note runtime impact,
  * note license, packaging, and local deployment concerns.
* Do not upload frames, videos, or images to external services.

## Pose Overlay Requirements

Overlay automatically detected pose on the replay video.

Required behavior:

* Overlay should draw detected keypoints for the frame nearest the current replay time.
* Overlay should draw labels for keypoints.
* Labels should be readable but not cover the video excessively.
* Overlay should distinguish:
  * body keypoints,
  * bat keypoints if available,
  * automatically detected phase/event frames,
  * low-confidence keypoints.
* Overlay should update when:
  * replay current time changes,
  * frame-step buttons are used,
  * analysis completes,
  * analysis is cleared.
* Overlay must not block video controls.
* If no detected pose is available, show a clear empty overlay state.
* If pose was detected from sampled frames rather than every original video frame, label
  the overlay as sampled-frame pose.

Do not put swing scoring rules in overlay rendering code. Overlay rendering should only
visualize pose and phase/event metadata returned by application services or API adapters.

## Continuous Swing Analysis Requirements

Do not require the user to assign one frame to each swing phase.

Replace the manual phase-frame workflow with one or both of these approaches:

1. Continuous analysis across the pose sequence.
2. Automatic phase/event detection from the pose sequence.

Required behavior:

* The user should not need to enter setup, stride, foot strike, impact, or follow-through
  frame indexes.
* Existing `phase_frames` input can remain as an internal/test override, but it should not
  be the primary UI workflow.
* The result should still expose phase/event information for user explanation and overlay
  highlighting.
* Phase/event detection should include confidence and limitations.
* Missing or ambiguous phase detection should lower confidence instead of crashing or
  producing overconfident feedback.

Recommended automatic phase/event detection candidates:

* Setup:
  * early stable frames before major hand/hip movement.
* Load / stride:
  * lead foot or lead knee starts moving away from setup,
  * head/hip loading pattern changes.
* Foot strike:
  * lead ankle/foot reaches its forward-most or planted position,
  * lead knee starts bracing.
* Impact:
  * bat tip/barrel or wrist path reaches likely contact zone,
  * maximum bat/wrist speed near front side when bat keypoints are unavailable.
* Follow-through:
  * frames after impact where wrists/bat continue through the zone and torso decelerates.

These are heuristic candidates and must include limitations until calibrated.

## Continuous Metric Requirements

Update swing metrics so they can use sequences, not just one fixed phase frame per
metric.

Required behavior:

* Metrics should accept ordered pose sequences and detected phase/event windows.
* Metrics should use a meaningful frame/window around each event, not only a single user
  selected frame.
* Metric results should expose:
  * measured value,
  * target range where known,
  * severity,
  * confidence,
  * evidence frame indexes or frame ranges,
  * limitations.
* Existing metric names may remain, but calculations should be adapted to sequence-aware
  inputs where appropriate.

Required metric updates:

* Shin-torso parallelism:
  * evaluate over setup/load windows and aggregate stable posture.
* Early connection angle:
  * evaluate around detected rotation start rather than manual foot-strike frame only.
* Lead knee blocking index:
  * compare lead knee angle trend from detected foot strike to impact.
* Head translation ratio:
  * calculate displacement over setup-to-impact window.
* Estimated attack angle:
  * fit a local trajectory around detected impact using bat tip/barrel when available,
    otherwise wrist/grip with low confidence.
* Hip-shoulder separation timing:
  * compare pelvis and shoulder rotation timing or peak angular velocity over the
    sequence.

## Application-Service Requirements

Introduce a video-driven swing analysis application workflow.

Recommended service shape:

```text
AnalyzeSwingVideoRequest
  media_id or stored-video reference
  handedness
  sampling options
  optional debug/test pose estimator

SwingVideoAnalysisApplicationService
  get video content through media application/storage services
  sample frames
  run pose detection
  run continuous/automatic swing analysis
  generate feedback
  return analysis + feedback + pose overlay data
```

Keep boundaries:

* `ui`: user controls and rendering only.
* `api`: request validation, application-service call, serialization, structured errors.
* `app`: orchestration of video lookup, sampling, pose extraction, swing analysis, and
  feedback.
* `video`: frame sampling and video metadata.
* `pose`: pose estimator interface and output conversion.
* `motion`: swing phases/events and sequence-aware metric calculations.
* `analysis`: scoring, rules, confidence, and fault detection.
* `feedback`: user-facing text and drills.
* `storage`: media lookup and report persistence only if explicitly scoped.

Do not call low-level video, pose, motion, analysis, or feedback functions directly from
UI callbacks.

## API Requirements

Add a browser-safe API endpoint for video-driven swing analysis.

Recommended endpoint:

```text
POST /api/v1/analysis/swing/video
```

Request fields:

* `media_id`: stored video ID.
* `handedness`: `right_handed`, `left_handed`, or `unknown`.
* `sampling`: optional sampling options if exposed.

Response fields:

* `analysis`: overall score, phase/event scores, metrics, faults, confidence,
  limitations.
* `feedback`: summary, good points, improvement points, drills, confidence,
  limitations.
* `pose`: browser-safe pose frames used for analysis.
* `events`: automatically detected phase/event frames or windows.
* `overlay`: keypoint labels, confidence, frame indexes/timestamps, and visual categories
  needed by the browser overlay.

Error handling:

* invalid media ID,
* missing stored file,
* unreadable video,
* pose extraction unavailable,
* no usable pose frames,
* ambiguous phase detection,
* sampling limit exceeded,
* internal service errors.

Errors must be structured and must not leak local filesystem paths.

Keep the existing pose-JSON endpoint for tests/dev workflows unless there is a documented
reason to deprecate it.

## UI Requirements

Update the motion-analysis UI:

* Remove manual phase frame inputs from the primary user workflow.
* Keep handedness selection.
* Add a `Run Swing Analysis` button that analyzes the selected stored video.
* Add a `Clear Analysis` button.
* Clear Analysis should:
  * clear analysis results,
  * clear detected pose/event overlay,
  * clear analysis status/errors,
  * leave uploaded videos and library records untouched,
  * leave replay selection untouched unless the user deletes the video.
* Show progress/status:
  * waiting for selected video,
  * sampling frames,
  * detecting pose,
  * detecting swing events,
  * scoring,
  * complete,
  * failed.
* Show detected event/phase summary after analysis.
* Show analysis confidence and limitations prominently.
* Keep throwing, pitching, and fielding as planned categories unless their services are
  implemented separately.

## Non-Goals

* Do not implement throwing, pitching, or fielding analysis.
* Do not add hosted services, cloud uploads, authentication, mobile adapters, Docker,
  deployment, release notes, version bumps, or packaging work.
* Do not upload user videos or frames externally.
* Do not require large real-user videos in tests.
* Do not claim professional biomechanics, injury diagnosis, or guaranteed coaching truth.
* Do not persist reports unless explicitly added through storage/application services in
  this task.

## Documentation Requirements

Update documentation if behavior or architecture changes:

* `PLANS.md` with DEV003-04 scope, implementation decisions, tasks, QA result, and final
  planning review.
* `docs/01_product/feature_catalog.md` for video-driven swing analysis, automatic pose,
  continuous/event-based analysis, and overlay labels.
* `docs/02_architecture/system_overview.md` for the video-to-pose-to-analysis pipeline.
* `docs/02_architecture/adr/` for important decisions, especially:
  * pose estimator dependency/adapter choice,
  * continuous swing phase/event detection model,
  * browser overlay data contract if materially changed.
* `docs/03_development_log/` with a dated log entry.
* `docs/04_motion_knowledge/swing.md` if metric or phase/event evaluation rules change.
* `docs/05_manuals/`:
  * update `web_video_upload_replay.md`,
  * update `swing_motion_analysis_ui.md` or create it if missing.

Manuals must explain:

* how to upload/select a video,
* how automatic pose detection works at a high level,
* what the overlay labels mean,
* why detected pose may be imperfect,
* how phases/events are automatically detected,
* how to run and clear analysis,
* how to interpret confidence and limitations.

Do not update changelog, release notes, versions, or deployment docs.

## Testing Requirements

Add focused tests without requiring private or large user media.

Required unit tests:

* Pose estimator interface and deterministic fake/test implementation.
* Video frame sampling policy for analysis.
* Pose-to-`PoseFrame` conversion.
* Automatic swing phase/event detection from deterministic pose sequences.
* Sequence-aware metric calculations.
* Confidence and limitations for missing/low-confidence keypoints.
* Clear-analysis frontend behavior if it is testable with static tests.

Required integration tests:

* Video-driven swing analysis application service with a tiny video fixture and fake pose
  estimator.
* API endpoint for `POST /api/v1/analysis/swing/video`.
* Browser-safe errors for invalid media ID, missing video, and no usable pose.
* Existing upload, library, replay, delete, health, and pose-JSON swing API tests still
  pass.

Required UI/static tests:

* New layout:
  * top replay row,
  * lower-left upload/library,
  * lower-right motion analysis.
* Run Swing Analysis requires a selected stored video.
* Clear Analysis button is present.
* Manual phase frame inputs are absent from the primary UI.
* Overlay canvas/layer supports labels.
* Static JavaScript includes overlay clearing behavior.
* Static JavaScript calls the video-driven swing endpoint, not only the pose-JSON
  endpoint, for the main run workflow.

Use deterministic fake pose results and tiny generated video fixtures. Do not commit
large videos, model weights, user media, generated reports, secrets, or credentials.

## Acceptance Criteria

* A user can upload/select a stored video and run swing analysis without pasting pose
  JSON.
* The app samples video frames and runs pose detection through a pose-layer interface.
* Detected pose keypoints are overlaid on the replay video with labels.
* The app does not require manual one-frame-per-phase assignment in the main UI.
* Swing phases/events are detected automatically or metrics run continuously over the
  pose sequence.
* Results include analysis, feedback, confidence, limitations, detected events, and pose
  overlay data.
* The layout matches:

```text
|          Replay video           |
| Upload video  | Motion analysis |
| Video library | Motion analysis |
```

* A `Clear Analysis` button clears results and overlays without deleting media.
* Existing media upload/library/replay/delete behavior remains unchanged.
* Existing pose-JSON swing API behavior remains available unless explicitly documented
  otherwise.
* UI/API/storage/video modules do not contain swing coaching rules.
* Tests cover pose extraction, automatic event detection or continuous analysis, API,
  UI layout, overlay labels, and clear-analysis behavior.
* Required quality commands pass.
* Relevant docs and manuals are updated.
* No release or deployment is created.

## Required Quality Commands

After code changes, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

If static JavaScript is changed and Node is available:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
```

## Open Questions For Implementation

Resolve these before or during implementation:

* Which concrete pose-estimation backend should be used for local automatic pose
  detection?
* Should production pose estimation be implemented now, or should this task first add a
  stable interface plus fake/test estimator and defer the concrete backend?
  - Plan to implement pose estimation now. 
* What sampling cap is acceptable for local responsiveness?
* Should detected pose results be cached for a stored video to avoid rerunning pose
  detection?
  - Yes. Implement caching for pose results.
* Should automatic phase/event detection return single event frames, frame windows, or
  both?
* Should overlay labels show all keypoints all the time, or only a reduced readable set
  by default?
  - Only a reduced readable set by default. However, labeling is not consistent then no labels required.

Recommended defaults if no clarification is available:

* Add the stable pose-estimator interface and deterministic fake/test estimator first;
  defer heavy production pose dependency if dependency review is not complete.
* Use a conservative sampling cap for local responsiveness and document it.
* Return both event frame indexes and event windows when feasible.
* Show a readable reduced label set by default, with unlabeled small points for secondary
  keypoints if needed.
