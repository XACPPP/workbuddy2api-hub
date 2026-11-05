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
| Image | `ghcr.io/xacppp/workbuddy2api-hub` |

The upstream default branch is `main`. Upstream provides Releases and tags;
the fork does not mirror a moving branch into its own source tree.

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

The workflow checks upstream at minute 17 of every hour (`17 * * * *`).
The repository's default-branch workflow definition is used, so this schedule
runs even though the business source itself is checked out from the upstream
tag inside the job.

To run it manually:

1. Open **Actions** in the fork.
2. Select **Publish Docker image**.
3. Choose **Run workflow** and enter an exact existing stable tag such as
   `v1.10.9`.
4. Leave `rebuild` off for the normal idempotent check.

Turn `rebuild` on only after reviewing the version, commit, and expected image.
An automatic re-scan never rebuilds a tag that already exists with both
required architectures.

## Release invariants

- The version tag is pushed only after both `linux/amd64` and `linux/arm64`
  builds succeed.
- `latest` is updated only in a later job that checks the version manifest
  again. Any failed or partial build leaves the old `latest` untouched.
- A workflow-wide concurrency group does not cancel a running release. A
  waiting run enters one at a time and re-checks whether the tag already
  exists.
- Tags and commits are resolved from GitHub API identity, not guessed from
  branch names.
- Build logs, source tag, source SHA, release URL, and image digest are held in
  the Actions run summary and manifest labels. Audit bookkeeping never gates
  publication, so a GitHub token's inability to write repository variables
  cannot change image availability.
- Old version images are not deleted.
- A GHA cache lowers repeated build time. Cache data is never used as proof
  that an image is publishable.

## Fork-specific source changes

At initialization the supplied workspace contained only the upstream checkout
and no separate deployment copy or authenticated NAS filesystem to inspect. A
synthetic source diff would therefore be misleading. The build stays
byte-identical to upstream, and the workflow fails closed if an unrecorded
business-source edit appears. If the real NAS deployment contains a patched
`wb_proxy.py`, diff it against the exact source tag before adding a patch here.

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
| `tests.yml` | Upstream Python/Node regression suite and source-version guard |
| `release.yml` | Upstream release artifact gate; kept unchanged and relevant to its own tags |
| `revert-guard.yml` | Pull-request rollback protection; kept unchanged |

The upstream `release-checksums.yml` has been removed from this fork. It could
not write upstream Release assets with the fork's token, and a Release event
would check out an unrelated main branch. It provided no fork maintenance value.

`maintenance/checks/workflow-contract.test.py` pins this active-workflow set,
the `maintenance/patches/` location, GHCR target, stable-release gate, and the
rule that `latest` is not applied by the dual-platform build step. Docker
publishing refuses to build if this contract test fails.

## Manual setup

The fork owner needs to allow GitHub Actions to write packages through the
repository `GITHUB_TOKEN`. The publish workflow declares `packages: write`; no
PAT is required for the standard fork owner path. No Actions variable or
environment secret must be created for the build.

After the first successful run, make the GHCR package public if anonymous pull
without registry login is required. Package visibility is a one-time GitHub
setting and is not changed by the workflow.
