---
name: baseball-motion-analysis
description: Use when working on baseball_motion_analysis features, architecture, tests, or docs involving local-PC upload/import UI, local media storage, video or image-sequence replay, pose extraction, swing, fielding, throwing, pitching, motion scoring, feedback reports, or baseball-specific motion knowledge. Follow service-oriented UI-independent boundaries and avoid implementing unrequested full motion analysis.
---

# Baseball Motion Analysis

## Purpose

Guide work on `baseball_motion_analysis` features while keeping the application local-PC-first, service-oriented, and independent from any specific UI framework or future API adapter.

Use it for:

* Local UI upload/import of videos
* Local UI upload/import of ordered image sequences
* Local media storage and metadata indexing
* Replay of uploaded and stored videos or image sequences
* Video and image-sequence validation and frame sampling
* Pose estimation
* Swing analysis
* Fielding analysis
* Throwing analysis
* Pitching analysis
* Motion scoring
* Feedback report generation
* Baseball-specific documentation
* Tests for motion evaluation logic

## Core Product Principle

The app should help users understand:

1. What is good about the motion
2. What may need improvement
3. Why it matters
4. What the system is uncertain about

Do not present feedback as a medical diagnosis or as a guaranteed coaching truth.

## Local-PC Product Workflow

Use this product workflow for current feature planning:

```text
local UI upload/import
  -> local storage and metadata index
  -> replay preparation
  -> optional motion type selection
  -> pose estimation
  -> motion analysis and scoring
  -> feedback report generation
  -> local report storage and UI display
```

The app should run on the user's computer without requiring a hosted web service. Future web or mobile adapters may reuse the same application services.

## Motion Analysis Pipeline

Use this conceptual pipeline when implementing motion-analysis features:

```text
video or image-sequence input
  -> media validation
  -> frame sampling
  -> pose estimation
  -> motion phase detection
  -> rule evaluation
  -> scoring
  -> feedback generation
  -> report output
```

## Module Responsibility

Keep responsibilities separated. UI callbacks and any future API routes should call application services, not low-level video, sequence, pose, motion, analysis, feedback, or storage functions directly.

### ui

Responsible for:

* Import/upload controls for videos and image sequences
* Library browsing for locally stored media
* Replay controls for videos and image sequences
* Displaying analysis progress, scores, and reports

Must not:

* Contain baseball mechanics rules
* Write files directly without going through storage/application services

### video

Responsible for:

* Loading video files
* Validating video format
* Extracting metadata
* Preparing replay metadata
* Sampling frames

Must not:

* Evaluate baseball mechanics
* Generate coaching feedback

### sequence

Responsible for:

* Validating ordered image sequences
* Extracting image dimensions and sequence metadata
* Preparing replay metadata
* Sampling frames from ordered images

Must not:

* Evaluate baseball mechanics
* Generate coaching feedback

### pose

Responsible for:

* Extracting body keypoints
* Returning keypoints in a stable internal format
* Hiding implementation details of the pose library

Must not:

* Contain swing, fielding, throwing, or pitching rules directly

### motion

Responsible for:

* Motion-specific domain models
* Swing, fielding, throwing, and pitching phase concepts
* Baseball-specific movement semantics

Must not:

* Load videos directly
* Depend on a concrete pose-estimation library

### analysis

Responsible for:

* Rule evaluation
* Score calculation
* Issue detection
* Confidence handling

### feedback

Responsible for:

* Converting analysis result into user-facing explanation
* Separating good points and improvement points
* Explaining uncertainty clearly

### storage

Responsible for:

* Persisting imported videos and image sequences in a configurable local data directory
* Keeping a metadata index for locally stored media and reports
* Avoiding external uploads by default
* Keeping user media and generated reports out of git

Must not:

* Run pose estimation or baseball rule evaluation directly

## Feedback Requirements

Feedback should include:

* `summary`
* `good_points`
* `improvement_points`
* `drills_or_suggestions`
* `confidence`
* `limitations`

Use cautious language:

* Prefer: "may indicate", "looks like", "based on the visible frames"
* Avoid: "this is definitely wrong", "you must", "injury risk is certain"

## Swing Analysis Initial Checkpoints

For MVP, consider these rough checkpoints:

* Stance balance
* Head stability
* Hip rotation timing
* Bat path
* Weight transfer
* Follow-through

Keep these as rule candidates, not absolute truth.

## Fielding Analysis Initial Checkpoints

For MVP, consider these rough checkpoints:

* Ready position
* Knee bend
* Glove position
* Footwork direction
* Body alignment to ball
* Transfer position

## Pitching / Throwing Analysis Initial Checkpoints

For MVP, consider these rough checkpoints:

* Balance position
* Stride direction
* Hip and shoulder separation
* Arm path
* Release posture
* Follow-through

## Testing Guidance

Prefer deterministic tests.

Use mocks for:

* Pose estimator
* Video file reader
* Image-sequence reader
* Storage layer

Test pure logic with fixed keypoint inputs.

Do not require real large videos or private user images in unit tests.

For local workflows, use integration tests that verify UI-adapter or application-service boundaries without requiring real user videos, external services, or external credentials.

## Documentation Guidance

When motion rules are added or changed, update:

* `docs/04_motion_knowledge/swing.md`
* `docs/04_motion_knowledge/fielding.md`
* `docs/04_motion_knowledge/throwing.md`
* `docs/04_motion_knowledge/pitching.md`

When architecture changes, update:

* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/`

When local-PC product behavior changes, update:

* `docs/01_product/product_brief.md`
* `docs/01_product/feature_catalog.md`
* `PLANS.md`

When new implementations, update documents in:
* `docs/05_manuals/`

## Done Checklist

Before finishing a motion-analysis task:

* [ ] Rule logic is separated from UI callbacks and any API routes
* [ ] Tests exist for normal and edge cases
* [ ] Confidence or limitations are represented
* [ ] User-facing feedback avoids overclaiming
* [ ] Relevant Obsidian docs are updated
