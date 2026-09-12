# 2026-09-12 Fault-Aware Swing Scoring

Implemented DEV007-02 fault-aware swing scoring.

## Changes

* Added `ADR-0014: Fault-Aware Swing Scoring`.
* Updated swing analysis so Detected Faults can contribute bounded score deductions.
* Added linked metric metadata to fault results so metric-backed faults are credited
  before any additional fault deduction is applied.
* Added phase-level metric and fault deduction fields to phase scores.
* Serialized the new score-impact fields through the API.
* Updated the browser result table and Detected Faults text to render returned score
  impact data without calculating scoring rules.
* Added deterministic unit, application-service, API, and static UI regression tests.

## Notes

Metric deductions are still the primary score mechanism. Fault deductions are capped by
phase, severity, and confidence, then reduced by linked metric deductions to avoid
uncontrolled double counting. Secondary evidence such as wrist-to-chest distance or
lead-knee forward drift can now lower the score when it triggers a supported fault.

No release or deployment was created.
