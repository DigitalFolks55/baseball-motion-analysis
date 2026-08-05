# Swing Motion Knowledge

Source reference: `docs/80_references/Deep-Research_Swing.pdf`

This document defines the first app-oriented swing evaluation model for youth baseball
side-view video or image-sequence analysis. The rules are coaching heuristics for
feedback and scoring, not medical advice or absolute truth. The app should report
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
* Coordinates should be normalized by body scale, commonly torso length or shoulder-hip
  distance, before spatial thresholds are applied.
* Rules should be skipped or marked low confidence when required keypoints are missing.

## Swing Phases

The swing is continuous, but the first evaluator should align frames to five phases.

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

## Kinematic Metrics

Use 2D vector math and normalized coordinates. The implementation should keep metric
calculation separate from scoring and feedback text.

### Shin-Torso Parallelism

Keypoints:

* Ankle to knee vector.
* Hip to shoulder vector.

Calculation:

* Absolute angle difference between the shin vector and torso vector.
* Evaluate primarily during setup and stride.

Interpretation:

* Smaller angle difference suggests the hitter is preserving the forward power posture.
* Larger angle difference may indicate upright posture, collapsed posture, or poor load.

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
phase sub-scores and metric-level deductions so feedback can explain why points were
lost.

Recommended phase weights:

* Setup: 10%
* Stride: 20%
* Foot Strike: 25%
* Impact: 35%
* Follow-through: 10%

Penalty behavior:

* Each metric should define a target range, a warning range, and a severe range.
* Penalties should scale with deviation magnitude from the target.
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
  selected from wrist/grip velocity, ankle movement, and hip/shoulder rotation cues
  instead of evenly spaced frame positions in the normal path.
* Results expose sampling diagnostics, pose-quality diagnostics, and per-phase confidence
  so low-quality results can explain likely causes.

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

Known limitations:

* MediaPipe body-pose analysis requires a configured local `.task` model file.
* Pose is estimated from sampled frames unless the selected quality mode and clip length
  allow full-frame processing under the configured cap.
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
