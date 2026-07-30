# baseball_motion_analysis

`baseball_motion_analysis` is a local-PC application for analyzing baseball motion from videos and ordered image sequences.

Initial target motions:

* Swing
* Fielding
* Pitching / throwing

The application gives feedback about:

* Good points
* Improvement points
* Suggested drills or next actions
* Confidence and limitations

## Architecture

The project uses a local-PC-first, service-oriented architecture. The first product target runs on the user's computer without a hosted web service.

The core analysis services should remain independent from the UI so future adapters can support:

1. Local desktop UI
2. Web app
3. iPhone app
4. Android app

Main layers:

```text
ui -> app services -> storage -> video/sequence -> pose -> motion -> analysis -> feedback
```

The existing HTTP health scaffold is not the primary product target. New product behavior should go through application services that can be called by the local UI and any future API adapter.

## Setup

```bash
uv sync
```

## Run Local Browser Mode

```bash
uv run uvicorn baseball_motion_analysis.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The browser UI supports video upload, local media library browsing, HTML5 video replay, and uploaded-video removal. Uploads are streamed to a staging file, validated through the application service, stored under the configured media root, and indexed in SQLite. Deleting a video from the library removes the metadata record and removes the stored media file when it exists.

Default runtime configuration:

```text
BMA_RUNTIME_MODE=local
BMA_MEDIA_ROOT=./data/media
BMA_DATABASE_PATH=./data/media/library.sqlite3
BMA_MAX_UPLOAD_MB=200
BMA_HOST=127.0.0.1
BMA_PORT=8000
```

For server mode, set `BMA_RUNTIME_MODE=server`, `BMA_HOST`, `BMA_PORT`, `BMA_MEDIA_ROOT`, and `BMA_DATABASE_PATH` before starting the same FastAPI app. Server mode stores files on the configured server-side filesystem. This MVP does not include authentication or multi-user authorization, so do not expose sensitive videos through an unrestricted public deployment.

## Local Media Input Foundation

The local input service supports:

* Recorded local video validation, metadata extraction, and frame sampling.
* Local image sequence validation and conversion into a common frame sequence.
* A local camera stream interface for future real-time analysis.
* Optional local file copy behavior under a configurable media root.

The DEV001 input foundation is service-level only. DEV002 adds the browser video upload and replay adapter described above. Browser WebSocket streaming, pose estimation, motion scoring, and feedback report generation are still not implemented.

## Browser Video Replay Limits

Direct browser replay is most reliable for MP4 and WebM files when the browser supports the contained codec. MOV, AVI, and MKV files may validate successfully through OpenCV but may not replay in every browser. This MVP does not transcode videos and does not add FFmpeg.

Frame stepping in the browser UI is approximate. It seeks by `1 / fps` when FPS is available, but normal HTML5 video playback does not guarantee frame-exact decoding.

## Local Media Cleanup

Uploaded browser videos and metadata are stored under `BMA_MEDIA_ROOT`. With the default settings, remove local test media and metadata by deleting:

```text
./data/media/
```

Only remove that directory when you no longer need the uploaded videos or local SQLite media index.

To remove one uploaded video, use the Delete action in the browser media library. That action deletes the stored file by media ID and removes its SQLite metadata record.

## Run Tests

```bash
uv run pytest
```

## Lint / Format / Type Check

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Format code:

```bash
uv run ruff format .
```

## Documentation

Documentation is managed as an Obsidian-compatible vault under `docs/`.

Important files:

* `docs/00_index.md`
* `docs/01_product/product_brief.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/`
* `docs/03_development_log/`
* `docs/04_motion_knowledge/`
* `docs/05_manuals/`

## Privacy

Videos may contain personal information.

Do not commit:

* User videos
* User image sequences
* Large video fixtures
* Model weights
* `.env`
* Tokens or credentials
* Generated reports with private content
