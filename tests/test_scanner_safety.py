from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repo_launch_doctor.models import Finding
from repo_launch_doctor.scanner import scan_repository


class ScannerSafetyRegressionTests(unittest.TestCase):
    def test_invalid_utf8_marks_scan_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            (root / "legacy.txt").write_bytes(b"\xff\xfe\x00")

            report = scan_repository(root)

            self.assertEqual(report.verdict, "INCOMPLETE")
            self.assertFalse(report.metadata["scan_complete"])
            self.assertTrue(
                any("legacy.txt" in error for error in report.metadata["scan_errors"])
            )
            self.assertIn(
                "scan-incomplete", {finding.check_id for finding in report.findings}
            )

    def test_internal_check_error_marks_scan_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
            findings = [
                Finding(
                    "internal-check-error",
                    "MEDIUM",
                    "A doctor check could not complete",
                    ".",
                    "Check failed with RuntimeError.",
                    "Report the failure.",
                )
            ]
            metadata = {
                "scan_complete": True,
                "incomplete_reasons": [],
                "scan_errors": [],
            }

            with patch(
                "repo_launch_doctor.scanner.run_checks",
                return_value=(findings, metadata),
            ):
                report = scan_repository(root)

            self.assertEqual(report.verdict, "INCOMPLETE")
            self.assertIn(
                "scan-incomplete", {finding.check_id for finding in report.findings}
            )
            self.assertTrue(
                any(
                    "internal check" in reason
                    for reason in report.metadata["incomplete_reasons"]
                )
            )

    def test_auto_detected_library_does_not_require_start_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            package = root / "src" / "sample_library"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text(
                '__version__ = "0.1.0"\n', encoding="utf-8"
            )
            (root / "pyproject.toml").write_text(
                """[project]
name = "sample-library"
version = "0.1.0"
""",
                encoding="utf-8",
            )

            report = scan_repository(root)

            self.assertEqual(report.metadata["project_type"], "library")
            self.assertNotIn(
                "missing-start-entrypoint",
                {finding.check_id for finding in report.findings},
            )

    def test_auto_detected_static_web_does_not_require_health_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base_docs(root)
            (root / "index.html").write_text(
                '<!doctype html><html><head><link rel="icon" href="favicon.ico"></head></html>',
                encoding="utf-8",
            )
            (root / "favicon.ico").write_bytes(b"ico")

            report = scan_repository(root)

            self.assertEqual(report.metadata["project_type"], "static-web")
            finding_ids = {finding.check_id for finding in report.findings}
            self.assertNotIn("missing-start-entrypoint", finding_ids)
            self.assertNotIn("missing-health-check", finding_ids)

    @staticmethod
    def _write_base_docs(root: Path) -> None:
        (root / "README.md").write_text(
            """# Sample

## Requirements

Python 3.11.

## Setup

No installation.

## Usage

Use the documented interface.

## Verification

Run the tests.

## Limitations

Static inspection only.
""",
            encoding="utf-8",
        )
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
