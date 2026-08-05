# ADR-0006: Video-Driven Swing Pose Estimation v1

## Status

Accepted

## Context

DEV003-04 moves swing analysis from pasted/demo pose JSON toward a selected-video
workflow. The app must sample stored video frames, create `PoseFrame` observations, detect
swing events automatically, and return overlay data for replay. The user requested pose
estimation now and in-memory caching of pose results.

The repository already uses OpenCV for video validation and frame decoding. Adding a
production pose model would require dependency, model-weight, packaging, runtime, and
license review. Network/model downloads are not acceptable for local privacy-first
defaults.

## Decision

Implement a pose-estimator interface in `pose` and provide a deterministic local
heuristic estimator for DEV003-04.

The heuristic estimator:

* accepts decoded sampled `FrameData`,
* returns existing `PoseFrame` objects,
* produces normalized 2D keypoints and confidence values,
* reports limitations that this is heuristic local pose estimation,
* does not upload frames externally,
* does not require new production dependencies or model weights.

Video-driven swing analysis is orchestrated by an application service:

```text
media ID
  -> media lookup
  -> sampled video frames
  -> pose estimator
  -> in-memory pose cache
  -> automatic swing event selection
  -> swing analysis and feedback
  -> overlay data for browser replay
```

Pose cache entries are in-memory only and keyed by media ID plus sampling options. Cache
entries are not persisted and are safe to discard on app restart.

## Consequences

### Positive

* The app can run the video-driven swing workflow locally without cloud calls.
* UI/API/storage/video modules still do not contain swing coaching rules.
* Tests can use deterministic tiny videos and deterministic pose outputs.
* A future production pose backend can replace the heuristic estimator behind the same
  interface.

### Negative

* The first estimator is not production-quality biomechanics pose estimation.
* Overlay points may be approximate and must be labeled with limitations.
* Bat keypoints are still inferred heuristically unless a future detector/model provides
  them.
* In-memory cache does not survive app restarts.
