.PHONY: sync test lint format format-check typecheck check run

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src

check: lint format-check typecheck test

run:
	uv run uvicorn baseball_motion_analysis.app.main:app --reload
