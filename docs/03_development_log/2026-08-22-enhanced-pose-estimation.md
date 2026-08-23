# 2026-08-22: Enhanced Pose Estimation Diagnostics

## Summary

Implemented DEV006-01 enhanced pose-estimation support for stored-video swing analysis.

The update improves how the app explains and uses pose quality before automatic phase
detection. It keeps the existing local MediaPipe body-pose backend and local
application-service workflow.

## Implementation Notes

- Added MediaPipe candidate switch and ambiguity diagnostics to pose debug output.
- Made temporal smoothing more conservative for high-speed wrist and ankle landmarks,
  with moderate preservation for elbows and knees.
- Added swing-specific frame-quality classification before automatic phase detection.
- Added active swing window detection so long idle lead-in or post-swing sections are
  less likely to distort phase selection.
- Improved estimated impact selection with a constrained late-swing window and additional
  body-motion cues beyond raw wrist velocity.
- Added scoring-evidence diagnostics for metrics affected by low-confidence,
  interpolated, out-of-frame, or heavily stabilized landmarks.
- Extended API responses and compact browser diagnostics with frame quality, active
  window, candidate switch/ambiguity, and scoring-evidence summaries.
- Preserved the limitation that MediaPipe Pose does not detect bat, barrel, ball, or
  exact contact.

## Verification

Targeted checks run during implementation:

```bash
python3 -m compileall src/baseball_motion_analysis
uv run pytest tests/unit/test_pose_estimation.py tests/unit/test_swing_motion_metrics.py tests/integration/test_swing_application_service.py tests/integration/test_swing_video_analysis_api.py tests/integration/test_web_video_upload_replay_api.py
```

Full quality gate results are recorded in `PLANS.md` after final verification.

## DEV006-02 Correction

Implemented the second pose/event-quality pass after real review showed that the main
regression was poor swing event detection rather than raw pose output alone.

### A/B Pose Decision

- Reverted the default MediaPipe candidate-switch holdback to the original best-scored
  candidate behavior by setting the default switch margin to `0.0`.
- Kept candidate-switch rejection as an explicit opt-in tuning behavior when a positive
  margin is configured.
- Retained the confirmed high-speed wrist and ankle smoothing safeguard because
  deterministic tests show it preserves real fast movement.

### Event Detection Changes

- Setup now prefers a stable pre-motion frame before the active swing window.
- Stride now prioritizes lower-body load, knee/ankle/hip movement, head movement, and
  rotation cues instead of wrist movement alone.
- Foot strike now uses quality-accepted candidate frames, the detected setup baseline,
  and lead-foot plant/stabilization cues after stride.
- Estimated impact no longer has a hard late-frame bias and now weights wrist/grip
  motion through contact-zone hand position and rotation cues.
- Follow-through now selects post-impact extension/deceleration when later evidence is
  available.
- Ordering repairs now run in quality-candidate frame space before mapping back to
  original frame indexes, preventing repaired events from landing on rejected frames.
- Phase and event responses now include fallback reasons, and the browser event list
  displays them when present.

### Verification

Targeted checks run before full quality gates:

```bash
uv run pytest tests/unit/test_pose_estimation.py tests/unit/test_swing_motion_metrics.py
uv run pytest tests/integration/test_swing_application_service.py tests/integration/test_swing_video_analysis_api.py tests/integration/test_web_video_upload_replay_api.py
```

## DEV006-03 Enhanced Swing Event Detection

Implemented the next event-detection revision from the available
`docs/99_prompts/DEV006-03_Enhance_pose_estimations_v2.md` prompt. The requested
`DEV006-03_Enhance_pose_estimations_v3.md` file was not present in the repository.

Changes:

- Added typed impact policy values: `body_pose_estimated`, `skip_without_ball`, and
  `require_ball_contact`.
- Added per-event status values so events can be reported as detected, estimated,
  skipped, or unavailable.
- Kept the default body-pose estimated impact path for compatibility.
- Marked impact skipped or unavailable with zero confidence when no-ball policies are
  selected; no ball/contact detector was added.
- Skipped impact-dependent metrics and suppressed impact-phase faults when impact is
  skipped or unavailable.
- Revised setup, stride, foot strike, and follow-through selection semantics to reduce
  late setup drift, trivial setup/stride adjacency, missed first foot plant, and
  unrelated late follow-through frames.
- Added the impact policy to app/API request paths and the browser advanced controls.

Verification:

```bash
uv run pytest tests/unit/test_swing_motion_metrics.py tests/unit/test_swing_analysis.py tests/integration/test_swing_application_service.py tests/integration/test_swing_video_analysis_api.py tests/integration/test_web_video_upload_replay_api.py
```

Remaining risks:

- Event detection is still heuristic and needs annotated real-swing event fixtures.
- Exact impact still requires future bat/ball/contact evidence.

## DEV006-04 Ordered Swing Event State Model

Implemented the DEV006-04 swing event-detection revision.

Changes:

- Added internal lead-leg lift analysis in the motion domain.
- Changed automatic stride selection to prefer visible lead-leg lift peak when present.
- Kept no-stride lower-body load as a lower-confidence fallback with explicit fallback
  reason.
- Made foot strike consume the lead-leg lift state so confident plant detection happens
  after visible lift/descent; no-lift or sparse cases are reported as lower-confidence
  fallbacks.
- Bounded follow-through search to the active swing window plus a small buffer and
  reduced scoring pressure toward idle/reset frames.
- Passed handedness into event detection through `SwingEventDetectionConfig` when the
  app/API caller knows handedness.
- Replaced the hidden advanced impact-policy dropdown in the browser with a visible
  `Impact Detection` On/Off control. The browser default is Off, mapping to skipped
  no-ball impact behavior; API compatibility for explicit policy values remains.

Verification:

```bash
uv run pytest tests/unit/test_swing_motion_metrics.py
uv run pytest tests/unit/test_swing_analysis.py tests/integration/test_swing_application_service.py tests/integration/test_swing_video_analysis_api.py tests/integration/test_web_video_upload_replay_api.py
```

Remaining risks:

- The state model is still heuristic and needs annotated real-swing event fixtures.
- Hitters with minimal or no visible leg lift rely on lower-confidence no-stride
  fallback semantics.
- Exact impact still requires future bat/ball/contact evidence.
