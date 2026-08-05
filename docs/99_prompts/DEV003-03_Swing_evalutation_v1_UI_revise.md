# DEV003-03 Swing Evaluation v1 UI Revision

## Goal

Revise the DEV003-02 swing analysis UI so it is easier to use during local video review.

The revised UI should keep the local-PC-first workflow, keep swing rules out of UI/API
adapters, provide sensible default swing pose inputs, explain each visible analysis
parameter, support a motion-analysis selector, show analysis results in the motion
analysis column, and overlay key motion points on the replayed video.

This task is a major UI revision over the existing DEV003-02 implementation. It should
not add release or deployment work.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-01_Swing_evaluation_v1.md`
* `docs/99_prompts/DEV003-02_Swing_evaluation_v1_UI.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md`
* Existing manuals under `docs/05_manuals/`
* Existing implementation:
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/api/swing_router.py`
  * `src/baseball_motion_analysis/api/schemas.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
* Existing tests:
  * `tests/integration/test_swing_analysis_api.py`
  * `tests/integration/test_web_video_upload_replay_api.py`
  * `tests/integration/test_swing_application_service.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_feedback.py`
  * `tests/unit/test_swing_motion_metrics.py`

## Current Implementation Context

DEV003-02 added:

* `POST /api/v1/analysis/swing`
* Swing analysis request/response schemas
* A local web UI swing analysis panel
* Pasted pose JSON, JSON file input, and deterministic demo pose data
* Display of score, phase scores, metrics, detected faults, feedback, confidence, and
  limitations

Current limitations to address in this revision:

* Swing pose defaults are available through a demo-load button, but the analysis workflow
  does not present defaults as a first-class starting state.
* Parameter labels exist but do not explain what each parameter means or how it affects
  analysis.
* The UI has grown into separate panels instead of a single one-row three-column review
  layout.
* Motion analysis is swing-specific in the UI; other motion categories are not exposed as
  planned options.
* Key pose/motion points are not overlaid on the replay video.
* User manuals do not yet describe the swing analysis UI revision.

## Scope

Implement a revised browser UI workflow with:

1. Swing analysis pose defaults.
2. Parameter explanations in the UI.
3. A one-row, three-column layout.
4. A motion-analysis selector for swing, throwing, pitching, and fielding.
5. Key motion point overlays on replayed video.
6. Updated manuals under `docs/05_manuals/`.

Keep the existing API/application-service boundary unless the implementation needs a
small browser-safe response addition for overlays. If response fields are added, keep them
generic and adapter-oriented, not rule-specific UI logic.

## Required UI Layout

Use one main review row with three columns on desktop.

### Left Column

Column contents:

* `Upload Video`
* `Video Library`

Behavior:

* Preserve existing upload, validation, status, error, refresh, replay selection, and
  delete behavior.
* Stack upload controls above the video library inside the left column.
* Keep local privacy messaging and upload-size messaging visible.
* Do not move replay playback controls into this column.

### Middle Column

Column header:

```text
Motion Analysis
```

Column contents:

* Motion analysis selector.
* Selected-motion parameter setup.
* Selected-motion action buttons.
* Selected-motion analysis status and errors.
* Selected-motion analysis results.

Motion selector options:

* Swing
* Throwing
* Pitching
* Fielding

Selection behavior:

* Swing should be the only fully runnable analysis type in this task, using the existing
  swing analysis API/service.
* Throwing, pitching, and fielding should be selectable only if the UI can present a clear
  "planned / not implemented yet" state without exposing non-working action buttons.
* Do not implement throwing, pitching, or fielding analysis rules in this task.
* When `Swing` is selected, show the swing setup details, buttons, and results in this
  middle column.
* The previous standalone `Swing Analysis` section should be moved into the middle
  `Motion Analysis` column. It may appear as a selected-motion subheading, but the column
  header should be `Motion Analysis`.
* Analysis results should be displayed in the `Motion Analysis` column, not below the
  three-column row.

### Right Column

Column contents:

* `Replay`

Behavior:

* Keep the current replay behavior as-is:
  * Video player
  * Playback speed
  * Previous-frame and next-frame controls
  * Title, time, resolution, FPS, playback status, and playback errors
* Add overlay support without breaking browser video controls.

## Responsive Layout Requirements

Desktop:

* Keep three columns in one row:
  * Left: upload and video library
  * Middle: motion analysis
  * Right: replay

Tablet and narrow screens:

* Columns may stack vertically when the viewport cannot display three readable columns.
* Preserve the same logical order: upload/library, motion analysis, replay.
* Text, buttons, selects, and result tables must not overflow their containers.

## Swing Pose Defaults

The swing analysis UI should start from usable defaults instead of an empty technical
state.

Required defaults:

* Default selected motion: `Swing`.
* Default handedness: `Right-handed`.
* Default phase frame indexes matching the deterministic demo pose sequence:
  * Setup: `0`
  * Stride: `1`
  * Foot Strike: `2`
  * Impact: `3`
  * Follow-through: `4`
* Default pose source: deterministic demo swing pose data, loaded or loadable without
  requiring the user to paste JSON first.
* Default analysis result state: not yet run, with clear text that the defaults are demo
  pose data and are not analysis of the selected uploaded video.

Default behavior options:

* Recommended: prefill swing default parameters and demo pose data on page load, while
  clearly marking the source as "Demo pose data".
* Acceptable: show a prominent "Use Default Swing Pose" button and load those defaults
  before analysis can run.

Do not present demo pose data as extracted from uploaded videos.

## Parameter Explanation Requirements

Each visible parameter or setup control should include concise user-facing explanation.
Use helper text, details/summary, tooltips, or compact inline descriptions.

Required swing setup explanations:

* Motion Type:
  * Explains that only swing is runnable now and other motion types are planned.
* Handedness:
  * Explains how right-handed and left-handed choices map lead and rear sides.
  * Explains that unknown lowers confidence because the service uses a default side
    interpretation.
* Pose Source:
  * Explains demo pose data, pasted pose JSON, and JSON file input.
  * Explains that uploaded videos are not automatically converted to pose data yet.
* Pose JSON:
  * Explains the expected frame/keypoint format and that coordinates are normalized 2D
    points with confidence values.
* Phase Frame Indexes:
  * Explains that phase indexes identify setup, stride, foot strike, impact, and
    follow-through frames.
  * Explains that all five phase fields should be set together or left blank for fallback
    behavior.
* Run Swing Analysis:
  * Explains that the button sends pose data to the local app service and returns
    in-memory results.
* Clear / Reset:
  * Explains whether it clears only results or also resets defaults.
* Confidence:
  * Explains that confidence reflects visible keypoint quality, handedness certainty, and
    phase detection certainty.
* Limitations:
  * Explains that limitations identify missing keypoints, fallback pose data, weak bat
    evidence, or camera/2D constraints.

The UI may use concise labels, but manuals must provide fuller explanation.

## Motion Point Overlay Requirements

Overlay key motion points on top of the replayed video.

Required behavior:

* Add a video overlay layer aligned with the rendered video element.
* Overlay should not block normal video controls.
* Overlay should update when:
  * A stored video replay is loaded.
  * The video current time changes.
  * The user steps previous/next frame.
  * Swing analysis or pose defaults are loaded.
* Overlay should support normalized pose coordinates from available pose frames.
* Overlay should map normalized coordinates to the displayed video rectangle.
* Overlay should show key swing points for the nearest available pose frame:
  * Nose or head proxy
  * Lead and rear shoulders
  * Lead and rear hips
  * Lead and rear knees
  * Lead and rear ankles
  * Lead and rear wrists
  * Bat tip or barrel when available
* Overlay should distinguish:
  * Key body points
  * Bat point
  * Current or evidence phase frame when applicable
* Overlay should be hidden or show a clear empty state when no pose data is available.
* Overlay should display an explicit source note when using demo pose data.

Implementation guidance:

* Prefer an absolutely positioned `<canvas>` or SVG overlay inside a replay wrapper.
* Keep overlay drawing in UI rendering code only. Do not add baseball scoring rules to
  overlay rendering.
* If handedness normalization is needed to label lead/rear points in the overlay, call
  the existing service/API result or use explicit non-rule mapping already exposed by the
  domain result. Do not duplicate fault thresholds or coaching evaluations in JavaScript.
* For demo/default pose data whose normalized coordinates exceed the video range, clamp
  drawing to the visible overlay bounds or normalize the demo fixture used by the UI.
* Overlay should remain visually legible on light/dark video content.

## Analysis Result Requirements

In the middle `Motion Analysis` column, show:

* Overall score.
* Confidence.
* Summary.
* Good points.
* Improvement points.
* Drills or suggestions.
* Limitations.
* Phase scores.
* Metrics with value, target range, severity, deduction, and evidence frames.
* Detected faults with type, phase, severity, evidence, and evidence frames.

Result behavior:

* Results should update after a successful analysis.
* Results should clear or reset when the selected motion changes.
* Swing results should remain clearly tied to the selected pose source.
* Long text must wrap cleanly inside the middle column.
* Result tables may use compact cards or scrollable tables if needed for column width.

## API and Application-Service Requirements

Keep using:

```text
POST /api/v1/analysis/swing
```

Required behavior:

* UI calls the API adapter.
* API adapter calls `SwingAnalysisApplicationService`.
* API adapter converts pose JSON into internal pose models.
* API adapter returns browser-safe structured errors.
* No API route contains swing thresholds, fault rules, drill mapping, or coaching text
  generation.

Only add new API fields if needed for overlay rendering or parameter explanations. If
new fields are added:

* Keep them derived from existing service results or request pose data.
* Add tests.
* Document them in architecture and manuals.

## Non-Goals

* Do not implement concrete pose estimation from uploaded video.
* Do not implement throwing, pitching, or fielding analysis rules.
* Do not implement bat detection or new computer-vision models.
* Do not persist swing reports unless separately scoped.
* Do not add hosted web services, cloud uploads, authentication, mobile adapters, Docker,
  deployment, release notes, version bumps, or packaging work.
* Do not require real user videos, large binary fixtures, external services, or external
  credentials.
* Do not add medical, injury, or guaranteed coaching claims.
* Do not hard-code score thresholds, fault rules, drill mapping, or swing coaching text in
  UI JavaScript, templates, API routes, media loaders, or storage adapters.

## Documentation Requirements

Update documentation if behavior or architecture changes:

* `PLANS.md` with DEV003-03 scope, task status, implementation decisions, QA result, and
  final-review-planning result.
* `docs/01_product/feature_catalog.md` to describe the revised motion-analysis UI,
  default swing pose setup, and replay overlay.
* `docs/02_architecture/system_overview.md` if the UI/data flow or overlay architecture
  changes.
* `docs/03_development_log/` with a dated development log entry.
* `docs/04_motion_knowledge/swing.md` only if swing evaluation rules or user-facing
  motion interpretation change.
* `docs/05_manuals/` for user-facing instructions:
  * Update an existing manual if the revised UI naturally belongs there.
  * Otherwise create a new manual, recommended:
    `docs/05_manuals/swing_motion_analysis_ui.md`.

Manual content must explain:

* How to upload a video and select it for replay.
* How to use the `Motion Analysis` column.
* What each motion type option means.
* That only swing analysis is currently runnable.
* How to use default swing pose data.
* How to provide pose JSON or a pose JSON file.
* What handedness means.
* What phase frame indexes mean.
* How to run swing analysis.
* How to read overall score, phase scores, metrics, faults, confidence, limitations, good
  points, improvement points, and drills.
* How to interpret overlaid key motion points on the replay video.
* Current limitations:
  * Uploaded videos are not automatically analyzed.
  * Pose data must already be available or demo data must be used.
  * Overlay points depend on pose coordinate quality.
  * Side-view 2D analysis has limitations.

Do not update release notes, changelog, version numbers, or deployment documentation for
this task.

## Testing Requirements

Add or update focused tests.

Required UI/static tests:

* Index page renders a one-row three-column structure:
  * Left column includes `Upload Video` and `Video Library`.
  * Middle column header is `Motion Analysis`.
  * Right column includes `Replay`.
* Motion selector includes swing, throwing, pitching, and fielding.
* Swing is selected by default.
* Swing default pose setup is available on initial load or through a clearly tested
  default-load button.
* Swing parameter explanations are present in the rendered page.
* Swing analysis results render inside the `Motion Analysis` column.
* Existing upload, library, replay, delete, and health behavior still passes.
* Overlay container or canvas is present over the replay video.
* Static JavaScript includes overlay update behavior tied to video time updates and frame
  stepping.

Required API tests:

* Existing DEV003-02 swing analysis API tests still pass.
* Add tests for any new API response fields or request fields.
* Error responses remain structured and do not include local filesystem paths.

Required frontend behavior tests where practical:

* Demo/default pose data can be submitted to swing analysis.
* Motion selection changes visible setup state.
* Selecting an unsupported motion shows a planned/not-implemented state and does not call
  an unsupported analysis endpoint.
* Overlay drawing function maps normalized pose coordinates into displayed video bounds.

Use deterministic fixtures only. Do not add large videos, user media, model weights, or
external credentials.

## Acceptance Criteria

* The local web UI uses a desktop one-row, three-column review layout.
* The left column contains upload and video library workflows.
* The middle column is headed `Motion Analysis`.
* The middle column contains a motion selector with swing, throwing, pitching, and
  fielding.
* Swing is the default selected motion and is the only runnable analysis type.
* The previous `Swing Analysis` workflow is moved into the middle column under the motion
  analysis setup/results area.
* Swing pose defaults are available without requiring the user to manually paste JSON.
* Each visible swing analysis parameter has concise UI explanation.
* Swing analysis results display in the `Motion Analysis` column.
* The right column keeps existing replay behavior.
* Key motion points can be overlaid on the replayed video when pose data is available.
* Overlay behavior does not block video playback controls.
* Existing upload, library, replay, delete, health, and swing API behavior remains
  unchanged.
* No baseball coaching rules are duplicated in UI JavaScript, templates, API routes,
  media loaders, storage adapters, or overlay rendering.
* `docs/05_manuals/` is updated or a new manual is created for the revised feature.
* Tests cover the new layout, defaults, explanations, selector, overlay presence, and API
  regression behavior.
* Required quality commands pass.
* `PLANS.md` and relevant docs are updated.
* No release or deployment is created.

## Required Quality Commands

After code changes, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed, run:

```bash
uv run ruff format .
```

Also run a JavaScript syntax check for touched static JavaScript if Node is available:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
```

## Open Questions For Implementation

Resolve these before or during implementation:

* Should swing demo/default pose data be automatically loaded on page open, or loaded by a
  button while still making defaults obvious?
* Should overlay points be drawn from the current pose input before analysis, from the
  latest successful analysis request, or both?
* Should phase/evidence frames be highlighted differently from ordinary pose points?
* Should unsupported motion options be enabled with an explanatory placeholder, or
  disabled while still visible?

Recommended defaults if no clarification is available:

* Load swing defaults on page open and clearly label them as demo pose data.
* Draw overlay points from the current pose input, and update source labeling after
  successful analysis.
* Highlight phase/evidence frames with a distinct outline or label.
* Keep unsupported motion options selectable so users can see that throwing, pitching,
  and fielding are planned, but disable run buttons and show an explanatory message.
