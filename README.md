# baseball_motion_analysis

`baseball_motion_analysis` is a web application for analyzing baseball motion from videos.

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

The project uses an API-first architecture so that the analysis backend can support:

1. Web app
2. iPhone app
3. Android app

Main layers:

```text
video -> pose -> motion -> analysis -> feedback -> api
```

## Setup

```bash
uv sync
```

## Run API

```bash
uv run uvicorn baseball_motion_analysis.app.main:app --reload
```

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

## Privacy

Videos may contain personal information.

Do not commit:

* User videos
* Large video fixtures
* Model weights
* `.env`
* Tokens or credentials
* Generated reports with private content
