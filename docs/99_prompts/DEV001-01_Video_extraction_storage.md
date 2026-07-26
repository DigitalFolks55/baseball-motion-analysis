# DEV001-01: Local Media Input Foundation

## Purpose

This development instruction replaces the earlier upload/API-oriented media input task with a **local PC application** version.

The tool is expected to run on a local machine. Media should be selected from local files or captured from a local camera device. Do not design this task around browser uploads, FastAPI upload endpoints, or WebSocket streaming unless the repository already requires them for an existing local UI shell. If any requirements are not relevent to the project goal, update technical requirements accordingly. Clean up unnessary dependencies and source code files.

## Required Reading

Before starting, read the following files if they exist:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- Existing files under `src/baseball_motion_analysis/`
- Existing tests under `tests/`
- Existing architecture docs under `docs/`

If any required file is missing, report it in the phase output and continue with the best available repository context.

## Task

Design and implement the **local media input foundation** for `baseball_motion_analysis`.

The input layer must support local PC workflows:

1. Load a recorded video file from local disk.
2. Load multiple local image files and convert them into a frame sequence.
3. Define a local camera stream interface for future real-time analysis.

## Goal

Create a flexible, testable input layer that normalizes different local media sources into one stable internal representation.

The output of the input layer must be usable by future pose-estimation, replay, and motion-analysis modules without those modules needing to know whether the source was:

- a recorded video file,
- a local image sequence, or
- a live camera stream.

## Important Direction Change

This task is for a **local PC application**, not a web API feature.

Replace upload/API assumptions with local application contracts:

- Use local file paths instead of uploaded file objects.
- Use local file validation instead of HTTP content-type validation.
- Use local camera device interfaces instead of browser WebSocket streaming.
- Use service methods and optional CLI/app adapters instead of FastAPI endpoints.
- Do not add `python-multipart` for this task.
- Do not implement browser-based WebSocket routes unless an existing local UI architecture already requires them.

## Execution Rules

Execute this task in phases. Use the specified agent for each phase. Do not skip phases.

Keep this task input-layer only. Do not implement pose estimation, swing analysis, pitching analysis, replay UI, or production media storage.

---

# Phase 1: planning agent

## Responsibilities

- Review the local PC application goal.
- Update `PLANS.md` with a task for local media input foundation.
- Define scope, non-goals, acceptance criteria, and risks.
- Confirm that this task is input-layer only.
- Confirm that web upload endpoints and WebSocket browser streaming are out of scope unless already required by the existing app architecture.
- Do not implement production code.

## Planning Scope

Scope must include:

- Local recorded video file input.
- Local multiple-image sequence input.
- Local camera stream interface contract.
- Local filesystem media path handling.
- Optional local media copy/save behavior.
- Frame sampling from recorded video.
- Common frame sequence model shared across input modes.

## Non-goals

Do not implement the following in this task:

- Full pose estimation.
- Full real-time motion analysis.
- Swing, pitching, batting, or fielding classification.
- Production video storage.
- Cloud upload/download.
- User account management.
- Full desktop GUI implementation.
- Browser upload endpoints.
- FastAPI upload endpoints.
- WebSocket streaming from browser camera.
- MediaPipe integration unless already required by existing code.

## Acceptance Criteria

The task is complete when:

- A local video file can be validated, opened, and converted into a `FrameSequence`.
- A local image list can be validated, opened, sorted, and converted into a `FrameSequence`.
- A local camera stream interface exists and can be stubbed or minimally probed without requiring tests to use real hardware.
- Input logic is separated from pose estimation and motion analysis.
- Local file paths are handled safely with clear validation and errors.
- Docs explain the three local input modes and current limitations.
- Unit tests cover validation, metadata extraction, video sampling, image sequence creation, and camera interface behavior where feasible.
- No large media files are committed.

---

# Phase 2: architecture agent

## Responsibilities

- Design the local input-layer architecture.
- Define module boundaries.
- Define common input abstractions.
- Update architecture documentation.
- Do not implement production behavior except minimal interface stubs if needed.

## Architecture Requirements

Keep input logic under:

```text
src/baseball_motion_analysis/video/
```

Suggested file structure:

```text
src/baseball_motion_analysis/
  video/
    __init__.py
    models.py
    validators.py
    video_loader.py
    image_sequence.py
    camera.py
    storage.py
    service.py
```

If the repository already has a different structure, follow the existing structure, but keep responsibilities clear.

## Common Models

Define or reuse stable models similar to:

- `MediaSourceType`
- `VideoMetadata`
- `FrameData`
- `FrameSequence`
- `FrameSamplingOptions`
- `VideoInputSource`
- `ImageSequenceInputSource`
- `CameraInputSource`
- `LocalMediaStorageConfig`

The models should represent:

- source type: `recorded_video`, `image_sequence`, or `camera_stream`
- source identifier
- frame index
- timestamp seconds
- width
- height
- fps or assumed fps
- total frame count when known
- duration seconds when known
- optional warnings
- optional internal media reference

## Design Rules

- Pose estimation must consume `FrameSequence` or an equivalent abstraction, not raw file paths.
- Recorded video parsing must not know about image sequence parsing.
- Local camera stream logic must not be mixed into recorded video parsing.
- UI-specific code must not be placed inside core video input modules.
- Service functions should coordinate validation, loading, sampling, and optional local media copying.
- Local filesystem paths may be accepted as input, but avoid leaking machine-specific absolute paths in public-facing result objects unless explicitly needed for local debug mode.
- Temporary files must use safe temporary directories and be cleaned up.
- Generated test fixtures must be small and created during tests.

## Local Application Contract

Instead of HTTP endpoints, provide local service contracts.

Recommended service methods:

```python
class MediaInputService:
    def load_video_file(
        self,
        path: Path,
        *,
        sampling: FrameSamplingOptions | None = None,
        copy_to_media_root: bool = False,
    ) -> FrameSequence:
        ...

    def load_image_sequence(
        self,
        paths: Sequence[Path],
        *,
        assumed_fps: float | None = None,
        sort_mode: str = "request_order",
        copy_to_media_root: bool = False,
    ) -> FrameSequence:
        ...

    def open_camera_stream(
        self,
        device_index: int = 0,
        *,
        requested_fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> CameraInputSource:
        ...
```

Optional CLI/app adapter commands may be proposed if the repository already has a command-line interface:

```bash
uv run baseball-motion video load --path data/sample.mp4
uv run baseball-motion video images --paths frame001.png frame002.png --assumed-fps 30
uv run baseball-motion camera probe --device-index 0
```

Do not build a full CLI unless the existing project structure already supports one.

## Local Media Storage Policy

Use a configurable local media root.

Recommended default:

```text
<project_root>/video/
```

Requirements:

- Create the media root only when copying/saving media is explicitly requested.
- Preserve original file extensions.
- Use collision-safe names if copying files.
- Do not copy large files during tests.
- Do not commit copied media files.
- Add or update `.gitignore` if needed to exclude local media outputs.

---

# Phase 3: coding agent

## Responsibilities

- Implement the architecture approved in Phase 2.
- Keep implementation small and testable.
- Use type hints.
- Do not change architecture decisions without reporting the reason.
- Prefer small pure functions for validation and metadata extraction.

## Functional Requirements

## 1. Recorded local video file input

Add support for reading a recorded video file from a local path.

Requirements:

- Accept a `pathlib.Path` or path-like object.
- Validate that the file exists.
- Validate file extension.
- Support at least:
  - `.mp4`
  - `.mov`
  - `.avi`
  - `.mkv`
  - `.webm`
- Validate that OpenCV can open the file.
- Extract basic metadata:
  - width
  - height
  - fps
  - total frame count
  - duration seconds
- Add frame sampling:
  - sample every N frames
  - sample by target fps
  - optional max frame count
- Convert frames into a stable internal `FrameSequence`.
- Include frame index and timestamp seconds for each sampled frame.
- Keep video decoding independent from pose estimation.
- If a sample file exists in `data/`, it may be used manually, but automated tests should generate tiny fixture videos instead of depending on committed video files.

## 2. Multiple local image sequence input

Add support for multiple local image files.

Requirements:

- Accept a sequence of local paths.
- Reject an empty sequence.
- Validate that every file exists.
- Validate file extension.
- Support at least:
  - `.jpg`
  - `.jpeg`
  - `.png`
  - `.webp`
- Validate that each image can be read.
- Sort frames by request order by default.
- Allow future sorting by:
  - filename
  - file modified timestamp
  - EXIF timestamp if available later
- Convert images into the same internal `FrameSequence` object used by video input.
- Add metadata:
  - frame count
  - width
  - height
  - source type
  - assumed fps if provided
  - duration seconds if fps is known
- Decide and document behavior for mismatched image dimensions:
  - either reject with a clear validation error, or
  - normalize in a clearly defined future task.
- Keep image loading independent from pose estimation.

## 3. Local camera stream interface

Define a local camera stream interface for future real-time analysis.

Requirements:

- Provide a `CameraInputSource` or equivalent interface.
- Support a default local device index, usually `0`.
- Provide methods similar to:
  - `open()`
  - `read_frame()`
  - `close()`
  - context manager support if practical
- Return `FrameData` or a compatible object from `read_frame()`.
- Add clear TODOs for future real-time pose estimation and motion analysis.
- Keep camera stream logic separate from recorded video parsing.
- Keep implementation minimal if needed.
- Tests must not require real camera hardware. Use mocks for camera behavior.

This phase should not implement full real-time analysis.

## 4. Local application response objects

For local application use, return structured Python objects rather than HTTP responses.

The result for recorded video should contain information similar to:

```python
{
    "source_type": "recorded_video",
    "frame_count": 120,
    "sampled_frame_count": 20,
    "fps": 30.0,
    "duration_seconds": 4.0,
    "width": 1920,
    "height": 1080,
    "frames": [
        {"frame_index": 0, "timestamp_seconds": 0.0},
        {"frame_index": 6, "timestamp_seconds": 0.2},
    ],
    "warnings": [],
}
```

The result for image sequences should contain information similar to:

```python
{
    "source_type": "image_sequence",
    "frame_count": 5,
    "fps": 10.0,
    "duration_seconds": 0.5,
    "width": 1280,
    "height": 720,
    "frames": [
        {"frame_index": 0, "timestamp_seconds": 0.0},
        {"frame_index": 1, "timestamp_seconds": 0.1},
    ],
    "warnings": [],
}
```

These are shape examples. Use typed models or dataclasses/Pydantic models according to the existing repository style.

## Dependency Requirements

- Use `uv`.
- If OpenCV is not already in `pyproject.toml`, add `opencv-python`.
- If NumPy is not already present and needed for frame arrays/tests, add `numpy`.
- If Pillow is already used in the repository, it may be used for image validation; otherwise OpenCV is acceptable.
- Do not add `python-multipart` for this local PC task.
- Do not add FastAPI only for this task.
- Do not add MediaPipe in this task unless strictly necessary.

---

# Phase 4: quality-assurance agent

## Responsibilities

- Add and run tests.
- Verify implementation against the acceptance criteria.
- Check edge cases.
- Run required quality commands.
- Fix QA issues if they are within the test or quality scope.

## Testing Requirements

Add unit tests for:

### File validation

- Existing valid video file extension passes.
- Unsupported video file extension fails.
- Missing video file fails.
- Existing valid image extension passes.
- Unsupported image file extension fails.
- Missing image file fails.
- Empty image sequence fails.

### Video metadata extraction

Use a tiny generated fixture video when possible.

Test:

- width
- height
- fps
- total frame count
- duration seconds
- frame index values
- timestamp values
- `sample_every_n_frames`
- `target_fps`
- `max_frame_count`

### Image sequence creation

Use generated tiny image files.

Test:

- request-order sorting by default
- frame count
- width
- height
- assumed fps
- duration seconds
- frame index values
- timestamp values
- mismatched dimensions behavior

### Camera stream interface

Use mocks only.

Test:

- camera object can be opened through the interface
- `read_frame()` returns a `FrameData`-compatible object when mocked
- `close()` releases resources
- no test requires real camera hardware

### Local media storage

If copy/save behavior is implemented, test:

- media root creation
- copied file naming
- extension preservation
- no absolute machine-specific path leaked in normal result metadata unless explicitly expected

## Required Quality Commands

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If a command cannot run because dependencies or project configuration are missing, report the exact reason and do not hide the failure.

---

# Phase 5: final-review-planning agent

## Responsibilities

- Compare the final implementation with `PLANS.md` and acceptance criteria.
- Confirm that documentation was updated.
- Confirm that tests and quality checks passed.
- Confirm that architecture remains local-application-first.
- Confirm that input logic is independent from pose estimation and motion analysis.
- Confirm that API/upload/WebSocket assumptions were not introduced unless required by existing architecture.
- Confirm that no large media files, copied local media, secrets, or generated artifacts were committed.
- Approve or block the result.

## Final Review Checklist

- [ ] `PLANS.md` includes the local media input foundation task.
- [ ] Architecture docs explain the local input layer.
- [ ] Recorded local video input works.
- [ ] Local image sequence input works.
- [ ] Local camera stream interface exists.
- [ ] Common `FrameSequence` or equivalent model is used.
- [ ] Frame index and timestamp metadata are available.
- [ ] Sampling options are implemented and tested.
- [ ] Tests do not require real camera hardware.
- [ ] No web upload endpoints were added for this task.
- [ ] No browser WebSocket streaming was added for this task.
- [ ] No pose estimation or real-time motion analysis was implemented.
- [ ] No large media files are committed.
- [ ] Required quality commands pass or failures are clearly reported.

---

# Documentation Requirements

Update or create:

- `docs/02_architecture/system_overview.md`
- `docs/01_product/feature_catalog.md` if it exists
- Optional: `docs/02_architecture/adr/ADR-0001-local-media-input-foundation.md`

Documentation must explain:

- The local PC application assumption.
- The three input modes:
  - recorded local video
  - local camera stream
  - local image sequence
- Why all input modes are normalized into one frame sequence abstraction.
- How future pose estimation can consume the same abstraction.
- Current limitations:
  - camera stream is foundation only
  - no full real-time motion analysis yet
  - no production video storage policy yet
  - no full desktop GUI yet
  - no browser upload/API contract in this task

---

# Final Output Required From Codex

At the end, report:

- Changed files
- Which agent handled each phase
- Implemented input modes
- Stubbed or future-work input modes
- Whether local PC application assumptions were preserved
- Test and quality command results
- Remaining risks
- Next recommended task

Use this format:

```text
## Summary

## Changed Files

## Phase Results
- Phase 1 planning agent:
- Phase 2 architecture agent:
- Phase 3 coding agent:
- Phase 4 quality-assurance agent:
- Phase 5 final-review-planning agent:

## Implemented Input Modes

## Stubbed / Future Work

## Test Results

## Remaining Risks

## Next Recommended Task
```
