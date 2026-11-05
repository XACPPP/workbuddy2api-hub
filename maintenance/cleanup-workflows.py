#!/usr/bin/env python3
"""Delete workflow files that are not explicitly registered in the fork policy."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / ".github" / "workflow-policy.json"
WORKFLOW_PREFIX = ".github/workflows/"
WORKFLOW_SUFFIXES = {".yml", ".yaml"}
REQUIRED = {"docker-publish.yml", "prune-workflows.yml", "tests.yml"}


def load_allowed(policy_path=POLICY):
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    if policy.get("schema") != 1:
        raise ValueError("unsupported workflow policy schema")
    allowed = policy.get("allowed")
    if not isinstance(allowed, list) or not all(
        isinstance(name, str) and name and "/" not in name and "\\" not in name
        for name in allowed
    ):
        raise ValueError("workflow policy allowlist must contain plain filenames")
    allowed = set(allowed)
    if not REQUIRED.issubset(allowed):
        missing = ", ".join(sorted(REQUIRED - allowed))
        raise ValueError(f"workflow policy is missing required files: {missing}")
    return allowed


def obsolete_workflow_paths(tree, allowed):
    paths = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.startswith(WORKFLOW_PREFIX):
            continue
        name = path[len(WORKFLOW_PREFIX):]
        if Path(name).suffix.lower() not in WORKFLOW_SUFFIXES:
            continue
        if name not in allowed:
            paths.append((path, item["sha"]))
    return sorted(paths)


def gh(*args, input_text=None):
    result = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh {' '.join(args)} failed")
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ref", default="main")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--policy", type=Path, default=POLICY)
    args = parser.parse_args(argv)

    try:
        allowed = load_allowed(args.policy)
        tree = json.loads(
            gh("api", f"repos/{args.repo}/git/trees/{args.ref}?recursive=1")
        )
        obsolete = obsolete_workflow_paths(tree, allowed)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"workflow cleanup aborted: {exc}", file=sys.stderr)
        return 1

    if not obsolete:
        print("No unregistered workflow files found.")
        return 0

    for path, sha in obsolete:
        if not args.apply:
            print(f"would delete {path}")
            continue
        payload = json.dumps(
            {
                "message": f"chore(ci): auto-remove unregistered workflow {Path(path).name}",
                "sha": sha,
                "branch": args.ref,
            }
        )
        gh(
            "api",
            "--method",
            "DELETE",
            f"repos/{args.repo}/contents/{path}",
            "--input",
            "-",
            input_text=payload,
        )
        print(f"deleted {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
