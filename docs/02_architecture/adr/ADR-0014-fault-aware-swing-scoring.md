# ADR-0014: Fault-Aware Swing Scoring

## Status

Accepted

## Context

DEV007-02 changes swing v2 scoring so Detected Faults are explicitly score-relevant.
Before this decision, analysis evaluated metric deductions, detected faults from those
metrics plus selected secondary evidence, and then computed phase scores from metrics
only. Detected Faults affected feedback, improvement priorities, drills, and browser
display, but they did not directly affect `phase_scores` or `overall_score`.

That created a mismatch for secondary fault evidence that is not represented as a scored
metric. For example, wrist-to-chest distance can trigger door swing / casting, and
lead-knee forward drift can trigger collapsed lead side, even when the linked metrics
are otherwise acceptable. Those faults should be visible in the score without moving
baseball scoring rules into UI or API adapters.

The app must remain local-PC-first and service-oriented. UI and API layers must only
serialize or render returned score data.

## Decision

Use a fault-aware phase scoring model in `analysis`.

The score remains a 0 to 100 phase-weighted score:

```text
metrics
  -> metric deductions
fault detection
  -> linked metrics + secondary evidence
  -> capped fault deductions
phase score
  -> 100 - metric deduction - fault deduction
overall score
  -> weighted phase scores
```

Each `SwingFaultResult` now carries:

* `deduction`: the fault's additional overall-score-point deduction.
* `linked_metrics`: the metrics that already explain some or all of the fault.

Each `SwingPhaseScore` now carries:

* `metric_deduction`: phase-local score points lost to metric deductions.
* `fault_deduction`: phase-local score points lost to additional fault deductions.

Metric deductions are credited first. A detected fault gets a severity- and
confidence-scaled phase cap, then subtracts the score already lost by linked metrics in
that same phase. Only the uncovered remainder becomes `fault.deduction`.

Default caps are configurable in `SwingAnalysisConfig`:

* warning fault cap: 20% of the phase point budget, scaled by confidence
* severe fault cap: 35% of the phase point budget, scaled by confidence

This means a metric-backed fault does not receive an uncontrolled duplicate penalty. If
the linked metrics already deducted more than the fault cap, the fault remains visible
but adds `0.0` extra deduction. If secondary evidence triggers a fault while linked
metrics are otherwise good, the fault can add a bounded deduction.

Fault confidence is calculated from evidence that actually triggered the fault:

* problematic linked metrics contribute their metric confidence
* triggered secondary evidence contributes its measurement confidence
* good linked metrics do not mask weak secondary evidence

Skipped or unavailable impact keeps suppressing impact-phase faults. Suppressed faults
do not add hidden fault deductions.

## Consequences

### Positive

* Detected Faults now have an explicit, testable score relationship.
* Secondary evidence such as wrist-to-chest distance and lead-knee forward drift can
  affect score without becoming UI-owned scoring logic.
* Metric-backed faults are capped and credited against existing metric deductions, which
  prevents uncontrolled double counting.
* API and browser clients can explain metric versus fault deductions without calculating
  baseball rules.
* Feedback, drills, detected faults, phase scores, and overall score tell a more
  consistent story.

### Negative

* API responses include additional scoring fields that clients may choose to display.
* Some previous scores can decrease when a fault is triggered by secondary evidence that
  had no metric deduction before DEV007-02.
* Fault caps are still provisional and need calibration with validated swing fixtures.

## Follow-Ups

* Calibrate fault caps with annotated non-private swing fixtures.
* Consider a future score explanation object if more motion types adopt fault-aware
  scoring.
