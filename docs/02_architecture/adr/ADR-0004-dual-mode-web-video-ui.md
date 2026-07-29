# ADR-0004: Dual-Mode Web Video Upload and Replay UI

## Status

Accepted

## Context

ADR-0002 established the local-PC-first service-oriented architecture. ADR-0003 established local path-based media input through `MediaInputService`, including video validation and OpenCV metadata extraction.

DEV002-01 explicitly adds a browser adapter for video upload, media library browsing, and HTML5 replay. This is an adapter for local browser mode and configurable server mode. It does not replace the local-PC-first foundation and does not authorize public multi-user production hosting.

Browser uploads differ from local file-path imports: the app receives multipart bytes from a browser and must write them to a controlled staging file before passing a safe internal `Path` to application services. Public browser responses must not expose absolute filesystem paths or storage internals.

## Decision

Add a dual-mode web video UI using FastAPI, Jinja2 templates, plain JavaScript, plain CSS, SQLite metadata persistence, and configurable local filesystem storage.

The runtime path is:

```text
browser UI
  -> web routes and API adapter
  -> video library application service
  -> media repository and file store
  -> existing media input service
  -> existing video validation and metadata extraction
```

The browser adapter streams uploaded files to a controlled staging location. `VideoLibraryApplicationService` then imports the staged file by calling the existing `MediaInputService`, persists metadata through a repository abstraction, and commits content through a file-store abstraction.

Uploaded-video deletion is also owned by `VideoLibraryApplicationService`. The browser and API provide only a media ID. The application service loads the media record, asks the file store to remove the committed file when it exists, and then asks the repository to delete the metadata record. API routes must not directly unlink files or execute SQL.

Public multi-user production hosting remains outside the current scope. Server mode only means the same FastAPI app can run with server-side filesystem and SQLite paths configured through environment variables.

## Interfaces

Application-service boundary:

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

Storage boundary:

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

The API and UI call these service interfaces. They do not call video validators, OpenCV metadata extraction, SQL, or file-copy helpers directly.

## Runtime Configuration

Configuration is environment-driven:

- `BMA_RUNTIME_MODE=local|server`
- `BMA_MEDIA_ROOT=<path>`
- `BMA_DATABASE_PATH=<path>`
- `BMA_MAX_UPLOAD_MB=<integer>`
- `BMA_HOST=<host>`
- `BMA_PORT=<port>`

Local mode defaults to `127.0.0.1`, stores media under a configurable local media directory, and requires no internet connection.

Server mode reuses the same application services and routes. Files are stored under the configured server-side media directory, and persistence depends on the hosting environment.

## Dependencies

Add `jinja2` because Starlette/FastAPI template rendering requires it for serving a maintainable browser page without a frontend build pipeline.

Alternatives considered:

- Inline HTML strings: avoids a dependency but makes UI maintenance and testing worse.
- React, Vue, or npm build tooling: unnecessary for this MVP and conflicts with local offline simplicity.

Runtime, packaging, license, and deployment considerations:

- `jinja2` is a lightweight Pallets project dependency, widely packaged, and suitable for offline local runtime once installed.
- It adds no hosted-service requirement.

Add `python-multipart` because FastAPI requires it to parse multipart browser uploads.

Alternatives considered:

- Raw request-body upload: possible, but less compatible with standard browser file forms and drag-and-drop `FormData`.
- Custom multipart parser: unnecessary risk.

Runtime, packaging, license, and deployment considerations:

- `python-multipart` is lightweight and only affects upload parsing.
- Upload limits and streaming to disk remain application responsibilities.

## Consequences

### Positive

- Local browser mode becomes usable for upload, library browsing, and replay.
- Server mode can be configured without changing core code.
- Existing video validation and metadata extraction remain centralized in the media input service.
- SQLite keeps the metadata index simple and avoids adding an ORM.
- Media content is served through media IDs instead of a public static media directory.
- Users can remove uploaded videos without manually editing the media directory or SQLite database.

### Negative

- Browser replay support depends on container and codec support; MP4 and WebM are the primary documented browser-oriented formats.
- SQLite write concurrency must be handled carefully in future multi-user scenarios.
- HTTP byte-range behavior becomes part of the replay contract.
- Deletion is destructive for local user media, so the UI must require an explicit user action and show clear status.
- Server deployments without authentication are unsafe for sensitive videos and remain out of scope.

## Non-Goals

- Pose estimation
- Motion classification or analysis
- Feedback reports
- Image-sequence browser upload
- Camera streaming
- Automatic transcoding or FFmpeg integration
- User accounts, authentication, authorization, or multi-tenant behavior
- Cloud object storage, CDN integration, Docker, production deployment, or release publishing
