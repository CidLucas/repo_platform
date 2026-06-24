"""version_module.py — Shared Memory Version Storage & Retrieval

Registers L1 tools for archiving and querying historical versions of
shared_business_memory entries.  Every time a fact is overwritten via
upsert, the previous version is saved to ``shared_business_memory_versions``.
Agents can then retrieve the full version history or a specific snapshot.

Content hashing (SHA-256) enables deduplication and change detection.

Tools registered:
  - shared_memory_get_versions       → list all historical versions for a fact
  - shared_memory_get_version        → retrieve a specific version by number
  - shared_memory_store_version      → explicit checkpoint without changing value
  - shared_memory_get_diff           → compare two versions (jsondiff or text)
  - shared_memory_get_current_version → get current version metadata

Design doc: docs/llm_wiki/SHARED_MEMORY_DESIGN.md (Fase 0 — versioning schema)
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client

from . import register_module

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VERSION_TABLE = "shared_business_memory_versions"

# Maximum versions kept per (client_id, entity_type, entity_name, key).
# When exceeded, oldest versions are pruned automatically.
_MAX_VERSIONS_PER_KEY = 50

# Same valid sources as memory_module
_VALID_SOURCES: frozenset[str] = frozenset(
    {"manual", "memory_agent", "specialist", "migration", "system"}
)

# Same valid entity types as memory_module
_VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"skill", "client", "contact", "supplier", "user", "snapshot", "routine",
     "agent_result", "agent_metadata"}
)

# ---------------------------------------------------------------------------
# jsondiff import (optional — falls back to text diff if unavailable)
# ---------------------------------------------------------------------------

try:
    from jsondiff import diff as jsondiff_diff  # type: ignore[import-untyped]
    _JSONDIFF_AVAILABLE = True
except ImportError:
    jsondiff_diff = None  # type: ignore[assignment]
    _JSONDIFF_AVAILABLE = False
    logger.info(
        "[version_module] jsondiff not installed — get_diff will use text "
        "diff (difflib) for all comparisons."
    )


# ---------------------------------------------------------------------------
# Helpers — content hashing
# ---------------------------------------------------------------------------


def compute_content_hash(value: Any) -> str:
    """Compute SHA-256 of the JSON value with canonical key ordering.

    Serialises ``value`` as JSON with ``sort_keys=True`` and
    ``ensure_ascii=False``, then returns the hex digest of the SHA-256
    hash of the UTF-8 encoded string.

    Args:
        value: Any JSON-serialisable value (dict, list, str, int, float,
               bool, None).

    Returns:
        64-character hex string representing the SHA-256 hash.
    """
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False,
                           default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _text_diff(old_value: Any, new_value: Any) -> list[str]:
    """Unified text diff between two JSON-serialised values.

    Serialises both values with ``indent=2`` and produces a unified diff
    via ``difflib.unified_diff``.  Useful when ``jsondiff`` is not
    installed or for ``mode=\"text\"``.

    Args:
        old_value: The older value.
        new_value: The newer value.

    Returns:
        A list of unified-diff lines (may be empty if values are identical).
    """
    old_text = json.dumps(old_value, indent=2, ensure_ascii=False,
                          default=str)
    new_text = json.dumps(new_value, indent=2, ensure_ascii=False,
                          default=str)
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    return list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="version_a",
        tofile="version_b",
        n=3,
    ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    """Validate entity_type against the allowed set. Raises ValueError."""
    if entity_type not in _VALID_ENTITY_TYPES:
        raise ValueError(
            f"Invalid {field_name} '{entity_type}'. "
            f"Must be one of: {sorted(_VALID_ENTITY_TYPES)}"
        )


def _normalize_entity_name(name: str) -> str:
    """Normalize entity name: lowercase, trimmed."""
    return name.strip().lower()


# ---------------------------------------------------------------------------
# Business logic — archiving
# ---------------------------------------------------------------------------


async def _archive_memory_version(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
) -> dict | None:
    """Archive the current version of a shared-memory fact before it is overwritten.

    Reads the existing row from ``shared_business_memory`` and saves a snapshot
    to ``shared_business_memory_versions``.  Should be called *before* an upsert
    that will change the fact.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type (e.g. ``"snapshot"``, ``"skill"``).
        entity_name: Entity name (case-insensitive, normalized to lowercase).
        key:         Fact key.

    Returns:
        A dict with ``version_count`` (total versions after archiving) and
        ``archived_version`` (the version number that was archived), or
        ``None`` if there was nothing to archive (first write — no previous row).
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    db = await get_supabase_client()

    # Read the current row (if it exists)
    current = await (
        db.schema("public")
        .table("shared_business_memory")
        .select("id, value, metadata, source, confidence, version, "
                "content_hash, created_at, updated_at")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .maybe_single()
        .execute()
    )

    row = current.data
    if not row:
        # First write — nothing to archive
        return None

    archived_version = int(row.get("version", 1))
    current_value = row["value"]
    current_hash = row.get("content_hash") or compute_content_hash(current_value)

    # ------------------------------------------------------------------
    # Dedup: skip archiving if the current value has the same content_hash
    # as the most recent archived version.
    # ------------------------------------------------------------------
    latest_version = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("content_hash, version")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )

    if latest_version.data and latest_version.data.get("content_hash") == current_hash:
        logger.debug(
            "[version_module] Skipping archive — current value hash matches "
            "latest archived version for %s:%s/%s (hash=%s)",
            entity_type, entity_name, key, current_hash[:12],
        )
        return {
            "version_count": None,  # unchanged
            "archived_version": archived_version,
            "skipped": True,
            "reason": "content_hash_unchanged",
        }

    # Build the version snapshot
    version_payload: dict[str, Any] = {
        "memory_id": row["id"],
        "client_id": client_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": current_value,
        "metadata": row.get("metadata", {}),
        "source": row.get("source", "manual"),
        "confidence": float(row.get("confidence", 1.0)),
        "version": archived_version,
        "content_hash": current_hash,
        "original_created_at": row.get("created_at"),
        "original_updated_at": row.get("updated_at"),
    }

    try:
        await (
            db.schema("public")
            .table(_VERSION_TABLE)
            .insert(version_payload)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "[version_module] Failed to archive version for "
            "%s:%s/%s client=%s: %s",
            entity_type, entity_name, key, client_id, exc,
        )
        raise RuntimeError(f"Failed to archive memory version: {exc}")

    # Count current versions (including the new one) and prune if needed
    count_result = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("id", count="exact")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .execute()
    )
    version_count = len(count_result.data) if count_result.data else 0

    # Auto-prune if over the limit
    if version_count > _MAX_VERSIONS_PER_KEY:
        await _prune_old_versions(
            client_id, entity_type, entity_name, key,
            max_versions=_MAX_VERSIONS_PER_KEY,
        )

    return {
        "version_count": version_count,
        "archived_version": archived_version,
    }


# ---------------------------------------------------------------------------
# Business logic — retrieval
# ---------------------------------------------------------------------------


async def _get_memory_versions(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    limit: int = 20,
) -> list[dict]:
    """Retrieve all historical versions for a shared-memory fact.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type.
        entity_name: Entity name.
        key:         Fact key.
        limit:       Maximum number of versions to return (default 20, max 100).

    Returns:
        List of version snapshots ordered by version descending (newest first).
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    db = await get_supabase_client()

    result = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .order("version", desc=True)
        .limit(limit)
        .execute()
    )

    rows = result.data if result.data else []

    return [
        _format_version_row(r)
        for r in rows
    ]


async def _get_memory_version(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    version: int,
) -> dict:
    """Retrieve a specific version of a shared-memory fact.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type.
        entity_name: Entity name.
        key:         Fact key.
        version:     The exact version number to retrieve (≥ 1).

    Returns:
        The version snapshot dict.

    Raises:
        ValueError: If the version does not exist.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    if version < 1:
        raise ValueError("version must be >= 1")

    db = await get_supabase_client()

    result = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .eq("version", version)
        .maybe_single()
        .execute()
    )

    row = result.data
    if not row:
        raise ValueError(
            f"Version {version} not found for "
            f"{entity_type}:{entity_name}/{key}"
        )

    return _format_version_row(row)


# ---------------------------------------------------------------------------
# Business logic — pruning
# ---------------------------------------------------------------------------


async def _prune_old_versions(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    max_versions: int = _MAX_VERSIONS_PER_KEY,
) -> int:
    """Delete oldest versions exceeding the limit.

    Keeps at most ``max_versions`` newest versions.  Returns the number of
    versions that were deleted.

    Args:
        client_id:    Client UUID.
        entity_type:  Entity type.
        entity_name:  Entity name.
        key:          Fact key.
        max_versions: Maximum versions to keep (default 50).

    Returns:
        Number of versions deleted.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if max_versions < 1:
        raise ValueError("max_versions must be >= 1")

    db = await get_supabase_client()

    # Find version IDs that exceed the limit (oldest first)
    result = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("id")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .order("version", desc=False)  # oldest first
        .execute()
    )

    rows = result.data if result.data else []
    total = len(rows)

    if total <= max_versions:
        return 0

    # IDs to delete: the oldest (total - max_versions) entries
    to_delete = [r["id"] for r in rows[:total - max_versions]]

    if not to_delete:
        return 0

    try:
        await (
            db.schema("public")
            .table(_VERSION_TABLE)
            .delete()
            .in_("id", to_delete)
            .eq("client_id", client_id)
            .execute()
        )
        deleted_count = len(to_delete)
    except Exception as exc:
        logger.warning(
            "[version_module] Failed to batch-prune %d versions: %s",
            len(to_delete), exc,
        )
        return 0

    if deleted_count > 0:
        logger.info(
            "[version_module] Pruned %d old versions for %s:%s/%s "
            "client=%s (now at %d)",
            deleted_count, entity_type, entity_name, key,
            client_id, total - deleted_count,
        )

    return deleted_count


# ---------------------------------------------------------------------------
# Business logic — explicit store version (checkpoint)
# ---------------------------------------------------------------------------


async def _store_memory_version(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    metadata: dict | None = None,
    reason: str | None = None,
) -> dict:
    """Explicitly archive the current version without changing the value.

    Useful for checkpointing before high-risk operations.  Deduplicates:
    if the current value's content_hash matches the most recent archived
    version, the call returns ``\"no_change\"`` instead of archiving a
    duplicate.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type.
        entity_name: Entity name.
        key:         Fact key.
        metadata:    Optional extra metadata for the archived version.
        reason:      Optional reason for the checkpoint (stored in
                     ``metadata.checkpoint_reason``).

    Returns:
        A dict with ``status``, ``version_archived``, and
        ``total_versions``.  ``status`` is ``\"archived\"`` when a new
        version was saved, or ``\"no_change\"`` when dedup skipped it.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    db = await get_supabase_client()

    # 1. Read the current row
    current = await (
        db.schema("public")
        .table("shared_business_memory")
        .select("id, value, metadata, source, confidence, version, "
                "content_hash, created_at, updated_at")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .maybe_single()
        .execute()
    )

    row = current.data
    if not row:
        raise ValueError(
            f"No current value found for {entity_type}:{entity_name}/{key}. "
            f"Cannot store version for a non-existent key."
        )

    current_value = row["value"]
    current_hash = row.get("content_hash") or compute_content_hash(current_value)
    current_version = int(row.get("version", 1))

    # 2. Dedup check: compare with most recent archived version
    latest_version = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("content_hash, version")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )

    if latest_version.data and latest_version.data.get("content_hash") == current_hash:
        return {
            "status": "no_change",
            "reason": "content_hash_unchanged — current value matches "
                      "latest archived version",
            "version_archived": None,
            "total_versions": None,
        }

    # 3. Build enriched metadata
    enriched_metadata: dict[str, Any] = dict(row.get("metadata", {}))
    if reason:
        enriched_metadata["checkpoint_reason"] = reason
    if metadata:
        enriched_metadata.update(metadata)

    # 4. Archive the current value as a new version snapshot
    version_payload: dict[str, Any] = {
        "memory_id": row["id"],
        "client_id": client_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": current_value,
        "metadata": enriched_metadata,
        "source": row.get("source", "manual"),
        "confidence": float(row.get("confidence", 1.0)),
        "version": current_version,
        "content_hash": current_hash,
        "original_created_at": row.get("created_at"),
        "original_updated_at": row.get("updated_at"),
    }

    try:
        await (
            db.schema("public")
            .table(_VERSION_TABLE)
            .insert(version_payload)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "[version_module] store_version failed for "
            "%s:%s/%s client=%s: %s",
            entity_type, entity_name, key, client_id, exc,
        )
        raise RuntimeError(f"Failed to store memory version: {exc}")

    # 5. Count versions and prune if needed
    count_result = await (
        db.schema("public")
        .table(_VERSION_TABLE)
        .select("id", count="exact")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .execute()
    )
    version_count = len(count_result.data) if count_result.data else 0

    if version_count > _MAX_VERSIONS_PER_KEY:
        await _prune_old_versions(
            client_id, entity_type, entity_name, key,
            max_versions=_MAX_VERSIONS_PER_KEY,
        )

    return {
        "status": "archived",
        "version_archived": current_version,
        "total_versions": version_count,
    }


# ---------------------------------------------------------------------------
# Business logic — diff
# ---------------------------------------------------------------------------


async def _get_memory_diff(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    version_a: int,
    version_b: int | None = None,
    mode: str = "json",
) -> dict:
    """Compare two versions of a shared-memory fact.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type.
        entity_name: Entity name.
        key:         Fact key.
        version_a:   Base version (older).
        version_b:   Target version.  If ``None``, compare against the
                     current (live) version.
        mode:        ``\"json\"`` for jsondiff structured output, or
                     ``\"text\"`` for unified diff via difflib.

    Returns:
        A dict with ``v1``, ``v2``, ``diff``, ``diff_stats``, ``mode``,
        and context fields.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    if version_a < 1:
        raise ValueError("version_a must be >= 1")

    if mode not in ("json", "text"):
        raise ValueError("mode must be 'json' or 'text'")

    db = await get_supabase_client()

    # ------------------------------------------------------------------
    # 1. Fetch version_a
    # ------------------------------------------------------------------
    va = await _get_memory_version(
        client_id, entity_type, entity_name, key, version_a,
    )

    # ------------------------------------------------------------------
    # 2. Determine version_b
    # ------------------------------------------------------------------
    if version_b is not None:
        if version_b < 1:
            raise ValueError("version_b must be >= 1")
        if version_b == version_a:
            return {
                "v1": {"version": version_a,
                       "content_hash": va.get("content_hash")},
                "v2": {"version": version_b,
                       "content_hash": va.get("content_hash")},
                "diff": None,
                "diff_stats": {"fields_added": 0, "fields_removed": 0,
                               "fields_modified": 0},
                "entity_type": entity_type,
                "entity_name": entity_name,
                "key": key,
                "mode": mode,
                "status": "no_diff — same version",
            }
        vb = await _get_memory_version(
            client_id, entity_type, entity_name, key, version_b,
        )
        vb_value = vb["value"]
        vb_hash = vb.get("content_hash")
        vb_version = version_b
        vb_archived_at = vb.get("archived_at")
    else:
        # Compare against the current (live) version
        current = await (
            db.schema("public")
            .table("shared_business_memory")
            .select("value, content_hash, version, updated_at")
            .eq("client_id", client_id)
            .eq("entity_type", entity_type)
            .eq("entity_name", entity_name)
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        if not current.data:
            raise ValueError(
                f"No current value found for "
                f"{entity_type}:{entity_name}/{key}"
            )
        vb_value = current.data["value"]
        vb_hash = current.data.get("content_hash") or compute_content_hash(
            vb_value
        )
        vb_version = int(current.data.get("version", 1))
        vb_archived_at = current.data.get("updated_at")

    va_value = va["value"]
    va_hash = va.get("content_hash")
    va_version = version_a
    va_archived_at = va.get("archived_at")

    # Early exit: hashes match → no diff
    if va_hash and vb_hash and va_hash == vb_hash:
        return {
            "v1": {"version": va_version, "content_hash": va_hash,
                   "archived_at": va_archived_at},
            "v2": {"version": vb_version, "content_hash": vb_hash,
                   "archived_at": vb_archived_at},
            "diff": None,
            "diff_stats": {"fields_added": 0, "fields_removed": 0,
                           "fields_modified": 0},
            "entity_type": entity_type,
            "entity_name": entity_name,
            "key": key,
            "mode": mode,
            "status": "no_diff — content_hash identical",
        }

    # ------------------------------------------------------------------
    # 3. Compute diff
    # ------------------------------------------------------------------
    if mode == "json" and _JSONDIFF_AVAILABLE and jsondiff_diff is not None:
        diff_result = jsondiff_diff(va_value, vb_value, syntax="symmetric")
        # Calculate diff stats
        diff_stats = {
            "fields_added": len(diff_result.get("insert", {})),
            "fields_removed": len(diff_result.get("delete", {})),
            "fields_modified": len(diff_result.get("change", {})),
        }
    else:
        diff_result = _text_diff(va_value, vb_value)
        diff_stats = {
            "fields_added": sum(1 for line in diff_result
                                if line.startswith("+")),
            "fields_removed": sum(1 for line in diff_result
                                 if line.startswith("-")),
            "fields_modified": 0,  # text diff doesn't track modifications
        }

    return {
        "v1": {"version": va_version, "content_hash": va_hash,
               "archived_at": va_archived_at},
        "v2": {"version": vb_version, "content_hash": vb_hash,
               "archived_at": vb_archived_at},
        "diff": diff_result,
        "diff_stats": diff_stats,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "mode": mode,
    }


# ---------------------------------------------------------------------------
# Business logic — get current version
# ---------------------------------------------------------------------------


async def _get_current_version(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
) -> dict:
    """Return the current version info for a shared-memory fact.

    Does NOT return the full value — only version metadata.

    Args:
        client_id:   Client UUID.
        entity_type: Entity type.
        entity_name: Entity name.
        key:         Fact key.

    Returns:
        A dict with ``version``, ``content_hash``, and ``updated_at``.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    db = await get_supabase_client()

    current = await (
        db.schema("public")
        .table("shared_business_memory")
        .select("version, content_hash, updated_at")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .maybe_single()
        .execute()
    )

    if not current.data:
        raise ValueError(
            f"No current value found for "
            f"{entity_type}:{entity_name}/{key}"
        )

    return {
        "version": int(current.data.get("version", 1)),
        "content_hash": current.data.get("content_hash"),
        "updated_at": current.data.get("updated_at"),
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _format_version_row(row: dict) -> dict:
    """Format a versions-table row into the standard API shape."""
    return {
        "id": row["id"],
        "memory_id": row.get("memory_id"),
        "client_id": row["client_id"],
        "entity_type": row["entity_type"],
        "entity_name": row["entity_name"],
        "key": row["key"],
        "value": row["value"],
        "metadata": row.get("metadata", {}),
        "source": row.get("source", "manual"),
        "confidence": float(row.get("confidence", 1.0)),
        "version": int(row.get("version", 1)),
        "content_hash": row.get("content_hash"),
        "archived_at": row["archived_at"],
        "original_created_at": row.get("original_created_at"),
        "original_updated_at": row.get("original_updated_at"),
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registers version-history tools."""
    registered_tools: list[str] = []

    # ----------------------------------------------------------------------
    # shared_memory_get_versions — list historical versions
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_get_versions",
        description=(
            "[Shared Memory] List all historical versions of a fact. "
            "Returns the full version history stored in "
            "shared_business_memory_versions, ordered newest-first. "
            "Use this to audit changes, compare versions, or recover "
            "previous values. "
            "Limit controls how many versions to return (default 20, max 100)."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_get_versions(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        limit: int = 20,
        client_id: str | None = None,
    ) -> dict:
        """List all historical versions for a shared-memory fact.

        Args:
            entity_type: Entity type (skill | client | contact | supplier |
                         user | snapshot | routine | agent_result | agent_metadata).
            entity_name: Entity name (case-insensitive, normalized to lowercase).
            key:         Fact key.
            limit:       Max versions to return (1–100, default 20).

        Returns:
            dict with total_versions, limit, and versions array.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[version_module] shared_memory_get_versions "
            "entity_type=%s entity_name=%s key=%s limit=%d client_id=%s",
            entity_type, entity_name, key, limit, client_id,
        )

        try:
            versions = await _get_memory_versions(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                limit=limit,
            )
            return {
                "client_id": client_id,
                "entity_type": entity_type,
                "entity_name": entity_name,
                "key": key,
                "total_versions": len(versions),
                "limit": limit,
                "versions": versions,
            }
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[version_module] shared_memory_get_versions failed: %s", exc
            )
            raise ToolError(
                f"Failed to get memory versions: {exc}"
            )

    logger.info("[Version Module] Tool 'shared_memory_get_versions' registered.")
    registered_tools.append("shared_memory_get_versions")

    # ----------------------------------------------------------------------
    # shared_memory_get_version — retrieve a specific version
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_get_version",
        description=(
            "[Shared Memory] Retrieve a specific historical version of a "
            "shared-memory fact by its version number. "
            "Returns the full snapshot (value, metadata, source, confidence) "
            "as it was at that point in time. "
            "Version numbers correspond to the 'version' field in "
            "shared_business_memory."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_get_version(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        version: int,
        client_id: str | None = None,
    ) -> dict:
        """Retrieve a specific historical version.

        Args:
            entity_type: Entity type.
            entity_name: Entity name (case-insensitive).
            key:         Fact key.
            version:     Exact version number (≥ 1).

        Returns:
            The version snapshot dict.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[version_module] shared_memory_get_version "
            "entity_type=%s entity_name=%s key=%s version=%d client_id=%s",
            entity_type, entity_name, key, version, client_id,
        )

        try:
            return await _get_memory_version(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                version=version,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[version_module] shared_memory_get_version failed: %s", exc
            )
            raise ToolError(
                f"Failed to get memory version: {exc}"
            )

    logger.info("[Version Module] Tool 'shared_memory_get_version' registered.")
    registered_tools.append("shared_memory_get_version")

    # ----------------------------------------------------------------------
    # shared_memory_store_version — explicit checkpoint
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_store_version",
        description=(
            "[Shared Memory] Create an explicit version checkpoint of a "
            "shared-memory fact WITHOUT changing its value. "
            "Useful before high-risk operations to mark a restore point. "
            "Automatically deduplicates — if the current value has not "
            "changed since the last archived version, returns 'no_change' "
            "instead of creating a duplicate. "
            "Use 'reason' to annotate the checkpoint (e.g. 'pre_migration', "
            "'approved_by_admin')."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_store_version(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        metadata: dict | None = None,
        reason: str | None = None,
        client_id: str | None = None,
    ) -> dict:
        """Create an explicit version checkpoint without changing the value.

        Args:
            entity_type: Entity type (skill | client | contact | supplier |
                         user | snapshot | routine | agent_result | agent_metadata).
            entity_name: Entity name (case-insensitive, normalized to lowercase).
            key:         Fact key.
            metadata:    Optional extra metadata for the archived version.
            reason:      Optional reason for the checkpoint (e.g. 'pre_migration').

        Returns:
            dict with status ('archived' | 'no_change'), version_archived,
            and total_versions.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[version_module] shared_memory_store_version "
            "entity_type=%s entity_name=%s key=%s reason=%s client_id=%s",
            entity_type, entity_name, key, reason, client_id,
        )

        try:
            return await _store_memory_version(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                metadata=metadata,
                reason=reason,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[version_module] shared_memory_store_version failed: %s", exc
            )
            raise ToolError(
                f"Failed to store memory version: {exc}"
            )

    logger.info(
        "[Version Module] Tool 'shared_memory_store_version' registered."
    )
    registered_tools.append("shared_memory_store_version")

    # ----------------------------------------------------------------------
    # shared_memory_get_diff — compare two versions
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_get_diff",
        description=(
            "[Shared Memory] Compare two versions of a shared-memory fact "
            "and return a structured diff. "
            "Use mode='json' for machine-readable jsondiff output "
            "(insert/delete/change), or mode='text' for a human-readable "
            "unified diff. If version_b is omitted, the diff is computed "
            "against the CURRENT (live) value. "
            "Returns 'no_diff' when the two versions are identical."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_get_diff(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        version_a: int,
        version_b: int | None = None,
        mode: str = "json",
        client_id: str | None = None,
    ) -> dict:
        """Compare two versions and return a structured diff.

        Args:
            entity_type: Entity type.
            entity_name: Entity name (case-insensitive).
            key:         Fact key.
            version_a:   Base version number (≥ 1).
            version_b:   Target version number. If omitted, compares against
                         the current (live) version.
            mode:        'json' for jsondiff (insert/delete/change) or 'text'
                         for unified diff (default: 'json').

        Returns:
            dict with v1, v2, diff, diff_stats, mode, and context fields.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[version_module] shared_memory_get_diff "
            "entity_type=%s entity_name=%s key=%s version_a=%d version_b=%s "
            "mode=%s client_id=%s",
            entity_type, entity_name, key, version_a,
            version_b, mode, client_id,
        )

        try:
            return await _get_memory_diff(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                version_a=version_a,
                version_b=version_b,
                mode=mode,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[version_module] shared_memory_get_diff failed: %s", exc
            )
            raise ToolError(
                f"Failed to compute memory diff: {exc}"
            )

    logger.info(
        "[Version Module] Tool 'shared_memory_get_diff' registered."
    )
    registered_tools.append("shared_memory_get_diff")

    # ----------------------------------------------------------------------
    # shared_memory_get_current_version — current version metadata
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_get_current_version",
        description=(
            "[Shared Memory] Return the current version metadata for a "
            "shared-memory fact. "
            "Returns only the version number, content_hash, and "
            "updated_at timestamp — does NOT return the full value. "
            "Use this to check whether a fact has changed since you last "
            "read it, or to get version info before calling get_diff."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_get_current_version(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        client_id: str | None = None,
    ) -> dict:
        """Return current version metadata for a shared-memory fact.

        Args:
            entity_type: Entity type.
            entity_name: Entity name (case-insensitive).
            key:         Fact key.

        Returns:
            dict with version, content_hash, and updated_at.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        logger.info(
            "[version_module] shared_memory_get_current_version "
            "entity_type=%s entity_name=%s key=%s client_id=%s",
            entity_type, entity_name, key, client_id,
        )

        try:
            return await _get_current_version(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[version_module] shared_memory_get_current_version "
                "failed: %s", exc
            )
            raise ToolError(
                f"Failed to get current version: {exc}"
            )

    logger.info(
        "[Version Module] Tool 'shared_memory_get_current_version' registered."
    )
    registered_tools.append("shared_memory_get_current_version")

    return registered_tools
