# System Overview

## Architecture Direction

`baseball_motion_analysis` uses an API-first backend so web and future mobile clients can share the same analysis services.

```text
api -> application services -> video -> pose -> motion -> analysis -> feedback
```

The API layer should call application services. It should not call low-level video loading, pose estimation, or baseball motion rule code directly.

## Module Boundaries

- `video`: video loading, validation, metadata extraction, and frame sampling.
- `pose`: pose extraction interfaces and implementations.
- `motion`: baseball motion concepts, motion types, and phase models.
- `analysis`: rule evaluation, scoring, issue detection, and confidence handling.
- `feedback`: user-facing explanation and report generation.
- `api`: HTTP route definitions and request/response boundaries.
- `app`: application factory, entrypoint, and application services.
- `storage`: local or remote persistence.
- `core`: shared configuration, errors, and cross-cutting primitives only.

## Current Foundation

The current scaffold exposes `GET /api/v1/health` through an application service. It does not perform motion analysis.
