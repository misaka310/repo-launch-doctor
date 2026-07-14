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

    def test_gitignore_fallback_works_without_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / ".gitignore").write_text(".env\n__pycache__/\n", encoding="utf-8")
            (root / ".env").write_text("PRIVATE_VALUE=hidden\n", encoding="utf-8")
            cache = root / "repo_launch_doctor" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "module.pyc").write_bytes(b"cache")

            report = scan_repository(root)

            self.assertEqual(report.metadata["ignore_detection_source"], ".gitignore-fallback")
            self.assertFalse(
                any(finding.check_id == "secret-risk-file" for finding in report.findings),
                report.findings,
            )
            self.assertFalse(
                any(
                    finding.check_id == "generated-artifact-present"
                    and "__pycache__" in finding.path
                    for finding in report.findings
                ),
                report.findings,
            )

    def test_gitignore_fallback_respects_negation_for_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / ".gitignore").write_text(".env\n!.env\n", encoding="utf-8")
            (root / ".env").write_text("PRIVATE_VALUE=visible\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertTrue(
                any(finding.check_id == "secret-risk-file" for finding in report.findings),
                report.findings,
            )

    def test_git_ignored_env_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=local-only\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(finding.path == ".env" for finding in report.findings),
                report.findings,
            )

    def test_tracked_secret_is_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / "credentials.json").write_text('{"token":"private"}\n', encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            finding = next(
                item for item in report.findings if item.path == "credentials.json"
            )
            self.assertEqual(finding.severity, "BLOCKER")
            self.assertNotIn("private", finding.evidence)

    def test_untracked_generated_directory_is_reported_when_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "build").mkdir()
            (root / "build" / "bundle.js").write_text("generated\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", "README.md", "LICENSE", "SECURITY.md", "run.bat")

            report = scan_repository(root)

            findings = [
                finding
                for finding in report.findings
                if finding.check_id == "generated-artifact-present"
            ]
            self.assertTrue(any(finding.path == "build" and finding.severity == "LOW" for finding in findings))

    def test_git_ignored_generated_directory_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / ".gitignore").write_text("build/\n", encoding="utf-8")
            (root / "build").mkdir()
            (root / "build" / "bundle.js").write_text("generated\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "generated-artifact-present"
                    and finding.path == "build"
                    for finding in report.findings
                ),
                report.findings,
            )

    def test_tracked_build_output_is_detected_even_when_content_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "build").mkdir()
            (root / "build" / "bundle.js").write_text("generated\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            finding = next(
                item
                for item in report.findings
                if item.check_id == "generated-artifact-present"
                and item.path == "build"
            )
            self.assertEqual(finding.severity, "MEDIUM")

    def test_hidden_dependency_directory_is_excluded_from_content_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            hidden = root / ".venv" / "Lib"
            hidden.mkdir(parents=True)
            (hidden / "huge.py").write_text("PORT = 65500\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertNotIn(65500, report.metadata["ports"])
            self.assertGreaterEqual(
                report.metadata["skipped_reasons"].get("content_ignored_directories", 0),
                1,
            )

    def test_max_paths_marks_report_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            for index in range(5):
                (root / f"extra-{index}.txt").write_text("x\n", encoding="utf-8")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"max_paths": 2}), encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertEqual(report.verdict, "INCOMPLETE")
            self.assertIsNone(report.score)
            self.assertIn(
                "scan-incomplete", {finding.check_id for finding in report.findings}
            )

    def test_nested_dependency_tree_is_not_read_but_tracked_paths_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            dependency = root / "packages" / "app" / "node_modules"
            dependency.mkdir(parents=True)
            (dependency / "dep.js").write_text("generated dependency\n", encoding="utf-8")
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
        self.assertIn("Verdict:", completed.stdout)

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

Python 3.11.

## Setup

No installation.

## Usage

Run the launcher.

## Verification

Run the tests.

## Limitations

Static inspection only.
""",
            encoding="utf-8",
        )
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")

    @classmethod
    def _write_healthy_repository(cls, root: Path) -> None:
        (root / "src").mkdir()
        (root / "public").mkdir()
        (root / "docs").mkdir()
        (root / "tests").mkdir()
        (root / "README.md").write_text(
            """# Healthy App

A local web app with a documented startup path.

## Requirements

Python 3.11 and Node.js 20.

## Setup

Run `npm install`.

## Usage

Run `start.bat` or `npm run dev` and open the local app.

## Verification

Run `npm test` and check `/health`.

## Limitations

Local single-user use only.

See [architecture](docs/architecture.md).
""",
            encoding="utf-8",
        )
        (root / "docs" / "architecture.md").write_text(
            "# Architecture\n", encoding="utf-8"
        )
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
        (root / "start.bat").write_text("@echo off\nnpm run dev\n", encoding="utf-8")
        (root / "package.json").write_text(
            json.dumps(
                {
                    "scripts": {
                        "dev": "node src/server.js",
                        "test": "node --test",
                        "build": "echo build",
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "index.html").write_text(
            '<!doctype html><html><head><link rel="icon" href="/public/favicon.svg"></head></html>',
            encoding="utf-8",
        )
        (root / "public" / "favicon.svg").write_text(
            "<svg></svg>\n", encoding="utf-8"
        )
        (root / "src" / "server.js").write_text(
            "const port = 8765; app.get('/health', (_req, res) => res.json({ok:true}));\n",
            encoding="utf-8",
        )
        (root / "tests" / "smoke.js").write_text("// smoke\n", encoding="utf-8")

    @staticmethod
    def _write_unhealthy_repository(root: Path, sensitive_value: str) -> None:
        (root / "logs").mkdir()
        (root / "README.md").write_text(
            "# Broken App\n\nSee [missing docs](docs/missing.md).\n",
            encoding="utf-8",
        )
        (root / ".env").write_text(
            f"PRIVATE_VALUE={sensitive_value}\n", encoding="utf-8"
        )
        (root / "logs" / "debug.log").write_text(
            sensitive_value, encoding="utf-8"
        )
        (root / "index.html").write_text(
            "<!doctype html><html><head></head></html>", encoding="utf-8"
        )
        (root / "server.py").write_text("PORT = 8123\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
