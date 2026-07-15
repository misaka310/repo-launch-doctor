from __future__ import annotations

import json
import unittest
from pathlib import Path

from audits.current import current_audit


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audits" / "current"


class CurrentAuditTests(unittest.TestCase):
    def test_metrics_count_all_four_classification_outcomes(self) -> None:
        rows = [
            {
                "findings": ["missing-start-entrypoint"],
                "labels": {
                    "missing-start-entrypoint": True,
                    "readme-missing-verification": False,
                },
            },
            {
                "findings": ["readme-missing-verification"],
                "labels": {
                    "missing-start-entrypoint": False,
                    "readme-missing-verification": True,
                },
            },
            {
                "findings": [
                    "missing-start-entrypoint",
                    "readme-missing-verification",
                ],
                "labels": {
                    "missing-start-entrypoint": False,
                    "readme-missing-verification": False,
                },
            },
            {
                "findings": [],
                "labels": {
                    "missing-start-entrypoint": True,
                    "readme-missing-verification": True,
                },
            },
        ]

        metrics = current_audit._metrics(rows)

        self.assertEqual(
            {"TP": 1, "FP": 1, "FN": 1, "TN": 1},
            {
                key: metrics["missing-start-entrypoint"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )
        self.assertEqual(
            {"TP": 1, "FP": 1, "FN": 1, "TN": 1},
            {
                key: metrics["readme-missing-verification"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )

    def test_published_current_audit_is_internally_consistent(self) -> None:
        selection = json.loads((AUDIT_DIR / "selection.json").read_text(encoding="utf-8"))
        review = json.loads((AUDIT_DIR / "manual-review.json").read_text(encoding="utf-8"))
        latest = json.loads(
            (AUDIT_DIR / "results" / "latest.json").read_text(encoding="utf-8")
        )

        self.assertEqual([], current_audit.validate_selection(selection))
        self.assertEqual(30, latest["selected_targets"])
        self.assertEqual(29, latest["eligible_targets"])
        self.assertEqual(1, latest["excluded_targets"])
        self.assertEqual(29, len(review["reviews"]))
        self.assertEqual(
            {"TP": 1, "FP": 0, "FN": 0, "TN": 28},
            {
                key: latest["metrics"]["missing-start-entrypoint"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )
        self.assertEqual(
            {"TP": 16, "FP": 0, "FN": 1, "TN": 12},
            {
                key: latest["metrics"]["readme-missing-verification"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )

    def test_published_audit_artifacts_do_not_leak_local_paths(self) -> None:
        for path in (
            AUDIT_DIR / "selection.json",
            AUDIT_DIR / "manual-review.json",
            AUDIT_DIR / "results" / "baseline.json",
            AUDIT_DIR / "results" / "baseline.md",
            AUDIT_DIR / "results" / "latest.json",
            AUDIT_DIR / "results" / "latest.md",
        ):
            rendered = path.read_text(encoding="utf-8").casefold()
            self.assertNotIn("c:\\00_dev", rendered, path)
            self.assertNotIn(".current-audit-cache", rendered, path)

    def test_baseline_and_latest_use_the_same_manual_labels(self) -> None:
        baseline = json.loads(
            (AUDIT_DIR / "results" / "baseline.json").read_text(encoding="utf-8")
        )
        latest = json.loads(
            (AUDIT_DIR / "results" / "latest.json").read_text(encoding="utf-8")
        )
        baseline_labels = {
            (row["repository"], row["commit"]): row["labels"]
            for row in baseline["results"]
        }
        latest_labels = {
            (row["repository"], row["commit"]): row["labels"]
            for row in latest["results"]
        }

        self.assertEqual(latest_labels, baseline_labels)
        self.assertEqual(
            {"TP": 1, "FP": 15, "FN": 0, "TN": 13},
            {
                key: baseline["metrics"]["missing-start-entrypoint"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )
        self.assertEqual(
            {"TP": 16, "FP": 6, "FN": 1, "TN": 6},
            {
                key: baseline["metrics"]["readme-missing-verification"][key]
                for key in ("TP", "FP", "FN", "TN")
            },
        )


if __name__ == "__main__":
    unittest.main()
