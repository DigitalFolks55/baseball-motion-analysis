# PLANS.md

## Project: baseball_motion_analysis

## Product Goal

Build a local-PC application that analyzes baseball motion from uploaded videos or ordered image sequences and gives useful feedback about good and bad points in the player's movement.

The current product should run on the user's computer without a hosted web service. Uploaded media, local metadata, and generated reports should stay in the local environment by default.

Initial motion targets:

1. Swing
2. Fielding
3. Throwing
4. Pitching

Current and future platform targets:

1. Local-PC app
2. Web app
3. iPhone app
4. Android app

## Current Strategy

Use a local-PC-first, service-oriented architecture.

Application services should support local UI workflows for upload/import, local storage, replay, motion analysis, scoring, and feedback report generation. The analysis core must not depend on the UI. Future web or mobile adapters can call the same application services or equivalent service interfaces.

## Agent Workflow

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
  -> release
```

## Milestones

### Milestone 0: Repository Foundation

Status: DONE

Goals:

* Create initial repository structure
* Configure uv
* Configure Codex agents
* Configure Obsidian docs
* Configure lint, format, type check, and tests

Acceptance criteria:

* `uv sync` works
* `uv run pytest` works
* `uv run ruff check .` works
* `uv run mypy src` works
* GitHub Actions CI workflow exists for lint, format check, type check, and tests
* Release-check workflow exists for release validation and artifact build
* Dependabot is configured for GitHub Actions and uv dependency updates
* Basic docs exist
* Agent workflow is documented

### Milestone 1: Local Media Upload, Import, and Metadata

Status: DONE

Goals:

* Upload or import video through a local UI
* Upload or import ordered image sequences through a local UI
* Validate file type, readability, ordering, and size
* Store imported media in the local environment
* Extract metadata for videos and image sequences

Acceptance criteria:

* Local application service accepts a sample video fixture
* Local application service accepts a tiny ordered image-sequence fixture
* Imported files are represented by stable local media IDs
* Invalid files and unordered sequences return clear errors
* Unit tests and application-service integration tests exist

DEV001-01 local media input foundation scope:

* Recorded local video file validation, metadata extraction, and frame sampling
* Multiple local image file validation, sorting, and conversion into a common frame sequence
* Local camera stream interface contract for future real-time analysis
* Local filesystem path handling with clear validation errors
* Optional local media copy behavior using a configurable media root
* Common `FrameSequence` model shared by video, image-sequence, and camera inputs

DEV001-01 non-goals:

* Full pose estimation
* Full real-time motion analysis
* Swing, pitching, batting, throwing, or fielding classification
* Production video storage
* Cloud upload/download
* User account management
* Full desktop GUI implementation
* Browser upload endpoints
* FastAPI upload endpoints
* Browser WebSocket camera streaming
* MediaPipe integration

DEV001-01 acceptance criteria:

* A local video file can be validated, opened, and converted into a `FrameSequence`.
* A local image list can be validated, opened, sorted, and converted into a `FrameSequence`.
* A local camera stream interface exists and can be tested without real camera hardware.
* Input logic is separated from pose estimation and motion analysis.
* Local file paths are handled safely with clear validation errors.
* Docs explain recorded video, image-sequence, and camera-stream input modes and limitations.
* Unit tests cover validation, metadata extraction, video sampling, image sequence creation, local copy behavior, and camera interface behavior.
* No large media files are committed.

### Milestone 2: Local Replay MVP

Status: IN_PROGRESS

Goals:

* Replay newly uploaded videos in the UI
* Replay newly uploaded image sequences in the UI
* Browse and replay previously stored files
* Provide replay manifests through application services

Acceptance criteria:

* UI can replay a stored video
* UI can replay a stored image sequence in order
* Replay does not require a hosted web service
* Tests cover replay manifest creation for videos and image sequences

DEV002-01 dual-mode web video upload and replay UI scope:

* Browser-based video upload page served by the existing FastAPI application
* Local browser mode where the app runs on the user's computer at `127.0.0.1`
* Server mode where the same app can run remotely with configurable host, port, media root, database path, and upload limit
* Server-side streamed multipart video uploads into a controlled staging location
* Reuse of the existing `MediaInputService`, video validation, OpenCV metadata extraction, and local media copy behavior
* Stable media IDs, SQLite metadata persistence, and media-ID-based content serving
* HTML5 video replay manifest, video content endpoint, browser seeking, and playback-speed controls
* Uploaded-video deletion through application services, including stored file removal and metadata record removal

DEV002-01 non-goals:

* Pose estimation
* Motion classification
* Swing, pitching, throwing, or fielding analysis
* Feedback reports
* Video annotation overlays
* Image-sequence upload UI
* Camera streaming or WebSocket video streaming
* Automatic transcoding, FFmpeg integration, cloud storage, authentication, authorization, Docker, deployment, or release publishing

DEV002-01 acceptance criteria:

* A user can open `/` in a browser and see a video upload, library, and replay UI.
* The upload endpoint streams uploaded videos to a staging file without loading the whole file into memory.
* Upload size is limited by configuration and failed staging files are cleaned up.
* Existing local media input validation and metadata extraction are reused through application services.
* Imported videos receive stable media IDs and persisted metadata records.
* The browser receives media IDs and replay URLs, not absolute filesystem paths.
* Stored videos are listed and can be replayed through an HTML5 video player.
* Seeking works through a byte-range-capable content endpoint.
* Runtime mode, media root, database path, maximum upload size, host, and port are configurable.
* Browser playback limitations for codecs and non-browser-oriented containers are documented.
* Users can remove an uploaded video from the UI.
* Deletion removes the stored media file when it exists and removes the metadata record.
* Deletion resolves targets only by media ID and does not expose absolute filesystem paths.
* Tests cover repository, file store, replay manifest, upload validation, staging cleanup, range responses, API responses, and existing health behavior.
* Tests cover successful deletion, missing-file deletion cleanup, and invalid media ID deletion errors.

DEV002-01 risks:

* Uploaded videos contain personal information and must stay under configured storage.
* Browser playback codec support varies by browser and operating system.
* Large uploads can exhaust memory or disk space if limits or streaming behavior regress.
* Temporary upload files may remain after errors unless cleanup paths are tested.
* Online server files may be ephemeral depending on the hosting environment.
* Public online deployment requires authentication and authorization that are outside this task.
* Concurrent upload behavior may affect a SQLite metadata index.
* Exact frame-by-frame playback cannot be guaranteed by a normal HTML5 video player.
* Browser seeking requires correct byte-range response behavior.
* Accidental deletion would remove local user media, so the UI must require an explicit user action.
* Deletion must keep metadata and file storage consistent even when a stored file is already missing.

### Milestone 3: Pose Extraction Interface

Status: TODO

Goals:

* Define pose estimation interface
* Add first implementation
* Return frame-level keypoints in a stable internal format

Acceptance criteria:

* Pose estimator can be mocked in tests
* Motion analysis does not depend on a specific pose library directly
* Sample video or image-sequence fixture test exists

### Milestone 4: Swing Analysis MVP

Status: IN_PROGRESS

Goals:

* Detect basic swing phases
* Evaluate simple rule-based checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns swing analysis result
* Result includes good points, bad points, and confidence notes
* Documentation explains current evaluation limitations

DEV003-01 swing evaluation v1 scope:

* Stable internal pose/keypoint observation models for swing evaluation
* Lead/rear handedness normalization for right-handed, left-handed, and unknown swings
* Swing phase references for setup, stride/load, foot strike, impact, and follow-through
* Deterministic side-view kinematic metrics:
  * Shin-torso parallelism
  * Early connection angle
  * Lead knee blocking index
  * Head translation ratio
  * Estimated attack angle
  * Hip-shoulder separation timing
* Rule-based detection for:
  * Door swing / casting
  * Forward axis drift / rushing
  * Arms-only / one-piece swing
  * Excessive upper swing / early extension
  * Collapsed lead side
* 100-point phase-weighted scoring with metric deductions and confidence handling
* Feedback report generation with summary, good points, improvement points, drills,
  confidence, and limitations
* Application-service orchestration for already-available pose/keypoint sequences

DEV003-01 implementation decisions:

* Use an internal `pose` schema with named keypoints, normalized 2D coordinates, and
  confidence values.
* Support caller-provided phase frame indexes and provide a conservative automatic
  fallback based on ordered frame positions.
* Keep uncertain numeric thresholds configurable until calibrated fixtures exist.
* Treat bat tip / barrel keypoints as optional and return explicit limitations when
  attack-angle evidence is weak.
* Return in-memory analysis and feedback results only; report persistence remains a
  later task.

DEV003-01 non-goals:

* New pose-estimation model integration
* Hosted web service behavior, cloud uploads, mobile adapters, deployment, or release
* Real user video fixtures or large binary test data
* UI integration unless needed through the application-service boundary
* Medical diagnosis, injury prediction, or absolute coaching claims

DEV003-01 acceptance criteria:

* A local application service can return a swing analysis result from deterministic
  synthetic pose observations.
* The implementation detects or accepts five swing phases.
* Metric, fault, scoring, feedback, and application-service behavior are covered by
  focused tests.
* Missing or low-confidence keypoints lower confidence and add limitations instead of
  crashing.
* Swing rules stay out of UI, API, storage, video, and sequence modules.
* Required quality commands pass.

DEV003-01 final-review-planning result:

* Implementation matches the documented local-PC-first service boundary.
* Unit and integration tests cover the required metric, fault, scoring, feedback, and
  application-service behavior.
* Documentation is updated in product, architecture, development-log, and motion
  knowledge docs.
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: concrete pose estimation, calibrated
  phase detection, UI launch behavior, and report persistence.

DEV004-01 swing evaluation v2 replacement planning scope:

* Replace the v1 swing evaluation methodology with a youth baseball 2D side-view
  baseline model from `docs/80_references/Youth Baseball Swing Baseline Research.pdf`.
* Preserve the local-PC-first application-service workflow for pose-sequence and
  stored-video swing analysis.
* Add phase-aligned, scale-normalized v2 metrics for normalized stance width, torso
  forward tilt and preservation, grip loading, rear knee sway, head translation, early
  connection, lead knee blocking, hip-shoulder separation timing, estimated attack
  angle, and follow-through posture/balance.
* Replace normal v1 fault/scoring semantics with v2 baseline rule evaluation,
  phase-weighted deductions, confidence handling, and drill-mapped feedback.
* Keep all thresholds configurable, and document formula-only thresholds from the PDF as
  visually verified or provisional before making them defaults.

DEV004-01 non-goals:

* Hosted services, cloud uploads, mobile adapters, deployment, release work, Docker,
  PyPI publishing, new production model downloads, committed model weights, bat/ball
  detector implementation, report persistence, or non-swing motion implementations.

DEV004-01 acceptance criteria:

* Normal swing analysis paths return v2 methodology metadata and v2 metric/error names.
* V1 scoring semantics are removed or isolated from normal swing evaluation behavior.
* Pose-sequence and stored-video swing analysis remain available through application
  services.
* UI/API adapters do not contain v2 thresholds, scoring rules, drill mappings, or
  baseball coaching logic.
* Unit tests cover v2 metrics, error detection, scoring, feedback, confidence, and
  missing-keypoint behavior.
* Integration tests cover application-service and browser-safe API behavior for v2.
* Product, architecture, motion-knowledge, manual, development-log, and planning docs
  are updated where behavior changes.
* Required quality commands pass and final planning review has no blocking issue.

DEV004-01 final-review-planning result:

* Implementation replaces the normal v1 swing methodology with
  `methodology_version: swing_evaluation_v2`.
* Pose-sequence and stored-video swing analysis remain available through the existing
  application-service and API boundaries.
* V2 metrics now include normalized stance width, torso forward tilt, torso tilt
  preservation, grip loading vector, rear knee sway, head translation, early connection,
  lead knee blocking, hip-shoulder separation timing, estimated attack angle, and
  follow-through posture/balance.
* UI/API adapters serialize and display methodology metadata and metric units without
  owning baseball thresholds, scoring rules, or drill mappings.
* Unit and integration tests cover v2 methodology metadata, metric output, scoring,
  feedback, missing keypoints, application-service behavior, and browser-safe API
  behavior.
* Product, architecture, ADR, motion-knowledge, manual, development-log, and planning
  docs are updated.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: threshold calibration from validated
  swing fixtures, bat/ball evidence sources, and improved event calibration.

DEV004-02 swing evaluation v2 overlay evaluation lines planning scope:

* Add optional evaluation-line overlays for stored-video swing v2 analysis.
* Return browser-safe evaluation-line primitives from the application/API response.
* Add an `Evaluation Lines` toggle immediately to the left of the replay `Speed`
  control.
* Draw returned evaluation lines on the existing replay canvas without rerunning
  analysis.

DEV004-02 non-goals:

* New swing scoring rules or threshold changes.
* Bat, ball, or barrel detector implementation.
* Throwing, pitching, fielding, report persistence, release, deployment, or packaging
  work.

DEV004-02 acceptance criteria:

* Evaluation-line geometry is generated by app/domain-owned analysis output, not browser
  rule logic.
* The browser toggle is off by default, disabled until overlay data exists, and uses
  `aria-pressed`.
* Pose keypoints, event labels, raw/stabilized overlay source selection, speed, and
  frame stepping continue to work.
* Tests cover evaluation-line construction, missing-keypoint handling, app service
  output, API serialization, UI markup, and JavaScript toggle behavior.

DEV004-02 final-review-planning result:

* Stored-video swing analysis returns browser-safe `evaluation_overlay` line primitives
  generated by the application service from v2 metric evidence and pose frames.
* The replay toolbar includes an `Evaluation Lines` toggle immediately to the left of
  `Speed`; it is off by default, disabled until overlay data exists, uses
  `aria-pressed`, and redraws without rerunning analysis or changing speed.
* Existing pose keypoint overlays, event labels, raw/stabilized overlay source
  selection, replay speed, frame stepping, clear analysis, upload, library, and replay
  behavior remain covered by tests.
* Product, architecture, ADR, manual, development-log, and planning docs are updated.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: MediaPipe body landmarks still lack
  bat and ball evidence, so bat-path-specific overlay lines remain limited until future
  detectors are added.

DEV004-03 swing evaluation v2 UI update planning scope:

* Make the `Video Library` panel scrollable for long local libraries.
* Add an independent `Poses` replay-toolbar toggle immediately before
  `Evaluation Lines`, preserving the order `Poses | Evaluation Lines | Speed`.
* Disable pose keypoint text tags while preserving pose skeletons, pose points, event
  labeling, and evaluation-line labels.
* Audit and fix evaluation-line construction/rendering so all required DEV004-02 line
  categories are returned and visible when evidence exists.
* Clarify overlay status and labels so users can distinguish pose overlays from
  evaluation-line overlays.

DEV004-03 non-goals:

* New swing scoring rules, threshold changes, drill mapping changes, or fault logic
  changes.
* Bat, ball, or barrel detector implementation.
* Throwing, pitching, fielding, report persistence, release, deployment, or packaging
  work.

DEV004-03 acceptance criteria:

* Long video libraries scroll without breaking upload, replay, delete, or refresh
  behavior.
* `Poses` and `Evaluation Lines` toggles are independent, accessible with
  `aria-pressed`, and redraw the canvas without rerunning analysis or changing speed.
* Pose text tags are disabled by default, while pose skeletons/points and event labels
  remain available when enabled.
* All required DEV004-02 evaluation-line categories are generated and rendered when
  their evidence exists; missing evidence skips or lowers confidence without crashing.
* UI/API adapters do not compute baseball scoring rules.
* Tests, product docs, manual, development log, and final planning review are updated.

DEV004-03 final-review-planning result:

* The `Video Library` list now uses a bounded scroll area and preserves existing upload,
  refresh, replay, and delete behavior.
* The replay toolbar order is `Poses | Evaluation Lines | Speed`.
* `Poses` and `Evaluation Lines` are independent toggle buttons with `aria-pressed`;
  toggling either redraws the overlay canvas without rerunning analysis or changing
  playback speed.
* `Poses` defaults on after pose overlay data exists and controls pose skeletons and
  keypoints. Pose text tags are disabled by default.
* `Evaluation Lines` remains off by default and controls service-returned metric guide
  lines with concise labels.
* Evaluation-line construction now verifies all required DEV004-02 metric categories for
  complete synthetic evidence, including follow-through posture and balance evidence.
* Product, architecture, manual, development-log, and planning docs are updated.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: MediaPipe body landmarks still lack
  bat and ball evidence, and overlays inherit sampled-pose/event-detection uncertainty.

DEV004-04 swing evaluation v2 aspect issue planning scope:

* Audit v2 swing metrics and related fault-evidence helpers for aspect-ratio-sensitive
  geometry.
* Introduce a domain-owned measurement coordinate policy that converts normalized pose
  points into same-space image coordinates when frame dimensions are available.
* Pass stored-video dimensions through application services into swing phase detection,
  metric extraction, scoring, and fault evidence.
* Keep browser evaluation-line overlay coordinates normalized so the existing replay
  canvas contract remains unchanged.
* Add non-square-frame regression tests proving corrected metric values differ from raw
  mixed-normalized coordinate math.

DEV004-04 non-goals:

* New scoring thresholds, drill mapping, feedback rewrites, pose-estimator behavior,
  bat/ball detector implementation, release, deployment, or packaging work.

DEV004-04 acceptance criteria:

* Stored-video swing v2 geometry uses frame width and height for distance, displacement,
  vector-angle, and joint-angle math.
* Pose-sequence callers can provide optional frame dimensions; missing dimensions retain
  the documented normalized-coordinate fallback without crashing.
* Normalized stance width, torso tilt, head drift, attack angle, and app/API dimension
  plumbing are covered by non-square-frame tests.
* Evaluation-line labels and normalized render coordinates continue through the existing
  frontend contract.
* Product, architecture, motion-knowledge, development-log, and planning docs are
  updated.
* Required quality commands pass and final planning review has no blocking issue.

DEV004-04 final-review-planning result:

* Swing v2 now uses `SwingMeasurementSpace` for aspect-aware distance, horizontal
  displacement, vector-angle, and joint-angle math when frame dimensions are available.
* Stored-video analysis passes source width and height into automatic phase detection,
  v2 metric extraction, scoring, and secondary fault evidence.
* Direct pose-sequence analysis accepts optional `frame_width` and `frame_height`;
  missing dimensions keep the documented normalized-coordinate fallback.
* Evaluation overlay primitives continue to return normalized points and labels for the
  existing browser replay contract.
* Unit and integration tests cover non-square-frame stance width, torso tilt, head
  translation, attack angle, stored-video dimension plumbing, API dimension plumbing,
  and overlay-line compatibility.
* Product, architecture, ADR, motion-knowledge, manual, development-log, and planning
  docs are updated.
* Required quality commands passed:
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: pose-sequence callers that omit frame
  dimensions still use the legacy fallback, and thresholds should still be calibrated
  against validated real swing fixtures.

DEV004-05 stance width baseline adjustment planning scope:

* Change normalized stance width target range from `1.2`-`1.5` torso lengths to
  `1.0`-`1.2` torso lengths.
* Keep the rule in the analysis layer and out of UI/API callbacks.
* Update deterministic tests and motion-knowledge documentation for the new target.

DEV004-05 final-review-planning result:

* `SwingAnalysisConfig` now uses `stance_width_min_ratio=1.0` and
  `stance_width_max_ratio=1.2`.
* The deterministic good swing fixture remains inside the updated stance-width range.
* Tests assert the returned normalized stance-width target range and good severity.
* Motion-knowledge and DEV004-01 prompt docs no longer state the old `1.2`-`1.5`
  baseline.
* No release or deployment was created.

DEV004-05 swing evaluation v2 UI update 2 planning scope:

* Add a replay-toolbar metric dropdown between `Evaluation Lines` and `Speed`.
* Populate the dropdown from returned `evaluation_overlay.metric_name` values for the
  current analysis result, with `All metrics` as the default behavior.
* Filter browser-rendered evaluation lines by selected metric without rerunning analysis,
  changing playback speed, changing replay selection, clearing results, or modifying
  service/API contracts.
* Keep `Evaluation Lines` as the master on/off control and keep `Poses` independent.

DEV004-05 swing evaluation v2 UI update 2 final-review-planning result:

* The replay toolbar now orders controls as `Poses`, `Evaluation Lines`, `Metric`, then
  `Speed`.
* The metric dropdown is disabled until evaluation-line data exists, resets to
  `All metrics` when analysis is cleared or a video changes, and uses concise UI labels
  for returned metric names.
* Browser canvas drawing filters already-returned evaluation primitives by
  `metric_name`; the app, API, motion, analysis, and feedback contracts remain unchanged.
* Static integration tests cover toolbar order, dropdown population logic, selected
  metric filtering, `All metrics`, the `Evaluation Lines` master toggle path, and
  metric-change redraw behavior without analysis reruns or speed changes.
* No ADR was added because no service/API data contract changed.
* No release or deployment was created.

DEV004-06 swing evaluation v2 UI update 3 planning scope:

* Convert the replay-toolbar `Metric` control from single-select filtering to
  multi-select filtering over returned `evaluation_overlay.metric_name` values.
* Preserve the `All metrics` default behavior and keep `Evaluation Lines` as the master
  on/off control.
* Keep metric selection changes in the browser only; do not rerun analysis, change
  playback speed, change replay selection, or alter app/API contracts.
* Constrain evidence-heavy metric and fault result cells with bounded scrolling so long
  frame lists or evidence text do not expand the results layout.

DEV004-06 swing evaluation v2 UI update 3 final-review-planning result:

* The replay toolbar still orders controls as `Poses`, `Evaluation Lines`, `Metric`, then
  `Speed`, and `Metric` now supports multiple selected metrics.
* `All metrics` remains the default state. Empty or all/default selection draws all
  applicable returned evaluation lines, while specific selections draw only lines whose
  returned `metric_name` is in the selected set.
* Browser filtering, option labels, concise overlay status, and canvas redraws remain in
  the UI layer. The app, API, motion, analysis, and feedback contracts are unchanged.
* Metric evidence frame cells and detected-fault evidence text use bounded, focusable,
  vertically scrollable wrappers to limit layout growth.
* Static integration tests cover multi-select markup, toolbar order, metric option
  population, selected-set filtering, all-metrics behavior, master toggle gating,
  no-rerun redraw behavior, and scrollable evidence styling.
* No ADR was added because no service/API data contract changed.
* No release or deployment was created.

DEV004-07 swing evaluation v2 UI update 4 planning scope:

* Replace the visible multi-row `Metric` selector with a compact dropdown-box style
  control similar to the replay `Speed` select while preserving multi-metric selection.
* Continue filtering already-returned evaluation-line primitives by selected
  `metric_name` values in the browser only.
* Narrow the `Metrics` table `Evidence` column to roughly five frame numbers and keep
  longer evidence frame lists accessible through bounded scrolling.
* Add bounded table-cell wrappers so unusually large table content scrolls instead of
  expanding the result layout.

DEV004-07 swing evaluation v2 UI update 4 final-review-planning result:

* The replay toolbar still orders controls as `Poses`, `Evaluation Lines`, `Metric`, then
  `Speed`; `Metric` is now a compact dropdown button with a checkbox menu.
* Multi-metric filtering is unchanged semantically: `All metrics` or empty/default state
  draws all returned evaluation lines, and specific checkbox selections draw only lines
  whose returned `metric_name` is in the selected set.
* The `Metrics` table marks its evidence column as compact and wraps evidence frame
  lists in bounded, focusable, scrollable content.
* General table cells now use bounded content wrappers so future unusually large table
  values do not expand the page layout.
* The app, API, motion, analysis, and feedback contracts are unchanged; no ADR was added.
* No release or deployment was created.

### Milestone 5: Fielding Analysis MVP

Status: TODO

Goals:

* Detect basic fielding posture and movement checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns fielding analysis result
* Feedback is understandable to non-engineers
* Tests cover core rule logic

### Milestone 6: Pitching / Throwing Analysis MVP

Status: TODO

Goals:

* Detect basic throwing phases
* Evaluate balance, arm path, stride, and follow-through checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns pitching analysis result
* Tests cover core rule logic
* Limitations are documented

### Milestone 7: Local UI MVP

Status: IN_PROGRESS

Goals:

* Upload or import videos and ordered image sequences
* Store imported media locally
* Browse uploaded and stored media
* Replay videos and image sequences
* Select motion type
* Display motion scores and feedback reports

Acceptance criteria:

* User can import a video or image sequence
* User can replay newly imported and previously stored media
* User can see analysis result and report
* UI and application services remain separated

DEV003-02 swing evaluation v1 UI scope:

* Local web UI panel for swing analysis from already-extracted pose/keypoint data.
* Pasted pose JSON input and deterministic demo pose data for local verification.
* Handedness selection for right-handed, left-handed, and unknown swings.
* Optional phase frame inputs for setup, stride/load, foot strike, impact, and
  follow-through.
* HTTP adapter at `/api/v1/analysis/swing` that converts browser-safe JSON into
  `AnalyzeSwingRequest`, calls `SwingAnalysisApplicationService`, and returns analysis
  plus feedback JSON.
* Result display for overall score, phase scores, metrics, detected faults, good points,
  improvement points, drills, confidence, and limitations.

DEV003-02 implementation decisions:

* Keep video-to-pose extraction outside this task; the UI must label swing analysis as
  pose-data based and must not imply that uploaded videos are automatically analyzed.
* Keep swing analysis results in memory only; report persistence remains future work.
* Do not expose `SwingAnalysisConfig` threshold overrides through the public UI/API until
  calibration and settings UX are designed.
* Keep all baseball swing rules and feedback text generation in `motion`, `analysis`,
  and `feedback`; UI and API adapters only validate, serialize, call app services, and
  render returned content.

DEV003-02 non-goals:

* Production pose estimation from video, bat detection, or new computer-vision models.
* Persistent swing reports or report storage.
* Hosted services, cloud uploads, authentication, mobile adapters, Docker, deployment, or
  release work.
* Real user videos, large fixtures, model weights, generated reports, secrets, or local
  media in git.

DEV003-02 acceptance criteria:

* The local web UI includes a swing analysis panel.
* The UI can submit pose JSON or demo pose data to the swing analysis API adapter.
* The API adapter calls `SwingAnalysisApplicationService` and returns deterministic
  analysis and feedback JSON.
* Invalid pose input returns structured browser-safe API errors and displays a clear UI
  error.
* Existing upload, library, replay, and health behavior remains unchanged.
* Tests cover successful and failing API/UI behavior.
* Required quality commands pass.
* Final planning review has no blocking issue.

DEV003-02 final-review-planning result:

* Implementation matches the documented local-PC-first UI/API adapter scope.
* The API adapter calls `SwingAnalysisApplicationService` and keeps swing rules out of
  UI, API, storage, video, and sequence modules.
* The local web UI clearly labels analysis as pose-data based and does not claim
  automatic analysis of uploaded videos.
* Integration tests cover successful API behavior, invalid handedness, unknown keypoint
  names, empty frames, invalid phase frames, malformed numeric values, and UI/static
  exposure.
* Documentation is updated in product, architecture, motion-knowledge, development-log,
  and planning docs.
* Required quality commands passed:
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: concrete pose estimation,
  uploaded-video analysis workflow, calibrated phase detection, and report persistence.

DEV003-03 swing evaluation v1 UI revision scope:

* Revise the local web UI into one desktop review row with three columns:
  * left column for `Upload Video` and `Video Library`
  * middle column headed `Motion Analysis`
  * right column for `Replay`
* Add a motion selector with swing, throwing, pitching, and fielding.
* Keep swing as the only runnable motion analysis type; show planned/not-implemented
  placeholders for throwing, pitching, and fielding.
* Load default swing pose data and phase indexes on page open, clearly labeled as demo
  pose data and not extracted from uploaded video.
* Add concise explanations for visible swing setup parameters and result concepts.
* Overlay available pose keypoints on the replay video with a non-interactive canvas.
* Update `docs/05_manuals/` with user-facing swing motion-analysis UI instructions.

DEV003-03 implementation decisions:

* Keep using `POST /api/v1/analysis/swing` and do not add API fields for overlays; the
  browser overlay draws from the current pose JSON input and latest phase/evidence frames.
* Keep overlay drawing purely visual; no swing score thresholds, fault rules, or coaching
  rules are added to UI code.
* Keep unsupported motion options selectable so users can see planned categories, but
  disable runnable analysis actions for unsupported selections.
* Keep results in memory only and keep threshold overrides internal.

DEV003-03 non-goals:

* Concrete pose estimation from uploaded videos.
* Throwing, pitching, or fielding analysis implementation.
* Bat detection, new computer-vision models, report persistence, hosted services,
  deployment, packaging, version bumps, release notes, or changelog updates.

DEV003-03 acceptance criteria:

* Desktop UI has a one-row three-column review layout.
* The left column contains upload and video library workflows.
* The middle column is headed `Motion Analysis`, includes the motion selector, and holds
  swing setup/results.
* The right column keeps existing replay behavior and adds a non-blocking keypoint
  overlay.
* Swing defaults and parameter explanations are visible.
* Existing upload, library, replay, delete, health, and swing API behavior remains
  unchanged.
* Tests cover layout, selector, defaults, explanations, overlay presence, and regression
  behavior.
* Required quality commands pass and final planning review has no blocking issue.

DEV003-03 final-review-planning result:

* Implementation matches the revised local browser UI scope.
* The browser page now uses a three-column review layout with left media tools, middle
  `Motion Analysis`, and right replay.
* Swing defaults are loaded on page open and labeled as deterministic demo pose data.
* Swing, throwing, pitching, and fielding are visible in the motion selector; only swing
  is runnable.
* Replay overlay drawing uses current pose input or demo pose data and remains
  non-interactive.
* Swing analysis still uses `/api/v1/analysis/swing` and
  `SwingAnalysisApplicationService`; swing rules are not duplicated in UI/API code.
* Product, architecture, development-log, and manual docs are updated.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining risks are non-blocking follow-up work: concrete pose estimation,
  uploaded-video analysis, overlay calibration against real video pose coordinates,
  report persistence, and throwing/pitching/fielding implementations.

DEV003-04 swing evaluation v1 core algorithm update scope:

* Add video-driven swing analysis from a selected stored video.
* Add a pose-estimator interface plus local deterministic heuristic estimator for
  sampled video frames; do not add a heavy production pose dependency in this task.
* Cache detected pose results in memory by media ID and sampling options to avoid
  rerunning pose detection during the same app session.
* Automatically select swing phase/event frames from the detected pose sequence; keep
  manual `phase_frames` only for internal/test overrides, not primary UI.
* Return browser-safe pose overlay data, event frames/windows, analysis, and feedback from
  `/api/v1/analysis/swing/video`.
* Revise the browser layout to put replay video on the top row, upload/library below
  left, and motion analysis below right.
* Add `Clear Analysis` behavior that clears results and overlays without deleting media
  or changing replay selection.

DEV003-04 implementation decisions:

* Honor user open-question answers embedded in the prompt:
  * implement pose estimation now,
  * cache pose results,
  * use a reduced readable label set and omit labels when they become inconsistent.
* Implement local pose estimation with the existing OpenCV/numpy stack and deterministic
  geometry heuristics so CI and local workflows do not need external model downloads.
* Use a conservative analysis sampling cap for responsiveness; tiny test videos can be
  fully sampled.
* Return event frame indexes and simple one-frame windows for overlay/highlighting.
* Keep existing pose-JSON swing analysis endpoint available.

DEV003-04 non-goals:

* Heavy production pose-model dependency, model downloads, cloud pose detection, or
  external video/frame uploads.
* Throwing, pitching, or fielding analysis implementation.
* Report persistence, deployment, packaging, version bumps, release notes, or changelog
  updates.

DEV003-04 acceptance criteria:

* A stored video can be analyzed without pasted pose JSON.
* Video frames are sampled, pose is detected through the pose interface, and pose results
  are converted into `PoseFrame` objects.
* Swing phase/event frames are selected automatically for the main workflow.
* Results include analysis, feedback, confidence, limitations, pose frames, events, and
  overlay data.
* The replay overlay draws detected pose keypoints and a reduced readable label set.
* The UI layout matches the replay-top, upload/library-left, motion-analysis-right
  structure.
* `Clear Analysis` clears analysis results and overlays without deleting media.
* Existing media and pose-JSON analysis behavior remains available.
* Tests and required quality commands pass.

DEV003-04 final review result:

* Planning, architecture, coding, quality-assurance, and final-review-planning stages are
  complete.
* The video-driven swing workflow analyzes stored videos without pasted pose JSON.
* Pose estimation runs through an explicit pose interface and uses in-memory cache reuse.
* Swing event frames are selected automatically for the primary workflow.
* The replay overlay receives pose/event metadata from the application service and can be
  cleared from the UI.
* Documentation and manuals reflect the new workflow and heuristic pose limitations.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* No release or deployment was created.
* Remaining non-blocking risks: heuristic pose quality, automatic event calibration,
  sampled-frame overlay alignment, report persistence, and future throwing/pitching/
  fielding implementations.

DEV003-05 swing evaluation v1 MediaPipe pose estimator scope:

* Replace the default synthetic heuristic estimator in stored-video swing analysis with a
  MediaPipe-based pose estimator for actual player body landmarks.
* Keep `HeuristicPoseEstimator` available for deterministic tests and explicit fallback
  only; it must not be the default user-selected video estimator.
* Use MediaPipe video-mode pose tracking for every sampled frame used by analysis.
* Convert MediaPipe landmarks into the existing internal `PoseFrame` model and preserve
  sampled frame indexes/timestamps.
* Run swing event detection, scoring, feedback, and replay overlay generation from
  MediaPipe-derived poses.
* Do not fake bat tip or barrel keypoints; report missing bat evidence as a limitation.
* Keep video frames local and avoid committing model weights or large video fixtures.

DEV003-05 implementation decisions:

* Adopt MediaPipe as the first real local pose backend for the app.
* Add a configurable MediaPipe Pose Landmarker model path because the installed
  MediaPipe package does not include the `.task` model asset.
* Make missing MediaPipe dependency or missing model asset a structured video-analysis
  error instead of silently falling back to synthetic pose.
* Keep sampled-frame defaults from DEV003-04: target FPS `12.0`, maximum sampled frame
  count `60`.
* Use fake MediaPipe-style result objects in unit tests so tests do not require model
  weights.

DEV003-05 non-goals:

* Bat tip/barrel detection, ball tracking, 3D biomechanics, report persistence,
  throwing/pitching/fielding implementation, release, or deployment.

DEV003-05 acceptance criteria:

* Stored-video swing analysis uses MediaPipe-derived body landmarks when configured.
* Missing MediaPipe dependency or model asset returns a clear structured error.
* Pose tracking processes every sampled frame used by analysis.
* MediaPipe landmarks are converted into `PoseFrame` objects.
* Swing scoring, feedback, events, and replay overlay use those evaluated poses.
* Missing/low-confidence detections and missing bat keypoints are reported as
  limitations.
* Tests and required quality commands pass.

DEV003-05 final review result:

* Planning, architecture, coding, quality-assurance, and final-review-planning stages are
  complete.
* Stored-video swing analysis now defaults to `MediaPipePoseEstimator`, not the
  synthetic heuristic estimator.
* MediaPipe landmarks are mapped to internal `PoseFrame` objects and used for swing event
  selection, scoring, feedback, and overlay generation.
* Missing MediaPipe dependency, missing `.task` model asset, tracking failure, and no
  detectable player pose return structured errors.
* `HeuristicPoseEstimator` remains available for tests and explicit injection only.
* Documentation and manuals describe `BMA_MEDIAPIPE_POSE_MODEL_PATH`, sampled-frame
  analysis, and the absence of bat/ball detection.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* `.venv` equivalents of the same checks also passed.
* No release or deployment was created.
* Remaining non-blocking risks: MediaPipe model asset setup, pose quality under poor
  camera angles/occlusion, automatic event calibration, sampled-frame overlay alignment,
  and future bat/ball detection.

DEV003-06 swing evaluation v1 pose performance improvement plan:

Status: DONE

Planning scope:

* Improve video-driven swing analysis reliability after MediaPipe integration without
  adding release, deployment, throwing, pitching, fielding, bat detection, or external
  uploads.
* Add configurable MediaPipe pose-estimator tuning, pose-quality diagnostics, and
  structured runtime errors.
* Increase swing video frame coverage through configurable quality modes and sampling
  diagnostics.
* Stabilize pose observations with best-player selection, outlier rejection, smoothing,
  and short-gap interpolation before phase detection and scoring.
* Replace normal automatic evenly spread phase selection with motion-aware event
  detection from pose trajectories while keeping provided phase frames for tests and
  expert overrides.
* Improve replay overlay alignment by mapping normalized keypoints into the rendered
  video content rectangle.
* Surface compact pose-quality, sampling, and phase-confidence diagnostics in API and UI
  responses.

Architecture decisions:

* Keep MediaPipe-specific configuration and result conversion inside the `pose` module.
* Keep post-processed pose output as internal `PoseFrame` objects; attach diagnostics
  through `PoseEstimationResult` and video-analysis response models.
* Keep swing sampling decisions in `SwingVideoAnalysisApplicationService`, because the
  service coordinates video metadata, local runtime caps, pose estimation, and analysis
  diagnostics.
* Keep baseball phase/metric rules in `motion` and `analysis`; UI and API adapters only
  choose quality mode, serialize diagnostics, and draw returned overlay data.
* Treat MediaPipe body pose as body-only evidence. Bat/ball-dependent metrics remain
  limited until a separate detector exists.

Acceptance criteria:

* Stored-video swing analysis defaults to higher frame coverage than DEV003-05 and
  returns sampling diagnostics.
* MediaPipe landmark mapping preserves raw normalized coordinates for analysis and
  reports out-of-frame landmarks instead of clamping before evaluation.
* Pose frames are stabilized before swing event detection and analysis.
* Multiple pose candidates select a consistent player when possible.
* Automatic swing events are selected from motion cues rather than evenly spread frames
  in the normal path.
* API and UI expose pose-quality, sampling, and phase-confidence diagnostics without
  filesystem paths.
* Overlay drawing accounts for the rendered video content rectangle and letterboxing.
* Required tests, docs, and quality gates are completed.

Coding result:

* Added configurable MediaPipe pose tuning through `MediaPipePoseEstimatorConfig`,
  `AppSettings`, and `.env.example`.
* Added pose diagnostic flags for smoothed, interpolated, and out-of-frame keypoints.
* Added best-player selection, outlier rejection, short-gap interpolation, smoothing, and
  pose-quality diagnostics.
* Added higher-accuracy, balanced, and faster swing sampling modes with sampling
  diagnostics.
* Replaced normal evenly spread automatic phase selection with motion-aware detection.
* Extended the video swing API response with sampling diagnostics, pose-quality
  diagnostics, phase confidence, and detection methods.
* Added UI quality-mode selection, compact pose-quality display, exact/nearest/
  interpolated overlay status, and content-rectangle overlay mapping.

Quality-assurance result:

* Added or updated unit tests for MediaPipe landmark mapping without clamping, best-player
  selection, stabilization/interpolation/outlier rejection, diagnostics, and motion-aware
  phase detection.
* Added or updated integration tests for video-analysis service diagnostics, API
  diagnostics, sampling metadata, and UI/static exposure.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* Local app startup smoke check passed at `http://127.0.0.1:8765/` with HTTP 200; the
  server was stopped afterward.

Final-review-planning result:

* Planning, architecture, coding, quality-assurance, and final-review-planning stages are
  complete.
* Implementation matches DEV003-06 required outcomes while keeping processing local and
  preserving UI-independent service boundaries.
* Documentation is updated in product, architecture, ADR, motion-knowledge, development
  log, manuals, `.env.example`, and `PLANS.md`.
* No release or deployment was created.
* Remaining non-blocking risks: MediaPipe native failures may occur below Python
  exception handling, phase detection is heuristic until calibrated, bat/ball data is not
  detected, and visual overlay verification with real landscape/portrait media remains a
  manual follow-up when suitable fixtures are available.

DEV003-07 swing evaluation v1 pose parity and stabilization diagnostics plan:

Status: DONE

Planning scope:

* Investigate poor real-frame overlay quality by separating raw MediaPipe detection,
  player-candidate selection, temporal post-processing, sampled-frame alignment, and
  browser overlay mapping diagnostics.
* Add a notebook-parity pose mode for debugging that uses one pose, raw MediaPipe
  normalized coordinates, no smoothing, no interpolation, no outlier rejection, and no
  heuristic fallback.
* Make the default stored-video app path favor ordinary single-player swing clips by
  requesting one pose unless multi-player behavior is explicitly configured.
* Keep all MediaPipe objects and image/video running-mode mapping inside the `pose`
  module.
* Expose raw-vs-stabilized overlay data and compact diagnostics through the existing
  `/api/v1/analysis/swing/video` path and local browser UI.
* Do not add throwing, pitching, fielding, bat detection, report persistence, release,
  deployment, external uploads, model weights, or large video fixtures.

Architecture decisions:

* Treat pose processing mode as an application-service request option that derives a
  `MediaPipePoseEstimatorConfig` for the pose module; UI and API adapters only serialize
  the requested mode.
* Keep raw MediaPipe result mapping and image-mode smoke/parity helpers in `pose` so
  MediaPipe dependencies do not leak into app, API, UI, motion, analysis, or feedback.
* Return stabilized pose as the analysis input, but keep raw pose frames available for
  debug overlay and diagnostics.
* Add explicit post-processing diagnostics so users can tell whether stabilization
  changed landmarks materially.
* Preserve local privacy boundaries: no source file paths, user video frames, model
  assets, generated reports, releases, or deployments are included.

Acceptance criteria:

* Notebook-parity mode disables smoothing, interpolation, outlier rejection, multi-pose
  candidate ambiguity, and heuristic fallback, with diagnostics identifying the mode.
* Default MediaPipe app/settings configuration requests one pose unless multi-person
  behavior is explicitly configured.
* Image-mode and video-mode MediaPipe result mapping can be compared with fake
  MediaPipe-style results in tests.
* First-frame player selection is more robust for clutter or multiple candidates and
  reports selected candidate indexes when available.
* Smoothing does not over-smooth high-velocity wrist/ankle landmarks.
* API responses include running mode, requested pose count, player-selection strategy,
  selected-candidate diagnostics, raw/stabilized diagnostics, and stabilization-delta
  debug fields.
* The browser UI can choose normal vs notebook-parity pose mode, choose stabilized vs
  raw overlay source, and shows frame offset in milliseconds when the overlay frame is
  not exact.
* Tests, docs, required quality gates, and local startup verification are completed.

Coding result:

* Added `MediaPipePoseEstimatorConfig.notebook_parity()` and changed default MediaPipe
  pose count to one.
* Added explicit outlier-rejection enablement plus high-velocity wrist/ankle smoothing
  protection.
* Added image-mode MediaPipe diagnostic execution/result mapping, selected-candidate
  diagnostics, raw diagnostics, and stabilization-delta diagnostics inside the `pose`
  module.
* Extended `SwingVideoAnalysisApplicationService` to cache by pose mode and return raw
  pose frames, raw overlay frames, raw diagnostics, and pose debug diagnostics.
* Extended `/api/v1/analysis/swing/video` request/response schemas with pose mode,
  overlay source, raw pose/overlay, raw diagnostics, and debug diagnostics.
* Added local browser advanced pose debug controls and overlay offset-in-milliseconds
  status text.

Quality-assurance result:

* Added unit tests for notebook-parity config defaults, image/video fake MediaPipe
  mapping parity, first-frame multi-candidate selection, high-velocity wrist smoothing,
  raw diagnostics, and selected-candidate diagnostics.
* Added integration tests for service/API raw pose diagnostics, raw overlay output,
  pose debug diagnostics, notebook-parity request behavior, and browser static debug
  controls/offset copy.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* Local app startup smoke check passed at `http://127.0.0.1:8765/` with HTTP 200; the
  server was stopped afterward.
* Local MediaPipe image-mode diagnostic smoke check on `data/test.png` with
  `models/pose_landmarker_full.task` returned one frame, 19 keypoints, full required
  landmark coverage, mean confidence `0.982`, image running mode, and selected candidate
  index `0`.

Final-review-planning result:

* Planning, architecture, coding, quality-assurance, and final-review-planning stages are
  complete.
* Implementation matches DEV003-07 required outcomes while keeping MediaPipe internals in
  `pose` and keeping UI/API adapters as request/response boundaries.
* Documentation is updated in product, architecture overview, ADR, swing motion
  knowledge, manual, development log, `.env.example`, and `PLANS.md`.
* No release or deployment was created.
* Remaining non-blocking risks: real notebook parity requires the original unannotated
  frame and local MediaPipe model, annotated screenshots can mislead detector behavior,
  MediaPipe still does not detect bat/ball evidence, and phase scoring remains heuristic
  until calibrated real-swing datasets are available.

DEV003-08 swing evaluation v1 UI revision 2 plan:

Status: IN_PROGRESS

Planning scope:

* Rename the visible `Notebook parity` pose-mode UI to `Single pose` while keeping
  backward-compatible internal request behavior.
* Reshape the browser review layout so upload/library sit on the left, replay/video is
  wider on the right, and motion analysis spans the bottom.
* Move limitations and pose-quality diagnostics under a foldable diagnostics area at the
  bottom of `Motion Analysis`.
* Investigate detected-event confidence versus phase-score confidence and make the UI
  labels explicit.
* Do not add scoring rules, pose algorithms, API/service boundary changes unless needed,
  throwing/pitching/fielding, release, or deployment.

Architecture decisions:

* Treat DEV003-08 as a browser UI and documentation revision. No new ADR is needed
  because application-service, pose, motion, analysis, and API boundaries remain stable.
* Keep the internal pose-mode value `notebook_parity` for DEV003-07 compatibility, but
  display it to users as `Single pose`.
* Label event rows as `Event confidence` because they come from motion phase detection.
* Label the phase-score table column as `Score confidence` because it comes from
  scoring evidence confidence.

Acceptance criteria:

* The visible browser UI uses `Single pose`, not `Notebook parity`.
* Pose mode choices are visible as `Normal` and `Single pose`.
* Desktop layout matches upload/library left, wider video right, motion analysis bottom.
* Mobile layout remains stacked and readable.
* Limitations and pose quality are under a foldable diagnostics box at the bottom of
  motion analysis.
* Event confidence and score confidence are clearly distinguished.
* Tests, docs, required quality gates, and startup smoke check are completed.

Coding result:

* Changed the visible pose-mode option to `Single pose` while preserving the internal
  `notebook_parity` request value.
* Revised the desktop grid so upload and library are left, replay is wider on the right,
  and motion analysis spans the bottom; mobile remains stacked.
* Moved limitations and pose quality into a bottom foldable `Diagnostics` section.
* Labeled event rows as `Event confidence` and the phase-score table as
  `Score Confidence` to distinguish motion phase confidence from scoring-evidence
  confidence.

Quality-assurance result:

* Updated UI/static integration coverage for the `Single pose` visible label, preserved
  internal `notebook_parity` request value, revised layout grid areas, foldable
  diagnostics placement, and distinct event/score confidence labels.
* Required quality commands passed:
  * `node --check src/baseball_motion_analysis/ui/web/static/app.js`
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`
* `uv run pytest` passed with 84 tests and one existing Starlette/httpx deprecation
  warning.
* Local app startup smoke check passed at `http://127.0.0.1:8765/` with HTTP 200; the
  server was stopped afterward.

Final-review-planning result:

* Planning, architecture, coding, quality-assurance, and final-review-planning stages are
  complete.
* Implementation matches DEV003-08 required UI outcomes without changing scoring rules
  or service boundaries.
* Documentation is updated in product, architecture overview, manual, development log,
  and `PLANS.md`; no ADR was needed for this UI-only revision.
* No release or deployment was created.
* Remaining non-blocking risk: CSS/static tests cover layout markers, but a manual visual
  pass on representative desktop and mobile viewport sizes is still useful before a
  broader release.

### Milestone 8: Release Preparation

Status: IN_PROGRESS

Goals:

* Stabilize local application-service behavior
* Confirm CI/CD readiness
* Add release checklist
* Update README and CHANGELOG
* Final planning review

Acceptance criteria:

* All tests pass
* GitHub Actions CI is green
* GitHub Actions release-check is green
* Release artifacts build with `uv build`
* Version is consistent across `pyproject.toml`, `CHANGELOG.md`, and the GitHub Release tag
* CHANGELOG.md is updated
* No secrets, user videos, large videos, model files, `.env` files, or generated reports are included
* Documentation is complete for MVP
* Release notes are prepared

## Current Task Board

| ID     | Task                          | Owner Agent           | Status | Notes               |
| ------ | ----------------------------- | --------------------- | ------ | ------------------- |
| T-0001 | Create project scaffold       | planning              | DONE   | Packages, docs, tests, and placeholders created |
| T-0002 | Define architecture overview  | architecture          | DONE   | Original API-first overview superseded by local-PC-first ADR |
| T-0003 | Configure uv project          | coding                | DONE   | `uv sync` passes |
| T-0004 | Configure tests and lint      | quality-assurance     | DONE   | pytest, ruff, format check, and mypy pass |
| T-0005 | Final review of scaffold      | final-review-planning | DONE   | No blocking issues found |
| T-0006 | Prepare initial release notes | release               | TODO   | v0.1.0 planning     |
| T-0007 | Add CI workflow foundation | release | DONE | `.github/workflows/ci.yml` created |
| T-0008 | Add release-check workflow foundation | release | DONE | `.github/workflows/release-check.yml` created |
| T-0009 | Configure Dependabot updates | release | DONE | GitHub Actions and uv updates configured |
| T-0010 | Update release-agent CI/CD responsibilities | release | DONE | `.codex/agents/release.toml` updated |
| T-0025 | Implement dual-mode web video upload and replay UI | final-review-planning | DONE | DEV002-01; supports Milestone 2 and Milestone 7; video-only browser adapter, no motion analysis |
| T-0026 | Add uploaded-video deletion to web media library | final-review-planning | DONE | DEV002-01 update; delete by media ID through app services; no motion analysis |
| T-0011 | Document release CI/CD gates | release | DONE | `AGENTS.md`, `CHANGELOG.md`, and development log updated |
| T-0012 | Add Docker release/deploy workflow | release | TODO | Future task, not in current scope |
| T-0013 | Add production deployment workflow | release | TODO | Future task, not in current scope |
| T-0014 | Reshape project direction to local-PC-first app | planning | DONE | `AGENTS.md`, agent TOMLs, skill, plans, and docs updated |
| T-0015 | Define local media storage architecture | architecture | TODO | Storage directory, metadata index, privacy boundaries |
| T-0016 | Define local UI technology choice | architecture | TODO | Must support upload/import, replay, and reports without hosted service |
| T-0017 | Implement local media import service | coding | TODO | Videos and ordered image sequences |
| T-0018 | Implement local replay manifests | coding | TODO | Uploaded and stored media |
| T-0019 | Plan local media input foundation | planning | DONE | DEV001-01 scope, non-goals, acceptance criteria, and risks documented |
| T-0020 | Design local media input foundation | architecture | DONE | Recorded video, image sequence, camera interface, optional local copy |
| T-0021 | Implement local media input foundation | coding | DONE | Input-layer only; no pose, analysis, upload endpoint, or WebSocket |
| T-0022 | QA local media input foundation | quality-assurance | DONE | 21 tests pass; required quality commands pass |
| T-0023 | Final review local media input foundation | final-review-planning | DONE | Local-PC scope and prompt acceptance criteria verified |
| T-0024 | Strip notebook outputs without Ruff notebook formatting checks | quality-assurance | DONE | CI and release-check strip notebook outputs; Ruff ignores `notebooks/` formatting |
| T-0027 | Add PR, issue, and security templates | quality-assurance | DONE | GitHub community templates added for review, reporting, and vulnerability handling |
| T-0028 | Plan swing evaluation v1 | planning | DONE | DEV003-01 scope, decisions, non-goals, acceptance criteria, and risks documented |
| T-0029 | Design swing evaluation v1 service boundary | architecture | DONE | ADR-0005 added for pose -> motion -> analysis -> feedback -> app boundary |
| T-0030 | Implement swing evaluation v1 | coding | DONE | Pose models, swing metrics, rule scoring, feedback, and app service implemented |
| T-0031 | QA swing evaluation v1 | quality-assurance | DONE | 57 tests pass; ruff, format check, and mypy pass |
| T-0032 | Final review swing evaluation v1 | final-review-planning | DONE | Acceptance criteria verified; release/deployment intentionally skipped |
| T-0033 | Plan swing evaluation v1 UI | planning | DONE | DEV003-02 scope, defaults, non-goals, and acceptance criteria documented |
| T-0034 | Design swing evaluation v1 UI/API adapter | architecture | DONE | `/api/v1/analysis/swing` adapter flow documented in system overview; no new ADR needed |
| T-0035 | Implement swing evaluation v1 UI/API adapter | coding | DONE | Added swing analysis API adapter and local web UI result display |
| T-0036 | QA swing evaluation v1 UI/API adapter | quality-assurance | DONE | 63 tests pass; ruff, format check, and mypy pass |
| T-0037 | Final review swing evaluation v1 UI | final-review-planning | DONE | Acceptance criteria verified; release/deployment intentionally skipped |
| T-0038 | Plan swing evaluation v1 UI revision | planning | DONE | DEV003-03 scope, defaults, selector, overlay, and manual requirements documented |
| T-0039 | Design swing evaluation v1 revised UI | architecture | DONE | Three-column browser UI and overlay data flow documented in system overview |
| T-0040 | Implement swing evaluation v1 UI revision | coding | DONE | Restructured page and added selector/defaults/explanations/overlay |
| T-0041 | QA swing evaluation v1 UI revision | quality-assurance | DONE | 63 tests pass; JS check, ruff, format check, and mypy pass |
| T-0042 | Final review swing evaluation v1 UI revision | final-review-planning | DONE | Acceptance criteria verified; release/deployment intentionally skipped |
| T-0043 | Plan swing evaluation v1 core algorithm update | planning | DONE | DEV003-04 scope, user answers, defaults, and acceptance criteria documented |
| T-0044 | Design video-driven swing analysis and pose cache | architecture | DONE | System overview and ADR-0006 document pose-estimator/cache/video -> analysis flow |
| T-0045 | Implement video-driven swing analysis | coding | DONE | Added pose estimator, app service, API, UI layout/run/clear/overlay updates |
| T-0046 | QA video-driven swing analysis | quality-assurance | DONE | Added tests; JS check and required uv checks pass |
| T-0047 | Final review video-driven swing analysis | final-review-planning | DONE | DEV003-04 acceptance criteria verified; no release/deployment |
| T-0048 | Plan MediaPipe swing pose estimator | planning | DONE | DEV003-05 scope, dependency decision, and acceptance criteria documented |
| T-0049 | Design MediaPipe pose backend boundary | architecture | DONE | ADR-0007 and system overview document MediaPipe backend flow |
| T-0050 | Implement MediaPipe pose estimator | coding | DONE | Added MediaPipe adapter, settings, app-service default, structured errors |
| T-0051 | QA MediaPipe pose estimator | quality-assurance | DONE | Added mapping/service/API/UI tests; required checks pass |
| T-0052 | Final review MediaPipe pose estimator | final-review-planning | DONE | DEV003-05 acceptance criteria verified; no release/deployment |
| T-0053 | Plan pose parity diagnostics | planning | DONE | DEV003-07 scope, acceptance criteria, risks, and non-goals documented |
| T-0054 | Design raw/stabilized pose diagnostics | architecture | DONE | ADR-0008 updated for notebook parity, raw overlay, and one-pose default |
| T-0055 | Implement pose parity diagnostics | coding | DONE | Added parity config, raw/stabilized diagnostics, API/UI debug controls |
| T-0056 | QA pose parity diagnostics | quality-assurance | DONE | 84 tests pass; JS, ruff, format, mypy, pytest, and startup smoke pass |
| T-0057 | Final review pose parity diagnostics | final-review-planning | DONE | DEV003-07 acceptance criteria verified; no release/deployment |
| T-0058 | Plan swing UI revision 2 | planning | DONE | DEV003-08 scope, confidence investigation, acceptance criteria documented |
| T-0059 | Design swing UI revision 2 | architecture | DONE | UI-only layout/label revision; no service boundary change or ADR needed |
| T-0060 | Implement swing UI revision 2 | coding | DONE | Rename single-pose UI, revise layout, fold diagnostics, label confidence |
| T-0061 | QA swing UI revision 2 | quality-assurance | DONE | 84 tests pass; JS, ruff, format, mypy, pytest, and startup smoke pass |
| T-0062 | Final review swing UI revision 2 | final-review-planning | DONE | DEV003-08 acceptance criteria verified; no release/deployment |
| T-0063 | Plan swing v2 metric overlay filter | planning | DONE | DEV004-05 UI update 2 scope and acceptance criteria documented |
| T-0064 | Design swing v2 metric overlay filter | architecture | DONE | UI-only filtering over returned `metric_name`; no service/API contract change |
| T-0065 | Implement swing v2 metric overlay filter | coding | DONE | Added replay-toolbar metric select and browser-side evaluation-line filtering |
| T-0066 | QA swing v2 metric overlay filter | quality-assurance | DONE | Static UI/JS tests updated; JS, ruff, format, mypy, and pytest checks pass |
| T-0067 | Final review swing v2 metric overlay filter | final-review-planning | DONE | Acceptance criteria verified; no release/deployment |
| T-0068 | Plan swing v2 multi-metric overlay filter | planning | DONE | DEV004-06 scope and acceptance criteria documented |
| T-0069 | Design swing v2 multi-metric overlay filter | architecture | DONE | UI-only selected-set filtering and evidence-cell scrolling; no service/API contract change |
| T-0070 | Implement swing v2 multi-metric overlay filter | coding | DONE | Added multi-select metric control and bounded evidence cells |
| T-0071 | QA swing v2 multi-metric overlay filter | quality-assurance | DONE | Static UI/JS tests updated; JS, ruff, format, mypy, and pytest checks pass |
| T-0072 | Final review swing v2 multi-metric overlay filter | final-review-planning | DONE | Acceptance criteria verified; no release/deployment |
| T-0073 | Plan compact swing v2 metric dropdown | planning | DONE | DEV004-07 scope and acceptance criteria documented |
| T-0074 | Design compact swing v2 metric dropdown | architecture | DONE | UI-only checkbox dropdown and bounded table cells; no service/API contract change |
| T-0075 | Implement compact swing v2 metric dropdown | coding | DONE | Added compact metric dropdown menu and narrower evidence column |
| T-0076 | QA compact swing v2 metric dropdown | quality-assurance | DONE | Static UI/JS tests updated; JS, ruff, format, mypy, and pytest checks pass |
| T-0077 | Final review compact swing v2 metric dropdown | final-review-planning | DONE | Acceptance criteria verified; no release/deployment |

## Open Decisions

| ID     | Decision                | Status                    | Owner        | Link                                                        |
| ------ | ----------------------- | ------------------------- | ------------ | ----------------------------------------------------------- |
| D-0001 | Web framework           | Superseded by local-PC-first direction | architecture | docs/02_architecture/adr/ADR-0001-api-first-architecture.md |
| D-0002 | Pose estimation library | TODO                      | architecture |                                                             |
| D-0003 | Local media storage policy | TODO                   | architecture |                                                             |
| D-0004 | Feedback scoring format | Accepted for swing v1     | planning     | docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md |
| D-0005 | Local UI framework      | TODO                      | architecture |                                                             |
| D-0006 | Image-sequence import format | TODO                 | architecture |                                                             |
| D-0007 | Swing UI analysis input | Accepted for DEV003-02    | planning     | Pasted pose JSON plus deterministic demo data; no video-to-pose claim |
| D-0008 | Motion analysis UI layout | Accepted for DEV003-03 | planning | Three-column browser review row with left media, middle analysis, right replay |
| D-0009 | Video-driven swing pose estimator | Accepted for DEV003-04 | architecture | Local deterministic heuristic estimator plus pose-estimator interface; no external model dependency |
| D-0010 | MediaPipe pose estimator backend | Accepted for DEV003-05 | architecture | MediaPipe Pose Landmarker as first real local player-body pose backend |
| D-0011 | Swing pose parity diagnostics | Accepted for DEV003-07 | architecture | Notebook-parity raw landmarks plus stabilized analysis overlay diagnostics |

## Risk Register

| Risk                                                          | Impact | Mitigation                                                              |
| ------------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| Video files contain personal data                             | High   | Keep local by default, avoid committing videos, document privacy policy |
| Image sequences contain personal data                         | High   | Keep local by default, avoid committing images, document privacy policy |
| Pose estimation quality varies by camera angle                | High   | Return confidence notes and limitations                                 |
| Motion feedback may be medically or technically overconfident | High   | Use cautious language and show confidence / uncertainty                 |
| Heavy dependencies may complicate local packaging              | Medium | Add dependencies only after architecture review                         |
| Local filesystem permissions vary by OS                       | Medium | Use configurable storage paths and clear errors                         |
| Future adapters may need API stability                        | Medium | Keep application-service interfaces explicit                            |
| Local media path leakage exposes personal directories          | High   | Keep normal result metadata to source labels or internal references, not absolute paths |
| Codec availability varies across local OpenCV installations   | Medium | Validate OpenCV open/read behavior and report clear errors              |
| Real camera hardware is unavailable in CI                     | Medium | Keep camera tests mocked and interface-only                             |
| Swing phase fallback may select imperfect phase frames         | Medium | Allow caller-provided phase frames and document calibration as follow-up |
| 2D side-view swing rules may miss 3D mechanics                 | Medium | Report confidence and limitations in every feedback result              |
| Swing UI may be mistaken for uploaded-video analysis           | Medium | Label the workflow as pose-data based until concrete pose extraction exists |
| Public threshold overrides may create confusing results        | Medium | Keep v1 UI/API thresholds internal until calibration and settings UX exist |
| Overlay points may be mistaken for detected video pose         | Medium | Label overlay source and demo pose data; do not claim uploaded-video extraction |
| Heuristic pose estimation is not production-quality            | High   | Report limitations, use interface boundary, and keep future model adapter isolated |
| Pose cache may become stale within a session                   | Medium | Key cache by media ID and sampling options; clear when media is deleted or app restarts |

## Definition of Done

A milestone is complete only when:

* Code is implemented
* Tests pass
* Docs are updated
* Risks are reviewed
* Final planning review is complete
