# ADR-0008: Swing Pose Quality And Sampling Diagnostics

## Status

Accepted

## Context

DEV003-05 made MediaPipe Pose Landmarker the default body-pose backend for stored-video
swing analysis. Real testing showed that detectable body landmarks are not enough by
themselves: fast swings can be undersampled, multiple people can confuse pose selection,
single-frame landmark jumps can distort scoring, evenly spread phase selection can miss
real events, and browser overlays can be misaligned when the video is letterboxed.

The app must remain local-PC-first and service-oriented. UI and API adapters must not
contain baseball swing thresholds or pose-estimator internals.

## Decision

Add a configurable pose-quality pipeline for video-driven swing analysis:

- Use quality-mode sampling in `SwingVideoAnalysisApplicationService`.
- Default to higher-accuracy swing sampling, with balanced and faster modes available.
- Process every original frame for short clips under a configurable safe cap.
- Keep explicit sampling overrides supported for tests and future expert workflows.
- Configure MediaPipe pose tuning through `AppSettings` and `BMA_MEDIAPIPE_*`
  environment variables.
- Let MediaPipe request multiple pose candidates and select the player by continuity,
  then visible landmark confidence, then body-box size.
- Preserve raw normalized landmark coordinates in `PoseFrame` and mark out-of-frame
  landmarks instead of clamping them before analysis.
- Stabilize pose frames with outlier rejection, short-gap interpolation, and smoothing.
- Return `PoseQualityDiagnostics` and `SwingVideoSamplingDiagnostics` through the
  application service and browser-safe API response.
- Detect automatic swing phases from wrist/grip velocity, ankle movement, and
  hip/shoulder rotation cues instead of using evenly spread frame positions as the normal
  path.
- Map browser overlay keypoints into the rendered video content rectangle, accounting for
  `object-fit: contain` letterboxing.

DEV003-07 extends this decision with a debug parity path:

- Default the app-facing MediaPipe configuration to one pose for ordinary single-player
  swing clips; multi-person candidate selection remains configurable instead of assumed.
- Add a notebook-parity pose mode that preserves raw MediaPipe normalized landmarks and
  disables smoothing, interpolation, and outlier rejection.
- Keep image-mode and video-mode MediaPipe result mapping inside the `pose` module so
  notebooks, API adapters, and UI code do not depend on MediaPipe task objects.
- Return raw and stabilized pose diagnostics separately, plus selected candidate indexes
  and stabilization-delta summaries when available.
- Let the browser choose raw or stabilized overlay data for debugging while swing
  analysis continues to use the stabilized sequence by default.

## Consequences

### Positive

- Fast swing events have better frame coverage by default.
- Poor-quality results can explain sparse sampling, low pose coverage, interpolation,
  rejected outliers, out-of-frame landmarks, and weak phase confidence.
- Multiple-person videos are more likely to track the same hitter across frames.
- Overlay placement is more faithful for landscape, portrait, and letterboxed playback.
- MediaPipe and stabilization details remain inside `pose` and `app` service boundaries.
- Poor overlay quality can be narrowed to raw detection, player selection, temporal
  post-processing, sampling offset, or browser mapping without external uploads.

### Negative

- Higher-accuracy mode increases local CPU time.
- Stabilization can smooth out very sharp motion when the input is noisy.
- Interpolated landmarks are lower-confidence estimates, not detected observations.
- Phase detection remains heuristic until calibrated swing datasets and bat/ball tracking
  are available.
- Notebook-parity mode is a diagnostic mode, not the final coached evaluation path.

## Follow-Ups

- Add calibrated bat tip/barrel and ball detection as a separate motion evidence source.
- Consider persistent pose/result caching if repeated local analysis becomes expensive.
- Add browser-level overlay tests with representative portrait and letterboxed fixtures.
