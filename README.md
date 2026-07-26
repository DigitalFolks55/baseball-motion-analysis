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

## Run API Scaffold

```bash
uv run uvicorn baseball_motion_analysis.app.main:app --reload
```

The API scaffold currently exposes health behavior only. Local-PC upload, storage, replay, and analysis workflows are planned but not implemented yet.

## Local Media Input Foundation

The local input service supports:

* Recorded local video validation, metadata extraction, and frame sampling.
* Local image sequence validation and conversion into a common frame sequence.
* A local camera stream interface for future real-time analysis.
* Optional local file copy behavior under a configurable media root.

This foundation is service-level only. It does not include a desktop GUI, browser upload endpoint, browser WebSocket streaming, pose estimation, replay UI, motion scoring, or feedback report generation.

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
