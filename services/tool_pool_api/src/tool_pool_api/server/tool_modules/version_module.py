"""version_module.py — Shared Memory Version Storage & Retrieval

Registers L1 tools for archiving and querying historical versions of
shared_business_memory entries.  Every time a fact is overwritten via
upsert, the previous version is saved to ``shared_business_memory_versions``.
Agents can then retrieve the full version history or a specific snapshot.

Tools registered:
  - shared_memory_get_versions  → list all historical versions for a fact
  - shared_memory_get_version   → retrieve a specific version by number

Design doc: docs/llm_wiki/SHARED_MEMORY_DESIGN.md (Fase 0 — versioning schema)
"""

from __future__ import annotations

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
) -> int | None:
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
        The number of versions that now exist for this key (including the
        just-archived one), or ``None`` if there was nothing to archive
        (first write — no previous row).
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
                "created_at, updated_at")
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

    # Build the version snapshot
    version_payload: dict[str, Any] = {
        "memory_id": row["id"],
        "client_id": client_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": row["value"],
        "metadata": row.get("metadata", {}),
        "source": row.get("source", "manual"),
        "confidence": float(row.get("confidence", 1.0)),
        "version": int(row.get("version", 1)),
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

    return version_count


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

    deleted_count = 0
    for vid in to_delete:
        try:
            await (
                db.schema("public")
                .table(_VERSION_TABLE)
                .delete()
                .eq("id", vid)
                .eq("client_id", client_id)
                .execute()
            )
            deleted_count += 1
        except Exception as exc:
            logger.warning(
                "[version_module] Failed to prune version %s: %s", vid, exc
            )

    if deleted_count > 0:
        logger.info(
            "[version_module] Pruned %d old versions for %s:%s/%s "
            "client=%s (now at %d)",
            deleted_count, entity_type, entity_name, key,
            client_id, total - deleted_count,
        )

    return deleted_count


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

    return registered_tools
