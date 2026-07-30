# Security Policy

## Supported Versions

This project is in early local-PC-first development and has not published a stable release line yet. Security fixes are handled on the `main` branch until versioned releases are established.

## Reporting a Vulnerability

Please do not report suspected vulnerabilities in public GitHub issues.

Use GitHub private vulnerability reporting if it is enabled for this repository. If it is not enabled, contact the repository maintainer privately and include only the minimum detail needed to understand the issue. Do not attach user videos, image sequences, generated reports, secrets, tokens, `.env` files, model weights, or local filesystem paths that may contain personal information.

Helpful report details:

- A short description of the vulnerability and affected workflow.
- Whether the issue involves local media import, video replay, storage, generated reports, CI/CD, dependencies, or release packaging.
- Reproduction steps using synthetic or non-private test data.
- Expected impact and any known workaround.

## Project Security Boundaries

`baseball_motion_analysis` is currently designed as a local-PC application. Uploaded videos, ordered image sequences, metadata, and generated reports should remain on the user's computer by default.

Security and privacy expectations:

- Do not upload user media externally unless the product design explicitly requires it and the user approves it.
- Do not commit user videos, image sequences, generated reports, credentials, `.env` files, model weights, or large binaries.
- Keep local media storage under a configurable data directory that is excluded from git.
- Avoid logging or returning full local file paths because they may contain personal names.
- Use `.env.example` for documented environment variables.

## Response Expectations

The maintainer will acknowledge a valid private vulnerability report when practical, assess severity and scope, and coordinate a fix before public disclosure. Release timing depends on project status, available verification, and whether the issue affects local media privacy, dependency integrity, CI/CD, or packaged artifacts.
