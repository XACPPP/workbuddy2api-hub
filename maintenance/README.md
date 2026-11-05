# WorkBuddy2API-Hub Fork maintenance

This fork owns the release pipeline, not a second copy of the business source.
Each image is built from the complete source tree of an upstream stable GitHub
Release. Fork maintenance files are composed onto that tree explicitly.

## Repository roles

| Role | Repository / path |
| --- | --- |
| Upstream | `https://github.com/ardeyouxipianyi/workbuddy2api-hub` |
| Origin | `https://github.com/XACPPP/workbuddy2api-hub` |
| Release trigger | `.github/workflows/docker-publish.yml` |
| Patch/workflow checks | `maintenance/checks/`, `maintenance/patches/` |
| Image | `ghcr.io/xacppp/workbuddy2api-hub-fork` |

The upstream default branch is `main`. Upstream provides Releases and tags;
the fork does not mirror a moving branch into its own source tree.

## Verified publish baseline

| Field | Observed value |
| --- | --- |
| Upstream Release | `v1.10.9` |
| Upstream source commit | `077fb2fcfc273e29bd1266e527afc4a3d548b516` |
| Version and `latest` manifest | `sha256:a896cee3cc5112a86b586f2d15d6a90cfca4a718fb78922eeddc7a13900accb5` |
| Platforms | `linux/amd64`, `linux/arm64` |
| Successful forced-build run | [Actions 41954943720](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41954943720) |

The manifest was queried from GHCR directly after the run. Both tags resolve
to the same multi-platform digest printed in that run's log and step summary.
On 2026-11-05, upstream `v1.10.10` was still a tag without a published Release,
so it was intentionally not used.

## Stable version rule

The automatic trigger accepts only a Release where all of these are true:

- `draft` is false;
- `prerelease` is false;
- `published_at` exists; and
- the tag is exact semver in the form `vX.Y.Z`.

Tags without a published Release are never selected automatically. This
distinction matters: when first configured (2026-11-05), upstream `v1.10.10`
was a Git tag but not a published Release, and its own test/release jobs were
red. The latest stable Release was [`v1.10.9`](https://github.com/ardeyouxipianyi/workbuddy2api-hub/releases/tag/v1.10.9),
resolved to commit `077fb2fcfc273e29bd1266e527afc4a3d548b516`.

## Schedule and manual controls

The workflow checks upstream at minute 17 of every hour (`17 * * * *`). The
workflow definition used by GitHub Actions is taken from the repository's
default branch; at execution time the upstream source is checked out from the
stable tag.

Automatic reliability comes from the hourly upstream Release check. A
`release` event is accepted only when GitHub dispatches it for the upstream
repository; fork-local Release events are ignored. GitHub does not guarantee
that an upstream repository's workflows are dispatched inside a fork, so no
release event is required for correctness.

GitHub's cron scheduler can delay scheduled runs during peak load. The stated
hourly cadence is the requested cadence, not a guarantee of exact start time.

The workflow contract then verifies this repository's maintenance files at the
fork commit SHA, not the upstream checkout's stock files.

To run it manually:

1. Open **Actions** in the fork.
2. Select **Publish Docker image**.
3. Choose **Run workflow** and enter an exact existing stable tag such as
   `v1.10.9`.
4. Leave `rebuild` off for the normal idempotent check.

Turn `rebuild` on only after checking the version, commit, and expected image.
An automatic re-scan never rebuilds a tag that is already present with both
required architectures.

The publish and promotion steps use one guarded job. This avoids GitHub's
cross-job credential boundary; an unchanged version exits during resolution
before Buildx starts. Rebuilds are serialized with a non-cancelling concurrency
group.

## Release invariants

- The version tag is pushed only after both `linux/amd64` and `linux/arm64`
  builds succeed.
- The pushed version manifest is checked after the multi-platform build.
  Only then is `latest` moved and checked again. Any failed or partial build
  leaves the old `latest` untouched.
- A workflow-wide concurrency group does not cancel a running release. A
  waiting run enters one at a time and re-checks whether the tag already
  exists.
- Tags and commits are resolved from GitHub API identity, not guessed from
  branch names.
- Build logs, source tag, source SHA, release URL, and image digest are held in
  the Actions run summary and manifest labels. Historical releases stay
  discoverable through their run records and immutable version tags.
- Old version images are not deleted.
- A GHA cache lowers repeated build time. Cache data is never used as proof
  that an image is publishable.

## Fork-specific source changes

The GitHub-only implementation did not receive a deployment copy of
`wb_proxy.py`. It therefore makes no claim that an unseen local patch can be
discarded. The image stays byte-identical to upstream, and the workflow fails
closed if an unrecorded business-source edit appears. If a maintained patch is
required, diff it against the exact source tag before adding it here.

To add a verified patch:

1. Download the exact upstream tag into a disposable checkout.
2. Make the smallest required source change.
3. Generate the diff with `git diff --binary` and save it under
   `maintenance/patches/`, for example `001-wb-proxy-...patch`.
4. Record the original problem, expected behavior, source version, and test
   evidence in this file.
5. Commit the patch; the workflow applies it before the Docker build.

Do not place a full modified `wb_proxy.py` in this repository unless the patch
mechanism itself cannot express the change. Never remove an existing local fix
because the patch source is temporarily unavailable.

## Verification levels

Workflow verification is necessary but does not prove the WorkBuddy upstream
model path works. A green Docker build only proves that both image platforms
were assembled. A two-architecture manifest check proves GHCR received both
architectures. A live gateway smoke test with real account data is separate
and is not performed by this release workflow.

The fork keeps only workflows that still have an active owner:

| Workflow | Purpose in this fork |
| --- | --- |
| `docker-publish.yml` | Upstream release discovery, deduplication, dual-arch GHCR build, latest promotion |
| `tests.yml` | Fork maintenance contract and release-engineering checks |
| `revert-guard.yml` | Pull-request rollback protection; kept unchanged |

The upstream `release-checksums.yml` has been removed from this fork. It could
not write upstream Release assets with the fork's token, and a Release event
would check out an unrelated main branch. It provided no fork maintenance value.

The upstream `release.yml` was also removed: it packages portable ZIP, OpenWrt
assets, and a draft GitHub Release, none of which this fork publishes. The
upstream business test matrix was replaced because its failing UI/403 checks
concern source that is not used to build this fork's image. The actual release
workflow still proves selected business files match upstream byte-for-byte
before Buildx starts.

`maintenance/checks/workflow-contract.test.py` pins this active-workflow set,
the `maintenance/patches/` location, GHCR target, stable-release gate, and the
rule that `latest` is not applied by the dual-platform build step. The
maintained `tests.yml` runs it together with release-engineering checks. Docker
publishing independently validates the same contract from the fork API.

The GitHub-only fork has no local patch file and does not modify any `wb_*.py`
or `dashboard.html`. If a verified local `wb_proxy.py` patch is supplied later,
it belongs under `maintenance/patches/` and must be tested against the target
upstream tag before merge.

## Manual setup

The fork owner needs to allow GitHub Actions to write packages through the
repository `GITHUB_TOKEN`. The publish workflow declares `packages: write`; no
PAT is required for the standard fork owner path. No Actions variable or
environment secret must be created for the build. If package visibility is
changed to private, a GitHub token with `read:packages` is needed for pulls:

```sh
echo '<GitHub token with read:packages>' \
  | docker login ghcr.io -u XACPPP --password-stdin
```

If anonymous pulls without a GHCR login are required, the package owner can
make it public once in GitHub package settings. That visibility choice is not
changed by the workflow.
