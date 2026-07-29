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

## Current Foundation

The current scaffold exposes `GET /api/v1/health` through an application service. Local media input foundation behavior is available through Python service objects. DEV002-01 adds video-only browser upload, SQLite media library indexing, and HTML5 replay. It does not perform pose estimation, image-sequence browser upload, camera streaming, motion analysis, scoring, or feedback generation.
