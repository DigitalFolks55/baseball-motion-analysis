# DEV002-01: Dual-Mode Web Video Upload and Replay UI

## Purpose

Design and implement a browser-based video upload, media library, and replay UI for `baseball_motion_analysis`.

The same application must support two runtime modes:

1. Local browser mode
   The FastAPI application runs on the user's computer and is accessed through a browser such as `http://127.0.0.1:8000`.

2. Server mode
   The same FastAPI application can run on a remote server and be accessed through a web browser.

The local-PC-first architecture must remain supported. Do not couple domain logic, video processing, storage policy, or future motion analysis to the web UI.

This task explicitly authorizes browser upload endpoints and a browser UI. This authorization applies only to this task and does not automatically authorize public production deployment, cloud storage, user accounts, or multi-tenant behavior.

---

## Required Reading

Before starting, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `.codex/agents/planning.toml`
* `.codex/agents/architecture.toml`
* `.codex/agents/coding.toml`
* `.codex/agents/quality-assurance.toml`
* `.codex/agents/final-review-planning.toml`
* `docs/01_product/product_brief.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0002-local-pc-first-architecture.md`
* `docs/02_architecture/adr/ADR-0003-local-media-input-foundation.md`
* `docs/99_prompts/DEV001-01_Video_extraction_storage.md`
* Existing code under:

  * `src/baseball_motion_analysis/app/`
  * `src/baseball_motion_analysis/api/`
  * `src/baseball_motion_analysis/video/`
  * `src/baseball_motion_analysis/storage/`
* Existing tests under `tests/`

Report any missing required files, then continue using the available repository context.

---

## Existing Foundation to Reuse

Reuse the existing media-input behavior wherever appropriate.

In particular, inspect and reuse:

* `MediaInputService`
* `VideoInputSource`
* `FrameSequence`
* `FrameSamplingOptions`
* `LocalMediaStorageConfig`
* Existing video validation
* Existing OpenCV metadata extraction
* Existing local media copy behavior

Do not duplicate video validation or metadata extraction inside API routes or UI callbacks.

The browser upload adapter may receive an uploaded file, but it must stream the file to a controlled staging location and then call an application service using a safe internal `Path`.

The UI and API must not call low-level video loader, validator, OpenCV, or filesystem-copy functions directly.

---

## Recommended Technical Direction

Use the existing FastAPI application as the server.

The preferred MVP stack is:

* FastAPI
* Jinja2 templates
* HTML5 `<video>`
* Plain JavaScript or small framework-free JavaScript modules
* Plain CSS
* Python standard-library `sqlite3` for the metadata index, unless the architecture agent documents and approves another lightweight option
* Configurable filesystem storage for uploaded video content

Do not introduce React, Vue, Node.js, npm, a frontend build pipeline, Streamlit, or Gradio unless the architecture agent demonstrates a material project benefit and documents the tradeoff in an ADR.

Do not load JavaScript or CSS libraries from public CDNs. The local application must remain usable without internet access.

Potential new Python dependencies include:

* `jinja2`
* `python-multipart`

Before adding them:

1. Explain why each dependency is required.
2. Explain considered alternatives.
3. Document runtime, packaging, license, and deployment concerns.
4. Add dependencies with `uv add`.
5. Never edit `uv.lock` manually.

---

## Mandatory Agent Workflow

Execute the following phases in order.

Do not skip a phase.

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

This is not a release task.

Do not:

* Create a GitHub Release.
* Create a tag.
* Publish a package.
* Bump the project version solely for this task.
* Deploy the application to a production service.
* Run the `release` agent unless explicitly requested later.

Each agent must provide a concise handoff to the next agent.

---

# Phase 1: planning Agent

## Responsibilities

The planning agent must:

* Update `PLANS.md`.
* Add a clearly identified task for the Web Video Upload and Replay UI.
* Relate the work to:

  * Milestone 2: Local Replay MVP
  * Milestone 7: Local UI MVP
* Define local browser mode and server mode.
* Define scope, non-goals, acceptance criteria, risks, and testing expectations.
* Confirm that pose estimation and motion analysis are not part of this task.
* Confirm that the existing local media input foundation must be reused.
* Confirm that the UI must call application services rather than low-level modules.
* Do not implement production code.

## Planning Risks

At minimum, document these risks:

* Uploaded videos contain personal information.
* Browser playback codec support varies.
* Large uploads can exhaust memory or disk space.
* Temporary upload files may remain after errors.
* Online server files may be ephemeral depending on the hosting environment.
* Public online deployment requires authentication and authorization that are outside this task.
* Concurrent upload behavior may affect a SQLite metadata index.
* Exact frame-by-frame playback cannot be guaranteed by a normal HTML5 video player.
* Browser seeking requires correct byte-range response behavior.

---

# Phase 2: architecture Agent

## Responsibilities

The architecture agent must design the solution before coding.

Create:

`docs/02_architecture/adr/ADR-0004-dual-mode-web-video-ui.md`

Do not delete or rewrite the historical decisions in ADR-0002 or ADR-0003.

ADR-0004 must explain that:

* ADR-0002 remains the foundation for local-PC-first behavior.
* ADR-0003 remains the foundation for local path-based media input.
* DEV002-01 explicitly adds a browser adapter.
* The browser adapter converts uploaded data into a controlled local or server-side staging file.
* Application services remain the boundary between UI/API adapters and the video/storage layers.
* Public multi-user production hosting remains outside the current scope.

## Required Architecture

Use a structure similar to:

```text
browser UI
  -> web routes and API adapter
  -> video library application service
  -> media repository and file store
  -> existing media input service
  -> existing video validation and metadata extraction
```

Recommended modules:

```text
src/baseball_motion_analysis/
  app/
    media_services.py

  api/
    media_router.py
    schemas.py

  ui/
    __init__.py
    web/
      __init__.py
      router.py
      templates/
        index.html
      static/
        app.js
        styles.css

  storage/
    models.py
    repository.py
    sqlite_repository.py
    local_file_store.py

  video/
    replay.py
```

The architecture agent may adjust exact filenames when repository conventions require it, but must preserve the boundaries.

## Required Interfaces

Define an application-service boundary similar to:

```python
class VideoLibraryApplicationService:
    def import_video(self, request: ImportVideoRequest) -> MediaRecord:
        ...

    def list_videos(self) -> tuple[MediaRecord, ...]:
        ...

    def get_video(self, media_id: str) -> MediaRecord:
        ...

    def get_replay_manifest(self, media_id: str) -> VideoReplayManifest:
        ...

    def delete_video(self, media_id: str) -> None:
        ...
```

The exact implementation may be synchronous for the MVP.

Define repository and storage abstractions similar to:

```python
class MediaRepository(Protocol):
    def save(self, record: MediaRecord) -> None:
        ...

    def get(self, media_id: str) -> MediaRecord | None:
        ...

    def list_all(self) -> tuple[MediaRecord, ...]:
        ...

    def delete(self, media_id: str) -> None:
        ...


class MediaFileStore(Protocol):
    def create_staging_file(self, suffix: str) -> Path:
        ...

    def commit_video(self, staging_path: Path, media_id: str) -> Path:
        ...

    def delete_staging_file(self, path: Path) -> None:
        ...

    def delete_committed_file(self, relative_path: Path) -> None:
        ...
```

Do not expose absolute filesystem paths to the browser.

## Runtime Modes

Define configuration for at least:

```text
BMA_RUNTIME_MODE=local|server
BMA_MEDIA_ROOT=<path>
BMA_DATABASE_PATH=<path>
BMA_MAX_UPLOAD_MB=<integer>
BMA_HOST=<host>
BMA_PORT=<port>
```

Expected defaults:

* Local mode:

  * Host defaults to `127.0.0.1`.
  * Files remain under a configurable local media directory.
  * No internet connection is required.

* Server mode:

  * Host and port can be set through environment variables or CLI configuration.
  * The same application services and UI are reused.
  * Files use the configured server-side media directory.
  * Documentation must state that persistent storage depends on the hosting environment.
  * Do not automatically expose the server publicly.

Use `.env.example` for documented configuration. Do not commit `.env`.

---

# Phase 3: coding Agent

## Feature Scope

Implement a video-only UI MVP.

Required:

* Browser page.
* Video file selection.
* Drag-and-drop upload area.
* Upload progress or visible upload status.
* Server-side streaming upload handling.
* Configurable upload-size limit.
* Video validation.
* Video metadata extraction.
* Stable media ID.
* Metadata persistence.
* Video library listing.
* Selection of a stored video.
* HTML5 video replay.
* Seeking.
* Playback-speed selection.
* Uploaded video deletion from the media library.
* Deletion of both the stored video file and its metadata record through application services.
* Clear empty, loading, success, and error states.
* Responsive desktop-first layout.
* Local and server runtime configurations.

Optional when straightforward:

* Approximate previous-frame and next-frame controls using video FPS.
* Keyboard shortcuts.

Do not make optional behavior a blocker for the required MVP.

## UI Design

Create a clean single-page layout.

### Header

Display:

* Product name.
* Short description such as “Baseball Motion Video Review”.
* Runtime mode badge:

  * Local
  * Server
* Privacy indicator explaining where files are stored.

### Upload Panel

Include:

* Drag-and-drop area.
* File picker button.
* Selected filename.
* File size.
* Upload status.
* Validation error area.
* Upload button.
* Clear/reset button.

Do not use the original filename as the internal stored filename.

### Video Library

Display stored videos using cards or rows.

Each item should show:

* Original display name.
* Upload/import time.
* Duration.
* Resolution.
* FPS when available.
* Processing state:

  * importing
  * ready
  * failed
* Replay action.
* Delete/remove action.

The browser must receive a media ID, not an absolute path.

Deleting a stored video must require an explicit user action and must remove both:

* The media metadata record.
* The stored media file when it exists.

The UI must show a clear success or error message after deletion. If the deleted video is currently loaded in the replay panel, the replay panel must be cleared.

### Replay Panel

Display:

* HTML5 video player.
* Video title.
* Duration.
* Current playback time.
* Resolution and FPS.
* Playback-speed selector with:

  * 0.25x
  * 0.5x
  * 1x
  * 1.5x
  * 2x
* Clear unsupported-playback message.
* Loading and playback-error states.

Native video controls may be retained.

When approximate frame stepping is implemented:

* Use `1 / fps` as the seek increment.
* Clearly document that browser frame stepping is approximate.
* Do not claim frame-exact decoding.

### Accessibility

Include:

* Associated labels.
* Keyboard-accessible controls.
* Visible focus states.
* Sufficient text contrast.
* Meaningful status messages.
* Appropriate `aria-live` usage for upload results where practical.

---

## API and Web Contracts

Use same-origin browser requests.

Recommended endpoints:

```text
GET  /
POST /api/v1/media/videos
GET  /api/v1/media/videos
GET  /api/v1/media/videos/{media_id}
GET  /api/v1/media/videos/{media_id}/replay
GET  /api/v1/media/videos/{media_id}/content
DELETE /api/v1/media/videos/{media_id}
```

Endpoint names may be adjusted to existing API conventions.

### Upload Endpoint

The upload endpoint must:

1. Accept multipart upload data.
2. Reject missing files.
3. Enforce a configurable maximum upload size.
4. Generate a controlled staging path.
5. Stream chunks to disk instead of loading the entire video into memory.
6. Clean the staging file after all failed imports.
7. Call the application service with the staging `Path`.
8. Reuse existing video validation and metadata extraction.
9. Store the final video using a generated media ID.
10. Return a typed response schema.
11. Avoid returning or logging private absolute paths.

Do not trust the browser-provided content type as the only validation.

### Replay Manifest

Return a typed manifest similar to:

```json
{
  "media_id": "stable-id",
  "display_name": "pitching-session.mp4",
  "content_url": "/api/v1/media/videos/stable-id/content",
  "duration_seconds": 8.4,
  "width": 1920,
  "height": 1080,
  "fps": 59.94,
  "browser_playback_status": "supported"
}
```

Possible playback statuses:

* `supported`
* `possibly_unsupported`
* `unsupported`
* `missing`

### Video Content Response

The video content endpoint must:

* Resolve content only through the media ID.
* Prevent path traversal.
* Return a suitable media type.
* Support browser seeking.
* Verify byte-range behavior.

Where the framework already supports HTTP range requests correctly, use the framework implementation.

Otherwise, implement and test:

* `Range` request parsing.
* `206 Partial Content`.
* `Content-Range`.
* `Accept-Ranges: bytes`.
* Correct content length.
* Invalid range handling.

Do not read the full video into memory for every request.

### Delete Endpoint

The delete endpoint must:

1. Resolve the target only by media ID.
2. Reject invalid or missing media IDs with a structured error.
3. Call the application service rather than deleting files or metadata directly in the API route.
4. Delete the stored media file when it exists.
5. Delete the metadata record.
6. Be idempotent only for filesystem cleanup after a valid media record is found; a second delete for the same media ID may return invalid media ID.
7. Avoid exposing absolute paths, stored relative paths, stack traces, or SQL errors.
8. Return a typed success response.

---

## Browser Playback Format Policy

The existing input foundation may support video containers that normal browsers cannot replay directly.

For this UI MVP:

* Guarantee direct browser replay only for documented browser-oriented formats such as MP4 and WebM when the contained codec is supported by the browser.
* Do not add automatic FFmpeg transcoding in this task.
* Do not add an FFmpeg dependency.
* Do not claim that every validated `.mov`, `.avi`, or `.mkv` file will replay in every browser.
* Allow the application to return a clear “uploaded but not browser-playable” result where appropriate.
* Document browser and codec limitations in the UI and manuals.

The core media-input service must not be unnecessarily restricted merely because the browser adapter has narrower playback capabilities.

---

## Metadata Persistence

Create a stable media record.

Minimum fields:

```text
media_id
source_type
display_name
stored_relative_path
file_extension
file_size_bytes
created_at
width
height
fps
total_frame_count
duration_seconds
status
error_code
error_message
```

Requirements:

* Store relative internal paths where possible.
* Keep path resolution inside the file-store adapter.
* Use UTC-aware timestamps.
* Do not expose `stored_relative_path` through public API schemas.
* Use a repository abstraction.
* Use SQLite for the initial repository unless architecture review selects another lightweight option.
* Use transactions for record creation and status updates.
* Keep SQL out of UI callbacks and API routes.

Do not add an ORM solely for this task.

---

## Error Handling

Return structured errors for at least:

* Unsupported extension.
* Empty upload.
* File too large.
* Unreadable video.
* Invalid media ID.
* Missing stored file.
* Storage write failure.
* Metadata repository failure.
* Unsupported browser playback.
* Invalid HTTP byte range.

Do not expose stack traces, absolute paths, environment values, or internal SQL errors to the browser.

The UI must display concise user-facing messages.

---

## Security and Privacy

Treat all videos as sensitive user data.

Required:

* Generate internal filenames.
* Preserve the original filename only as sanitized display metadata.
* Prevent `../` and absolute-path injection.
* Store media under the configured media root.
* Do not make the media directory a generic public static directory.
* Serve videos only through media-ID-based endpoints.
* Delete uploaded videos only by media ID through application services.
* Limit upload size.
* Stream uploads to disk.
* Clean failed staging files.
* Do not log full local paths.
* Do not log video contents.
* Do not commit uploaded files.
* Ensure configured media directories remain excluded from git.
* Keep secrets and `.env` out of git.
* Do not enable permissive cross-origin access without a documented requirement.

For server mode, display and document this warning:

> This MVP does not include authentication or multi-user authorization. Do not expose sensitive videos through an unrestricted public deployment.

---

## Application Startup

Keep the current FastAPI application factory.

Mount:

* Web UI routes.
* Static UI assets.
* Existing API router.
* New media API router.

Expected local command should remain simple, for example:

```bash
uv run uvicorn baseball_motion_analysis.app.main:app --reload
```

The root page should be available at:

```text
http://127.0.0.1:8000/
```

Do not add Docker configuration in this task.

Do not add provider-specific deployment configuration.

Document generic server-mode startup using environment configuration.

---

# Phase 4: quality-assurance Agent

## Required Unit Tests

Add tests for:

* Media ID generation.
* Media record serialization.
* Repository save/get/list behavior.
* Relative path handling.
* Filename sanitization.
* Path traversal rejection.
* Upload size-limit logic.
* Staging-file cleanup.
* Replay manifest generation.
* Missing media records.
* Missing stored files.
* Stored media deletion.
* Metadata deletion.
* Deleting a record whose stored file is already missing.
* Browser playback status classification.
* Range-header parsing if custom range handling is implemented.

## Required Integration Tests

Using FastAPI test utilities, test:

* `GET /` returns the Web UI.
* Static JavaScript and CSS are available.
* A tiny valid video fixture can be uploaded.
* Upload returns a stable media ID.
* Uploaded metadata is persisted.
* Uploaded video appears in the library endpoint.
* Replay manifest contains a media-ID-based content URL.
* Video content endpoint returns content.
* Deleting an uploaded video removes it from the library endpoint.
* Deleting an uploaded video removes the stored file.
* Deleting an invalid media ID returns a structured error.
* Valid range request returns `206` when applicable.
* `Content-Range` and `Accept-Ranges` are correct.
* Invalid range request returns an appropriate response.
* Invalid extension is rejected.
* Empty upload is rejected.
* Oversized upload is rejected.
* Unreadable video is rejected.
* Failed upload does not leave a staging file.
* API responses do not contain absolute file paths.
* Existing health endpoint still works.
* Existing media-input tests remain green.

Use tiny generated fixtures.

Do not require:

* Real user videos.
* Internet access.
* External credentials.
* Camera hardware.
* Cloud storage.
* A running production server.

## Manual UI Verification

Document a manual verification checklist covering:

* Open the root page.
* Upload a small MP4.
* Observe validation and progress state.
* Select the uploaded item from the library.
* Play and pause the video.
* Seek forward and backward.
* Change playback speed.
* Delete the uploaded video and confirm it disappears from the library.
* Reload the browser and confirm the library remains available.
* Verify an invalid file shows a clear error.
* Verify the layout at desktop and narrow browser widths.
* Verify local mode remains usable without internet access.

## Required Commands

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

When formatting is required:

```bash
uv run ruff format .
```

Report:

* What was tested.
* What failed.
* What was fixed.
* What remains risky.
* Whether all acceptance criteria pass.

---

# Phase 5: final-review-planning Agent

Perform final alignment review.

Confirm:

* The implementation matches this task.
* `PLANS.md` is updated.
* ADR-0004 exists.
* Product and architecture docs are updated.
* The browser UI calls application services.
* API routes do not contain video-processing logic.
* Existing media-input behavior is reused.
* Local browser mode works.
* Server mode is configurable.
* Uploads are streamed instead of fully buffered.
* File-size limits exist.
* Staging files are cleaned after failure.
* Browser video seeking works.
* Absolute paths are not exposed.
* Public production deployment is not implied to be secure.
* Tests and required checks pass.
* No videos, secrets, generated databases, `.env`, or private reports are committed.

Provide one final status:

```text
READY
```

or:

```text
BLOCKED
```

When blocked, list the blocking issues with file references and recommended corrections.

---

## Documentation Updates

Update at least:

* `PLANS.md`
* `README.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0004-dual-mode-web-video-ui.md`
* `docs/05_manuals/` with local browser usage instructions
* `.env.example`
* `CHANGELOG.md` under an unreleased section when repository conventions require it

Documentation must explain:

* How to install dependencies.
* How to run local browser mode.
* How to configure server mode.
* Where uploaded videos are stored.
* Maximum upload size configuration.
* Supported browser replay formats.
* Codec limitations.
* Privacy limitations.
* Why public deployment without authentication is unsafe.
* How to remove local test media and metadata safely.
* How to remove an uploaded video from the UI.

Use Obsidian-compatible Markdown.

---

## Non-Goals

Do not implement:

* Pose estimation.
* Motion classification.
* Swing analysis.
* Pitching analysis.
* Fielding analysis.
* Feedback reports.
* Video annotations or pose overlays.
* Camera streaming.
* WebSocket video streaming.
* Automatic video transcoding.
* FFmpeg integration.
* User registration.
* Login or authentication.
* Multi-tenant authorization.
* Cloud object storage.
* S3 integration.
* CDN integration.
* Payment behavior.
* Public production deployment.
* Docker deployment.
* Mobile applications.
* React, Vue, or a separate frontend build unless approved by architecture review.
* Release publishing.

---

## Definition of Done

The task is done only when:

* A user can open the application in a browser.
* A user can upload a valid small video.
* The upload is streamed safely to a staging file.
* Existing video validation and metadata extraction are reused.
* The imported video receives a stable media ID.
* Metadata is persisted.
* The video appears in a media library.
* The user can select and replay the video.
* The user can remove an uploaded video.
* Removing a video deletes the metadata record and stored file.
* Browser seeking works through a content endpoint.
* Local browser mode works without internet access.
* Server mode can be configured without changing core code.
* The UI and API call application services.
* No low-level video or storage behavior is embedded in UI callbacks.
* Invalid uploads return understandable errors.
* Failed uploads do not leave temporary files.
* Tests are added and pass.
* Lint, formatting, and typing checks pass.
* Documentation and `PLANS.md` are updated.
* The final-review-planning agent reports `READY`.
