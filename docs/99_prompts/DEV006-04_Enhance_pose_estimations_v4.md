# DEV006-04 Enhance Pose Estimations v4

## Objective

Improve swing event detection quality after DEV006-03 user review. The remaining issue is
that stride, foot strike, and follow-through are still selected mostly as independent
candidate frames. Revise event detection into a more explicit ordered swing-state model
so stride and foot strike depend on observable lead-leg lift/plant behavior, impact can
be clearly disabled for no-ball videos, and follow-through represents the end of the
swing rather than idle motion after the swing.

Preserve the local-PC-first, service-oriented architecture. Complete implementation,
tests, documentation, and verification. Do not create a release or deployment.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Do not stop after planning.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/99_prompts/DEV006-01_Enhance_pose_estimations.md`
- `docs/99_prompts/DEV006-02_Enhance_pose_estimations_v2.md`
- `docs/99_prompts/DEV006-03_Enhance_pose_estimations_v2.md`
- `docs/04_motion_knowledge/swing.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/ADR-0012-enhanced-swing-pose-diagnostics.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Review relevant implementation and tests:

- `src/baseball_motion_analysis/motion/swing.py`
- `src/baseball_motion_analysis/analysis/swing.py`
- `src/baseball_motion_analysis/app/swing_services.py`
- `src/baseball_motion_analysis/api/schemas.py`
- `src/baseball_motion_analysis/api/swing_router.py`
- `src/baseball_motion_analysis/ui/web/templates/index.html`
- `src/baseball_motion_analysis/ui/web/static/app.js`
- `tests/unit/test_swing_motion_metrics.py`
- `tests/unit/test_swing_analysis.py`
- `tests/integration/test_swing_application_service.py`
- `tests/integration/test_swing_video_analysis_api.py`
- `tests/integration/test_web_video_upload_replay_api.py`

## Current Findings

Address these user-observed issues:

- `stride`: a frame where one leg is up should be considered stride evidence, but the
  current detector can select an earlier frame even when the lead leg is visibly up on a
  later frame.
- `foot_strike`: the current detector can select foot strike even when the leg was not
  previously up. Later frames may show the actual leg lift and subsequent plant.
- `impact`: videos without a visible ball still produce poor body-pose-only impact
  estimates. The UI needs a clear enable/disable control for impact detection, not only a
  hidden advanced policy dropdown.
- `follow_through`: follow-through should represent the swing finish/end. Current
  selection can drift into frames where swing motion has already stopped and the player
  is idle or resetting.

## Scope

### Ordered Swing-State Event Model

Revise automatic event detection from mostly independent frame scoring to a small ordered
state model:

```text
setup
  -> lead_leg_lift_onset / stride
  -> lead_leg_lift_peak
  -> lead_foot_descent
  -> foot_strike / plant
  -> optional impact
  -> follow_through_finish
```

Keep this model inside the `motion` module. App, API, and UI layers may pass options and
render returned metadata, but they must not implement baseball event rules.

The implementation does not need to expose every internal state as a public phase, but
it should use the states internally so foot strike cannot be confidently selected before
real stride/leg-lift evidence exists.

### Stride / Lead-Leg Lift Detection

Add explicit lead-leg lift detection.

Required behavior:

- Use handedness when available to identify the lead side; otherwise infer lead side from
  stride direction or pre-impact foot movement.
- Measure lead ankle vertical lift relative to setup baseline.
- Use lead knee vertical movement and/or knee flexion as secondary evidence.
- Detect one or both of:
  - `lead_leg_lift_onset`: first sustained frame where the lead foot begins lifting.
  - `lead_leg_lift_peak`: highest visible lead-foot lift before descent.
- Select the public `stride` frame according to a documented mode. Prefer one default:
  - `leg_lift_peak` if the user expectation is "stride when one leg is up".
  - `leg_lift_onset` only if coaching semantics require the start of stride.
- If no leg lift exists, support a lower-confidence fallback for no-stride hitters, such
  as lower-body forward-load onset, and report a clear fallback reason.
- Do not select stride from wrist/grip movement alone.

### Foot Strike Depends On Prior Leg Lift

Make foot strike detection depend on validated stride/leg-lift evidence.

Required behavior:

- Do not confidently detect foot strike unless the lead foot was previously lifted or a
  documented no-stride fallback is active.
- After leg lift, detect lead-foot descent and first plant/stabilization.
- Require meaningful lead-foot lift above setup baseline before plant when frame density
  allows.
- Select foot strike as the first frame where the lead foot returns near the ground/setup
  level and velocity stays low for 2-3 sampled frames when enough frames exist.
- Avoid selecting a planted setup frame as foot strike before the leg lift.
- If the sequence is too sparse to show lift/descent/plant, return lower confidence and
  a fallback reason such as `foot_strike_sparse_or_no_prior_lift`.

### Impact Enable / Disable UI

The backend already has impact policy options. Improve the browser UX so users can
clearly choose whether impact detection is enabled.

Required behavior:

- Add a visible, primary swing-analysis control for impact detection:
  - `Impact Detection: On / Off`, or equivalent.
- Map `On` to `body_pose_estimated`.
- Map `Off` to `skip_without_ball`.
- Keep `require_ball_contact` available only if still useful for API/advanced workflows,
  but the normal UI should make the no-ball choice obvious.
- Consider defaulting the UI to `Off` if no ball/contact evidence is expected in most
  videos. If preserving current default is safer, document the decision.
- Changing the impact control should clear stale analysis results before the next run.
- Event rows should visibly show `estimated`, `skipped`, or `unavailable` status.
- If impact is skipped/unavailable, avoid making the replay overlay imply exact contact.

Do not implement ball, bat, barrel, or contact detection in this task.

### Follow-Through As Swing Finish

Revise follow-through selection so it represents swing finish/end, not idle frames after
the swing.

Required behavior:

- Search after estimated impact, or if impact is skipped, after foot strike plus
  rotational/hand-acceleration evidence.
- Limit the search to the active swing window end plus a small configurable or documented
  buffer. Do not search the entire remaining clip by default.
- Use sampled timestamps when available, or frame-count fallback when timestamps are not
  available, to cap the post-impact/post-foot-strike search window.
- Detect finish from:
  - peak hand/grip extension or peak torso/shoulder rotation,
  - followed by extension plateau or deceleration,
  - with posture still related to the swing.
- Prefer the first stable finish frame after peak extension/rotation.
- Penalize frames where the player has returned to idle, started walking/resetting, or
  shows large whole-body translation unrelated to the swing.
- If the finish is outside sampled frames, return lower confidence and a fallback reason
  instead of blindly selecting the final frame.

## Non-Goals

- Do not implement ball, bat, barrel, or contact detection.
- Do not add hosted services, cloud upload, telemetry, release/deployment work, Docker,
  PyPI publishing, or mobile adapters.
- Do not change fielding, throwing, or pitching behavior.
- Do not commit videos, model weights, secrets, generated reports, or heavy fixtures.
- Do not move baseball rules into UI, API routes, storage, video, or pose modules.
- Do not perform broad swing scoring or threshold redesign beyond changes required to
  handle skipped/unavailable impact and event confidence correctly.

## Architecture Requirements

- Keep ordered event semantics in `motion`.
- Keep application orchestration and request defaults in `app`.
- Keep API serialization in `api`.
- Keep UI logic rule-free; it may render controls and returned event status, confidence,
  detection method, and fallback reason.
- Keep pose extraction under `pose`; do not add swing phase rules to pose estimation.
- Preserve backward compatibility for app/API callers where practical.
- If event metadata changes materially, update ADR-0012 or add a new ADR under
  `docs/02_architecture/adr/`.

## Testing Requirements

Add deterministic tests with small pose fixtures. Tests must not require real user
videos, external services, credentials, or heavy binary fixtures.

Required unit tests:

- Stride selects the leg-up frame or configured leg-lift event when the lead leg lifts
  later than initial lower-body motion.
- Stride does not trigger from wrist/grip motion alone.
- Stride reports a lower-confidence no-stride fallback when no leg lift exists.
- Foot strike is not confidently detected before prior lead-leg lift.
- Foot strike selects the first stable plant after lift/descent.
- Foot strike reports lower confidence when sampling is too sparse to observe
  lift/descent/plant.
- Follow-through selects swing finish before idle/walking/reset frames.
- Follow-through reports lower confidence when the finish appears outside sampled frames.
- Impact disabled policy keeps impact-dependent metrics not evaluated and does not emit
  impact-phase faults from a proxy frame.

Required integration/API/UI tests:

- App-service video analysis passes the selected impact policy and returns event status.
- API `/api/v1/analysis/swing/video` accepts the impact enable/disable behavior and
  serializes event status/fallback reasons.
- Browser UI contains the visible impact detection control, sends the expected
  `impact_detection_policy`, and clears stale results when the control changes.
- Static UI tests confirm event status text remains visible in results.

## Documentation Requirements

Update all relevant docs:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/` if the event model changes materially
- `docs/03_development_log/` with a dated entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must clearly state:

- how stride/leg lift is detected.
- how foot strike depends on prior leg lift or no-stride fallback.
- how the impact enable/disable UI maps to backend policy.
- how follow-through finish is bounded to avoid idle post-swing frames.
- known limitations, especially that bat/ball/contact evidence is still not detected.

## Quality Gates

Run these checks after coding:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

All quality gates must pass before final review.

## Acceptance Criteria

- Stride can align with visible lead-leg lift instead of earlier unrelated movement.
- Foot strike is not confidently selected before a prior lead-leg lift or documented
  no-stride fallback.
- The browser UI has a clear impact detection enable/disable control.
- Disabling impact maps to skipped impact behavior and prevents impact-dependent scoring
  from using a proxy contact frame.
- Follow-through represents swing finish/end and avoids idle or reset frames after the
  swing.
- Event confidence, status, detection method, and fallback reason remain visible through
  app/API/UI responses.
- Deterministic unit and integration tests cover the revised behavior.
- Required docs are updated.
- Required quality gates pass.
- No release or deployment is created.
