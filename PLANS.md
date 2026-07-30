# PLANS.md

## Project: baseball_motion_analysis

## Product Goal

Build a local-PC application that analyzes baseball motion from uploaded videos or ordered image sequences and gives useful feedback about good and bad points in the player's movement.

The current product should run on the user's computer without a hosted web service. Uploaded media, local metadata, and generated reports should stay in the local environment by default.

Initial motion targets:

1. Swing
2. Fielding
3. Throwing
4. Pitching

Current and future platform targets:

1. Local-PC app
2. Web app
3. iPhone app
4. Android app

## Current Strategy

Use a local-PC-first, service-oriented architecture.

Application services should support local UI workflows for upload/import, local storage, replay, motion analysis, scoring, and feedback report generation. The analysis core must not depend on the UI. Future web or mobile adapters can call the same application services or equivalent service interfaces.

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

### Milestone 1: Local Media Upload, Import, and Metadata

Status: IN_PROGRESS

Goals:

* Upload or import video through a local UI
* Upload or import ordered image sequences through a local UI
* Validate file type, readability, ordering, and size
* Store imported media in the local environment
* Extract metadata for videos and image sequences

Acceptance criteria:

* Local application service accepts a sample video fixture
* Local application service accepts a tiny ordered image-sequence fixture
* Imported files are represented by stable local media IDs
* Invalid files and unordered sequences return clear errors
* Unit tests and application-service integration tests exist

DEV001-01 local media input foundation scope:

* Recorded local video file validation, metadata extraction, and frame sampling
* Multiple local image file validation, sorting, and conversion into a common frame sequence
* Local camera stream interface contract for future real-time analysis
* Local filesystem path handling with clear validation errors
* Optional local media copy behavior using a configurable media root
* Common `FrameSequence` model shared by video, image-sequence, and camera inputs

DEV001-01 non-goals:

* Full pose estimation
* Full real-time motion analysis
* Swing, pitching, batting, throwing, or fielding classification
* Production video storage
* Cloud upload/download
* User account management
* Full desktop GUI implementation
* Browser upload endpoints
* FastAPI upload endpoints
* Browser WebSocket camera streaming
* MediaPipe integration

DEV001-01 acceptance criteria:

* A local video file can be validated, opened, and converted into a `FrameSequence`.
* A local image list can be validated, opened, sorted, and converted into a `FrameSequence`.
* A local camera stream interface exists and can be tested without real camera hardware.
* Input logic is separated from pose estimation and motion analysis.
* Local file paths are handled safely with clear validation errors.
* Docs explain recorded video, image-sequence, and camera-stream input modes and limitations.
* Unit tests cover validation, metadata extraction, video sampling, image sequence creation, local copy behavior, and camera interface behavior.
* No large media files are committed.

### Milestone 2: Local Replay MVP

Status: IN_PROGRESS

Goals:

* Replay newly uploaded videos in the UI
* Replay newly uploaded image sequences in the UI
* Browse and replay previously stored files
* Provide replay manifests through application services

Acceptance criteria:

* UI can replay a stored video
* UI can replay a stored image sequence in order
* Replay does not require a hosted web service
* Tests cover replay manifest creation for videos and image sequences

DEV002-01 dual-mode web video upload and replay UI scope:

* Browser-based video upload page served by the existing FastAPI application
* Local browser mode where the app runs on the user's computer at `127.0.0.1`
* Server mode where the same app can run remotely with configurable host, port, media root, database path, and upload limit
* Server-side streamed multipart video uploads into a controlled staging location
* Reuse of the existing `MediaInputService`, video validation, OpenCV metadata extraction, and local media copy behavior
* Stable media IDs, SQLite metadata persistence, and media-ID-based content serving
* HTML5 video replay manifest, video content endpoint, browser seeking, and playback-speed controls
* Uploaded-video deletion through application services, including stored file removal and metadata record removal

DEV002-01 non-goals:

* Pose estimation
* Motion classification
* Swing, pitching, throwing, or fielding analysis
* Feedback reports
* Video annotation overlays
* Image-sequence upload UI
* Camera streaming or WebSocket video streaming
* Automatic transcoding, FFmpeg integration, cloud storage, authentication, authorization, Docker, deployment, or release publishing

DEV002-01 acceptance criteria:

* A user can open `/` in a browser and see a video upload, library, and replay UI.
* The upload endpoint streams uploaded videos to a staging file without loading the whole file into memory.
* Upload size is limited by configuration and failed staging files are cleaned up.
* Existing local media input validation and metadata extraction are reused through application services.
* Imported videos receive stable media IDs and persisted metadata records.
* The browser receives media IDs and replay URLs, not absolute filesystem paths.
* Stored videos are listed and can be replayed through an HTML5 video player.
* Seeking works through a byte-range-capable content endpoint.
* Runtime mode, media root, database path, maximum upload size, host, and port are configurable.
* Browser playback limitations for codecs and non-browser-oriented containers are documented.
* Users can remove an uploaded video from the UI.
* Deletion removes the stored media file when it exists and removes the metadata record.
* Deletion resolves targets only by media ID and does not expose absolute filesystem paths.
* Tests cover repository, file store, replay manifest, upload validation, staging cleanup, range responses, API responses, and existing health behavior.
* Tests cover successful deletion, missing-file deletion cleanup, and invalid media ID deletion errors.

DEV002-01 risks:

* Uploaded videos contain personal information and must stay under configured storage.
* Browser playback codec support varies by browser and operating system.
* Large uploads can exhaust memory or disk space if limits or streaming behavior regress.
* Temporary upload files may remain after errors unless cleanup paths are tested.
* Online server files may be ephemeral depending on the hosting environment.
* Public online deployment requires authentication and authorization that are outside this task.
* Concurrent upload behavior may affect a SQLite metadata index.
* Exact frame-by-frame playback cannot be guaranteed by a normal HTML5 video player.
* Browser seeking requires correct byte-range response behavior.
* Accidental deletion would remove local user media, so the UI must require an explicit user action.
* Deletion must keep metadata and file storage consistent even when a stored file is already missing.

### Milestone 3: Pose Extraction Interface

Status: TODO

Goals:

* Define pose estimation interface
* Add first implementation
* Return frame-level keypoints in a stable internal format

Acceptance criteria:

* Pose estimator can be mocked in tests
* Motion analysis does not depend on a specific pose library directly
* Sample video or image-sequence fixture test exists

### Milestone 4: Swing Analysis MVP

Status: TODO

Goals:

* Detect basic swing phases
* Evaluate simple rule-based checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns swing analysis result
* Result includes good points, bad points, and confidence notes
* Documentation explains current evaluation limitations

### Milestone 5: Fielding Analysis MVP

Status: TODO

Goals:

* Detect basic fielding posture and movement checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns fielding analysis result
* Feedback is understandable to non-engineers
* Tests cover core rule logic

### Milestone 6: Pitching / Throwing Analysis MVP

Status: TODO

Goals:

* Detect basic throwing phases
* Evaluate balance, arm path, stride, and follow-through checkpoints
* Generate feedback

Acceptance criteria:

* Local application service returns pitching analysis result
* Tests cover core rule logic
* Limitations are documented

### Milestone 7: Local UI MVP

Status: IN_PROGRESS

Goals:

* Upload or import videos and ordered image sequences
* Store imported media locally
* Browse uploaded and stored media
* Replay videos and image sequences
* Select motion type
* Display motion scores and feedback reports

Acceptance criteria:

* User can import a video or image sequence
* User can replay newly imported and previously stored media
* User can see analysis result and report
* UI and application services remain separated

### Milestone 8: Release Preparation

Status: IN_PROGRESS

Goals:

* Stabilize local application-service behavior
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
| T-0002 | Define architecture overview  | architecture          | DONE   | Original API-first overview superseded by local-PC-first ADR |
| T-0003 | Configure uv project          | coding                | DONE   | `uv sync` passes |
| T-0004 | Configure tests and lint      | quality-assurance     | DONE   | pytest, ruff, format check, and mypy pass |
| T-0005 | Final review of scaffold      | final-review-planning | DONE   | No blocking issues found |
| T-0006 | Prepare initial release notes | release               | TODO   | v0.1.0 planning     |
| T-0007 | Add CI workflow foundation | release | DONE | `.github/workflows/ci.yml` created |
| T-0008 | Add release-check workflow foundation | release | DONE | `.github/workflows/release-check.yml` created |
| T-0009 | Configure Dependabot updates | release | DONE | GitHub Actions and uv updates configured |
| T-0010 | Update release-agent CI/CD responsibilities | release | DONE | `.codex/agents/release.toml` updated |
| T-0025 | Implement dual-mode web video upload and replay UI | final-review-planning | DONE | DEV002-01; supports Milestone 2 and Milestone 7; video-only browser adapter, no motion analysis |
| T-0026 | Add uploaded-video deletion to web media library | final-review-planning | DONE | DEV002-01 update; delete by media ID through app services; no motion analysis |
| T-0011 | Document release CI/CD gates | release | DONE | `AGENTS.md`, `CHANGELOG.md`, and development log updated |
| T-0012 | Add Docker release/deploy workflow | release | TODO | Future task, not in current scope |
| T-0013 | Add production deployment workflow | release | TODO | Future task, not in current scope |
| T-0014 | Reshape project direction to local-PC-first app | planning | DONE | `AGENTS.md`, agent TOMLs, skill, plans, and docs updated |
| T-0015 | Define local media storage architecture | architecture | TODO | Storage directory, metadata index, privacy boundaries |
| T-0016 | Define local UI technology choice | architecture | TODO | Must support upload/import, replay, and reports without hosted service |
| T-0017 | Implement local media import service | coding | TODO | Videos and ordered image sequences |
| T-0018 | Implement local replay manifests | coding | TODO | Uploaded and stored media |
| T-0019 | Plan local media input foundation | planning | DONE | DEV001-01 scope, non-goals, acceptance criteria, and risks documented |
| T-0020 | Design local media input foundation | architecture | DONE | Recorded video, image sequence, camera interface, optional local copy |
| T-0021 | Implement local media input foundation | coding | DONE | Input-layer only; no pose, analysis, upload endpoint, or WebSocket |
| T-0022 | QA local media input foundation | quality-assurance | DONE | 21 tests pass; required quality commands pass |
| T-0023 | Final review local media input foundation | final-review-planning | DONE | Local-PC scope and prompt acceptance criteria verified |
| T-0024 | Strip notebook outputs without Ruff notebook formatting checks | quality-assurance | DONE | CI and release-check strip notebook outputs; Ruff ignores `notebooks/` formatting |
| T-0027 | Add PR, issue, and security templates | quality-assurance | DONE | GitHub community templates added for review, reporting, and vulnerability handling |

## Open Decisions

| ID     | Decision                | Status                    | Owner        | Link                                                        |
| ------ | ----------------------- | ------------------------- | ------------ | ----------------------------------------------------------- |
| D-0001 | Web framework           | Superseded by local-PC-first direction | architecture | docs/02_architecture/adr/ADR-0001-api-first-architecture.md |
| D-0002 | Pose estimation library | TODO                      | architecture |                                                             |
| D-0003 | Local media storage policy | TODO                   | architecture |                                                             |
| D-0004 | Feedback scoring format | TODO                      | planning     |                                                             |
| D-0005 | Local UI framework      | TODO                      | architecture |                                                             |
| D-0006 | Image-sequence import format | TODO                 | architecture |                                                             |

## Risk Register

| Risk                                                          | Impact | Mitigation                                                              |
| ------------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| Video files contain personal data                             | High   | Keep local by default, avoid committing videos, document privacy policy |
| Image sequences contain personal data                         | High   | Keep local by default, avoid committing images, document privacy policy |
| Pose estimation quality varies by camera angle                | High   | Return confidence notes and limitations                                 |
| Motion feedback may be medically or technically overconfident | High   | Use cautious language and show confidence / uncertainty                 |
| Heavy dependencies may complicate local packaging              | Medium | Add dependencies only after architecture review                         |
| Local filesystem permissions vary by OS                       | Medium | Use configurable storage paths and clear errors                         |
| Future adapters may need API stability                        | Medium | Keep application-service interfaces explicit                            |
| Local media path leakage exposes personal directories          | High   | Keep normal result metadata to source labels or internal references, not absolute paths |
| Codec availability varies across local OpenCV installations   | Medium | Validate OpenCV open/read behavior and report clear errors              |
| Real camera hardware is unavailable in CI                     | Medium | Keep camera tests mocked and interface-only                             |

## Definition of Done

A milestone is complete only when:

* Code is implemented
* Tests pass
* Docs are updated
* Risks are reviewed
* Final planning review is complete
