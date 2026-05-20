"""Phase 0 / F0.5 — Langfuse prompt audit + in-repo fallback inventory.

Run this script in CI (and on demand) to verify that every Blu MVP prompt
referenced by application code has:

1. a built-in fallback registered in
   ``libs/blu_prompt_management/.../templates.py`` (``BUILTIN_TEMPLATES``);
2. an in-repo Markdown fallback under
   ``libs/blu_prompt_management/prompts/<domain>/<slug>.md`` so that
   reviewers can diff prompt content without parsing Python; and
3. a ``production``-labeled version in Langfuse.

Exits non-zero when any MVP prompt is missing a production label or a
markdown fallback. Use ``--write-fallbacks`` to materialize the markdown
files from the current built-in templates (idempotent).

Usage::

    python scripts/audit_langfuse_prompts.py
    python scripts/audit_langfuse_prompts.py --write-fallbacks
    python scripts/audit_langfuse_prompts.py --json

Environment:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY  (required for live lookup)
    LANGFUSE_HOST                             (default: https://us.cloud.langfuse.com)
    LANGFUSE_PROMPT_LABEL                     (default: production)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from base64 import b64encode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PM_PKG = REPO_ROOT / "libs" / "blu_prompt_management" / "src" / "blu_prompt_management"
FALLBACK_DIR = PM_PKG / "prompts"

if str(PM_PKG.parent) not in sys.path:
    sys.path.insert(0, str(PM_PKG.parent))


def _load_builtin_templates() -> dict[str, Any]:
    from blu_prompt_management.templates import BUILTIN_TEMPLATES  # type: ignore

    return BUILTIN_TEMPLATES


# ---------------------------------------------------------------------------
# MVP prompt inventory — must match docs/internal/kpi-catalog.md and the
# fragments composed by libs/blu_prompt_management/.../dynamic_builder.py.
# ---------------------------------------------------------------------------

#: Prompts the MVP is allowed to ship without a production label in Langfuse
#: yet (e.g. fragments only consumed indirectly via composition). They still
#: require a markdown fallback.
WAIVE_LANGFUSE_PRODUCTION: set[str] = {
    # Fragments are composed locally, never fetched as a single prompt.
    *{name for name in []},
}

#: Prompts that must NOT exist anymore — flagged for cleanup. Source:
#: /memories/repo/langfuse-prompts.md "Garbage Prompts".
GARBAGE_PROMPTS: set[str] = {
    "atendente/confirmacao-agendamento",
    "atendente/esclarecimento",
    "rag/query",
    "rag/hybrid",
    "elicitation/options",
    "elicitation/confirmation",
    "elicitation/freeform",
    "error/tool-failed",
    "error/not-found",
    "sql-generation",
    "sql/analytics-v2-schema",
    "sql/analytics-v2-guide",
}


# ---------------------------------------------------------------------------
# Langfuse fetch
# ---------------------------------------------------------------------------


@dataclass
class LangfuseStatus:
    """Status of a single prompt name on the Langfuse server."""

    name: str
    found: bool
    versions: list[int] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    has_production: bool = False
    error: str | None = None


def _fetch_langfuse(prompt_name: str, *, host: str, headers: dict[str, str], label: str) -> LangfuseStatus:
    import urllib.parse
    import urllib.request

    encoded = urllib.parse.quote(prompt_name, safe="")
    url = f"{host.rstrip('/')}/api/public/v2/prompts/{encoded}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - allow env-controlled host
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network shim
        return LangfuseStatus(name=prompt_name, found=False, error=str(exc))

    labels = data.get("labels") or []
    if isinstance(data.get("versions"), list):
        versions = [int(v) for v in data["versions"] if isinstance(v, int | str)]
    else:
        versions = [int(data["version"])] if data.get("version") is not None else []
    return LangfuseStatus(
        name=prompt_name,
        found=True,
        versions=versions,
        labels=list(labels),
        has_production=label in labels,
    )


# ---------------------------------------------------------------------------
# Fallback file management
# ---------------------------------------------------------------------------


def _fallback_path(prompt_name: str) -> Path:
    """Map a prompt name to ``prompts/<domain>/<slug>.md``.

    Names like ``atendente/default`` → ``prompts/atendente/default.md``.
    Names without a ``/`` go under ``prompts/_uncategorized/<name>.md``.
    """
    if "/" in prompt_name:
        domain, slug = prompt_name.split("/", 1)
    else:
        domain, slug = "_uncategorized", prompt_name
    safe_slug = slug.replace("/", "_")
    return FALLBACK_DIR / domain / f"{safe_slug}.md"


def _render_fallback(template: Any) -> str:
    return (
        f"---\n"
        f"name: {template.name}\n"
        f"category: {template.category.value}\n"
        f"version: {template.version}\n"
        f"required_variables: {list(template.required_variables)}\n"
        f"optional_variables: {dict(template.optional_variables)}\n"
        f"---\n\n"
        f"<!--\n"
        f"This file is the in-repo fallback for prompt `{template.name}`.\n"
        f"It is used when Langfuse is unreachable. The canonical content lives\n"
        f"in Langfuse under label `production` (see\n"
        f"docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).\n"
        f"\n"
        f"Description: {template.description}\n"
        f"-->\n\n"
        f"{template.content.rstrip()}\n"
    )


def _write_fallbacks(builtins: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    for name, template in builtins.items():
        path = _fallback_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = _render_fallback(template)
        if not path.exists() or path.read_text(encoding="utf-8") != rendered:
            path.write_text(rendered, encoding="utf-8")
            written.append(path.relative_to(REPO_ROOT))
    return written


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@dataclass
class AuditRow:
    name: str
    in_builtins: bool
    fallback_path: str
    fallback_exists: bool
    langfuse: LangfuseStatus | None
    waived: bool

    @property
    def status(self) -> str:
        if not self.in_builtins:
            return "MISSING_BUILTIN"
        if not self.fallback_exists:
            return "MISSING_FALLBACK"
        if self.waived:
            return "OK_WAIVED"
        if self.langfuse is None:
            return "OK_NO_NETWORK"
        if not self.langfuse.found:
            return "MISSING_LANGFUSE"
        if not self.langfuse.has_production:
            return "MISSING_PRODUCTION_LABEL"
        return "OK"


def audit(*, check_langfuse: bool, label: str) -> list[AuditRow]:
    builtins = _load_builtin_templates()
    rows: list[AuditRow] = []

    headers: dict[str, str] | None = None
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    if check_langfuse:
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        if not public_key or not secret_key:
            print(
                "[warn] LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set — "
                "skipping live Langfuse checks.",
                file=sys.stderr,
            )
            check_langfuse = False
        else:
            token = b64encode(f"{public_key}:{secret_key}".encode()).decode()
            headers = {"Authorization": f"Basic {token}"}

    for name, template in sorted(builtins.items()):
        fp = _fallback_path(name)
        lf_status = None
        if check_langfuse and headers is not None:
            lf_status = _fetch_langfuse(name, host=host, headers=headers, label=label)
        rows.append(
            AuditRow(
                name=name,
                in_builtins=True,
                fallback_path=str(fp.relative_to(REPO_ROOT)),
                fallback_exists=fp.exists(),
                langfuse=lf_status,
                waived=name in WAIVE_LANGFUSE_PRODUCTION,
            )
        )
        # Touch the dataclass attribute for completeness
        _ = template

    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_table(rows: list[AuditRow]) -> None:
    width = max((len(r.name) for r in rows), default=20)
    print(f"\n{'PROMPT'.ljust(width)}  STATUS                    FALLBACK")
    print("-" * (width + 60))
    for r in rows:
        print(f"{r.name.ljust(width)}  {r.status.ljust(24)}  {r.fallback_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Blu MVP Langfuse prompts.")
    parser.add_argument(
        "--write-fallbacks",
        action="store_true",
        help="Write/refresh in-repo Markdown fallbacks under libs/blu_prompt_management/prompts/.",
    )
    parser.add_argument(
        "--no-langfuse",
        action="store_true",
        help="Skip live Langfuse calls (useful in offline CI).",
    )
    parser.add_argument(
        "--label",
        default=os.environ.get("LANGFUSE_PROMPT_LABEL", "production"),
        help="Required Langfuse label (default: production).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of a table."
    )
    args = parser.parse_args(argv)

    if args.write_fallbacks:
        builtins = _load_builtin_templates()
        written = _write_fallbacks(builtins)
        for p in written:
            print(f"[wrote] {p}")
        if not written:
            print("[ok] all in-repo fallbacks already up to date.")

    rows = audit(check_langfuse=not args.no_langfuse, label=args.label)

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": r.name,
                        "status": r.status,
                        "fallback_path": r.fallback_path,
                        "fallback_exists": r.fallback_exists,
                        "in_builtins": r.in_builtins,
                        "langfuse": (
                            None
                            if r.langfuse is None
                            else {
                                "found": r.langfuse.found,
                                "has_production": r.langfuse.has_production,
                                "labels": r.langfuse.labels,
                                "versions": r.langfuse.versions,
                                "error": r.langfuse.error,
                            }
                        ),
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
    else:
        _print_table(rows)

    failures = [r for r in rows if r.status not in {"OK", "OK_WAIVED", "OK_NO_NETWORK"}]
    if failures:
        print(
            f"\n[fail] {len(failures)} prompt(s) failed audit. "
            f"Run with --write-fallbacks and/or push the missing Langfuse versions.",
            file=sys.stderr,
        )
        return 1
    print("\n[ok] all MVP prompts have built-in templates and in-repo fallbacks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
