"""Regression checks for scoped report cleanup and failed generation."""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "retention", Path(__file__).with_name("retain_latest.py")
)
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class RetentionTests(unittest.TestCase):
    def test_cleanup_preserves_pr_other_workflow_newer_and_unrelated(self):
        current = {"id": 9, "workflow_id": 12}

        def artifact(i, name="reports", branch="main", created="2026-01-01", run=None):
            return {
                "id": i,
                "name": name,
                "created_at": created,
                "expired": False,
                "workflow_run": {"id": run or i, "head_branch": branch},
            }

        kept = artifact(90, created="2026-02-01", run=9)
        entries = [
            kept,
            artifact(1),
            artifact(2, branch="feature"),
            artifact(3),
            artifact(4, name="unrelated"),
            artifact(5, created="2026-03-01"),
            artifact(6),
        ]
        deleted = []

        def request(path, method="GET"):
            if method == "DELETE":
                deleted.append(path)
                return
            if path == "/actions/runs/9":
                return current
            if path == "/actions/artifacts/90":
                return kept
            if path.endswith("&page=1"):
                return {"artifacts": entries}
            if path.endswith("&page=2"):
                return {"artifacts": []}
            return {
                "workflow_id": 13 if path.endswith("/3") else 12,
                "event": "pull_request" if path.endswith("/6") else "push",
            }

        env = {
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_RUN_ID": "9",
            "CURRENT_ARTIFACT_ID": "90",
            "REPORT_ARTIFACT_NAMES": "reports",
        }
        with patch.dict(os.environ, env), patch.object(retention, "request", request):
            retention.main()
        self.assertEqual(deleted, ["/actions/artifacts/1"])

    def test_expired_current_artifact_prevents_deletion(self):
        env = {
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_RUN_ID": "9",
            "CURRENT_ARTIFACT_ID": "90",
            "REPORT_ARTIFACT_NAMES": "reports",
        }
        with (
            patch.dict(os.environ, env),
            patch.object(
                retention, "request", side_effect=[{"id": 9}, {"expired": True}]
            ) as request,
        ):
            with self.assertRaises(SystemExit):
                retention.main()
        self.assertEqual(request.call_count, 2)

    def test_non_main_prevents_any_request(self):
        with (
            patch.dict(os.environ, {"GITHUB_REF": "refs/heads/feature"}),
            patch.object(retention, "request") as request,
        ):
            with self.assertRaises(SystemExit):
                retention.main()
        request.assert_not_called()

    def test_missing_reports_preserves_existing_site(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "report-site").mkdir()
            existing = root / "report-site/index.html"
            existing.write_text("last valid publication")
            shutil.copy(
                Path(__file__).with_name("build_latest.py"), root / "scripts/build_latest.py"
            )
            result = subprocess.run(
                ["python", str(root / "scripts/build_latest.py"), "--kind", "api"],
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(existing.read_text(), "last valid publication")


if __name__ == "__main__":
    unittest.main()
