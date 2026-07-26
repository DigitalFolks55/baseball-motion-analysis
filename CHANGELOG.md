# Changelog

All notable changes to `baseball_motion_analysis` will be documented in this file.

## Unreleased

### Added

- GitHub Actions CI workflow for lint, format check, type check, and tests.
- GitHub Actions release-check workflow for release validation and package build artifacts.
- Dependabot configuration for GitHub Actions and uv dependency updates.
- Local-PC-first product and architecture direction for UI upload/import, local storage, replay, motion analysis, scoring, and feedback reports.
- ADR-0002 documenting the local-PC-first service-oriented architecture.
- Local media input foundation for recorded video files, image sequences, and a mocked-testable camera stream interface.
- Optional local media copy behavior with a configurable media root.
- Unit tests for local media validation, metadata extraction, video sampling, image sequence creation, local copy behavior, and camera stream behavior.

### Changed

- Project guidance, skill instructions, agent TOML files, planning docs, and product docs now prioritize a local-PC app instead of a hosted web service.
- ADR-0001 is marked superseded by the local-PC-first architecture decision.
- Removed `python-multipart` because browser upload endpoints are out of scope for the local-PC input foundation.

## 0.1.0

### Added

- Initial repository foundation for an API-first baseball motion analysis application.
