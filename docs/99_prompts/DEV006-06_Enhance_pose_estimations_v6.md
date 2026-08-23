# DEV006-06 Enhance Pose Estimations v6

## Objective

Revert the normal product behavior away from `Impact Detection: Off` / skipped-impact
evaluation and improve body-pose estimated impact quality instead.

User review showed that skipping impact removes too much useful swing evaluation:
contact-specific metrics disappear, impact faults are suppressed, phase scoring becomes
confusing, and overall confidence can look unreliable. The product should return to a
normal workflow where impact is estimated from body-pose motion cues, while clearly
labeling it as estimated and improving the quality of the selected impact frame.

The goal is not to claim true bat-ball contact. The goal is to keep impact available for
evaluation while making the estimated impact frame better and more transparent.

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
- `docs/99_prompts/DEV006-04_Enhance_pose_estimations_v4.md`
- `docs/99_prompts/DEV006-05_Enhance_pose_estimations_v5.md`
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

Skipping impact is too costly for the current evaluation model:

- Impact-specific metrics are not evaluated.
- Impact faults are suppressed.
- Impact phase reporting becomes confusing.
- Overall confidence can drop because metric coverage is reduced.
- Some metrics that users expect from the report disappear or become fallback-only.

Therefore the normal UI/workflow should not provide a no-impact mode for swing
evaluation. The app should use body-pose estimated impact by default and focus on
improving estimated impact quality.

The implementation must still be honest: body pose cannot confirm ball contact. Impact
must be labeled as an estimated body-motion event until a future bat/ball/contact
detector exists.

## Scope

### Revert Normal Skip-Impact Behavior

Required behavior:

- Remove or hide the normal browser `Impact Detection: Off` option.
- Set the normal browser request behavior to `body_pose_estimated`.
- Ensure normal stored-video swing analysis evaluates impact metrics and impact-phase
  faults from the estimated body-pose impact frame.
- Revert DEV006-05 behavior that suppresses impact from normal event rows, replay event
  overlays, or phase-score reports in the normal workflow.
- Revert DEV006-05 no-ball fallback metric behavior from the normal workflow if it only
  exists to support skipped impact.
- Keep backend/API enum values only if needed for backward compatibility or future
  advanced API use, but they must not be exposed as the normal browser product path.
- If `skip_without_ball` remains accepted by API for compatibility, document it as
  advanced/diagnostic and keep current safe behavior for callers that explicitly use it.

### Improve Estimated Impact Detection Quality

Revise impact selection in `motion` so the estimated impact frame is more reliable from
body-pose evidence.

Required behavior:

- Keep impact after foot strike and before follow-through.
- Search impact inside a bounded post-foot-strike / pre-follow-through window, not across
  unrelated late frames.
- Use multiple cues instead of raw wrist speed alone:
  - wrist/grip speed,
  - wrist/grip acceleration or deceleration,
  - hand path entering the front-torso/contact-zone region,
  - lead-side bracing or reduced lead-knee collapse,
  - hip/shoulder rotation timing,
  - transition toward follow-through extension.
- Penalize frames that are too close to stride/foot strike when hand path has not entered
  the contact-zone region.
- Penalize late follow-through-only frames after peak extension or after clear
  deceleration.
- Prefer a local maximum or high-scoring frame that balances hand speed, body rotation,
  front-side position, and ordering constraints.
- Return impact detection method, confidence, and fallback reason when evidence is weak.
- Do not add bat, barrel, ball, or contact detection in this task.

### Confidence Model

Improve user-facing confidence so it is relevant and trusted.

Required behavior:

- Since normal impact is no longer skipped, avoid confidence penalties caused only by
  intentionally skipped impact metrics in the normal browser path.
- Continue to distinguish:
  - event confidence,
  - score/evaluation confidence,
  - pose quality,
  - limitations.
- If the API still supports explicit skipped impact for advanced callers, skipped metrics
  should be reported as coverage/availability rather than silently making visible
  confidence look contradictory.
- Document the overall confidence formula or presentation enough that users can
  understand why it differs from per-event or per-phase confidence.

### UI Behavior

Required behavior:

- The normal browser UI should not invite the user to turn off impact detection.
- Impact should appear as an estimated event row and replay event label in the normal
  workflow.
- The report should clearly label impact as estimated body-pose impact, not confirmed
  ball contact.
- Phase scores and impact-related metrics should be present in normal analysis results
  when pose evidence is sufficient.
- Any remaining advanced skipped-impact state should not be confused with the normal
  report path.

## Non-Goals

- Do not implement ball, bat, barrel, or contact detection.
- Do not claim true bat-ball contact from body pose.
- Do not add hosted services, cloud upload, telemetry, release/deployment work, Docker,
  PyPI publishing, or mobile adapters.
- Do not change fielding, throwing, or pitching behavior.
- Do not commit videos, model weights, secrets, generated reports, or heavy fixtures.
- Do not perform a broad swing scoring redesign beyond changes needed to restore normal
  estimated-impact evaluation and improve impact event quality.

## Architecture Requirements

- Keep impact event semantics and heuristic selection inside `motion`.
- Keep scoring, confidence, and fault behavior inside `analysis`.
- Keep application orchestration and defaults inside `app`.
- Keep API serialization and compatibility handling inside `api`.
- Keep UI rule-free; it may render controls and returned metadata but must not calculate
  impact thresholds or baseball mechanics.
- Preserve service-oriented boundaries so future web/mobile adapters can reuse the same
  behavior.
- If the impact policy or response contract changes materially, update ADR-0012 or add a
  new ADR under `docs/02_architecture/adr/`.

## Testing Requirements

Add deterministic tests with small pose fixtures. Tests must not require real user
videos, external services, credentials, or heavy binary fixtures.

Required unit tests:

- Normal/default event config uses `body_pose_estimated` impact.
- Default impact is visible in event output, replay overlay eligibility, and phase-score
  reporting.
- Normal/default analysis evaluates impact-related metrics when pose evidence is
  sufficient.
- Estimated impact is selected after foot strike and before follow-through.
- Estimated impact is not selected from early hand movement before contact-zone evidence.
- Estimated impact is not selected from late follow-through-only movement.
- Estimated impact confidence/fallback reason is lower when hand/body cues are weak.
- Existing setup, stride, foot strike, and follow-through behavior from DEV006-04 remains
  intact.
- If `skip_without_ball` remains for API compatibility, explicit skipped-impact callers
  still do not crash and still suppress contact-specific faults safely.

Required integration/API/UI tests:

- Browser UI no longer exposes `Impact Detection: Off` as a normal control, or clearly
  defaults to On with no user-facing skip option.
- Browser swing video request sends `body_pose_estimated` or omits the field so the
  backend default is body-pose estimated impact.
- App-service video analysis returns impact as an estimated visible event in the normal
  path.
- API `/api/v1/analysis/swing/video` serializes impact status as `estimated` in the
  normal path.
- Replay overlay marks estimated impact as an event frame in the normal path.
- Impact-related metrics and faults are present when deterministic fixtures provide
  sufficient evidence.
- Quality gates cover the revised UI and API behavior.

## Documentation Requirements

Update relevant docs:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/ADR-0012-enhanced-swing-pose-diagnostics.md` if behavior or
  API contract changes materially
- `docs/03_development_log/` with a dated entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must state:

- The normal browser workflow uses body-pose estimated impact.
- Impact is estimated, not confirmed ball contact.
- Skipping impact is not part of the normal UI workflow because it removes too much
  evaluation coverage.
- How estimated impact is selected from body-pose cues.
- Known limitations of body-pose-only impact estimation.
- How to interpret event confidence versus score/evaluation confidence.

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

- The normal browser workflow no longer offers skipped-impact evaluation as the standard
  path.
- Normal swing video analysis uses body-pose estimated impact.
- Impact appears in normal event rows, replay overlays, phase scores, and impact-related
  evaluation when pose evidence is sufficient.
- The estimated impact frame quality is improved using multiple body-pose cues and
  ordering constraints.
- Impact remains clearly labeled as estimated body-pose impact, not confirmed contact.
- Confidence presentation no longer looks low solely because impact was intentionally
  skipped in the normal path.
- Deterministic unit and integration tests cover the revised behavior.
- Relevant docs and `PLANS.md` are updated.
- Required quality gates pass.
- No release or deployment is created.
