# Swing Motion Analysis UI

## Purpose

The Motion Analysis panel lets a local user run swing evaluation from a selected stored
video and view feedback with pose/event overlays on the replay video.

The current workflow is local and in-memory. It does not upload media to an external
service and does not persist analysis reports yet.

Swing results use `swing_evaluation_v2`, the current youth baseball 2D side-view
baseline methodology.

## Page Layout

On desktop, the page is organized as:

```text
| Upload Video  | Replay video    |
| Video Library | Replay video    |
|        Motion Analysis          |
```

On narrow screens the page stacks in this order:

1. Upload Video
2. Video Library
3. Replay
4. Motion Analysis

## Upload And Replay A Video

1. In `Upload Video`, choose or drop a video file.
2. Select `Upload`.
3. In `Video Library`, select `Replay` for the stored video.
4. Use replay controls to play, pause, change speed, or step approximately one frame at a
   time when FPS is available.
5. After swing analysis returns overlay data, use `Poses` to show or hide pose points
   and skeleton lines, use `Evaluation Lines` to show or hide v2 metric guide lines, and
   use `Metric` to show all returned evaluation lines or selected metric groups on the
   replay canvas.

Uploaded videos are stored locally under the configured media root and are served through
media-ID-based URLs. Browser replay is most reliable with MP4 and WebM.

The `Video Library` list scrolls when many videos are available so upload, replay, and
analysis controls remain reachable.

## Select Motion Type

In `Motion Analysis`, use the motion selector:

- `Swing`: runnable in the current implementation.
- `Throwing`: planned, not runnable yet.
- `Pitching`: planned, not runnable yet.
- `Fielding`: planned, not runnable yet.

When a planned motion type is selected, the UI shows that it is not implemented and does
not run an unsupported analysis endpoint.

## Swing Parameters

### Selected Video

The selected video is the stored video currently loaded in the replay panel. `Run Swing
Analysis` stays disabled until a stored video is selected.

### Handedness

Choose:

- `Right-handed`: the left side is treated as the lead side.
- `Left-handed`: the right side is treated as the lead side.
- `Unknown`: the analysis uses a default side interpretation and lowers confidence.

### Pose

Pose is detected locally from sampled video frames through the pose application boundary
using MediaPipe body landmarks. The app requests one MediaPipe pose by default for
ordinary single-player swing clips. If `BMA_MEDIAPIPE_NUM_POSES` is raised for crowded
clips, the pose module selects the likely hitter by continuity from the previous frame,
then landmark confidence, visible body size, center preference, and in-frame evidence.

Real video analysis requires a local MediaPipe Pose Landmarker `.task` model path:

```text
BMA_MEDIAPIPE_POSE_MODEL_PATH=/path/to/pose_landmarker.task
```

The model file is a local asset and should not be committed to the repository.

MediaPipe tuning can be configured with:

```text
BMA_MEDIAPIPE_NUM_POSES=1
BMA_MEDIAPIPE_MIN_POSE_DETECTION_CONFIDENCE=0.5
BMA_MEDIAPIPE_MIN_POSE_PRESENCE_CONFIDENCE=0.5
BMA_MEDIAPIPE_MIN_TRACKING_CONFIDENCE=0.5
BMA_MEDIAPIPE_MIN_LANDMARK_CONFIDENCE=0.3
BMA_MEDIAPIPE_SMOOTHING_WINDOW=3
BMA_MEDIAPIPE_MAX_INTERPOLATION_GAP_FRAMES=2
BMA_MEDIAPIPE_OUTLIER_REJECTION_ENABLED=true
BMA_MEDIAPIPE_OUTLIER_DISTANCE_RATIO=0.75
BMA_MEDIAPIPE_HIGH_VELOCITY_SMOOTHING_LIMIT_RATIO=0.8
BMA_MEDIAPIPE_STABILIZATION_DELTA_WARNING_RATIO=0.35
BMA_MEDIAPIPE_PLAYER_SELECTION_STRATEGY=continuity_confidence_size
BMA_MEDIAPIPE_ENABLE_SEGMENTATION_MASK=false
BMA_MEDIAPIPE_RUNTIME_DELEGATE=cpu
```

CPU is the default runtime delegate because stable local execution is preferred over
faster but more fragile GPU initialization.

### Quality Mode

Choose a swing analysis quality mode:

- `Higher accuracy`: samples more frames and can process every original frame for short
  clips under the configured cap.
- `Balanced`: uses fewer frames than higher accuracy while still preserving more motion
  events than faster mode.
- `Faster`: reduces local runtime but can miss foot strike, estimated impact, or quick
  hand movement.

### Advanced Pose Debug

The advanced pose debug controls are for diagnosis when app overlay quality differs from
raw single-frame detector results:

- `Pose Mode: Normal`: uses the normal MediaPipe video-mode path and temporal
  stabilization.
- `Pose Mode: Single pose`: requests one pose and disables smoothing, interpolation,
  and outlier rejection so the returned landmarks stay close to raw MediaPipe output.
- `Overlay Source: Stabilized`: draws the landmarks used by swing analysis.
- `Overlay Source: Raw`: draws the raw detector landmarks returned before stabilization.

Single pose mode is not the final coaching path. It helps identify whether a poor
overlay comes from raw detection, candidate selection, temporal post-processing, sampled
frame alignment, or browser drawing.

### Events

Setup, stride, foot strike, impact, and follow-through are selected automatically from
the ordered pose sequence. The user does not enter phase frame indexes in the UI. Impact
is an estimated impact window from body-pose motion cues; exact ball contact is not
claimed unless future bat or ball detection supplies that evidence.

## Run Analysis

Select `Run Swing Analysis`.

The browser sends the selected media ID and handedness to the local API adapter:

```text
POST /api/v1/analysis/swing/video
```

The application service:

- Resolves the stored video by media ID.
- Samples video frames with higher-accuracy defaults: full-frame processing for short
  clips under the safe cap, otherwise a higher target FPS with a configurable cap.
- Tracks MediaPipe body pose for every sampled frame.
- Stabilizes pose observations with outlier rejection, short-gap interpolation, and
  smoothing.
- Reuses in-memory cached pose results for repeated runs with the same media ID and
  sampling options.
- Automatically selects swing event frames from wrist/grip velocity, foot movement, and
  hip/shoulder rotation cues.
- Runs the existing swing scoring and feedback service.
- Runs the v2 baseline swing scoring and feedback service.
- Supplies the stored video width and height to v2 swing scoring so geometric metrics
  are measured in aspect-aware image coordinates before torso-length normalization.
- Builds optional evaluation-line primitives from v2 metric evidence and pose frames.
- Returns methodology metadata, stabilized and raw pose overlay frames, event metadata,
  evaluation lines, sampling diagnostics, raw/stabilized pose-quality diagnostics, debug
  diagnostics, scores, feedback, confidence, and limitations.

## Clear Analysis

Select `Clear Analysis` to remove current results and overlays from the page. This does
not delete the uploaded video or remove it from the video library.

## Read Results

Results appear in the `Motion Analysis` panel.

- `Overall`: total score out of 100.
- `Methodology`: the returned swing evaluation methodology, currently
  `swing_evaluation_v2`.
- `Confidence`: how reliable the result is based on keypoint quality, handedness
  certainty, and event detection certainty.
- `Good Points`: visible strengths detected from pose data.
- `Improvement Points`: likely areas to improve.
- `Drills`: suggested practice actions tied to detected swing faults.
- `Detected Events And Phase Scores`: automatically selected setup, stride, foot strike,
  impact, and follow-through event frames plus event confidence, detection method, phase
  scoring, and score confidence. Event confidence comes from motion phase detection;
  score confidence comes from the pose/keypoint evidence used by phase scoring.
- `Metrics`: v2 measured values, units, target ranges, severity, deductions, and
  evidence frames.
- `Detected Faults`: fault candidates, affected phases, severity, evidence, and evidence
  frames.
- `Diagnostics`: a foldable section at the bottom of motion analysis. It contains:
  `Limitations` for sampling limits, missing or low-confidence MediaPipe landmarks,
  missing bat evidence, fallback event detection, or 2D camera constraints; and
  `Pose Quality` for effective FPS, sampled frame count, pose detection ratio, required
  landmark coverage, mean/min confidence, smoothed frames, interpolated frames, rejected
  outliers, raw pose coverage, requested pose count, selected candidate indexes,
  processing mode, and stabilization deltas.

Feedback is cautious. Treat it as a local rule-based review aid, not a medical diagnosis
or guaranteed coaching truth.

## Replay Overlay

After analysis completes, the replay panel draws detected pose data on top of the
rendered video content rectangle for the sampled pose frame nearest the current replay
time.

The overlay can show:

- Body keypoints.
- Highlighting for automatically detected event frames.
- Optional evaluation lines for v2 metric evidence such as stance width, torso tilt,
  head drift, lead blocking, hip/shoulder axes, and grip-path fallback attack angle.
- Low-confidence point styling.
- Whether the selected overlay source is raw or stabilized.
- The offset in milliseconds when replay time maps to the nearest sampled pose frame
  rather than an exact pose frame.

The overlay updates when replay time changes, frame-step buttons are used, analysis
completes, analysis is cleared, or the window is resized. The overlay does not block
video controls.

The replay toolbar order is `Poses`, `Evaluation Lines`, `Metric`, then `Speed`.

The `Poses` button is on by default after pose overlay data exists and disabled before
analysis returns pose data. It toggles pose skeleton lines and keypoint circles. Pose
keypoint text tags such as `Head`, `L Wrist`, and `R Wrist` are disabled by default to
reduce clutter.

The `Evaluation Lines` button is off by default and disabled until the current swing
analysis returns evaluation-line data. It toggles service-returned metric guide lines
with concise labels such as `Stance width`, `Torso tilt`, `Lead block`, `Head drift`, or
`Grip path`.

The compact `Metric` dropdown is disabled until the current swing analysis returns
evaluation-line data. It opens a checkbox menu with `All metrics` plus one option for
each returned metric that has line data, using labels such as `Stance width`,
`Tilt hold`, `Hip/shoulder timing`, or `Follow-through`. Checking one or more metric
options filters the visible evaluation lines by the returned `metric_name`. Returning to
`All metrics` or leaving no specific metric selected shows all returned evaluation lines.

The two overlay buttons are independent. Users can show poses only, evaluation lines
only, both overlays, or neither. Toggling either button or changing the metric dropdown
redraws the canvas only; it does not rerun analysis, change replay speed, clear results,
or delete media. Evaluation-line geometry is returned by the swing analysis service,
while the browser only filters and renders it.

Metric evidence frame lists and detected-fault evidence text are bounded inside
scrollable result cells when they become long. The `Metrics` evidence column is compact
and sized for short frame-number lists. Short evidence values remain compact.

## Current Limitations

- MediaPipe body-pose analysis requires a configured local `.task` model file.
- Pose is estimated from sampled frames, not necessarily every original video frame.
- Overlay drawing accounts for `object-fit: contain` and letterboxing, but browser replay
  time is still matched to exact, nearest sampled, or interpolated pose frames.
- Evaluation lines are visual aids over returned analysis evidence. MediaPipe still
  detects body landmarks only, so bat/ball-specific line evidence is unavailable unless
  future detectors add those keypoints; grip-path fallback lines use lower-confidence
  styling.
- Evaluation-line labels identify metric evidence and are separate from pose overlays.
- Stored-video metric values use the selected video's source dimensions for aspect-aware
  geometry. Direct pose-JSON workflows without frame dimensions use a compatibility
  fallback that is less reliable for non-square sources.
- Single pose mode is diagnostic-only and intentionally skips temporal cleanup.
- MediaPipe does not detect bat tip, bat barrel, or ball position.
- Automatic event detection is motion-aware but still heuristic and not calibrated from
  real swing datasets.
- Some v2 thresholds are provisional and configurable until calibrated with validated
  swing fixtures.
- The analysis is 2D side-view rule-based evaluation and may miss 3D movement details.
- Throwing, pitching, and fielding analysis are planned but not implemented.
- Reports are not persisted yet.
