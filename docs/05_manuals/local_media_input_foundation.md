# Local Media Input Foundation User Manual

## Purpose

This manual explains the current local media input foundation for `baseball_motion_analysis`.

The implementation is for a local-PC application. Media is selected from local files or a local camera device interface. It does not use browser uploads, FastAPI upload endpoints, or browser WebSocket camera streaming.

## Current Capabilities

The local input foundation supports three input modes:

- Recorded local video files
- Local image sequences
- Local camera stream interface

All decoded frames are normalized into shared Python objects:

- `FrameData`: one decoded frame with frame index, timestamp, width, height, source type, and image array.
- `FrameSequence`: a sequence of `FrameData` objects plus source metadata.

Future pose estimation, replay, and motion analysis should consume `FrameSequence` or `FrameData` instead of reading raw local paths directly.

## What Is Not Included Yet

This implementation does not include:

- Full desktop GUI
- Browser upload endpoint
- FastAPI upload endpoint
- Browser WebSocket camera streaming
- Pose estimation
- Swing, fielding, pitching, or throwing analysis
- Motion scoring
- Feedback report generation
- Replay UI
- Production media storage index

## Supported File Types

Recorded video files:

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`
- `.webm`

Image sequence files:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

The file extension must be supported, and OpenCV must be able to open or read the file.

## Basic Setup

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

## Loading a Recorded Video File

Use `MediaInputService.load_video_file()` with a local `Path`.

```python
from pathlib import Path

from baseball_motion_analysis.video import FrameSamplingOptions, MediaInputService

service = MediaInputService()

sequence = service.load_video_file(
    Path("data/sample.mp4"),
    sampling=FrameSamplingOptions(sample_every_n_frames=5),
)

print(sequence.source_type)
print(sequence.metadata.width, sequence.metadata.height)
print(sequence.metadata.fps)
print(sequence.metadata.total_frame_count)
print(sequence.sampled_frame_count)
print(sequence.frames[0].frame_index)
print(sequence.frames[0].timestamp_seconds)
```

The returned `FrameSequence` contains sampled frames. It does not contain pose-estimation results or baseball motion analysis.

## Video Sampling Options

`FrameSamplingOptions` supports:

- `sample_every_n_frames`: sample every N frames. Default is `1`.
- `target_fps`: sample close to a target frames-per-second rate when source fps is known.
- `max_frame_count`: stop after this many sampled frames.

Example:

```python
from pathlib import Path

from baseball_motion_analysis.video import FrameSamplingOptions, MediaInputService

service = MediaInputService()

sequence = service.load_video_file(
    Path("data/sample.mp4"),
    sampling=FrameSamplingOptions(
        target_fps=5.0,
        max_frame_count=20,
    ),
)
```

If both `sample_every_n_frames` and `target_fps` are provided, the implementation uses the stricter interval so sampling does not exceed the requested target.

## Loading an Image Sequence

Use `MediaInputService.load_image_sequence()` with a list of local image paths.

```python
from pathlib import Path

from baseball_motion_analysis.video import MediaInputService

service = MediaInputService()

sequence = service.load_image_sequence(
    [
        Path("frames/frame001.png"),
        Path("frames/frame002.png"),
        Path("frames/frame003.png"),
    ],
    assumed_fps=30.0,
)

print(sequence.source_type)
print(sequence.metadata.total_frame_count)
print(sequence.metadata.duration_seconds)
print(sequence.frames[0].timestamp_seconds)
```

By default, image frames use the order provided by the caller.

## Image Sequence Sorting

Supported `sort_mode` values:

- `request_order`: keep the caller-provided order. This is the default.
- `filename`: sort by file name.
- `modified_time`: sort by local file modified timestamp.

Example:

```python
from pathlib import Path

from baseball_motion_analysis.video import MediaInputService

service = MediaInputService()

sequence = service.load_image_sequence(
    [
        Path("frames/frame003.png"),
        Path("frames/frame001.png"),
        Path("frames/frame002.png"),
    ],
    assumed_fps=30.0,
    sort_mode="filename",
)
```

EXIF timestamp sorting is not implemented yet.

## Image Dimension Rule

All images in one sequence must have the same width and height.

If dimensions are mismatched, the service rejects the sequence with a clear validation error. Automatic resizing or normalization is reserved for a future task.

## Opening a Local Camera Stream

Use `MediaInputService.open_camera_stream()` to create a local camera stream object.

```python
from baseball_motion_analysis.video import MediaInputService

service = MediaInputService()

camera = service.open_camera_stream(
    device_index=0,
    requested_fps=30.0,
    width=1280,
    height=720,
)

with camera:
    frame = camera.read_frame()
    print(frame.frame_index)
    print(frame.timestamp_seconds)
```

The camera interface is foundation-only. It is designed for future real-time analysis, but real-time pose estimation and motion analysis are not implemented yet.

Automated tests use mocks and do not require real camera hardware.

## Optional Local Copy Behavior

By default, loading a video or image sequence reads from the provided local paths and does not copy files.

Set `copy_to_media_root=True` to copy selected media into a configurable local media root.

```python
from pathlib import Path

from baseball_motion_analysis.video import LocalMediaStorageConfig, MediaInputService

service = MediaInputService(
    LocalMediaStorageConfig(media_root=Path("video"))
)

sequence = service.load_video_file(
    Path("data/sample.mp4"),
    copy_to_media_root=True,
)

print(sequence.internal_media_reference)
```

Copy behavior:

- Creates the media root only when copying is requested.
- Preserves original file extensions.
- Uses collision-safe names.
- Returns an internal media reference instead of exposing an absolute machine-specific path.

The default media root `video/` is ignored by git.

## Validation Errors

The input layer raises `MediaValidationError` when a local file path or media sequence is invalid.

Common validation failures:

- File does not exist.
- Path is not a file.
- Extension is unsupported.
- OpenCV cannot open a video.
- OpenCV cannot read an image.
- Image sequence is empty.
- Image sequence contains mismatched dimensions.

Example:

```python
from pathlib import Path

from baseball_motion_analysis.video import MediaInputService, MediaValidationError

service = MediaInputService()

try:
    service.load_video_file(Path("missing.mp4"))
except MediaValidationError as error:
    print(error)
```

## Privacy Notes

Videos and image sequences may contain personal information.

Follow these rules:

- Keep user media local by default.
- Do not commit videos, image sequences, generated reports, or local media copies.
- Do not log full user file paths if they may include personal names.
- Do not upload media externally unless the user explicitly approves a future workflow.

## Current Limitations

- OpenCV codec support may vary by local machine.
- Camera stream support is interface-level only.
- No production media metadata index exists yet.
- No replay library or local UI exists yet.
- No pose estimation or motion analysis is performed by this input layer.

## Related Documents

- [[01_product/feature_catalog]]
- [[02_architecture/system_overview]]
- [[02_architecture/adr/ADR-0003-local-media-input-foundation]]
- [[03_development_log/2026-07-20-local-media-input-foundation]]
