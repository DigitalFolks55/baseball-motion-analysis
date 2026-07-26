# 2026-07-26 CI Notebook Format Ignore

## Summary

Updated quality-check configuration so CI still strips Jupyter notebook outputs while Ruff ignores notebook JSON formatting.

## Changes

- Added `notebooks/` to Ruff's extended exclude list.
- Kept notebook output-stripping steps in CI and release-check workflows.
- Made CI Ruff commands explicitly exclude `notebooks/`.
- Avoided making notebook JSON formatting part of Ruff release readiness checks.

## Validation

- Local notebook output-stripping step passed.
- `uv sync` passed.
- `uv run ruff check --exclude notebooks .` passed.
- `uv run ruff format --check --exclude notebooks .` passed.
- `uv run mypy src` passed.
- `uv run pytest` passed with 21 tests and one existing FastAPI/Starlette deprecation warning.
- `uv build` passed.
