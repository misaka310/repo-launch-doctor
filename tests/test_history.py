from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_launch_doctor.cli import main
from repo_launch_doctor.history import scan_git_history


class GitHistorySecretScanTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout.strip()

    def _init_repo(self, root: Path) -> None:
        self._git(root, "init")
        self._git(root, "config", "user.name", "History Test")
        self._git(root, "config", "user.email", "history@example.invalid")
        (root / "README.md").write_text("# sample\n", encoding="utf-8")
        self._git(root, "add", "README.md")
        self._git(root, "commit", "-m", "initial")

    def test_range_scan_finds_secret_added_then_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            secret = "ghp_" + ("A" * 36)
            (root / "config.txt").write_text(f"token={secret}\n", encoding="utf-8")
            self._git(root, "add", "config.txt")
            self._git(root, "commit", "-m", "temporarily add config")
            (root / "config.txt").unlink()
            self._git(root, "add", "-A")
            self._git(root, "commit", "-m", "remove config")
            head = self._git(root, "rev-parse", "HEAD")

            report = scan_git_history(root, revision_range=f"{base}..{head}")

            self.assertEqual(report.commits_scanned, 2)
            self.assertTrue(any(f.detector == "github-token" for f in report.findings))
            payload = json.dumps(report.to_dict())
            self.assertNotIn(secret, payload)

    def test_scan_checks_commit_messages_without_echoing_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            secret = "sk-proj-" + ("B" * 40)
            (root / "note.txt").write_text("safe\n", encoding="utf-8")
            self._git(root, "add", "note.txt")
            self._git(root, "commit", "-m", f"debug key {secret}")
            head = self._git(root, "rev-parse", "HEAD")

            report = scan_git_history(root, revision_range=f"{base}..{head}")

            finding = next(f for f in report.findings if f.location == "commit-message")
            self.assertEqual(finding.detector, "openai-key")
            self.assertNotIn(secret, json.dumps(report.to_dict()))

    def test_sensitive_filename_in_history_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            (root / ".env").write_text("SAFE_MODE=true\n", encoding="utf-8")
            self._git(root, "add", ".env")
            self._git(root, "commit", "-m", "add local env by mistake")
            head = self._git(root, "rev-parse", "HEAD")

            report = scan_git_history(root, revision_range=f"{base}..{head}")

            self.assertTrue(any(f.detector == "sensitive-filename" and f.path == ".env" for f in report.findings))

    def test_code_expression_with_secret_in_identifier_is_not_a_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            (root / "patterns.py").write_text(
                "SAFE_SECRET_VALUE_RE = re.compile(r'example')\n"
                "_SECRET_PATTERNS = (re.compile(r'example'),)\n"
                "secret = 'sk-proj-' + ('B' * 40)\n",
                encoding="utf-8",
            )
            self._git(root, "add", "patterns.py")
            self._git(root, "commit", "-m", "add safe detector pattern")
            head = self._git(root, "rev-parse", "HEAD")

            report = scan_git_history(root, revision_range=f"{base}..{head}")

            self.assertEqual(report.findings, [])

    def test_clean_range_and_cli_return_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            self._git(root, "add", "app.py")
            self._git(root, "commit", "-m", "add app")
            head = self._git(root, "rev-parse", "HEAD")
            output = root / "history-report"

            exit_code = main(
                [
                    "history-scan",
                    str(root),
                    "--range",
                    f"{base}..{head}",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "history-report.json").is_file())
            self.assertTrue((output / "history-report.md").is_file())

    def test_cli_returns_one_when_history_contains_a_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._init_repo(root)
            base = self._git(root, "rev-parse", "HEAD")
            secret = "AKIA" + ("C" * 16)
            (root / "aws.txt").write_text(secret + "\n", encoding="utf-8")
            self._git(root, "add", "aws.txt")
            self._git(root, "commit", "-m", "add aws config")
            head = self._git(root, "rev-parse", "HEAD")

            exit_code = main(["history-scan", str(root), "--range", f"{base}..{head}"])

            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
