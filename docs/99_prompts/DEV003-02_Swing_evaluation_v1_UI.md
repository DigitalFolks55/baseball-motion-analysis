# DEV003-02 Swing Evaluation v1 UI

## Goal

Implement the first local-PC UI and API-adapter workflow for displaying the swing
evaluation implemented by `DEV003-01_Swing_evaluation_v1.md`.

The UI should let a local user run swing evaluation from an already available pose
keypoint sequence, select or confirm swing handedness and phase frames, and view the
returned score, phase scores, good points, improvement points, drills, confidence, and
limitations.

This task is a UI integration layer over the existing swing analysis application service.
It must not reimplement baseball swing rules in UI callbacks, JavaScript, API routes,
media loaders, or storage adapters.

## Source Documents To Read First

Before implementation, read:

* `AGENTS.md`
* `PLANS.md`
* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/99_prompts/DEV003-01_Swing_evaluation_v1.md`
* `docs/04_motion_knowledge/swing.md`
* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/ADR-0005-swing-evaluation-v1.md`
* Existing implementation:
  * `src/baseball_motion_analysis/app/swing_services.py`
  * `src/baseball_motion_analysis/pose/models.py`
  * `src/baseball_motion_analysis/motion/swing.py`
  * `src/baseball_motion_analysis/analysis/swing.py`
  * `src/baseball_motion_analysis/feedback/swing.py`
* Existing local web UI and API adapter code:
  * `src/baseball_motion_analysis/ui/web/router.py`
  * `src/baseball_motion_analysis/ui/web/templates/index.html`
  * `src/baseball_motion_analysis/ui/web/static/app.js`
  * `src/baseball_motion_analysis/ui/web/static/styles.css`
  * `src/baseball_motion_analysis/api/router.py`
  * `src/baseball_motion_analysis/api/media_router.py`
  * `src/baseball_motion_analysis/app/main.py`
* Existing tests for the touched modules:
  * `tests/integration/test_swing_application_service.py`
  * `tests/integration/test_web_video_upload_replay_api.py`
  * `tests/unit/test_swing_analysis.py`
  * `tests/unit/test_swing_feedback.py`
  * `tests/unit/test_swing_motion_metrics.py`

## Current Implementation Context

`DEV003-01` added the service-oriented swing evaluation foundation:

* `SwingAnalysisApplicationService.analyze_pose_sequence()`
* `AnalyzeSwingRequest`
  * `frames: Sequence[PoseFrame]`
  * `handedness: SwingHandedness`
  * `phase_frames: Mapping[SwingPhase, int] | None`
  * `config: SwingAnalysisConfig | None`
* `AnalyzeSwingResponse`
  * `analysis: SwingAnalysisResult`
  * `feedback: SwingFeedbackReport`

The local web UI currently supports:

* Video upload
* Local video library browsing
* Replay manifest loading
* Browser video playback
* Playback speed control
* Previous-frame and next-frame stepping

The repository does not yet include a production pose-estimation workflow from uploaded
video to `PoseFrame` sequences. Therefore, this UI task must present swing analysis as
available for already-extracted pose data only. Do not claim that uploaded videos are
automatically analyzed unless a separate pose-extraction feature is implemented.

## Scope

Implement a local web UI path and API adapter for swing evaluation from pose keypoint
data.

Required behavior:

* Add a swing analysis section to the local web UI.
* Let the user choose swing handedness:
  * Right-handed
  * Left-handed
  * Unknown
* Let the user provide or use phase frame indexes for the five phases:
  * Setup / Stance
  * Loading / Stride
  * Foot Strike / Foot Plant
  * Impact
  * Follow-through
* Support analysis from already-extracted pose frames.
* Call an application-service-backed API adapter that uses
  `SwingAnalysisApplicationService`.
* Display:
  * Overall score
  * Phase scores
  * Detected faults
  * Good points
  * Improvement points
  * Drills or suggestions
  * Confidence
  * Limitations
  * Metric values, severity, and evidence frames
* Handle missing or low-confidence keypoints with the returned limitations and confidence.
* Show clear empty, loading, success, and error states.
* Keep all swing mechanics rules in `motion`, `analysis`, and `feedback`, not in UI or API
  adapter code.

## Recommended UI Input Strategy

Because video-to-pose extraction is not yet implemented, use one of these local-first
input paths:

1. Primary path: a pose JSON input or upload control that accepts already-extracted
   `PoseFrame` data.
2. Developer/demo path: a deterministic built-in sample pose sequence used only for
   local UI verification and tests.

The UI must label the feature accurately, for example:

* "Swing Analysis From Pose Data"
* "Upload or paste pose keypoints exported by the pose layer."
* "Video-to-pose extraction is not yet included in this workflow."

Do not present demo pose data as an analysis of the selected uploaded video.

## Non-Goals

* Do not implement pose estimation from video.
* Do not implement bat detection or a new computer-vision model.
* Do not persist swing reports unless a storage/application-service report workflow is
  explicitly added in this task.
* Do not add hosted web services, cloud upload, authentication, mobile adapters, Docker,
  deployment, or release work.
* Do not require real user videos or large binary fixtures in tests.
* Do not add medical, injury, or guaranteed coaching claims.
* Do not hard-code score thresholds, fault rules, drill mapping, or swing coaching text in
  UI JavaScript, templates, API routes, media loaders, or storage adapters.

## Architecture Requirements

Follow the repository boundaries:

* `ui`: render controls, collect user inputs, call API adapter, and display response.
* `api`: validate HTTP request/response shape, convert JSON payloads to typed app models,
  call application services, and return structured JSON errors.
* `app`: orchestrate swing analysis through `SwingAnalysisApplicationService`.
* `pose`: own stable keypoint names and frame observation models.
* `motion`, `analysis`, `feedback`: remain the only layers containing swing mechanics,
  scoring, and feedback logic.
* `storage`: do not write swing reports directly from UI or API routes.

Recommended API shape:

```text
POST /api/v1/analysis/swing
```

The endpoint should accept a request payload that can be converted to
`AnalyzeSwingRequest`. Keep the payload independent of a specific UI so future web,
mobile, or local desktop adapters can reuse the same contract.

If the route is placed under a different prefix, document the reason in `PLANS.md` or an
architecture note.

## API Data Requirements

Request fields:

* `frames`: non-empty list of pose frames.
* `handedness`: `right_handed`, `left_handed`, or `unknown`.
* `phase_frames`: optional object with frame indexes for:
  * `setup`
  * `stride`
  * `foot_strike`
  * `impact`
  * `follow_through`
* `config`: optional threshold overrides only if the implementation can keep them typed
  and validated. Otherwise omit config from the public API for this task.

Pose frame JSON shape:

```json
{
  "frame_index": 0,
  "timestamp_seconds": 0.0,
  "keypoints": {
    "nose": { "x": 0.5, "y": 0.2, "confidence": 0.9 },
    "left_shoulder": { "x": 0.45, "y": 0.35, "confidence": 0.95 }
  }
}
```

The API adapter should map keypoint strings to `PoseKeypointName`, coordinates to
`Point2D`, and values to `PoseKeypoint`.

Response fields:

* `analysis.overall_score`
* `analysis.phase_scores`
* `analysis.metrics`
* `analysis.detected_faults`
* `analysis.good_points`
* `analysis.improvement_priorities`
* `analysis.confidence`
* `analysis.limitations`
* `analysis.phases`
* `analysis.handedness`
* `feedback.summary`
* `feedback.good_points`
* `feedback.improvement_points`
* `feedback.drills_or_suggestions`
* `feedback.confidence`
* `feedback.limitations`

Return structured errors for:

* Empty frame list.
* Unknown keypoint name.
* Invalid handedness.
* Missing required fields.
* Invalid phase frame indexes.
* Non-numeric coordinates or confidence values.

Do not leak local filesystem paths in error responses.

## UI Requirements

Update the existing local web UI instead of creating a separate landing page.

Recommended layout:

* Keep the current upload, library, and replay panels.
* Add a "Swing Analysis" panel near the replay panel.
* Use compact controls suitable for repeated review:
  * Handedness select or segmented control.
  * Phase frame number inputs for all five phases.
  * Optional buttons to copy the current replay frame index into a selected phase field
    when FPS is available.
  * Pose JSON textarea or file input.
  * "Run Swing Analysis" button.
  * "Clear Analysis" button.
* Disable the run button until required pose data is available.
* Display loading status while the API request is active.
* Display validation errors near the analysis controls.
* Preserve the existing video upload and replay behavior.

Result display:

* Overall score as a prominent numeric value.
* Confidence as a numeric value and short status label.
* Phase scores as a compact list or table.
* Metrics as a compact table with:
  * Metric name
  * Value
  * Target range
  * Severity
  * Deduction
  * Evidence frames
* Faults as a list with fault type, phase, severity, evidence, and evidence frames.
* Feedback sections:
  * Summary
  * Good points
  * Improvement points
  * Drills or suggestions
  * Limitations

Use cautious labels and wording consistent with `SwingFeedbackReport`. The UI should
display service-generated feedback as returned rather than rewriting baseball-specific
coaching text in JavaScript.

## UX and Accessibility Requirements

* Keep controls keyboard accessible.
* Use `aria-live` for loading, success, and error status messages.
* Keep visible text concise and task-focused.
* Ensure result tables remain readable on narrow screens.
* Avoid layout shifts when results load.
* Do not let long metric names, limitation text, filenames, or error text overflow their
  containers.
* Clearly mark when analysis was run from pasted/imported pose data or demo pose data.
* Do not imply cloud upload. Keep local privacy messaging consistent with the existing
  local-PC workflow.

## Testing Requirements

Add focused tests for the UI and API adapter.

Required API tests:

* Successful swing analysis request using deterministic synthetic pose frames.
* The API response includes analysis and feedback fields needed by the UI.
* Invalid handedness returns a structured client error.
* Unknown keypoint name returns a structured client error.
* Empty frame list returns a structured client error.
* Invalid phase frame index returns a structured client error.
* Error responses do not include local filesystem paths.

Required UI/static tests:

* The index page renders the swing analysis panel and controls.
* Existing upload, library, and replay UI tests still pass.
* Static JavaScript can call the swing analysis endpoint and render:
  * Overall score
  * Confidence
  * Good points
  * Improvement points
  * Drills or suggestions
  * Limitations
* Frontend error handling displays a clear message when analysis fails.

Use deterministic fixtures from existing swing tests where practical. Do not add large
videos, user media, model weights, or external credentials.

## Documentation Requirements

Update documentation if behavior or architecture changes:

* `PLANS.md` with task status, scope decisions, and final review result.
* `docs/01_product/feature_catalog.md` to describe the UI-visible swing analysis
  capability and its current pose-data limitation.
* `docs/02_architecture/system_overview.md` if a new API route or app-service adapter
  flow is added.
* `docs/02_architecture/adr/` only if a major new architectural decision is introduced.
* `docs/03_development_log/` with a development log entry.

Do not update release notes, changelog, version numbers, or deployment documentation for
this task.

## Acceptance Criteria

* The local web UI includes a swing analysis panel.
* The UI can submit already-extracted pose data to an API adapter.
* The API adapter calls `SwingAnalysisApplicationService` and returns deterministic
  analysis and feedback JSON.
* The UI displays score, phase scores, metrics, detected faults, feedback, confidence,
  and limitations.
* Handedness and optional phase frame inputs are passed through to the application
  service.
* Invalid pose input shows a clear UI error and a structured API error.
* Existing upload, library, replay, and health behavior remains unchanged.
* No baseball coaching rules are duplicated in UI JavaScript, templates, API routes,
  media loaders, or storage adapters.
* Tests cover successful and failing API/UI behavior.
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

## Open Questions For Implementation

Resolve these before or during implementation:

* Should the first UI support pasted pose JSON, a pose JSON file upload, a deterministic
  demo pose sequence, or more than one of these input modes?
* Should swing analysis results remain in memory only for this UI task, or should a
  follow-up task add report persistence through storage/application services?
* Should the public API expose `SwingAnalysisConfig` threshold overrides now, or keep
  thresholds internal until calibration and settings UX are designed?

Recommended defaults if no clarification is available:

* Support pasted pose JSON and deterministic demo pose data.
* Keep results in memory only.
* Do not expose threshold overrides in the public UI/API yet.
