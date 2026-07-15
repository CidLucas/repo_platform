"""
sbm_to_lightrag_synthesis.py — SBM → LightRAG Synthesis Skill (T4.1a)

L2 Skill that reads curated records from shared_business_memory per client_id,
groups them by entity_type + entity_name, generates a Markdown synthesis for each
entity, and inserts them into LightRAG via ainsert_custom_kg().

Design decisions:
  DD-T41-01: Registered as MCP tool (skill_name='sbm_to_lightrag_synthesis')
  DD-T41-03: Query filters curated=true, expires_at IS NULL
  DD-T41-04: Grouping in Python by entity_type/entity_name
  DD-T41-05: SYNTHESIS_TEMPLATES per entity_type
  DD-T41-06: rag_client.ainsert_custom_kg() — one call per entity
  DD-T41-07: normalize_entity_name() canonical ID; contacts prefixed with 'contact:'
  DD-T41-09: Per-entity error handling — log and continue
  DD-T41-10: source_id with YYYYMMDD for idempotency
"""

from __future__ import annotations

import logging
from datetime import UTC, date, timezone
from typing import Any
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.tool_modules import register_module
from tool_pool_api.server.utils.entity import normalize_entity_name_strict as normalize_entity_name

logger = logging.getLogger(__name__)

_TABLE = "shared_business_memory"

# ---------------------------------------------------------------------------
# SYNTHESIS_TEMPLATES
# ---------------------------------------------------------------------------

# Each template is a Markdown-formatted string with {field} placeholders.
# Placeholders are drawn from SBM record fields and a synthetic facts block
# built from all key-value pairs. Snapshot templates additionally have
# {resumo_executivo} and {indicadores} blocks.

SYNTHESIS_TEMPLATES: dict[str, str] = {
    "skill": """\
# {entity_name}
**Type**: Skill
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
""",

    "client": """\
# {entity_name}
**Type**: Client
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
""",

    "contact": """\
# contact:{entity_name}
**Type**: Contact
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
""",

    "supplier": """\
# {entity_name}
**Type**: Supplier
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
""",

    "user": """\
# {entity_name}
**Type**: User
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
""",

    "snapshot": """\
# Snapshot: {entity_name}
**Type**: Snapshot
**Last Updated**: {updated_at}

## Resumo Executivo
{resumo_executivo}

## Indicadores
{indicadores}

## All Facts
{facts}
""",
}


# ---------------------------------------------------------------------------
# build_synthesis helpers
# ---------------------------------------------------------------------------

def _format_json_value(value: Any) -> str:
    """Format a JSONB value for Markdown display.

    - Strings: rendered as-is
    - Numbers / bools: str()
    - Lists: bullet points
    - Dicts: key: value lines
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        items = [f"- {_format_json_value(v)}" for v in value]
        return "\n".join(items)
    if isinstance(value, dict):
        lines = [f"- **{k}**: {_format_json_value(v)}" for k, v in value.items()]
        return "\n".join(lines)
    return str(value)


def _build_facts_block(records: list[dict]) -> str:
    """Build a Markdown facts section from SBM key-value records.

    Each record becomes a heading with its value rendered underneath.
    Records with empty/{} values are skipped.
    """
    lines: list[str] = []
    for rec in records:
        key = rec.get("key", "unknown")
        value = rec.get("value")
        # Skip empty values
        if value is None:
            continue
        if isinstance(value, dict) and not value:
            continue
        if isinstance(value, str) and not value.strip():
            continue

        formatted = _format_json_value(value)
        lines.append(f"### {key}")
        lines.append("")
        lines.append(formatted)
        lines.append("")

    return "\n".join(lines).strip()


def _build_snapshot_blocks(records: list[dict]) -> tuple[str, str]:
    """Extract resumo_executivo and indicadores from snapshot records.

    Returns:
        (resumo_executivo_md, indicadores_md)
    """
    resumo: list[str] = []
    indicadores: list[str] = []

    for rec in records:
        key = rec.get("key", "")
        value = rec.get("value")

        if isinstance(value, (dict, list)):
            formatted = _format_json_value(value)
        elif isinstance(value, (str, int, float, bool)):
            formatted = str(value)
        else:
            formatted = str(value) if value is not None else ""

        key_lower = key.lower()
        if "resumo" in key_lower or "executivo" in key_lower:
            resumo.append(formatted)
        elif "indicador" in key_lower or "metrica" in key_lower or key_lower in (
            "kpi", "metrics", "stats", "statistics"
        ):
            indicadores.append(f"### {key}\n{formatted}")
        else:
            indicadores.append(f"### {key}\n{formatted}")

    resumo_md = "\n\n".join(resumo) if resumo else "_No executive summary available._"
    indicadores_md = (
        "\n\n".join(indicadores) if indicadores else "_No indicators available._"
    )

    return resumo_md, indicadores_md


# ---------------------------------------------------------------------------
# build_synthesis
# ---------------------------------------------------------------------------

def build_synthesis(records: list[dict]) -> str:
    """Build a Markdown synthesis document from all SBM records for one entity.

    The entity_type is extracted from the first record. Templates are filled
    with entity metadata and a facts block listing all key-value pairs.

    For entity_type='snapshot', a special layout with resumo_executivo and
    indicadores sections is generated (DQ2: SIM incluir snapshots).

    Args:
        records: List of SBM rows for a single (entity_type, entity_name)
                 pair, ordered by updated_at DESC (most recent first).

    Returns:
        Markdown-formatted synthesis string.
    """
    if not records:
        return ""

    entity_type = records[0].get("entity_type", "unknown")
    entity_name = records[0].get("entity_name", "unknown")
    source = records[0].get("source", "unknown")
    confidence = records[0].get("confidence", 1.0)
    updated_at = records[0].get("updated_at", "unknown")

    # Normalize entity_name for the heading
    normalized_name = normalize_entity_name(str(entity_name), entity_type)

    template = SYNTHESIS_TEMPLATES.get(entity_type)
    if template is None:
        # Fallback: use a generic template for unknown types
        template = """\
# {entity_name}
**Type**: {entity_type}
**Source**: {source}
**Confidence**: {confidence}
**Last Updated**: {updated_at}

## Facts
{facts}
"""

    facts = _build_facts_block(records)

    if entity_type == "snapshot":
        resumo_executivo, indicadores = _build_snapshot_blocks(records)
        return template.format(
            entity_name=normalized_name,
            source=source,
            confidence=confidence,
            updated_at=updated_at,
            facts=facts,
            resumo_executivo=resumo_executivo,
            indicadores=indicadores,
        )

    return template.format(
        entity_name=normalized_name,
        source=source,
        confidence=confidence,
        updated_at=updated_at,
        facts=facts,
    )


# ---------------------------------------------------------------------------
# execute — core business logic
# ---------------------------------------------------------------------------

async def execute(
    client_id: UUID,
    rag_client: Any,
) -> dict:
    """Execute the SBM → LightRAG synthesis cycle for a single client.

    Steps:
      1. Query curated SBM records (DD-T41-03).
      2. Group by (entity_type, entity_name) in Python (DD-T41-04).
      3. Build Markdown synthesis per entity (DD-T41-05).
      4. Insert into LightRAG via ainsert_custom_kg() (DD-T41-06).
      5. Per-entity error handling: log and continue (DD-T41-09).

    Args:
        client_id: UUID of the client (tenant isolation).
        rag_client: LightRAG client instance with ainsert_custom_kg() method
                    (from T4.1b lightrag_client).

    Returns:
        {
            "processed": int,         # number of entities successfully synced
            "errors": [               # per-entity failures
                {"entity_name": str, "entity_type": str, "error": str}
            ],
            "entities_synced": [str], # canonical IDs of synced entities
        }
    """
    # Lazy import — avoids circular dependency at registration time
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client()

    # 1. Query all curated, non-expired records (DD-T41-03)
    logger.info(
        "[sbm_to_lightrag_synthesis] Querying SBM for client_id=%s", client_id
    )
    try:
        result = (
            db.schema("public")
            .table(_TABLE)
            .select("*")
            .eq("client_id", str(client_id))
            .eq("curated", True)
            .is_("expires_at", None)
            .order("entity_type, entity_name, updated_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.exception(
            "[sbm_to_lightrag_synthesis] SBM query failed for client_id=%s: %s",
            client_id,
            exc,
        )
        raise ToolError(f"Failed to query shared_business_memory: {exc}") from exc

    rows: list[dict] = result.data if result.data else []
    total_documents = len(rows)
    logger.info(
        "[sbm_to_lightrag_synthesis] Retrieved %d records for client_id=%s",
        total_documents,
        client_id,
    )

    if not rows:
        return {
            "processed": 0,
            "errors": [],
            "entities_synced": [],
        }

    # 2. Group by (entity_type, entity_name) — DD-T41-04
    #    Records are already ordered by updated_at DESC, so the most recent
    #    version of each (entity_type, entity_name, key) comes first.
    groups: dict[tuple[str, str], list[dict]] = {}
    seen_keys: dict[tuple[str, str], set[str]] = {}

    for row in rows:
        entity_type = row.get("entity_type", "unknown")
        entity_name = row.get("entity_name", "unknown")
        key = row.get("key", "")

        group_key = (entity_type, entity_name)

        if group_key not in groups:
            groups[group_key] = []
            seen_keys[group_key] = set()

        # Deduplicate by key: keep only the most recent (first seen due to
        # updated_at DESC ordering)
        if key not in seen_keys[group_key]:
            seen_keys[group_key].add(key)
            groups[group_key].append(row)

    logger.info(
        "[sbm_to_lightrag_synthesis] Grouped into %d unique entities",
        len(groups),
    )

    # 3-4. Synthesize and insert into LightRAG
    today_str = date.today().strftime("%Y%m%d")  # YYYYMMDD for idempotency
    source_id = f"sbm_synthesis_{today_str}"

    processed = 0
    errors: list[dict[str, str]] = []
    entities_synced: list[str] = []
    synced_pairs: list[tuple[str, str]] = []

    for (entity_type, entity_name), recs in groups.items():
        normalized_name = normalize_entity_name(str(entity_name), entity_type)

        try:
            synthesis_md = build_synthesis(recs)

            # Contrato real do LightRAG (>=1.5): ainsert_custom_kg(custom_kg)
            # com chunks + entities; o source_id da entity referencia o chunk
            # do MESMO call (mapeado internamente para chunk_id).
            await rag_client.ainsert_custom_kg(
                {
                    "chunks": [
                        {
                            "content": synthesis_md,
                            "source_id": source_id,
                            "file_path": f"sbm/{entity_type}/{normalized_name}",
                        }
                    ],
                    "entities": [
                        {
                            "entity_name": normalized_name,
                            "entity_type": entity_type,
                            "description": synthesis_md,
                            "source_id": source_id,
                        }
                    ],
                    "relationships": [],  # DQ3: no relations in T4.1
                }
            )

            processed += 1
            entities_synced.append(normalized_name)
            synced_pairs.append((normalized_name, entity_type))
            logger.debug(
                "[sbm_to_lightrag_synthesis] Synced entity %s (%s)",
                normalized_name,
                entity_type,
            )

        except Exception as exc:
            # DD-T41-09: log error and continue
            logger.error(
                "[sbm_to_lightrag_synthesis] Failed to sync entity %s (%s): %s",
                normalized_name,
                entity_type,
                exc,
            )
            errors.append(
                {
                    "entity_name": normalized_name,
                    "entity_type": entity_type,
                    "error": str(exc),
                }
            )

    logger.info(
        "[sbm_to_lightrag_synthesis] Cycle complete: "
        "processed=%d errors=%d total_entities=%d",
        processed,
        len(errors),
        len(groups),
    )

    # 6. Write knowledge_graph_summary (T4.1f)
    await _write_knowledge_graph_summary(
        client_id=client_id,
        total_documents=total_documents,
        total_entities=len(entities_synced),
        synced_pairs=synced_pairs,
        errors=errors,
    )

    return {
        "processed": processed,
        "errors": errors,
        "entities_synced": entities_synced,
    }


# ---------------------------------------------------------------------------
# _write_knowledge_graph_summary (T4.1f)
# ---------------------------------------------------------------------------


async def _write_knowledge_graph_summary(
    client_id: UUID,
    total_documents: int,
    total_entities: int,
    synced_pairs: list[tuple[str, str]],
    errors: list[dict],
) -> None:
    """Write knowledge_graph_summary (schema KnowledgeGraphSummary) em 3 destinos.

    Schema alinhado ao validador de knowledge_graph_sync (DD-04):
    ``{total_documents, total_entities, top_entities, last_sync, version}``
    (+ ``sync_status`` como campo extra informativo).

    Destinos, em ordem:
      1. clientes_blu.available_tools via knowledge_graph_sync (durável,
         invalida o cache de contexto) — non-fatal.
      2. Redis ``ctx:{client_id}:knowledge_graph_summary`` (lido por
         get_domain_projection) — non-fatal.
      3. Fallback SBM (entity_type='system') apenas se o Redis falhar.

    Args:
        client_id: Client UUID.
        total_documents: Number of SBM records processed in this cycle.
        total_entities: Number of entities successfully synced.
        synced_pairs: (canonical name, entity_type) dos entities sincronizados.
        errors: Per-entity failure details.
    """
    from datetime import datetime
    from datetime import timezone as dt_timezone

    # Determine sync_status
    if not synced_pairs and errors:
        sync_status = "failed"
    elif errors:
        sync_status = "partial"
    else:
        sync_status = "ok"

    # DQ3: sem relations em T4.1 → degree 0 para todos; top_entities são os
    # primeiros N sincronizados (ordem estável do ciclo).
    top_entities = [
        {"name": name, "type": etype, "degree": 0}
        for name, etype in synced_pairs[:10]
    ]

    now_iso = datetime.now(UTC).isoformat()

    summary: dict = {
        "total_documents": total_documents,
        "total_entities": total_entities,
        "top_entities": top_entities,
        "last_sync": now_iso,
        "version": 1,
        "sync_status": sync_status,
    }

    logger.info(
        "[sbm_to_lightrag_synthesis] KG summary: total_documents=%d "
        "total_entities=%d sync_status=%s top_entities=%d",
        total_documents,
        total_entities,
        sync_status,
        len(top_entities),
    )

    # 1. Durable writeback: clientes_blu.available_tools (T4.3) — non-fatal
    try:
        from tool_pool_api.server.tool_modules.knowledge_graph_sync import (
            update_knowledge_graph_summary,
        )

        await update_knowledge_graph_summary(client_id, summary)
    except Exception as exc:
        logger.warning(
            "[sbm_to_lightrag_synthesis] Durable KG summary writeback failed "
            "(non-fatal): %s",
            exc,
        )

    # 2. Try Context Service (Redis)
    try:
        from tool_pool_api.server.dependencies import get_context_service

        ctx_service = get_context_service()
        redis_key = f"ctx:{client_id}:knowledge_graph_summary"
        import asyncio

        await asyncio.to_thread(
            ctx_service.cache.set_json,
            redis_key,
            summary,
            86_400,  # 24h TTL
        )
        logger.info(
            "[sbm_to_lightrag_synthesis] KG summary written to Redis key=%s",
            redis_key,
        )
        return
    except Exception as exc:
        logger.warning(
            "[sbm_to_lightrag_synthesis] Could not write KG summary to "
            "Context Service Redis: %s — falling back to SBM",
            exc,
        )

    # 3. Fallback: write to shared_business_memory
    try:
        from blu_supabase_client import get_supabase_client

        db = get_supabase_client()

        payload = {
            "client_id": str(client_id),
            "entity_type": "system",
            "entity_name": "knowledge_graph_summary",
            "key": "knowledge_graph_summary",
            "value": summary,
            "metadata": {"last_sync": now_iso},
            "source": "system",
            "confidence": 1.0,
            "curated": True,
        }

        (
            db.schema("public")
            .table("shared_business_memory")
            .upsert(
                payload,
                on_conflict="client_id,entity_type,entity_name,key",
            )
            .execute()
        )
        logger.info(
            "[sbm_to_lightrag_synthesis] KG summary written to SBM fallback "
            "for client_id=%s",
            client_id,
        )
    except Exception as exc:
        logger.error(
            "[sbm_to_lightrag_synthesis] Failed to write KG summary to "
            "SBM fallback for client_id=%s: %s",
            client_id,
            exc,
        )


# ---------------------------------------------------------------------------
# MCP Tool registration (DD-T41-01)
# ---------------------------------------------------------------------------


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register the sbm_to_lightrag_synthesis tool on the MCP server.

    This tool is an L2 infrastructure/background skill. It can be triggered
    by the Routine Engine (via pg_cron) or called directly for manual sync.
    """
    registered_tools: list[str] = []

    @mcp.tool(
        name="sbm_to_lightrag_synthesis",
        description=(
            "[SBM→LightRAG] Synthesize curated shared_business_memory records "
            "into LightRAG knowledge graph entities for the authenticated client. "
            "Groups records by entity_type/entity_name, generates Markdown "
            "syntheses, and inserts them via ainsert_custom_kg(). "
            "Returns {processed, errors, entities_synced}. "
            "Call this to refresh the knowledge graph with the latest curated "
            "business memory."
        ),
    )
    async def sbm_to_lightrag_synthesis(
        ctx: Context,
        client_id: str | None = None,
    ) -> dict:
        """Synthesize curated SBM records into LightRAG knowledge graph.

        Uses the client_id from the authentication context or explicitly
        provided parameter.

        Args:
            client_id: Optional explicit client UUID. If omitted, derived
                       from the auth context.

        Returns:
            dict with processed count, errors list, and entities_synced list.
        """
        if not client_id:
            raise ToolError(
                "client_id is required — authentication context missing"
            )

        # Validate UUID
        try:
            uuid_obj = UUID(client_id)
        except ValueError:
            raise ToolError(f"Invalid client_id: {client_id}")

        logger.info(
            "[sbm_to_lightrag_synthesis] Tool invoked for client_id=%s",
            client_id,
        )

        try:
            # Lazy import rag_client factory (T4.1b)
            from tool_pool_api.server.utils.lightrag_client import (
                get_client_rag,
            )

            rag_client = await get_client_rag(uuid_obj)
            return await execute(
                client_id=uuid_obj,
                rag_client=rag_client,
            )
        except ImportError as exc:
            raise ToolError(
                f"LightRAG client not available: {exc}. "
                f"Ensure T4.1b (lightrag_client.py) is deployed."
            )
        except ToolError:
            raise
        except Exception as exc:
            logger.exception(
                "[sbm_to_lightrag_synthesis] Tool execution failed: %s", exc
            )
            raise ToolError(
                f"sbm_to_lightrag_synthesis failed: {exc}"
            )

    logger.info(
        "[SBM→LightRAG Module] Tool 'sbm_to_lightrag_synthesis' registered."
    )
    registered_tools.append("sbm_to_lightrag_synthesis")

    return registered_tools
