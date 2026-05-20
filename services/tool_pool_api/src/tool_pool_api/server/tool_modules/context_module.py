# tool_pool_api/server/tool_modules/context_module.py
"""
Context Module - Transaction registration and data-source listing

Gives the context-gatherer agent the ability to:
  - register_transaction: write a sale or purchase into analytics_v2
  - list_data_sources: surface what data has already been ingested
"""

import logging
import os
from datetime import UTC, datetime
from datetime import date as date_type
from uuid import uuid4

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client
from tool_pool_api.server.dependencies import get_context_service

from . import register_module

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VENDA_TYPES = {"venda", "receita", "entrada"}
_COMPRA_TYPES = {"compra", "aquisição", "aquisicao"}


async def _resolve_data_id(db, data_str: str) -> int | None:
    """Return dim_datas.data_id for the given ISO date string, or None."""
    result = (
        await db.schema("analytics_v2")
        .table("dim_datas")
        .select("data_id")
        .eq("data", data_str)
        .maybe_single()
        .execute()
    )
    return result.data["data_id"] if result.data else None


async def _resolve_customer_id(db, client_id: str, nome: str) -> int | None:
    """Return dim_clientes.customer_id (BIGINT PK) by partial name match (ILIKE)."""
    result = (
        await db.schema("analytics_v2")
        .table("dim_clientes")
        .select("customer_id")
        .eq("client_id", client_id)
        .ilike("nome", f"%{nome}%")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0]["customer_id"] if rows else None


async def _resolve_fornecedor_id(db, client_id: str, nome: str) -> int | None:
    """Return dim_fornecedores.fornecedor_id by partial name match (ILIKE)."""
    result = (
        await db.schema("analytics_v2")
        .table("dim_fornecedores")
        .select("fornecedor_id")
        .eq("client_id", client_id)
        .ilike("nome", f"%{nome}%")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0]["fornecedor_id"] if rows else None


async def _resolve_produto_id(db, client_id: str, nome: str) -> int | None:
    """Return dim_inventory.inventory_id by partial name or SKU match."""
    result = (
        await db.schema("analytics_v2")
        .table("dim_inventory")
        .select("inventory_id")
        .eq("client_id", client_id)
        .ilike("nome", f"%{nome}%")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0]["inventory_id"] if rows else None


# ---------------------------------------------------------------------------
# register_transaction
# ---------------------------------------------------------------------------


async def _register_transaction_logic(
    tipo_transacao: str,
    valor: float,
    data: str,
    ctx: Context,
    cliente_nome: str | None = None,
    fornecedor_nome: str | None = None,
    produto_nome: str | None = None,
    quantidade: float | None = None,
    valor_unitario: float | None = None,
    documento: str | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Register a business transaction into analytics_v2.

    Args:
        tipo_transacao: Transaction type — "venda", "compra", "despesa", or any
            free-text label. Determines target table: vendas/despesas → fato_transacoes,
            compras → fato_compras.
        valor: Total monetary value of the transaction.
        data: Competence date in ISO format (YYYY-MM-DD).
        cliente_nome: Customer name (used for dim_clientes lookup on vendas).
        fornecedor_nome: Supplier name (used for dim_fornecedores lookup on compras/despesas).
        produto_nome: Product/item name (used for dim_inventory lookup).
        quantidade: Quantity transacted.
        valor_unitario: Unit price.
        documento: Document reference (NF number, invoice ID, etc.).
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    if not tipo_transacao:
        raise ToolError("tipo_transacao é obrigatório.")
    if valor is None:
        raise ToolError("valor é obrigatório.")
    if not data:
        raise ToolError("data é obrigatória (formato YYYY-MM-DD).")

    # Validate / normalise date
    try:
        date_type.fromisoformat(data)
    except ValueError:
        raise ToolError(f"data inválida: '{data}'. Use o formato YYYY-MM-DD.")

    tipo_lower = tipo_transacao.strip().lower()
    is_compra = tipo_lower in _COMPRA_TYPES

    try:
        db = get_supabase_client()

        # Resolve foreign keys
        data_competencia_id = await _resolve_data_id(db, data)
        if data_competencia_id is None:
            logger.warning("[Context] dim_datas sem entrada para %s — data_competencia_id será nulo", data)

        dim_customer_id: int | None = None
        if cliente_nome:
            dim_customer_id = await _resolve_customer_id(db, client_id, cliente_nome)
            if dim_customer_id is None:
                logger.warning("[Context] dim_clientes: nenhum match para '%s'", cliente_nome)

        dim_fornecedor_id: int | None = None
        if fornecedor_nome:
            dim_fornecedor_id = await _resolve_fornecedor_id(db, client_id, fornecedor_nome)
            if dim_fornecedor_id is None:
                logger.warning("[Context] dim_fornecedores: nenhum match para '%s'", fornecedor_nome)

        dim_produto_id: int | None = None
        if produto_nome:
            dim_produto_id = await _resolve_produto_id(db, client_id, produto_nome)
            if dim_produto_id is None:
                logger.warning("[Context] dim_inventory: nenhum match para '%s'", produto_nome)

        if is_compra:
            record_id = str(uuid4())
            row = {
                "compra_id": record_id,
                "client_id": client_id,
                "data_competencia_id": data_competencia_id,
                "fornecedor_id": dim_fornecedor_id,
                "produto_id": dim_produto_id,
                "documento": documento,
                "quantidade": quantidade,
                "valor_unitario": valor_unitario,
                "valor": valor,
                "status": "registered",
            }
            await db.schema("analytics_v2").table("fato_compras").insert(row).execute()
            table = "fato_compras"
            pk_field = "compra_id"
        else:
            record_id = str(uuid4())
            row = {
                "transacao_id": record_id,
                "client_id": client_id,
                "data_competencia_id": data_competencia_id,
                "customer_id": dim_customer_id,
                "fornecedor_id": dim_fornecedor_id,
                "produto_id": dim_produto_id,
                "documento": documento,
                "quantidade": quantidade,
                "valor_unitario": valor_unitario,
                "valor": valor,
                "status": "registered",
                "tipo_transacao": tipo_transacao.strip(),
            }
            await db.schema("analytics_v2").table("fato_transacoes").insert(row).execute()
            table = "fato_transacoes"
            pk_field = "transacao_id"

        logger.info(
            "[Context] Transação registrada: %s=%s tipo=%s valor=%s cliente=%s",
            pk_field, record_id, tipo_transacao, valor, client_id,
        )
        return {
            pk_field: record_id,
            "table": table,
            "tipo_transacao": tipo_transacao,
            "valor": valor,
            "data": data,
            "data_competencia_id": data_competencia_id,
            "client_id_dim": dim_customer_id,
            "fornecedor_id_dim": dim_fornecedor_id,
            "produto_id_dim": dim_produto_id,
            "message": f"Transação registrada em {table} com sucesso.",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro ao registrar transação: %s", e)
        raise ToolError(f"Erro ao registrar transação: {e}")


# ---------------------------------------------------------------------------
# list_data_sources
# ---------------------------------------------------------------------------


async def _list_data_sources_logic(
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    Return an overview of data already ingested for this client.

    Queries analytics_v2 fact and dimension tables to surface row counts and
    the most recent ingestion job recorded in reg_jobs.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    try:
        db = get_supabase_client()
        schema = db.schema("analytics_v2")

        # Row counts per table (each count is a separate lightweight query)
        async def _count(table: str, fk: str = "client_id") -> int:
            result = (
                await schema.table(table)
                .select(fk, count="exact")
                .eq(fk, client_id)
                .limit(0)
                .execute()
            )
            return result.count or 0

        counts = {
            "fato_transacoes": await _count("fato_transacoes"),
            "fato_compras": await _count("fato_compras"),
            "dim_clientes": await _count("dim_clientes"),
            "dim_fornecedores": await _count("dim_fornecedores"),
            "dim_inventory": await _count("dim_inventory"),
        }

        # Most recent ingestion jobs
        jobs_result = (
            await schema.table("reg_jobs")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        recent_jobs = jobs_result.data or []

        logger.info("[Context] list_data_sources para %s: %s", client_id, counts)
        return {
            "row_counts": counts,
            "recent_ingestion_jobs": recent_jobs,
            "summary": (
                f"{counts['fato_transacoes']} transações, "
                f"{counts['fato_compras']} compras, "
                f"{counts['dim_clientes']} clientes, "
                f"{counts['dim_fornecedores']} fornecedores, "
                f"{counts['dim_inventory']} produtos."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro ao listar fontes de dados: %s", e)
        raise ToolError(f"Erro ao listar fontes de dados: {e}")


# ---------------------------------------------------------------------------
# query_data_catalog
# ---------------------------------------------------------------------------


async def _query_data_catalog_logic(
    ctx: Context,
    source_id: str | None = None,
    resource_type: str | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Query the client's data catalog: what spreadsheets/files are registered,
    their column-mapping status, and ingestion quality.

    Args:
        source_id: UUID of a specific client_data_sources row. When provided,
            returns full detail for that source (including sample data and
            per-column confidence scores). When omitted, returns a summary
            list of all sources.
        resource_type: Filter by resource type (e.g. "spreadsheet", "csv",
            "database"). Case-insensitive partial match.

    Returns a catalog view with:
      - sources: list of registered data sources with mapping health
      - Each source exposes: storage_location, source_type, resource_type,
        sync_status, last_synced_at, detected_entity_context,
        mapped_columns (canonical → source), unmapped_columns,
        needs_review_columns, ingestion_quality
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    try:
        db = get_supabase_client()

        if source_id:
            # Full detail for a single source
            result = (
                await db.table("client_data_sources")
                .select(
                    "id, source_type, resource_type, storage_type, storage_location, "
                    "sync_status, last_synced_at, detected_entity_context, "
                    "column_mapping, auto_column_mapping, unmapped_columns, "
                    "needs_review_columns, match_confidence, ingestion_quality, "
                    "ignored_columns, is_auto_generated, reviewed_at, "
                    "user_column_changes, watermark_column, last_watermark_value, "
                    "source_columns, created_at, updated_at"
                )
                .eq("client_id", client_id)
                .eq("id", source_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                raise ToolError(f"Fonte de dados não encontrada: {source_id}")

            row = result.data
            return {
                "source": _format_source_detail(row),
            }

        # Summary list — all sources for this client
        query = (
            db.table("client_data_sources")
            .select(
                "id, source_type, resource_type, storage_type, storage_location, "
                "sync_status, last_synced_at, detected_entity_context, "
                "column_mapping, unmapped_columns, needs_review_columns, "
                "ingestion_quality, is_auto_generated, reviewed_at, created_at"
            )
            .eq("client_id", client_id)
            .order("updated_at", desc=True)
        )
        if resource_type:
            query = query.ilike("resource_type", f"%{resource_type}%")

        result = await query.execute()
        rows = result.data or []

        sources = [_format_source_summary(r) for r in rows]
        total = len(sources)
        needs_review_count = sum(1 for s in sources if s["needs_review_count"] > 0)
        unmapped_count = sum(1 for s in sources if s["unmapped_count"] > 0)

        logger.info("[Context] query_data_catalog para %s: %d fontes", client_id, total)
        return {
            "total_sources": total,
            "needs_review_count": needs_review_count,
            "unmapped_count": unmapped_count,
            "sources": sources,
            "summary": (
                f"{total} fonte(s) registrada(s). "
                f"{needs_review_count} com colunas pendentes de revisão. "
                f"{unmapped_count} com colunas não mapeadas."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro ao consultar catálogo: %s", e)
        raise ToolError(f"Erro ao consultar catálogo de dados: {e}")


def _format_source_summary(row: dict) -> dict:
    column_mapping = row.get("column_mapping") or {}
    unmapped = row.get("unmapped_columns") or []
    needs_review = row.get("needs_review_columns") or []
    quality = row.get("ingestion_quality") or {}

    return {
        "id": row["id"],
        "storage_location": row.get("storage_location"),
        "source_type": row.get("source_type"),
        "resource_type": row.get("resource_type"),
        "sync_status": row.get("sync_status"),
        "last_synced_at": row.get("last_synced_at"),
        "detected_entity_context": row.get("detected_entity_context"),
        "is_reviewed": row.get("reviewed_at") is not None,
        "mapped_count": len(column_mapping),
        "unmapped_count": len(unmapped) if isinstance(unmapped, list) else 0,
        "needs_review_count": len(needs_review) if isinstance(needs_review, list) else 0,
        "mapped_columns": column_mapping,
        "unmapped_columns": unmapped,
        "needs_review_columns": needs_review,
        "ingestion_quality": quality,
        "created_at": row.get("created_at"),
    }


def _format_source_detail(row: dict) -> dict:
    base = _format_source_summary(row)
    base.update({
        "auto_column_mapping": row.get("auto_column_mapping") or {},
        "user_column_changes": row.get("user_column_changes") or {},
        "match_confidence": row.get("match_confidence") or {},
        "ignored_columns": row.get("ignored_columns") or [],
        "is_auto_generated": row.get("is_auto_generated"),
        "reviewed_at": row.get("reviewed_at"),
        "watermark_column": row.get("watermark_column"),
        "last_watermark_value": row.get("last_watermark_value"),
        "source_columns": row.get("source_columns") or [],
    })
    return base


# ---------------------------------------------------------------------------
# suggest_column_mapping
# ---------------------------------------------------------------------------


async def _suggest_column_mapping_logic(
    source_id: str,
    ctx: Context,
    schema_type: str = "invoices",
    client_id: str | None = None,
) -> dict:
    """
    Suggest canonical-field mappings for a registered data source by calling
    the match-columns edge function.

    Args:
        source_id: UUID of the client_data_sources row whose source_columns
            should be matched.
        schema_type: Target schema to match against — one of "invoices",
            "fato_transacoes", "dim_clientes", "dim_inventory".
            Defaults to "invoices" (the broadest alias set).

    Returns the match-columns response: matched (canonical→source),
    unmatched (source columns with no good match), needs_review (low-confidence
    candidates), confidence_scores, and detected_context.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")
    if not source_id:
        raise ToolError("source_id é obrigatório.")
    if not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY:
        raise ToolError("SUPABASE_URL / SUPABASE_SERVICE_KEY não configurados.")

    try:
        db = get_supabase_client()

        # Read source_columns from client_data_sources
        ds_result = (
            await db.table("client_data_sources")
            .select("id, source_columns, storage_location")
            .eq("client_id", client_id)
            .eq("id", source_id)
            .maybe_single()
            .execute()
        )
        if not ds_result.data:
            raise ToolError(f"Fonte de dados não encontrada: {source_id}")

        source_columns: list[str] = ds_result.data.get("source_columns") or []
        if not source_columns:
            raise ToolError(
                "Esta fonte de dados não tem source_columns registrados. "
                "Execute a sincronização primeiro para descobrir as colunas."
            )

        # Call match-columns edge function
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{_SUPABASE_URL}/functions/v1/match-columns",
                json={
                    "source_columns": source_columns,
                    "schema_type": schema_type,
                    "client_id": client_id,
                },
                headers={
                    "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            match_result = response.json()

        logger.info(
            "[Context] suggest_column_mapping: source_id=%s matched=%d unmatched=%d",
            source_id,
            len(match_result.get("matched", {})),
            len(match_result.get("unmatched", [])),
        )
        return {
            "source_id": source_id,
            "storage_location": ds_result.data.get("storage_location"),
            "matched": match_result.get("matched", {}),
            "unmatched": match_result.get("unmatched", []),
            "needs_review": match_result.get("needs_review", []),
            "confidence_scores": match_result.get("confidence_scores", {}),
            "detected_context": match_result.get("detected_context"),
        }

    except ToolError:
        raise
    except httpx.HTTPStatusError as exc:
        logger.error("[Context] match-columns HTTP %s: %s", exc.response.status_code, exc.response.text)
        raise ToolError(f"Erro ao chamar match-columns: HTTP {exc.response.status_code}")
    except Exception as e:
        logger.exception("[Context] Erro em suggest_column_mapping: %s", e)
        raise ToolError(f"Erro ao sugerir mapeamento de colunas: {e}")


# ---------------------------------------------------------------------------
# update_schema_mapping
# ---------------------------------------------------------------------------


async def _update_schema_mapping_logic(
    source_id: str,
    confirmed_mapping: dict,
    ctx: Context,
    ignored_columns: list | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Persist a user-confirmed column mapping to client_data_sources.

    Args:
        source_id: UUID of the client_data_sources row to update.
        confirmed_mapping: Dict of {canonical_field: source_column} pairs that
            the user has confirmed. This becomes the authoritative column_mapping.
        ignored_columns: List of source column names to explicitly ignore during
            ingestion (not mapped, not flagged as unmatched).

    Updates column_mapping, sets reviewed_at, computes unmapped_columns as
    the remaining unmatched columns (source_columns minus confirmed minus ignored).
    Tracks user changes against auto_column_mapping in user_column_changes.

    IMPORTANT: always present the full mapping table to the user and receive
    explicit confirmation before calling this tool.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")
    if not source_id:
        raise ToolError("source_id é obrigatório.")
    if not confirmed_mapping or not isinstance(confirmed_mapping, dict):
        raise ToolError("confirmed_mapping é obrigatório e deve ser um dicionário não vazio.")

    try:
        db = get_supabase_client()

        # Read current state to compute diffs
        ds_result = (
            await db.table("client_data_sources")
            .select("id, source_columns, auto_column_mapping, storage_location")
            .eq("client_id", client_id)
            .eq("id", source_id)
            .maybe_single()
            .execute()
        )
        if not ds_result.data:
            raise ToolError(f"Fonte de dados não encontrada: {source_id}")

        row = ds_result.data
        source_columns: list[str] = row.get("source_columns") or []
        auto_mapping: dict = row.get("auto_column_mapping") or {}
        ignored: list[str] = ignored_columns or []

        # Columns that are neither confirmed nor ignored
        mapped_source_values = set(confirmed_mapping.values())
        unmapped = [c for c in source_columns if c not in mapped_source_values and c not in ignored]

        # Diff against auto_column_mapping to record what the user changed
        user_changes: dict = {}
        for canonical, source_col in confirmed_mapping.items():
            auto_val = auto_mapping.get(canonical)
            if auto_val != source_col:
                user_changes[canonical] = {"auto": auto_val, "confirmed": source_col}

        now = datetime.now(tz=UTC).isoformat()
        update_payload = {
            "column_mapping": confirmed_mapping,
            "unmapped_columns": unmapped,
            "ignored_columns": ignored,
            "reviewed_at": now,
            "user_column_changes": user_changes,
            "updated_at": now,
        }

        await (
            db.table("client_data_sources")
            .update(update_payload)
            .eq("client_id", client_id)
            .eq("id", source_id)
            .execute()
        )

        logger.info(
            "[Context] update_schema_mapping: source_id=%s mapped=%d unmapped=%d",
            source_id, len(confirmed_mapping), len(unmapped),
        )
        return {
            "source_id": source_id,
            "storage_location": row.get("storage_location"),
            "column_mapping": confirmed_mapping,
            "unmapped_columns": unmapped,
            "ignored_columns": ignored,
            "user_changes_count": len(user_changes),
            "message": (
                f"Mapeamento salvo: {len(confirmed_mapping)} coluna(s) confirmada(s), "
                f"{len(unmapped)} não mapeada(s), {len(ignored)} ignorada(s). "
                "O Data Analyst já pode consultar esta fonte."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro em update_schema_mapping: %s", e)
        raise ToolError(f"Erro ao salvar mapeamento: {e}")


# ---------------------------------------------------------------------------
# get_knowledge_status
# ---------------------------------------------------------------------------


async def _get_knowledge_status_logic(
    ctx: Context,
    agent_slug: str | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Return the knowledge completeness status for this client.

    Args:
        agent_slug: When provided, filters document types to those consumed
            by this agent and surfaces requirement thresholds from
            knowledge_agent_requirements. Pass the calling agent's slug
            (e.g. "data-analyst") so the result is immediately actionable.
            Omit to get a full cross-agent view.

    Returns a completeness_score (0–1 weighted average), per-document status,
    and lists of missing required documents and documents below threshold.
    Call this at session start to orient what context is already available.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    try:
        db = get_supabase_client()

        # 1. Document types — all, or filtered by consumed_by
        types_result = (
            await db.table("knowledge_document_types")
            .select("id, name, fields, status, coverage_weight, domain_id, consumed_by")
            .order("sort_order")
            .execute()
        )
        all_types: list[dict] = types_result.data or []

        if agent_slug:
            all_types = [
                t for t in all_types
                if agent_slug in (t.get("consumed_by") or [])
                or "all" in (t.get("consumed_by") or [])
            ]

        # 2. Requirements for this agent (thresholds)
        requirements: dict[str, dict] = {}
        if agent_slug:
            req_result = (
                await db.table("knowledge_agent_requirements")
                .select("document_type_id, requirement_type, coverage_threshold")
                .eq("agent_slug", agent_slug)
                .execute()
            )
            requirements = {r["document_type_id"]: r for r in (req_result.data or [])}

        # 3. Existing client knowledge documents
        kd_result = (
            await db.table("client_knowledge_documents")
            .select("document_type_id, status, field_coverage, vector_document_id, updated_at")
            .eq("client_id", client_id)
            .execute()
        )
        kd_map: dict[str, dict] = {r["document_type_id"]: r for r in (kd_result.data or [])}

        # 4. Build per-type status
        docs: list[dict] = []
        total_weight = 0.0
        covered_weight = 0.0
        missing_required: list[str] = []
        needs_attention: list[str] = []

        for doc_type in all_types:
            type_id = doc_type["id"]
            expected_fields: list[str] = doc_type.get("fields") or []
            weight = float(doc_type.get("coverage_weight") or 1.0)
            existing = kd_map.get(type_id)
            req = requirements.get(type_id)

            field_coverage: dict = (existing or {}).get("field_coverage") or {}

            if expected_fields:
                cov_values = [float(field_coverage.get(f, 0.0)) for f in expected_fields]
                avg_coverage = sum(cov_values) / len(cov_values)
            else:
                avg_coverage = 1.0 if existing else 0.0

            threshold = float((req or {}).get("coverage_threshold") or 0.7)
            meets_threshold = avg_coverage >= threshold
            total_weight += weight
            covered_weight += weight * avg_coverage

            entry: dict = {
                "document_type_id": type_id,
                "name": doc_type["name"],
                "domain_id": doc_type.get("domain_id"),
                "status": (existing or {}).get("status", "missing"),
                "coverage_score": round(avg_coverage, 3),
                "field_coverage": field_coverage,
                "vector_document_id": (existing or {}).get("vector_document_id"),
                "updated_at": (existing or {}).get("updated_at"),
            }
            if req:
                entry["requirement_type"] = req["requirement_type"]
                entry["coverage_threshold"] = threshold
                entry["meets_threshold"] = meets_threshold

            status = entry["status"]
            req_type = (req or {}).get("requirement_type")
            if status == "missing" and req_type == "minimum":
                missing_required.append(type_id)
            elif not meets_threshold and req_type == "minimum":
                needs_attention.append(type_id)

            docs.append(entry)

        overall = round(covered_weight / total_weight, 3) if total_weight > 0 else 0.0

        logger.info(
            "[Context] get_knowledge_status client=%s agent=%s score=%.2f missing=%d",
            client_id, agent_slug, overall, len(missing_required),
        )
        return {
            "completeness_score": overall,
            "total_types_checked": len(docs),
            "missing_required": missing_required,
            "needs_attention": needs_attention,
            "documents": docs,
            "summary": (
                f"Completeness: {overall:.0%}. "
                f"{len(missing_required)} required document(s) missing. "
                f"{len(needs_attention)} below threshold."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro em get_knowledge_status: %s", e)
        raise ToolError(f"Erro ao consultar status de conhecimento: {e}")


# ---------------------------------------------------------------------------
# update_context_document
# ---------------------------------------------------------------------------


async def _update_context_document_logic(
    document_type_id: str,
    field_updates: dict,
    ctx: Context,
    metadata_updates: dict | None = None,
    vector_document_id: str | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Upsert a client_knowledge_documents row, merging new knowledge into the
    existing field_coverage without overwriting already-filled fields.

    Args:
        document_type_id: ID from knowledge_document_types (e.g. "perfil_operador",
            "mapa_dados", "vocabulario_negocio", "perfil_empresarial").
        field_updates: Dict mapping field names to coverage scores (0.0–1.0).
            Example: {"fontes_dados": 0.8, "relacionamentos": 0.4}.
            Merged on top of existing coverage — higher values win.
        metadata_updates: Optional free-form dict merged into the metadata JSONB.
            Use for human-readable content: {"setor": "distribuição", ...}.
        vector_document_id: UUID of the vector_db.documents row if this update
            was triggered by a document write.

    This tool is internal bookkeeping — call it whenever a conversation reveals
    new information about the client. No user confirmation needed.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")
    if not document_type_id:
        raise ToolError("document_type_id é obrigatório.")
    if not field_updates or not isinstance(field_updates, dict):
        raise ToolError("field_updates deve ser um dicionário não vazio.")

    try:
        db = get_supabase_client()

        # Validate document type and get expected fields
        type_result = (
            await db.table("knowledge_document_types")
            .select("id, name, fields")
            .eq("id", document_type_id)
            .maybe_single()
            .execute()
        )
        if not type_result.data:
            raise ToolError(f"Tipo de documento desconhecido: '{document_type_id}'.")

        doc_type = type_result.data
        expected_fields: list[str] = doc_type.get("fields") or []

        # Read current state
        existing_result = (
            await db.table("client_knowledge_documents")
            .select("id, field_coverage, metadata, status")
            .eq("client_id", client_id)
            .eq("document_type_id", document_type_id)
            .maybe_single()
            .execute()
        )
        existing = existing_result.data

        # Merge — new values overwrite only what's explicitly passed
        current_coverage: dict = (existing or {}).get("field_coverage") or {}
        merged_coverage = {**current_coverage, **{
            k: float(v) for k, v in field_updates.items()
        }}

        # Compute status from merged coverage
        if expected_fields:
            cov_values = [merged_coverage.get(f, 0.0) for f in expected_fields]
            avg = sum(cov_values) / len(cov_values)
        else:
            avg = 1.0 if merged_coverage else 0.0

        if avg == 0.0:
            status = "missing"
        elif avg >= 0.7:
            status = "present"
        else:
            status = "partial"

        # Merge metadata
        current_meta: dict = (existing or {}).get("metadata") or {}
        merged_meta = {**current_meta, **(metadata_updates or {})}

        now = datetime.now(tz=UTC).isoformat()
        payload = {
            "client_id": client_id,
            "document_type_id": document_type_id,
            "status": status,
            "field_coverage": merged_coverage,
            "metadata": merged_meta,
            "updated_at": now,
        }
        if vector_document_id:
            payload["vector_document_id"] = vector_document_id
            payload["source"] = "agent"

        if existing:
            await (
                db.table("client_knowledge_documents")
                .update(payload)
                .eq("client_id", client_id)
                .eq("document_type_id", document_type_id)
                .execute()
            )
        else:
            await db.table("client_knowledge_documents").insert(payload).execute()

        logger.info(
            "[Context] update_context_document: client=%s type=%s status=%s score=%.2f",
            client_id, document_type_id, status, avg,
        )
        return {
            "document_type_id": document_type_id,
            "name": doc_type["name"],
            "status": status,
            "coverage_score": round(avg, 3),
            "field_coverage": merged_coverage,
            "message": f"{doc_type['name']} atualizado: {status} ({avg:.0%} de cobertura).",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception("[Context] Erro em update_context_document: %s", e)
        raise ToolError(f"Erro ao atualizar documento de contexto: {e}")


# ---------------------------------------------------------------------------
# Module registration
# ---------------------------------------------------------------------------


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Context."""

    mcp.tool(
        name="register_transaction",
        description=(
            "Register a business transaction (sale, purchase, or expense) into analytics_v2. "
            "Parameters: tipo_transacao (string, required — e.g. 'venda', 'compra', 'despesa'), "
            "valor (number, required — total value), data (string, required — YYYY-MM-DD), "
            "cliente_nome (string, optional — for sales), "
            "fornecedor_nome (string, optional — for purchases/expenses), "
            "produto_nome (string, optional), quantidade (number, optional), "
            "valor_unitario (number, optional), documento (string, optional — NF or reference). "
            "Vendas/despesas go to fato_transacoes; compras go to fato_compras. "
            "IMPORTANT: always present a confirmation summary to the user BEFORE calling this tool."
        ),
    )(mcp_inject_client_id(get_context_service)(_register_transaction_logic))

    mcp.tool(
        name="list_data_sources",
        description=(
            "Return an overview of data already ingested for this client: "
            "row counts for fato_transacoes, fato_compras, dim_clientes, "
            "dim_fornecedores, and dim_inventory, plus the 10 most recent "
            "ingestion jobs from reg_jobs. Use to answer 'what data do we have?' "
            "and to orient schema-mapping conversations."
        ),
    )(mcp_inject_client_id(get_context_service)(_list_data_sources_logic))

    mcp.tool(
        name="query_data_catalog",
        description=(
            "Query the client's data catalog: registered spreadsheets/files, "
            "their column-mapping health, and ingestion quality. "
            "Parameters: source_id (UUID, optional — get full detail for one source), "
            "resource_type (string, optional — filter by type, e.g. 'spreadsheet'). "
            "Returns mapped_columns (canonical→source), unmapped_columns, "
            "needs_review_columns, detected_entity_context, sync_status, and ingestion_quality. "
            "Use before suggest_column_mapping to understand what is already mapped "
            "and what still needs attention."
        ),
    )(mcp_inject_client_id(get_context_service)(_query_data_catalog_logic))

    mcp.tool(
        name="suggest_column_mapping",
        description=(
            "Suggest canonical-field mappings for a registered data source by calling "
            "the match-columns engine. "
            "Parameters: source_id (UUID, required — from query_data_catalog), "
            "schema_type (string, optional — 'invoices' | 'fato_transacoes' | "
            "'dim_clientes' | 'dim_inventory'; defaults to 'invoices'). "
            "Returns matched (canonical→source), unmatched, needs_review (low-confidence "
            "candidates), confidence_scores, and detected_context. "
            "Always call query_data_catalog first to confirm source_columns exist."
        ),
    )(mcp_inject_client_id(get_context_service)(_suggest_column_mapping_logic))

    mcp.tool(
        name="update_schema_mapping",
        description=(
            "Persist a user-confirmed column mapping to client_data_sources. "
            "Parameters: source_id (UUID, required), "
            "confirmed_mapping (object, required — {canonical_field: source_column}), "
            "ignored_columns (array of strings, optional — columns to skip during ingestion). "
            "Sets reviewed_at, computes unmapped_columns, and records user changes vs auto-mapping. "
            "IMPORTANT: always present the full mapping table and receive explicit confirmation "
            "before calling this tool."
        ),
    )(mcp_inject_client_id(get_context_service)(_update_schema_mapping_logic))

    mcp.tool(
        name="get_knowledge_status",
        description=(
            "Return the knowledge completeness status for this client across all document types. "
            "Parameters: agent_slug (string, optional — filter by what this agent needs and surface "
            "coverage thresholds; e.g. 'data-analyst', 'knowledge-assistant'). "
            "Returns completeness_score (0–1), missing_required (document type IDs), "
            "needs_attention (below threshold), and per-document field_coverage. "
            "Call at session start to orient what context is already available before querying or writing."
        ),
    )(mcp_inject_client_id(get_context_service)(_get_knowledge_status_logic))

    mcp.tool(
        name="update_context_document",
        description=(
            "Upsert a client_knowledge_documents row, merging new field coverage without overwriting existing. "
            "Parameters: document_type_id (string, required — e.g. 'perfil_operador', 'mapa_dados', "
            "'vocabulario_negocio', 'perfil_empresarial'), "
            "field_updates (object, required — {field_name: coverage_score 0.0–1.0}), "
            "metadata_updates (object, optional — human-readable content merged into metadata JSONB), "
            "vector_document_id (UUID string, optional — links to a vector_db.documents row). "
            "Call whenever a conversation reveals new information about the client. "
            "No user confirmation needed — this is internal bookkeeping."
        ),
    )(mcp_inject_client_id(get_context_service)(_update_context_document_logic))

    registered = [
        "register_transaction",
        "list_data_sources",
        "query_data_catalog",
        "suggest_column_mapping",
        "update_schema_mapping",
        "get_knowledge_status",
        "update_context_document",
    ]
    logger.info("[Context Module] Tools registered: %s", registered)
    return registered
