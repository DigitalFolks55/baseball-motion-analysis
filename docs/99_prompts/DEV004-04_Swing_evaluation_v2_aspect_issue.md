# DEV004-04 Swing Evaluation v2 Aspect Issue

## Goal

Fix the swing evaluation v2 aspect-ratio measurement issue so geometry-based metrics use
consistent physical image coordinates instead of mixing independently normalized `x` and
`y` pose coordinates.

This task should correct measurement accuracy, update affected overlay line coordinates as
needed, and verify that all impacted swing v2 metrics remain deterministic and
browser-renderable.

This is not a release or deployment task.

## Background

The current swing v2 implementation appears to calculate several distances and angles
directly from MediaPipe-style normalized pose coordinates:

```text
x: normalized by image width
y: normalized by image height
```

Using Euclidean distance or angle math directly on these mixed normalized axes is
geometrically incorrect when the source video is not square. For example, a stance-width
line that visually looks close to one torso length may be reported around `0.6` because
horizontal and vertical units are not on the same scale.

The fix should make measurement logic aspect-aware while preserving the existing
service-oriented architecture and browser-neutral analysis contracts.

## Requested Changes

Implement these product and technical changes:

1. Audit all swing evaluation v2 metrics that use pose geometry.
2. Introduce a clear coordinate-space policy for swing measurement math.
3. Correct aspect-ratio-sensitive distance, vector, and angle calculations.
4. Ensure evaluation overlay lines still render in the correct video positions.
5. Add tests proving metrics are stable and correct for non-square video dimensions.
6. Update documentation to explain the coordinate-space rule and affected metrics.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV004-01_Swing_evaluation_v2.md`
* `docs/99_prompts/DEV004-02_Swing_evaluation_v2_overlay_evaluation_lines.md`
* `docs/99_prompts/DEV004-03_Swing_evaluation_v2_UI_update.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/01_product/feature_catalog.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
* `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
* `docs/02_architecture/adr/ADR-0010-swing-evaluation-overlay-lines.md`
* `docs/05_manuals/swing_motion_analysis_ui.md`
* Existing implementation:
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
* Existing tests:
  * `tests/unit/test_swing_evaluation_overlay_lines.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_swing_video_analysis_api.py`
  * Any existing swing motion unit tests under `tests/`

## Required Agent Workflow

Follow the repository workflow in order:

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
```

Do not run the release agent. Do not create a release, deployment, Docker setup, hosted
web service, PyPI package, version tag, or changelog release entry.

## Current Findings

The likely issue is that swing evaluation uses normalized pose coordinates directly for
Euclidean distances, vector magnitudes, and angle calculations.

This can affect metrics such as:

* `normalized_stance_width`
* `torso_forward_tilt`
* `torso_tilt_preservation`
* `grip_loading_vector`
* `rear_knee_sway`
* `head_translation_ratio`
* `early_connection_angle`
* `lead_knee_blocking_index`
* `estimated_attack_angle`
* `follow_through_posture_balance`

`hip_shoulder_separation_timing` may be less directly affected if it compares relative
ordering or timing only, but any axis angle or vector evidence used by that metric must
still be audited.

## Required Outcomes

### 1. Coordinate-Space Policy

Define and implement one consistent policy for measurement math.

Required behavior:

* Do not calculate physical distances or angles by directly mixing raw normalized `x` and
  `y` coordinates.
* Convert pose points to a common measurement coordinate space before geometric math.
* Prefer pixel-space coordinates when frame width and height are known.
* If pixel dimensions are unavailable, use an explicit fallback that preserves existing
  behavior and marks the confidence or limitation clearly where practical.
* Keep UI rendering coordinates browser-friendly. Overlay output may still use normalized
  coordinates if the frontend expects normalized coordinates, but measurement math must be
  aspect-aware.

Acceptable implementation approaches include:

* Convert normalized keypoints to pixel coordinates using frame width and height before
  computing distances, vectors, slopes, and angles.
* Or convert normalized points to an aspect-correct unit coordinate space where `x` is
  scaled by aspect ratio before geometric calculations.

The chosen approach must be documented.

### 2. Metric Audit And Fixes

Audit every swing v2 metric and fix each affected calculation.

Required behavior:

* Stance width should compare ankle distance against torso length in the same coordinate
  space.
* Torso tilt should use an aspect-aware torso vector from hip midpoint to shoulder
  midpoint.
* Tilt preservation should compare torso angles or vectors in the same coordinate space
  across frames.
* Grip loading vector should use aspect-aware vector magnitude and direction.
* Rear knee sway should use aspect-aware lateral displacement and support references.
* Head translation ratio should compare head movement and body scale in the same
  coordinate space.
* Early connection angle should calculate joint/vector angles in the same coordinate
  space.
* Lead knee blocking should calculate knee/leg segment geometry in the same coordinate
  space.
* Hip and shoulder axis evidence should be checked for aspect-aware angle display or
  calculation.
* Attack angle or grip-path fallback should calculate the path angle in the same
  coordinate space.
* Follow-through posture and balance should use aspect-aware torso/head displacement math.

Do not change v2 coaching concepts, scoring categories, deduction names, drill mapping, or
feedback wording unless required to describe corrected measurement semantics.

### 3. Data Contract And Metadata

Ensure the analysis layer has access to video or frame dimensions when needed.

Required behavior:

* Identify where frame width and height are available in the current pipeline.
* Pass dimensions through application-service boundaries without making UI callbacks
  calculate baseball mechanics.
* Keep pose extraction independent from swing scoring.
* Avoid changing persisted media records unless needed.
* Avoid adding a production dependency unless there is a clear need.

If dimensions cannot be supplied in some workflows, handle that path explicitly in code
and tests.

### 4. Evaluation Overlay Lines

Keep evaluation overlay line rendering correct after measurement fixes.

Required behavior:

* Overlay line start/end points should still map onto the video correctly.
* Evaluation-line labels should still be produced.
* The `Evaluation Lines` toggle should continue to control evaluation lines only.
* The `Poses` toggle should continue to control pose skeleton/keypoint display only.
* Do not reintroduce pose keypoint text tags.
* Do not fabricate bat, ball, barrel, or bat-tip keypoints.

### 5. Tests

Add or update deterministic tests for aspect-ratio correctness.

Required test coverage:

* A non-square frame, such as `1920x1080` or `1280x720`, where raw normalized math would
  produce a different answer than aspect-aware math.
* `normalized_stance_width` using ankle distance and torso length in the same coordinate
  space.
* At least one aspect-sensitive angle metric, such as torso tilt or attack angle.
* At least one aspect-sensitive displacement metric, such as head translation or rear knee
  sway.
* Overlay-line generation still returns labels and normalized render coordinates.
* Existing API serialization tests still pass.
* Missing or unknown dimensions are handled without crashing.

Tests must not require real user videos or large binary assets.

### 6. Documentation

Update documentation where behavior or architecture changes.

Required documentation updates:

* `PLANS.md` status or notes for DEV004-04.
* `docs/01_product/feature_catalog.md` if user-visible swing evaluation behavior is
  described there.
* `docs/04_motion_knowledge/swing.md` to explain that geometric swing metrics are
  calculated in aspect-aware image coordinates.
* `docs/03_development_log/` with an Obsidian-compatible development log entry.
* An ADR under `docs/02_architecture/adr/` if the coordinate-space policy changes a
  service contract or becomes a durable architectural decision.

## Architecture Requirements

Keep existing boundaries:

* `motion` owns swing metric calculations and coordinate-space helpers.
* `app` passes media/frame context into motion evaluation and converts analysis evidence
  into browser-neutral overlay primitives.
* `api` serializes analysis results and overlay primitives only.
* `ui` displays overlay primitives and must not calculate swing metric values.
* `pose` owns keypoint extraction and should not contain swing scoring rules.
* `video` and `sequence` may provide frame dimensions and metadata, but must not contain
  swing evaluation rules.

Prefer a small typed helper or value object for coordinate conversion if it avoids
duplicating aspect-ratio correction logic across metrics.

## Acceptance Criteria

The task is complete only when:

* Swing v2 geometric metrics no longer use mixed raw normalized coordinates for distances
  or angles when frame dimensions are available.
* Non-square-frame tests prove the corrected calculations differ from the previous broken
  raw-normalized behavior where appropriate.
* `normalized_stance_width` uses a same-space ankle distance and torso length.
* Other affected measures are audited and either fixed or explicitly documented as not
  affected.
* Evaluation overlay lines and labels still render through the existing frontend contract.
* Pose overlay labels remain disabled.
* `Evaluation Lines` and `Poses` toggles continue to work independently.
* Documentation and `PLANS.md` are updated.
* The required quality commands pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Risks And Constraints

* Correcting measurement geometry may change existing scores and feedback for the same
  video. This is expected if prior values were distorted by aspect ratio.
* Historical tests that assumed raw normalized math should be updated to assert the
  corrected behavior.
* Some videos may not expose reliable dimensions; those cases must remain stable and
  explainable.
* MediaPipe body pose does not provide bat or ball tracking by default. Do not imply that
  bat tip, barrel, or ball location is detected unless an explicit keypoint source exists.
* Keep this local-PC-first. Do not upload videos, images, pose data, or reports to external
  services.

## Final Review Checklist

Before final response, confirm:

* The implementation followed `planning -> architecture -> coding -> quality-assurance ->
  final-review-planning`.
* All affected metrics were audited.
* Tests cover non-square aspect-ratio behavior.
* Overlay labels and toggles were not regressed.
* Documentation was updated.
* Required quality commands passed, or any failure is clearly reported with the reason.
* No release or deployment work was performed.
