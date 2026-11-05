#!/usr/bin/env python3
"""Safety tests for old failed workflow run cleanup."""

import datetime as dt
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "maintenance" / "cleanup-runs.py"
SPEC = importlib.util.spec_from_file_location("cleanup_runs", SCRIPT)
CLEANUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLEANUP)


class WorkflowRunCleanupTest(unittest.TestCase):
    def test_success_and_active_runs_are_preserved(self):
        now = dt.datetime(2026, 11, 5, 12, tzinfo=dt.timezone.utc)
        runs = [
            {
                "id": 1,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-11-04T00:00:00Z",
            },
            {
                "id": 2,
                "status": "in_progress",
                "conclusion": None,
                "created_at": "2026-11-04T00:00:00Z",
            },
            {
                "id": 3,
                "status": "queued",
                "conclusion": None,
                "created_at": "2026-11-04T00:00:00Z",
            },
        ]
        self.assertEqual(CLEANUP.select_stale_runs(runs, now, dt.timedelta(hours=6)), [])

    def test_recent_failures_are_preserved(self):
        now = dt.datetime(2026, 11, 5, 12, tzinfo=dt.timezone.utc)
        runs = [
            {
                "id": 4,
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-11-05T10:00:00Z",
            }
        ]
        self.assertEqual(CLEANUP.select_stale_runs(runs, now, dt.timedelta(hours=6)), [])

    def test_old_failures_and_cancellations_are_selected(self):
        now = dt.datetime(2026, 11, 5, 12, tzinfo=dt.timezone.utc)
        runs = [
            {
                "id": 5,
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-11-05T01:00:00Z",
            },
            {
                "id": 6,
                "status": "completed",
                "conclusion": "cancelled",
                "created_at": "2026-11-04T01:00:00Z",
            },
        ]
        selected = CLEANUP.select_stale_runs(runs, now, dt.timedelta(hours=6))
        self.assertEqual([run["id"] for run in selected], [6, 5])


if __name__ == "__main__":
    unittest.main()
