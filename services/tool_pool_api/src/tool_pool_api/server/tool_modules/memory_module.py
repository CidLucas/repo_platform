"""
"""memory_module.py -- Shared Business Memory Tools (T0.4-T0.6)

Registers L1 tools for interacting with the `shared_business_memory` and
`shared_memory_links` tables in Supabase.  Agents communicate via shared
memory (not direct conversation), reading and writing knowledge about
entities (clients, contacts, suppliers, users, skill-derived facts,
and snapshots).

Tools registered:
  - shared_memory_list    -> list entities with memory entries
  - shared_memory_read    -> read a single fact by composite key
  - shared_memory_upsert  -> insert or update a fact (versioned)
  - shared_memory_link    -> create semantic link between entities
  - shared_memory_unlink  -> remove a link by id
  - shared_memory_get_links -> query links by entity and/or type

Design doc: docs/llm_wiki/SHARED_MEMORY_DESIGN.md (Fase 0)
"""

import json
import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client

from . import register_module

logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"skill", "client", "contact", "supplier", "user", "snapshot"}
)

_TABLE = "shared_business_memory"
_LINKS_TABLE = "shared_memory_links"


# ---------------------------------------------------------------------------
# Link validation helpers
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
# Business logic
# ---------------------------------------------------------------------------


async def _shared_memory_list_logic(
    client_id: str,
    entity_type: str | None = None,
) -> dict:
    """
    List all entities that have memory entries for a given client.

    Returns total_entities, by_type breakdown, and entities array
    sorted by (entity_type, entity_name).
    """
    if entity_type is not None:
        _validate_entity_type(entity_type)

    db = await get_supabase_client()

    query = (
        db.schema("public")
        .table(_TABLE)
        .select("entity_type, entity_name, count(*), max(updated_at) as last_updated")
        .eq("client_id", client_id)
    )
    if entity_type:
        query = query.eq("entity_type", entity_type)

    result = await query.group_by("entity_type, entity_name").execute()

    rows = result.data if result.data else []

    entities: list[dict] = []
    type_counts: dict[str, int] = {}

    for r in rows:
        et = r["entity_type"]
        en = r["entity_name"]
        cnt = r.get("count", 0)
        lu = r.get("last_updated")
        entities.append(
            {
                "entity_type": et,
                "entity_name": en,
                "key_count": cnt,
                "last_updated": lu,
            }
        )
        type_counts[et] = type_counts.get(et, 0) + 1

    entities.sort(key=lambda e: (e["entity_type"], e["entity_name"]))

    return {
        "total_entities": len(entities),
        "client_id": client_id,
        "entity_type_filter": entity_type,
        "by_type": type_counts,
        "entities": entities,
    }


# ---------------------------------------------------------------------------
# Read business logic
# ---------------------------------------------------------------------------


async def _shared_memory_read_logic(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
) -> dict:
    """
    Read a single shared-memory fact by its composite key
    (client_id, entity_type, entity_name, key).

    Returns the full record or raises ValueError if not found.
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")

    db = await get_supabase_client()

    result = await (
        db.schema("public")
        .table(_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .eq("entity_type", entity_type)
        .eq("entity_name", entity_name)
        .eq("key", key)
        .maybe_single()
        .execute()
    )

    row = result.data
    if not row:
        raise ValueError(
            f"Memory entry not found: {entity_type}:{entity_name}/{key}"
        )

    return {
        "id": row["id"],
        "client_id": row["client_id"],
        "entity_type": row["entity_type"],
        "entity_name": row["entity_name"],
        "key": row["key"],
        "value": row["value"],
        "source": row["source"],
        "confidence": float(row["confidence"]) if row.get("confidence") else 1.0,
        "version": row.get("version", 1),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Upsert business logic
# ---------------------------------------------------------------------------


async def _shared_memory_upsert_logic(
    client_id: str,
    entity_type: str,
    entity_name: str,
    key: str,
    body: dict,
    frontmatter: dict | None = None,
    source: str = "manual",
    confidence: float = 1.0,
) -> dict:
    """
    Insert or update a shared-memory fact.

    Uses INSERT ... ON CONFLICT (client_id, entity_type, entity_name, key)
    DO UPDATE with version = version + 1.

    body maps to the ``value`` column (the actual fact content).
    frontmatter maps to the ``metadata`` column (provenance/context).
    """
    _validate_entity_type(entity_type)
    entity_name = _normalize_entity_name(entity_name)
    key = key.strip().lower()

    if not entity_name or not key:
        raise ValueError("entity_name and key are required")
    if not isinstance(body, dict):
        raise ValueError("body must be a dict")

    db = await get_supabase_client()

    payload = {
        "client_id": client_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": body,
        "metadata": frontmatter if frontmatter is not None else {},
        "source": source if source in (
            "manual", "memory_agent", "specialist", "migration", "system"
        ) else "manual",
        "confidence": confidence,
    }

    try:
        result = await (
            db.schema("public")
            .table(_TABLE)
            .upsert(
                payload,
                on_conflict="client_id,entity_type,entity_name,key",
                default_to_null=False,
            )
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to upsert shared-memory entry: {exc}")

    row = result.data[0] if result.data else None
    if not row:
        raise RuntimeError("Failed to upsert memory entry --  no data returned")

    return {
        "id": row["id"],
        "client_id": row["client_id"],
        "entity_type": row["entity_type"],
        "entity_name": row["entity_name"],
        "key": row["key"],
        "value": row["value"],
        "metadata": row.get("metadata", {}),
        "source": row["source"],
        "confidence": float(row["confidence"]) if row.get("confidence") else 1.0,
        "version": row.get("version", 1),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Link business logic
# ---------------------------------------------------------------------------


async def _shared_memory_link_logic(
    client_id: str,
    source_entity_type: str,
    source_entity_name: str,
    target_entity_type: str,
    target_entity_name: str,
    link_type: str,
    source: str = "manual",
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> dict:
    """
    Create a semantic link between two entities.

    Returns the created link record.
    """
    _validate_entity_type(source_entity_type, "source_entity_type")
    _validate_entity_type(target_entity_type, "target_entity_type")

    source_entity_name = _normalize_entity_name(source_entity_name)
    target_entity_name = _normalize_entity_name(target_entity_name)
    link_type = link_type.strip().lower()

    if not source_entity_name or not target_entity_name:
        raise ValueError("source_entity_name and target_entity_name are required")
    if len(link_type) < 2 or len(link_type) > 128:
        raise ValueError(
            "link_type must be between 2 and 128 characters"
        )

    db = await get_supabase_client()

    payload = {
        "client_id": client_id,
        "source_entity_type": source_entity_type,
        "source_entity_name": source_entity_name,
        "target_entity_type": target_entity_type,
        "target_entity_name": target_entity_name,
        "link_type": link_type,
        "source": source if source in (
            "manual", "memory_agent", "specialist", "migration", "system"
        ) else "manual",
        "confidence": confidence,
        "metadata": metadata or {},
    }

    try:
        result = await (
            db.schema("public")
            .table(_LINKS_TABLE)
            .insert(payload)
            .execute()
        )
    except Exception as exc:
        err_str = str(exc).lower()
        if "duplicate key" in err_str or "uq_shared_memory_link" in err_str:
            raise ValueError(
                f"Link already exists: "
                f"{source_entity_type}:{source_entity_name} "
                f"─[{link_type}]-> "
                f"{target_entity_type}:{target_entity_name}"
            )
        raise

    row = result.data[0] if result.data else None
    if not row:
        raise RuntimeError("Failed to create link --  no data returned")

    return {
        "id": row["id"],
        "client_id": row["client_id"],
        "source_entity_type": row["source_entity_type"],
        "source_entity_name": row["source_entity_name"],
        "link_type": row["link_type"],
        "target_entity_type": row["target_entity_type"],
        "target_entity_name": row["target_entity_name"],
        "source": row["source"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


async def _shared_memory_unlink_logic(
    client_id: str,
    link_id: str,
) -> dict:
    """
    Remove a link by its id.

    Returns the deleted link id.
    """
    db = await get_supabase_client()

    result = await (
        db.schema("public")
        .table(_LINKS_TABLE)
        .delete()
        .eq("id", link_id)
        .eq("client_id", client_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise ValueError(
            f"Link '{link_id}' not found or does not belong to this client"
        )

    return {
        "deleted": True,
        "id": link_id,
    }


async def _shared_memory_get_links_logic(
    client_id: str,
    entity_type: str | None = None,
    entity_name: str | None = None,
    link_type: str | None = None,
    direction: str = "both",
) -> dict:
    """
    Query links by source entity, target entity, and/or link_type.

    Args:
        client_id: Client UUID.
        entity_type: Optional filter --  only links involving this entity type.
        entity_name: Optional filter --  only links involving this entity name.
        link_type: Optional filter --  only links of this type.
        direction:
            "outgoing" --  links where entity is the source
            "incoming" --  links where entity is the target
            "both" --  both directions (default)

    Returns outgoing, incoming, and summary counts.
    """
    db = await get_supabase_client()

    if entity_type is not None:
        _validate_entity_type(entity_type)
    if link_type is not None:
        link_type = link_type.strip().lower()

    outgoing: list[dict] = []
    incoming: list[dict] = []

    async def _fetch_outgoing() -> list[dict]:
        q = (
            db.schema("public")
            .table(_LINKS_TABLE)
            .select("*")
            .eq("client_id", client_id)
        )
        if entity_type:
            q = q.eq("source_entity_type", entity_type)
        if entity_name:
            q = q.eq("source_entity_name", _normalize_entity_name(entity_name))
        if link_type:
            q = q.eq("link_type", link_type)
        result = await q.order("created_at", desc=True).execute()
        return result.data or []

    async def _fetch_incoming() -> list[dict]:
        q = (
            db.schema("public")
            .table(_LINKS_TABLE)
            .select("*")
            .eq("client_id", client_id)
        )
        if entity_type:
            q = q.eq("target_entity_type", entity_type)
        if entity_name:
            q = q.eq("target_entity_name", _normalize_entity_name(entity_name))
        if link_type:
            q = q.eq("link_type", link_type)
        result = await q.order("created_at", desc=True).execute()
        return result.data or []

    if direction in ("outgoing", "both"):
        outgoing = await _fetch_outgoing()
    if direction in ("incoming", "both"):
        incoming = await _fetch_incoming()

    return {
        "client_id": client_id,
        "direction": direction,
        "entity_type_filter": entity_type,
        "entity_name_filter": entity_name,
        "link_type_filter": link_type,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "total_links": len(outgoing) + len(incoming),
        "outgoing": outgoing,
        "incoming": incoming,
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registers shared memory tools."""
    registered_tools: list[str] = []

    @mcp.tool(
        name="shared_memory_list",
        description=(
            "[Shared Memory] List all entities that have business-memory "
            "entries for the current client. Optionally filter by entity_type "
            "(skill | client | contact | supplier | user). "
            "Returns a summary breakdown and the full entity list with "
            "key-counts and last-updated timestamps. "
            "Use this to discover what entities exist before calling "
            "shared_memory_read for a specific one."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_list(
        ctx: Context,
        entity_type: str | None = None,
        client_id: str | None = None,
    ) -> dict:
        """
        List all entities with shared-memory entries for this client.

        Args:
            entity_type: Optional filter --  "skill", "client",
                         "contact", "supplier", or "user".
                         When omitted all entity types are returned.

        Returns:
            dict with total_entities, by_type breakdown, and entities
            array sorted by (entity_type, entity_name).
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        logger.info(
            "[memory_module] shared_memory_list client_id=%s entity_type=%s",
            client_id,
            entity_type,
        )

        try:
            return await _shared_memory_list_logic(
                client_id=client_id,
                entity_type=entity_type,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_list failed: %s", exc
            )
            raise ToolError(
                f"Failed to list shared-memory entities: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_list' registered.")
    registered_tools.append("shared_memory_list")

    # ----------------------------------------------------------------------
    # shared_memory_read --  read a single fact by composite key
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_read",
        description=(
            "[Shared Memory] Read a single fact from shared memory by its "
            "composite key (client_id, entity_type, entity_name, key). "
            "Valid entity types: skill | client | contact | supplier | user | snapshot. "
            "Returns the full record including value, metadata, version, and timestamps."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_read(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        client_id: str | None = None,
    ) -> dict:
        """
        Read a single shared-memory fact by its composite key.

        Args:
            entity_type: Entity type (skill | client | contact | supplier | user | snapshot).
            entity_name: Entity name (case-insensitive, normalized to lowercase).
            key: Fact key (e.g. "tom_amigavel", "preferencia_horario").

        Returns:
            dict with the full record: id, client_id, entity_type, entity_name,
            key, value, source, confidence, version, created_at, updated_at.
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        logger.info(
            "[memory_module] shared_memory_read "
            "entity_type=%s entity_name=%s key=%s client_id=%s",
            entity_type,
            entity_name,
            key,
            client_id,
        )

        try:
            return await _shared_memory_read_logic(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_read failed: %s", exc
            )
            raise ToolError(
                f"Failed to read shared-memory entry: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_read' registered.")
    registered_tools.append("shared_memory_read")

    # ----------------------------------------------------------------------
    # shared_memory_upsert --  insert or update a fact
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_upsert",
        description=(
            "[Shared Memory] Insert or update a fact in shared memory. "
            "Uses upsert semantics: creates a new row if the composite key "
            "(client_id, entity_type, entity_name, key) doesn't exist, "
            "or updates the existing row (incrementing version). "
            "body maps to the 'value' column (the fact content); "
            "frontmatter maps to the 'metadata' column (provenance). "
            "Valid entity types: skill | client | contact | supplier | user | snapshot."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_upsert(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        body: dict,
        frontmatter: dict | None = None,
        source: str = "manual",
        confidence: float = 1.0,
        client_id: str | None = None,
    ) -> dict:
        """
        Insert or update a shared-memory fact.

        Args:
            entity_type: Entity type (skill | client | contact | supplier | user | snapshot).
            entity_name: Entity name (case-insensitive, normalized to lowercase).
            key: Fact key (e.g. "tom_amigavel", "preferencia_horario").
            body: The fact value (dict --  maps to 'value' column).
            frontmatter: Optional metadata dict (maps to 'metadata' column).
            source: Provenance --  "manual" | "memory_agent" | "specialist" | "migration" | "system".
            confidence: Confidence score (0.0--1.0, default 1.0).

        Returns:
            dict with the full upserted record including version.
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        logger.info(
            "[memory_module] shared_memory_upsert "
            "entity_type=%s entity_name=%s key=%s client_id=%s",
            entity_type,
            entity_name,
            key,
            client_id,
        )

        try:
            return await _shared_memory_upsert_logic(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                body=body,
                frontmatter=frontmatter,
                source=source,
                confidence=confidence,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_upsert failed: %s", exc
            )
            raise ToolError(
                f"Failed to upsert shared-memory entry: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_upsert' registered.")
    registered_tools.append("shared_memory_upsert")

    # ----------------------------------------------------------------------
    # shared_memory_link --  create a semantic link between entities
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_link",
        description=(
            "[Shared Memory] Create a semantic link between two entities. "
            "Links represent relationships like 'contact Joao works_for supplier Distribuidora X'. "
            "link_type is free-form: works_for, applies_to, prefers, reports_to, depends_on, etc. "
            "Valid entity types: skill | client | contact | supplier | user."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_link(
        ctx: Context,
        source_entity_type: str,
        source_entity_name: str,
        target_entity_type: str,
        target_entity_name: str,
        link_type: str,
        source: str = "manual",
        confidence: float = 1.0,
        metadata: str | None = None,
        client_id: str | None = None,
    ) -> dict:
        """
        Create a semantic link between two entities.

        Args:
            source_entity_type: Entity type of the source (skill | client | contact | supplier | user).
            source_entity_name: Name of the source entity (case-insensitive, normalized to lowercase).
            target_entity_type: Entity type of the target (skill | client | contact | supplier | user).
            target_entity_name: Name of the target entity (case-insensitive).
            link_type: Relationship label --  e.g. "works_for", "applies_to", "prefers".
            source: Origin of the link --  "manual" | "memory_agent" | "specialist" | "migration" | "system".
            confidence: Confidence score (0.0--1.0, default 1.0).
            metadata: Optional JSON string with extra link metadata.

        Returns:
            dict with id, source, target, link_type, and provenance info.
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        parsed_metadata: dict | None = None
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
                if not isinstance(parsed_metadata, dict):
                    raise ValueError("metadata must be a JSON object")
            except (json.JSONDecodeError, ValueError) as exc:
                raise ToolError(f"Invalid metadata JSON: {exc}")

        logger.info(
            "[memory_module] shared_memory_link "
            "source=%s:%s link_type=%s target=%s:%s client_id=%s",
            source_entity_type, source_entity_name,
            link_type,
            target_entity_type, target_entity_name,
            client_id,
        )

        try:
            return await _shared_memory_link_logic(
                client_id=client_id,
                source_entity_type=source_entity_type,
                source_entity_name=source_entity_name,
                target_entity_type=target_entity_type,
                target_entity_name=target_entity_name,
                link_type=link_type,
                source=source,
                confidence=confidence,
                metadata=parsed_metadata,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_link failed: %s", exc
            )
            raise ToolError(
                f"Failed to create shared-memory link: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_link' registered.")
    registered_tools.append("shared_memory_link")

    # ----------------------------------------------------------------------
    # shared_memory_unlink --  remove a semantic link by id
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_unlink",
        description=(
            "[Shared Memory] Remove a semantic link between entities by its id. "
            "Use shared_memory_get_links to find the link id first."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_unlink(
        ctx: Context,
        link_id: str,
        client_id: str | None = None,
    ) -> dict:
        """
        Remove a semantic link by its id.

        Args:
            link_id: UUID of the link to remove (from shared_memory_get_links).

        Returns:
            dict with deleted=true and the id.
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        logger.info(
            "[memory_module] shared_memory_unlink link_id=%s client_id=%s",
            link_id,
            client_id,
        )

        try:
            return await _shared_memory_unlink_logic(
                client_id=client_id,
                link_id=link_id,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_unlink failed: %s", exc
            )
            raise ToolError(
                f"Failed to remove shared-memory link: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_unlink' registered.")
    registered_tools.append("shared_memory_unlink")

    # ----------------------------------------------------------------------
    # shared_memory_get_links --  query links by entity and/or type
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_get_links",
        description=(
            "[Shared Memory] Query semantic links by entity and/or link_type. "
            "Returns outgoing links (where entity is the source), incoming links "
            "(where entity is the target), or both. "
            "Filter by entity_type, entity_name, and/or link_type."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_get_links(
        ctx: Context,
        entity_type: str | None = None,
        entity_name: str | None = None,
        link_type: str | None = None,
        direction: str = "both",
        client_id: str | None = None,
    ) -> dict:
        """
        Query semantic links between entities.

        Args:
            entity_type: Optional --  filter links involving this entity type.
            entity_name: Optional --  filter links involving this entity name.
            link_type: Optional --  filter links of this type (e.g. "works_for").
            direction: "outgoing" | "incoming" | "both" (default).

        Returns:
            dict with outgoing, incoming arrays, and summary counts.
        """
        if not client_id:
            raise ToolError(
                "client_id is required --  authentication context missing"
            )

        if direction not in ("outgoing", "incoming", "both"):
            raise ToolError(
                "direction must be 'outgoing', 'incoming', or 'both'"
            )

        logger.info(
            "[memory_module] shared_memory_get_links "
            "entity_type=%s entity_name=%s link_type=%s direction=%s client_id=%s",
            entity_type,
            entity_name,
            link_type,
            direction,
            client_id,
        )

        try:
            return await _shared_memory_get_links_logic(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                link_type=link_type,
                direction=direction,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_get_links failed: %s", exc
            )
            raise ToolError(
                f"Failed to get shared-memory links: {exc}"
            )

    logger.info(
        "[Memory Module] Tool 'shared_memory_get_links' registered."
    )
    registered_tools.append("shared_memory_get_links")

    return registered_tools
