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
        os_name = platform.get("os") or item.get("os")
        architecture = platform.get("architecture") or item.get("architecture")
        if not os_name or not architecture:
            continue
        if os_name == "unknown" or architecture == "unknown":
            continue
        platforms.append(f"{os_name}/{architecture}")
    print(",".join(platforms))


if __name__ == "__main__":
    main()
