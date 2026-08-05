# 2026-08-03 Swing Video-Driven Core Update

## Summary

Implemented DEV003-04 video-driven swing analysis workflow.

## Changes

- Added a pose estimation interface and deterministic local heuristic estimator.
- Added `SwingVideoAnalysisApplicationService` for stored-video analysis by media ID.
- Added in-memory pose caching keyed by media ID and sampling options.
- Added `/api/v1/analysis/swing/video` for video-driven swing analysis.
- Updated the browser UI so replay is the full-width top row, with upload/library below
  on the left and motion analysis below on the right.
- Removed the primary UI requirement for pasted pose data and manual phase frame indexes.
- Added pose/event overlay rendering from returned analysis metadata.
- Added a `Clear Analysis` action that removes analysis results and overlays without
  deleting media.

## Verification Scope

- Unit coverage for heuristic pose estimation.
- Application-service integration coverage for video analysis and cache reuse.
- API integration coverage for upload-to-analysis workflow, overlay/event response data,
  cache-hit behavior, invalid media IDs, and invalid sampling options.
- UI/static integration coverage for the video-driven workflow and layout markers.

## Limitations

- The current pose estimator is heuristic and is not a production-calibrated pose model.
- Pose is sampled at a capped frame rate/count for local responsiveness.
- Automatic event detection remains conservative and needs calibration against real swing
  fixtures.
- Reports remain in-memory and are not persisted.
