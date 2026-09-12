# DEV007-01 Fix FPS Dependency

## Objective

Make stored-video swing analysis and replay pose overlays behave consistently across
different source frame rates. Preserve the currently acceptable 30 FPS behavior as the
calibration reference while correcting frame-rate-dependent sampling, temporal pose
post-processing, swing event detection, timing metrics, and browser overlay
synchronization.

The implementation must support constant-frame-rate videos below, at, and above 30 FPS.
It must also handle variable or irregular frame timestamps when the decoder exposes
them, with a clear fallback and limitation when reliable presentation timestamps are
unavailable.

This task includes implementation, deterministic tests, documentation, and verification.
It is not a release or deployment task.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Do not stop after planning. Do not run
the release agent or create a release, deployment, Docker setup, hosted service, package
publication, version tag, or GitHub Release.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/ADR-0007-mediapipe-pose-estimator.md`
- `docs/02_architecture/adr/ADR-0008-swing-pose-quality-and-sampling.md`
- `docs/02_architecture/adr/ADR-0011-swing-aspect-aware-measurement-space.md`
- `docs/02_architecture/adr/ADR-0012-enhanced-swing-pose-diagnostics.md`
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/local_media_input_foundation.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Review the relevant implementation:

- `src/baseball_motion_analysis/video/video_loader.py`
- `src/baseball_motion_analysis/video/models.py`
- `src/baseball_motion_analysis/video/replay.py`
- `src/baseball_motion_analysis/pose/models.py`
- `src/baseball_motion_analysis/pose/estimation.py`
- `src/baseball_motion_analysis/motion/swing.py`
- `src/baseball_motion_analysis/analysis/swing.py`
- `src/baseball_motion_analysis/app/swing_services.py`
- `src/baseball_motion_analysis/api/schemas.py`
- `src/baseball_motion_analysis/api/swing_router.py`
- `src/baseball_motion_analysis/ui/web/static/app.js`

Review existing tests for every touched module, especially:

- `tests/unit/test_media_input_video.py`
- `tests/unit/test_pose_estimation.py`
- `tests/unit/test_swing_motion_metrics.py`
- `tests/integration/test_swing_application_service.py`
- `tests/integration/test_swing_video_analysis_api.py`
- `tests/integration/test_web_video_upload_replay_api.py`

## Confirmed Current Defects

### 1. Motion calculations use displacement per sampled frame

Swing motion functions named as velocity calculations currently measure normalized
distance between adjacent sampled frames without dividing by elapsed time. Fixed
per-frame thresholds are then used for active-window, stride, foot-strike, impact, and
follow-through decisions.

The same physical ankle speed was reproduced as approximately `0.048` normalized body
scales per frame at 30 FPS and `0.024` at 60 FPS. The existing foot-plant persistence
threshold classified those inputs differently. This changes the selected phase frames
and therefore the postures and metrics that are scored.

### 2. Sampling cadence and temporal coverage depend on source FPS

The current integer interval is calculated with `round(source_fps / target_fps)`, and the
loader stops after collecting `max_frame_count` samples. This can produce an effective
FPS different from the requested target and can analyze only a prefix of the video.

One reproduced default higher-accuracy case was a five-second 40 FPS video: it sampled
at 40 FPS, reached the 180-frame cap, and stopped near 4.475 seconds. The equivalent
30 FPS video covered the complete clip. A late impact or follow-through can therefore
be absent depending on source FPS.

The current short-clip full-frame branch also changes MediaPipe input cadence solely
because one source has fewer frames under the cap.

### 3. Pose stabilization windows are frame-count based

Outlier comparisons, interpolation gaps, smoothing windows, and high-velocity landmark
checks operate on adjacent frame positions or fixed frame counts. Their real-time
durations change with source or effective FPS, so equivalent movement can be smoothed,
interpolated, or rejected differently.

### 4. Source timestamps assume constant FPS

Video frame timestamps are synthesized as `frame_index / metadata.fps`. This does not
represent variable-frame-rate presentation timestamps and can pass incorrect time values
to MediaPipe video mode and replay overlays.

### 5. Browser overlays are not synchronized to presented video frames

The browser redraws the pose overlay on the HTML media `timeupdate` event. That event can
fire much less frequently than decoded video frames, leaving an old skeleton visible
while playback advances.

Overlay selection also calculates `round(currentTime * manifest.fps)` and compares frame
indexes instead of using each overlay frame's `timestamp_seconds`. This can select the
following constant-FPS frame early and cannot align variable-frame-rate content.

### 6. Existing tests do not establish cross-FPS equivalence

Current tests cover basic metadata and target-FPS sampling, but swing-video integration
tests primarily use small 10 FPS fixtures with mocked pose output. There is no regression
test proving that equivalent motion at different frame rates selects equivalent events
and produces equivalent metrics or scores.

## Required Outcomes

### 1. Define A Timestamp Policy

Create one explicit temporal model shared across video sampling, pose estimation, motion
analysis, and replay overlay metadata.

Required behavior:

- Keep `frame_index` as the stable decoded source-frame identifier.
- Treat `timestamp_seconds` as the presentation time of that source frame.
- Preserve monotonically increasing timestamps through sampling and pose estimation.
- Use decoder-provided presentation timestamps when they are valid and monotonic.
- When decoder timestamps are missing or invalid, fall back to constant-FPS timestamps
  only when valid FPS metadata exists.
- Record a diagnostic or limitation when timestamps are synthesized or repaired.
- Reject or safely repair duplicate, decreasing, non-finite, or negative timestamps
  before calling MediaPipe video mode.
- Do not silently treat variable-frame-rate content as exact constant-frame-rate content.
- Keep normal results and logs free of absolute source paths.

If OpenCV cannot provide reliable presentation timestamps for supported variable-frame-
rate inputs, document that constraint and design the interface so a future decoder can
supply timestamps without changing motion-analysis APIs. Do not add a production
dependency unless the planning and architecture steps explain the need, alternatives,
runtime impact, license, and packaging consequences.

### 2. Sample By Time And Cover The Full Clip

Replace prefix-only, rounded-frame-interval sampling with a timestamp-aware policy.

Required behavior:

- If source FPS is below the requested analysis FPS, use every source frame without
  fabricating frames.
- If source FPS is above the requested analysis FPS, sample close to the requested
  temporal cadence without allowing integer rounding to produce a higher cadence.
- Apply `max_frame_count` across the full usable clip duration. Do not satisfy the cap by
  taking only the first N eligible frames.
- Preserve the first and last usable temporal regions when the cap requires sparse
  sampling, so setup and follow-through are both eligible for analysis.
- Keep selected source frame indexes and timestamps ordered, unique, and deterministic.
- Define how sampling behaves when duration, FPS, total frame count, or timestamps are
  missing or inconsistent.
- Make sampling diagnostics distinguish requested FPS, achieved/effective FPS, temporal
  coverage, cap application, and timestamp source or fallback.
- Review whether short clips should continue using every source frame. Source FPS alone
  must not cause materially different motion interpretation after temporal normalization.
- Preserve cache correctness by including every option that changes sampled pose output
  in the pose cache key.

The architecture step must decide whether the default higher-accuracy mode uses a stable
maximum analysis cadence such as 30 FPS or uses all short-clip frames with fully
time-normalized downstream processing. Record the decision in an ADR. In either case,
equivalent source videos must meet the cross-FPS acceptance criteria below.

### 3. Make Motion Analysis Time-Based

Replace FPS-dependent per-frame motion semantics with elapsed-time-aware calculations.

Required behavior:

- Calculate motion rates using the timestamp delta between observations.
- Define valid minimum and maximum timestamp deltas and handle invalid gaps explicitly.
- Express velocity thresholds in documented time-based units, preferably body scales per
  second for normalized motion and degrees per second for angular motion.
- Calibrate converted thresholds so 30 FPS behavior remains the regression reference
  unless a documented correction is required.
- Audit active-window, setup, stride, foot-strike, impact, and follow-through detection
  for fixed frame-count assumptions.
- Replace persistence and search rules such as "next two frames" with duration-based
  windows where those frames represent time.
- Keep ordering constraints based on sequence positions where they express event order
  rather than elapsed duration.
- Ensure sparse or missing timestamps reduce confidence or produce an explicit fallback
  instead of silently changing threshold meaning.

Audit every helper that calculates or consumes movement, velocity, acceleration,
deceleration, rotation onset, stability, or temporal separation. Renaming misleading
helpers is encouraged when it clarifies units.

### 4. Correct Timing Metrics And Units

`hip_shoulder_separation_timing` currently reports a difference in frame positions. The
same 100 ms delay therefore produces different numeric values at different FPS.

Required behavior:

- Report temporal separation in a real-time unit such as milliseconds or seconds.
- Update metric metadata, API serialization, target thresholds, UI labels, documentation,
  and tests consistently.
- Preserve the scoring intent of the existing 30 FPS minimum lag threshold by converting
  it to the chosen unit, then refine only with documented baseball-motion rationale.
- Audit other output described as frames or timing and make its unit explicit.
- Treat a response-unit change as an API contract change and document it in the ADR.

### 5. Make Pose Post-Processing Time-Aware

Temporal stabilization must represent comparable durations across sampling cadences.

Required behavior:

- Define smoothing by a time window or compute frame neighbors from timestamps.
- Define interpolation eligibility by missing duration, not only missing-frame count.
- Make outlier and high-velocity decisions account for elapsed time.
- Avoid smoothing legitimate high-speed wrist and ankle motion merely because sampling
  cadence changed.
- Preserve raw pose frames for diagnostics.
- Continue exposing stabilization changes, interpolation, rejection, and pose coverage.
- Add timing-related diagnostics or limitations when irregular or sparse samples make
  stabilization unreliable.
- Keep pose extraction independent of swing-specific coaching and scoring rules.

If public environment variables or configuration fields change from frame counts to
durations, either provide a documented compatibility path or clearly record the breaking
configuration change. Do not keep a frame-count name with time-unit behavior.

### 6. Synchronize Replay Overlay To Presented Frames

Use presentation time as the primary browser alignment key.

Required behavior:

- Select overlay frames using returned `timestamp_seconds`, not
  `round(currentTime * fps)`.
- During playback, use `HTMLVideoElement.requestVideoFrameCallback` and its `mediaTime`
  when supported.
- Provide a bounded fallback for browsers without `requestVideoFrameCallback`, such as
  `requestAnimationFrame` while playing plus normal media events.
- Redraw after seeking completes and on loaded metadata, play, pause, resize, overlay
  source changes, and relevant analysis-result changes.
- Start and stop callbacks cleanly so repeated video selection or playback does not create
  multiple update loops.
- Keep the overlay frame-match status and offset based on the same timestamp used to draw
  the pose.
- Do not label an overlay frame exact unless its timestamp matches the presented frame
  within a documented tolerance.
- Keep frame-step controls usable for constant-FPS videos. For variable-frame-rate videos,
  avoid claiming exact single-frame stepping when only average FPS metadata is available.
- Preserve current aspect-aware overlay coordinates, raw/stabilized source controls,
  event markers, evaluation lines, localization, and accessibility behavior.

The UI must only synchronize and render returned analysis data. It must not calculate
baseball motion rules or scoring thresholds.

### 7. Diagnostics And User-Facing Limitations

Make FPS and timing behavior inspectable without exposing implementation noise in the
normal workflow.

Required behavior:

- Sampling diagnostics show source-reported FPS, requested analysis FPS, achieved FPS,
  sampled and total frame counts, analyzed time range, source duration when known, cap
  status, and timestamp source/fallback.
- Warn when temporal coverage excludes a meaningful part of the clip.
- Warn when unreliable timestamps force constant-FPS fallback.
- Keep technical detail in the existing diagnostics area rather than coaching feedback.
- Keep English and Japanese UI strings isolated in the existing localization structure.
- Do not expose local absolute paths or other private media details.

## Architecture Requirements

- `video` owns timestamp extraction, fallback policy, temporal frame sampling, and source
  timing diagnostics.
- `pose` consumes ordered timestamped frames and owns time-aware landmark stabilization.
- `motion` owns time-aware swing phase detection and motion/timing metric calculations.
- `analysis` owns converted metric thresholds, scoring, issue detection, and confidence.
- `app` owns quality-mode orchestration, sampling policy selection, cache keys, and
  browser-neutral diagnostics and overlay output.
- `api` serializes explicit timestamps, units, and diagnostics without calculating them.
- `ui` synchronizes replay and renders results without containing motion-analysis rules.
- Keep application services reusable by future local desktop, web, and mobile adapters.
- Add a new ADR under `docs/02_architecture/adr/` for the timestamp, sampling, and
  time-normalized analysis policy. Update existing ADRs where their current statements
  are superseded.

## Testing Requirements

Use deterministic synthetic poses, fake capture/decoder objects, and tiny generated video
fixtures. Tests must not require private user videos, external services, credentials,
model downloads, or heavy binary assets.

### Video Sampling Unit Tests

Add coverage for:

- Constant source FPS values including 24, 30, 40, 50, 60, and 120 FPS.
- Sources below and above the requested target FPS.
- A non-integer ratio such as 40 to 30 FPS without oversampling or prefix truncation.
- Full-duration coverage when `max_frame_count` is smaller than eligible frames.
- First and final temporal regions represented under a cap.
- Deterministic, ordered, unique indexes and timestamps.
- Missing FPS with valid timestamps.
- Missing timestamps with valid constant FPS.
- Duplicate, decreasing, negative, non-finite, and irregular timestamps.
- Sampling diagnostics and limitations for fallback and incomplete coverage.

### Motion And Analysis Unit Tests

Create one continuous synthetic swing trajectory and resample it at 24, 30, 60, and
120 FPS. Also test an irregular timestamp sequence derived from the same trajectory.

Required assertions:

- Active swing windows represent approximately the same time interval.
- Setup, stride, foot strike, estimated impact, and follow-through timestamps agree
  within a documented temporal tolerance appropriate to the lowest tested cadence.
- Foot-plant persistence and phase detection do not change solely because FPS changes.
- Time-based movement rates agree within numeric tolerance.
- Hip-shoulder separation timing reports the same real-time value and unit.
- Metrics that describe pose geometry remain equivalent within numeric tolerance.
- Metric severities, detected faults, phase scores, and overall score remain equivalent
  unless a phase falls within the documented sampling-resolution tolerance.
- Missing or invalid timestamps follow the documented fallback or limitation path.
- Existing 30 FPS fixtures retain expected behavior after explicit threshold conversion.

Do not make tests pass by using broad tolerances that would hide a one-phase or one-score-
category regression. Document every cross-FPS tolerance and why it is appropriate.

### Pose Stabilization Unit Tests

Add coverage proving that equivalent timestamped landmark trajectories at different FPS:

- Use comparable smoothing durations.
- Interpolate comparable gap durations.
- Reject equivalent outliers consistently.
- Preserve legitimate fast wrist and ankle motion consistently.
- Produce comparable stabilized coordinates at shared timestamps.

Keep notebook-parity or raw mode free of stabilization as currently documented.

### Application, API, And UI Tests

Add coverage for:

- Application-service sampling diagnostics across multiple source FPS values.
- API serialization of timestamp source, analyzed time range, achieved FPS, and changed
  timing metric units.
- Pose cache separation for materially different temporal sampling options.
- Timestamp-based overlay-frame selection with sparse sampled frames.
- Constant and irregular frame timestamps.
- Presented-frame callback lifecycle, seek redraw, and fallback update behavior.
- Exact versus nearest overlay status using timestamp tolerance.
- No `currentTime * fps` dependency in pose-overlay selection.
- Existing upload, replay, localization, overlay toggle, metric line, and error behavior.

Prefer extracting small pure JavaScript timing/selection helpers if that enables meaningful
tests. A static string assertion alone is insufficient to verify playback synchronization.

### Practical Validation

If local non-private test clips at multiple frame rates are available, compare the raw and
stabilized overlays and report results without committing the media. This validation is
helpful but must not replace deterministic automated tests. Do not upload local media or
send it to an external service.

## Documentation Requirements

Update:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- relevant existing ADRs plus a new FPS/timestamp policy ADR
- `docs/03_development_log/` with a dated Obsidian-compatible entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/local_media_input_foundation.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must explain:

- The supported timestamp and frame-rate model.
- How analysis sampling covers the clip under target-FPS and frame-count limits.
- The units used for motion rates and hip-shoulder separation timing.
- How 30 FPS behavior was used as the conversion baseline.
- How pose stabilization windows behave across FPS.
- How browser overlays synchronize to presented video time.
- Variable-frame-rate and decoder timestamp limitations.
- How to interpret timestamp fallback, incomplete coverage, and sparse-sampling warnings.

## Non-Goals

- Do not replace MediaPipe or introduce a new pose model.
- Do not add bat, barrel, ball, or contact detection.
- Do not redesign baseball coaching rules beyond the timing-unit conversions needed for
  FPS independence.
- Do not promise identical MediaPipe landmarks for differently encoded source files;
  require consistent pipeline semantics and bounded downstream results for equivalent
  deterministic pose trajectories.
- Do not add video transcoding, frame interpolation, fabricated poses, or FPS upsampling.
- Do not change fielding, throwing, or pitching analysis unless shared timestamp models
  require a compatibility update. Do not introduce their full analysis implementations.
- Do not add hosted services, cloud upload, telemetry, deployment, Docker, mobile adapters,
  authentication, PyPI publishing, or release work.
- Do not commit videos, model files, generated reports, `.env` files, credentials, or
  heavy fixtures.

## Acceptance Criteria

- Equivalent deterministic swing trajectories sampled at 24, 30, 60, and 120 FPS select
  equivalent swing phases within the documented time tolerance.
- Equivalent trajectories produce consistent time-based motion rates, timing metrics,
  severity categories, faults, phase scores, and overall score within documented numeric
  tolerances.
- Existing acceptable 30 FPS analysis behavior remains the calibration reference and has
  explicit regression coverage.
- Target-FPS sampling does not unexpectedly exceed the target because of integer-ratio
  rounding.
- Applying a frame cap represents the full usable clip rather than analyzing only its
  prefix.
- Pose stabilization uses elapsed-time semantics and produces comparable results across
  tested sampling cadences.
- Decoder timestamps are preserved when reliable; constant-FPS synthesis is explicit and
  diagnosed when used.
- MediaPipe receives valid monotonically increasing timestamps.
- Replay pose overlays are selected by timestamp and updated with presented video frames
  where the browser supports that API.
- Seeking and browsers without presented-frame callbacks still redraw reliably without
  leaking duplicate animation loops.
- Sampling and timing diagnostics clearly expose achieved cadence, analyzed time range,
  fallback status, and limitations.
- Architecture boundaries, localization policy, privacy requirements, and local-PC-first
  behavior remain intact.
- Relevant tests and documentation are updated.
- Final planning review reports no blocking issue.

## Quality Gates

Run after coding:

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

Run any added JavaScript test command documented by the implementation. Do not declare
the task complete if cross-FPS equivalence tests, full-duration sampling tests, overlay
synchronization tests, or required repository quality gates fail.

## Final Review Notes To Capture

During `final-review-planning`, confirm:

- Each confirmed defect has an implementation change and meaningful regression test.
- Time units and thresholds are explicit and consistent across domain models, analysis,
  API schemas, UI labels, and documentation.
- The 30 FPS reference behavior is preserved or every intentional difference is recorded.
- Cross-FPS tolerances are narrow, explained, and do not conceal phase or scoring changes.
- Variable-frame-rate behavior is tested at the timestamp-model boundary and documented.
- Sampling covers the full usable clip under a cap.
- Replay overlay callbacks are cleaned up correctly and timestamp selection is shared by
  drawing and status reporting.
- No secrets, private media, large videos, model files, generated reports, or unrelated
  user changes are included.
- All required quality gates pass.
- No release or deployment was created.
