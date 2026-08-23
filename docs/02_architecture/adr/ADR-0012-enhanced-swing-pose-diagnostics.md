# ADR-0012: Enhanced Swing Pose Diagnostics And Active Window Detection

## Status

Accepted

## Context

DEV003-06 and DEV003-07 added MediaPipe body-pose diagnostics, raw/stabilized pose
output, and motion-aware swing event detection. Real swing videos can still produce
poor results when weak body frames influence phase selection, idle video sections
dominate the event window, MediaPipe candidate selection is ambiguous, or stabilization
changes high-speed wrist and ankle landmarks.

The app must remain local-PC-first. UI and API adapters must display diagnostics without
owning pose-estimator internals or baseball scoring rules.

## Decision

Enhance the stored-video swing path with additional local diagnostics and phase-selection
guards:

```text
sampled frames
  -> MediaPipe raw pose frames
  -> player candidate selection with switch/ambiguity diagnostics
  -> stabilized pose frames
  -> swing frame-quality classification
  -> active swing window detection
  -> constrained estimated impact selection
  -> v2 analysis and scoring-evidence diagnostics
```

The `pose` module continues to own MediaPipe result mapping, candidate scoring, and
stabilization. It reports candidate switch and ambiguity counts in
`PoseDebugDiagnostics`. DEV006-02 reverted the DEV006-01 default candidate-switch
holdback because the original best-scored-candidate behavior can produce better pose
quality when the next candidate is genuinely stronger. Candidate-switch rejection remains
available only when an explicit positive `candidate_switch_margin` is configured.

The `motion` module owns swing-specific frame-quality classification and active window
detection because those checks depend on swing phase landmarks and movement cues. It
marks weak or rejected phase-detection frames while preserving original frame indexes
and timestamps. DEV006-02 corrected phase detection so setup is selected from stable
pre-motion frames when available, stride prioritizes lower-body load, foot strike uses
the detected setup baseline and lead-foot plant/stabilization cues, and follow-through
uses post-impact extension/deceleration rather than a trivial next-frame fallback.

The `app` layer returns browser-safe diagnostics for frame quality, active swing window,
and scoring evidence. The API serializes those structures without local paths or model
paths. The browser renders compact counts and frame ranges only.

Impact remains an estimated body-motion window. Selection now considers wrist/grip
motion, acceleration/deceleration, contact-zone hand position, and rotation cues without
a hard late-frame bias, but it still does not claim exact bat-ball contact.

DEV006-03 extends the same decision with explicit event availability semantics. The
motion domain owns `SwingEventDetectionConfig`, `SwingImpactDetectionPolicy`, and
`SwingEventStatus`; app/API layers only pass the selected policy and serialize the
result. The default `body_pose_estimated` policy preserves existing behavior and marks
impact as estimated. `skip_without_ball` marks impact skipped, and
`require_ball_contact` marks impact unavailable until a future ball/contact detector
exists. No bat, ball, barrel, or contact detector is introduced by this decision.

When impact is skipped or unavailable, analysis treats impact-dependent metrics as not
evaluated and suppresses impact-phase faults that would otherwise use the proxy impact
frame as contact evidence. The proxy frame remains only for ordering, replay alignment,
and UI display compatibility.

DEV006-03 also revises event-selection semantics: setup biases to the earliest stable
stance, stride requires sustained lower-body onset with separation from setup when
possible, foot strike prefers the first sustained lead-foot plant, and follow-through
prefers the first stable finish/extension plateau instead of unrelated late frames.

DEV006-04 keeps the public phase model stable and revises the internal motion-owned
event state model. Automatic detection now looks for lead-leg lift before treating
stride as confident. When a lead-leg lift is visible, the public stride frame is the
lead-leg lift peak; when no lift is visible, stride uses a lower-confidence no-stride
lower-body-load fallback with an explicit reason. Foot strike consumes the lead-leg
state and is confident only after prior lift/descent/plant evidence, or it is marked as a
no-stride/sparse fallback.

Follow-through selection is bounded to the active swing window plus a small buffer and
uses the first swing-related finish after extension/rotation evidence rather than
searching all remaining clip frames. Browser UI now exposes a visible `Impact Detection`
On/Off control that maps to existing backend policy values; no event logic moves into
the UI.

DEV006-05 clarifies the display contract for skipped and unavailable events. The
motion-owned phase model still retains a proxy impact frame for ordering and
compatibility, but the application event window now carries explicit visibility and
overlay flags. API and UI adapters use those flags so skipped impact remains available
as status metadata without appearing as a normal detected contact event or replay event
label.

DEV006-05 also narrows the meaning of impact-dependent scoring. Truly contact-specific
metrics and impact-phase faults remain suppressed when impact is skipped or unavailable.
Non-contact metrics that can still provide useful no-ball feedback may use documented
fallback anchors with lower confidence: head translation uses setup-to-foot-strike
evidence, and follow-through posture/balance uses foot-strike-to-finish evidence.

DEV006-06 supersedes the DEV006-04 browser-control decision and DEV006-05 browser
default for the normal product path. The backend policy enum remains for API
compatibility, but the local browser UI no longer exposes an impact-off selector and
always sends `body_pose_estimated` for normal swing analysis. Impact quality is improved
in the motion domain instead: the detector refines impact after foot strike using
wrist/grip motion transition, contact-zone hand position, lead-side bracing, and
rotation evidence, with penalties for early pre-contact or late finish-only frames.
Weak estimated-impact evidence is represented by lower event confidence and fallback
metadata, not by skipped normal impact.

## Consequences

### Positive

* Idle lead-in and post-swing frames are less likely to distort phase selection.
* Event detection is less likely to treat wrist waggle as stride, maximum ankle
  displacement as foot strike, late hand extension as impact, or the immediate next
  frame as follow-through.
* Impact-dependent scoring can be explicitly skipped when the user wants no-ball
  evaluation instead of body-pose estimated contact.
* Event rows and phase responses expose whether each event is detected, estimated,
  skipped, or unavailable.
* Skipped impact no longer appears as a normal event label or overlay marker in no-ball
  browser results.
* No-ball videos retain selected non-contact feedback instead of losing all
  follow-through scoring evidence.
* Stride and foot strike are less likely to be inverted because foot strike depends on
  prior lead-leg lift evidence or an explicit no-stride fallback.
* Follow-through is less likely to drift into idle/reset frames after the swing.
* Weak pose frames can be ignored or down-weighted before automatic phase detection.
* Poor results can be attributed more clearly to sampling, raw pose quality, player
  tracking, stabilization, active-window fallback, event-order repair, or scoring
  evidence limitations.
* High-speed wrist and ankle landmarks are less likely to be over-smoothed.
* Service boundaries remain reusable by future web, mobile, or desktop adapters.

### Negative

* Phase detection is still heuristic until calibrated swing fixtures and bat/ball
  tracking exist.
* No-ball impact policy still reduces scored metric coverage because contact-specific
  impact metrics become not evaluated.
* Hitters with little or no visible leg lift rely on lower-confidence fallback semantics.
* More diagnostics increase response size slightly.
* Candidate indexes are MediaPipe-result local diagnostics, not persistent player IDs.

## Follow-Ups

* Add bat tip, barrel, ball, and contact detection as a separate evidence source.
* Add calibrated annotated swing fixtures for phase and threshold tuning.
* Add camera-angle and side-view suitability scoring.
