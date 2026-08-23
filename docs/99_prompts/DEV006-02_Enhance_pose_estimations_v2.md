# DEV006-02 Enhance Pose Estimations v2

## Objective

Recover and improve swing pose/event quality after DEV006-01. Treat body pose estimation quality and swing event detection quality as related but separate problems:

1. Compare the original/pre-DEV006 pose-estimation behavior against the current DEV006-01 behavior. If the original logic is better, revert the degraded pose-estimation changes. If any DEV006-01 improvements are confirmed, keep or update only those parts.
2. Revise swing event detection so setup, stride, foot strike, impact, and follow-through are selected from baseball-motion semantics instead of incidental movement or fallback ordering.

Do not create a release or deployment.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Complete implementation, tests, documentation, and verification. Do not stop after planning.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/99_prompts/DEV006-01_Enhance_pose_estimations.md`
- `docs/04_motion_knowledge/swing.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/ADR-0007-swing-analysis-service.md`
- `docs/02_architecture/adr/ADR-0008-web-video-upload-replay.md`
- `docs/02_architecture/adr/ADR-0009-web-image-sequence-upload-replay.md`
- `docs/02_architecture/adr/ADR-0011-swing-pose-estimation.md`
- `docs/02_architecture/adr/ADR-0012-enhanced-swing-pose-diagnostics.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Review relevant implementation and tests:

- `src/baseball_motion_analysis/pose/`
- `src/baseball_motion_analysis/motion/swing.py`
- `src/baseball_motion_analysis/analysis/swing.py`
- `src/baseball_motion_analysis/app/swing_services.py`
- `src/baseball_motion_analysis/api/schemas.py`
- `src/baseball_motion_analysis/api/swing_router.py`
- `src/baseball_motion_analysis/ui/web/static/app.js`
- `tests/unit/test_pose_estimation.py`
- `tests/unit/test_swing_motion_metrics.py`
- `tests/unit/test_swing_analysis.py`
- `tests/integration/test_swing_application_service.py`
- `tests/integration/test_swing_video_analysis_api.py`
- `tests/integration/test_web_video_upload_replay_api.py`

## Current Regression Hypotheses

Investigate these suspected causes before deciding what to keep or revert:

- Setup detection may be worse because the active swing window can trim away the true setup frame. Setup should usually come from a stable pre-motion period, not from inside an already-active window.
- Stride and impact cues may be too dependent on grip/wrist movement. Small hand waggle or camera jitter can dominate stride and impact scoring even when lower-body events are not present.
- Foot strike currently risks selecting from all frames instead of only quality-filtered candidate frames, so weak or rejected frames may still become events.
- Foot strike may measure lead ankle displacement from `frames[0]` instead of the detected setup baseline.
- Foot strike should identify lead foot plant/stabilization after stride, not simply maximum ankle displacement.
- Impact selection may be biased too late in the sequence by a hard late-window preference and may choose post-contact frames.
- Follow-through may be selected as `impact + 1` or `foot_strike + 1`, which is ordered but not semantically meaningful.
- `_ordered_unique_positions` may hide poor detection by forcibly shifting phase indexes instead of surfacing fallback reasons and lower confidence.

## Scope

### Pose-Estimation A/B Audit

Establish a deterministic comparison between the original/pre-DEV006 pose-estimation behavior and the current DEV006-01 behavior.

Required checks:

- Compare raw pose output, candidate selection, candidate switching, smoothing, interpolation, and frame-quality classification.
- Use deterministic fake MediaPipe outputs and local tiny fixtures only. Do not commit user videos, large videos, model weights, or generated reports.
- Identify whether DEV006-01 candidate switch rejection, ambiguity handling, temporal smoothing, fast-keypoint preservation, interpolation, or quality labels degraded pose quality.
- Revert degraded pose-estimation changes to original behavior when original behavior is better.
- Keep or revise only improvements that are confirmed by tests and documented behavior.
- Preserve public API compatibility where possible. If a response contract must change, update schemas, docs, tests, and UI handling together.

### Swing Event Detection Revision

Revise event detection in `src/baseball_motion_analysis/motion/swing.py`. Treat event detection as motion-domain logic, not pose-estimator logic.

Required behavior:

- `setup`: choose a stable pre-motion frame before active swing start when available. Do not restrict setup to the active swing window.
- `stride`: prioritize lower-body loading and stride indicators such as lead ankle, lead knee, rear hip, pelvis, and head movement. Reduce wrist/grip dominance. Use handedness-aware logic if the existing data supports it.
- `foot_strike`: use the detected setup frame as the baseline, select only quality-accepted candidate frames, and detect lead foot plant/stabilization or velocity drop after stride. Do not select rejected frames. Do not define foot strike as maximum ankle displacement.
- `impact`: remove hard late-window bias. Prefer a constrained local event using hand path, torso-front crossing, local hand speed, body rotation, and event ordering. Continue to label this as estimated impact because the current system does not detect bat/ball contact.
- `follow_through`: detect a meaningful post-impact frame using hand extension, deceleration, posture, and balance cues. Do not simply choose the immediate next frame.
- Phase ordering should remain valid, but ordering repair must include explicit fallback reasons and lower confidence rather than hiding weak detections.
- Per-event confidence and fallback reasons must be available to application/API/UI diagnostics.

## Non-Goals

- Do not implement bat or ball detection.
- Do not implement full swing coaching or scoring redesign beyond what event detection requires.
- Do not change fielding, throwing, or pitching logic unless a shared utility requires a narrowly scoped update.
- Do not introduce a hosted service, cloud upload, mobile adapter, Docker deployment, production deployment, or release.
- Do not add production dependencies without explaining need, alternatives, runtime impact, and license/packaging concerns.

## Architecture Requirements

- Keep pose extraction under `pose`.
- Keep swing phase/event detection under `motion`.
- Keep rule scoring under `analysis`.
- Keep application orchestration under `app`.
- UI and API layers must call application services, not low-level pose or motion functions directly.
- Diagnostics should expose enough detail for debugging while avoiding private file-path leakage.
- Any new configuration should be explicit, typed, and documented. Prefer conservative defaults that match the best-confirmed behavior.

If behavior or boundaries change materially, add or update an ADR under `docs/02_architecture/adr/`.

## Testing Requirements

Add or update deterministic tests covering:

- Original-vs-current pose post-processing comparison, including candidate switching, smoothing, interpolation, and low-confidence handling.
- Reversion of any DEV006-01 pose-estimation logic that is shown to be worse than original behavior.
- `setup` selected from stable pre-motion frames instead of the active-only window.
- `stride` not triggered by wrist waggle alone.
- `foot_strike` uses the detected setup baseline.
- `foot_strike` cannot select frames excluded by quality filtering.
- `foot_strike` prefers plant/stabilization after stride over maximum displacement.
- `impact` is not pushed to a late post-contact frame solely by late-window bias.
- `follow_through` is not automatically the frame immediately after impact.
- Fallback reasons and confidence are reported for weak or repaired phase selections.
- Application-service and API responses remain backward compatible or are updated consistently with schema/UI/docs.

Tests must not require real user videos, external services, credentials, or heavy binary fixtures.

## Documentation Requirements

Update all relevant docs:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/` if behavior or boundaries change materially
- `docs/03_development_log/` with a dated entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md` if user-visible diagnostics or behavior changes

Documentation must clearly state:

- Which DEV006-01 pose-estimation changes were reverted, retained, or revised.
- Why the chosen pose-estimation behavior is better.
- How each swing event is detected after this revision.
- Known limitations, especially that impact remains estimated without bat/ball contact detection.

## Quality Gates

Run these checks after coding:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed, run:

```bash
uv run ruff format .
```

## Acceptance Criteria

- A/B audit between original/pre-DEV006 and current DEV006-01 pose-estimation behavior is completed and documented.
- Any pose-estimation logic that is worse than the original behavior is reverted or gated off by default.
- Any retained pose-estimation improvement has deterministic tests and documentation.
- Event detection is revised for setup, stride, foot strike, impact, and follow-through using baseball-motion semantics.
- Event detection no longer selects setup only from an active swing window, foot strike from rejected frames, foot strike from the wrong baseline, impact from hard late bias, or follow-through as a trivial next-frame fallback.
- Event confidence and fallback reasons are explicit enough for diagnostics.
- Relevant docs are updated.
- All quality gates pass.
- Final review confirms no blocking issues and no release/deployment was created.
