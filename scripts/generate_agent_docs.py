#!/usr/bin/env python3
"""
Generate auto-skills and auto-agent-types markdown from in-repo registries.

Usage:
    python scripts/generate_agent_docs.py [--check]

If --check is provided, prints diffs and exits non-zero on mismatch.
The script adds each lib's src/ directory to sys.path so it can be run
without a virtualenv installation (useful in CI that installs editable deps).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR  = REPO_ROOT / "docs"
OUTPUT_SKILLS = DOCS_DIR / "auto-skills.md"
OUTPUT_AGENTS = DOCS_DIR / "auto-agent-types.md"

# Ensure monorepo libs are importable regardless of install state.
_LIBS = [
    "blu_agent_framework",
    "blu_tool_registry",
]
for _lib in _LIBS:
    _src = REPO_ROOT / "libs" / _lib / "src"
    if _src.exists() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_skills() -> str:
    """Build markdown from SKILL_REGISTRY (SkillDefinition objects)."""
    try:
        from blu_agent_framework.skills import SKILL_REGISTRY
    except Exception as exc:
        print(f"[generate_agent_docs] Failed to import skills module: {exc}", file=sys.stderr)
        return "# Auto-generated skills\n\n_(import failed — see stderr)_\n"

    lines = [
        "# Auto-generated skills\n",
        "_Generated from `blu_agent_framework.skills.SKILL_REGISTRY`._\n\n",
    ]
    if not SKILL_REGISTRY:
        lines.append("_(registry is empty)_\n")
        return "".join(lines)

    for slug in sorted(SKILL_REGISTRY):
        skill = SKILL_REGISTRY[slug]
        # SkillDefinition is a dataclass — access attributes directly.
        description       = getattr(skill, "description", "")
        prompt_name       = getattr(skill, "prompt_name", "")
        required_tools    = getattr(skill, "required_tool_names", [])
        max_turns         = getattr(skill, "max_turns", "?")
        on_max_turns      = getattr(skill, "on_max_turns", "?")
        tags              = getattr(skill, "tags", [])

        lines.append(f"## `{slug}`\n\n")
        lines.append(f"- **description**: {description}\n")
        lines.append(f"- **prompt_name**: `{prompt_name}`\n")
        lines.append(f"- **required_tools**: {', '.join(f'`{t}`' for t in required_tools) or '_(none)_'}\n")
        lines.append(f"- **max_turns**: {max_turns}\n")
        lines.append(f"- **on_max_turns**: `{on_max_turns}`\n")
        if tags:
            lines.append(f"- **tags**: {', '.join(tags)}\n")
        lines.append("\n")

    return "".join(lines)


def render_agents() -> str:
    """Build markdown from AgentTypeRegistry (AgentTypeConfig objects)."""
    try:
        from blu_agent_framework.registry import AgentTypeRegistry
    except Exception as exc:
        print(f"[generate_agent_docs] Failed to import registry module: {exc}", file=sys.stderr)
        return "# Auto-generated agent types\n\n_(import failed — see stderr)_\n"

    lines = [
        "# Auto-generated agent types\n",
        "_Generated from `blu_agent_framework.registry.AgentTypeRegistry`._\n\n",
    ]

    all_types = AgentTypeRegistry.all()
    if not all_types:
        lines.append("_(registry is empty)_\n")
        return "".join(lines)

    for slug in sorted(all_types):
        cfg = all_types[slug]
        name          = getattr(cfg, "name", slug)
        description   = getattr(cfg, "description", "")
        tier_required = getattr(cfg, "tier_required", None)
        tier_str      = tier_required.value if tier_required is not None else "?"
        enabled_tools = getattr(cfg, "enabled_tools", [])
        prompt_name   = getattr(cfg, "prompt_name", "")
        fragments     = getattr(cfg, "fragments", [])
        max_turns     = getattr(cfg, "max_turns", "?")
        on_max_turns  = getattr(cfg, "on_max_turns", "?")
        routing_hint  = getattr(cfg, "routing_hint", "")

        lines.append(f"## `{slug}` — {name}\n\n")
        lines.append(f"- **description**: {description}\n")
        lines.append(f"- **tier_required**: `{tier_str}`\n")
        lines.append(f"- **max_turns**: {max_turns}  **on_max_turns**: `{on_max_turns}`\n")
        if enabled_tools:
            lines.append(f"- **enabled_tools**: {', '.join(f'`{t}`' for t in enabled_tools)}\n")
        if prompt_name:
            lines.append(f"- **prompt_name**: `{prompt_name}`\n")
        if fragments:
            lines.append(f"- **fragments**: {', '.join(fragments)}\n")
        if routing_hint:
            lines.append(f"- **routing_hint**: {routing_hint}\n")
        lines.append("\n")

    return "".join(lines)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def write_if_changed(path: Path, content: str, check: bool) -> int:
    """Write *content* to *path* unless unchanged.  In check mode, diff only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text() if path.exists() else ""
    if old.strip() == content.strip():
        print(f"{path.name}: up to date")
        return 0
    if check:
        print(f"DIFF {path.relative_to(REPO_ROOT)}:")
        _print_diff(old, content)
        return 2
    path.write_text(content)
    print(f"Wrote {path}")
    return 0


def _print_diff(old: str, new: str) -> None:
    import difflib
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="current",
        tofile="generated",
    )
    sys.stdout.writelines(diff)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="Exit non-zero if docs are out of date")
    args = p.parse_args()

    skills_md = render_skills()
    agents_md = render_agents()

    rc1 = write_if_changed(OUTPUT_SKILLS, skills_md, args.check)
    rc2 = write_if_changed(OUTPUT_AGENTS, agents_md, args.check)

    if rc1 or rc2:
        print("\nRun `python scripts/generate_agent_docs.py` to regenerate.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
