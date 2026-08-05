# DEV003-01 Swing Evaluation v1

## Goal

Implement the first local-PC swing motion evaluation workflow described in
`docs/04_motion_knowledge/swing.md`.

The feature should analyze pose/keypoint time series from a side-view baseball swing,
detect major swing phases, calculate rule-based metrics, score the swing, and generate
feedback with good points, improvement points, drills, confidence, and limitations.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/04_motion_knowledge/swing.md`
* Relevant architecture docs under `docs/02_architecture/`
* Existing tests for `motion`, `analysis`, `feedback`, `pose`, and application services
  touched by this work

## Scope

Implement swing evaluation from an already available pose/keypoint sequence. Keep media
loading, frame sampling, pose extraction, swing phase detection, scoring, and feedback
separated.

Required behavior:

* Accept frame-level pose observations with timestamps or frame indexes.
* Normalize handedness into lead side and rear side.
* Detect or accept the five swing phases:
  * Setup / Stance
  * Loading / Stride
  * Foot Strike / Foot Plant
  * Impact
  * Follow-through
* Calculate these metrics where keypoints are available:
  * Shin-torso parallelism
  * Early connection angle
  * Lead knee blocking index
  * Head translation ratio
  * Estimated attack angle
  * Hip-shoulder separation timing
* Evaluate these fault candidates:
  * Door Swing / Casting
  * Forward Axis Drift / Rushing
  * Arms-Only / One-Piece Swing
  * Excessive Upper Swing / Early Extension
  * Collapsed Lead Side
* Return an overall score, phase scores, metric deductions, detected faults, evidence,
  confidence, and limitations.
* Generate a feedback report with summary, good points, improvement points, drills or
  suggestions, confidence, and limitations.

## Non-Goals

* Do not implement a new pose-estimation model unless the project already has the pose
  interface ready for it.
* Do not implement hosted web services, cloud uploads, authentication, mobile adapters,
  or deployment.
* Do not require real user videos or large binary fixtures.
* Do not hard-code baseball rules in UI callbacks, API routes, storage adapters, or media
  loaders.
* Do not claim medical diagnosis, injury prediction, or guaranteed coaching truth.

## Architecture Requirements

Follow the repository boundaries:

* `pose`: expose stable keypoint observations and confidence values.
* `motion`: define swing phases, handedness normalization, swing-specific domain models,
  and geometric metric inputs.
* `analysis`: evaluate metrics, rule candidates, score deductions, confidence, and issue
  severity.
* `feedback`: convert analysis results into cautious user-facing feedback and drills.
* `app`: expose an application service method that orchestrates swing evaluation.
* `ui`: call the application service only if UI integration is included in this task.
* `storage`: persist reports only through storage/application services if report storage
  is included in this task.

Prefer small pure functions for geometry and scoring so unit tests can use synthetic
keypoints.

## Data Model Requirements

Define or reuse typed models for:

* Frame pose observation:
  * frame index or timestamp
  * normalized keypoints
  * keypoint confidence
* Swing handedness:
  * right-handed
  * left-handed
  * unknown
* Swing phase frame references:
  * setup
  * stride/load
  * foot strike
  * impact
  * follow-through
* Swing metric result:
  * metric name
  * measured value
  * target range when known
  * severity
  * confidence
  * evidence frames
* Swing fault result:
  * fault type
  * affected phase
  * evidence
  * severity
  * confidence
* Swing analysis result:
  * overall score
  * phase scores
  * metric results
  * detected faults
  * good points
  * improvement priorities
  * limitations

## Metric Requirements

Use 2D vector math and scale-normalized coordinates.

Metric details:

* Shin-torso parallelism:
  * Compare ankle-to-knee and hip-to-shoulder vector angles.
  * Evaluate setup and stride.
* Early connection angle:
  * Compare torso vector with lead shoulder-to-lead wrist vector.
  * Target range is 80 to 105 degrees at rotation start.
* Lead knee blocking index:
  * Compare lead knee angle at foot strike and impact.
  * Bracing or extension is good; additional flexion is a collapse signal.
* Head translation ratio:
  * Compute horizontal head displacement from setup to impact divided by torso length.
  * Threshold must be configurable and initially conservative because the source PDF did
    not preserve the exact numeric threshold in extraction.
* Estimated attack angle:
  * Use wrist/grip and bat tip/barrel trajectory when available.
  * Target range is +5 to +15 degrees.
  * Above +20 degrees is a warning for excessive upper swing.
  * If bat tip is unavailable, return low confidence or use grip trajectory as a fallback
    with an explicit limitation.
* Hip-shoulder separation timing:
  * Compare pelvis/hip vector rotation timing with shoulder vector rotation timing.
  * Pelvis should lead shoulders.

## Scoring Requirements

Use a 100-point score with phase-weighted deductions:

* Setup: 10%
* Stride: 20%
* Foot Strike: 25%
* Impact: 35%
* Follow-through: 10%

Scoring rules:

* Each metric should have target, warning, and severe ranges where possible.
* Deductions should scale with deviation magnitude.
* Missing metrics should lower confidence instead of automatically creating maximum
  deductions.
* The result should expose the largest deduction as the primary improvement priority.
* Scores and feedback must be deterministic for the same keypoint input.

## Feedback Requirements

Generate cautious feedback using `feedback` module logic.

The report should include:

* `summary`
* `good_points`
* `improvement_points`
* `drills_or_suggestions`
* `confidence`
* `limitations`

Map detected faults to drills:

* Door Swing / Casting:
  * Cross-arm rotation drill
  * Inside-out tee drill
* Forward Axis Drift / Rushing:
  * 5-second rear hip load hold drill
  * Single-leg balance swing drill
* Arms-Only / One-Piece Swing:
  * Chest-hugged bat swing drill
  * Tee placement drill
* Excessive Upper Swing / Early Extension:
  * High-grip freeze drill
  * Hula-hoop swing-path drill
* Collapsed Lead Side:
  * Firm lead-leg stop drill
  * Single-leg swing drill

Use cautious language:

* Prefer "may indicate", "looks like", and "based on the visible frames".
* Avoid absolute coaching claims and injury claims.

## Acceptance Criteria

* A local application service can return a swing analysis result from a deterministic
  synthetic pose sequence.
* The implementation detects or accepts the five swing phases.
* Metric calculations are covered by unit tests with known geometric inputs.
* Fault detection is covered by unit tests for each fault candidate.
* Scoring produces overall and phase scores with deterministic deductions.
* Feedback includes good points, improvement points, drills or suggestions, confidence,
  and limitations.
* Low-confidence or missing keypoints lower confidence and add limitations instead of
  crashing.
* No UI callback, API route, storage adapter, video loader, or sequence loader contains
  hard-coded swing coaching rules.
* No large media, model weights, generated reports, secrets, or user videos are added.

## Test Requirements

Add focused tests for:

* 2D angle and vector helpers.
* Handedness normalization.
* Swing phase input validation or phase detector behavior.
* Each metric listed above.
* Each fault candidate listed above.
* Phase-weighted scoring and largest-deduction selection.
* Feedback mapping from faults to report sections and drills.
* Application service orchestration with mocked pose/keypoint input.
* Missing keypoint and low-confidence keypoint behavior.

Use synthetic keypoint fixtures or tiny existing fixtures only. Do not require real user
videos or external credentials.

## Documentation Requirements

Update documentation if product behavior, architecture boundaries, or evaluation rules
change during implementation.

At minimum, confirm whether these docs need updates:

* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/adr/` if a major design decision is introduced
* `docs/03_development_log/` for the implementation log
* `PLANS.md` status or milestone notes

## Required Quality Commands

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

## Open Questions For Implementation

* Which pose keypoint schema will be the stable internal format for swing evaluation?
* Will v1 require automatic phase detection, or may callers provide phase frame indexes?
* What conservative thresholds should be used for head translation ratio and wrist-chest
  distance before calibration fixtures exist?
* How should bat tip detection be represented when the pose model does not provide bat
  keypoints?
* Should report persistence be included in DEV003-01, or should it return an in-memory
  result only?
