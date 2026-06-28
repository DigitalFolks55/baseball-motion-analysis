# PLANS.md

## Project: baseball_motion_analysis

## Product Goal

Build a web application that analyzes baseball motion from uploaded videos and gives useful feedback about good and bad points in the player's movement.

Initial motion targets:

1. Swing
2. Fielding
3. Throwing
4. Pitching

Future platform targets:

1. Web app
2. iPhone app
3. Android app

## Current Strategy

Use an API-first architecture.

The backend should expose motion analysis APIs that can be reused by future mobile apps. The first UI can be simple, but the analysis core must not depend on the web UI.

## Agent Workflow

```text
planning
  -> architecture
  -> coding
  -> quality-assurance
  -> final-review-planning
  -> release
```

## Milestones

### Milestone 0: Repository Foundation

Status: IN_PROGRESS

Goals:

* Create initial repository structure
* Configure uv
* Configure Codex agents
* Configure Obsidian docs
* Configure lint, format, type check, and tests

Acceptance criteria:

* `uv sync` works
* `uv run pytest` works
* `uv run ruff check .` works
* `uv run mypy src` works
* GitHub Actions CI workflow exists for lint, format check, type check, and tests
* Release-check workflow exists for release validation and artifact build
* Dependabot is configured for GitHub Actions and uv dependency updates
* Basic docs exist
* Agent workflow is documented

### Milestone 1: Video Upload and Metadata

Status: TODO

Goals:

* Load uploaded video
* Validate file type and size
* Extract metadata
* Sample frames

Acceptance criteria:

* API accepts a sample video
* Invalid files return clear errors
* Unit tests and API tests exist

### Milestone 2: Pose Extraction Interface

Status: TODO

Goals:

* Define pose estimation interface
* Add first implementation
* Return frame-level keypoints in a stable internal format

Acceptance criteria:

* Pose estimator can be mocked in tests
* Motion analysis does not depend on a specific pose library directly
* Sample fixture test exists

### Milestone 3: Swing Analysis MVP

Status: TODO

Goals:

* Detect basic swing phases
* Evaluate simple rule-based checkpoints
* Generate feedback

Acceptance criteria:

* API returns swing analysis result
* Result includes good points, bad points, and confidence notes
* Documentation explains current evaluation limitations

### Milestone 4: Fielding Analysis MVP

Status: TODO

Goals:

* Detect basic fielding posture and movement checkpoints
* Generate feedback

Acceptance criteria:

* API returns fielding analysis result
* Feedback is understandable to non-engineers
* Tests cover core rule logic

### Milestone 5: Pitching / Throwing Analysis MVP

Status: TODO

Goals:

* Detect basic throwing phases
* Evaluate balance, arm path, stride, and follow-through checkpoints
* Generate feedback

Acceptance criteria:

* API returns pitching analysis result
* Tests cover core rule logic
* Limitations are documented

### Milestone 6: Web UI MVP

Status: TODO

Goals:

* Upload video from browser
* Select motion type
* Display feedback report

Acceptance criteria:

* User can upload a video
* User can see analysis result
* API and UI remain separated

### Milestone 7: Release Preparation

Status: IN_PROGRESS

Goals:

* Stabilize API
* Confirm CI/CD readiness
* Add release checklist
* Update README and CHANGELOG
* Final planning review

Acceptance criteria:

* All tests pass
* GitHub Actions CI is green
* GitHub Actions release-check is green
* Release artifacts build with `uv build`
* Version is consistent across `pyproject.toml`, `CHANGELOG.md`, and the GitHub Release tag
* CHANGELOG.md is updated
* No secrets, user videos, large videos, model files, `.env` files, or generated reports are included
* Documentation is complete for MVP
* Release notes are prepared

## Current Task Board

| ID     | Task                          | Owner Agent           | Status | Notes               |
| ------ | ----------------------------- | --------------------- | ------ | ------------------- |
| T-0001 | Create project scaffold       | planning              | DONE   | Packages, docs, tests, and placeholders created |
| T-0002 | Define architecture overview  | architecture          | DONE   | API-first overview documented |
| T-0003 | Configure uv project          | coding                | DONE   | `uv sync` passes |
| T-0004 | Configure tests and lint      | quality-assurance     | DONE   | pytest, ruff, format check, and mypy pass |
| T-0005 | Final review of scaffold      | final-review-planning | DONE   | No blocking issues found |
| T-0006 | Prepare initial release notes | release               | TODO   | v0.1.0 planning     |
| T-0007 | Add CI workflow foundation | release | DONE | `.github/workflows/ci.yml` created |
| T-0008 | Add release-check workflow foundation | release | DONE | `.github/workflows/release-check.yml` created |
| T-0009 | Configure Dependabot updates | release | DONE | GitHub Actions and uv updates configured |
| T-0010 | Update release-agent CI/CD responsibilities | release | DONE | `.codex/agents/release.toml` updated |
| T-0011 | Document release CI/CD gates | release | DONE | `AGENTS.md`, `CHANGELOG.md`, and development log updated |
| T-0012 | Add Docker release/deploy workflow | release | TODO | Future task, not in current scope |
| T-0013 | Add production deployment workflow | release | TODO | Future task, not in current scope |

## Open Decisions

| ID     | Decision                | Status                    | Owner        | Link                                                        |
| ------ | ----------------------- | ------------------------- | ------------ | ----------------------------------------------------------- |
| D-0001 | Web framework           | Proposed: FastAPI backend | architecture | docs/02_architecture/adr/ADR-0001-api-first-architecture.md |
| D-0002 | Pose estimation library | TODO                      | architecture |                                                             |
| D-0003 | Video storage policy    | TODO                      | architecture |                                                             |
| D-0004 | Feedback scoring format | TODO                      | planning     |                                                             |

## Risk Register

| Risk                                                          | Impact | Mitigation                                                              |
| ------------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| Video files contain personal data                             | High   | Keep local by default, avoid committing videos, document privacy policy |
| Pose estimation quality varies by camera angle                | High   | Return confidence notes and limitations                                 |
| Motion feedback may be medically or technically overconfident | High   | Use cautious language and show confidence / uncertainty                 |
| Heavy dependencies may complicate deployment                  | Medium | Add dependencies only after architecture review                         |
| Mobile support may require API stability                      | Medium | Keep API-first design from start                                        |

## Definition of Done

A milestone is complete only when:

* Code is implemented
* Tests pass
* Docs are updated
* Risks are reviewed
* Final planning review is complete
