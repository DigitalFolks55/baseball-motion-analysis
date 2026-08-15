# 2026-08-12 Swing Evaluation v2

## Summary

Implemented DEV004-01 planning, architecture, coding, QA, and final-review preparation
for replacing normal swing analysis with the v2 youth baseball 2D side-view baseline
methodology.

## Changes

* Added v2 methodology metadata to swing analysis results.
* Replaced the normal v1 metric set with v2 baseline metrics:
  normalized stance width, torso forward tilt, torso tilt preservation, grip loading,
  rear knee sway, head translation, early connection, lead knee blocking,
  hip-shoulder separation timing, estimated attack angle, and follow-through posture.
* Updated rule evaluation, phase-weighted scoring, detected error evidence, and
  improvement-priority selection for the v2 baseline.
* Updated feedback drill mappings to the v2 youth-friendly correction protocols.
* Updated API serialization with methodology version and metric units.
* Updated the browser result table to display methodology and metric units.
* Added ADR-0009 for the v2 replacement decision.

## Validation

Quality commands were run after implementation:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Remaining Risks

* Some formula-only thresholds from the baseline PDF remain configurable and provisional
  until visually verified or calibrated with validated fixtures.
* MediaPipe body pose still does not provide bat tip, bat barrel, or ball evidence.
* Automatic event detection is motion-aware but heuristic.

## DEV004-02 Overlay Evaluation Lines

Implemented optional swing v2 evaluation-line overlays for stored-video analysis.

Changes:

* Added browser-neutral evaluation-line primitives at the swing video application
  service boundary.
* Serialized evaluation lines through `/api/v1/analysis/swing/video` as
  `evaluation_overlay`.
* Added an `Evaluation Lines` toggle immediately to the left of the replay `Speed`
  control.
* Rendered returned lines on the existing letterbox-aware replay canvas without
  changing pose keypoints, event labels, raw/stabilized overlay source behavior, speed,
  frame stepping, or analysis execution.
* Added ADR-0010 for the service/API overlay-line contract.

Validation added:

* Unit tests for evaluation-line construction, missing-keypoint skips, and low-confidence
  grip-path fallback attack-angle lines.
* Integration/static tests for stored-video service output, API serialization, UI button
  placement, and JavaScript toggle/rendering behavior.

Remaining risks:

* Evaluation lines are visual aids over the sampled pose evidence and inherit pose
  sampling and event-detection uncertainty.
* MediaPipe body landmarks still do not provide bat or ball evidence; grip-path fallback
  attack-angle lines remain lower confidence until future detectors are added.

## DEV004-03 UI Update

Implemented the swing v2 replay UI follow-up.

Changes:

* Made the `Video Library` list scrollable for long local libraries.
* Added an independent `Poses` toggle before `Evaluation Lines`, preserving the toolbar
  order `Poses | Evaluation Lines | Speed`.
* Kept `Poses` on by default after analysis returns pose overlay data and disabled before
  overlay data exists.
* Disabled pose keypoint text tags during replay while preserving pose skeletons,
  keypoint circles, event labels, and evaluation-line labels.
* Improved overlay status text so active overlay modes are distinguishable.
* Verified the evaluation-line builder returns all required swing v2 metric categories
  when complete synthetic evidence exists.
* Added follow-through posture evidence to the follow-through evaluation overlay output.

Validation added:

* Unit coverage for all required evaluation-line metric categories.
* Integration/API coverage that stored-video analysis serializes every returned
  evaluation-line category without exposing local paths.
* UI/static coverage for scrollable library styling, toolbar order, independent overlay
  toggles, disabled pose tags, replay speed preservation, and overlay rendering hooks.

Remaining risks:

* Evaluation lines remain visual aids over sampled pose evidence and can still inherit
  sparse-sampling, event-detection, and MediaPipe landmark uncertainty.
* Bat and ball evidence is still unavailable unless future detectors add those
  keypoints.
