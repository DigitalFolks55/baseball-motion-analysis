# 2026-08-02 Development Log

## Summary

Implemented DEV003-01 Swing Evaluation v1 as a local-PC-first, service-oriented
foundation for analyzing already-extracted side-view swing pose sequences.

## Changes

* Added stable 2D pose observation models with named keypoints and confidence values.
* Added swing handedness normalization, phase references, geometry helpers, and
  kinematic metric calculations.
* Added swing rule evaluation, fault detection, phase-weighted scoring, confidence
  handling, and limitations.
* Added swing feedback generation with cautious language and drill suggestions.
* Added `SwingAnalysisApplicationService` for application-service orchestration.
* Added ADR-0005 for the swing evaluation service boundary.
* Updated product, architecture, motion-knowledge, and planning docs.

## Tests

* Added unit tests for geometry helpers, handedness normalization, phase handling,
  swing metrics, fault candidates, scoring, feedback, and missing-keypoint behavior.
* Added an integration test for application-service orchestration.
* Verified:
  * `uv run ruff check .`
  * `uv run ruff format --check .`
  * `uv run mypy src`
  * `uv run pytest`

## Risks

* Automatic swing phase detection is a conservative ordered-frame fallback and needs
  future calibration.
* 2D side-view analysis cannot fully represent 3D swing mechanics.
* Attack-angle confidence is reduced when bat tip or barrel keypoints are missing.
* A concrete pose-estimation model and UI-launched analysis remain future tasks.
