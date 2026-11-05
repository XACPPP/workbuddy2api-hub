#!/usr/bin/env python3
"""Static contract checks for the fork-only GHCR workflow."""

from pathlib import Path
import sys
import unittest


class WorkflowContractTest(unittest.TestCase):
    workflow_dir = None

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        workflows = root / ".github" / "workflows"
        if workflows.is_dir():
            cls.workflows = workflows
        else:
            cls.workflows = cls.workflow_dir or Path(".")
        cls.publish = (cls.workflows / "docker-publish.yml").read_text(
            encoding="utf-8"
        )

    def test_only_active_workflows_remain(self):
        self.assertEqual(
            {
                path.name
                for path in self.workflows.iterdir()
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
        self.assertIn("schedule:", self.publish)
        self.assertIn("workflow_dispatch:", self.publish)
        self.assertIn("release:", self.publish)
        self.assertIn("draft == false", self.publish)
        self.assertIn("prerelease == false", self.publish)
        self.assertIn("published_at != null", self.publish)
        self.assertIn(".tag_name | test(", self.publish)

    def test_image_and_platforms(self):
        self.assertIn("IMAGE: ghcr.io/xacppp/workbuddy2api-hub-fork", self.publish)
        self.assertIn("platforms: linux/amd64,linux/arm64", self.publish)

    def test_latest_is_later_and_verified(self):
        build_start = self.publish.index("  build:")
        promote_start = self.publish.index("  promote:")
        build_block = self.publish[build_start:promote_start]
        versions_block = build_block[build_block.index("docker/metadata-action"):]
        self.assertNotIn("value=latest", versions_block)
        self.assertIn("needs: [resolve, build]", self.publish[promote_start:])
        self.assertIn("imagetools create", self.publish[promote_start:])

    def test_latest_requires_this_run_to_build(self):
        promote_start = self.publish.index("  promote:")
        self.assertIn("needs.build.outputs.built == 'true'", self.publish[promote_start:])

    def test_concurrency_and_cache(self):
        self.assertIn(
            "group: workbuddy-ghcr-publish\n  cancel-in-progress: false",
            self.publish,
        )
        self.assertIn("cache-from: type=gha", self.publish)
        self.assertIn("cache-to: type=gha", self.publish)

    def test_patch_entry_point(self):
        self.assertIn("maintenance/patches/*.patch", self.publish)

    def test_same_version_does_not_launch_build_or_promote(self):
        start = self.publish.index("  resolve:")
        end = self.publish.index("  build:")
        resolve = self.publish[start:end]
        self.assertIn("no build or latest mutation", resolve)
        self.assertIn("needs.resolve.outputs.publish == 'true'", self.publish)
        self.assertIn("needs.build.outputs.built == 'true'", self.publish)

    def test_manifest_check_uses_build_digest(self):
        self.assertIn('"$IMAGE:$TAG" --raw', self.publish)
        self.assertNotIn(
            "pkgs/container/workbuddy2api-hub-fork/manifests/$DIGEST", self.publish
        )

    def test_audit_recording_is_not_a_release_gate(self):
        self.assertNotIn("actions/variables", self.publish)
        self.assertIn('echo "latest_published=$TAG"', self.publish)

    def test_oci_platform_is_nested_under_platform(self):
        self.assertIn('platform = item.get("platform")', self.publish)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--workflow-dir":
        WorkflowContractTest.workflow_dir = Path(sys.argv.pop(2))
        sys.argv.pop(1)
    unittest.main()
