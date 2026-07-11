from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repo_launch_doctor.cli import main
from repo_launch_doctor.config import load_config
from repo_launch_doctor.models import Finding, ScanReport
from repo_launch_doctor.scanner import scan_repository


class RepoLaunchDoctorTests(unittest.TestCase):
    def test_report_orders_findings_and_calculates_score(self) -> None:
        report = ScanReport(
            root="sample",
            generated_at="2026-07-11T00:00:00Z",
            files_scanned=4,
            findings=[
                Finding("low", "LOW", "Low", "README.md", "e", "r"),
                Finding("blocker", "BLOCKER", "Blocker", ".env", "e", "r"),
                Finding("medium", "MEDIUM", "Medium", "app.py", "e", "r"),
                Finding("high", "HIGH", "High", "start.bat", "e", "r"),
            ],
            metadata={},
        )

        self.assertEqual(
            [finding.severity for finding in report.sorted_findings()],
            ["BLOCKER", "HIGH", "MEDIUM", "LOW"],
        )
        self.assertEqual(report.score, 30)
        self.assertEqual(
            report.counts,
            {"BLOCKER": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 1, "INFO": 0},
        )

    def test_config_loads_defaults_and_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps(
                    {
                        "ignore_paths": ["private/**"],
                        "ignore_checks": ["missing-security-doc"],
                        "expected_ports": [8717],
                        "expected_start_commands": ["start.bat"],
                        "expected_health_endpoints": ["/health"],
                        "accepted_generated_paths": ["dist/**"],
                        "project_type": "web",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)

            self.assertIn(".git/**", config.ignore_paths)
            self.assertIn("private/**", config.ignore_paths)
            self.assertEqual(config.expected_ports, (8717,))
            self.assertEqual(config.expected_start_commands, ("start.bat",))
            self.assertEqual(config.project_type, "web")

    def test_hyphenated_windows_launcher_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(
                "# CLI\n\n## Requirements\nPython 3.11\n\n## Setup\nNo install.\n\n## Usage\nRun run-doctor.bat.\n\n## Verification\nRun tests.\n\n## Limitations\nStatic checks only.\n",
                encoding="utf-8",
            )
            (root / "run-doctor.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
            (root / "config.example.json").write_text("{}\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertNotIn(
                "missing-start-entrypoint", {finding.check_id for finding in report.findings}
            )
            self.assertIn("run-doctor.bat", report.metadata["start_commands"])

    def test_env_example_is_not_treated_as_a_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / ".env.example").write_text("API_KEY=replace-me\n", encoding="utf-8")

            report = scan_repository(root)

            self.assertFalse(
                any(
                    finding.check_id == "secret-risk-file" and finding.path == ".env.example"
                    for finding in report.findings
                )
            )

    def test_static_web_project_does_not_require_health_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)
            (root / "src" / "server.js").unlink()
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"project_type": "static-web"}), encoding="utf-8"
            )

            report = scan_repository(root)

            self.assertNotIn(
                "missing-health-check", {finding.check_id for finding in report.findings}
            )

    def test_scan_healthy_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_healthy_repository(root)

            report = scan_repository(root)

            self.assertGreaterEqual(report.score, 90)
            self.assertFalse(
                any(finding.severity in {"BLOCKER", "HIGH"} for finding in report.findings),
                report.findings,
            )
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
            self.assertLess(report.score, 90)

            for filename in ("report.json", "report.md", "report.html"):
                path = output / filename
                self.assertTrue(path.exists(), filename)
                rendered = path.read_text(encoding="utf-8")
                self.assertNotIn(sensitive_value, rendered)

    def test_ignore_check_suppresses_selected_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_unhealthy_repository(root, "private-value")
            (root / ".repo-launch-doctor.json").write_text(
                json.dumps({"ignore_checks": ["missing-favicon"]}),
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertNotIn("missing-favicon", {finding.check_id for finding in report.findings})

    def test_cli_writes_reports_and_honors_fail_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            output = Path(temp_dir) / "reports"
            root.mkdir()
            self._write_unhealthy_repository(root, "private-value")

            no_fail_code = main(
                ["scan", str(root), "--output", str(output), "--fail-on", "none"]
            )
            high_fail_code = main(
                ["scan", str(root), "--output", str(output), "--fail-on", "high"]
            )

            self.assertEqual(no_fail_code, 0)
            self.assertEqual(high_fail_code, 1)
            self.assertTrue((output / "report.json").exists())

    @staticmethod
    def _write_healthy_repository(root: Path) -> None:
        (root / "src").mkdir()
        (root / "public").mkdir()
        (root / "docs").mkdir()
        (root / "README.md").write_text(
            """# Healthy App

A local web app with a documented startup path.

## Requirements

Python 3.11 and Node.js 20.

## Setup

Run `npm install`.

## Usage

Run `start.bat` or `npm run dev` and open http://127.0.0.1:8765.

## Verification

Run `npm test` and check `/health`.

## Limitations

Local single-user use only.

See [architecture](docs/architecture.md).
""",
            encoding="utf-8",
        )
        (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
        (root / "config.example.json").write_text("{}\n", encoding="utf-8")
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
        (root / "public" / "favicon.svg").write_text("<svg></svg>\n", encoding="utf-8")
        (root / "src" / "server.js").write_text(
            "const port = 8765; app.get('/health', (_req, res) => res.json({ok:true}));\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_unhealthy_repository(root: Path, sensitive_value: str) -> None:
        (root / "logs").mkdir()
        (root / "README.md").write_text(
            "# Broken App\n\nSee [missing docs](docs/missing.md).\n",
            encoding="utf-8",
        )
        (root / ".env").write_text(f"PRIVATE_VALUE={sensitive_value}\n", encoding="utf-8")
        (root / "logs" / "debug.log").write_text(sensitive_value, encoding="utf-8")
        (root / "index.html").write_text("<!doctype html><html><head></head></html>", encoding="utf-8")
        (root / "server.py").write_text("PORT = 8123\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
