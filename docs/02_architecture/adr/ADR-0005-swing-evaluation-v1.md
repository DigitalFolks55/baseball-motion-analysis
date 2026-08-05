# ADR-0005: Swing Evaluation v1 Service Boundary

## Status

Accepted

## Context

DEV003-01 introduces the first swing motion evaluation workflow. The current product is
local-PC-first, and existing media/replay behavior already separates UI and API adapters
from application services. Swing evaluation must follow the same boundary: UI and future
API adapters should not contain baseball coaching rules, scoring logic, or feedback text
generation.

The first implementation analyzes already-available pose/keypoint time series. It does
not add a concrete pose-estimation model, report persistence, hosted web behavior, or UI
integration.

## Decision

Implement swing evaluation as a service-oriented pipeline:

```text
application service
  -> pose observation models
  -> motion swing phase and metric calculations
  -> analysis rule evaluation and scoring
  -> feedback report generation
  -> in-memory analysis result
```

Module responsibilities:

* `pose`: stable frame-level keypoint observation models with normalized 2D coordinates
  and confidence values.
* `motion`: swing handedness normalization, phase references, 2D geometry helpers, and
  swing metric calculations.
* `analysis`: configurable swing rule thresholds, fault detection, phase-weighted
  scoring, and confidence aggregation.
* `feedback`: cautious user-facing swing report generation and drill suggestions.
* `app`: `SwingAnalysisApplicationService` orchestration for callers that already have
  pose observations.

The v1 service supports caller-provided phase frame indexes and also provides a
conservative automatic fallback that selects representative ordered frames. Configurable
thresholds are used for metrics whose exact calibrated values are not yet established.
Bat tip / barrel points are optional; when absent, attack-angle confidence is reduced and
the limitation is included in the result.

## Consequences

### Positive

* Swing rules remain independent from UI, API, storage, video, and sequence modules.
* Tests can use deterministic synthetic keypoint sequences without real user videos.
* Future pose-estimation implementations can target a stable internal observation model.
* Feedback can explain uncertainty instead of overclaiming.

### Negative

* Automatic phase detection is intentionally conservative and should be improved with
  real calibration data later.
* Side-view 2D metrics cannot fully represent 3D swing mechanics.
* Attack-angle estimates are limited when bat keypoints are unavailable.
* Report persistence remains a separate task.
