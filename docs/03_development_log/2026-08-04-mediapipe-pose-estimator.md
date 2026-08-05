# 2026-08-04 MediaPipe Pose Estimator

## Summary

Implemented DEV003-05 MediaPipe pose-estimator requirements for video-driven swing
analysis.

## Changes

- Added a `MediaPipePoseEstimator` behind the existing pose-estimator interface.
- Added MediaPipe landmark mapping into the internal `PoseFrame` model.
- Added configuration for `BMA_MEDIAPIPE_POSE_MODEL_PATH`.
- Changed stored-video swing analysis so the default estimator is MediaPipe, not the
  synthetic heuristic estimator.
- Preserved `HeuristicPoseEstimator` for deterministic tests and explicit injection only.
- Added structured errors for missing MediaPipe dependency, missing model asset, tracking
  failure, and no detectable player pose.
- Preserved pose cache behavior while retaining original pose-estimation limitations.
- Updated UI copy and manuals to describe MediaPipe body-pose tracking.

## Limitations

- The repository does not commit MediaPipe `.task` model files.
- Real analysis requires a local model path configured with `BMA_MEDIAPIPE_POSE_MODEL_PATH`.
- MediaPipe Pose detects body landmarks only. Bat tip, bat barrel, and ball tracking
  remain future work.
- Analysis still runs on sampled frames by default.
