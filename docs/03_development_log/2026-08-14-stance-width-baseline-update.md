# 2026-08-14 Stance Width Baseline Update

## Summary

Updated the swing evaluation v2 normalized stance-width baseline from `1.2`-`1.5`
torso lengths to `1.0`-`1.2` torso lengths.

## Changes

* Changed the default `SwingAnalysisConfig` stance-width target range.
* Adjusted the deterministic good swing fixture so its stance width remains inside the
  updated baseline.
* Added test assertions for the returned stance-width target range and severity.
* Updated motion-knowledge and DEV004-01 prompt documentation to use the new baseline.

## Verification

Required verification passed:

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run mypy src
UV_CACHE_DIR=.uv-cache uv run pytest
```
