"""
Push all BUILTIN_TEMPLATES (+ L3 skill templates) to Langfuse.

For each template:
  - If it does NOT exist in Langfuse → create it (label=production).
  - If it EXISTS but does NOT have label 'production' → create a new version with label=production.
  - If it EXISTS with label 'production' → skip (idempotent).

Usage:
  python3 scripts/push_prompts_to_langfuse.py
  python3 scripts/push_prompts_to_langfuse.py --dry-run
  python3 scripts/push_prompts_to_langfuse.py --force   # push even if production label exists
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode

from dotenv import load_dotenv

load_dotenv(".env")

PK = os.environ["LANGFUSE_PUBLIC_KEY"]
SK = os.environ["LANGFUSE_SECRET_KEY"]
HOST = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
AUTH = b64encode(f"{PK}:{SK}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Repo path
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "libs", "blu_prompt_management", "src"))


def _req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    url = f"{HOST}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def get_prompt(name: str) -> dict | None:
    encoded = urllib.parse.quote(name, safe="")
    status, data = _req("GET", f"/api/public/v2/prompts/{encoded}")
    return data if status == 200 and isinstance(data, dict) else None


def create_prompt(name: str, content: str, tags: list[str] | None = None) -> bool:
    body = {
        "name": name,
        "prompt": content,
        "type": "text",
        "labels": ["production"],
        "tags": tags or [],
    }
    status, resp = _req("POST", "/api/public/v2/prompts", body)
    ok = status in (200, 201)
    if not ok:
        print(f"    ⚠ CREATE failed ({status}): {resp}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Push even if production label already exists")
    parser.add_argument("--only", help="Comma-separated list of prompt names to push")
    args = parser.parse_args()

    from blu_prompt_management.templates import BUILTIN_TEMPLATES, _L3_SKILL_TEMPLATE_MAP

    all_templates = {**BUILTIN_TEMPLATES, **_L3_SKILL_TEMPLATE_MAP}

    only_set = set(args.only.split(",")) if args.only else None

    created = skipped = failed = 0

    for name, template in sorted(all_templates.items()):
        if only_set and name not in only_set:
            continue

        existing = get_prompt(name)
        has_production = (
            existing is not None
            and "production" in (existing.get("labels") or [])
        )

        if has_production and not args.force:
            print(f"  ✓ SKIP (already has production): {name}")
            skipped += 1
            continue

        action = "UPDATE" if existing else "CREATE"
        print(f"  → {action}: {name}", end="")

        if args.dry_run:
            print("  [dry-run]")
            continue

        tags = list(template.tags) if hasattr(template, "tags") and template.tags else []
        ok = create_prompt(name, template.content, tags=tags)
        if ok:
            print("  ✅")
            created += 1
        else:
            print("  ❌")
            failed += 1

        time.sleep(0.2)  # rate limit

    print(f"\nDone: {created} pushed, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
