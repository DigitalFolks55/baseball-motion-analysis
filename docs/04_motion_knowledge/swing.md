# Swing Motion Knowledge

Source reference: `docs/80_references/Youth Baseball Swing Baseline Research.pdf`

This document defines the current v2 app-oriented swing evaluation model for youth
baseball side-view video or image-sequence analysis. The rules are coaching heuristics
for feedback and scoring, not medical advice or absolute truth. The app should report
uncertainty when camera angle, keypoint confidence, missing bat visibility, or phase
detection quality is weak.

## Evaluation Scope

Initial swing evaluation should focus on standard 2D side-view analysis from a local
video or ordered image sequence. The intended player group is youth baseball players,
where feedback should be understandable to players, coaches, and parents.

Primary goals:

* Detect the main swing phases.
* Measure scale-invariant body and bat-path metrics from pose keypoints.
* Identify good points and likely improvement points.
* Generate actionable feedback tied to the largest score deductions.
* Preserve confidence and limitation notes for uncertain detections.

Non-goals for the first swing evaluation:

* Do not claim professional-grade biomechanics.
* Do not require force-plate, bat-sensor, ball-tracking, or 3D motion-capture data.
* Do not diagnose injuries or guarantee coaching correctness.
* Do not hard-code swing rules in UI callbacks, route handlers, or storage adapters.

## Required Input Assumptions

The swing evaluator should receive pose and optional bat/keypoint trajectories from the
pose layer or motion preprocessing layer. Raw media loading remains outside this domain
knowledge.

Minimum useful keypoints:

* Head proxy: nose or ear.
* Shoulders: lead and rear shoulder.
* Elbows: lead and rear elbow.
* Wrists or hands: lead and rear wrist, preferably both hands near the grip.
* Hips: lead and rear hip.
* Knees: lead and rear knee.
* Ankles or feet: lead and rear ankle or foot.
* Optional bat tip or barrel keypoint when available.

Frame-level requirements:

* Pose keypoints should include confidence values.
* Side-view handedness should be normalized into lead side and rear side.
* Coordinates should be measured in a consistent image coordinate space and then
  normalized by body scale, commonly torso length or shoulder-hip distance, before
  spatial thresholds are applied.
* When source frame width and height are known, normalized pose points should be
  converted to pixel-space or equivalent aspect-aware coordinates before distance,
  displacement, vector-angle, or joint-angle math is performed.
* Rules should be skipped or marked low confidence when required keypoints are missing.

## Swing Phases

The swing is continuous, but the first evaluator should align frames to five phases.

Before automatic phase alignment, stored-video analysis should distinguish body landmark
quality from swing event quality:

* Body landmark quality describes whether the visible frame contains enough reliable
  head, torso, wrist, hip, knee, and ankle evidence for swing analysis.
* Swing event quality describes whether the ordered pose sequence contains enough motion
  cues to place setup, stride, foot strike, estimated impact, and follow-through.

For video-driven analysis, weak body-pose frames may be ignored or down-weighted for
phase detection while preserving their original frame indexes and timestamps for replay
alignment. The app should report weak or rejected frame counts rather than hiding that
uncertainty.

The automatic path should detect an active swing window before selecting phases. This
reduces the chance that long pre-swing stance time, walking, coach movement, or
post-swing idle frames dominate impact or follow-through selection. Setup should still
prefer the earliest stable high-quality stance evidence before the active window when it
exists. If the first usable pose frame already shows motion, setup should be reported as
uncertain rather than silently selecting a late frame. Stride should prioritize sustained
lower-body onset instead of wrist waggle and should not collapse next to setup when
enough sampled frames exist. When the lead leg visibly lifts, stride should align with
that lead-leg lift state; no-stride hitters should be reported with lower-confidence
fallback semantics. Foot strike should use the detected setup baseline and should depend
on prior lead-leg lift/descent/plant evidence when visible, not a planted setup frame or
later maximum displacement. Estimated impact should avoid hard late-frame bias, and
follow-through should represent the first stable swing finish inside the active swing
window plus a small buffer rather than unrelated idle/reset frames.

### 1. Setup / Stance

Purpose: establish a balanced power position before movement.

Evaluation concepts:

* Stance is slightly wider than shoulder width.
* Weight appears balanced over the balls of both feet.
* Knees are slightly active rather than locked or flared outward.
* Hip flexion creates forward trunk tilt.
* Shin and torso angles are approximately parallel.
* Grip starts around ear-to-shoulder height and near the rear side, not far outside the
  body.

Good indicators:

* Stable head and torso.
* Shin-torso parallelism is maintained.
* Hands start in a compact position that does not predispose the bat to cast outward.

Improvement indicators:

* Upright posture with little forward trunk tilt.
* Hands or grip drift too far away from the rear side before the swing.
* Lower body looks locked, collapsed, or unstable.

### 2. Loading / Stride

Purpose: load over the rear hip while beginning controlled forward movement.

Evaluation concepts:

* The player shifts weight into the rear hip as the lead foot lifts or strides.
* Rear knee should not sway outside the rear foot boundary.
* Head translation toward the pitcher should remain limited.
* Grip and upper body remain loaded while the lead foot strides.
* Pelvis and shoulders begin to create separation rather than moving as one rigid block.

Good indicators:

* Rear hip load is visible without excessive sway.
* Head movement is smooth and limited.
* Upper body stays back long enough to create hip-shoulder separation.

Improvement indicators:

* Rear knee sways beyond the rear foot.
* Head and torso rush forward early.
* Hands drift forward with the stride instead of staying loaded.

Implementation note: if the lead leg visibly lifts, the automatic detector should use
lead ankle vertical lift from setup baseline, with lead knee lift/flexion as secondary
evidence, and select the public stride frame at the visible leg-lift peak. If no lift is
visible, lower-body load can be used only as a lower-confidence no-stride fallback.

### 3. Foot Strike / Foot Plant

Purpose: transition from forward movement into rotation and energy transfer.

Evaluation concepts:

* Lead heel or foot plant starts the explosive rotational sequence.
* Lead knee stops flexing and begins to brace or extend.
* Pelvis rotation should lead shoulder rotation.
* Early connection angle between the lead forearm and torso should be approximately
  80 to 105 degrees at rotation start.

Good indicators:

* Lead side forms a firm blocking wall.
* Pelvis rotation begins before shoulder rotation.
* Lead forearm stays connected to torso rotation instead of disconnecting away from the
  body.

Improvement indicators:

* Lead knee keeps collapsing after landing.
* Pelvis and shoulders rotate with no visible timing lag.
* Lead arm disconnects early, causing a wide door-swing path.

Implementation note: foot strike should be searched after lead-leg lift/descent when
that state is visible. A confident plant requires the lead foot to return near the
setup/ground baseline and stabilize for a short window when frame density allows. If no
prior leg lift is visible, foot strike should carry an explicit no-stride or sparse
fallback reason.

### 4. Impact

Purpose: transfer stored rotational energy through the ball.

Evaluation concepts:

* Top hand is palm-up and bottom hand is palm-down when visible.
* Rear foot is on the toe.
* Lead leg remains firm.
* Rear elbow is slotted near the torso.
* Head stays between the knees rather than drifting beyond the front side.
* Head, rear knee, and ground form a stable rear-side axis.
* Eyes remain directed toward the contact point when face visibility allows.
* Estimated attack angle is ideally +5 to +15 degrees.
* Estimated attack angle above +20 degrees suggests an excessive upper swing or pop-up
  tendency.

Good indicators:

* Firm lead side with stable head position.
* Connected rear elbow and compact hand path.
* Slight upward attack angle without excessive uppercut.

Improvement indicators:

* Lead knee collapses or drifts forward.
* Head lunges outside the base.
* Rear shoulder drops and attack angle becomes too steep upward.

Implementation note: without bat/barrel and ball evidence, impact remains an estimated
body-motion window. The current app can use wrist/grip velocity, acceleration or
deceleration, contact-zone hand position, lead-side/body constraints, and rotation cues,
but it must not claim exact bat-ball contact from body landmarks alone.

The service boundary exposes three impact policies:

* `body_pose_estimated`: default behavior; impact is estimated from body-pose motion
  cues and marked as estimated.
* `skip_without_ball`: impact is skipped when no ball/contact evidence is available;
  this remains for explicit API compatibility and future advanced workflows.
* `require_ball_contact`: impact is unavailable unless a future ball/contact detector
  supplies evidence.

The stricter policies do not add a ball detector. They prevent contact-dependent
evaluation from being inferred from a body-pose proxy.

The normal browser workflow does not expose an `Impact Detection` off/on control. It
uses `body_pose_estimated` impact and labels impact as estimated, not confirmed contact.
The detector should select impact after foot strike within the active swing window using
wrist/grip motion transition, contact-zone hand position, lead-side bracing, and
rotation cues. It should penalize early pre-contact frames and late finish-only frames.
Explicit API callers can still request skipped impact; skipped impact should not be
shown as a normal detected contact event or replay event label.

### 5. Follow-Through

Purpose: decelerate smoothly while preserving swing direction and balance.

Evaluation concepts:

* Bat continues through the hitting zone instead of stopping abruptly.
* Early wrist roll is avoided when wrist/hand orientation can be inferred.
* Forward trunk tilt and head stability from impact are mostly preserved.
* Finish remains balanced between both feet.

Good indicators:

* Balanced finish.
* Torso posture remains controlled after contact.
* Hands and barrel extend through the swing path.

Improvement indicators:

* Sudden posture loss after impact.
* Early wrist roll or immediate pull-off.
* Finish falls forward, backward, or off the side-view axis.

Implementation note: follow-through should be bounded to the active swing window plus a
small buffer. The detector should prefer the first finish frame after extension or
rotation evidence and should penalize large whole-body translation, walking, or reset
motion after the swing.

## Kinematic Metrics

Use 2D vector math in aspect-aware image coordinates, then normalize distances by body
scale where the metric requires a ratio. Browser overlay primitives may still carry
normalized points for rendering, but metric math should not mix raw normalized `x` and
`y` units from non-square frames. The implementation should keep metric calculation
separate from scoring and feedback text.

### Normalized Stance Width

Keypoints:

* Lead ankle.
* Rear ankle.
* Torso length from shoulder and hip midpoints.

Calculation:

* Horizontal ankle distance divided by torso length.

Target:

* 1.0 to 1.2 torso lengths during setup.

Interpretation:

* Within range suggests a stable but rotatable base.
* Too narrow or too wide may reduce balance or rotational ease.

### Torso Forward Tilt And Preservation

Keypoints:

* Both hips.
* Both shoulders.

Calculation:

* Torso vector angle relative to vertical at setup.
* Absolute tilt change from setup to impact.

Target:

* Setup torso forward tilt is approximately 25 to 35 degrees.
* Tilt preservation threshold is configurable until calibrated fixtures exist.

Interpretation:

* Within range suggests a power posture.
* Large loss of tilt through impact may indicate early extension.

### Grip Loading Vector

Keypoints:

* Wrists or grip proxy.
* Rear ankle, heel, or foot index when available.
* Rear shoulder and head proxy.

Calculation:

* Grip height is checked against the ear-to-shoulder band.
* Horizontal grip position is checked against the rear foot support boundary.

Interpretation:

* Compact rear-side grip loading reduces casting risk.
* Grip outside the baseline area may indicate an early hand cast.

### Rear Knee Sway

Keypoints:

* Rear knee.
* Rear ankle or rear foot.
* Torso length.

Calculation:

* Rear knee movement outside the rear foot boundary divided by torso length.

Interpretation:

* Low sway suggests controlled rear-hip loading.
* Excessive sway may indicate rushing or poor rear-side load.

### Early Connection Angle

Keypoints:

* Torso vector.
* Lead shoulder to lead wrist vector.

Calculation:

* Angle between torso axis and lead forearm or lead-arm vector at rotation start.

Target:

* Approximately 80 to 105 degrees at the start of trunk rotation.

Interpretation:

* Within target suggests the bat and arms are connected to torso rotation.
* Above target or excessive wrist-to-chest distance may indicate door swing or casting.

### Lead Knee Blocking Index

Keypoints:

* Lead hip, lead knee, lead ankle.

Calculation:

* Change in lead knee angle from foot strike to impact.

Interpretation:

* Knee angle maintained or extending suggests proper front-side bracing.
* Additional knee flexion after foot strike suggests lead-side collapse.

### Head Translation Ratio

Keypoints:

* Head proxy.
* Torso length scale.

Calculation:

* Horizontal head displacement from setup to impact divided by torso length.

Interpretation:

* Lower displacement suggests a stable rotational axis.
* Excessive forward displacement suggests rushing or forward axis drift.
* Exact threshold should be configurable and calibrated with fixtures because the
  source PDF extraction did not preserve the numeric symbol value.

### Estimated Attack Angle

Keypoints:

* Both wrists or grip point.
* Bat tip or barrel when available.

Calculation:

* Fit a local trajectory around impact and calculate the tangent angle at impact.
* Horizontal is 0 degrees; upward tilt is positive.

Target:

* Ideal range: +5 to +15 degrees.
* Warning range: above +20 degrees may indicate excessive upper swing.

Interpretation:

* Slight positive angle suggests the swing path matches a typical incoming pitch path.
* Excessive positive angle suggests the bat may be undercutting the ball.

### Hip-Shoulder Separation Timing

Keypoints:

* Pelvis or hip vector.
* Shoulder vector.

Calculation:

* Compare timing of pelvis rotation onset or peak angular velocity against shoulder
  rotation onset or peak angular velocity.
* Report the separation in milliseconds. Positive values mean pelvis rotation leads
  shoulder rotation; negative values mean shoulders lead hips.
* The current threshold conversion preserves the earlier 30 FPS calibration reference:
  one frame of lag at 30 FPS is `33.333` milliseconds.

Interpretation:

* Pelvis should lead shoulders.
* Little or no phase lag suggests an arms-only or one-piece swing.

## Common Fault Patterns

Fault detection should return evidence, affected phases, severity, and confidence.
Rules should use configurable thresholds and should not fire when required keypoints
are unreliable.

### Door Swing / Casting

Likely cause:

* Upright torso posture, disconnected lead arm, centrifugal casting, arm-dominant swing,
  or bat weight mismatch.

Detection candidates:

* Early connection angle exceeds the target range at rotation start.
* Wrist or grip horizontal distance from the chest, normalized by torso length, exceeds
  a configurable threshold.
* Setup posture lacks forward trunk tilt.

Likely effect:

* Wide bat path, late contact point, weaker contact.

Suggested feedback:

* "Your hands may be getting away from your body early. Try keeping your posture tilted
  forward and turning around that spine angle."

Suggested drills:

* Cross-arm rotation drill.
* Inside-out tee drill.

### Forward Axis Drift / Rushing

Likely cause:

* Poor rear-hip load or early upper-body lunge toward the pitcher.

Detection candidates:

* Rear knee moves outside the rear ankle or rear foot boundary during stride.
* Head translation ratio from setup to impact exceeds a configurable threshold.
* Upper body moves forward before foot strike.

Likely effect:

* Unstable contact timing and reduced ability to adjust to off-speed pitches.

Suggested feedback:

* "Your head and upper body may be moving forward early. Try loading into the back hip
  and staying balanced until the front foot lands."

Suggested drills:

* 5-second rear hip load hold drill.
* Single-leg balance swing drill.

### Arms-Only / One-Piece Swing

Likely cause:

* Pelvis and shoulders rotate together without hip-shoulder separation, or arms dominate
  the movement.

Detection candidates:

* Pelvis-shoulder rotation lag is near zero.
* Elbow angle remains static during swing initiation.
* Lower-body rotation does not clearly precede upper-body rotation.

Likely effect:

* Reduced bat speed and weaker energy transfer.

Suggested feedback:

* "Your hips and shoulders may be turning together. Try starting the turn from the hips
  and letting the hands follow."

Suggested drills:

* Chest-hugged bat swing drill.
* Tee placement drill.

### Excessive Upper Swing / Early Extension

Likely cause:

* Rear shoulder dip, loss of forward trunk angle, pelvis thrusting forward, or excessive
  intent to lift the ball.

Detection candidates:

* Estimated attack angle exceeds +20 degrees.
* Trunk tilt shifts backward relative to setup before or at impact.
* Grip drops below the barrel or hands lose height through contact when bat keypoints are
  available.

Likely effect:

* Undercutting the ball, pop-up tendency, inconsistent contact.

Suggested feedback:

* "Your swing path may be getting too upward through contact. Try keeping your hands
  above the barrel and preserving your posture."

Suggested drills:

* High-grip freeze drill.
* Hula-hoop swing-path drill.

### Collapsed Lead Side

Likely cause:

* Lead knee fails to brace after foot plant or drifts forward, reducing front-side
  braking.

Detection candidates:

* Lead knee flexes further from foot strike to impact.
* Lead knee moves forward past the lead ankle after foot strike.
* Head and center of mass continue drifting forward through impact.

Likely effect:

* Energy leaks forward, rotational speed decays, contact consistency drops.

Suggested feedback:

* "Your front side may be soft at contact. Try firming up the lead leg and pushing the
  ground away with the front foot."

Suggested drills:

* Firm lead-leg stop drill.
* Single-leg swing drill.

## Scoring Model

Use a 100-point score with phase-weighted deductions. Score calculations should produce
phase sub-scores, metric-level deductions, and fault-level score impact so feedback can
explain why points were lost.

Recommended phase weights:

* Setup: 10%
* Stride: 20%
* Foot Strike: 25%
* Impact: 35%
* Follow-through: 10%

Penalty behavior:

* Each metric should define a target range, a warning range, and a severe range.
* Penalties should scale with deviation magnitude from the target.
* Detected faults should be score-relevant through the analysis layer. Metric-backed
  faults should credit existing linked metric deductions first, then apply only a capped
  additional fault deduction when the fault severity and confidence justify it.
* Secondary fault evidence that is not represented as a scored metric, such as excessive
  wrist-to-chest distance or lead-knee forward drift, should be able to reduce the
  relevant phase score when the evidence is sufficiently supported.
* Fault caps should scale with phase weight, severity, and confidence so low-confidence
  evidence has smaller score impact than high-confidence evidence.
* Suppressed impact-phase faults should not add hidden score penalties when impact is
  skipped or unavailable.
* Missing or low-confidence metrics should reduce confidence rather than automatically
  deducting full points.
* The scoring layer should identify the largest deduction as the primary improvement
  priority.

## Feedback Requirements

The feedback layer should convert analysis results into cautious, plain-language
guidance.

Report sections:

* `summary`: short overall swing assessment.
* `scores`: overall score, phase scores, and confidence.
* `good_points`: observed strengths with evidence.
* `improvement_points`: most important improvement areas with evidence.
* `drills_or_suggestions`: drills tied to detected fault patterns.
* `limitations`: missing keypoints, camera-angle issues, missing bat visibility, or weak
  phase detection.

Language style:

* Prefer "may indicate", "looks like", and "based on the visible frames".
* Avoid "definitely wrong", "must", and injury claims.
* Explain the body part, timing, likely effect, and one clear next action.

## Implementation Notes For The App

The UI and any future API must call an application service, not this domain logic
directly. A clean implementation should keep:

* Phase detection in `motion` or a swing-specific motion component.
* Metric calculation in `motion` or `analysis` pure functions.
* Rule evaluation and scoring in `analysis`.
* User-facing text generation in `feedback`.
* Local media and reports in `storage`.

The first implementation should prioritize deterministic, fixture-based tests using
synthetic keypoint sequences before relying on real videos.

## Current Implementation Status

DEV003-01 implements the first rule-based swing evaluation foundation for pose/keypoint
sequences that are already available to the application. It provides:

* Internal normalized 2D pose observation models.
* Handedness normalization for lead and rear body sides.
* Caller-provided phase frames plus a conservative automatic phase fallback.
* The v1 kinematic metrics listed above.
* Rule-based fault detection and phase-weighted scoring.
* Feedback report generation with drills, confidence, and limitations.
* Application-service orchestration that returns an in-memory result.

DEV003-02 exposes this foundation through the local browser UI for already-extracted
pose data. The UI can submit pasted pose JSON, a pose JSON file, or deterministic demo
pose data to `/api/v1/analysis/swing` and display the returned scores, metrics, faults,
feedback, confidence, and limitations.

DEV003-04 adds the first video-driven swing workflow. A stored uploaded video can be
analyzed through `/api/v1/analysis/swing/video`; the application service samples frames,
estimates pose locally, automatically selects representative setup, stride, foot strike,
impact, and follow-through frames, runs swing scoring, and returns pose/event overlay
metadata for replay.

DEV003-05 replaces the default stored-video heuristic pose placeholder with MediaPipe
Pose Landmarker body-pose detection. The video analysis service now expects a configured
local MediaPipe `.task` model and converts MediaPipe landmarks into the internal
`PoseFrame` model before swing event selection, scoring, feedback, and replay overlay
generation.

`HeuristicPoseEstimator` remains available only for tests or explicit fallback injection.
It should not be used as the default analysis source for user-selected videos.

DEV003-06 improves the practical quality of MediaPipe-driven analysis:

* Higher-accuracy swing sampling is the default, with faster and balanced quality modes
  available for local runtime tradeoffs.
* MediaPipe can request multiple pose candidates and selects the player by track
  continuity first, then visible landmark confidence and body-box size.
* Raw normalized landmark coordinates are preserved for analysis. Out-of-frame landmarks
  are marked for diagnostics and clamped only when drawn in the browser overlay.
* Pose observations are stabilized with outlier rejection, short-gap interpolation, and
  smoothing before automatic phase detection and scoring.
* Automatic setup, stride, foot strike, estimated impact, and follow-through events are
  selected from stable pre-motion posture, lower-body load, lead-foot plant, constrained
  body-motion contact-window cues, and post-impact extension/deceleration instead of
  evenly spaced frame positions in the normal path.
* DEV006-02 restored default MediaPipe candidate selection to the original best-scored
  candidate behavior after the DEV006-01 switch holdback proved risky for pose quality.
  Candidate switch rejection remains an explicit tuning option rather than the default.
* Results expose sampling diagnostics, pose-quality diagnostics, and per-phase confidence
  plus fallback reasons so low-quality results can explain likely causes.

DEV003-07 adds pose-parity diagnostics for cases where app overlays look worse than a
notebook experiment:

* The normal stored-video path requests one MediaPipe pose by default for ordinary
  single-player clips. Multi-person selection can still be enabled explicitly with
  `BMA_MEDIAPIPE_NUM_POSES`.
* Notebook-parity mode requests one pose and disables outlier rejection, interpolation,
  and smoothing so the app can show raw MediaPipe normalized landmarks for comparison.
* Raw and stabilized pose diagnostics are reported separately, including selected
  candidate indexes when MediaPipe returns candidates.
* Stabilization reports how much landmarks moved relative to body scale and warns when
  a change is large enough to justify comparing the raw overlay.
* High-velocity wrist and ankle landmarks are not smoothed aggressively because they are
  important for swing timing and can move quickly in valid motion.
* The browser can draw either stabilized analysis landmarks or raw detector landmarks and
  shows the replay-to-pose-frame offset in milliseconds when the overlay frame is not
  exact.

MediaPipe body pose does not provide bat tip, bat barrel, or ball landmarks. Swing
analysis must not fake those keypoints. Attack-angle and bat-path related feedback should
remain lower confidence and include a limitation unless a future bat detector supplies
that evidence.

Video-driven analysis uses the continuous ordered pose sequence as input, but the v1
metrics still report evidence around representative event frames or event windows. The
UI no longer asks users to assign setup, stride, foot strike, impact, or follow-through
frames manually.

DEV004-01 replaces the normal v1 swing scoring semantics with the v2 youth baseline
methodology. Normal results now include `methodology_version: swing_evaluation_v2` and
evaluate normalized stance width, torso forward tilt, torso tilt preservation, grip
loading vector, rear knee sway, head translation ratio, early connection, lead knee
blocking, hip-shoulder separation timing, estimated attack angle, and follow-through
posture/balance.

DEV004-04 corrects the measurement coordinate policy for non-square videos. Stored-video
analysis now passes source frame width and height into phase detection, v2 metric
calculation, and secondary fault evidence so distances and angles are calculated in the
same image coordinate space before torso-length normalization. Direct pose-sequence
callers may also provide frame dimensions; if they do not, the evaluator keeps the
legacy normalized-coordinate fallback and should be treated as lower-fidelity geometry
for non-square sources.

DEV007-01 makes stored-video swing timing independent of source FPS. The motion layer
uses `timestamp_seconds` as presentation time rather than treating adjacent sampled
frames as equal elapsed-time steps. Linear movement thresholds are interpreted as body
scales per second, angular movement thresholds as degrees per second, and persistence
windows are mapped from the 30 FPS reference into real-time durations. Stored-video
quality modes use stable target cadences of 30 FPS, 24 FPS, and 12 FPS for higher
accuracy, balanced, and faster modes respectively, with frame caps distributed across
the full usable clip. This keeps setup and follow-through regions eligible even when the
source video has a high frame rate.

DEV007-02 makes Detected Faults explicitly score-relevant. Swing fault results now
include linked metric names and bounded score impact. Phase scores now separate metric
deductions from additional fault deductions. The analysis layer credits linked metric
deductions before adding any fault deduction, preventing uncontrolled double counting
while allowing secondary evidence such as wrist-to-chest distance or lead-knee forward
drift to affect score. UI and API layers only serialize and render these returned
fields.

Known limitations:

* MediaPipe body-pose analysis requires a configured local `.task` model file.
* Pose is estimated from timestamp-selected sampled frames. Higher-FPS short clips no
  longer bypass the quality-mode target cadence solely because they fit under the frame
  cap.
* OpenCV decoder timestamps are backend dependent; constant-FPS synthesis or timestamp
  repair is reported as a diagnostic limitation when needed.
* Faster analysis mode can miss foot strike or the estimated impact window.
* Notebook-parity mode is a diagnostic view of raw MediaPipe landmarks, not the final
  stabilized analysis path.
* Automatic phase detection uses motion cues, but it is still heuristic and not
  calibrated from real swing events.
* Bat tip / barrel keypoints are not detected by MediaPipe Pose; attack angle falls back
  to grip trajectory with reduced confidence when bat keypoints are missing.
* 2D side-view pose cannot perfectly evaluate all rotation, depth, contact, or bat/ball
  mechanics.
* Report persistence remains future work.
