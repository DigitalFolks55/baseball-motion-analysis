# 2026-08-05 Swing Pose Performance Improvements

## Summary

Implemented DEV003-06 improvements for video-driven swing evaluation after MediaPipe
integration.

## Changes

- Added `MediaPipePoseEstimatorConfig` with configurable pose count, confidence
  thresholds, smoothing, interpolation, outlier rejection, player-selection strategy,
  segmentation mask flag, and runtime delegate.
- Added pose-quality diagnostics for detected frame ratio, required landmark coverage,
  mean/min confidence, smoothed frames, interpolated frames, rejected outliers, and
  out-of-frame landmarks.
- Preserved raw normalized MediaPipe landmark coordinates in internal pose frames and
  marked out-of-frame landmarks instead of clamping before analysis.
- Added best-player selection that prefers track continuity before confidence and body
  size.
- Added stabilization for sampled pose frames before swing phase detection and scoring.
- Added faster, balanced, and higher-accuracy swing sampling modes with sampling
  diagnostics.
- Replaced normal automatic evenly spread phase selection with motion-aware selection
  from wrist/grip velocity, ankle movement, and hip/shoulder rotation cues.
- Extended `/api/v1/analysis/swing/video` responses with pose diagnostics, sampling
  diagnostics, phase confidence, and phase detection methods.
- Added a UI quality-mode control, pose-quality diagnostics section, and overlay mapping
  that accounts for the rendered video content rectangle and letterboxing.

## Validation

- Focused pose, swing motion, app-service, API, and UI tests passed.
- Full quality gates are run after documentation updates.

## Remaining Risks

- MediaPipe native runtime failures below Python exception handling can still terminate
  the process on some platforms.
- Phase detection is motion-aware but still heuristic and not calibrated from real swing
  datasets.
- MediaPipe body pose does not detect bat tip, bat barrel, or ball position.
- Browser overlay behavior needs visual verification with representative landscape and
  portrait clips when fixtures are available.

## DEV003-07 Update

Implemented the second pose-performance pass for poor overlay diagnostics and notebook
parity comparison.

### Changes

- Changed the default MediaPipe pose count to one pose for ordinary single-player swing
  clips while keeping multi-pose behavior configurable.
- Added notebook-parity pose mode with raw single-pose MediaPipe landmarks and no
  outlier rejection, interpolation, or smoothing.
- Added raw pose frames, raw pose diagnostics, selected-candidate diagnostics, and
  raw-vs-stabilized delta summaries to pose/app/API responses.
- Added image-mode and video-mode MediaPipe result mapping helpers that can be compared
  in tests with fake MediaPipe-style results, plus a local image-mode diagnostic utility
  for one decoded frame.
- Improved first-frame player selection for cluttered multi-candidate results by using
  centered, in-frame, plausible body evidence.
- Prevented smoothing from over-smoothing high-velocity wrist and ankle landmarks.
- Added browser advanced pose debug controls for normal/notebook-parity mode and
  stabilized/raw overlay source.
- Added overlay status copy that reports frame offset in milliseconds when the shown
  sampled pose frame is not exact.

### Validation

- Focused pose unit tests and video-analysis service/API/UI integration tests passed.
- Local MediaPipe image-mode diagnostic on `data/test.png` with
  `models/pose_landmarker_full.task` returned one frame, 19 keypoints, full required
  landmark coverage, mean confidence `0.982`, image running mode, and selected candidate
  index `0`.
- Full quality gates are run after documentation updates.

### Remaining Risks

- Real MediaPipe parity against notebooks depends on a local `.task` model and original
  unannotated video frame. Annotated screenshots are useful for visual inspection but are
  not equivalent detector inputs.
- Raw overlay can reveal detector weaknesses but does not add bat, barrel, or ball
  detection.

## DEV003-08 Update

Implemented the second browser UI revision for the video-driven swing analysis screen.

### Changes

- Renamed the visible pose-mode menu option from `Notebook parity` to `Single pose`
  while keeping the internal `notebook_parity` request value for DEV003-07 compatibility.
- Revised the desktop layout to keep upload and video library on the left, make replay
  wider on the right, and place motion analysis across the bottom.
- Moved limitations and pose-quality details into a closed-by-default foldable
  diagnostics section at the bottom of motion analysis.
- Clarified confidence labels: detected-event rows now show `Event confidence` from
  motion phase detection, while the phase-score table shows `Score Confidence` from
  scoring evidence.

### Validation

- Updated UI/static regression tests for the label change, layout markers, diagnostics
  fold, request value, and confidence labels.
- Full quality gates are run after documentation updates.

### Remaining Risks

- The layout remains HTML/CSS-tested; visual review with representative viewport sizes is
  still useful before a broader release.
