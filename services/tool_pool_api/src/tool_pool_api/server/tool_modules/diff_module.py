"""diff_module.py — Human-readable diff between shared-memory versions

Computes line-based diffs between two versions of a shared_business_memory
fact.  Uses Python's ``difflib`` (stdlib, streaming-friendly) for speed and
low memory overhead.  Output highlights additions, deletions, and context
lines in standard unified-diff format.

Tools registered:
  - shared_memory_diff  → compute diff between two versions of a fact

Design doc: docs/llm_wiki/SHARED_MEMORY_DESIGN.md (Fase 0 — versioning)
"""

from __future__ import annotations

import difflib
import json
import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service

from tool_pool_api.server.tool_modules import register_module
from tool_pool_api.server.tool_modules.version_module import _get_memory_version as _fetch_version

# Bind mcp_inject_client_id to its already-configured form so it can be used
# as a plain @decorator below. The factory signature is
#     mcp_inject_client_id(get_context_service_fn) -> decorator
# and the tools in this module use the @mcp_inject_client_id sugar form
# (which would otherwise pass the tool function as get_context_service_fn,
# breaking FastMCP's Pydantic schema generation). This rebind keeps the
# @mcp_inject_client_id syntax working without touching every tool.
mcp_inject_client_id = mcp_inject_client_id(get_context_service)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core diff logic (pure, sync, no DB — testable in isolation)
# ---------------------------------------------------------------------------


def _value_to_text(value: Any) -> str:
    """Convert a shared-memory value to stable, diffable text.

    Dicts are serialised as pretty-printed JSON with sorted keys so that
    structural diffs are meaningful.  Scalars become ``str(val)``.
    ``None`` produces an empty string so that missing pages surface as
    empty-content diffs.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    return str(value)


def _compute_diff(
    old_text: str,
    new_text: str,
    old_label: str = "old",
    new_label: str = "new",
    context_lines: int = 3,
) -> dict[str, Any]:
    """Compute a line-based unified diff between two text blobs.

    Args:
        old_text:      Content of the older version.
        new_text:      Content of the newer version.
        old_label:     Header label for the old version.
        new_label:     Header label for the new version.
        context_lines: Number of context lines in the diff (default 3).

    Returns:
        A structured dict with the diff output and summary statistics.
    """
    # Normalise line endings and split into lines.
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_label,
            tofile=new_label,
            n=context_lines,
            lineterm="",  # keepends=True already carries the newline
        )
    )

    # Classify lines for summary.
    added = 0
    deleted = 0
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1

    changed = 0 if added == 0 and deleted == 0 else 1  # binary "has changes"

    return {
        "has_changes": (added > 0 or deleted > 0),
        "summary": {
            "lines_added": added,
            "lines_deleted": deleted,
            "total_changes": added + deleted,
            "context_lines": context_lines,
        },
        "diff": "\n".join(diff_lines) if diff_lines else "(no differences)",
    }


def _format_version_label(entity_name: str, key: str, version: int) -> str:
    """Build a human-readable label for a version in the diff header."""
    return f"{entity_name}/{key}@v{version}"


# ---------------------------------------------------------------------------
# Business logic — diff orchestration
# ---------------------------------------------------------------------------


async def _diff_memory_versions(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    version_a: int,
    version_b: int,
    context_lines: int = 3,
) -> dict[str, Any]:
    """Fetch two versions from storage and compute their diff.

    Args:
        client_id:     Client UUID.
        entity_type:   Entity type.
        entity_name:   Entity name.
        key:           Fact key.
        version_a:     First version number (≥ 1).
        version_b:     Second version number (≥ 1).
        context_lines: Context lines for the diff (default 3, max 20).

    Returns:
        Dict with version_a, version_b, diff output, and summary.
    """
    if version_a < 1 or version_b < 1:
        raise ValueError("version numbers must be >= 1")

    if context_lines < 0:
        raise ValueError("context_lines must be >= 0")
    if context_lines > 20:
        raise ValueError("context_lines must be <= 20")

    # Fetch both versions in parallel (two independent DB calls).
    import asyncio

    async def fetch(v: int):
        return await _fetch_version(
            client_id=client_id,
            entity_type=entity_type,
            entity_name=entity_name,
            key=key,
            version=v,
        )

    (row_a, row_b) = await asyncio.gather(
        fetch(version_a),
        fetch(version_b),
    )

    # Build header labels
    label_a = _format_version_label(entity_name, key, version_a)
    label_b = _format_version_label(entity_name, key, version_b)

    # If version_a > version_b, swap so the diff always reads
    # naturally from older → newer.
    swapped = version_a > version_b
    if swapped:
        row_a, row_b = row_b, row_a
        label_a, label_b = label_b, label_a

    text_a = _value_to_text(row_a.get("value"))
    text_b = _value_to_text(row_b.get("value"))

    diff_result = _compute_diff(
        old_text=text_a,
        new_text=text_b,
        old_label=label_a,
        new_label=label_b,
        context_lines=context_lines,
    )

    # Return the original caller-specified versions in the response metadata,
    # but note whether they were swapped for natural ordering.
    result = {
        "client_id": client_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "version_a": version_a,
        "version_b": version_b,
        "swapped_for_natural_order": swapped,
        "has_changes": diff_result["has_changes"],
        "summary": diff_result["summary"],
        "diff": diff_result["diff"],
        "version_a_info": {
            "archived_at": row_a.get("archived_at"),
            "source": row_a.get("source"),
            "confidence": row_a.get("confidence"),
        },
        "version_b_info": {
            "archived_at": row_b.get("archived_at"),
            "source": row_b.get("source"),
            "confidence": row_b.get("confidence"),
        },
        "_hint": (
            "Use 'shared_memory_get_versions' to list available versions "
            "for this fact."
        ),
    }

    return result


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registers diff-generation tools."""
    registered_tools: list[str] = []

    # ----------------------------------------------------------------------
    # shared_memory_diff — compute diff between two versions
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_diff",
        description=(
            "[Shared Memory] Compute a human-readable line-based diff "
            "between two historical versions of a fact.  "
            "Uses unified diff format — lines prefixed with '+' are "
            "additions, '-' are deletions, and lines without prefix are "
            "context.  "
            "Optimised for speed and low memory overhead via "
            "streaming difflib.\n\n"
            "Edge cases:\n"
            "- Empty pages: handled (diff shows all lines as additions "
            "or deletions).\n"
            "- Identical pages: diff shows '(no differences)'.\n"
            "- Missing version: ToolError with clear message.\n\n"
            "Tip: use 'shared_memory_get_versions' to discover version "
            "numbers before diffing."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_diff(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        version_a: int,
        version_b: int,
        context_lines: int = 3,
        client_id: str | None = None,
    ) -> dict:
        """Compute a diff between two historical versions.

        Args:
            entity_type:   Entity type.
            entity_name:   Entity name.
            key:           Fact key.
            version_a:     First version number.
            version_b:     Second version number.
            context_lines: Context lines (0–20, default 3).

        Returns:
            Dict with diff output and summary statistics.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[diff_module] shared_memory_diff "
            "etype=%s ename=%s key=%s v%d→v%d ctx=%d client=%s",
            entity_type, entity_name, key,
            version_a, version_b, context_lines, client_id,
        )

        try:
            result = await _diff_memory_versions(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                version_a=version_a,
                version_b=version_b,
                context_lines=context_lines,
            )
            return result
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[diff_module] shared_memory_diff failed: %s", exc
            )
            raise ToolError(
                f"Failed to compute diff: {exc}"
            )

    logger.info("[Diff Module] Tool 'shared_memory_diff' registered.")
    registered_tools.append("shared_memory_diff")

    return registered_tools
