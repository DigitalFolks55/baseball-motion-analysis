# 2026-09-08 FPS-Independent Swing Analysis

## Summary

Implemented DEV007-01 timing fixes for stored-video swing analysis and replay overlays.
The work keeps the local-PC-first service boundary: video owns timestamp extraction and
sampling, pose owns MediaPipe timestamp use and stabilization, motion owns swing timing
semantics, analysis owns converted thresholds and units, and API/UI layers serialize or
render returned data.

## Changes

- Added timestamp provenance and sampling diagnostics to video metadata.
- Replaced prefix-only frame sampling with timestamp-aware selection across the usable
  clip duration.
- Kept higher-accuracy stored-video analysis on a 30 FPS maximum cadence, with balanced
  at 24 FPS and faster at 12 FPS.
- Converted pose smoothing and interpolation compatibility settings to duration-based
  behavior using the 30 FPS reference.
- Converted swing motion helper thresholds to elapsed-time rates and changed
  `hip_shoulder_separation_timing` output to milliseconds.
- Updated replay overlay selection to use returned `timestamp_seconds` and presented
  video frame callbacks where browsers support them.
- Updated docs for timestamp policy, sampling coverage, timing units, diagnostics,
  stabilization duration, and OpenCV/VFR limitations.

## Verification

- Added deterministic unit coverage for full-duration sampling, source FPS values below
  and above a 30 FPS target, timestamp fallback/repair diagnostics, duration-based pose
  stabilization, and timestamp-based hip/shoulder timing.
- Added a Node-backed pytest check that executes the browser overlay timing helper logic
  from `app.js` and verifies timestamp selection instead of `currentTime * fps` matching.

## Notes

- OpenCV remains the decoder for this task. Presentation timestamp reliability can vary
  by container and backend, so constant-FPS synthesis or timestamp repair is explicitly
  diagnosed instead of hidden.
- No release, deployment, Docker setup, model download, uploaded media, or generated
  report artifact was created.
