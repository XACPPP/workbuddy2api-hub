#!/usr/bin/env python3
"""Safety tests for automatic unregistered-workflow cleanup."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "maintenance" / "cleanup-workflows.py"
SPEC = importlib.util.spec_from_file_location("cleanup_workflows", SCRIPT)
CLEANUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLEANUP)


class WorkflowCleanupTest(unittest.TestCase):
    def test_policy_protects_required_workflows(self):
        allowed = CLEANUP.load_allowed()
        self.assertTrue(CLEANUP.REQUIRED.issubset(allowed))
        self.assertIn("prune-workflows.yml", allowed)

    def test_invalid_or_missing_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text('{"schema":1,"allowed":[]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                CLEANUP.load_allowed(path)
        with self.assertRaises(FileNotFoundError):
            CLEANUP.load_allowed(Path(tempfile.gettempdir()) / "missing-policy.json")

    def test_only_unregistered_workflow_files_are_obsolete(self):
        tree = {
            "tree": [
                {"type": "blob", "path": ".github/workflows/tests.yml", "sha": "1"},
                {"type": "blob", "path": ".github/workflows/old.yml", "sha": "2"},
                {"type": "blob", "path": ".github/workflows/nested/old.yaml", "sha": "3"},
                {"type": "blob", "path": "README.md", "sha": "4"},
                {"type": "tree", "path": ".github/workflows/dir", "sha": "5"},
            ]
        }
        obsolete = CLEANUP.obsolete_workflow_paths(tree, {"tests.yml"})
        self.assertEqual(
            obsolete,
            [
                (".github/workflows/nested/old.yaml", "3"),
                (".github/workflows/old.yml", "2"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
