#!/usr/bin/env python3
"""Print comma-separated OS/architecture pairs from an OCI index."""

import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as stream:
        manifest = json.load(stream)
    platforms = []
    for item in manifest.get("manifests", []):
        platform = item.get("platform") or {}
        if (
            not platform
            or platform.get("os") == "unknown"
            or platform.get("architecture") == "unknown"
        ):
            continue
        platforms.append(
            f"{platform.get('os', '')}/{platform.get('architecture', '')}"
        )
    print(",".join(platforms))


if __name__ == "__main__":
    main()
