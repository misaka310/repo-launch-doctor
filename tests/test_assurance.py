from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from repo_launch_doctor.cli import build_parser, main
from repo_launch_doctor.reporters import render_html, render_markdown
from repo_launch_doctor.scanner import scan_repository


class StaticAssuranceTests(unittest.TestCase):
    def _write_public_cli_repository(self, root: Path) -> None:
        (root / "README.md").write_text(
            "# Sample\n\n"
            "## Requirements\nPython 3.11\n\n"
            "## Setup\nNo setup required.\n\n"
            "## Usage\nRun `run.bat`.\n\n"
            "## Verification\n`python -m unittest`\n\n"
            "## Limitations\nStatic example only.\n",
            encoding="utf-8",
        )
        (root / "run.bat").write_text("@echo off\n", encoding="utf-8")
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")

    def test_scan_reports_static_assurance_and_explicit_unchecked_areas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_public_cli_repository(root)

            report = scan_repository(root)

            self.assertEqual("static", report.metadata["assurance_level"])
            coverage = report.metadata["coverage"]
            self.assertEqual("checked", coverage["repository_files"])
            self.assertEqual("checked", coverage["readme_and_entrypoints"])
            self.assertEqual("not_checked", coverage["runtime"])
            self.assertEqual("not_checked", coverage["dependencies"])
            self.assertEqual("not_checked", coverage["github_settings"])
            self.assertEqual("not_checked", coverage["binary_contents"])

    def test_reports_label_pass_and_score_as_static(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_public_cli_repository(root)
            report = scan_repository(root)

            html = render_html(report)
            markdown = render_markdown(report)

            self.assertIn("Static readiness", html)
            self.assertIn("static score / 100", html)
            self.assertIn("not_checked", html)
            self.assertIn("静的判定", markdown)
            self.assertIn("静的スコア", markdown)
            self.assertIn("保証範囲", markdown)

    def test_scan_defaults_to_high_as_the_failure_threshold(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["scan", "."])
        self.assertEqual("high", args.fail_on)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Missing entrypoint\n", encoding="utf-8")
            output = root / "reports"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = main(["scan", str(root), "--output", str(output)])
            self.assertEqual(1, code)


if __name__ == "__main__":
    unittest.main()
