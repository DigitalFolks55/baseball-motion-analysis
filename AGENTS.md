# AGENTS.md

## Project

Repository name: `baseball_motion_analysis`

This project is a baseball motion analysis application. It loads baseball videos and evaluates important motion types such as:

* Swing
* Fielding
* Pitching / throwing

The product should identify good points and bad points in the player's motion and generate understandable feedback for players, coaches, and parents.

The first target is a web application. Future targets include iPhone and Android applications, so the architecture must stay API-first and UI-independent.

## Working Language

* User-facing documentation should be written in English unless requested otherwise.
* Code, module names, class names, function names, and commit messages should use English.
* Technical notes may use English.

## Development Principles

1. Keep domain logic independent from UI.
2. Keep video loading, pose estimation, motion evaluation, and feedback generation separated.
3. Prefer small, testable modules.
4. Do not hard-code baseball coaching rules inside API routes.
5. Do not commit large videos, model weights, credentials, or generated artifacts.
6. Use `uv` for dependency and environment management.
7. Use Obsidian-compatible Markdown for development logs, architecture notes, and feature documentation.

## Architecture Direction

Use this separation:

* `video`: video loading, validation, frame sampling
* `pose`: keypoint extraction interface and implementations
* `motion`: swing, fielding, pitching domain logic
* `analysis`: scoring, rule evaluation, issue detection
* `feedback`: natural language feedback and report generation
* `api`: HTTP API endpoints
* `app`: application entrypoint
* `storage`: local or remote file persistence

The API layer must call application services, not low-level video or pose functions directly.

## Agent Workflow

Use the following AI agent workflow.

1. `planning`

   * Clarify goal, scope, acceptance criteria, risks, and task breakdown.
   * Update `PLANS.md`.
   * Create or update Obsidian docs when product behavior changes.

2. `architecture`

   * Design module boundaries, interfaces, data flow, and architectural decisions.
   * Create ADRs under `docs/02_architecture/adr/` for important decisions.

3. `coding`

   * Implement code according to the plan and architecture.
   * Keep changes small and testable.
   * Use type hints.
   * Prefer explicit names over clever abstractions.

4. `quality-assurance`

   * Add and run tests.
   * Check edge cases, regression risks, typing, formatting, and linting.
   * Verify behavior against acceptance criteria.

5. `final-review-planning`

   * Planning agent performs final review.
   * Confirm the implementation matches original requirements.
   * Confirm docs, tests, and release notes are updated.
   * Identify unresolved risks before release.

6. `release`

   * Prepare release notes, version bump, changelog, and deployment checklist.
   * Confirm GitHub Actions CI and release-check workflows are green before release.
   * Confirm version consistency across `pyproject.toml`, `CHANGELOG.md`, and the GitHub Release tag.
   * Confirm no secrets, user videos, large videos, model files, `.env` files, or generated reports are included.
   * Do not release if tests fail or final planning review is incomplete.
   * Do not release if CI/CD checks fail.

## Required Before Coding

Before implementing any feature, Codex must read:

* `AGENTS.md`
* `PLANS.md`
* Relevant docs under `docs/`
* Existing tests for the touched module

For motion-analysis features, also read:

* `.agents/skills/baseball-motion-analysis/SKILL.md`
* `docs/04_motion_knowledge/`

## Required After Coding

After modifying code, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

## Testing Policy

Minimum required tests:

* Unit tests for pure logic
* Integration tests for API behavior
* Fixture-based tests for video metadata and frame extraction
* No tests should require real user videos or external credentials

Avoid committing heavy binary test data. Use tiny fixtures only.

## Documentation Policy

Use Obsidian-compatible Markdown.

Update documentation when:

* A feature is added or changed
* Motion evaluation rules change
* Architecture boundaries change
* API behavior changes
* A major decision is made

Use:

* `docs/01_product/feature_catalog.md` for feature descriptions
* `docs/02_architecture/adr/` for architecture decisions
* `docs/03_development_log/` for daily development logs
* `docs/04_motion_knowledge/` for baseball motion knowledge

## Dependency Policy

Use `uv`.

Allowed commands:

```bash
uv add <package>
uv add --group dev <package>
uv remove <package>
uv sync
uv lock
uv run <command>
```

Do not edit `uv.lock` manually.

Before adding production dependencies, explain:

* Why it is needed
* Alternative options
* Runtime impact
* License or deployment concern if relevant

## Security and Privacy

Videos may contain personal information. Treat video files as sensitive user data.

Rules:

* Do not log full file paths if they may include personal names.
* Do not upload videos externally unless explicitly required by the product design.
* Do not commit videos, secrets, tokens, or local environment files.
* Keep `.env` out of git.
* Use `.env.example` for documented environment variables.

## Release and CI/CD Policy

Before release, the release agent must confirm:

* GitHub Actions CI is green for the release commit.
* The `release-check` workflow is green.
* `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, and `uv run pytest` pass.
* `CHANGELOG.md` is updated.
* Version values are consistent across `pyproject.toml`, `CHANGELOG.md`, and the GitHub Release tag.
* Final-review-planning approval exists.
* No secrets, user videos, large videos, model files, `.env` files, or generated reports are included.

Block release if any required CI/CD, quality, version, privacy, or final-review check fails.

Current release boundaries:

* Do not add Docker deployment unless explicitly requested.
* Do not add production deployment unless explicitly requested.
* Do not publish to PyPI unless explicitly requested.

## Definition of Done

A task is done only when:

* Implementation matches the plan
* Tests are added or updated
* `uv run pytest` passes
* Lint and format checks pass
* Relevant docs are updated
* `PLANS.md` status is updated
* Final planning review has no blocking issue
