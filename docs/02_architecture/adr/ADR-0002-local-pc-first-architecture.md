# ADR-0002: Local-PC-first Architecture

## Status

Accepted

## Context

The current product direction is a local-PC application. Users should be able to import videos or ordered image sequences, store them locally, replay them in the UI, run motion analysis locally, and view generated feedback reports without requiring a hosted web service.

The project may later add web, iPhone, or Android targets. To avoid rewriting core behavior, the local UI should not own video processing, pose estimation, motion analysis, scoring, feedback generation, or storage policy.

## Decision

Use a local-PC-first, service-oriented architecture.

The primary runtime path is:

```text
local UI -> application services -> storage -> video/sequence -> pose -> motion -> analysis -> feedback
```

Application services are the boundary between UI adapters and core behavior. The existing HTTP API scaffold may remain as a future adapter, but new product behavior should not assume a hosted web service.

## Consequences

### Positive

- Users can keep sensitive videos and image sequences on their own computer.
- Local upload, storage, replay, analysis, and report generation can be implemented without hosted infrastructure.
- The analysis core remains reusable by future UI, web, or mobile adapters.
- Tests can target application services and pure domain logic without UI or network requirements.

### Negative

- Local packaging and filesystem permissions become product concerns.
- The local storage index must be designed carefully to avoid private path leakage.
- Future web or mobile adapters may need adapter-specific storage and replay implementations.

## Implementation Notes

Initial module responsibilities:

- `ui`: local import, library, replay, analysis launch, and report display.
- `app`: application services and entrypoints.
- `storage`: configurable local media and report persistence.
- `video`: video validation, metadata, replay preparation, and frame sampling.
- `sequence`: ordered image-sequence validation, metadata, replay preparation, and frame sampling.
- `pose`: keypoint extraction behind a stable interface.
- `motion`: baseball motion models and phase concepts.
- `analysis`: rule evaluation, scoring, issue detection, and confidence handling.
- `feedback`: understandable report generation.
- `api`: optional future adapter only.

UI callbacks and future API routes must call application services instead of low-level modules directly.
