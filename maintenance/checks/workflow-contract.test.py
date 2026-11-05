#!/usr/bin/env python3
"""Static contract checks for the fork-only GHCR workflow."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PUBLISH = (WORKFLOWS / "docker-publish.yml").read_text(encoding="utf-8")


class WorkflowContractTest(unittest.TestCase):
    def test_only_active_workflows_remain(self):
        self.assertEqual(
            {
                path.name
                for path in WORKFLOWS.iterdir()
                if path.suffix in {".yml", ".yaml"}
            },
            {
                "docker-publish.yml",
                "release.yml",
                "revert-guard.yml",
                "tests.yml",
            },
        )

    def test_stable_release_and_manual_post_conditions(self):
        self.assertIn("schedule:", PUBLISH)
        self.assertIn("workflow_dispatch:", PUBLISH)
        self.assertIn("release:", PUBLISH)
        self.assertIn("draft == false", PUBLISH)
        self.assertIn("prerelease == false", PUBLISH)
        self.assertIn("published_at != null", PUBLISH)
        self.assertIn(".tag_name | test(", PUBLISH)

    def test_image_and_platforms(self):
        self.assertIn("IMAGE: ghcr.io/xacppp/workbuddy2api-hub", PUBLISH)
        self.assertIn("platforms: linux/amd64,linux/arm64", PUBLISH)

    def test_latest_is_later_and_verified(self):
        build_start = PUBLISH.index("  build:")
        promote_start = PUBLISH.index("  promote:")
        build_block = PUBLISH[build_start:promote_start]
        versions_block = build_block[build_block.index("docker/metadata-action"):]
        self.assertNotIn("value=latest", versions_block)
        self.assertIn("needs: [resolve, build]", PUBLISH[promote_start:])
        self.assertIn("imagetools create", PUBLISH[promote_start:])

    def test_concurrency_and_cache(self):
        self.assertIn(
            "group: workbuddy-ghcr-publish\n  cancel-in-progress: false",
            PUBLISH,
        )
        self.assertIn("cache-from: type=gha", PUBLISH)
        self.assertIn("cache-to: type=gha", PUBLISH)

    def test_patch_entry_point(self):
        self.assertTrue((ROOT / "maintenance" / "patches").is_dir())
        self.assertIn("maintenance/patches/*.patch", PUBLISH)

    def test_manifest_check_uses_build_digest(self):
        self.assertIn('"$IMAGE@$DIGEST" --raw', PUBLISH)
        self.assertNotIn("pkgs/container/workbuddy2api-hub/manifests/$DIGEST", PUBLISH)


if __name__ == "__main__":
    unittest.main()
