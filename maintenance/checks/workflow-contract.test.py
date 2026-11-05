#!/usr/bin/env python3
"""Static contract checks for the fork-only GHCR workflow."""

import sys
import unittest
from pathlib import Path


class WorkflowContractTest(unittest.TestCase):
    workflow_dir = None

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.workflows = cls.workflow_dir or cls.root / ".github" / "workflows"
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
                "prune-workflows.yml",
                "revert-guard.yml",
                "tests.yml",
            },
        )
        self.assertFalse(
            (self.workflows / "release.yml").exists(),
            "upstream release packaging has no role in this fork",
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
        build = self.publish.index("id: build")
        promote = self.publish.index("name: Promote verified version to latest")
        self.assertNotIn("value=latest", self.publish[build:promote])
        self.assertIn("imagetools create", self.publish[promote:])
        self.assertIn('"$IMAGE:latest" --raw', self.publish[promote:])

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
        self.assertIn("build and latest are untouched", self.publish)
        self.assertIn("if: steps.resolve.outputs.publish == 'true'", self.publish)

    def test_every_publication_step_is_gated_by_resolution(self):
        start = self.publish.index("id: resolve")
        end = self.publish.index("id: build")
        before_build = self.publish[start:end]
        for step in (
            "Check out upstream source at the stable tag",
            "Apply maintained patches",
            "Validate workflow contract",
            "Log in to GHCR",
            "Extract Docker metadata",
        ):
            block = before_build[before_build.index(step):]
            head = "\n".join(block.splitlines()[:8])
            self.assertRegex(
                head,
                r"if:\s*(?:>-\s*)?\$?\{?\{?\s*steps\.resolve\.outputs\.publish\s*==\s*'true'",
            )

    def test_publish_validates_the_composed_checkout(self):
        step = self.publish.index("name: Validate workflow contract")
        block = self.publish[step:]
        head = "\n".join(block.splitlines()[:10])
        self.assertIn("maintenance/checks/workflow-contract.test.py", head)
        self.assertNotIn("CONTRACT_REPOSITORY", head)

    def test_release_event_cannot_build_from_fork(self):
        self.assertIn(
            '"$SOURCE_REPOSITORY" != "$UPSTREAM_OWNER/$UPSTREAM_REPO"',
            self.publish,
        )

    def test_schedule_is_explicitly_reenabled(self):
        self.assertIn("gh workflow enable docker-publish.yml", self.publish)
        self.assertIn('if [[ "$STATE" != "active" ]]', self.publish)

    def test_failure_cannot_reach_latest(self):
        promote = self.publish.index("name: Promote verified version to latest")
        build = self.publish.index("name: Build and push version tag")
        self.assertLess(build, promote)
        self.assertIn("manifest-platforms.py latest.json", self.publish)
        self.assertIn("latest lacks", self.publish)

    def test_manifest_check_uses_pushed_tag(self):
        self.assertIn('"$IMAGE:$TAG" --raw', self.publish)
        self.assertNotIn(
            "pkgs/container/workbuddy2api-hub-fork/manifests/$DIGEST", self.publish
        )

    def test_audit_recording_is_not_a_release_gate(self):
        self.assertNotIn("actions/variables", self.publish)
        self.assertIn('echo "latest_published=$TAG"', self.publish)

    def test_oci_platform_is_nested_under_platform(self):
        manifest = self.root / "maintenance" / "checks" / "manifest-platforms.py"
        helper = manifest.read_text(encoding="utf-8")
        self.assertIn('item.get("platform")', helper)
        self.assertIn('item.get("os")', helper)

    def test_existing_tag_uses_registry_manifest(self):
        resolve_start = self.publish.index("name: Resolve stable upstream Release")
        resolve_end = self.publish.index("name: Stop when this version")
        self.assertIn('inspect "$IMAGE:$TAG" --raw', self.publish[resolve_start:resolve_end])
        self.assertIn(
            "maintenance/checks/manifest-platforms.py",
            self.publish[resolve_start:resolve_end],
        )

    def test_auto_cleanup_is_registered_and_periodic(self):
        cleanup = (self.workflows / "prune-workflows.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('cron: "23 */6 * * *"', cleanup)
        self.assertIn("contents: write", cleanup)
        self.assertIn("cleanup-workflows.py", cleanup)
        policy = self.root / ".github" / "workflow-policy.json"
        self.assertTrue(policy.is_file())


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--workflow-dir":
        WorkflowContractTest.workflow_dir = Path(sys.argv.pop(2))
        sys.argv.pop(1)
    unittest.main()
