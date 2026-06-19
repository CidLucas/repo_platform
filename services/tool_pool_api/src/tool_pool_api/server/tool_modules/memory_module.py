"""memory_module.py -- Shared Business Memory Tools (T0.4-T0.6)

Registers L1 tools for interacting with the ``shared_business_memory`` and
``shared_memory_links`` tables in Supabase.  Agents communicate via shared
memory (not direct conversation), reading and writing knowledge about
entities (clients, contacts, suppliers, users, skill-derived facts,
and snapshots).

Tools registered:
  - shared_memory_list    -> list entities with memory entries
  - shared_memory_read    -> read a single fact by composite key
  - shared_memory_upsert  -> insert or update a fact (versioned)
  - shared_memory_write   -> write a new fact (strict INSERT; supersede=True to upsert)
  - shared_memory_search  -> semantic vector search via Cohere embeddings (T3.1c)
  - shared_memory_flush   -> soft-delete entries (marks flushed_at in metadata; T5.4)
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

from tool_pool_api.server.dependencies import get_context_service
from blu_context_service.context_schemas import _SNAPSHOT_DIMENSION_FIELDS

from . import register_module

logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"skill", "client", "contact", "supplier", "user", "snapshot", "routine",
     "agent_result", "agent_metadata"}
)

_TABLE = "shared_business_memory"
_LINKS_TABLE = "shared_memory_links"

# ---------------------------------------------------------------------------
# Snapshot constants (T2.2a + T2.2b)
# ---------------------------------------------------------------------------

_SNAPSHOT_BASE_FIELDS: frozenset[str] = frozenset({
    "snapshot_id", "dimensao", "periodo", "gerado_em",
    "vigencia_inicio", "vigencia_fim", "indicadores", "alertas",
    "resumo_executivo",
})

_SNAPSHOT_FRONTMATTER_REQUIRED: frozenset[str] = frozenset({
    "tipo", "dimensao", "periodo", "gerado_em", "gerado_por",
    "versao", "template_version", "fontes",
})

_VALID_DIMENSIONS: frozenset[str] = frozenset(
    {"financeiro", "clientes", "agenda", "compras"}
)

_VALID_PERIODS: frozenset[str] = frozenset(
    {"diario", "semanal", "mensal"}
)


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


def _is_flushed(metadata: dict | None) -> bool:
    """Check whether a shared-memory entry has been flushed.

    Flushed entries have ``flushed_at`` set in their metadata JSONB column.
    This is a soft-delete marker — the row still exists but should be treated
    as cleared/unavailable.

    Args:
        metadata: The metadata dict from the row (may be None, treated as not flushed).

    Returns:
        True if the entry is marked as flushed.
    """
    if not isinstance(metadata, dict):
        return False
    return "flushed_at" in metadata


def _check_not_flushed(metadata: dict | None, entity_ref: str) -> None:
    """Raise ValueError if the entry is flushed.

    Used before returning read results to ensure flushed entries are not
    surfaced to agents.

    Args:
        metadata: The metadata dict from the row.
        entity_ref: Human-readable entity reference for the error message.

    Raises:
        ValueError: If the entry is flushed.
    """
    if _is_flushed(metadata):
        raise ValueError(
            f"Memory entry has been flushed (soft-deleted): {entity_ref}"
        )


# ---------------------------------------------------------------------------
# Snapshot validation (T2.2b + T2.2f)
# ---------------------------------------------------------------------------


def _validate_snapshot_frontmatter(
    entity_name: str,
    frontmatter: dict,
) -> None:
    """Validate that a snapshot has the required frontmatter fields.

    Args:
        entity_name: e.g. "financeiro:semanal" -- used for cross-validation.
        frontmatter: The frontmatter dict to validate.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(frontmatter, dict):
        raise ValueError(
            "frontmatter is required for entity_type='snapshot' and must be a dict"
        )

    # Validate required fields
    missing = _SNAPSHOT_FRONTMATTER_REQUIRED - set(frontmatter.keys())
    if missing:
        raise ValueError(
            f"Snapshot frontmatter missing required fields: {sorted(missing)}"
        )

    # Validate 'tipo' field
    if frontmatter.get("tipo") != "snapshot":
        raise ValueError(
            "frontmatter.tipo must be 'snapshot'"
        )

    # Validate dimension
    dimensao = frontmatter.get("dimensao")
    if dimensao not in _VALID_DIMENSIONS:
        raise ValueError(
            f"frontmatter.dimensao '{dimensao}' is invalid. "
            f"Must be one of: {sorted(_VALID_DIMENSIONS)}"
        )

    # Cross-validate with entity_name: dimension must match
    parts = entity_name.split(":")
    entity_dim = parts[0] if parts else ""
    if entity_dim and entity_dim != dimensao:
        raise ValueError(
            f"entity_name dimension '{entity_dim}' does not match "
            f"frontmatter.dimensao '{dimensao}'"
        )

    # Validate period
    periodo = frontmatter.get("periodo")
    if periodo not in _VALID_PERIODS:
        raise ValueError(
            f"frontmatter.periodo '{periodo}' is invalid. "
            f"Must be one of: {sorted(_VALID_PERIODS)}"
        )

    # Cross-validate period with entity_name
    if len(parts) > 1 and parts[1] and parts[1] != periodo:
        raise ValueError(
            f"entity_name period '{parts[1]}' does not match "
            f"frontmatter.periodo '{periodo}'"
        )

    # Validate version is positive int
    versao = frontmatter.get("versao")
    if not isinstance(versao, int) or versao < 1:
        raise ValueError(
            "frontmatter.versao must be a positive integer"
        )

    # Validate template_version is positive int
    template_version = frontmatter.get("template_version")
    if not isinstance(template_version, int) or template_version < 1:
        raise ValueError(
            "frontmatter.template_version must be a positive integer"
        )

    # Validate fontes is a list of strings
    fontes = frontmatter.get("fontes")
    if not isinstance(fontes, list) or not all(isinstance(f, str) for f in fontes):
        raise ValueError("frontmatter.fontes must be a list of strings")


def _validate_snapshot_body(
    entity_name: str,
    body: dict,
) -> None:
    """Validate a snapshot body against its dimension schema.

    Args:
        entity_name: e.g. "financeiro:semanal" -- dimension extracted from here.
        body: The body dict (value column content).

    Raises:
        ValueError: If validation fails.
    """
    # Extract dimension from entity_name
    parts = entity_name.split(":")
    dimensao = parts[0] if parts else ""

    if not dimensao:
        raise ValueError(
            "Cannot determine snapshot dimension from entity_name"
        )

    if dimensao not in _VALID_DIMENSIONS:
        raise ValueError(
            f"Invalid snapshot dimension '{dimensao}'. "
            f"Must be one of: {sorted(_VALID_DIMENSIONS)}"
        )

    # Validate base fields are present
    missing_base = _SNAPSHOT_BASE_FIELDS - set(body.keys())
    if missing_base:
        raise ValueError(
            f"Snapshot body missing required base fields: {sorted(missing_base)}"
        )

    # Validate 'dimensao' inside body matches entity_name
    body_dimensao = body.get("dimensao")
    if body_dimensao != dimensao:
        raise ValueError(
            f"body.dimensao '{body_dimensao}' does not match "
            f"entity_name dimension '{dimensao}'"
        )

    # Validate 'indicadores' is a list
    indicadores = body.get("indicadores")
    if not isinstance(indicadores, list):
        raise ValueError("body.indicadores must be a list")

    # Validate indicators against dimension spec
    dim_spec = _SNAPSHOT_DIMENSION_FIELDS.get(dimensao)
    if dim_spec is None:
        raise ValueError(
            f"Unknown snapshot dimension '{dimensao}'"
        )

    # Build a lookup of indicator names present in body
    body_indicator_names: set[str] = set()
    for ind in indicadores:
        if not isinstance(ind, dict):
            raise ValueError(
                f"Each indicator in body.indicadores must be a dict"
            )
        nome = ind.get("nome")
        if not nome or not isinstance(nome, str):
            raise ValueError(
                f"Each indicator must have a 'nome' (string)"
            )
        body_indicator_names.add(nome)

        # Validate required fields within each indicator
        if "valor" not in ind:
            raise ValueError(
                f"Indicator '{nome}' missing required field 'valor'"
            )
        if "unidade" not in ind:
            raise ValueError(
                f"Indicator '{nome}' missing required field 'unidade'"
            )
        tendencia = ind.get("tendencia")
        if tendencia is not None and tendencia not in ("alta", "baixa", "estavel"):
            raise ValueError(
                f"Indicator '{nome}' has invalid tendencia '{tendencia}'. "
                f"Must be 'alta', 'baixa', or 'estavel'"
            )

    # Validate required indicators from dimension spec are present
    required_indicators = {
        ind_spec["nome"]
        for ind_spec in dim_spec["indicadores"]
        if ind_spec.get("required", False)
    }
    missing_indicators = required_indicators - body_indicator_names
    if missing_indicators:
        raise ValueError(
            f"Missing required indicators for dimension '{dimensao}': "
            f"{sorted(missing_indicators)}"
        )

    # Validate unknown indicators
    known_indicator_names = {
        ind_spec["nome"] for ind_spec in dim_spec["indicadores"]
    }
    unknown_indicators = body_indicator_names - known_indicator_names
    if unknown_indicators:
        logger.warning(
            "[memory_module] Snapshot body contains unknown indicators "
            "for dimension '%s': %s",
            dimensao,
            sorted(unknown_indicators),
        )

    # Validate 'alertas' is a list of strings
    alertas = body.get("alertas")
    if not isinstance(alertas, list):
        raise ValueError("body.alertas must be a list")

    # Validate 'resumo_executivo' is a string
    resumo = body.get("resumo_executivo")
    if resumo is not None and not isinstance(resumo, str):
        raise ValueError("body.resumo_executivo must be a string")


# ---------------------------------------------------------------------------
# Snapshot validation (T2.2b + T2.2f)
# ---------------------------------------------------------------------------


def _validate_snapshot_frontmatter(
    entity_name: str,
    frontmatter: dict,
) -> None:
    """Validate that a snapshot has the required frontmatter fields.

    Args:
        entity_name: e.g. "financeiro:semanal" -- used for cross-validation.
        frontmatter: The frontmatter dict to validate.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(frontmatter, dict):
        raise ValueError(
            "frontmatter is required for entity_type='snapshot' and must be a dict"
        )

    # Validate required fields
    missing = _SNAPSHOT_FRONTMATTER_REQUIRED - set(frontmatter.keys())
    if missing:
        raise ValueError(
            f"Snapshot frontmatter missing required fields: {sorted(missing)}"
        )

    # Validate 'tipo' field
    if frontmatter.get("tipo") != "snapshot":
        raise ValueError(
            "frontmatter.tipo must be 'snapshot'"
        )

    # Validate dimension
    dimensao = frontmatter.get("dimensao")
    if dimensao not in _VALID_DIMENSIONS:
        raise ValueError(
            f"frontmatter.dimensao '{dimensao}' is invalid. "
            f"Must be one of: {sorted(_VALID_DIMENSIONS)}"
        )

    # Cross-validate with entity_name: dimension must match
    parts = entity_name.split(":")
    entity_dim = parts[0] if parts else ""
    if entity_dim and entity_dim != dimensao:
        raise ValueError(
            f"entity_name dimension '{entity_dim}' does not match "
            f"frontmatter.dimensao '{dimensao}'"
        )

    # Validate period
    periodo = frontmatter.get("periodo")
    if periodo not in _VALID_PERIODS:
        raise ValueError(
            f"frontmatter.periodo '{periodo}' is invalid. "
            f"Must be one of: {sorted(_VALID_PERIODS)}"
        )

    # Cross-validate period with entity_name
    if len(parts) > 1 and parts[1] and parts[1] != periodo:
        raise ValueError(
            f"entity_name period '{parts[1]}' does not match "
            f"frontmatter.periodo '{periodo}'"
        )

    # Validate version is positive int
    versao = frontmatter.get("versao")
    if not isinstance(versao, int) or versao < 1:
        raise ValueError(
            "frontmatter.versao must be a positive integer"
        )

    # Validate template_version is positive int
    template_version = frontmatter.get("template_version")
    if not isinstance(template_version, int) or template_version < 1:
        raise ValueError(
            "frontmatter.template_version must be a positive integer"
        )

    # Validate fontes is a list of strings
    fontes = frontmatter.get("fontes")
    if not isinstance(fontes, list) or not all(isinstance(f, str) for f in fontes):
        raise ValueError("frontmatter.fontes must be a list of strings")


def _validate_snapshot_body(
    entity_name: str,
    body: dict,
) -> None:
    """Validate a snapshot body against its dimension schema.

    Args:
        entity_name: e.g. "financeiro:semanal" -- dimension extracted from here.
        body: The body dict (value column content).

    Raises:
        ValueError: If validation fails.
    """
    # Extract dimension from entity_name
    parts = entity_name.split(":")
    dimensao = parts[0] if parts else ""

    if not dimensao:
        raise ValueError(
            "Cannot determine snapshot dimension from entity_name"
        )

    if dimensao not in _VALID_DIMENSIONS:
        raise ValueError(
            f"Invalid snapshot dimension '{dimensao}'. "
            f"Must be one of: {sorted(_VALID_DIMENSIONS)}"
        )

    # Validate base fields are present
    missing_base = _SNAPSHOT_BASE_FIELDS - set(body.keys())
    if missing_base:
        raise ValueError(
            f"Snapshot body missing required base fields: {sorted(missing_base)}"
        )

    # Validate 'dimensao' inside body matches entity_name
    body_dimensao = body.get("dimensao")
    if body_dimensao != dimensao:
        raise ValueError(
            f"body.dimensao '{body_dimensao}' does not match "
            f"entity_name dimension '{dimensao}'"
        )

    # Validate 'indicadores' is a list
    indicadores = body.get("indicadores")
    if not isinstance(indicadores, list):
        raise ValueError("body.indicadores must be a list")

    # Validate indicators against dimension spec
    dim_spec = _SNAPSHOT_DIMENSION_FIELDS.get(dimensao)
    if dim_spec is None:
        raise ValueError(
            f"Unknown snapshot dimension '{dimensao}'"
        )

    # Build a lookup of indicator names present in body
    body_indicator_names: set[str] = set()
    for ind in indicadores:
        if not isinstance(ind, dict):
            raise ValueError(
                f"Each indicator in body.indicadores must be a dict"
            )
        nome = ind.get("nome")
        if not nome or not isinstance(nome, str):
            raise ValueError(
                f"Each indicator must have a 'nome' (string)"
            )
        body_indicator_names.add(nome)

        # Validate required fields within each indicator
        if "valor" not in ind:
            raise ValueError(
                f"Indicator '{nome}' missing required field 'valor'"
            )
        if "unidade" not in ind:
            raise ValueError(
                f"Indicator '{nome}' missing required field 'unidade'"
            )
        tendencia = ind.get("tendencia")
        if tendencia is not None and tendencia not in ("alta", "baixa", "estavel"):
            raise ValueError(
                f"Indicator '{nome}' has invalid tendencia '{tendencia}'. "
                f"Must be 'alta', 'baixa', or 'estavel'"
            )

    # Validate required indicators from dimension spec are present
    required_indicators = {
        ind_spec["nome"]
        for ind_spec in dim_spec["indicadores"]
        if ind_spec.get("required", False)
    }
    missing_indicators = required_indicators - body_indicator_names
    if missing_indicators:
        raise ValueError(
            f"Missing required indicators for dimension '{dimensao}': "
            f"{sorted(missing_indicators)}"
        )

    # Validate unknown indicators
    known_indicator_names = {
        ind_spec["nome"] for ind_spec in dim_spec["indicadores"]
    }
    unknown_indicators = body_indicator_names - known_indicator_names
    if unknown_indicators:
        logger.warning(
            "[memory_module] Snapshot body contains unknown indicators "
            "for dimension '%s': %s",
            dimensao,
            sorted(unknown_indicators),
        )

    # Validate 'alertas' is a list of strings
    alertas = body.get("alertas")
    if not isinstance(alertas, list):
        raise ValueError("body.alertas must be a list")

    # Validate 'resumo_executivo' is a string
    resumo = body.get("resumo_executivo")
    if resumo is not None and not isinstance(resumo, str):
        raise ValueError("body.resumo_executivo must be a string")


# ---------------------------------------------------------------------------
# TTL lifecycle helper (Fase 4 — T4.4c)
# ---------------------------------------------------------------------------


def _compute_ttl_columns(
    ttl_tier: str | None = None,
    source: str = "manual",
) -> dict:
    """Compute soft_delete_at and hard_delete_at based on ttl_tier.

    If ttl_tier is provided, validate and use its interval.
    If not provided, infer default from source.

    Returns a dict with keys: soft_delete_at, hard_delete_at, ttl_tier.
    Values are ISO-format datetime strings or None.
    For 'curated' tier, both are None (never expires).

    Raises ValueError for invalid ttl_tier.
    """
    from datetime import datetime, timedelta, timezone

    # Resolve tier: explicit > source default
    if ttl_tier is not None:
        tier = ttl_tier.strip().lower()
    else:
        tier = _SOURCE_TTL_DEFAULTS.get(source)
        if tier is None:
            # Unknown source — conservative default: specialist (30d)
            logger.warning(
                "[memory_module] Unknown source '%s' for TTL tier inference, "
                "defaulting to 'specialist' (30d).",
                source,
            )
            tier = "specialist"

    # Validate against enum
    if tier not in _VALID_TTL_TIERS:
        raise ValueError(
            f"Invalid ttl_tier '{tier}'. "
            f"Must be one of: {sorted(_VALID_TTL_TIERS)}"
        )

    # Compute intervals
    interval_days = _TTL_TIER_INTERVALS[tier]

    if interval_days is None:
        # curated — never expires
        return {
            "soft_delete_at": None,
            "hard_delete_at": None,
            "ttl_tier": tier,
        }

    now = datetime.now(timezone.utc)
    soft = now + timedelta(days=interval_days)
    hard = now + timedelta(days=interval_days + _ARCHIVAL_PERIOD_DAYS)

    return {
        "soft_delete_at": soft.isoformat(),
        "hard_delete_at": hard.isoformat(),
        "ttl_tier": tier,
    }


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

    # T5.4 — Check if entry has been flushed (soft-deleted)
    _check_not_flushed(
        row.get("metadata"),
        f"{entity_type}:{entity_name}/{key}",
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

    If an existing row is found, its current state is archived to
    ``shared_business_memory_versions`` before the update, and the version
    number is incremented.  Uses INSERT ... ON CONFLICT (client_id,
    entity_type, entity_name, key) DO UPDATE.

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

    # Snapshot validation (T2.2b + T2.2f)
    if entity_type == "snapshot":
        if frontmatter is None:
            raise ValueError(
                "frontmatter is required for entity_type='snapshot'"
            )
        _validate_snapshot_frontmatter(entity_name, frontmatter)
        _validate_snapshot_body(entity_name, body)

    db = await get_supabase_client()

    # ── Archive current version before overwriting (T5.3) ──────────
    from .version_module import _archive_memory_version as _archive_version

    archive_result = await _archive_version(
        client_id=client_id,
        entity_type=entity_type,
        entity_name=entity_name,
        key=key,
    )

    new_version = (
        archive_result["archived_version"] + 1
        if archive_result is not None
        else 1
    )

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
        "version": new_version,
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
# Vector search business logic (T3.1c)
# ---------------------------------------------------------------------------


async def _shared_memory_search_logic(
    client_id: str,
    query: str,
    entity_type: str | None = None,
    category: str | None = None,
    match_count: int = 10,
    match_threshold: float = 0.3,
) -> dict:
    """
    Busca vetorial na shared_business_memory.

    1. Gera embedding da query via Cohere embed-multilingual-light-v3.0
    2. Chama RPC public.search_shared_memory()
    3. Retorna resultados com similarity scores

    Args:
        client_id: UUID do cliente
        query: Texto de busca em linguagem natural
        entity_type: Filtrar por tipo de entidade (opcional)
        category: Filtrar por categoria semântica (opcional)
        match_count: Máximo de resultados (default 10)
        match_threshold: Similaridade mínima (default 0.3)

    Returns:
        dict com query, total_results e results ordenados por similarity.

    Raises:
        ToolError: Se Cohere não disponível ou query embedding falhar.
    """
    if not query or not query.strip():
        raise ValueError("query is required and cannot be empty")

    if entity_type is not None:
        _validate_entity_type(entity_type)

    # 1. Gerar embedding da query via Cohere
    try:
        from blu_llm_service import get_cohere_embedding_model
        embedder = get_cohere_embedding_model()
        query_embedding = embedder.embed_query(query.strip())
        embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"
    except ImportError:
        raise ToolError(
            "blu_llm_service não disponível para embedding vetorial. "
            "Verifique se o pacote está instalado."
        )
    except ValueError as exc:
        raise ToolError(
            f"Configuração do Cohere ausente: {exc}. "
            "Configure CO_API_KEY no ambiente."
        )
    except Exception as exc:
        raise ToolError(f"Falha ao gerar embedding da query: {exc}")

    # 2. Chamar RPC search_shared_memory
    db = await get_supabase_client()
    try:
        result = await db.rpc(
            "search_shared_memory",
            {
                "p_client_id": client_id,
                "p_query_embed": embedding_str,
                "p_match_count": match_count,
                "p_match_threshold": match_threshold,
                "p_entity_type": entity_type,
                "p_category": category,
            },
        ).execute()
    except Exception as exc:
        logger.error(
            "[memory_module] RPC search_shared_memory failed: %s", exc
        )
        raise ToolError(
            f"Falha ao buscar na memória compartilhada: {exc}"
        )

    # 3. Formatar resultado
    rows = result.data or []
    formatted_results = []
    for r in rows:
        formatted_results.append({
            "id": r["id"],
            "entity_type": r["entity_type"],
            "entity_name": r["entity_name"],
            "key": r["key"],
            "value": r["value"],
            "category": r.get("category"),
            "source": r.get("source"),
            "confidence": float(r.get("confidence", 1.0)),
            "similarity": round(float(r["similarity"]), 4),
        })

    return {
        "query": query,
        "total_results": len(formatted_results),
        "results": formatted_results,
    }


# ---------------------------------------------------------------------------
# Flush business logic (T5.4)
# ---------------------------------------------------------------------------


async def _shared_memory_flush_logic(
    client_id: str,
    entity_type: str | None = None,
    entity_name: str | None = None,
    key: str | None = None,
) -> dict:
    """Flush (soft-delete) shared-memory entries for a client.

    Marks matching entries as flushed by setting ``metadata->>'flushed_at'``
    to the current UTC ISO timestamp.  This is a soft-delete — rows remain in
    the database but are hidden from ``shared_memory_read``.

    Filters are optional.  When no filters are provided, all entries for
    the client are flushed.  The operation is **idempotent** — already-flushed
    entries are silently skipped.

    Args:
        client_id: UUID of the client whose memory is being flushed.
        entity_type: Optional filter — only flush entries of this type.
        entity_name: Optional filter — only flush entries with this name.
        key: Optional filter — only flush entries with this key.

    Returns:
        dict with ``flushed_count`` (number of entries actually flushed in
        this call), ``total_scanned`` (number of rows matching filters),
        and ``skipped_already_flushed``.

    Raises:
        ValueError: If entity_type is invalid or no rows match.
    """
    from datetime import datetime, timezone

    if entity_type is not None:
        _validate_entity_type(entity_type)
    if entity_name is not None:
        entity_name = _normalize_entity_name(entity_name)
    if key is not None:
        key = key.strip().lower()

    db = await get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Query matching rows (all columns needed, only distinct per unique key)
    query = (
        db.schema("public")
        .table(_TABLE)
        .select("id, metadata")
        .eq("client_id", client_id)
    )
    if entity_type:
        query = query.eq("entity_type", entity_type)
    if entity_name:
        query = query.eq("entity_name", entity_name)
    if key:
        query = query.eq("key", key)

    result = await query.execute()
    rows = result.data if result.data else []

    total_scanned = len(rows)
    if total_scanned == 0:
        raise ValueError(
            "No shared-memory entries match the given filters. "
            "Nothing to flush."
        )

    # 2. Identify which rows need flushing (not already flushed)
    rows_to_flush: list[str] = []
    skipped_already_flushed = 0

    for r in rows:
        meta = r.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        if "flushed_at" in meta:
            skipped_already_flushed += 1
            continue
        rows_to_flush.append(r["id"])

    if not rows_to_flush:
        return {
            "flushed_count": 0,
            "total_scanned": total_scanned,
            "skipped_already_flushed": skipped_already_flushed,
            "message": (
                f"All {total_scanned} matching entries are already flushed."
            ),
            "flushed_at": now_iso,
        }

    # 3. Batch update flushed_at in metadata
    flushed_count = 0
    flush_errors: list[str] = []

    for row_id in rows_to_flush:
        try:
            # Read current metadata
            meta_result = await (
                db.schema("public")
                .table(_TABLE)
                .select("metadata")
                .eq("id", row_id)
                .single()
                .execute()
            )
            current_meta = (meta_result.data or {}).get("metadata", {}) or {}
            if isinstance(current_meta, str):
                try:
                    current_meta = json.loads(current_meta)
                except (json.JSONDecodeError, TypeError):
                    current_meta = {}

            current_meta["flushed_at"] = now_iso

            await (
                db.schema("public")
                .table(_TABLE)
                .update({"metadata": current_meta})
                .eq("id", row_id)
                .eq("client_id", client_id)
                .execute()
            )
            flushed_count += 1
        except Exception as exc:
            logger.error(
                "[memory_module] Flush error for row %s: %s", row_id, exc
            )
            flush_errors.append(str(exc))

    return {
        "flushed_count": flushed_count,
        "total_scanned": total_scanned,
        "skipped_already_flushed": skipped_already_flushed,
        "flush_errors": flush_errors if flush_errors else [],
        "flushed_at": now_iso,
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
    # shared_memory_write --  write a new fact (strict INSERT by default)
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_write",
        description=(
            "[Shared Memory] Write a new fact into shared memory. "
            "By default this is a strict INSERT — it fails if the "
            "composite key (client_id, entity_type, entity_name, key) "
            "already exists. Set supersede=true to overwrite. "
            "The ``value`` parameter maps directly to the jsonb column. "
            "Use ``category`` to classify the fact semantically "
            "(knowledge | rag | documents | memory-agent | "
            "context | decision | preference). "
            "Optional ``agent_id``, ``ttl``, and ``priority`` are stored "
            "inside the metadata column."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_write(
        ctx: Context,
        entity_type: str,
        entity_name: str,
        key: str,
        value: dict,
        category: str | None = None,
        agent_id: str | None = None,
        ttl: int | None = None,
        priority: int | None = None,
        supersede: bool = False,
        source: str = "manual",
        confidence: float = 1.0,
        client_id: str | None = None,
    ) -> dict:
        """
        Write a new shared-memory fact.

        Args:
            entity_type: Entity type (skill | client | contact | supplier | user | snapshot).
            entity_name: Entity name (case-insensitive, normalized to lowercase).
            key: Fact key (e.g. "tom_amigavel", "preferencia_horario").
            value: The fact value (dict — maps to 'value' jsonb column).
            category: Optional semantic category for filtering/routing.
            agent_id: Optional agent UUID (stored in metadata).
            ttl: Optional time-to-live in seconds (stored in metadata).
            priority: Optional priority 0-100 (stored in metadata).
            supersede: If True, upsert to overwrite an existing entry. Default False (strict insert).
            source: Provenance — "manual" | "memory_agent" | "specialist" | "migration" | "system".
            confidence: Confidence score (0.0--1.0, default 1.0).

        Returns:
            dict with the full written record including id, version, and timestamps.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        # Tool-level validation (T1.4b)
        if not entity_type or not entity_type.strip():
            raise ToolError("entity_type is required")
        if not entity_name or not entity_name.strip():
            raise ToolError("entity_name is required")
        if not key or not key.strip():
            raise ToolError("key is required")
        if not isinstance(value, dict):
            raise ToolError("value must be a dict")
        if category is not None and category not in _VALID_CATEGORIES:
            raise ToolError(
                f"Invalid category '{category}'. "
                f"Must be one of: {sorted(_VALID_CATEGORIES)}"
            )

        logger.info(
            "[memory_module] shared_memory_write "
            "entity_type=%s entity_name=%s key=%s category=%s "
            "supersede=%s client_id=%s",
            entity_type,
            entity_name,
            key,
            category,
            supersede,
            client_id,
        )

        try:
            return await _shared_memory_write_logic(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
                value=value,
                category=category,
                agent_id=agent_id,
                ttl=ttl,
                priority=priority,
                supersede=supersede,
                source=source,
                confidence=confidence,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_write failed: %s", exc
            )
            raise ToolError(
                f"Failed to write shared-memory entry: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_write' registered.")
    registered_tools.append("shared_memory_write")

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

    # ----------------------------------------------------------------------
    # shared_memory_search -- semantic vector search in shared business memory
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_search",
        description=(
            "[Shared Memory] Semantic (vector) search in shared business memory. "
            "Use this to find facts about business entities by meaning, not exact keywords. "
            "The query is embedded with Cohere (embed-multilingual-light-v3.0, 384 dims) "
            "and matched against stored facts using cosine similarity via pgvector HNSW index. "
            "Parameters: query (natural language search text), entity_type (optional filter "
            "by entity type: skill|client|contact|supplier|user|snapshot|routine|agent_result|"
            "agent_metadata), category (optional filter by semantic category), match_count "
            "(max results, default 10), match_threshold (minimum similarity 0.0-1.0, default 0.3). "
            "Returns facts ranked by similarity score. Use this when you need to find business "
            "knowledge semantically, e.g., 'which clients prefer communication via WhatsApp' "
            "or 'what are the key facts about supplier Distribuidora X'."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_search(
        ctx: Context,
        query: str,
        entity_type: str | None = None,
        category: str | None = None,
        match_count: int = 10,
        match_threshold: float = 0.3,
        client_id: str | None = None,
    ) -> dict:
        """
        Search shared business memory using semantic (vector) similarity.

        Generates a Cohere embedding for the query text and matches it against
        stored fact embeddings via the pgvector HNSW index in shared_business_memory.

        Args:
            query: Natural language search text describing what you're looking for.
                   Write it as a question or description, e.g.:
                   - "preferências de comunicação dos clientes"
                   - "fornecedores com contrato vigente"
                   - "faturamento mensal dos últimos 6 meses"
                   - "clientes com tom amigável"
            entity_type: Optional filter. Only return facts of this entity type.
                         Valid: skill, client, contact, supplier, user, snapshot,
                         routine, agent_result, agent_metadata.
            category: Optional filter by semantic category.
            match_count: Maximum number of results to return (default 10, max 50).
            match_threshold: Minimum similarity score 0.0--1.0 (default 0.3).
                             Lower values return more but less relevant results.

        Returns:
            dict with:
            - query: The original search text
            - total_results: Number of matching facts found
            - results: Array of facts ordered by similarity (descending).
              Each fact has: id, entity_type, entity_name, key, value,
              category, source, confidence, similarity.

        Examples:
            >>> # Find all communication preferences
            >>> shared_memory_search(query="preferências de comunicação dos clientes")

            >>> # Find financial data about a specific supplier
            >>> shared_memory_search(
            ...     query="dados financeiros e contratos",
            ...     entity_type="supplier",
            ...     match_count=5,
            ... )

            >>> # Find snapshot data with stricter threshold
            >>> shared_memory_search(
            ...     query="resumo financeiro mensal",
            ...     entity_type="snapshot",
            ...     match_threshold=0.5,
            ... )
        """
        if not client_id:
            raise ToolError(
                "client_id is required -- authentication context missing"
            )

        if match_count < 1 or match_count > 50:
            raise ToolError(
                "match_count must be between 1 and 50"
            )

        if match_threshold < 0.0 or match_threshold > 1.0:
            raise ToolError(
                "match_threshold must be between 0.0 and 1.0"
            )

        logger.info(
            "[memory_module] shared_memory_search "
            "query='%s' entity_type=%s category=%s "
            "match_count=%d match_threshold=%.2f client_id=%s",
            query[:80],
            entity_type,
            category,
            match_count,
            match_threshold,
            client_id,
        )

        try:
            return await _shared_memory_search_logic(
                client_id=client_id,
                query=query,
                entity_type=entity_type,
                category=category,
                match_count=match_count,
                match_threshold=match_threshold,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except ToolError:
            raise
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_search failed: %s", exc
            )
            raise ToolError(
                f"Failed to search shared memory: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_search' registered.")
    registered_tools.append("shared_memory_search")

    # ----------------------------------------------------------------------
    # shared_memory_flush --  soft-delete memory entries (T5.4)
    # ----------------------------------------------------------------------

    @mcp.tool(
        name="shared_memory_flush",
        description=(
            "[Shared Memory] Flush (soft-delete) shared-memory entries. "
            "Marks matching entries as flushed by recording a timestamp in "
            "their metadata. Flushed entries are hidden from "
            "shared_memory_read but remain in the database for recovery "
            "and auditing. "
            "Filters (entity_type, entity_name, key) are optional; when none "
            "are provided, ALL entries for the current client are flushed. "
            "Idempotent — calling flush multiple times on already-flushed "
            "entries is safe and returns flushed_count=0. "
            "Use this after exporting data or when you need to reset the "
            "shared memory for a client."
        ),
    )
    @mcp_inject_client_id
    async def shared_memory_flush(
        ctx: Context,
        entity_type: str | None = None,
        entity_name: str | None = None,
        key: str | None = None,
        client_id: str | None = None,
    ) -> dict:
        """Flush (soft-delete) shared-memory entries.

        Marks matching entries as flushed so they are no longer returned by
        ``shared_memory_read``.  The rows are NOT hard-deleted — they remain
        for auditing and can be recovered.

        Args:
            entity_type: Optional — only flush entries of this type.
                         Valid: skill, client, contact, supplier, user,
                         snapshot, routine, agent_result, agent_metadata.
            entity_name: Optional — only flush entries with this name.
                         Case-insensitive, normalized to lowercase.
            key: Optional — only flush the specific key.
                 Case-insensitive, normalized to lowercase.

        Returns:
            dict with:
            - flushed_count: number of entries actually flushed in this call
            - total_scanned: number of rows matching filters
            - skipped_already_flushed: entries already flushed (idempotent)
            - flush_errors: any errors during the operation (empty on success)
            - flushed_at: ISO timestamp of the flush operation

        Examples:
            >>> # Flush all entries for a specific entity
            >>> shared_memory_flush(
            ...     entity_type="client",
            ...     entity_name="joao_silva",
            ... )

            >>> # Flush a single fact
            >>> shared_memory_flush(
            ...     entity_type="skill",
            ...     entity_name="comunicacao",
            ...     key="tom_amigavel",
            ... )

            >>> # Flush ALL shared memory for the client (use with caution!)
            >>> shared_memory_flush()
        """
        if not client_id:
            raise ToolError(
                "client_id is required -- authentication context missing"
            )

        if entity_type is not None:
            try:
                _validate_entity_type(entity_type)
            except ValueError as exc:
                raise ToolError(str(exc))

        logger.info(
            "[memory_module] shared_memory_flush "
            "entity_type=%s entity_name=%s key=%s client_id=%s",
            entity_type,
            entity_name,
            key,
            client_id,
        )

        try:
            return await _shared_memory_flush_logic(
                client_id=client_id,
                entity_type=entity_type,
                entity_name=entity_name,
                key=key,
            )
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error(
                "[memory_module] shared_memory_flush failed: %s", exc
            )
            raise ToolError(
                f"Failed to flush shared memory: {exc}"
            )

    logger.info("[Memory Module] Tool 'shared_memory_flush' registered.")
    registered_tools.append("shared_memory_flush")

    return registered_tools
