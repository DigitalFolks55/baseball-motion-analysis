---
name: baseball-motion-analysis
description: Use when working on baseball_motion_analysis features, architecture, tests, or docs involving video loading, pose extraction, swing, fielding, throwing, pitching, motion scoring, feedback reports, or baseball-specific motion knowledge. Follow API-first boundaries and avoid implementing unrequested full motion analysis.
---

# Baseball Motion Analysis

## Purpose

Guide work on `baseball_motion_analysis` features while keeping the backend API-first and the baseball domain logic independent from UI routes.

Use it for:

* Video upload and frame sampling
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

## Motion Analysis Pipeline

Use this conceptual pipeline when implementing motion-analysis features:

```text
video input
  -> video validation
  -> frame sampling
  -> pose estimation
  -> motion phase detection
  -> rule evaluation
  -> scoring
  -> feedback generation
  -> report output
```

## Module Responsibility

Keep responsibilities separated. API routes should call application services, not low-level video, pose, motion, analysis, or feedback functions directly.

### video

Responsible for:

* Loading video files
* Validating video format
* Extracting metadata
* Sampling frames

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
* Storage layer

Test pure logic with fixed keypoint inputs.

Do not require real large videos in unit tests.

For API behavior, use integration tests that verify route/service boundaries without requiring real user videos or external credentials.

## Documentation Guidance

When motion rules are added or changed, update:

* `docs/04_motion_knowledge/swing.md`
* `docs/04_motion_knowledge/fielding.md`
* `docs/04_motion_knowledge/throwing.md`
* `docs/04_motion_knowledge/pitching.md`

When architecture changes, update:

* `docs/02_architecture/system_overview.md`
* `docs/02_architecture/adr/`

## Done Checklist

Before finishing a motion-analysis task:

* [ ] Rule logic is separated from API routes
* [ ] Tests exist for normal and edge cases
* [ ] Confidence or limitations are represented
* [ ] User-facing feedback avoids overclaiming
* [ ] Relevant Obsidian docs are updated
