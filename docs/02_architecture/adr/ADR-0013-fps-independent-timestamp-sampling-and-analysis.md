# ADR-0013: FPS-Independent Timestamp, Sampling, And Analysis Policy

## Status

Accepted

## Context

Stored-video swing analysis was calibrated around the currently acceptable 30 FPS path,
but several implementation details still use sampled-frame positions as a proxy for real
time. Different source frame rates can therefore change sampled temporal coverage, pose
stabilization duration, swing phase selection, movement thresholds, reported timing
metrics, and browser overlay synchronization.

The confirmed DEV007-01 defects include:

- Movement helpers calculate normalized displacement per sampled frame instead of
  elapsed-time rates.
- Video sampling uses rounded frame intervals and stops at the first `max_frame_count`
  samples, so high-FPS videos can be oversampled or analyzed only as a prefix.
- Pose smoothing, short-gap interpolation, outlier rejection, and high-velocity landmark
  protection use frame-count windows.
- Source timestamps are synthesized from `frame_index / fps`, which hides variable or
  irregular presentation timing.
- Browser overlays select frames with `currentTime * fps` and redraw from coarse media
  events rather than presented video frame times.

The app must remain local-PC-first. UI and API adapters must render and serialize timing
data without owning decoder policy, timestamp repair, pose post-processing, baseball
motion thresholds, scoring, or feedback logic.

## Decision

Adopt one timestamp-first temporal contract across video loading, pose estimation, swing
motion analysis, scoring, diagnostics, API serialization, and browser overlay rendering.

### Timestamp Model

`frame_index` remains the stable decoded source-frame identifier. `timestamp_seconds`
becomes the presentation time for that source frame, after validation or repair by the
video layer. Motion, pose, app, API, and UI code must not reinterpret `frame_index` as
elapsed time.

The video layer owns timestamp extraction and normalization:

- Prefer decoder-provided presentation timestamps when they are finite, non-negative, and
  strictly increasing. With the current OpenCV implementation, `CAP_PROP_POS_MSEC` is a
  best-effort timestamp source and must be diagnosed as such.
- When decoder timestamps are missing or globally invalid and valid constant-FPS metadata
  exists, synthesize timestamps as `frame_index / source_fps`.
- When decoder timestamps are mostly valid but contain isolated duplicate or decreasing
  values, repair to the next valid monotonic time using the smaller of the local cadence
  estimate or 1 ms, then record timestamp-repair diagnostics.
- Reject or skip frames with non-finite or negative timestamps unless valid FPS metadata
  permits a full constant-FPS synthesis for the source.
- If a stored-video swing analysis cannot produce at least two ordered timed frames from
  decoder timestamps or valid FPS metadata, fail with a structured timing limitation
  rather than silently running frame-count semantics.
- MediaPipe video mode receives integer milliseconds derived from the repaired
  monotonically increasing presentation timestamps. Any final millisecond duplicate is
  advanced by 1 ms and counted in diagnostics.

Diagnostics should expose timestamp provenance without absolute local paths. Add
structured values rather than parsing warning strings, for example:

- `timestamp_source`: `decoder`, `opencv_pos_msec`, `constant_fps`, or `repaired`
- `timestamp_fallback_reason`: `missing_decoder_timestamps`,
  `invalid_decoder_timestamps`, `missing_fps`, or `millisecond_collision`
- `timestamp_repair_count`
- `timestamp_limitations`

OpenCV timestamp support is container/backend-dependent. DEV007-01 will not add PyAV,
FFmpeg bindings, or another production decoder dependency. The `video` module should
shape its implementation around a replaceable decoder/timing helper so a future decoder
can provide stronger variable-frame-rate presentation timestamps without changing pose,
motion, analysis, API, or UI contracts.

### Full-Duration Time-Based Sampling

Replace prefix-only interval sampling for analysis paths with timestamp-aware uniform
selection across the full usable clip. Keep `FrameSamplingOptions` as the public video
sampling input, but interpret `target_fps` and `max_frame_count` through time, not
rounded source-frame intervals.

For a timed source:

1. Decode or discover ordered source frame candidates with source frame indexes and
   normalized timestamps.
2. If the source cadence is below the requested analysis cadence, select every usable
   source frame. Do not fabricate frames, interpolate images, or upsample poses.
3. If the source cadence is above the requested cadence, compute
   `cadence_count = floor(duration_seconds * requested_fps) + 1` and never select more
   frames than that cadence permits.
4. Apply `max_frame_count` to the whole usable time range:
   `selected_count = min(eligible_source_count, cadence_count, max_frame_count)`.
5. Select `selected_count` desired timestamps evenly from first usable timestamp through
   last usable timestamp, then choose the nearest unique source frame for each desired
   timestamp with deterministic tie-breaking toward the earlier source frame.
6. Preserve ordered, unique `frame_index` and `timestamp_seconds` values. Include first
   and final usable temporal regions whenever at least two frames can be selected.

If duration metadata is missing but decoded timestamps are monotonic, sampling uses the
first and last decoded timestamps as the usable range. If timestamps are synthesized from
FPS and total frame count is missing, the usable range is discovered by decoding. If
target FPS is missing, explicit `sample_every_n_frames` remains supported for generic
media-loading compatibility, but stored-video swing analysis should use quality-mode
target cadences.

Sampling diagnostics must distinguish:

- source-reported FPS
- requested analysis FPS
- achieved FPS over the sampled time range
- sampled and total frame counts
- analyzed start/end/duration
- source duration when known
- cap application
- timestamp source, fallback, and repair counts
- whether temporal coverage is incomplete

### Quality-Mode Cadence And 30 FPS Compatibility

Higher-accuracy stored-video swing analysis uses a stable maximum analysis cadence of
30 FPS by default. Balanced remains 24 FPS, and faster remains 12 FPS. Existing caps are
retained as defaults: higher accuracy 180 frames, balanced 120 frames, faster 60 frames.

The previous short-clip full-frame branch is superseded for stored-video swing analysis.
A 60 FPS short clip should no longer feed MediaPipe twice as often as an equivalent
30 FPS clip solely because it is under the old full-frame cap. Low-FPS sources, such as
24 FPS, still use every source frame because the app does not create frames that do not
exist.

The existing `full_frame_max_frame_count` request field should remain accepted for
backward compatibility during DEV007-01, but default quality-mode analysis must not use
it to bypass the target cadence. Public docs and diagnostics should treat full-frame
analysis as true only when every source frame was selected because the source cadence was
at or below the requested cadence, or because a future explicit all-frames mode is added.

This preserves 30 FPS behavior as the calibration baseline while reducing performance
variance and cache churn for higher-FPS uploads. Any test or fixture that intentionally
requests non-default sampling must include the timing-affecting request options in the
pose cache key.

### Pose Interface And Time-Aware Post-Processing

Pose estimation continues to sit behind the `PoseEstimator` interface and consumes
ordered `FrameData`. The pose module owns MediaPipe result mapping, player selection,
timestamp conversion to MediaPipe milliseconds, raw pose preservation, and temporal
post-processing. It must not contain swing scoring or coaching rules.

Replace frame-count stabilization settings with duration settings:

- `smoothing_window_seconds`, default `0.100` seconds, converted from the old
  3-frame-at-30-FPS behavior.
- `max_interpolation_gap_seconds`, default `0.067` seconds, converted from the old
  2-frame-at-30-FPS behavior.

Keep a compatibility path for existing environment variables:

- If new duration settings are unset, `BMA_MEDIAPIPE_SMOOTHING_WINDOW=3` maps to
  `0.100` seconds.
- If new duration settings are unset, `BMA_MEDIAPIPE_MAX_INTERPOLATION_GAP_FRAMES=2`
  maps to `0.067` seconds.
- Emit configuration deprecation documentation and diagnostics where practical. Do not
  keep frame-count names while changing them to seconds behavior.

Outlier rejection and high-velocity smoothing protection must account for elapsed time.
Thresholds that previously represented per-sample displacement at the 30 FPS reference
cadence are converted to rates by multiplying by 30:

```text
body_scales_per_second = legacy_body_scales_per_30fps_frame * 30
degrees_per_second = legacy_degrees_per_30fps_frame * 30
```

Notebook-parity mode remains raw and unstabilized. Normal mode returns raw and
stabilized pose frames plus diagnostics for smoothing, interpolation, rejection,
timestamp repair, pose coverage, and timing limitations. Irregular or sparse samples
should reduce confidence or add limitations instead of silently changing stabilization
meaning.

### Time-Based Swing Motion And Analysis

The `motion` module owns elapsed-time-aware swing phase detection and motion metric
calculation. Helpers that calculate or consume movement, velocity, acceleration,
deceleration, rotation onset, stability, persistence, or temporal separation must use
timestamp deltas.

Use these units:

- normalized linear motion rate: body scales per second
- angular motion rate: degrees per second
- timing separations: milliseconds in public metric output

Adjacent-frame rate calculations require a positive finite delta. Treat deltas below
1 ms as invalid. Treat adjacent deltas above 250 ms as sparse for velocity/event
detection; the implementation may skip those rate samples or lower event confidence, but
must record a limitation instead of applying 30 FPS thresholds to them.

Rules that express event order may remain sequence-position based. Rules that express
persistence or search duration must become duration-based. The legacy "next two frames"
or "two-frame persistence" behavior maps to `2 / 30 = 0.067` seconds unless a more
specific baseball rationale is documented.

Preserve 30 FPS scoring intent by converting existing per-frame thresholds to time-based
thresholds using the 30 FPS baseline. A changed result at 30 FPS must be treated as a
regression unless the coding or QA phase documents a deliberate correction.

### Hip-Shoulder Separation Timing Contract

`hip_shoulder_separation_timing` changes from a frame-position difference to
milliseconds. This is an API contract change and must be updated consistently in domain
models, analysis thresholds, API serialization, UI labels, docs, and tests.

The old default minimum lag was `1.0` frame at 30 FPS. The new default minimum is:

```text
33.333 milliseconds
```

The metric value is `shoulder_rotation_onset_timestamp - hip_rotation_onset_timestamp`
in milliseconds. Positive values mean hips lead shoulders. Negative values mean
shoulders lead hips. Existing 30 FPS fixtures should continue to evaluate the same
severity category after this conversion.

### Application, API, And Cache Boundaries

`SwingVideoAnalysisApplicationService` owns quality-mode selection, request option
normalization, local orchestration, in-memory pose caching, and browser-neutral overlay
output. The API serializes explicit units and diagnostics. The UI renders those returned
values and must not calculate timing policy, timestamp repair, swing events, metric
thresholds, score deductions, or feedback.

The pose cache key must include every option that can change sampled pose output:

- media ID
- quality mode
- normalized requested target FPS
- normalized max frame count
- timestamp source/fallback policy version
- pose mode and overlay source when they affect generated overlay data
- MediaPipe model path identity or configured backend identity
- pose-estimator processing settings
- stabilization duration settings
- event policy only if it affects cached overlay/event output

The cache remains session-local and path-private. Diagnostics and normal logs must not
include absolute source paths, model paths, or local user directory names.

### Browser Presented-Frame Synchronization

Browser overlay selection uses overlay `timestamp_seconds` as the primary key. Remove
`round(currentTime * fps)` from pose-frame matching.

Add small pure JavaScript helpers for testability:

- choose the nearest overlay frame by timestamp with deterministic tie-breaking toward
  the earlier overlay frame
- compute exact-vs-nearest status from the same timestamp used for drawing
- start and stop one overlay update loop per selected media/result

Use `HTMLVideoElement.requestVideoFrameCallback` and callback `mediaTime` during
playback when available. On browsers without that API, use a bounded
`requestAnimationFrame` loop while playing plus media events for loaded metadata, seek,
pause, resize, overlay-source changes, and analysis-result changes. Cancel pending
callbacks when media selection or analysis results change.

An overlay match is exact only when the drawn overlay timestamp is within
`min(10 ms, half the median overlay sample interval)` of the presented media time. The
same offset is used for the status label and drawing. Constant-FPS frame-step buttons can
continue to seek by `1 / fps` when FPS is known; for variable-frame-rate or synthesized
timing, labels should not claim exact single-frame stepping.

### Dependency, Packaging, And Privacy

Do not add a new production decoder dependency for DEV007-01. OpenCV remains the decoder
implementation, with explicit timestamp-source diagnostics and documented VFR limits.

No media is uploaded externally. No user videos, model weights, generated reports,
credentials, `.env` files, or heavy fixtures should be committed. Local media storage
remains configurable and isolated from git.

## Consequences

### Positive

- Equivalent deterministic swing trajectories at 24, 30, 60, and 120 FPS can be tested
  against the same time-based phase and scoring expectations.
- The accepted 30 FPS behavior remains the conversion baseline while high-FPS videos no
  longer change analysis solely by feeding more sampled frames into MediaPipe.
- Frame caps preserve setup and follow-through eligibility across the clip instead of
  analyzing only a prefix.
- Variable or irregular timestamp handling becomes inspectable through diagnostics.
- Pose, motion, analysis, API, and UI responsibilities remain separated.
- Browser overlays align with presented media time where supported.

### Negative

- Higher-FPS short clips may produce fewer analyzed frames than before, which can change
  results when the old behavior benefited from accidental oversampling.
- OpenCV cannot guarantee reliable presentation timestamps for every VFR container or
  backend, so some files will still use diagnosed constant-FPS synthesis.
- Time-based sampling may require a timing discovery pass before decoding selected image
  frames, increasing implementation complexity.
- API clients must handle the hip-shoulder timing unit change from frames to
  milliseconds.
- Configuration compatibility for old frame-count stabilization fields adds temporary
  complexity.

## Implementation Handoff

Coding should proceed in this order:

1. Add video timing diagnostics and a tested timestamp-normalization helper in the
   `video` module.
2. Replace interval/prefix sampling with uniform full-duration time sampling and update
   sampling diagnostics.
3. Update app quality-mode defaults so stored-video swing analysis keeps stable 12, 24,
   or 30 FPS target cadences rather than short-clip full-frame sampling.
4. Convert MediaPipe/stabilization frame-count settings to duration settings with the
   compatibility path described above.
5. Convert motion/event helpers and analysis thresholds to elapsed-time units, including
   hip-shoulder lag in milliseconds.
6. Extend app/API schemas with timing diagnostics and explicit metric units.
7. Extract/test browser overlay timestamp helpers and wire
   `requestVideoFrameCallback` with a clean fallback lifecycle.

## Follow-Ups

- Revisit whether a PyAV or FFmpeg-based decoder is worth the packaging cost after
  DEV007-01 tests expose real OpenCV timestamp gaps.
- Add calibrated annotated swing fixtures when non-private data is available.
- Consider persistent pose/result caching only after cache keys include a durable timing
  and pose-configuration fingerprint.
