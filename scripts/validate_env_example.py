#!/usr/bin/env python3
"""
Validate that `.env.example` contains the required env var keys listed in
`scripts/required_envs.json`.

Intended to run in CI on PRs to ensure the example file matches required keys.
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ROOT / "scripts" / "required_envs.json"
ENV_EXAMPLE = ROOT / ".env.example"


def load_required():
    with open(REQUIRED, "r", encoding="utf-8") as f:
        return json.load(f)


def load_example_keys():
    if not ENV_EXAMPLE.exists():
        print(f"Error: {ENV_EXAMPLE} not found")
        sys.exit(2)

    keys = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            keys.add(key)
    return keys


def main():
    req = load_required()
    example_keys = load_example_keys()

    missing = set()
    # Ensure global ones are present
    for k in req.get("global", []):
        if k not in example_keys:
            missing.add(k)

    # Ensure union of service keys are present (optional but helpful)
    for svc, arr in req.items():
        if svc == "global":
            continue
        for k in arr:
            if k not in example_keys:
                missing.add(k)

    if not missing:
        print("OK: .env.example contains all required keys")
        return 0

    print("ERROR: .env.example is missing the following required keys:")
    for k in sorted(missing):
        print(f" - {k}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
