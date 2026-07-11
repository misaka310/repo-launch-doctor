# Repo Launch Doctor Design

## Purpose

Repo Launch Doctor checks whether a local repository is easy to start, safe to publish, and honest about what it can do. It produces actionable reports without modifying the scanned repository.

## User flow

1. Run `run-doctor.bat <repository-path>` on Windows, or `python -m repo_launch_doctor scan <repository-path>` on any supported shell.
2. The doctor reads repository files, Git metadata, documentation, scripts, and common project configuration.
3. It writes JSON, Markdown, and standalone HTML reports under `reports/`.
4. The report groups findings by severity and gives the affected path, evidence, and a concrete fix.

## Scope

The first release checks:

- README existence and whether it contains setup, start, verification, requirements, and limitations guidance.
- Whether commands and relative paths mentioned in Markdown resolve to real files or package scripts where statically verifiable.
- Common start entrypoints such as `.bat`, `.cmd`, `.ps1`, package scripts, Python entrypoints, and executable launch files.
- Duplicate or suspicious default ports found in source and documentation.
- Secret-risk file names and tracked sensitive artifacts without printing secret values.
- Generated junk, logs, caches, virtual environments, build outputs, and local configuration that appear tracked.
- Missing favicon declarations or favicon files for detected local web applications.
- Health-check routes documented or implemented for detected local services.
- Test, lint, typecheck, and build commands declared by the project.
- Broken local Markdown links and image references.
- Public-readiness metadata such as license, security notes, configuration examples, and explicit limitations.

The first release does not execute arbitrary commands from the target repository. A later opt-in verification mode may run explicitly allowlisted commands.

## Architecture

- `repo_launch_doctor/cli.py`: command parsing, exit codes, and output paths.
- `repo_launch_doctor/scanner.py`: repository inventory and orchestration.
- `repo_launch_doctor/checks/`: independent checks returning a shared finding model.
- `repo_launch_doctor/models.py`: report and finding dataclasses.
- `repo_launch_doctor/reporters.py`: JSON, Markdown, and standalone HTML output.
- `repo_launch_doctor/config.py`: defaults plus optional `.repo-launch-doctor.json` overrides.
- `tests/fixtures/`: small intentionally healthy and unhealthy repositories.

Each check is read-only and independently testable. A failed check becomes an internal-error finding instead of aborting the whole scan.

## Severity and scoring

- `BLOCKER`: likely secret exposure, missing primary entrypoint, or a public claim that cannot be reproduced.
- `HIGH`: setup is likely broken or key documentation points to missing files.
- `MEDIUM`: usability, verification, or maintainability weakness.
- `LOW`: polish and discoverability issue.
- `INFO`: detected capabilities and commands.

The score starts at 100 and deducts weighted points, but the report always prioritizes concrete findings over the numeric score.

## Safety

- Never modify the scanned repository.
- Never print suspected secret values.
- Skip `.git`, dependency trees, model files, large binaries, and configured exclusions.
- Resolve paths before reading and do not follow links outside the scan root by default.
- Limit file count and file size to keep scans bounded.

## Configuration

An optional `.repo-launch-doctor.json` can define:

- ignored paths and checks;
- expected start commands;
- expected health endpoints;
- expected local ports;
- whether the repository is a web app, library, desktop app, or documentation-only project;
- accepted generated artifacts.

## Verification

- Unit tests for each check and reporter.
- End-to-end tests against healthy and unhealthy fixtures.
- A self-scan of Repo Launch Doctor.
- Windows launcher smoke test where supported.

## Completion criteria

- A fresh clone can run the doctor with Python 3.11+ and no third-party dependencies.
- Healthy and unhealthy fixture scans produce deterministic JSON, Markdown, and HTML reports.
- Secret values are never included in reports.
- Tests pass and the self-scan completes.
- README contains a copy-paste quick start, sample output, limitations, and public-release guidance.
