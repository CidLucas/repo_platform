#!/usr/bin/env python3
"""
scripts/check_env.py

Simple env var checker for core services. Use during local boot or CI to
ensure required environment variables are present.

Usage:
  python scripts/check_env.py            # check global + all services
  python scripts/check_env.py --service tool_pool_api

Exit code: 0 = OK, 1 = missing vars
"""
import json
import os
import sys
from argparse import ArgumentParser

ROOT = os.path.dirname(os.path.dirname(__file__))
REQUIRED_PATH = os.path.join(ROOT, "scripts", "required_envs.json")


def load_required():
    with open(REQUIRED_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_service(reqs, service=None):
    missing = {}
    global_vars = set(reqs.get("global", []))

    services = [service] if service else [s for s in reqs.keys() if s != "global"]

    for svc in services:
        svc_vars = global_vars.union(set(reqs.get(svc, [])))
        miss = [v for v in sorted(svc_vars) if not os.getenv(v)]
        if miss:
            missing[svc] = miss

    return missing


def main():
    p = ArgumentParser()
    p.add_argument("--service", help="Service to check (default: all)")
    args = p.parse_args()

    try:
        reqs = load_required()
    except FileNotFoundError:
        print(f"required_envs.json not found at: {REQUIRED_PATH}")
        sys.exit(2)

    missing = check_service(reqs, args.service)

    if not missing:
        if args.service:
            print(f"OK: all required env vars present for service '{args.service}'")
        else:
            print("OK: all required env vars present for all services")
        return 0

    print("Missing required environment variables:")
    for svc, vars in missing.items():
        print(f" - {svc}: {', '.join(vars)}")

    return 1


if __name__ == "__main__":
    code = main()
    sys.exit(code)
