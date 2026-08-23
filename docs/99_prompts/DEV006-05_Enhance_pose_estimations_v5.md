# DEV006-05 Enhance Pose Estimations v5

## Objective

Improve swing event-detection and scoring behavior after DEV006-04 user review.
The latest implementation made the impact policy technically explicit, but the product
behavior is confusing:

- Turning impact detection off still shows impact in the evaluation/event display.
- Event confidence appears lower than before, with stride often near 50%.
- Impact and follow-through can show 0% confidence when impact is disabled.
- Some swing metrics that were previously available are now marked not evaluated.

Revise the impact-off contract, confidence display, and non-contact metric fallback
behavior so no-ball videos remain useful without implying exact ball contact.

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

Address these user-observed issues and implementation findings.

### Impact Off Still Appears In Evaluation

The UI sends `impact_detection_policy` correctly, and the backend marks impact as
`skipped` for `skip_without_ball`. However, the application service still emits a
`SwingEventWindow` for every phase, including skipped impact. This makes the browser
timeline/event list look like impact is still part of normal evaluation.

Current behavior to revise:

- `_events_from_phases(...)` returns impact even when `phases.status_for(IMPACT)` is
  `SKIPPED`.
- The UI can render a skipped impact marker as if it were an ordinary event frame.
- The backend still uses an internal proxy impact frame for ordering and compatibility,
  but that proxy should not be shown as a detected contact event when impact is off.

### Confidence Looks Lower Than Before

The new ordered-state event model applies fallback penalties when the detector cannot
confirm strong event evidence. This is useful, but it can make valid no-leg-lift or
sparse-frame swings look worse than they are:

- Stride often falls near 50% because no-leg-lift fallback subtracts confidence.
- Impact confidence is forced to `0.0` when impact is skipped.
- Follow-through score confidence can become `0.0` because its only metric is currently
  marked not evaluated when impact is unavailable.

The implementation must make clear distinctions between:

- event-detection confidence,
- score/evaluation confidence,
- skipped/unavailable phase status,
- metric not-evaluated status.

Skipped impact should not be presented as a low-confidence detected impact.

### Metrics Were Removed By Impact-Off Policy

With impact disabled, these metrics are currently marked not evaluated:

- `TORSO_TILT_PRESERVATION`
- `HEAD_TRANSLATION_RATIO`
- `LEAD_KNEE_BLOCKING_INDEX`
- `ESTIMATED_ATTACK_ANGLE`
- `FOLLOW_THROUGH_POSTURE_BALANCE`

Some of these are truly contact/impact dependent, but others can still provide useful
no-ball feedback if they use a different anchor frame and clearly report the limitation.

## Scope

### Impact-Off Product Contract

Revise the behavior so `Impact Detection: Off` means no user-visible impact event.

Required behavior:

- Keep `skip_without_ball` available as the no-ball policy.
- When impact is skipped, do not show impact as a normal detected event in browser event
  rows, replay overlays, or user-facing evaluation summaries.
- Internal code may retain a proxy impact frame for ordered phase repair or legacy metric
  compatibility, but that frame must be clearly marked internal/skipped and must not
  imply ball contact.
- API/app responses should make skipped impact unambiguous.
- Prefer one of these contract options:
  - omit skipped impact from user-visible `events`; or
  - add explicit display metadata such as `is_visible`, `is_overlay_event`, or
    `display_frame_index: null`.
- If the API contract changes materially, preserve backward compatibility where
  practical and document the migration.
- Existing callers must still be able to inspect impact status through phase metadata.

### Impact Mode Semantics

Clarify and implement the normal user-facing modes:

- `Off / No ball`: no user-visible impact event; skip only truly contact-dependent
  metrics; no impact faults.
- `On / Body estimate`: use body-pose-estimated impact and label it as estimated, not
  confirmed contact.
- `Ball/contact required`: keep as advanced/API-only behavior unless a real detector is
  later added.

Do not implement ball, bat, barrel, or contact detection in this task.

### Restore Useful Non-Contact Metrics

Reclassify metrics so impact-off videos still produce useful analysis when possible.

Required behavior:

- Keep truly contact-dependent metrics not evaluated when impact is off unless a safe
  non-contact variant is explicitly designed and renamed or limited.
- Restore or add fallback variants for metrics that do not strictly require contact:
  - `HEAD_TRANSLATION_RATIO`: compute with setup-to-foot-strike or setup-to-swing-finish
    fallback when impact is skipped, with lower confidence and a limitation.
  - `FOLLOW_THROUGH_POSTURE_BALANCE`: compute from foot-strike or late-swing/follow-
    through anchors when impact is skipped, with lower confidence and a limitation.
- Review whether these can safely keep their current metric names. If semantics change
  materially, update labels/descriptions to avoid implying impact-based measurement.
- Ensure follow-through phase scoring does not become 0% confidence solely because
  impact is off.
- Ensure skipped metrics are displayed as not evaluated, not as failed or zero-quality
  movement.

Recommended classification:

- Usually skip without impact:
  - `ESTIMATED_ATTACK_ANGLE`
  - impact-specific torso/knee metrics unless a clearly named fallback is implemented
- Usually evaluate with no-ball fallback:
  - `HEAD_TRANSLATION_RATIO`
  - `FOLLOW_THROUGH_POSTURE_BALANCE`

### Confidence Semantics And Display

Revise confidence handling so users can understand what was detected, skipped, or
evaluated.

Required behavior:

- Do not display skipped impact as `0%` confidence. Display `Skipped` or equivalent.
- Keep event confidence and score confidence separately labeled.
- Event confidence should describe phase/event placement quality.
- Score confidence should describe whether scoring evidence was available and reliable.
- If a phase has no evaluated metrics because the phase was intentionally skipped, show
  that state explicitly instead of presenting it as poor confidence.
- If no-leg-lift stride fallback is valid for the observed swing, avoid an automatic
  severe penalty that makes every such stride look poor.
- Keep fallback reasons visible, but do not let fallback reasons alone create misleading
  zero-confidence results.

### Stride Confidence Calibration

Review the no-leg-lift fallback introduced in DEV006-04.

Required behavior:

- Keep explicit lead-leg-lift detection as the preferred stride evidence.
- Keep lower-body-load fallback for no-stride hitters or sparse/occluded videos.
- Calibrate fallback confidence so valid no-stride swings are marked limited, not
  automatically poor.
- Continue to prevent stride from being selected from wrist/grip movement alone.
- Add tests that prevent stride confidence from being pinned near 50% for valid
  no-stride fallback fixtures.

### UI Behavior

Revise browser behavior to match the product contract.

Required behavior:

- `Impact Detection: Off` should visibly remove or suppress the impact event marker from
  normal results and overlay.
- Event rows should not imply exact contact for skipped impact.
- Metrics skipped because of impact-off should clearly show `Not evaluated` or a concise
  limitation.
- Metrics restored through no-ball fallback should show their fallback limitation.
- Impact-off should not make follow-through look like 0% quality when follow-through
  posture can still be evaluated.
- Changing impact mode must still clear stale analysis results.

## Non-Goals

- Do not implement ball, bat, barrel, or contact detection.
- Do not add hosted services, cloud upload, telemetry, release/deployment work, Docker,
  PyPI publishing, or mobile adapters.
- Do not change fielding, throwing, or pitching behavior.
- Do not commit videos, model weights, secrets, generated reports, or heavy fixtures.
- Do not move baseball rules into UI, API routes, storage, video, or pose modules.
- Do not perform broad scoring-threshold redesign beyond impact-off, confidence, and
  restored no-ball metric behavior.

## Architecture Requirements

- Keep swing event semantics and metric fallback calculations in `motion`.
- Keep scoring, fault suppression, score confidence, and not-evaluated handling in
  `analysis`.
- Keep application orchestration and API request defaults in `app` and `api`.
- Keep UI rule-free; it may render controls, status, confidence, fallback reasons, and
  returned display metadata.
- Preserve service-oriented boundaries so future web/mobile adapters can reuse the same
  behavior.
- If event metadata changes materially, update ADR-0012 or add a new ADR under
  `docs/02_architecture/adr/`.

## Testing Requirements

Add deterministic tests with small pose fixtures. Tests must not require real user
videos, external services, credentials, or heavy binary fixtures.

Required unit tests:

- `skip_without_ball` marks impact skipped and prevents impact faults.
- Skipped impact is not treated as a normal detected event for user-visible event output
  or display metadata.
- Skipped impact does not display as low-confidence detected impact.
- `HEAD_TRANSLATION_RATIO` remains evaluated with an explicit no-ball fallback when
  impact is skipped, if sufficient setup/foot-strike or setup/follow-through evidence
  exists.
- `FOLLOW_THROUGH_POSTURE_BALANCE` remains evaluated with an explicit no-ball fallback
  when impact is skipped and follow-through evidence exists.
- Truly impact/contact-dependent metrics remain not evaluated when impact is skipped.
- Follow-through phase score confidence is not forced to 0% when restored no-ball
  follow-through evidence exists.
- Valid no-stride fallback does not pin stride confidence near 50% solely because no
  visible leg lift exists.
- Weak or sparse stride/foot-strike evidence still reports lower confidence and fallback
  reasons.

Required integration/API/UI tests:

- App-service video analysis with `skip_without_ball` does not return a normal
  user-visible impact event or returns explicit display metadata suppressing it.
- API `/api/v1/analysis/swing/video` serializes impact-off status/display behavior
  consistently.
- Browser UI sends the selected `impact_detection_policy` and clears stale results when
  impact mode changes.
- Browser UI suppresses skipped impact from normal event rows/overlays or labels it in a
  way that cannot be mistaken for detected contact.
- Browser UI distinguishes event confidence from score confidence and displays skipped
  impact as `Skipped`, not `0%`.
- Browser UI still displays restored no-ball metrics and their limitations.

## Documentation Requirements

Update all relevant docs:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/` if the app/API event contract changes materially
- `docs/03_development_log/` with a dated entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must clearly state:

- what `Impact Detection: Off` does and does not do.
- why skipped impact is not a detected contact event.
- which metrics are skipped without impact/contact evidence.
- which metrics still run with no-ball fallback anchors.
- how event confidence differs from score confidence.
- why no-leg-lift stride fallback can be valid but lower certainty than visible lift.
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

- Turning impact detection off removes or suppresses impact from normal user-visible
  event evaluation and replay overlays.
- Skipped impact is shown as skipped, not as a detected event with 0% confidence.
- Impact faults remain suppressed when impact is skipped.
- Useful non-contact metrics, especially head translation and follow-through posture,
  are evaluated with documented no-ball fallbacks when sufficient evidence exists.
- Truly contact-dependent metrics remain not evaluated when impact is skipped.
- Follow-through score confidence is not forced to 0% solely because impact detection is
  off.
- Stride fallback confidence is calibrated so valid no-stride swings are limited but not
  automatically poor.
- Event confidence and score confidence are clearly distinguished in API/UI behavior.
- Deterministic unit and integration tests cover the revised behavior.
- Required docs are updated.
- Required quality gates pass.
- No release or deployment is created.
