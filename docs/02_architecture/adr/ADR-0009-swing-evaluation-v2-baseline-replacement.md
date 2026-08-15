# ADR-0009: Swing Evaluation v2 Baseline Replacement

## Status

Accepted

## Context

DEV004-01 replaces the normal swing evaluation methodology. The previous v1 model used
a smaller checklist-style metric set and grew into a video-driven MediaPipe workflow, but
the scoring semantics remained tied to the original six metrics.

The new reference,
`docs/80_references/Youth Baseball Swing Baseline Research.pdf`, defines a youth
baseball 2D side-view baseline model organized around phase alignment, torso-length
normalization, vector angles, phase-weighted scoring, common youth swing error patterns,
and drill-mapped feedback.

The app must remain local-PC-first and service-oriented. UI and API adapters must not
contain baseball thresholds, fault rules, scoring deductions, or drill decisions.

## Decision

Replace the normal swing evaluator with a v2 baseline model behind the existing
application-service and API boundaries.

The normal service path remains:

```text
pose observations or stored video
  -> phase alignment
  -> swing metric calculation
  -> rule evaluation and scoring
  -> feedback generation
  -> browser-safe response
```

The v2 domain model adds methodology metadata and uses these normal metrics:

* Normalized stance width
* Torso forward tilt
* Torso tilt preservation
* Grip loading vector
* Rear knee sway
* Head translation ratio
* Early connection angle
* Lead knee blocking index
* Hip-shoulder separation timing
* Estimated attack angle
* Follow-through posture and balance

The existing endpoints remain available for compatibility:

* `POST /api/v1/analysis/swing`
* `POST /api/v1/analysis/swing/video`

Responses now include `methodology_version: swing_evaluation_v2`. Metric responses also
include a unit string so browser clients can display v2 values without knowing baseball
rules.

Thresholds live in `SwingAnalysisConfig`. Values that are confirmed from the reference
PDF are used directly when practical, while formula-only thresholds that were not
reliably recoverable remain configurable and provisional until calibrated with validated
fixtures.

## Consequences

### Positive

* Normal swing results are clearly identified as v2 baseline evaluation.
* V2 scoring is based on a broader phase-aligned metric set from the baseline research.
* Existing local video, pose estimation, caching, diagnostics, API, and replay overlay
  workflows remain usable.
* UI and API adapters continue to serialize returned data without owning baseball rules.

### Negative

* Existing v1 metric names and exact deductions are no longer stable public semantics.
* Some thresholds remain provisional until visually verified from the PDF or calibrated
  with real fixtures.
* MediaPipe body pose still lacks bat tip, bat barrel, and ball evidence, so attack-angle
  confidence can remain limited for real videos.
