"""Push a single prompt to Langfuse by name. Uses urllib only."""
from __future__ import annotations
import argparse, json, os, re, sys
from base64 import b64encode
from pathlib import Path
import urllib.request, urllib.error

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "libs" / "blu_prompt_management" / "src"))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

PK = os.environ["LANGFUSE_PUBLIC_KEY"]
SK = os.environ["LANGFUSE_SECRET_KEY"]
HOST = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
AUTH = b64encode(f"{PK}:{SK}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}


def req(method, path, body=None):
    url = f"{HOST}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get_prompt_content(name: str) -> str:
    """Try templates first, then fallback .md files."""
    # try fallback md
    slug = name.replace("/", os.sep)
    md_path = REPO_ROOT / "libs/blu_prompt_management/src/blu_prompt_management/prompts" / f"{slug}.md"
    if md_path.exists():
        txt = md_path.read_text()
        txt = re.sub(r"^---.*?---\s*", "", txt, flags=re.DOTALL)
        txt = re.sub(r"<!--.*?-->", "", txt, flags=re.DOTALL)
        return txt.strip()

    # try templates.py (includes L3 skills via get_builtin_template)
    from blu_prompt_management.templates import get_builtin_template
    t = get_builtin_template(name)
    if t is not None:
        return t.content
    raise ValueError(f"Prompt '{name}' not found in templates or fallback .md")


def push(name: str, force: bool = False):
    # check if exists with production label
    status, data = req("GET", f"/api/public/v2/prompts/{urllib.parse.quote(name, safe='')}?label=production")
    if status == 200 and not force:
        print(f"SKIP {name} — already in Langfuse with label=production")
        return

    content = get_prompt_content(name)
    status2, resp2 = req("POST", "/api/public/v2/prompts", {
        "name": name,
        "prompt": content,
        "labels": ["production"],
        "config": {"type": "text"},
    })
    if status2 in (200, 201):
        print(f"PUSHED {name} — status {status2}")
    else:
        print(f"ERROR {name} — status {status2}: {resp2}")


import urllib.parse

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    push(args.name, args.force)
