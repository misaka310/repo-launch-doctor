from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_launch_doctor.scanner import scan_repository


class RepositoryBoundaryTests(unittest.TestCase):
    @staticmethod
    def _git(root: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @staticmethod
    def _write_base(root: Path) -> None:
        (root / "README.md").write_text(
            "# Sample\n\n## Requirements\nPython\n\n## Setup\nNone\n\n## Usage\nRun it.\n\n## Verification\nRun tests.\n\n## Limitations\nNone.\n",
            encoding="utf-8",
        )

    def test_detects_machine_specific_shared_skill_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base(root)
            (root / "AGENTS.md").write_text(
                "Use C:\\00_dev\\.agents\\skills\\browser-extension-update-delivery\\SKILL.md.\n",
                encoding="utf-8",
            )
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "reload-extension.ps1").write_text(
                "$helper = 'C:\\00_dev\\.agents\\skills\\browser-extension-update-delivery\\scripts\\invoke_reload_server.ps1'\n",
                encoding="utf-8",
            )
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)
            matches = {
                finding.path
                for finding in report.findings
                if finding.check_id == "workspace-specific-dependency"
            }

            self.assertEqual({"AGENTS.md", "scripts/reload-extension.ps1"}, matches)

    def test_detects_tracked_internal_agent_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_base(root)
            plan = root / "docs" / "superpowers" / "plans"
            plan.mkdir(parents=True)
            (plan / "implementation.md").write_text("internal agent plan\n", encoding="utf-8")
            self._git(root, "init")
            self._git(root, "add", ".")

            report = scan_repository(root)

            self.assertTrue(
                any(
                    finding.check_id == "internal-agent-plan-tracked"
                    and finding.path == "docs/superpowers/plans/implementation.md"
                    for finding in report.findings
                ),
                report.findings,
            )


if __name__ == "__main__":
    unittest.main()
