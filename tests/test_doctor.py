from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from repo_launch_doctor.cli import main
from repo_launch_doctor.config import load_config
from repo_launch_doctor.models import Finding, ScanReport
from repo_launch_doctor.reporters import render_html
from repo_launch_doctor.scanner import scan_repository
from repo_launch_doctor.schema import validate_report_payload


class RepoLaunchDoctorTests(unittest.TestCase):
    def test_report_orders_findings_calculates_score_and_verdict(self) -> None:
        report = ScanReport(
            repository="sample",
            generated_at="2026-07-11T00:00:00Z",
            files_scanned=4,
            paths_discovered=8,
            findings=[
                Finding("low", "LOW", "Low", "README.md", "e", "r"),
                Finding("blocker", "BLOCKER", "Blocker", ".env", "e", "r"),
                Finding("medium", "MEDIUM", "Medium", "app.py", "e", "r"),
                Finding("high", "HIGH", "High", "start.bat", "e", "r"),
            ],
            metadata={"scan_complete": True},
        )

        self.assertEqual(
            [finding.severity for finding in report.sorted_findings()],
            ["BLOCKER", "HIGH", "MEDIUM", "LOW"],
        )
        self.assertEqual(report.score, 30)
        self.assertEqual(report.verdict, "FAIL")
        self.assertEqual(report.to_dict()["schema_version"], "1.0")

    def test_incomplete_report_has_no_score(self) -> None:
        report = ScanReport(
            repository="sample",
            generated_at="2026-07-11T00:00:00Z",
            files_scanned=1,
            paths_discovered=2,
            metadata={"scan_complete": False},
        )
        self.assertEqual(report.verdict, "INCOMPLETE")
        self.assertIsNone(report.score)

    def test_generated_report_conforms_to_report_v1_schema_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            report = scan_repository(root)
            self.assertEqual(validate_report_payload(report.to_dict()), [])
            incomplete = report.to_dict()
            incomplete["verdict"] = "INCOMPLETE"
            incomplete["score"] = None
            incomplete["metadata"]["scan_complete"] = False
            self.assertEqual(validate_report_payload(incomplete), [])

    def test_report_schema_rejects_verdict_score_and_structure_mismatches(self) -> None:
        report = ScanReport("sample", "2026-01-01T00:00:00Z", 0, 0, metadata={"scan_complete": True}).to_dict()
        invalid = []
        changed = dict(report); changed["score"] = None; invalid.append(changed)
        changed = dict(report); changed["metadata"] = {"scan_complete": False}; invalid.append(changed)
        changed = dict(report); changed["counts"] = {"HIGH": 0}; invalid.append(changed)
        incomplete = dict(report); incomplete["verdict"] = "INCOMPLETE"; incomplete["score"] = 100; incomplete["metadata"] = {"scan_complete": False}; invalid.append(incomplete)
        incomplete = dict(report); incomplete["verdict"] = "INCOMPLETE"; incomplete["score"] = None; incomplete["metadata"] = {"scan_complete": True}; invalid.append(incomplete)
        for payload in invalid:
            self.assertTrue(validate_report_payload(payload), payload)

    def test_config_loads_defaults_and_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps(
                    {
                        "ignore_paths": ["archive/**"],
                        "ignore_checks": ["missing-security-doc"],
                        "expected_ports": [8717],
                        "expected_start_commands": ["start.bat"],
                        "expected_health_endpoints": ["/health"],
                        "accepted_generated_paths": ["public/generated-demo/**"],
                        "project_type": "web",
                        "max_paths": 500,
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)

            self.assertIn("**/.git/**", config.ignore_paths)
            self.assertIn("**/.benchmark-cache/**", config.ignore_paths)
            self.assertIn("**/.current-audit-cache/**", config.ignore_paths)
            self.assertIn("archive/**", config.ignore_paths)
            self.assertEqual(config.expected_ports, (8717,))
            self.assertEqual(config.expected_start_commands, ("start.bat",))
            self.assertEqual(config.project_type, "web")
            self.assertEqual(config.max_paths, 500)

    def test_unknown_config_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"max_fiels": 10}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Unknown configuration keys"):
                load_config(root)

    def test_safety_checks_cannot_be_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"ignore_checks": ["secret-risk-file"]}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "cannot be ignored"):
                load_config(root)

    def test_hyphenated_windows_launcher_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run-doctor.bat").write_text("@echo off\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )
            self.assertIn("run-doctor.bat", report.metadata["start_commands"])

    def test_descriptive_root_shell_launcher_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "runqemu.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "run-tests.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "examples").mkdir()
            (root / "examples" / "start-example.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertIn("runqemu.sh", report.metadata["start_commands"])
            self.assertNotIn("run-tests.sh", report.metadata["start_commands"])
            self.assertNotIn("examples/start-example.sh", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_env_example_is_not_treated_as_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".env.example").write_text("API_KEY=replace-me\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file"
                    and finding.path == ".env.example"
                    for finding in report.findings
                )
            )

    def test_tracked_npmrc_without_auth_is_not_treated_as_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".npmrc").write_text(
                "registry=https://registry.npmjs.org/\nengine-strict=true\n",
                encoding="utf-8",
            )
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file"
                    and finding.path == ".npmrc"
                    for finding in report.findings
                ),
                report.findings,
            )

    def test_tracked_npmrc_with_auth_assignment_is_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            auth_key = "//registry.npmjs.org/:_auth" + "Token"
            value = "local-package-credential"
            (root / ".npmrc").write_text(f"{auth_key}={value}\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            finding = next(
                finding
                for finding in report.findings
                if finding.check_id == "secret-risk-file" and finding.path == ".npmrc"
            )
            self.assertEqual("BLOCKER", finding.severity)
            self.assertNotIn(value, finding.evidence)

    def test_tracked_mode_env_without_sensitive_assignment_is_not_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".env.production").write_text(
                "PUBLIC_BASE_URL=https://example.invalid\nFEATURE_ENABLED=true\nTOKEN_EXPIRATION=3600\n",
                encoding="utf-8",
            )
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file"
                    and finding.path == ".env.production"
                    for finding in report.findings
                )
            )

    def test_tracked_mode_env_with_sensitive_assignment_is_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            value = "deployment-secret-value"
            (root / ".env.production").write_text(
                f"PUBLIC_BASE_URL=https://example.invalid\nDEPLOY_TOKEN={value}\n",
                encoding="utf-8",
            )
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            finding = next(
                finding
                for finding in report.findings
                if finding.check_id == "secret-risk-file"
                and finding.path == ".env.production"
            )
            self.assertEqual("BLOCKER", finding.severity)
            self.assertNotIn(value, finding.evidence)

    def test_tracked_env_template_expression_is_not_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".env.production").write_text(
                "DEPLOY_TOKEN=${DEPLOY_TOKEN}\n", encoding="utf-8"
            )
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file"
                    and finding.path == ".env.production"
                    for finding in report.findings
                )
            )

    def test_tracked_secret_is_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            value = "private-value-do-not-copy"
            (root / ".env").write_text(f"TOKEN={value}\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)
            secret = next(
                finding for finding in report.findings if finding.check_id == "secret-risk-file"
            )

            self.assertEqual(secret.severity, "BLOCKER")
            self.assertNotIn(value, secret.evidence)

    def test_git_ignored_env_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=private\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file" and finding.path == ".env"
                    for finding in report.findings
                )
            )

    def test_gitignore_fallback_works_without_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=private\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")

            report = scan_repository(root)

            self.assertEqual(report.metadata["ignore_detection_source"], ".gitignore-fallback")
            self.assertNotIn("secret-risk-file", {finding.check_id for finding in report.findings})
            self.assertNotIn("generated-artifact-present", {finding.check_id for finding in report.findings})

    def test_gitignore_fallback_respects_negation_for_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".gitignore").write_text(".env*\n!.env.production\n", encoding="utf-8")
            (root / ".env.local").write_text("TOKEN=private-local\n", encoding="utf-8")
            (root / ".env.production").write_text("DEPLOY_TOKEN=private-production\n", encoding="utf-8")

            report = scan_repository(root)

            secret_paths = {
                finding.path
                for finding in report.findings
                if finding.check_id == "secret-risk-file"
            }
            self.assertNotIn(".env.local", secret_paths)
            self.assertIn(".env.production", secret_paths)

    def test_tracked_idea_and_ds_store_are_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".idea").mkdir()
            (root / ".idea" / "workspace.xml").write_text("<project />", encoding="utf-8")
            (root / ".DS_Store").write_bytes(b"desktop")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            paths = {
                finding.path
                for finding in report.findings
                if finding.check_id == "generated-artifact-present"
            }
            self.assertIn(".idea", paths)
            self.assertIn(".DS_Store", paths)

    def test_source_build_directories_are_not_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / "build").mkdir()
            (root / "build" / "build.ts").write_text("export const build = true;\n", encoding="utf-8")
            (root / "build" / "build.yaml").write_text("name: source-build\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "build"
                    for finding in report.findings
                )
            )

    def test_tracked_build_output_is_detected_even_when_content_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / "build").mkdir()
            (root / "build" / "app.js").write_text("bundle", encoding="utf-8")
            (root / ".gitignore").write_text("build/\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", "-f", "build/app.js")
            self._git(root, "add", "README.md", "LICENSE", "SECURITY.md", "package.json", "index.html", "favicon.ico", "server.js", ".gitignore")

            report = scan_repository(root)

            self.assertTrue(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "build"
                    for finding in report.findings
                )
            )

    def test_untracked_generated_directory_is_reported_when_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            self._git(root, "init")
            self._git(root, "add", ".")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")

            report = scan_repository(root)

            self.assertTrue(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "node_modules"
                    for finding in report.findings
                )
            )

    def test_git_ignored_generated_directory_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "node_modules"
                    for finding in report.findings
                )
            )

    def test_nested_dependency_tree_is_not_read_but_tracked_paths_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            nested = root / "packages" / "app" / "node_modules" / "pkg"
            nested.mkdir(parents=True)
            (nested / "index.js").write_text("secret-looking = 'not scanned'", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertTrue(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "packages/app/node_modules"
                    for finding in report.findings
                )
            )
            self.assertGreater(
                report.metadata["skipped_reasons"]["content_ignored_directories"], 0
            )

    def test_hidden_dependency_directory_is_excluded_from_content_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            nested = root / ".cache" / "node_modules"
            nested.mkdir(parents=True)
            (nested / "secret.txt").write_text("TOKEN=not-read", encoding="utf-8")

            report = scan_repository(root)

            self.assertGreater(
                report.metadata["skipped_reasons"]["content_ignored_directories"], 0
            )

    def test_max_paths_marks_report_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            for index in range(5):
                (root / f"file-{index}.txt").write_text("x\n", encoding="utf-8")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"max_paths": 3}), encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertEqual(report.verdict, "INCOMPLETE")
            self.assertIsNone(report.score)
            self.assertFalse(report.is_complete)
            self.assertIn("scan-incomplete", {finding.check_id for finding in report.findings})

    def test_max_files_marks_report_incomplete_but_path_checks_continue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "a.txt").write_text("a\n", encoding="utf-8")
            (root / "z").mkdir()
            (root / "z" / "secrets.json").write_text('{"token":"x"}\n', encoding="utf-8")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"max_files": 1}), encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertEqual(report.verdict, "INCOMPLETE")
            self.assertIsNone(report.score)
            self.assertIn(
                "scan-incomplete", {finding.check_id for finding in report.findings}
            )
            self.assertTrue(
                any(finding.path == "z/secrets.json" for finding in report.findings)
            )
            self.assertGreater(report.metadata["skipped_reasons"]["content_file_limit"], 0)

    def test_static_web_with_favicon_ico_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "index.html").write_text(
                '<!doctype html><html><head><link rel="icon" href="favicon.ico"></head></html>',
                encoding="utf-8",
            )
            (root / "favicon.ico").write_bytes(b"ico")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"project_type": "static-web"}), encoding="utf-8"
            )

            report = scan_repository(root)
            ids = {finding.check_id for finding in report.findings}

            self.assertNotIn("missing-favicon", ids)
            self.assertNotIn("missing-start-entrypoint", ids)
            self.assertIn("open index.html", report.metadata["start_commands"])

    def test_favicon_declaration_must_point_to_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "index.html").write_text(
                '<!doctype html><html><head><link rel="icon" href="missing.ico"></head></html>',
                encoding="utf-8",
            )
            (root / "favicon.ico").write_bytes(b"ico")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"project_type": "static-web"}), encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertIn(
                "missing-favicon", {finding.check_id for finding in report.findings}
            )

    def test_runtime_signals_exclude_tests_docs_and_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_server.py").write_text(
                "PORT = 8123\nHEALTH = '/health'\n# pytest example\n", encoding="utf-8"
            )
            (root / "docs").mkdir()
            (root / "docs" / "example.md").write_text(
                "Open http://127.0.0.1:8765/status\n", encoding="utf-8"
            )
            (root / "pyproject.toml").write_text(
                '[project]\nname="sample"\nversion="0.1.0"\n', encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertEqual(report.metadata["ports"], [])
            self.assertEqual(report.metadata["health_endpoints"], [])
            self.assertNotIn(
                "python -m pytest", report.metadata["verification_commands"]
            )
            self.assertNotIn(
                "python -m unittest discover -s tests",
                report.metadata["verification_commands"],
            )

    def test_pyproject_scripts_are_python_cli_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pyproject.toml").write_text(
                '[project]\nname="sample"\nversion="0.1"\n[project.scripts]\nsample = "sample.cli:main"\n',
                encoding="utf-8",
            )
            report = scan_repository(root)
            self.assertEqual(report.metadata["project_type"], "cli")
            self.assertIn("sample", report.metadata["start_commands"])
            self.assertNotIn("missing-start-entrypoint", {f.check_id for f in report.findings})

    def test_pyproject_gui_scripts_are_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pyproject.toml").write_text(
                '[project]\nname="sample"\nversion="0.1"\n[project.gui-scripts]\nsample-gui = "sample.app:main"\n',
                encoding="utf-8",
            )
            report = scan_repository(root)
            self.assertIn("sample-gui", report.metadata["start_commands"])

    def test_package_bin_is_a_node_cli_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "package.json").write_text(
                json.dumps({"name": "sample-cli", "bin": {"sample": "cli.js"}}),
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertIn("sample", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_docs_only_repository_is_not_required_to_have_a_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "guide.md").write_text("# Guide\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertEqual("docs", report.metadata["project_type"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_make_run_target_is_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "Makefile").write_text("run:\n\tgo run ./cmd/server\n", encoding="utf-8")
            (root / "go.mod").write_text("module example.com/app\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertIn("make run", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_root_dockerfile_entrypoint_is_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "Dockerfile").write_text(
                'FROM alpine\nCOPY app /app\nENTRYPOINT ["/app"]\n', encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertIn("Dockerfile ENTRYPOINT", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_readme_launch_command_is_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "README.md").write_text(
                "# App\n\n## Usage\n\n```bash\ndotnet run --project App\n```\n",
                encoding="utf-8",
            )
            (root / "App.csproj").write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup></Project>',
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertIn("dotnet run --project App", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_browser_extension_manifest_is_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            extension = root / "extension"
            extension.mkdir()
            (extension / "manifest.json").write_text(
                json.dumps({"manifest_version": 3, "name": "Example", "version": "1.0"}),
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertIn("load browser extension", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_root_go_main_is_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
            (root / "main.go").write_text("package main\nfunc main() {}\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertIn("go run .", report.metadata["start_commands"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_package_library_is_not_required_to_have_a_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "example-library",
                        "main": "index.js",
                        "exports": {".": "./index.js"},
                        "peerDependencies": {"react": ">=18"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "index.js").write_text("export const value = 1;\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertEqual("library", report.metadata["project_type"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_dotnet_library_is_not_required_to_have_a_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "Example.csproj").write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>',
                encoding="utf-8",
            )
            (root / "Example.cs").write_text("public class Example {}\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertEqual("library", report.metadata["project_type"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_dotnet_web_sdk_is_not_classified_as_a_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "WebApp.csproj").write_text(
                '<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>',
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertNotEqual("library", report.metadata["project_type"])
            self.assertIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_maven_aggregator_is_not_required_to_have_a_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pom.xml").write_text(
                "<project><modelVersion>4.0.0</modelVersion><packaging>pom</packaging><modules><module>core</module></modules></project>",
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertEqual("library", report.metadata["project_type"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_documentation_workspace_is_not_required_to_have_a_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "README.md").write_text(
                "# Company command center\n\nA documentation and operations workspace.\n",
                encoding="utf-8",
            )
            (root / "strategy").mkdir()
            (root / "strategy" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "policy.json").write_text("{}\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertEqual("docs", report.metadata["project_type"])
            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )

    def test_concrete_readme_verification_commands_count_without_testing_heading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(
                "# App\n\n## Quick checks\n\n```bash\nruff check .\nmypy src\npytest\n```\n",
                encoding="utf-8",
            )

            findings = {finding.check_id for finding in scan_repository(root).findings}

            self.assertNotIn("readme-missing-verification", findings)

    def test_batch_build_command_counts_as_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(
                "# Desktop app\n\n## Build & Run\n\n```bat\nbuild.bat\nbuild.bat run\n```\n",
                encoding="utf-8",
            )

            findings = {finding.check_id for finding in scan_repository(root).findings}

            self.assertNotIn("readme-missing-verification", findings)

    def test_manual_testing_command_counts_as_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(
                "# UI library\n\nUse `npm run playground` for local development and manual testing.\n",
                encoding="utf-8",
            )

            findings = {finding.check_id for finding in scan_repository(root).findings}

            self.assertNotIn("readme-missing-verification", findings)

    def test_broken_pyproject_does_not_create_a_phantom_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pyproject.toml").write_text("[project.scripts\nbroken", encoding="utf-8")
            report = scan_repository(root)
            self.assertNotIn("broken", report.metadata["start_commands"])

    def test_empty_pyproject_scripts_table_is_not_an_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pyproject.toml").write_text("[project]\nname='x'\n[project.scripts]\n", encoding="utf-8")
            report = scan_repository(root)
            self.assertIn("missing-start-entrypoint", {f.check_id for f in report.findings})
            self.assertEqual(report.metadata["start_commands"], [])

    def test_multiple_python_cli_commands_are_collected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "pyproject.toml").write_text(
                "[project]\nname='x'\n[project.scripts]\nalpha='x:main'\nbeta='x:main'\n",
                encoding="utf-8",
            )
            report = scan_repository(root)
            self.assertEqual({"alpha", "beta"}, set(report.metadata["start_commands"]))

    def test_main_py_detection_uses_exact_basename_and_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "main.py").write_text("", encoding="utf-8")
            (root / "src" / "example").mkdir(parents=True)
            (root / "src" / "example" / "main.py").write_text("", encoding="utf-8")
            (root / "domain.py").write_text("", encoding="utf-8")
            (root / "notmain.py").write_text("", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "main.py").write_text("", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "main.py").write_text("", encoding="utf-8")
            report = scan_repository(root)
            self.assertEqual(
                {"python main.py", "python src/example/main.py"},
                {command for command in report.metadata["start_commands"] if command.startswith("python ")},
            )

    def test_pytest_repository_does_not_suggest_unittest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_example.py").write_text("def test_ok(): pass\n", encoding="utf-8")
            (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            report = scan_repository(root)
            self.assertIn("python -m pytest", report.metadata["verification_commands"])
            self.assertNotIn("python -m unittest discover -s tests", report.metadata["verification_commands"])

    def test_unittest_repository_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_example.py").write_text("import unittest\nclass T(unittest.TestCase): pass\n", encoding="utf-8")
            report = scan_repository(root)
            self.assertIn("python -m unittest discover -s tests", report.metadata["verification_commands"])

    def test_mixed_python_test_frameworks_are_both_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_example.py").write_text("import unittest\nclass T(unittest.TestCase): pass\n", encoding="utf-8")
            (root / "conftest.py").write_text("", encoding="utf-8")
            report = scan_repository(root)
            self.assertTrue({"python -m pytest", "python -m unittest discover -s tests"}.issubset(report.metadata["verification_commands"]))

    def test_unknown_python_tests_do_not_produce_a_guessed_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_example.py").write_text("def check(): pass\n", encoding="utf-8")
            report = scan_repository(root)
            self.assertFalse(any(command.startswith("python -m") for command in report.metadata["verification_commands"]))

    def test_readme_words_in_prose_or_code_do_not_count_as_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Sample\n\nThis mentions test and 注意 only.\n```md\n## Setup\n```\n", encoding="utf-8")
            findings = {f.check_id for f in scan_repository(root).findings}
            self.assertIn("readme-missing-setup", findings)
            self.assertIn("readme-missing-verification", findings)

    def test_japanese_readme_headings_are_recognized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Sample\n## 要件\n## セットアップ\n## 使い方\n## 動作確認\n## 制限事項\n", encoding="utf-8")
            findings = {f.check_id for f in scan_repository(root).findings}
            self.assertFalse(any(item.startswith("readme-missing-") for item in findings))

    def test_scan_healthy_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)

            report = scan_repository(root)

            self.assertEqual(report.verdict, "PASS")
            self.assertEqual(report.score, 100)
            self.assertFalse(report.findings, report.findings)
            self.assertIn(8765, report.metadata["ports"])
            self.assertIn("/health", report.metadata["health_endpoints"])
            self.assertIn("npm test", report.metadata["verification_commands"])

    def test_scan_unhealthy_repository_and_redacts_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sensitive_value = "SENSITIVE_VALUE_SHOULD_NOT_APPEAR"
            self._write_unhealthy_repository(root, sensitive_value)
            output = root / "doctor-output"

            report = scan_repository(root, output_directory=output)

            finding_ids = {finding.check_id for finding in report.findings}
            self.assertIn("secret-risk-file", finding_ids)
            self.assertIn("broken-markdown-link", finding_ids)
            self.assertIn("missing-favicon", finding_ids)
            self.assertIn("missing-health-check", finding_ids)
            self.assertEqual(report.verdict, "FAIL")

            for filename in ("report.json", "report.md", "report.html"):
                path = output / filename
                self.assertTrue(path.exists(), filename)
                rendered = path.read_text(encoding="utf-8")
                self.assertNotIn(sensitive_value, rendered)

    def test_reports_redact_absolute_path_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "shareable-repo"
            root.mkdir()
            self._write_healthy_repository(root)
            output = Path(temp_dir) / "out"

            report = scan_repository(root, output_directory=output)

            self.assertEqual(report.repository, "shareable-repo")
            for filename in ("report.json", "report.md", "report.html"):
                rendered = (output / filename).read_text(encoding="utf-8")
                self.assertNotIn(str(root.resolve()), rendered)
                self.assertIn("shareable-repo", rendered)

    def test_ignore_check_is_visible_in_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"ignore_checks": ["missing-security-doc"]}),
                encoding="utf-8",
            )
            (root / "SECURITY.md").unlink()

            report = scan_repository(root)

            self.assertNotIn(
                "missing-security-doc", {finding.check_id for finding in report.findings}
            )
            self.assertEqual(
                report.metadata["suppressed_findings"],
                {"missing-security-doc": 1},
            )

    def test_html_has_clear_verdict_and_collapsible_severity_groups(self) -> None:
        report = ScanReport(
            repository="sample",
            generated_at="2026-07-11T00:00:00Z",
            files_scanned=2,
            paths_discovered=4,
            findings=[Finding("x", "HIGH", "Problem", ".", "e", "r")],
            metadata={"scan_complete": True},
        )
        rendered = render_html(report)
        self.assertIn(">FAIL<", rendered)
        self.assertIn("<details id='severity-high'", rendered)
        self.assertIn("検査範囲", rendered)

    def test_cli_writes_reports_and_honors_fail_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            output = Path(temp_dir) / "reports"
            root.mkdir()
            self._write_unhealthy_repository(root, "private-value")

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                no_fail_code = main(
                    ["scan", str(root), "--output", str(output), "--fail-on", "none"]
                )
                high_fail_code = main(
                    ["scan", str(root), "--output", str(output), "--fail-on", "high"]
                )

            self.assertEqual(no_fail_code, 0)
            self.assertEqual(high_fail_code, 1)
            self.assertTrue((output / "report.json").exists())

    def test_cli_returns_2_for_incomplete_scan_even_with_fail_on_none(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "extra.txt").write_text("x\n", encoding="utf-8")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"max_files": 1}), encoding="utf-8"
            )
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                output = Path(temp_dir) / "cli-output"
                code = main(
                    [
                        "scan",
                        str(root),
                        "--output",
                        str(output),
                        "--fail-on",
                        "none",
                    ]
                )
            self.assertEqual(code, 2)

    def test_batch_launcher_is_location_independent(self) -> None:
        batch = (Path(__file__).parents[1] / "run-doctor.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn('pushd "%~dp0"', batch)
        self.assertIn('set "OUTPUT=', batch)
        self.assertIn('--fail-on "%FAIL_ON%"', batch)

    @unittest.skipUnless(os.name == "nt", "Windows launcher smoke test")
    def test_batch_launcher_runs_from_another_directory(self) -> None:
        repository = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                ["cmd.exe", "/c", str(repository / "run-doctor.bat"), str(repository), "none"],
                cwd=temp_dir,
                env={**os.environ, "CI": "1"},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Static verdict:", completed.stdout)

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)

    @staticmethod
    def _write_base_docs(root: Path) -> None:
        (root / "README.md").write_text(
            """# Sample

## Requirements

Python 3.11

## Setup

Install dependencies.

## Usage

Run the launcher.

## Verification

Run tests.

## Limitations

Demo only.
""",
            encoding="utf-8",
        )
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")

    @classmethod
    def _write_healthy_repository(cls, root: Path) -> None:
        cls._write_base_docs(root)
        (root / "package.json").write_text(
            json.dumps(
                {
                    "name": "healthy",
                    "scripts": {"start": "node server.js", "test": "node --test"},
                }
            ),
            encoding="utf-8",
        )
        (root / "index.html").write_text(
            '<!doctype html><html><head><link rel="icon" href="favicon.ico"></head></html>',
            encoding="utf-8",
        )
        (root / "favicon.ico").write_bytes(b"ico")
        (root / "server.js").write_text(
            "const port = 8765; app.get('/health', handler);\n", encoding="utf-8"
        )

    @classmethod
    def _write_unhealthy_repository(cls, root: Path, secret: str) -> None:
        (root / "README.md").write_text(
            "# Broken\n\n[Missing](docs/missing.png)\n", encoding="utf-8"
        )
        (root / ".env").write_text(f"TOKEN={secret}\n", encoding="utf-8")
        (root / "package.json").write_text(
            json.dumps({"name": "broken", "scripts": {"start": "node server.js"}}),
            encoding="utf-8",
        )
        (root / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
        (root / "server.js").write_text("const port = 8765;\n", encoding="utf-8")
