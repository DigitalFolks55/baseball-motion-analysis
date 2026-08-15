# DEV004-01 Swing Evaluation v2

## Goal

Replace the current swing evaluation methodology with a baseline-driven youth baseball
2D side-view swing evaluation model based on
`docs/80_references/Youth Baseball Swing Baseline Research.pdf`.

The implementation should preserve the local-PC-first video analysis workflow and
existing application-service boundary, but replace the v1 checklist/scoring methodology
with a clearer baseline model built around phase alignment, scale-normalized kinematic
metrics, rule-based error detection, phase-weighted scoring, and drill-mapped feedback.

This is not a release or deployment task.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/80_references/Youth Baseball Swing Baseline Research.pdf`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md`
* `docs/02_architecture/adr/ADR-0006-video-driven-swing-pose-estimation.md`
* `docs/02_architecture/adr/ADR-0007-mediapipe-pose-estimator.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Existing implementation:
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/analysis/swing.py`
  * `src/baseball_motion_analysis/feedback/swing.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/pose/models.py`
  * `src/baseball_motion_analysis/pose/estimation.py`
* Existing tests:
  * `tests/unit/test_swing_motion_metrics.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_feedback.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_analysis_api.py`
  * `tests/integration/test_swing_video_analysis_api.py`

## Required Agent Workflow

Follow the repository workflow in order:

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
```

Do not run the release agent. Do not create a release, deployment, Docker setup,
hosted web service, PyPI package, or version tag.

## Current Findings From The Baseline Research

The source PDF defines an automated youth baseball swing diagnostic model for 2D
side-view video. It treats the swing as a time series aligned into five phases:

* Setup / stance
* Loading / stride
* Foot strike / foot plant
* Impact
* Follow-through

The methodology evaluates scale-invariant kinematic metrics from 2D pose keypoints,
normalizing distances by torso length and relying on vector angles for posture, joint,
and segment relationships.

Confirmed baseline targets and checkpoints from the PDF:

* Setup stance width should be 1.0 to 1.2 times torso length.
* Setup torso forward tilt should be approximately 25 to 35 degrees relative to vertical.
* Setup grip should be between ear and shoulder height and aligned over the rear foot
  support line.
* During stride, the rear knee should not sway beyond the rear foot boundary.
* During stride, horizontal head movement should remain limited.
* At foot strike, lead knee flexion should stop and the lead side should form a blocking
  wall.
* Rotational sequence should proceed pelvis first, then thorax/shoulders, then
  arms/hands, then bat.
* At impact, the lead leg should remain firm, rear elbow should be near the torso, rear
  foot should be on the toe, and the head should stay inside the knee base.
* Torso forward tilt established at setup should be preserved through impact.
* Attack angle should be a slight upward trajectory; excessive positive attack angle is
  associated with pop-up or under-ball contact tendencies.
* Follow-through should preserve balance, avoid forced early wrist rollover, and extend
  through the hitting zone.

The PDF text extraction drops some formula-only numeric thresholds. Do not invent those
thresholds. During implementation, visually verify the PDF formula values where possible
and keep all baseline thresholds configurable. Any threshold that is not confidently
recoverable should be documented as provisional and calibrated through fixtures later.

## Replacement Scope

Replace the v1 swing evaluation methodology, not merely add new labels on top of it.

In scope:

* Introduce a v2 swing baseline model for youth baseball side-view analysis.
* Preserve existing local video analysis orchestration:

  ```text
  stored video
    -> frame sampling
    -> local pose estimation
    -> pose quality handling
    -> swing phase alignment
    -> v2 baseline metric extraction
    -> v2 rule evaluation and scoring
    -> v2 feedback
    -> browser-safe response and replay overlay data
  ```

* Support analysis from already-available pose/keypoint sequences.
* Support the current stored-video swing endpoint and local browser UI.
* Replace or migrate v1 metric/fault names where they conflict with v2.
* Keep legacy request paths backward-compatible unless there is a documented reason to
  break them.
* Keep v2 rules out of UI, API routes, storage adapters, video loaders, and sequence
  loaders.
* Keep uncertainty explicit when pose quality, camera angle, missing bat evidence, or
  phase detection quality is weak.

Out of scope:

* New hosted services, cloud uploads, authentication, mobile adapters, deployment, or
  release work.
* New production model downloads or committed model weights.
* Bat tip, bat barrel, or ball detection as a new model dependency.
* Report persistence unless it is already required by an existing service contract.
* Fielding, throwing, or pitching analysis.
* Medical diagnosis, injury prediction, or absolute coaching claims.

## Architecture Requirements

Keep the existing module boundaries:

* `pose`: body keypoint observation models, confidence values, MediaPipe mapping,
  stabilization, and pose diagnostics.
* `motion`: swing phases, handedness normalization, v2 metric input models, vector
  geometry, and phase-aligned kinematic metric calculations.
* `analysis`: v2 baseline thresholds, rule evaluation, severity, confidence aggregation,
  score calculation, and improvement-priority selection.
* `feedback`: cautious report generation and drill mapping from v2 detected errors.
* `app`: application service orchestration for pose-sequence and stored-video analysis.
* `api`: browser-safe request/response schemas and route adapters only.
* `ui`: local review workflow, controls, visualization, and rendering only.

If v2 changes public response semantics materially, add a new ADR under
`docs/02_architecture/adr/` explaining the replacement decision and compatibility
strategy.

## Data Model Requirements

Define or update typed models for:

* `SwingEvaluationVersion` or equivalent metadata identifying v2 results.
* Baseline swing phase references:
  * setup
  * loading / stride
  * foot strike / foot plant
  * impact
  * follow-through
* Phase confidence:
  * detection method
  * evidence frame or window
  * confidence score
  * limitations
* V2 metric result:
  * metric identifier
  * phase or phase window
  * measured value
  * unit
  * target range or target relation
  * warning/severe threshold when known
  * severity
  * confidence
  * required keypoints
  * evidence frame indexes
* V2 detected error:
  * error pattern
  * root biomechanical cause
  * affected phase
  * evidence
  * likely effect
  * severity
  * confidence
* V2 analysis result:
  * methodology version
  * overall score
  * phase scores
  * metric results
  * detected errors
  * primary improvement priority
  * good points
  * limitations
  * diagnostics links to sampling and pose quality data where available

Prefer explicit new v2 names over ambiguous reuse when v1 names encode old behavior.

## Phase Alignment Requirements

The v2 evaluator should evaluate phases as baseline key events and windows, not as
evenly spaced placeholders.

Required behavior:

* Reuse current motion-aware event selection as the starting point.
* Keep caller-provided phase frames available for tests and expert/internal callers.
* Improve phase references where needed so v2 metrics can use:
  * setup frame/window
  * loading stride window
  * foot strike frame
  * rotation start frame when distinguishable from foot strike
  * impact frame/window
  * follow-through frame/window
* Return explicit limitations when impact, rotation start, or follow-through is weakly
  inferred.
* Do not fabricate high confidence for videos with sparse sampling or poor pose
  coverage.

## V2 Metric Requirements

Use 2D vector math and scale-normalized coordinates. Metric calculation should remain
separate from scoring and feedback.

Required v2 metrics:

* Normalized stance width:
  * phase: setup and optionally foot strike
  * keypoints: lead ankle, rear ankle, hips, shoulders
  * calculation: horizontal ankle distance divided by torso length
  * baseline: 1.0 to 1.2 torso lengths
* Torso forward tilt and tilt preservation:
  * phase: setup through impact
  * keypoints: hips and shoulders
  * calculation: torso vector angle relative to vertical and variance/change through
    impact
  * baseline: setup tilt approximately 25 to 35 degrees; preservation threshold should
    be configurable
* Grip loading vector:
  * phase: setup/loading
  * keypoints: wrists or grip proxy, rear ankle or rear foot, shoulders, ear/head proxy
  * calculation: grip height relative to ear-shoulder band and horizontal position
    relative to rear foot support boundary
  * baseline: grip between ear and shoulder height and not drifting away from the rear
    support line
* Rear knee sway:
  * phase: loading/stride
  * keypoints: rear knee, rear ankle or rear foot
  * calculation: rear knee horizontal movement relative to rear foot boundary
  * baseline: rear knee stays inside the rear foot boundary
* Head translation ratio:
  * phase: setup to impact
  * keypoints: nose or ear, torso length
  * calculation: horizontal head displacement divided by torso length
  * baseline: minimal head displacement; numeric threshold must be configurable and
    visually verified or calibrated
* Early connection angle:
  * phase: rotation start / foot strike
  * keypoints: lead shoulder, lead wrist, torso vector
  * calculation: angle between lead arm/forearm vector and torso axis
  * baseline: use PDF-verified target when recovered; otherwise retain a configurable
    provisional range and document the limitation
* Lead knee blocking index:
  * phase: foot strike to impact
  * keypoints: lead hip, lead knee, lead ankle
  * calculation: impact knee flexion angle minus foot-strike knee flexion angle, using a
    documented sign convention
  * baseline: maintained or extended lead knee indicates blocking; additional flexion
    indicates collapse
* Hip-shoulder separation / kinematic sequence timing:
  * phase: stride to foot strike and rotation start
  * keypoints: hip vector, shoulder vector
  * calculation: pelvis rotation timing or angular velocity should lead shoulder
    rotation timing
  * baseline: pelvis leads shoulders; no lag is an arms-only/one-piece indicator
* Estimated attack angle:
  * phase: impact window
  * keypoints: wrists/grip and optional bat tip/barrel
  * calculation: tangent angle of fitted wrist/bat trajectory around impact
  * baseline: slight upward trajectory; excessive positive angle is an excessive upper
    swing indicator
  * confidence: low when bat tip/barrel is unavailable and wrist-only fallback is used
* Follow-through posture and balance:
  * phase: follow-through
  * keypoints: torso, head proxy, ankles/feet, wrists/grip
  * calculation: preserve tilt and head stability, avoid abrupt balance loss or early
    pull-off when visible
  * baseline: balanced finish with posture maintained

## V2 Error Detection Requirements

Detect these youth baseball swing error patterns with evidence, severity, confidence,
and affected phases:

* Door swing / casting:
  * root cause: upright posture, centrifugal grip detachment, arm-dominant swing, or bat
    weight mismatch
  * v2 evidence candidates: poor setup torso tilt, grip/wrist distance from chest,
    excessive early connection angle, grip drifting outside support boundary
* Forward axis drift / rushing:
  * root cause: insufficient rear-hip loading and early lunge before foot plant
  * v2 evidence candidates: rear knee sways past rear foot boundary, head translation
    exceeds threshold, upper body moves forward before foot strike
* Arms-only / one-piece swing:
  * root cause: lack of pelvis-shoulder separation or poor core sequence
  * v2 evidence candidates: no pelvis-to-shoulder phase lag, minimal elbow angle change,
    lower body not leading upper body
* Excessive upper swing / early extension:
  * root cause: rear shoulder drop, early loss of forward torso tilt, or excessive lift
    intent
  * v2 evidence candidates: excessive positive attack angle, torso tilt decreases beyond
    threshold from setup to impact, hands drop relative to barrel when bat evidence
    exists
* Collapsed lead side:
  * root cause: weak lead-leg block or insufficient ground reaction/braking
  * v2 evidence candidates: lead knee flexes after foot strike, lead knee drifts forward
    past lead ankle, head/axis continues moving forward through impact

Rules must not fire when required keypoints are missing or low confidence. In those
cases, lower confidence and add limitations.

## Scoring Requirements

Use a deterministic 100-point phase-weighted score. Preserve the current user-facing
concept of overall and phase scores, but replace v1 deductions with v2 metric and error
deductions.

Phase weights:

* Setup: 10%
* Stride: 20%
* Foot strike: 25%
* Impact: 35%
* Follow-through: 10%

Required behavior:

* Each metric should define target, warning, and severe ranges where the source supports
  them.
* Thresholds should live in a v2 config object, not inside UI or API adapters.
* Missing or low-confidence metrics should lower confidence rather than create maximum
  point deductions.
* Phase scores should explain which v2 metric caused each deduction.
* The primary improvement priority should come from the largest meaningful deduction,
  weighted by confidence and severity.
* Scores must be deterministic for the same pose input and configuration.

## Feedback Requirements

Generate cautious feedback in the `feedback` module.

The v2 report should include:

* summary
* scores
* good_points
* improvement_points
* drills_or_suggestions
* confidence
* limitations

Map detected v2 error patterns to youth-friendly correction protocols:

* Door swing / casting:
  * Cross-chest rotation drill
  * Inside-out tee drill
  * cue: keep bow posture and turn around the spine
* Forward axis drift / rushing:
  * 5-second rear leg hold drill
  * Single-leg swing drill
  * cue: sit into the back hip and hold before striding
* Arms-only / one-piece swing:
  * Hugged-bat lower-body drill
  * Stationary tee work
  * cue: turn hips first and let the arms follow
* Excessive upper swing / early extension:
  * High-grip stop drill
  * Hoop rotation drill
  * cue: keep hands higher through contact and preserve posture
* Collapsed lead side:
  * Front-leg stiff-stop drill
  * Single-leg swing drill
  * cue: push the ground back firmly with the front foot

Use cautious language:

* Prefer "may indicate", "looks like", and "based on the visible frames".
* Avoid "definitely wrong", "must", injury claims, and guaranteed coaching claims.

## API And UI Requirements

Preserve the local browser swing analysis workflow.

Required behavior:

* The stored-video swing endpoint should return v2 methodology metadata.
* Existing browser-safe response fields should remain stable where practical.
* If field names change, keep compatibility aliases or document why compatibility cannot
  be preserved.
* UI should display v2 metric names, v2 detected errors, v2 phase scores, confidence, and
  limitations.
* Replay overlay behavior should continue to show pose keypoints and event frames.
* UI code must not contain v2 thresholds, scoring rules, or drill decision logic.

## Migration Requirements

Treat v1 as replaced for normal swing evaluation.

Required behavior:

* Remove or isolate old v1 methodology so normal application paths do not mix v1 and v2
  scoring semantics.
* Update tests that assert v1-only metric names or deductions.
* Keep compatibility for internal/test callers only when it reduces breakage and does
  not confuse public behavior.
* Update documentation to state that v2 is the current swing methodology.
* Add an ADR if the implementation keeps both v1 and v2 engines concurrently.

## Testing Requirements

Add or update deterministic tests using synthetic pose fixtures and tiny existing media
fixtures only.

Required unit tests:

* 2D vector inclination and joint-angle helpers.
* Torso-length normalization.
* Handedness normalization for lead/rear side metric inputs.
* Normalized stance width target, warning, and severe behavior.
* Torso forward tilt and tilt-preservation behavior.
* Grip loading vector behavior.
* Rear knee sway behavior.
* Head translation ratio behavior.
* Early connection angle behavior.
* Lead knee blocking sign convention and collapse behavior.
* Hip-shoulder separation timing behavior.
* Estimated attack angle with and without bat keypoints.
* Follow-through posture/balance behavior where pose evidence supports it.
* Each v2 detected error pattern.
* V2 phase-weighted scoring and primary-priority selection.
* V2 feedback drill mapping and cautious language.
* Missing/low-confidence keypoint behavior.

Required integration tests:

* `SwingAnalysisApplicationService` returns a v2 result from deterministic synthetic
  pose observations.
* Stored-video swing analysis returns v2 methodology metadata through the application
  service.
* `/api/v1/analysis/swing` and `/api/v1/analysis/swing/video` return browser-safe v2
  results without exposing absolute file paths.
* Existing upload, library, replay, delete, clear-analysis, raw/stabilized overlay, and
  unsupported motion-type behavior remains unchanged where touched.

No tests should require real user videos, external credentials, network calls, model
downloads, committed large media files, or generated reports in git.

## Documentation Requirements

Update:

* `PLANS.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/` if v2 changes architecture or compatibility strategy
* `docs/05_manuals/swing_motion_analysis_ui.md` if visible UI behavior changes
* `docs/03_development_log/`

Documentation must explain:

* v2 replaces v1 as the normal swing evaluation methodology.
* v2 is based on the youth baseball side-view baseline research PDF.
* v2 evaluates phase-aligned, scale-normalized metrics rather than uncalibrated visual
  checklist claims.
* Some numeric thresholds are configurable and provisional until calibrated with
  validated fixtures.
* MediaPipe still detects body landmarks only; bat/ball evidence remains limited unless
  future evidence sources are added.

## Quality Gates

After code changes, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed, run:

```bash
uv run ruff format .
```

Final review should confirm:

* v2 replaces the normal v1 swing evaluation path.
* Baseball rules remain outside UI/API/storage/video/sequence modules.
* Tests cover v2 metrics, errors, scoring, feedback, application services, and API
  behavior.
* Docs and `PLANS.md` are updated.
* No secrets, user videos, large media, model weights, `.env` files, generated reports,
  or release artifacts are included.
