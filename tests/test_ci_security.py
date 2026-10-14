from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


class CiSecurityTests(unittest.TestCase):
    def test_tests_workflow_avoids_dynamic_pip_install_and_limits_token(self) -> None:
        text = TESTS_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)
        self.assertNotIn("python -m pip install .", text)
        self.assertGreaterEqual(text.count("python -m repo_launch_doctor --version"), 2)


if __name__ == "__main__":
    unittest.main()
