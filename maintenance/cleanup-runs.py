#!/usr/bin/env python3
"""Delete old failed workflow runs while preserving successful audit records."""

import argparse
import datetime as dt
import json
import subprocess
import sys


DELETABLE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "startup_failure"}


def gh(*args):
    result = subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh {' '.join(args)} failed")
    return result.stdout


def load_runs(repo):
    pages = json.loads(
        gh("api", "--paginate", f"repos/{repo}/actions/runs?per_page=100", "--slurp")
    )
    return [run for page in pages for run in page.get("workflow_runs", [])]


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def select_stale_runs(runs, now, minimum_age):
    cutoff = now - minimum_age
    selected = []
    for run in runs:
        if run.get("status") != "completed":
            continue
        timestamp = run.get("created_at") or run.get("run_started_at")
        if not timestamp:
            continue
        if run.get("conclusion") not in DELETABLE_CONCLUSIONS:
            continue
        if parse_time(timestamp) <= cutoff:
            selected.append(run)
    return sorted(selected, key=lambda run: (run["created_at"], run["id"]))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--minimum-age-hours", type=int, default=6)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.minimum_age_hours < 1:
        print("workflow run cleanup aborted: minimum age must be at least 1 hour")
        return 1

    try:
        runs = load_runs(args.repo)
        now = dt.datetime.now(dt.timezone.utc)
        stale = select_stale_runs(
            runs, now, dt.timedelta(hours=args.minimum_age_hours)
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"workflow run cleanup aborted: {exc}", file=sys.stderr)
        return 1

    if not stale:
        print("No stale failed or cancelled workflow runs found.")
        return 0

    for run in stale:
        label = (
            f"{run['id']} {run.get('name', '?')} "
            f"{run.get('conclusion', '?')} {run.get('created_at', '?')}"
        )
        if not args.apply:
            print(f"would delete {label}")
            continue
        gh(
            "api",
            "--method",
            "DELETE",
            f"repos/{args.repo}/actions/runs/{run['id']}",
        )
        print(f"deleted {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
