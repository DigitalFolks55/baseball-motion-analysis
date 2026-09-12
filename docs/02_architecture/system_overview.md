# System Overview

## Architecture Direction

`baseball_motion_analysis` is local-PC-first. The current product should run on the user's computer without requiring a hosted web service, while a browser adapter can be used locally or configured for a server runtime.

The architecture remains UI-independent and service-oriented so future web or mobile adapters can share the same analysis services.

```text
local UI or browser UI -> application services -> storage -> video/sequence -> pose -> motion -> analysis -> feedback
```

The local UI and any future API layer should call application services. They should not call low-level video loading, image-sequence loading, pose estimation, storage, or baseball motion rule code directly.

## Module Boundaries

- `ui`: local interface for upload/import, local library browsing, replay, analysis launch, and report viewing.
- `video`: video loading, validation, metadata extraction, replay preparation, and frame sampling.
- `sequence`: ordered image-sequence validation, metadata extraction, replay preparation, and frame sampling.
- `pose`: pose extraction interfaces and implementations.
- `motion`: baseball motion concepts, motion types, and phase models.
- `analysis`: rule evaluation, scoring, issue detection, and confidence handling.
- `feedback`: user-facing explanation and report generation.
- `app`: local application entrypoint and application services.
- `storage`: local media persistence, metadata index, and generated report persistence.
- `api`: HTTP adapter for health and browser media workflows. API routes call application services rather than low-level video or storage modules.
- `core`: shared configuration, errors, and cross-cutting primitives only.

## Required Local Workflows

### Upload or Import

The UI should accept videos and ordered image sequences. Application services should validate input, create storage records, and return a stable media identifier plus metadata.

### Local Media Input Foundation

The input layer lives under `src/baseball_motion_analysis/video/` for the current foundation. It normalizes local input modes into a common frame sequence abstraction:

```text
recorded video file
local image sequence
local camera stream
  -> MediaInputService
  -> FrameSequence / CameraInputSource
```

Supported input modes:

- Recorded local video files are validated by path, extension, and OpenCV readability. Metadata includes width, height, fps, total frame count, and duration when available. Sampling can use every N frames, target fps, and a maximum sampled frame count.
- Local image sequences are validated as existing readable image files, sorted by request order by default, and converted into the same `FrameSequence` model. Filename and modified-time sorting are available for local workflows. EXIF timestamp sorting is reserved for a future task.
- Local camera streams use a minimal `CameraInputSource` interface with `open()`, `read_frame()`, `close()`, and context manager support. This is an interface foundation only; tests should mock camera capture instead of requiring hardware.

Future pose estimation should consume `FrameSequence` or `FrameData` objects and should not inspect raw local file paths directly.

### Local Storage

Uploaded media should stay in a configurable local data directory. The storage layer owns file persistence and metadata indexing. No module should assume that user media can be committed or uploaded externally.

For DEV001-01, storage is intentionally limited to optional local copy behavior for selected video and image files. Production media indexing, replay library management, report persistence, and long-term storage policy remain future work.

For DEV002-01, browser-uploaded videos are streamed to controlled staging files, imported through `VideoLibraryApplicationService`, committed under generated internal filenames, and indexed in SQLite. Public browser responses use media IDs and omit absolute paths and stored relative paths.

Uploaded-video deletion also goes through `VideoLibraryApplicationService`. The UI and API provide a media ID only. The application service coordinates committed-file removal through the file store and metadata removal through the repository. SQL and direct file unlinking stay out of API routes and UI callbacks.

### Replay

Replay should work for both just-uploaded and previously stored media. Application services should provide replay manifests, such as video file references or ordered frame references, without exposing storage internals to motion analysis modules.

For browser video replay, the service returns a manifest:

```text
media id -> display metadata -> media-ID content URL -> browser playback status
```

The content endpoint resolves files only through the media ID and supports HTTP byte ranges for normal browser seeking. Direct browser replay is documented as most reliable for MP4 and WebM, and frame stepping is approximate rather than frame-exact.

### Motion Analysis

Analysis should run after media is validated and stored:

```text
media id
  -> replay or sampling manifest
  -> frames
  -> pose estimation
  -> motion-specific analysis
  -> scoring
  -> feedback report
  -> local report persistence
```

For DEV003-01, swing evaluation is available when a caller already has frame-level pose
observations. The service path is:

```text
pose observations
  -> SwingAnalysisApplicationService
  -> motion swing phases and metrics
  -> analysis scoring and fault detection
  -> feedback report generation
  -> in-memory result
```

This first swing-analysis service does not load media, run a concrete pose model, persist
reports, or integrate with UI callbacks. Swing coaching rules live in `motion`,
`analysis`, and `feedback`, and adapters should call the application service.

For DEV003-02, the local web UI and HTTP adapter expose the DEV003-01 swing service for
already-extracted pose data:

```text
browser swing analysis panel
  -> POST /api/v1/analysis/swing
  -> API JSON validation and pose-model conversion
  -> SwingAnalysisApplicationService
  -> in-memory analysis and feedback JSON
  -> browser result display
```

The API adapter owns request validation, enum/keypoint conversion, browser-safe error
responses, and serialization. It does not contain swing thresholds, fault rules, drill
mapping, or coaching text generation. The browser UI may provide pasted pose JSON and
deterministic demo pose data, but it must not present uploaded videos as automatically
analyzed until a concrete pose-estimation workflow exists.

For DEV003-03, the browser UI is revised into a local review workspace:

```text
left column: upload + video library
middle column: Motion Analysis selector + selected analysis setup/results
right column: replay player + non-interactive keypoint overlay canvas
```

Swing remains the only runnable motion analysis type. Throwing, pitching, and fielding
are visible as planned categories without runnable analysis behavior. Swing defaults are
demo pose data loaded in the browser and labeled as such. The replay overlay draws from
the current pose JSON input and latest phase/evidence frames; it is a UI visualization
only and does not perform pose estimation or motion scoring. Swing analysis still flows
through `/api/v1/analysis/swing` and `SwingAnalysisApplicationService`.

For DEV003-04, swing analysis can run from a selected stored video:

```text
browser Motion Analysis column
  -> POST /api/v1/analysis/swing/video
  -> SwingVideoAnalysisApplicationService
  -> VideoLibraryApplicationService media lookup
  -> MediaInputService frame sampling
  -> pose estimator interface
  -> in-memory pose cache by media ID and sampling options
  -> automatic swing phase/event selection
  -> SwingAnalysisApplicationService
  -> analysis + feedback + pose/event overlay data
  -> browser replay overlay
```

The first local estimator is deterministic and heuristic so the workflow runs without
external model downloads. It is behind the `pose` interface and reports limitations so a
future production pose backend can replace it without moving swing rules into UI, API,
storage, or video modules. Pose caching is in-memory and session-local; it improves repeat
analysis of the same stored video but is not persistent report storage.

For DEV003-05, the selected-video swing workflow replaces the default heuristic estimator
with a MediaPipe body pose backend:

```text
browser Motion Analysis column
  -> POST /api/v1/analysis/swing/video
  -> SwingVideoAnalysisApplicationService
  -> MediaInputService sampled frames
  -> MediaPipePoseEstimator
  -> MediaPipe Pose Landmarker video-mode tracking
  -> PoseFrame sequence from actual player landmarks
  -> automatic swing event selection
  -> SwingAnalysisApplicationService
  -> analysis + feedback + pose/event overlay data
```

MediaPipe remains isolated inside the `pose` module. The default stored-video path must
not silently use synthetic heuristic pose. A configured local MediaPipe `.task` model
asset is required for real player pose detection; missing dependency or model asset is
reported as a structured analysis error. The repository does not commit model weights.

MediaPipe detects player body landmarks only. It does not detect bat tip, bat barrel, or
ball position. Swing analysis must report missing bat evidence as a limitation and use
existing lower-confidence fallback calculations only where supported.

For DEV003-06, the video-driven swing workflow adds pose-performance safeguards before
scoring:

```text
stored video
  -> quality-mode sampling policy
  -> MediaPipe pose candidate selection
  -> raw internal landmark mapping
  -> outlier rejection + short-gap interpolation + smoothing
  -> pose-quality diagnostics
  -> motion-aware swing event detection
  -> scoring, feedback, and replay overlay diagnostics
```

MediaPipe tuning values are configured through `AppSettings` and `BMA_MEDIAPIPE_*`
environment variables rather than hidden in the estimator constructor. The pose module
preserves raw normalized landmark positions for analysis and marks out-of-frame,
smoothed, and interpolated landmarks. Overlay rendering clamps only when drawing into the
rendered video content rectangle.

The swing video endpoint returns sampling diagnostics, pose-quality diagnostics, and
per-phase confidence/detection-method metadata. UI code renders those diagnostics but
does not contain swing thresholds or coaching rules.

DEV007-01 supersedes the stored-video timing parts of DEV003-06 with a timestamp-first
policy:

```text
stored video
  -> video-owned timestamp normalization and full-duration time sampling
  -> pose-owned MediaPipe timestamp input and duration-based stabilization
  -> motion-owned elapsed-time event detection and timing metrics
  -> analysis-owned converted thresholds and scoring
  -> API/UI serialization and rendering of explicit timestamps, units, and diagnostics
```

`frame_index` remains the decoded source-frame identifier. `timestamp_seconds` is the
presentation time used for pose estimation, motion analysis, and replay overlays. The
video layer uses valid monotonic OpenCV timestamps when available, otherwise synthesizes
or repairs timestamps with explicit diagnostics. Stored-video quality modes use stable
target cadences: 30 FPS for higher accuracy, 24 FPS for balanced, and 12 FPS for faster.
Frame-count caps are applied across the full usable clip duration so setup and
follow-through regions both remain eligible.

Pose stabilization windows and interpolation gaps are duration-based. Motion helpers use
body scales per second or degrees per second for movement rates, and
`hip_shoulder_separation_timing` is serialized in milliseconds. API routes and browser
UI render these returned units and diagnostics without calculating timing policy,
thresholds, or baseball rules.

For DEV003-07, the normal app path defaults to one MediaPipe pose for single-player
clips. The app service can derive a notebook-parity pose mode for diagnostics; that mode
requests one pose and disables temporal post-processing so raw MediaPipe landmarks can be
compared with notebook experiments. The pose module also exposes fake-testable
image-mode and video-mode result mapping helpers while keeping MediaPipe task objects out
of API, UI, motion, analysis, and feedback modules.

Video-analysis responses carry stabilized pose frames for scoring plus raw pose frames
for debug overlay. Debug diagnostics include running mode, processing mode, requested
pose count, selection strategy, selected candidate indexes, raw/stabilized quality
diagnostics, and stabilization-delta summaries. The browser computes the current replay
offset to the nearest sampled pose frame and shows the offset in milliseconds when it is
not exact.

DEV003-08 keeps those service/API boundaries unchanged and revises only browser
presentation. The UI displays the diagnostic raw single-pose mode as `Single pose` while
continuing to send the existing internal `notebook_parity` value. The review layout uses
upload/library on the left, a wider replay panel on the right, and motion analysis across
the bottom. Limitations and pose-quality diagnostics are grouped under a foldable
diagnostics area. Event rows label motion phase-detection confidence as `Event
confidence`; the phase-score table labels scoring-evidence confidence as `Score
Confidence`.

DEV004-01 replaces the normal swing scoring methodology while preserving the same local
service and API flow:

```text
pose observations or stored video
  -> existing phase alignment and pose-quality handling
  -> v2 baseline swing metrics
  -> v2 rule evaluation and phase-weighted scoring
  -> v2 feedback
  -> browser-safe response with methodology metadata
```

The v2 evaluator is based on
`docs/80_references/Youth Baseball Swing Baseline Research.pdf`. It reports
`methodology_version: swing_evaluation_v2` and evaluates normalized stance width, torso
forward tilt, torso tilt preservation, grip loading, rear knee sway, head translation,
early connection, lead knee blocking, hip-shoulder separation timing, estimated attack
angle, and follow-through posture/balance. UI and API adapters display returned metric
names, units, scores, and faults, but v2 thresholds, scoring, and drill mapping stay in
`motion`, `analysis`, and `feedback`.

DEV007-02 keeps the same service/API boundaries and makes Detected Faults explicitly
score-relevant:

```text
v2 metric deductions
  -> detected faults with linked metrics and secondary evidence
  -> capped fault-aware phase scoring
  -> API/UI rendering of returned metric and fault score impact
```

The `analysis` module credits linked metric deductions before applying any additional
fault deduction. Fault deductions are capped by phase, severity, and confidence, so a
metric-backed fault is not double-counted as a full independent penalty. Secondary
evidence that is not itself a scored metric, such as wrist-to-chest distance or lead-knee
forward drift, can still lower the relevant phase score when it triggers a supported
fault. API and UI adapters serialize and display returned `metric_deduction`,
`fault_deduction`, fault `deduction`, and `linked_metrics` fields without calculating
baseball scoring rules.

DEV004-02 extends the stored-video swing response with optional evaluation-line overlay
primitives:

```text
v2 analysis result + pose frames
  -> app-owned evaluation overlay line construction
  -> API serialization as browser-safe normalized points
  -> UI toggle and canvas rendering
```

Evaluation-line geometry is generated from v2 metric evidence and pose frames in the
application service. API routes serialize the returned primitives, and browser code only
stores, toggles, and draws them on the same letterbox-aware replay canvas used for pose
overlays. MediaPipe still supplies body landmarks only; bat/ball-specific lines remain
limited to available bat keypoints or lower-confidence grip-path fallback evidence.

DEV004-03 keeps that service/API contract and revises browser presentation. The replay
toolbar separates pose visibility from evaluation-line visibility with independent
`Poses` and `Evaluation Lines` toggles before `Speed`. The UI disables pose keypoint text
tags by default, keeps event labels distinct from evaluation-line labels, and constrains
the local video library to a scrollable list when many uploaded videos exist. The
application service continues to own evaluation-line geometry and now verifies all
required v2 metric line categories when evidence is available.

DEV004-04 corrects swing v2 geometric measurement for non-square sources:

```text
stored video dimensions + normalized pose observations
  -> app service passes frame width/height
  -> motion measurement space converts points for geometry math
  -> analysis scoring uses aspect-aware metric values
  -> app/API/UI keep overlay points normalized for browser rendering
```

The `motion` layer owns the coordinate-space helper and metric calculations. The `app`
layer supplies media dimensions when stored-video metadata is available. The pose-JSON API
accepts optional frame dimensions for callers that have them, while missing dimensions
retain the legacy normalized-coordinate fallback for compatibility.

DEV004-05 UI update 2 keeps the DEV004-02/DEV004-04 service and API contracts unchanged
and revises only browser presentation. The replay toolbar adds a `Metric` dropdown
between `Evaluation Lines` and `Speed`. The browser populates that dropdown from
returned `evaluation_overlay.metric_name` values and filters already-returned normalized
line primitives before frame/event applicability checks. The `Evaluation Lines` toggle
remains the master on/off control, `Poses` remains independent, and no swing thresholds,
deductions, drills, or metric calculations move into the UI.

DEV004-06 UI update 3 keeps the same contract and extends the browser metric filter from
one selected metric to a selected metric set. Empty/default selection means all metrics,
while specific selections are matched against returned `metric_name` values before
frame/event applicability checks. The browser also wraps evidence-heavy metric and fault
content in bounded scrollable cells; this is layout behavior only and does not affect
analysis results.

DEV004-07 UI update 4 keeps that selected-set filtering contract unchanged and revises
only browser presentation. The visible `Metric` control becomes a compact dropdown button
with checkbox options, so it aligns with the `Speed` control while still supporting
multiple selected metrics. The browser narrows the metrics evidence column and uses
bounded table-cell wrappers for unusually large table content.

DEV005-01 adds browser UI localization without changing service or API contracts:

```text
structured analysis/API response
  -> browser localization dictionaries and selected language state
  -> English or Japanese UI labels, status messages, and rendered result text
```

English remains the default language. The browser header exposes an `English / 日本語`
selector and persists the selected language in local storage. Static UI strings use
localization keys, and already-returned swing analysis results are kept in browser state
so changing language re-renders visible feedback, metric labels, events, faults, and
diagnostics without rerunning analysis. Domain logic, analysis rules, storage, video,
pose estimation, application services, and API schemas remain language-independent.

DEV006-01 strengthens video-driven swing pose quality and event alignment while keeping
the same local service boundary:

```text
stored video
  -> quality-mode frame sampling
  -> MediaPipe pose estimation
  -> player candidate switch/ambiguity diagnostics
  -> raw and stabilized pose frames
  -> swing-specific frame-quality classification
  -> active swing window detection
  -> constrained estimated impact selection
  -> v2 scoring and scoring-evidence diagnostics
  -> compact browser diagnostics
```

The `pose` module owns candidate selection, stabilization, and raw/stabilized pose
diagnostics. The `motion` module owns swing-specific frame-quality classification,
active-window detection, and phase selection. The `app` layer returns browser-safe
diagnostics for frame quality, active window, and scoring evidence. API and UI adapters
serialize and render those diagnostics but do not calculate swing thresholds or
pose-quality rules.

DEV006-02 corrects regressions found after DEV006-01:

```text
pose candidates
  -> best-score selection by default
  -> optional candidate-switch holdback only when configured

quality-accepted pose frames
  -> stable pre-motion setup selection
  -> lower-body stride/load selection
  -> lead-foot plant selection from detected setup baseline
  -> constrained estimated body-motion impact without hard late-frame bias
  -> post-impact extension/deceleration follow-through selection
  -> phase confidence and fallback reasons
```

The service/API boundary is preserved. Fallback reasons already owned by the motion
model are serialized through phase/event responses, and the browser displays them as
diagnostic text without calculating baseball rules.

DEV006-03 adds explicit swing event availability semantics:

```text
API request impact_detection_policy
  -> app SwingEventDetectionConfig
  -> motion event status and fallback reason
  -> analysis skips impact-dependent metrics when impact is skipped/unavailable
  -> API/UI event status display
```

The `motion` module owns the `body_pose_estimated`, `skip_without_ball`, and
`require_ball_contact` impact policy behavior. The default remains the current
body-pose estimated impact. No ball/contact detector is introduced; stricter policies
mark impact skipped or unavailable and keep a proxy frame only for ordering/replay
compatibility. The `analysis` module treats skipped or unavailable impact as missing
evidence for impact-dependent metrics and suppresses impact-phase faults that would
otherwise use that proxy as contact evidence.

DEV006-03 also tightens automatic event semantics. Setup biases to the earliest stable
stance, stride requires lower-body onset separation from setup when enough frames exist,
foot strike prefers the first sustained lead-foot plant, and follow-through prefers the
first stable finish/extension plateau instead of unrelated late frames.

DEV006-04 keeps the same service boundary and changes the internal motion event model:

```text
quality-accepted pose frames
  -> setup
  -> lead-leg lift peak or no-stride lower-body-load fallback
  -> lead-foot descent and first stable plant
  -> optional impact policy
  -> bounded follow-through finish
```

The `motion` module owns lead-leg lift scoring, no-stride fallback reasons, foot-strike
dependency on prior lift, and active-window-bounded follow-through selection. The `app`
layer passes known handedness into `SwingEventDetectionConfig` so motion can choose the
lead side when available. API compatibility is preserved through the existing
`impact_detection_policy` string. DEV006-06 restores the normal browser path to always
send `body_pose_estimated` impact and removes the visible `Impact Detection` On/Off
control; it does not contain event rules.

DEV006-05 keeps `SwingPhaseFrames` complete for internal ordering compatibility but
adds an app/API display contract for event windows:

```text
motion phase status
  -> app event visibility / overlay flags
  -> API event display metadata
  -> browser filters normal event rows and replay labels
```

Skipped or unavailable impact can still be inspected through phase status metadata, but
it is not treated as a normal user-visible event or replay overlay marker. The `motion`
module also distinguishes truly contact-dependent metrics from non-contact metrics that
can use fallback anchors when impact is unavailable. Head translation can use
setup-to-foot-strike evidence, and follow-through posture/balance can use
foot-strike-to-finish evidence with lower confidence and explicit limitations. Impact
faults and contact-specific metrics remain suppressed without ball/contact evidence.

DEV006-06 supersedes the DEV006-05 browser product default. The skipped-impact policy
remains accepted for explicit API compatibility, but the browser no longer presents it
as a normal no-ball review option. Estimated impact selection is refined in the motion
domain after foot strike, with candidate scoring that combines wrist/grip motion
transition, contact-zone hand position, lead-side bracing, rotation evidence, and
penalties for early pre-contact or late finish-only frames. Weak body-pose impact
evidence lowers impact event confidence through fallback metadata rather than changing
normal impact status to skipped.

## Current Foundation

The current scaffold exposes `GET /api/v1/health` through an application service. Local media input foundation behavior is available through Python service objects. DEV002-01 adds video-only browser upload, SQLite media library indexing, and HTML5 replay. DEV003-01 adds swing analysis for already-extracted pose/keypoint sequences, including scoring and feedback generation. DEV003-02 exposes that swing analysis through the local browser UI and `/api/v1/analysis/swing` for already-extracted pose JSON and deterministic demo data. DEV003-03 revises the browser workspace into media, motion-analysis, and replay columns and adds a pose-keypoint overlay drawn from the current pose input. DEV003-04 adds video-driven swing analysis through `/api/v1/analysis/swing/video`, sampled-frame pose estimation through a pose-layer interface, automatic event selection, in-memory pose caching, and overlay data for the replay UI. DEV003-05 adopts MediaPipe Pose Landmarker as the first real local player-body pose backend for stored-video swing analysis. DEV003-06 adds quality-mode sampling, pose stabilization, diagnostics, motion-aware event selection, and improved overlay alignment. DEV003-07 adds notebook-parity pose diagnostics, raw-vs-stabilized overlay output, one-pose default configuration, selected-candidate diagnostics, and replay offset copy. DEV003-08 renames that visible debug mode to `Single pose`, revises the browser layout, folds secondary diagnostics, and clarifies event versus score confidence labels. DEV004-01 replaces normal swing scoring with the v2 youth baseline methodology and returns methodology metadata and metric units. DEV004-02 adds optional replay evaluation lines returned by the swing video service and toggled in the replay toolbar. DEV004-03 adds independent pose/evaluation-line overlay toggles, disables pose text tags by default, makes the video library scrollable, and verifies all required evaluation-line categories. DEV004-04 passes source dimensions into swing v2 measurement math for non-square video correctness while preserving normalized overlay primitives. DEV004-05 UI update 2 adds a browser-only metric dropdown that filters returned evaluation lines by `metric_name`; DEV004-06 expands it to multi-select and bounds evidence-heavy cells; DEV004-07 makes the metric chooser compact and narrows evidence-table content; DEV005-01 adds an English/Japanese language selector and browser-side localization for UI/result text. DEV006-01 adds swing frame-quality diagnostics, active swing window detection, constrained estimated impact selection, candidate switch/ambiguity counts, and scoring-evidence diagnostics. DEV006-02 reverts default candidate-switch holdback to original best-score behavior, keeps confirmed high-speed stabilization safeguards, revises event detection around baseball-motion semantics, and serializes event fallback reasons. DEV006-03 adds configurable impact availability policy, event statuses, skipped impact-dependent scoring, and tighter setup/stride/foot-strike/follow-through semantics. DEV006-04 adds lead-leg lift stride selection, foot-strike dependency on prior lift or no-stride fallback, visible browser impact On/Off control, and active-window-bounded follow-through finish selection. DEV006-05 suppresses explicitly skipped impact from normal event display/overlay, restores no-ball fallback evaluation for selected non-contact metrics, and calibrates no-leg-lift stride fallback confidence. DEV006-06 removes the normal browser impact-off control, restores body-pose estimated impact as the browser path, and refines estimated impact after foot strike using contact-zone and bracing cues. DEV007-01 adds timestamp normalization, full-duration time sampling, duration-based pose post-processing, elapsed-time swing motion helpers, millisecond hip/shoulder timing, timestamp diagnostics, and presented-frame replay overlay synchronization. DEV007-02 adds fault-aware swing scoring with linked metric credits and capped fault deductions. It does not perform image-sequence browser upload, camera streaming, report persistence, bat/ball detection, production model packaging, release/deployment, automatic throwing/pitching/fielding analysis, or language-specific scoring.
