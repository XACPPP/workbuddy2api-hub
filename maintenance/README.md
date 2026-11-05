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
| Workflow allowlist | `.github/workflow-policy.json` |

The upstream default branch is `main`. Upstream provides Releases and tags;
the fork does not mirror a moving branch into its own source tree.

## Verified publish baseline

| Field | Observed value |
| --- | --- |
| Upstream Release | `v1.10.11` |
| Upstream source commit | `6e1e54869d27ef0dce803e2293c4b95b1ecc470f` |
| Version and `latest` manifest | `sha256:2965ab0216d0787845028fc2fcabb623c6944bb43f03f17637d9fdff75bb4254` |
| Platforms | `linux/amd64`, `linux/arm64` |
| Successful build and promotion | [Actions 41998471742](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41998471742) |

The manifest was queried from GHCR directly after the run. Both tags resolve
to the same multi-platform digest printed in that run's log and step summary.
The image is currently published as `v1.10.11` and `latest`; `v1.10.9` remains
available for rollback.

The earlier `v1.10.9` baseline and its forced-build run
[Actions 41954943720](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41954943720)
remain in the audit history. On 2026-11-05, upstream `v1.10.10` was a tag
without a published Release and was intentionally not used.

The image manifest query on 2026-11-05 also showed that GHCR still contained
only `v1.10.9` and `latest`; the later `v1.10.11` release had not been built.
The failed manual run
[Actions 41997342761](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41997342761)
exposed a contract-test path bug before Buildx started.

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
fork commit SHA. The source checkout starts with the complete upstream tag and
then replaces its workflow directory with the registered fork files before the
contract test runs.

Public forks do not provide a reliable cross-repository `release` event or a
guaranteed inherited scheduler. The GitHub Actions run history had no
`schedule` event despite the workflow API reporting `active`. The workflow now
checks that state before resolution and re-enables the workflow only if GitHub
has explicitly disabled it; the hourly check remains the fallback. A future
upstream workflow can optionally call this fork with `repository_dispatch`
event type `upstream_release` and a `client_payload.tag`, but this repository
does not claim that upstream currently sends it.

The fork's publish workflow accepts that optional event, validates the
requested tag against the upstream stable Release, and then uses the same
resolution, source, build, manifest, and promotion gates as a manual run. It
does not trust the event payload as proof that a Release is stable.

On 2026-11-05 at 17:01 Asia/Shanghai, after the publish workflow succeeded and
reported `active`, the `event=schedule` query still returned no runs. Manual
publication and cleanup are verified; inherited fork cron dispatch is not.
Until a scheduled run is observed, the hourly check is a fallback rather than
a proven trigger.

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
| `prune-workflows.yml` | Deletes workflow files absent from the fork allowlist |

## Automatic workflow cleanup

`.github/workflow-policy.json` is the only source of truth for which workflow
files may remain. `prune-workflows.yml` runs immediately when a workflow or the
policy changes, and again every six hours at minute 23 (`23 */6 * * *`). It
uses the GitHub Contents API to delete every `.yml` or `.yaml` below
`.github/workflows/` that is not in the allowlist.

Safety rules:

- Only unregistered files are treated as obsolete. A workflow that failed
  once is not automatically deleted; transient failure is not evidence of
  permanent invalidity.
- A missing, malformed, or incomplete policy aborts cleanup without deleting
  anything.
- The required publishing and maintenance workflows must remain present in the
  policy. This prevents an empty allowlist from deleting the release chain.
- A normal push triggers the cleanup at once; the six-hour schedule is a
  fallback for missed runs.

`maintenance/checks/workflow-cleanup.test.py` covers the fail-closed policy
checks and confirms that only unregistered workflow files are selected.
The live canary test on 2026-11-05 added an unregistered
`prune-canary.yml`; the cleanup run deleted it automatically, and
[Actions 41957559930](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41957559930)
recorded `deleted .github/workflows/prune-canary.yml`.

The canary's resulting commit (`351a126`) is intentionally retained as a
historical audit record. The temporary workflow is not present on `main`, and
the final maintenance run
[Actions 41957800314](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41957800314)
is green.

Workflow-file cleanup and Actions-run cleanup are separate. The fork
intentionally had 52 run records on 2026-11-05, including runs from removed
workflow names (`tests`, `GHCR doctor`), while the repository itself retained
only four files. `maintenance/cleanup-runs.py` now removes completed failures,
cancellations, timeouts, and startup failures older than six hours. Successful
runs and all queued or in-progress runs are preserved as release evidence and
active work. A public fork inherits the upstream Actions history and exposes
it through the normal repository Runs API. The deleted workflow ID and its
historical run remain queryable even though no workflow file exists, so the
tab is not a reliable inventory of this fork's current workflow files.

The first live cleanup removed 31 completed failures and cancellations older
than six hours, reducing queryable runs from 54 to 25 while preserving every
successful run. The run is
[Actions 41998082078](https://github.com/XACPPP/workbuddy2api-hub/actions/runs/41998082078).

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
