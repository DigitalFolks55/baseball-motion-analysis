# ADR-0011: Swing Aspect-Aware Measurement Space

## Status

Accepted

## Context

Swing evaluation v2 uses normalized 2D pose observations from MediaPipe-style landmarks.
Those landmarks store `x` normalized by image width and `y` normalized by image height.
Directly calculating Euclidean distances or angles from those mixed normalized axes is
incorrect for non-square videos.

The issue was visible in metrics such as normalized stance width: the overlay could look
close to one torso length, while the measured ratio was much smaller because horizontal
and vertical units were not in the same coordinate space.

The app must remain local-PC-first and service-oriented. Browser UI and API adapters must
not calculate baseball metrics or scoring rules.

## Decision

Swing v2 geometry uses a motion-layer measurement space:

* When frame width and height are available, normalized pose points are converted to
  same-space image coordinates before distance, displacement, vector-angle, or
  joint-angle calculations.
* Distance-ratio metrics are still normalized by torso length, but both numerator and
  torso scale are measured in the same coordinate space.
* Stored-video swing analysis passes source frame dimensions from media metadata into
  phase detection, metric calculation, scoring, and secondary fault evidence.
* Pose-sequence analysis accepts optional frame dimensions for callers that know the
  source image size.
* Missing dimensions keep the legacy normalized-coordinate fallback for compatibility and
  deterministic synthetic tests.
* Evaluation overlay primitives continue to use normalized points for browser rendering.

## Consequences

### Positive

* Non-square videos produce more faithful stance-width, tilt, drift, angle, and posture
  measurements.
* The `motion` layer owns coordinate conversion and baseball geometry, preserving UI/API
  boundaries.
* Existing browser overlay rendering remains compatible because returned line endpoints
  stay normalized.
* Direct pose-sequence callers can opt into corrected geometry without changing existing
  payloads.

### Negative

* Corrected metrics can change scores and feedback for the same video compared with the
  earlier raw-normalized implementation.
* Pose-sequence callers that omit source dimensions still use a lower-fidelity fallback
  on non-square sources.
* Tests that asserted old raw-normalized values need to assert the corrected
  aspect-aware behavior instead.

## Follow-Ups

* Add calibration fixtures from real side-view youth swings to validate updated metric
  thresholds.
* Consider returning an explicit analysis limitation when pose-sequence requests omit
  dimensions but coordinates appear normalized.
