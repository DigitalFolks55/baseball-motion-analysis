# 2026-07-20 Local-PC Direction

## Summary

Reshaped the project direction from a web-first application to a local-PC-first baseball motion analysis application.

## Changes

- Updated `AGENTS.md` to prioritize local UI, local storage, replay, application services, and local analysis workflows.
- Updated `.agents/skills/baseball-motion-analysis/SKILL.md` for local upload/import, image sequences, local storage, replay, analysis, scoring, and feedback reports.
- Updated all `.codex/agents/*.toml` files so planning, architecture, coding, QA, final review, and release agents follow the local-PC-first scope.
- Updated `PLANS.md`, `README.md`, product docs, and architecture docs.
- Added ADR-0002 for the local-PC-first, service-oriented architecture.
- Marked ADR-0001 as superseded for the current product direction.

## Required Product Functions

- Upload or import videos through the UI.
- Upload or import ordered image sequences through the UI.
- Store uploaded media in the local environment.
- Replay uploaded and stored videos or image sequences in the UI.
- Run local pose estimation, swing, fielding, pitching, throwing analysis, motion scoring, and feedback report generation.

## Non-Goals

- No hosted web service implementation.
- No Docker or production deployment workflow.
- No full motion-analysis implementation in this documentation-only change.
