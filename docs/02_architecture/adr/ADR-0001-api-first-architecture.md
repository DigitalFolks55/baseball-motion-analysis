# ADR-0001: API-first Architecture

## Status

Proposed

## Context

The first target is a web application. Future targets include iPhone and Android applications.

If the analysis logic is tightly coupled to the web UI, future mobile support will require rewriting core behavior.

## Decision

Use an API-first architecture.

The backend exposes motion analysis APIs. The web UI consumes these APIs. Future mobile apps should consume the same APIs.

## Consequences

### Positive

- Web and mobile can share backend logic
- Motion analysis core remains reusable
- API tests can verify product behavior
- UI can be replaced without rewriting analysis

### Negative

- Initial setup is slightly more complex than a single simple UI script
- API schema design must be maintained carefully

## Implementation Notes

Main backend layers:

```text
video -> pose -> motion -> analysis -> feedback -> api

API routes should not contain baseball mechanics logic.
