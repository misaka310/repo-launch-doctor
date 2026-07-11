# Repo Launch Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free, read-only repository checker that produces actionable JSON, Markdown, and HTML reports for launchability and public readiness.

**Architecture:** A Python package inventories bounded repository files, runs independent static checks, normalizes findings into dataclasses, and renders three report formats. The CLI never executes target-project commands and only invokes `git ls-files` to identify tracked files when Git is available.

**Tech Stack:** Python 3.11+ standard library, `unittest`, Windows batch launcher, GitHub Actions.

---

### Task 1: Package skeleton and report model

**Files:**
- Create: `pyproject.toml`
- Create: `repo_launch_doctor/__init__.py`
- Create: `repo_launch_doctor/__main__.py`
- Create: `repo_launch_doctor/models.py`
- Test: `tests/test_doctor.py`

- [ ] Define immutable `Finding` and `ScanReport` dataclasses, severity weights, deterministic sorting, summary counts, and score calculation.
- [ ] Add a failing unit test that verifies blocker/high/medium/low ordering and score deductions.
- [ ] Run `python -m unittest discover -s tests -v` and confirm the model test initially fails.
- [ ] Implement the minimum model code and rerun the test until it passes.

### Task 2: Configuration and bounded inventory

**Files:**
- Create: `repo_launch_doctor/config.py`
- Create: `repo_launch_doctor/inventory.py`
- Modify: `tests/test_doctor.py`

- [ ] Test loading defaults and `.repo-launch-doctor.json` overrides for ignored paths, ignored checks, expected ports, expected start commands, and accepted generated paths.
- [ ] Test that inventory excludes `.git`, dependencies, caches, binaries, files over the size limit, and symlinks escaping the repository root.
- [ ] Implement safe JSON validation, normalized relative paths, file-count limits, and optional `git ls-files` tracked-file discovery.

### Task 3: Static checks

**Files:**
- Create: `repo_launch_doctor/checks.py`
- Modify: `tests/test_doctor.py`

- [ ] Add tests for README/setup/start/test/requirements/limitations detection.
- [ ] Add tests for broken local Markdown links and missing referenced images.
- [ ] Add tests for suspicious tracked secret filenames without secret-value disclosure.
- [ ] Add tests for tracked logs, caches, local configs, build output, and virtual environments.
- [ ] Add tests for web-app favicon and health-route detection.
- [ ] Add tests for start entrypoints, declared package scripts, and discovered ports.
- [ ] Implement each check as a pure function returning findings; convert individual check failures into an internal-error finding instead of aborting the scan.

### Task 4: Scan orchestration and reports

**Files:**
- Create: `repo_launch_doctor/scanner.py`
- Create: `repo_launch_doctor/reporters.py`
- Modify: `tests/test_doctor.py`

- [ ] Test an intentionally healthy temporary repository and an intentionally unhealthy temporary repository end to end.
- [ ] Test JSON, Markdown, and standalone HTML creation.
- [ ] Put a realistic secret string inside the unhealthy fixture and assert it never appears in any report.
- [ ] Implement scan orchestration, stable report serialization, HTML escaping, severity sections, score summary, evidence, and recommended fixes.

### Task 5: CLI and Windows launcher

**Files:**
- Create: `repo_launch_doctor/cli.py`
- Create: `run-doctor.bat`
- Create: `.repo-launch-doctor.example.json`
- Modify: `tests/test_doctor.py`

- [ ] Test `scan <path> --output <directory>` and `--fail-on none|blocker|high|medium` exit behavior.
- [ ] Implement concise console output with generated report paths.
- [ ] Add a launcher that uses `py -3` when available and falls back to `python`.

### Task 6: Public documentation and automation

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `.github/workflows/tests.yml`

- [ ] Document the copy-paste quick start, report meanings, checks, configuration, safety guarantees, limitations, and examples.
- [ ] Add a GitHub Actions workflow for Python 3.11, 3.12, and 3.13 on Windows and Ubuntu.
- [ ] Ensure generated reports, caches, and local configuration are ignored.

### Task 7: Verification

- [ ] Run `python -m unittest discover -s tests -v` and require all tests to pass.
- [ ] Run `python -m repo_launch_doctor scan . --output reports/self --fail-on none`.
- [ ] Confirm `reports/self/report.json`, `report.md`, and `report.html` exist and contain no secret values.
- [ ] Run `python -m compileall repo_launch_doctor tests`.
- [ ] Review the final change set for generated junk, absolute local paths, credentials, and unsupported public claims.
