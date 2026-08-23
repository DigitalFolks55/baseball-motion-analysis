# DEV006-03 Enhance Pose Estimations v2

## Objective

Improve swing event detection quality after DEV006-02. The main remaining problem is not
raw pose estimation quality alone; it is that setup, stride, foot strike, impact, and
follow-through are still selected by heuristics that can drift late or cascade from an
earlier incorrect event.

This task should revise event semantics while preserving the local-PC-first,
service-oriented architecture. Do not create a release or deployment.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Complete implementation, tests,
documentation, and verification. Do not stop after planning.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/99_prompts/DEV006-01_Enhance_pose_estimations.md`
- `docs/99_prompts/DEV006-02_Enhance_pose_estimations_v2.md`
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
- `src/baseball_motion_analysis/ui/web/static/app.js`
- `tests/unit/test_swing_motion_metrics.py`
- `tests/unit/test_swing_analysis.py`
- `tests/integration/test_swing_application_service.py`
- `tests/integration/test_swing_video_analysis_api.py`
- `tests/integration/test_web_video_upload_replay_api.py`

## Current Findings

Investigate and address these observed event-detection issues:

- `setup`: should usually be an early stable frame, but current detection can pick a
  later frame after the swing has already started.
- `stride`: depends on setup; when setup is late, stride becomes late or too close to
  setup.
- `impact`: current body-pose-only estimated impact is always returned. Add an explicit
  option for whether impact should be estimated from body pose, require ball/contact
  evidence, or be skipped when ball/contact evidence is unavailable.
- `foot_strike`: sometimes the foot is already landed, but a later frame is selected.
  Current scoring can still prefer later displacement or drift over the first plant.
- `follow_through`: should represent the end/finish of the swing, but current scoring
  can pick a later unrelated frame when extension evidence is weak.

## Scope

### Event Detection Configuration

Add an explicit, typed event-detection configuration owned by the motion/app boundary.
Use conservative defaults that preserve current runnable behavior unless the user selects
another option.

Required option:

```text
impact_detection_policy:
  body_pose_estimated
  require_ball_contact
  skip_without_ball
```

Expected behavior:

- `body_pose_estimated`: current product default. Choose an estimated impact window from
  body-pose cues and clearly label it as estimated.
- `require_ball_contact`: do not select impact unless bat/ball/contact evidence exists.
  Because the app does not currently detect ball/contact, return impact as unavailable
  or low-confidence skipped evidence with an explicit reason.
- `skip_without_ball`: skip impact-dependent event selection when contact evidence is not
  available. Impact-dependent metrics should be skipped or downgraded with explicit
  limitations instead of using a guessed frame.

If the existing `SwingPhaseFrames` model cannot represent unavailable impact safely,
design the smallest compatible model change and update app/API/UI/docs/tests together.

### Setup Detection

Setup detection should not depend entirely on the active-window start.

Required behavior:

- Prefer the earliest stable high-quality stance frame in the early part of the clip.
- Use a short stability window over lower body, hips, shoulders, head, and grip.
- Do not break stability ties toward later frames when an earlier valid setup exists.
- If the player is already moving from the first usable frame, report
  `setup_unavailable_or_late` or equivalent fallback reason with lower confidence.
- Do not choose setup from frames where lower-body stride/load has already begun unless
  no earlier usable stance exists.

### Stride Detection

Stride should be a load/stride onset event, not simply the next frame after setup.

Required behavior:

- Detect first sustained lead-foot, lead-knee, hip, or center movement after setup.
- Keep wrist/grip movement as a secondary cue only.
- Enforce a minimum separation from setup when enough sampled frames exist.
- If setup confidence is low, cap stride confidence and expose a fallback reason such as
  `setup_uncertain`.
- Avoid selecting stride and setup as adjacent frames unless the sequence is genuinely
  too sparse.

### Foot Strike Detection

Foot strike should identify the first lead-foot plant/stabilization after stride.

Required behavior:

- Identify the lead foot from stride direction when possible.
- Use the detected setup baseline.
- Search only quality-accepted frames when possible.
- Prefer the first frame or short interval where lead ankle/heel velocity drops below a
  plant threshold after meaningful displacement.
- Require plant/stability to persist for 2-3 sampled frames when frame density allows.
- Do not choose the later maximum foot displacement if an earlier plant is visible.
- If sampling is too sparse to observe plant, return lower confidence and an explicit
  fallback reason.

### Impact Policy And Impact-Dependent Metrics

Impact remains estimated unless future ball/contact evidence exists.

Required behavior:

- Add a request/config path for impact policy through application service and API.
- If impact is skipped or unavailable, do not pretend exact contact was detected.
- Identify all impact-dependent metrics and either skip them, lower their confidence, or
  use a documented fallback depending on the selected policy.
- UI should clearly show when impact was estimated, skipped, or unavailable.
- Do not implement ball detection in this task.

Impact-dependent areas to review include:

- torso tilt preservation
- head translation to impact
- lead knee blocking from foot strike to impact
- estimated attack angle
- any phase score or fault evidence requiring impact

### Follow-Through Detection

Follow-through should represent the swing finish/end, not simply the latest available
frame.

Required behavior:

- Search after estimated impact or, if impact is skipped, after foot strike plus
  rotational/hand acceleration evidence.
- Detect hand extension reaching a plateau or deceleration.
- Prefer the first stable finish frame after peak extension.
- Penalize frames where the player has already returned to idle, walked away, or moved
  into unrelated post-swing motion.
- If the finish is outside sampled frames, return lower confidence and an explicit
  fallback reason instead of blindly choosing the final frame.

## Non-Goals

- Do not implement ball, bat, barrel, or contact detection.
- Do not add hosted services, cloud upload, telemetry, release/deployment work, Docker,
  PyPI publishing, or mobile adapters.
- Do not change fielding, throwing, or pitching behavior.
- Do not commit videos, model weights, secrets, generated reports, or heavy fixtures.
- Do not move baseball rules into UI, API routes, storage, video, or pose modules.

## Architecture Requirements

- Keep event semantics under `motion`.
- Keep application orchestration and request defaults under `app`.
- Keep API serialization under `api`.
- Keep UI display logic rule-free; it may render returned event methods, confidence, and
  fallback reasons.
- Keep pose extraction under `pose`; do not add swing-event rules to pose estimation.
- If impact can be unavailable, define a clear typed boundary so analysis/scoring does
  not crash or silently use an invalid frame.
- Add or update an ADR if the phase/event model changes materially.

## Testing Requirements

Add deterministic tests covering:

- setup selected from early stable stance frames even when active-window detection starts
  later.
- setup reports a low-confidence fallback when the player is already moving at the first
  usable frame.
- stride is not adjacent to setup when enough frames exist and lower-body onset occurs
  later.
- stride confidence is capped when setup is uncertain.
- foot strike selects first sustained plant rather than later maximum displacement.
- foot strike does not use rejected frame-quality candidates.
- foot strike reports lower confidence when sampling is too sparse to observe plant.
- `body_pose_estimated` impact policy preserves estimated-impact behavior and limitations.
- `require_ball_contact` or `skip_without_ball` does not invent impact without
  contact evidence.
- impact-dependent metrics are skipped, downgraded, or limited consistently when impact
  is unavailable.
- follow-through selects first stable finish/extension plateau rather than unrelated
  late frames.
- follow-through reports lower confidence when finish is outside sampled frames.
- API and UI responses expose event method, confidence, unavailable/skipped state, and
  fallback reasons without local file paths.

Tests must not require real user videos, external services, credentials, or heavy binary
fixtures.

## Documentation Requirements

Update all relevant docs:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/` if the event/phase model changes materially
- `docs/03_development_log/` with a dated entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must clearly state:

- how setup, stride, foot strike, impact, and follow-through are detected after this
  revision.
- how impact policy works.
- which metrics are impact-dependent and what happens when impact is unavailable.
- known limitations, especially that bat/ball/contact evidence is not detected yet.

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

- Setup no longer drifts late when early stable stance frames are available.
- Stride no longer becomes trivially adjacent to setup when enough sampled frames exist.
- Impact policy is configurable and does not invent contact when the selected policy
  requires or skips ball/contact evidence.
- Foot strike prefers first sustained plant over later maximum displacement.
- Follow-through prefers first stable finish/extension plateau over unrelated late
  frames.
- Event confidence and fallback reasons are explicit for uncertain or skipped events.
- Impact-dependent metrics handle unavailable impact safely and visibly.
- Deterministic unit and integration tests cover the revised behavior.
- Relevant docs are updated.
- All quality gates pass.
- Final review confirms no blocking issues and no release/deployment was created.
