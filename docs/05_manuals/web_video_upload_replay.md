# Web Video Upload and Replay

## Purpose

The browser UI lets a user upload a local video, browse stored videos, replay a selected video through an HTML5 video player, and remove uploaded videos from the media library.

This is a video-only MVP. Pose estimation, motion classification, swing analysis, pitching analysis, fielding analysis, feedback reports, camera streaming, and image-sequence browser upload are not included.

## Install Dependencies

```bash
uv sync
```

The browser UI uses FastAPI, Jinja2 templates, `python-multipart` upload parsing, SQLite, and local filesystem storage.

## Local Browser Mode

Use local browser mode when the app runs on the same computer as the browser.

```bash
uv run uvicorn baseball_motion_analysis.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Default configuration:

```text
BMA_RUNTIME_MODE=local
BMA_HOST=127.0.0.1
BMA_PORT=8000
BMA_MEDIA_ROOT=./data/media
BMA_DATABASE_PATH=./data/media/library.sqlite3
BMA_MAX_UPLOAD_MB=200
```

Local mode does not require an internet connection after dependencies are installed.

## Server Mode

Server mode uses the same FastAPI app and application services, but media and metadata are stored on the configured server-side filesystem.

Example:

```bash
BMA_RUNTIME_MODE=server \
BMA_HOST=0.0.0.0 \
BMA_PORT=8000 \
BMA_MEDIA_ROOT=/srv/baseball-motion-analysis/media \
BMA_DATABASE_PATH=/srv/baseball-motion-analysis/media/library.sqlite3 \
uv run uvicorn baseball_motion_analysis.app.main:app --host 0.0.0.0 --port 8000
```

Persistent storage depends on the hosting environment. Ephemeral hosts may delete uploaded videos or the SQLite database between restarts.

This MVP does not include authentication or multi-user authorization. Do not expose sensitive videos through an unrestricted public deployment.

## Upload Behavior

The upload endpoint:

- Accepts standard browser multipart uploads.
- Streams uploaded bytes to a controlled staging file.
- Enforces `BMA_MAX_UPLOAD_MB`.
- Rejects empty uploads.
- Calls the application service with the staged local path.
- Reuses existing video validation and OpenCV metadata extraction.
- Generates an internal media ID and internal stored filename.
- Cleans staging files after failed uploads.

The original browser filename is kept only as sanitized display metadata. API responses do not include absolute paths or stored relative paths.

## Delete Behavior

Use the Delete action on a library item to remove one uploaded video.

Deletion:

- Uses the media ID, not a filesystem path.
- Calls the application service.
- Removes the stored video file when it exists.
- Removes the SQLite metadata record.
- Clears the replay panel when the deleted video is currently selected.

A second delete request for the same media ID returns an invalid media ID error because the metadata record has already been removed.

## Replay Behavior

The library lists stored videos with display name, upload time, duration, resolution, FPS, and status.

Selecting Replay loads a manifest with a media-ID-based content URL:

```text
/api/v1/media/videos/{media_id}/content
```

The content endpoint resolves files only through the media ID and supports HTTP byte ranges for browser seeking.

Playback speeds:

- 0.25x
- 0.5x
- 1x
- 1.5x
- 2x

Previous-frame and next-frame controls are approximate. They seek by `1 / fps` when FPS is available. Normal HTML5 video playback does not guarantee frame-exact decoding.

## Browser Format Limits

MP4 and WebM are the most reliable direct browser replay formats when the contained codec is supported by the browser.

MOV, AVI, and MKV files may validate through OpenCV and be stored, but may not replay in every browser. This MVP does not transcode videos, does not add FFmpeg, and does not claim that every validated video can be replayed directly by every browser.

## Privacy

Videos may contain personal information.

Rules for this MVP:

- Uploaded files stay under `BMA_MEDIA_ROOT`.
- The media directory is not mounted as a generic public static directory.
- Videos are served only through media-ID-based endpoints.
- Videos are deleted only through media-ID-based application-service behavior.
- Do not commit uploaded media, local SQLite databases, generated reports, `.env`, credentials, or private test data.
- Do not enable broad cross-origin access without a documented requirement.

## Remove Local Test Media

With default settings, remove local uploaded test media and metadata by deleting:

```text
./data/media/
```

Only delete this directory when you no longer need the uploaded videos or media library metadata.

To remove a single uploaded video, use the Delete action in the browser library instead of manually editing the SQLite database or media directory.

## Manual Verification Checklist

- Open `http://127.0.0.1:8000/`.
- Upload a small MP4.
- Observe selected filename, file size, upload status, and validation result.
- Select the uploaded item from the library.
- Play and pause the video.
- Seek forward and backward.
- Change playback speed.
- Delete the uploaded video and confirm it disappears from the library.
- Reload the browser and confirm the library remains available.
- Upload an invalid file and confirm a clear error appears.
- Check the layout at desktop and narrow browser widths.
- Confirm local mode remains usable without internet access.
