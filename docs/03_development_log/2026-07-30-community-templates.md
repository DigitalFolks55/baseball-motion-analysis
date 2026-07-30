# 2026-07-30 Community Templates

## Summary

Added GitHub community health templates for pull requests, issues, and security reporting.

## Changes

- Added a focused pull request template with related issue, changes, tests, and privacy/safety sections.
- Added an issue template with type, reproduction, acceptance criteria, privacy, and environment sections.
- Added a security policy that directs vulnerability details away from public issues and documents local media privacy boundaries.
- Updated `PLANS.md` with the completed repository-maintenance task.

## Tests

- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run mypy src` passed.
- `uv run pytest` passed with 41 tests and 1 existing Starlette/httpx deprecation warning.

## Risks

- The security policy points to GitHub private vulnerability reporting when available but does not list a personal contact address.
