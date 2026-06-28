# 2026-06-24 Release CI Foundation

## Summary

Added the initial CI/CD release foundation for `baseball_motion_analysis`.

## Changes

- Added GitHub Actions CI for lint, format check, type check, and tests.
- Added GitHub Actions release-check workflow for release validation and `uv build`.
- Added Dependabot updates for GitHub Actions and uv dependencies.
- Updated release-agent responsibilities for CI/CD readiness, version consistency, changelog checks, privacy checks, and release blocking rules.
- Documented release and CI/CD policy in `AGENTS.md`.
- Updated `PLANS.md` with release foundation tasks and milestone acceptance criteria.

## Non-Goals

- No Docker deployment workflow.
- No production deployment workflow.
- No PyPI publishing.
