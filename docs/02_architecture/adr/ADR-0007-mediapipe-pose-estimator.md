# ADR-0007: MediaPipe Pose Estimator Backend

## Status

Accepted

## Context

DEV003-04 proved the video-driven swing analysis workflow with a deterministic heuristic
pose estimator. That estimator does not inspect video pixels, so real uploaded videos
produce incorrect overlay positions and unreliable swing scoring.

DEV003-05 requires actual player body pose detection from sampled video frames while
keeping the application local-PC-first and service-oriented.

MediaPipe Pose Landmarker is a good first local backend because it runs on the user's
computer, supports video-mode tracking, returns normalized body landmarks with
confidence/presence values, and is lighter to integrate than research frameworks such as
MMPose.

## Decision

Adopt MediaPipe Pose Landmarker as the first real local body pose backend.

The implementation keeps the existing `PoseEstimator` interface and adds a concrete
`MediaPipePoseEstimator` in the `pose` module. MediaPipe imports, model/task setup,
landmark mapping, and per-frame tracking behavior stay inside the pose module.

Stored-video swing analysis uses:

```text
media ID
  -> VideoLibraryApplicationService media lookup
  -> MediaInputService sampled frames
  -> MediaPipePoseEstimator
  -> PoseFrame sequence
  -> automatic swing event selection
  -> swing scoring and feedback
  -> overlay data
```

The app requires a configured MediaPipe Pose Landmarker `.task` model path for the real
backend. The repository must not commit model weights. Missing MediaPipe dependency or
missing model asset is reported as a structured video-analysis error instead of silently
falling back to synthetic pose for user-selected videos.

The runtime delegate is explicit. CPU is the default because stable local execution is
preferred over faster but more fragile GPU startup. Most missing dependency, missing
model, unsupported runtime, or tracking failures are converted into structured analysis
errors, but native MediaPipe failures may still terminate the process below Python
exception handling.

`HeuristicPoseEstimator` remains available only for tests and explicit fallback injection.

MediaPipe Pose does not detect bat tip or bat barrel. The app must not fake bat keypoints
as detected data. Swing analysis reports missing bat evidence as a limitation and uses
existing lower-confidence wrist/grip fallback behavior where available.

## Consequences

### Positive

* Video overlays and swing analysis can be based on actual player body landmarks.
* Pose-library details remain isolated from UI, API, video, motion, analysis, and
  feedback modules.
* Tests can continue to inject deterministic estimators or fake MediaPipe-style results.
* The app stays local and does not upload frames externally.

### Negative

* Users need a local MediaPipe model asset configured before real video analysis can run.
* MediaPipe body landmarks do not solve bat detection.
* Pose quality still depends on camera angle, player visibility, lighting, and
  occlusion.
* Packaging size and platform compatibility are more complex than the heuristic
  placeholder.
