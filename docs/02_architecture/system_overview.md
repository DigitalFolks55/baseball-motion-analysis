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

## Current Foundation

The current scaffold exposes `GET /api/v1/health` through an application service. Local media input foundation behavior is available through Python service objects. DEV002-01 adds video-only browser upload, SQLite media library indexing, and HTML5 replay. DEV003-01 adds swing analysis for already-extracted pose/keypoint sequences, including scoring and feedback generation. DEV003-02 exposes that swing analysis through the local browser UI and `/api/v1/analysis/swing` for already-extracted pose JSON and deterministic demo data. DEV003-03 revises the browser workspace into media, motion-analysis, and replay columns and adds a pose-keypoint overlay drawn from the current pose input. DEV003-04 adds video-driven swing analysis through `/api/v1/analysis/swing/video`, sampled-frame pose estimation through a pose-layer interface, automatic event selection, in-memory pose caching, and overlay data for the replay UI. DEV003-05 adopts MediaPipe Pose Landmarker as the first real local player-body pose backend for stored-video swing analysis. DEV003-06 adds quality-mode sampling, pose stabilization, diagnostics, motion-aware event selection, and improved overlay alignment. DEV003-07 adds notebook-parity pose diagnostics, raw-vs-stabilized overlay output, one-pose default configuration, selected-candidate diagnostics, and replay offset copy. DEV003-08 renames that visible debug mode to `Single pose`, revises the browser layout, folds secondary diagnostics, and clarifies event versus score confidence labels. It does not perform image-sequence browser upload, camera streaming, report persistence, bat/ball detection, production model packaging, release/deployment, or automatic throwing/pitching/fielding analysis.
