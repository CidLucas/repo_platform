#!/usr/bin/env python3
"""
Generate auto-skills and auto-agent-types markdown files from in-repo registries.

Usage:
    python scripts/generate_agent_docs.py [--check]

If --check is provided, script prints diffs and exits with non-zero if mismatch.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT_SKILLS = DOCS_DIR / "auto-skills.md"
OUTPUT_AGENTS = DOCS_DIR / "auto-agent-types.md"


def render_skills():
    # Dynamic import: assume libs are on PYTHONPATH when running from project root
    try:
        registry_mod = importlib.import_module("blu_agent_framework.skills")
    except Exception as e:
        print("Failed to import skills module:", e)
        return ""

    skills = getattr(registry_mod, "SKILL_REGISTRY", {})
    lines = ["# Auto-generated skills\n", "Generated from SKILL_REGISTRY\n\n"]
    for slug, meta in sorted(skills.items()):
        lines.append(f"## {slug}\n")
        if isinstance(meta, dict):
            desc = meta.get("description") or meta.get("prompt_name") or ""
            lines.append(f"- description: {desc}\n")
            lines.append("\n")
        else:
            lines.append("- description: (unserializable metadata)\n\n")
    return "".join(lines)


def render_agents():
    try:
        registry_mod = importlib.import_module("blu_agent_framework.registry")
    except Exception as e:
        print("Failed to import registry module:", e)
        return ""

    AgentTypeRegistry = getattr(registry_mod, "AgentTypeRegistry", None)
    lines = ["# Auto-generated agent types\n", "Generated from AgentTypeRegistry\n\n"]
    if AgentTypeRegistry is None:
        return "".join(lines)
    # Try to list types if a list_types exists
    try:
        types = AgentTypeRegistry.list_types()
    except Exception:
        types = []
    for t in types:
        lines.append(f"## {t}\n- description: TODO\n\n")
    return "".join(lines)


def write_if_changed(path: Path, content: str, check: bool) -> int:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    if path.exists():
        old = path.read_text()
    else:
        old = ""
    if old.strip() == content.strip():
        print(f"{path.name}: up to date")
        return 0
    if check:
        print(f"{path.name} differs")
        return 2
    path.write_text(content)
    print(f"Wrote {path}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    skills_md = render_skills()
    agents_md = render_agents()

    rc1 = write_if_changed(OUTPUT_SKILLS, skills_md, args.check)
    rc2 = write_if_changed(OUTPUT_AGENTS, agents_md, args.check)
    if rc1 or rc2:
        sys.exit(2)


if __name__ == "__main__":
    main()
