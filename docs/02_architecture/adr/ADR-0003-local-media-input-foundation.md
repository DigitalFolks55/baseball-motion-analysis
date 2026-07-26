# ADR-0003: Local Media Input Foundation

## Status

Accepted

## Context

The current product direction is a local-PC application. The first input foundation must accept local recorded videos, local image sequences, and future local camera streams without introducing browser upload endpoints, FastAPI upload handling, or browser WebSocket camera streaming.

Pose estimation, replay, and motion-analysis modules should not need to know whether frames came from a recorded video file, an image sequence, or a camera stream.

## Decision

Implement local media input under `src/baseball_motion_analysis/video/`.

The input layer exposes common models:

- `MediaSourceType`
- `VideoMetadata`
- `FrameData`
- `FrameSequence`
- `FrameSamplingOptions`
- `VideoInputSource`
- `ImageSequenceInputSource`
- `CameraInputSource`
- `LocalMediaStorageConfig`

The application contract is `MediaInputService`, which coordinates validation, loading, frame sampling, image-sequence creation, camera stream construction, and optional local copy behavior.

## Boundaries

- Recorded video parsing stays in `video_loader.py`.
- Image-sequence parsing stays in `image_sequence.py`.
- Camera stream logic stays in `camera.py`.
- File validation stays in `validators.py`.
- Optional local copy behavior stays in `storage.py`.
- Service coordination stays in `service.py`.

No UI-specific code belongs in these modules.

## Local Storage Policy

The default local media root is `video/` relative to the current working directory. The directory is created only when copy behavior is explicitly requested. Copied files preserve extensions and use collision-safe names. Production media indexing and long-term storage policy are future work.

Normal frame sequence metadata should avoid exposing absolute machine-specific paths. Internal media references may use generated local identifiers for application coordination.

## Consequences

### Positive

- Future pose estimation can consume one frame abstraction.
- Tests can generate tiny media fixtures and avoid real user media.
- Local camera support has a clear contract without requiring hardware in tests.
- The architecture remains local-PC-first and independent from browser upload assumptions.

### Negative

- OpenCV codec support may vary by local installation.
- Camera behavior is foundation-only until real-time analysis is designed.
- Production storage indexing remains a separate architecture task.

## Non-Goals

- Full pose estimation
- Swing, pitching, throwing, or fielding classification
- Full real-time motion analysis
- Production media storage
- Full desktop GUI
- Browser upload endpoints
- Browser WebSocket streaming
- MediaPipe integration
