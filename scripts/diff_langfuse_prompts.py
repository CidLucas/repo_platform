"""
Compare prompts used in the project vs what's in Langfuse (label=production).

Outputs:
  MISSING  — used in code but not in Langfuse with production label
  ORPHAN   — in Langfuse (production) but not referenced in code
  OK       — present in both
"""
from __future__ import annotations
import json, os, sys, time
import urllib.request, urllib.error, urllib.parse
from base64 import b64encode
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "libs" / "blu_prompt_management" / "src"))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

PK = os.environ["LANGFUSE_PUBLIC_KEY"]
SK = os.environ["LANGFUSE_SECRET_KEY"]
HOST = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
AUTH = b64encode(f"{PK}:{SK}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}


def lf_get(path: str) -> tuple[int, any]:
    url = f"{HOST}{path}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


# ── 1. Collect prompts used in code ──────────────────────────────────────────
from blu_prompt_management.templates import BUILTIN_TEMPLATES

# BUILTIN_TEMPLATES is dict[str, PromptTemplateConfig] — keys are prompt names
used: set[str] = set(BUILTIN_TEMPLATES.keys())

# pick up any extra names referenced via get_prompt() calls in source
import re
for pyfile in REPO_ROOT.rglob("*.py"):
    if ".venv" in str(pyfile) or "__pycache__" in str(pyfile):
        continue
    try:
        src = pyfile.read_text(errors="ignore")
    except Exception:
        continue
    # patterns: name="tool/sql-generation"  or  prompt_name = "specialists/..."
    for m in re.finditer(r'["\']([a-z][a-z0-9/_:-]{3,60})["\']', src):
        candidate = m.group(1)
        if "/" in candidate or ":" in candidate:
            # filter to known prefixes
            if any(candidate.startswith(p) for p in (
                "agents/", "specialists/", "tool/", "skill:", "fragment/",
                "orchestrator/", "rag/", "text_to_sql/",
            )):
                used.add(candidate)

print(f"Prompts referenced in code: {len(used)}")

# ── 2. Fetch all prompts from Langfuse ───────────────────────────────────────
lf_prompts: dict[str, list[str]] = {}  # name → labels
page = 1
while True:
    status, data = lf_get(f"/api/public/v2/prompts?limit=100&page={page}")
    if status != 200:
        print(f"ERROR fetching Langfuse prompts page {page}: {status}")
        break
    items = data.get("data", [])
    if not items:
        break
    for item in items:
        name = item.get("name", "")
        labels = item.get("labels") or []
        lf_prompts.setdefault(name, [])
        lf_prompts[name] = list(set(lf_prompts[name] + labels))
    meta = data.get("meta", {})
    total_pages = meta.get("totalPages", 1)
    if page >= total_pages:
        break
    page += 1
    time.sleep(0.1)

print(f"Prompts in Langfuse: {len(lf_prompts)}")

# ── 3. Diff ───────────────────────────────────────────────────────────────────
lf_with_prod = {n for n, labels in lf_prompts.items() if "production" in labels}
lf_all = set(lf_prompts.keys())

missing = sorted(used - lf_with_prod)       # in code, not in LF with production
orphans = sorted(lf_with_prod - used)        # in LF production, not in code
in_code_no_prod = sorted((used & lf_all) - lf_with_prod)  # exists but no prod label
ok = sorted(used & lf_with_prod)

print("\n" + "="*65)
print(f"MISSING (in code, NOT in Langfuse production): {len(missing)}")
for n in missing:
    labels = lf_prompts.get(n, [])
    suffix = f"  [has labels: {labels}]" if labels else "  [not in LF at all]"
    print(f"  ✗ {n}{suffix}")

print(f"\nIN CODE, IN LF but NO 'production' label: {len(in_code_no_prod)}")
for n in in_code_no_prod:
    print(f"  ⚠ {n}  labels={lf_prompts[n]}")

print(f"\nORPHAN (in Langfuse production, NOT referenced in code): {len(orphans)}")
for n in orphans:
    print(f"  ? {n}")

print(f"\nOK (in code + Langfuse production): {len(ok)}")
for n in ok:
    print(f"  ✓ {n}")

print("="*65)
print(f"\nSummary: {len(ok)} OK | {len(missing)} MISSING | {len(in_code_no_prod)} no-prod-label | {len(orphans)} orphan")
