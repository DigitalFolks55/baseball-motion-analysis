# ADR-0010: Swing Evaluation Overlay Lines

## Status

Accepted

## Context

DEV004-02 adds optional visual guide lines to the replay overlay for swing evaluation v2.
The browser already renders pose keypoints, event labels, and raw/stabilized pose sources
on a canvas over the video. Evaluation lines need to reference v2 metric evidence while
remaining optional and toggleable without rerunning analysis.

The app must remain local-PC-first and service-oriented. UI and API adapters must not
own baseball thresholds, deductions, fault rules, or coaching decisions.

## Decision

Return evaluation-line overlay primitives from the stored-video swing analysis
application service and serialize them through the API as browser-safe data.

The service contract uses normalized points and metadata:

* metric name
* phase
* evidence frame index
* optional source keypoint names
* explicit start and end normalized points
* label
* severity
* confidence
* style
* color role

The application service builds these primitives from already computed v2 analysis
evidence and pose frames. It skips lines when required keypoints are missing, and marks
fallback lines such as grip-trajectory attack angle with lower-confidence styling when
bat keypoints are not available.

The API serializes the returned primitives only. The browser stores them separately from
pose keypoints and draws them on the existing letterbox-aware overlay canvas only when
the `Evaluation Lines` toggle is on.

## Consequences

### Positive

* Evaluation-line geometry stays owned by service output instead of browser rules.
* Users can show or hide lines without rerunning analysis or changing playback speed.
* Future UI, API, or mobile adapters can reuse the same browser-neutral primitives.
* Missing bat/ball evidence remains explicit because MediaPipe supplies body landmarks
  only.

### Negative

* The first overlay set is limited to body-pose and fallback grip-path evidence.
* Labels and line density must stay conservative so the replay does not become cluttered.

## Follow-Ups

* Add calibrated bat, barrel, and ball evidence lines when future detectors provide those
  keypoints.
* Add browser screenshot-level checks for representative portrait and letterboxed video
  clips when UI automation coverage is expanded.
