# tool_pool_api/server/tool_modules/rfq_module.py
"""
Módulo RFQ (Request for Quotation) - Ferramentas de cotação e compras

Tools for the RFQ Agent: parsing buying lists, dispatching RFQs,
collecting responses, optimizing allocation, and generating POs.

**Architecture**:
- All DB operations via Supabase service_role client
- client_id injected by middleware, never in prompts
- session_id from lifespan context for scoping RFQ data

**Security**:
- client_id: Injected server-side via mcp_inject_cliente_id
- RLS on all tables ensures tenant isolation
- PO creation/approval requires explicit confirmation
"""

import json
import logging
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.dependencies import get_context_service
from vizu_agent_framework.approval import (
    ApprovalEngine,
    ApprovalError,
    resolve_policy,
)
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_elicitation_service.exceptions import ElicitationRequired
from vizu_google_suite_client import GoogleSheetsClient
from vizu_models import ElicitationOption, ElicitationType
from vizu_supabase_client import get_supabase_client

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# PARSE & VALIDATE
# =============================================================================


async def _parse_buying_list_logic(
    ctx: Context,
    raw_text: str | None = None,
    file_id: str | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    Parse a buying list from raw text or uploaded CSV/XLSX into structured items.

    Args:
        raw_text: Free-text or CSV-formatted buying list typed by user.
                  Each line: item name, quantity, and optionally specs.
                  Example: "Parafuso M6, 500, aço inox\\nPorca M6, 500"
        file_id: UUID of a previously uploaded CSV/XLSX file.
                 If provided, raw_text is ignored.

    Returns:
        dict with items, warnings, total_items
    """
    items: list[dict] = []
    warnings: list[str] = []

    if file_id:
        try:
            db = get_supabase_client()
            file_result = db.table("uploaded_files_metadata").select(
                "file_name,storage_path,parsed_data"
            ).eq("id", file_id).maybe_single().execute()

            file_data = file_result.data
            if not file_data:
                raise ToolError(f"Arquivo não encontrado: {file_id}")

            parsed = file_data.get("parsed_data")
            if parsed and isinstance(parsed, dict):
                rows = parsed.get("rows") or parsed.get("data") or []
                columns = parsed.get("columns") or []
                items = _extract_items_from_rows(rows, columns)
            else:
                warnings.append(
                    f"Arquivo {file_data['file_name']} sem dados parseados. "
                    "Tente enviar a lista como texto."
                )
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"[RFQ] Failed to load file {file_id}: {e}")
            raise ToolError(f"Erro ao carregar arquivo: {e}")

    elif raw_text:
        items, parse_warnings = _parse_text_to_items(raw_text)
        warnings.extend(parse_warnings)

    else:
        raise ToolError(
            "Forneça raw_text (lista digitada) ou file_id (arquivo enviado)."
        )

    logger.info(f"[RFQ] Parsed {len(items)} items, {len(warnings)} warnings")

    return {
        "items": items,
        "warnings": warnings,
        "total_items": len(items),
    }


def _parse_text_to_items(text: str) -> tuple[list[dict], list[str]]:
    """Parse free-text buying list into structured items."""
    items: list[dict] = []
    warnings: list[str] = []
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    for i, line in enumerate(lines, 1):
        # Try comma/semicolon/tab separation
        parts: list[str] = []
        for sep in ["\t", ";", ","]:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 2:
                break
        else:
            parts = [line]

        item: dict = {
            "name": parts[0] if parts else line,
            "sku": "",
            "qty": 0,
            "specs": "",
            "unit": "un",
        }

        if len(parts) >= 2:
            try:
                item["qty"] = int(
                    parts[1].replace(".", "").replace(",", "").strip()
                )
            except ValueError:
                item["specs"] = parts[1]
                warnings.append(
                    f"Linha {i}: quantidade não reconhecida em '{parts[1]}'"
                )

        if len(parts) >= 3:
            item["specs"] = parts[2]

        if len(parts) >= 4:
            item["unit"] = parts[3]

        if item["qty"] <= 0:
            warnings.append(
                f"Linha {i} ({item['name']}): quantidade zerada ou ausente"
            )

        items.append(item)

    return items, warnings


def _extract_items_from_rows(
    rows: list[dict], columns: list[str]
) -> list[dict]:
    """Extract structured items from parsed CSV rows."""
    items: list[dict] = []
    name_col = _find_column(columns, ["nome", "item", "produto", "name", "description", "descricao", "material"])
    qty_col = _find_column(columns, ["qtd", "qty", "quantidade", "quantity", "quant"])
    sku_col = _find_column(columns, ["sku", "codigo", "cod", "code", "ref"])
    specs_col = _find_column(columns, ["specs", "especificacao", "spec", "detalhe", "obs"])
    unit_col = _find_column(columns, ["unidade", "unit", "un", "uom"])

    for row in rows:
        item = {
            "name": str(row.get(name_col, "")) if name_col else str(list(row.values())[0]) if row else "",
            "sku": str(row.get(sku_col, "")) if sku_col else "",
            "qty": 0,
            "specs": str(row.get(specs_col, "")) if specs_col else "",
            "unit": str(row.get(unit_col, "un")) if unit_col else "un",
        }
        if qty_col and row.get(qty_col):
            try:
                item["qty"] = int(float(str(row[qty_col]).replace(",", ".")))
            except (ValueError, TypeError):
                pass
        items.append(item)

    return items


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    """Find best matching column name from candidates."""
    cols_lower = {c.lower().strip(): c for c in columns}
    for candidate in candidates:
        if candidate in cols_lower:
            return cols_lower[candidate]
    return None


async def _validate_buying_list_logic(
    ctx: Context,
    items: list[dict],
    cliente_id: str | None = None,
) -> dict:
    """
    Validate a parsed buying list for completeness and correctness.

    Args:
        items: List of item dicts from parse_buying_list.
               Each should have: name, qty. Optional: sku, specs, unit.

    Returns:
        dict with valid, errors, warnings, cleaned_items
    """
    errors: list[str] = []
    warnings: list[str] = []
    cleaned: list[dict] = []

    if not items:
        return {
            "valid": False,
            "errors": ["Lista vazia. Adicione itens."],
            "warnings": [],
            "cleaned_items": [],
        }

    seen_names: set[str] = set()
    for i, item in enumerate(items, 1):
        name = str(item.get("name", "")).strip()
        qty = item.get("qty", 0)

        if not name:
            errors.append(f"Item {i}: nome obrigatório")
            continue

        if name.lower() in seen_names:
            warnings.append(f"Item {i} ({name}): duplicado na lista")
        seen_names.add(name.lower())

        if not isinstance(qty, (int, float)) or qty <= 0:
            errors.append(f"Item {i} ({name}): quantidade deve ser > 0")
            continue

        cleaned.append({
            "name": name,
            "sku": str(item.get("sku", "")).strip(),
            "qty": int(qty),
            "specs": str(item.get("specs", "")).strip(),
            "unit": str(item.get("unit", "un")).strip(),
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "cleaned_items": cleaned,
    }


# =============================================================================
# SUPPLIER MANAGEMENT
# =============================================================================


async def _list_suppliers_logic(
    ctx: Context,
    category: str | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    List available suppliers for the current tenant.

    Args:
        category: Optional category filter (e.g., "alimentos", "construção").

    Returns:
        dict with suppliers list and total count
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()
        query = db.table("supplier_roster").select(
            "id,name,contact_email,contact_phone,categories"
        ).eq("client_id", cliente_id).eq("is_active", True)

        if category:
            query = query.contains("categories", [category])

        result = query.execute()
        suppliers = result.data or []

        return {
            "suppliers": suppliers,
            "total": len(suppliers),
        }
    except Exception as e:
        logger.error(f"[RFQ] Failed to list suppliers: {e}")
        raise ToolError(f"Erro ao listar fornecedores: {e}")


# =============================================================================
# RFQ DISPATCH & RESPONSE
# =============================================================================


async def _dispatch_rfq_logic(
    ctx: Context,
    supplier_id: str,
    items: list[dict],
    deadline: str | None = None,
    cliente_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Send an RFQ to a specific supplier. Creates a record in rfq_requests.

    Phase 1: mock dispatch — record created but no message sent.
    Use submit_mock_response to simulate the supplier reply.

    Args:
        supplier_id: UUID of the supplier from list_suppliers
        items: List of items to quote (from validate_buying_list cleaned_items)
        deadline: ISO date string for response deadline (default: 48h)

    Returns:
        dict with rfq_id, supplier_name, status, items_count, deadline
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    session_id = session_id or ctx.request_context.lifespan_context.get("session_id")

    if not cliente_id or not session_id:
        raise ToolError("Missing cliente_id or session_id in context")

    if not items:
        raise ToolError("Lista de itens vazia. Não é possível enviar cotação.")

    try:
        db = get_supabase_client()

        # Verify supplier belongs to this tenant
        supplier_result = db.table("supplier_roster").select(
            "id,name"
        ).eq("id", supplier_id).eq("client_id", cliente_id).eq(
            "is_active", True
        ).maybe_single().execute()

        supplier = supplier_result.data
        if not supplier:
            raise ToolError(f"Fornecedor não encontrado ou inativo: {supplier_id}")

        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except ValueError:
                raise ToolError(f"Formato de deadline inválido: {deadline}. Use ISO 8601.")
        else:
            deadline_dt = datetime.now(UTC) + timedelta(days=2)

        rfq_id = str(uuid4())

        db.table("rfq_requests").insert({
            "id": rfq_id,
            "session_id": session_id,
            "client_id": cliente_id,
            "supplier_id": supplier_id,
            "items": items,
            "status": "sent",
            "sent_at": datetime.now(UTC).isoformat(),
            "deadline": deadline_dt.isoformat(),
        }).execute()

        logger.info(
            f"[RFQ] Dispatched RFQ {rfq_id} to supplier {supplier['name']} "
            f"({len(items)} items, deadline {deadline_dt.date()})"
        )

        return {
            "rfq_id": rfq_id,
            "supplier_name": supplier["name"],
            "status": "sent",
            "items_count": len(items),
            "deadline": deadline_dt.isoformat(),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to dispatch RFQ: {e}")
        raise ToolError(f"Erro ao enviar cotação: {e}")


async def _check_rfq_responses_logic(
    ctx: Context,
    cliente_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Check the status of all RFQ requests for the current session.

    Returns:
        dict with responses list, total, responded, pending, all_responded
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    session_id = session_id or ctx.request_context.lifespan_context.get("session_id")

    if not cliente_id or not session_id:
        raise ToolError("Missing cliente_id or session_id in context")

    try:
        db = get_supabase_client()

        result = db.table("rfq_requests").select(
            "id,supplier_id,status,response_data,deadline,"
            "supplier_roster(name)"
        ).eq("session_id", session_id).eq("client_id", cliente_id).execute()

        rfqs = result.data or []
        responded_list = [r for r in rfqs if r["status"] == "responded"]
        pending_list = [r for r in rfqs if r["status"] in ("sent", "pending")]

        responses = []
        for rfq in rfqs:
            supplier_info = rfq.get("supplier_roster") or {}
            responses.append({
                "rfq_id": rfq["id"],
                "supplier_name": supplier_info.get("name", "Desconhecido"),
                "status": rfq["status"],
                "response_data": rfq.get("response_data"),
                "deadline": rfq.get("deadline"),
            })

        return {
            "responses": responses,
            "total": len(rfqs),
            "responded": len(responded_list),
            "pending": len(pending_list),
            "all_responded": len(pending_list) == 0 and len(rfqs) > 0,
        }

    except Exception as e:
        logger.error(f"[RFQ] Failed to check responses: {e}")
        raise ToolError(f"Erro ao verificar respostas: {e}")


async def _submit_mock_response_logic(
    ctx: Context,
    rfq_id: str,
    prices: list[dict],
    delivery_days: int = 7,
    payment_terms: str = "30 dias",
    notes: str = "",
    cliente_id: str | None = None,
) -> dict:
    """
    Submit a mock supplier response for testing (Phase 1 only).

    Args:
        rfq_id: UUID of the RFQ to respond to
        prices: List of {name: str, unit_price: float, available: bool}
        delivery_days: Estimated delivery time in days (default: 7)
        payment_terms: Payment terms string (default: "30 dias")
        notes: Additional notes from the supplier

    Returns:
        dict with rfq_id and updated status
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")

    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    if not prices:
        raise ToolError("Lista de preços vazia.")

    try:
        db = get_supabase_client()

        rfq_result = db.table("rfq_requests").select(
            "id,status,items"
        ).eq("id", rfq_id).eq("client_id", cliente_id).maybe_single().execute()

        rfq = rfq_result.data
        if not rfq:
            raise ToolError(f"Cotação não encontrada: {rfq_id}")

        if rfq["status"] == "responded":
            raise ToolError("Esta cotação já foi respondida.")

        response_data = {
            "prices": prices,
            "delivery_days": delivery_days,
            "payment_terms": payment_terms,
            "notes": notes,
            "responded_at": datetime.now(UTC).isoformat(),
        }

        db.table("rfq_requests").update({
            "status": "responded",
            "response_data": response_data,
            "raw_response": json.dumps(response_data, ensure_ascii=False),
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", rfq_id).execute()

        logger.info(f"[RFQ] Mock response submitted for RFQ {rfq_id}")

        return {
            "rfq_id": rfq_id,
            "status": "responded",
            "items_quoted": len(prices),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to submit mock response: {e}")
        raise ToolError(f"Erro ao submeter resposta: {e}")


# =============================================================================
# OPTIMIZATION
# =============================================================================


async def _optimize_allocation_logic(
    ctx: Context,
    max_concentration_pct: int = 60,
    prefer_fastest_delivery: bool = False,
    max_delivery_days: int | None = None,
    required_payment_terms: str | None = None,
    enforce_moq: bool = True,
    cliente_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Optimize item allocation across suppliers based on collected quotes.

    Algorithm:
    1. For each item, find cheapest available supplier
    2. Apply constraints: MOQ, delivery window, payment terms
    3. Allocate to cheapest, respecting the concentration cap
    4. If cap exceeded, redistribute lowest-variance items to 2nd cheapest

    Args:
        max_concentration_pct: Max % of total order value per supplier (default 60)
        prefer_fastest_delivery: Prefer faster delivery over cheapest price
        max_delivery_days: Maximum acceptable delivery time in days (None = no limit)
        required_payment_terms: Required payment terms filter (e.g. "30 dias", "60 dias")
        enforce_moq: Whether to enforce supplier minimum order quantities (default True)

    Returns:
        dict with allocations, summary, rationale, unallocated, constraint_warnings
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    session_id = session_id or ctx.request_context.lifespan_context.get("session_id")

    if not cliente_id or not session_id:
        raise ToolError("Missing cliente_id or session_id in context")

    try:
        db = get_supabase_client()

        rfqs_result = db.table("rfq_requests").select(
            "id,supplier_id,items,response_data,"
            "supplier_roster(id,name)"
        ).eq("session_id", session_id).eq("client_id", cliente_id).eq(
            "status", "responded"
        ).execute()

        rfqs = rfqs_result.data or []

        if not rfqs:
            raise ToolError(
                "Nenhuma resposta de fornecedor disponível. "
                "Aguarde as respostas ou use submit_mock_response para teste."
            )

        # Build price matrix: item_name -> [quotes]
        price_matrix: dict[str, list[dict]] = {}
        supplier_names: dict[str, str] = {}

        for rfq in rfqs:
            supplier_info = rfq.get("supplier_roster") or {}
            supplier_id = rfq["supplier_id"]
            supplier_name = supplier_info.get("name", supplier_id)
            supplier_names[supplier_id] = supplier_name

            response = rfq.get("response_data") or {}
            prices = response.get("prices", [])
            delivery_days = response.get("delivery_days", 999)

            original_items = rfq.get("items", [])
            for price_entry in prices:
                item_name = price_entry.get("name", "")
                if not item_name:
                    continue

                if item_name not in price_matrix:
                    price_matrix[item_name] = []

                qty = 0
                for orig_item in original_items:
                    if orig_item.get("name", "").lower() == item_name.lower():
                        qty = orig_item.get("qty", 0)
                        break

                price_matrix[item_name].append({
                    "supplier_id": supplier_id,
                    "supplier_name": supplier_name,
                    "unit_price": float(price_entry.get("unit_price", 0)),
                    "available": price_entry.get("available", True),
                    "delivery_days": delivery_days,
                    "payment_terms": response.get("payment_terms", ""),
                    "moq": int(price_entry.get("moq", 0)),
                    "qty": qty,
                })

        # ---- Phase 2: Load supplier MOQ/metadata from roster ----
        supplier_meta: dict[str, dict] = {}
        roster_ids = list(supplier_names.keys())
        if roster_ids:
            roster_result = db.table("supplier_roster").select(
                "id,moq_rules,payment_terms,delivery_days_avg"
            ).in_("id", roster_ids).execute()
            for row in (roster_result.data or []):
                supplier_meta[row["id"]] = row

        # ---- Phase 2: Constraint filtering & warnings ----
        constraint_warnings: list[str] = []

        for item_name, quotes in price_matrix.items():
            for q in quotes:
                sid = q["supplier_id"]
                s_meta = supplier_meta.get(sid, {})

                # Delivery constraint
                if max_delivery_days and q["delivery_days"] > max_delivery_days:
                    q["available"] = False
                    constraint_warnings.append(
                        f"⏱️ {item_name}: {q['supplier_name']} excluído — "
                        f"entrega {q['delivery_days']}d > limite {max_delivery_days}d"
                    )

                # Payment terms constraint
                if required_payment_terms and q.get("payment_terms"):
                    if required_payment_terms.lower() not in q["payment_terms"].lower():
                        q["available"] = False
                        constraint_warnings.append(
                            f"💳 {item_name}: {q['supplier_name']} excluído — "
                            f"prazo '{q['payment_terms']}' ≠ exigido '{required_payment_terms}'"
                        )

                # MOQ constraint (from response or roster)
                if enforce_moq:
                    moq = q.get("moq", 0)
                    # Fallback to roster-level MOQ rules
                    if not moq:
                        moq_rules = s_meta.get("moq_rules") or {}
                        moq = moq_rules.get(item_name, moq_rules.get("default", 0))
                    if moq and q["qty"] < moq:
                        constraint_warnings.append(
                            f"📦 {item_name}: {q['supplier_name']} — "
                            f"qtd solicitada ({q['qty']}) < MOQ ({moq}). "
                            f"Considere ajustar para {moq} unidades."
                        )
                        # Don't exclude, but flag — agent decides

        # Greedy allocation
        allocations: dict[str, list[dict]] = {}
        unallocated: list[str] = []
        rationale_parts: list[str] = []

        for item_name, quotes in price_matrix.items():
            available_quotes = [
                q for q in quotes if q["available"] and q["unit_price"] > 0
            ]

            if not available_quotes:
                unallocated.append(item_name)
                rationale_parts.append(f"- {item_name}: sem cotação disponível")
                continue

            if prefer_fastest_delivery:
                available_quotes.sort(key=lambda q: (q["delivery_days"], q["unit_price"]))
            else:
                available_quotes.sort(key=lambda q: (q["unit_price"], q["delivery_days"]))

            best = available_quotes[0]
            sid = best["supplier_id"]

            if sid not in allocations:
                allocations[sid] = []

            allocations[sid].append({
                "name": item_name,
                "qty": best["qty"],
                "unit_price": best["unit_price"],
                "subtotal": round(best["qty"] * best["unit_price"], 2),
            })

            if len(available_quotes) > 1:
                saving = available_quotes[-1]["unit_price"] - best["unit_price"]
                rationale_parts.append(
                    f"- {item_name}: alocado para {best['supplier_name']} "
                    f"(R$ {best['unit_price']:.2f}/un, "
                    f"economia de R$ {saving:.2f}/un vs. mais caro)"
                )
            else:
                rationale_parts.append(
                    f"- {item_name}: alocado para {best['supplier_name']} "
                    f"(única cotação: R$ {best['unit_price']:.2f}/un)"
                )

        # Enforce concentration cap
        total_value = sum(
            sum(it["subtotal"] for it in items)
            for items in allocations.values()
        )

        if total_value > 0:
            max_value = total_value * (max_concentration_pct / 100.0)
            for sid, items in list(allocations.items()):
                supplier_total = sum(it["subtotal"] for it in items)
                if supplier_total <= max_value:
                    continue

                # Sort by price variance (lowest first = easiest to move)
                items_with_alt = []
                for item in items:
                    alt_prices = [
                        q["unit_price"]
                        for q in price_matrix.get(item["name"], [])
                        if q["supplier_id"] != sid and q["available"]
                    ]
                    variance = (
                        min(alt_prices) - item["unit_price"]
                        if alt_prices else float("inf")
                    )
                    items_with_alt.append((item, variance, alt_prices))

                items_with_alt.sort(key=lambda x: x[1])

                moved: list[str] = []
                running_total = supplier_total
                for item, _var, alt_prices in items_with_alt:
                    if running_total <= max_value:
                        break
                    if not alt_prices:
                        continue
                    for q in price_matrix[item["name"]]:
                        if q["supplier_id"] != sid and q["available"]:
                            alt_sid = q["supplier_id"]
                            if alt_sid not in allocations:
                                allocations[alt_sid] = []
                            allocations[alt_sid].append({
                                "name": item["name"],
                                "qty": item["qty"],
                                "unit_price": q["unit_price"],
                                "subtotal": round(item["qty"] * q["unit_price"], 2),
                            })
                            running_total -= item["subtotal"]
                            moved.append(item["name"])
                            break

                allocations[sid] = [
                    it for it in items if it["name"] not in moved
                ]
                if moved:
                    rationale_parts.append(
                        f"\n⚠️ Redistribuição: {', '.join(moved)} movidos "
                        f"do fornecedor {supplier_names.get(sid, sid)} "
                        f"para respeitar limite de {max_concentration_pct}%"
                    )

        # Recalculate totals after redistribution
        total_cost = sum(
            sum(it["subtotal"] for it in items)
            for items in allocations.values()
        )

        # Single-source baseline
        single_source_costs: dict[str, float] = {}
        for _item_name, quotes in price_matrix.items():
            for q in quotes:
                sid = q["supplier_id"]
                if sid not in single_source_costs:
                    single_source_costs[sid] = 0
                single_source_costs[sid] += q["qty"] * q["unit_price"]

        cheapest_single = (
            min(single_source_costs.values()) if single_source_costs else total_cost
        )

        savings_pct = (
            round((cheapest_single - total_cost) / cheapest_single * 100, 1)
            if cheapest_single > 0 else 0
        )

        # Risk score
        if allocations and total_cost > 0:
            max_share = max(
                sum(it["subtotal"] for it in items) / total_cost * 100
                for items in allocations.values()
            )
            risk = "baixo" if max_share < 40 else "médio" if max_share < 60 else "alto"
        else:
            max_share = 0
            risk = "n/a"

        allocation_list = []
        for sid, items in allocations.items():
            subtotal = sum(it["subtotal"] for it in items)
            allocation_list.append({
                "supplier_id": sid,
                "supplier_name": supplier_names.get(sid, sid),
                "items": items,
                "subtotal": round(subtotal, 2),
                "share_pct": round(subtotal / total_cost * 100, 1) if total_cost > 0 else 0,
            })

        allocation_list.sort(key=lambda a: a["subtotal"], reverse=True)

        return {
            "allocations": allocation_list,
            "summary": {
                "total_cost": round(total_cost, 2),
                "currency": "BRL",
                "savings_vs_single_source": round(cheapest_single - total_cost, 2),
                "savings_pct": savings_pct,
                "risk_score": risk,
                "supplier_count": len(allocation_list),
                "items_allocated": sum(len(a["items"]) for a in allocation_list),
                "items_unallocated": len(unallocated),
            },
            "rationale": "\n".join(rationale_parts),
            "unallocated": unallocated,
            "constraint_warnings": constraint_warnings,
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Optimization failed: {e}")
        raise ToolError(f"Erro na otimização: {e}")


# =============================================================================
# REPORT & PO GENERATION
# =============================================================================


async def _generate_po_report_logic(
    ctx: Context,
    allocation_result: dict,
    cliente_id: str | None = None,
) -> dict:
    """
    Generate a Markdown procurement report from optimization results.

    Args:
        allocation_result: Full output from optimize_allocation tool.

    Returns:
        dict with report_markdown and purchase_orders_preview
    """
    allocations = allocation_result.get("allocations", [])
    summary = allocation_result.get("summary", {})
    rationale = allocation_result.get("rationale", "")
    unallocated = allocation_result.get("unallocated", [])

    currency = summary.get("currency", "BRL")
    total = summary.get("total_cost", 0)
    savings = summary.get("savings_vs_single_source", 0)
    savings_pct = summary.get("savings_pct", 0)
    risk = summary.get("risk_score", "n/a")

    lines = [
        "# Relatório de Cotação\n",
        "## Resumo Executivo\n",
        f"Análise indica economia de **{currency} {savings:,.2f} ({savings_pct}%)** "
        f"frente à melhor opção single-source. "
        f"Total otimizado: **{currency} {total:,.2f}** "
        f"distribuído entre **{len(allocations)} fornecedores**. "
        f"Risco de concentração: **{risk}**.\n",
    ]

    lines.append("## Alocação por Fornecedor\n")
    po_previews = []

    for alloc in allocations:
        lines.append(f"### {alloc['supplier_name']} ({alloc['share_pct']}%)\n")
        lines.append("| Item | Qtd | Preço Unit. | Subtotal |")
        lines.append("|------|-----|-------------|----------|")
        for item in alloc["items"]:
            lines.append(
                f"| {item['name']} | {item['qty']} | "
                f"{currency} {item['unit_price']:,.2f} | "
                f"{currency} {item['subtotal']:,.2f} |"
            )
        lines.append(f"\n**Total: {currency} {alloc['subtotal']:,.2f}**\n")

        po_previews.append({
            "supplier_id": alloc["supplier_id"],
            "supplier_name": alloc["supplier_name"],
            "items": alloc["items"],
            "total": alloc["subtotal"],
        })

    lines.append("## Análise de Custos\n")
    lines.append("| Cenário | Custo Total |")
    lines.append("|---------|-------------|")
    lines.append(f"| **Otimizado (multi-source)** | **{currency} {total:,.2f}** |")
    if savings > 0:
        lines.append(f"| Melhor single-source | {currency} {total + savings:,.2f} |")
        lines.append(f"| Economia | {currency} {savings:,.2f} ({savings_pct}%) |")

    if unallocated:
        lines.append("\n## ⚠️ Itens Não Alocados\n")
        for item in unallocated:
            lines.append(f"- {item}")

    # Phase 2: Constraint warnings section
    constraint_warnings = allocation_result.get("constraint_warnings", [])
    if constraint_warnings:
        lines.append("\n## ⚠️ Alertas de Restrições\n")
        for warning in constraint_warnings:
            lines.append(f"- {warning}")

    if rationale:
        lines.append("\n## Racional das Decisões\n")
        lines.append(rationale)

    lines.append("\n## Próximos Passos\n")
    lines.append("1. Revise a alocação acima")
    lines.append("2. Use `create_purchase_order` para gerar os pedidos de compra")
    lines.append("3. Aprove cada PO com `approve_purchase_order`")

    return {
        "report_markdown": "\n".join(lines),
        "purchase_orders_preview": po_previews,
    }


async def _create_purchase_order_logic(
    ctx: Context,
    supplier_id: str,
    items: list[dict],
    total_amount: float,
    currency: str = "BRL",
    confirmed: bool = False,
    cliente_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Create a draft Purchase Order for a supplier.

    Uses ElicitationRequired to pause and ask for user confirmation
    before persisting the PO.

    Args:
        supplier_id: UUID of the supplier
        items: List of {name, qty, unit_price, subtotal} from allocation
        total_amount: Total value of the PO
        currency: Currency code (default: BRL)
        confirmed: Whether user already confirmed (set by elicitation flow)

    Returns:
        dict with po_id, supplier_name, total, status
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    session_id = session_id or ctx.request_context.lifespan_context.get("session_id")

    if not cliente_id or not session_id:
        raise ToolError("Missing cliente_id or session_id in context")

    try:
        db = get_supabase_client()

        supplier_result = db.table("supplier_roster").select(
            "name"
        ).eq("id", supplier_id).eq("client_id", cliente_id).maybe_single().execute()

        supplier_name = (
            supplier_result.data.get("name", supplier_id)
            if supplier_result.data else supplier_id
        )

        # HITL gate: require user confirmation before creating PO
        if not confirmed:
            item_names = [it.get("name", "?") for it in items[:5]]
            preview = ", ".join(item_names)
            if len(items) > 5:
                preview += f" (+{len(items) - 5} itens)"

            raise ElicitationRequired(
                type=ElicitationType.CONFIRMATION,
                message=(
                    f"Criar Pedido de Compra?\n\n"
                    f"• **Fornecedor:** {supplier_name}\n"
                    f"• **Itens:** {preview}\n"
                    f"• **Total:** {currency} {total_amount:,.2f}\n\n"
                    f"O PO será criado em status **rascunho** e precisará de aprovação."
                ),
                tool_name="create_purchase_order",
                tool_args={
                    "supplier_id": supplier_id,
                    "items": items,
                    "total_amount": total_amount,
                    "currency": currency,
                    "confirmed": True,
                },
                options=[
                    ElicitationOption(value="yes", label="Sim, criar PO"),
                    ElicitationOption(value="no", label="Não, cancelar"),
                ],
                metadata={
                    "supplier_name": supplier_name,
                    "total_amount": total_amount,
                    "currency": currency,
                    "items_count": len(items),
                },
            )

        po_id = str(uuid4())

        # ── P3.1 — Approval Engine policy gate ────────────────────────────
        # The chat elicitation above already captured the operator's intent.
        # Now resolve the tenant's `approval_policy` for this action: if it
        # demands a separate, role-routed approval (e.g. finance-responsible
        # on PRO+), park the PO as `pending_approval` and enqueue an
        # `approval_requests` row for the dashboard Approvals Tray.
        decision = resolve_policy(
            client_id=cliente_id,
            agent_slug="rfq-agent",
            action="create_purchase_order",
            payload={"total_amount": total_amount, "supplier_id": supplier_id},
            supabase=db,
        )

        po_status = "pending_approval" if decision.requires_async_approval else "draft"

        db.table("purchase_orders").insert({
            "id": po_id,
            "session_id": session_id,
            "client_id": cliente_id,
            "supplier_id": supplier_id,
            "items": items,
            "total_amount": total_amount,
            "currency": currency,
            "status": po_status,
        }).execute()

        approval_id: str | None = None
        if decision.requires_async_approval:
            try:
                req = ApprovalEngine(supabase=db).request(
                    agent_slug="rfq-agent",
                    action="create_purchase_order",
                    payload={
                        "po_id": po_id,
                        "supplier_id": supplier_id,
                        "supplier_name": supplier_name,
                        "total_amount": total_amount,
                        "currency": currency,
                        "items_count": len(items),
                    },
                    session_id=session_id,
                    routed_to_role=decision.routed_role,
                    sla_hours=decision.sla_hours,
                )
                approval_id = req.id
            except ApprovalError:
                logger.exception(
                    "[RFQ] approval enqueue failed for PO %s; falling back to draft",
                    po_id,
                )
                db.table("purchase_orders").update({"status": "draft"}).eq("id", po_id).execute()
                po_status = "draft"

        logger.info(
            f"[RFQ] PO {po_id} created for {supplier_name}: "
            f"{currency} {total_amount:,.2f} (status={po_status}, approval={approval_id})"
        )

        return {
            "po_id": po_id,
            "supplier_name": supplier_name,
            "total_amount": total_amount,
            "currency": currency,
            "status": po_status,
            "items_count": len(items),
            "approval_id": approval_id,
            "approval_reason": decision.reason,
        }

    except (ToolError, ElicitationRequired):
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to create PO: {e}")
        raise ToolError(f"Erro ao criar pedido de compra: {e}")


async def _approve_purchase_order_logic(
    ctx: Context,
    po_id: str,
    confirmed: bool = False,
    cliente_id: str | None = None,
) -> dict:
    """
    Approve a draft Purchase Order, moving it to 'approved' status.

    Uses ElicitationRequired to pause and ask for user confirmation
    before actually approving. The HITL gate ensures the user explicitly
    confirms the action in the chat UI.

    Args:
        po_id: UUID of the purchase order to approve
        confirmed: Whether user already confirmed (set by elicitation flow)

    Returns:
        dict with po_id, updated status, and approval timestamp
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")

    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()

        po_result = db.table("purchase_orders").select(
            "id,status,supplier_id,total_amount,currency,items,"
            "supplier_roster(name)"
        ).eq("id", po_id).eq("client_id", cliente_id).maybe_single().execute()

        po = po_result.data
        if not po:
            raise ToolError(f"Pedido de compra não encontrado: {po_id}")

        if po["status"] == "approved":
            return {
                "po_id": po_id,
                "status": "approved",
                "message": "Este pedido já está aprovado.",
            }

        if po["status"] not in {"draft", "pending_approval"}:
            raise ToolError(
                f"Só é possível aprovar pedidos em status 'draft' ou 'pending_approval'. "
                f"Status atual: {po['status']}"
            )

        supplier_info = po.get("supplier_roster") or {}
        supplier_name = supplier_info.get("name", "Fornecedor")
        total = po["total_amount"]
        currency = po["currency"]
        items_count = len(po.get("items") or [])

        # HITL gate: raise ElicitationRequired if not yet confirmed
        if not confirmed:
            raise ElicitationRequired(
                type=ElicitationType.CONFIRMATION,
                message=(
                    f"Confirmar aprovação do Pedido de Compra?\n\n"
                    f"• **Fornecedor:** {supplier_name}\n"
                    f"• **Itens:** {items_count}\n"
                    f"• **Total:** {currency} {total:,.2f}\n\n"
                    f"Esta ação é irreversível."
                ),
                tool_name="approve_purchase_order",
                tool_args={"po_id": po_id, "confirmed": True},
                options=[
                    ElicitationOption(value="yes", label="Sim, aprovar"),
                    ElicitationOption(value="no", label="Não, cancelar"),
                ],
                metadata={
                    "po_id": po_id,
                    "supplier_name": supplier_name,
                    "total_amount": float(total),
                    "currency": currency,
                },
            )

        now = datetime.now(UTC).isoformat()

        # ── P3.1 — Approval Engine policy gate ────────────────────────────
        # If the tenant policy routes this action to a separate role, do not
        # immediately flip the PO to `approved`; enqueue an `approval_requests`
        # row instead and surface the deferred state to the agent so it can
        # tell the operator a finance-responsible needs to sign off.
        decision = resolve_policy(
            client_id=cliente_id,
            agent_slug="rfq-agent",
            action="approve_purchase_order",
            payload={"total_amount": float(total), "po_id": po_id},
            supabase=db,
        )

        if decision.requires_async_approval:
            try:
                req = ApprovalEngine(supabase=db).request(
                    agent_slug="rfq-agent",
                    action="approve_purchase_order",
                    payload={
                        "po_id": po_id,
                        "supplier_id": po["supplier_id"],
                        "supplier_name": supplier_name,
                        "total_amount": float(total),
                        "currency": currency,
                        "items_count": items_count,
                    },
                    routed_to_role=decision.routed_role,
                    sla_hours=decision.sla_hours,
                )
            except ApprovalError as exc:
                logger.exception("[RFQ] approval enqueue failed for PO %s", po_id)
                raise ToolError(f"Falha ao registrar aprovação: {exc}") from exc

            db.table("purchase_orders").update({"status": "pending_approval"}).eq("id", po_id).execute()
            logger.info(
                "[RFQ] PO %s queued for async approval (id=%s, role=%s)",
                po_id, req.id, decision.routed_role,
            )
            return {
                "po_id": po_id,
                "supplier_name": supplier_name,
                "total_amount": float(total),
                "currency": currency,
                "status": "pending_approval",
                "approval_id": req.id,
                "approval_reason": decision.reason,
                "message": (
                    f"Pedido encaminhado para aprovação ({decision.routed_role or 'responsável'}). "
                    f"SLA {decision.sla_hours}h."
                ),
            }

        db.table("purchase_orders").update({
            "status": "approved",
            "approved_by": cliente_id,
            "approved_at": now,
        }).eq("id", po_id).execute()

        logger.info(f"[RFQ] PO {po_id} approved by {cliente_id}")

        return {
            "po_id": po_id,
            "supplier_name": supplier_name,
            "total_amount": po["total_amount"],
            "currency": po["currency"],
            "status": "approved",
            "approved_at": now,
        }

    except (ToolError, ElicitationRequired):
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to approve PO: {e}")
        raise ToolError(f"Erro ao aprovar pedido: {e}")


# =============================================================================
# NEGOTIATION (Phase 2)
# =============================================================================


async def _suggest_counter_offer_logic(
    ctx: Context,
    supplier_id: str,
    items: list[dict],
    cliente_id: str | None = None,
) -> dict:
    """
    Suggest counter-offer prices by comparing current quotes against historical data.

    Analyzes past rfq_requests for the same items from this tenant and calculates
    median/min historical prices. Suggests counter-offer where current price is
    above the historical median.

    Args:
        supplier_id: UUID of the supplier to counter-offer
        items: List of {name, unit_price} from the supplier's current quote

    Returns:
        dict with suggestions list and summary
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")

    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    if not items:
        raise ToolError("Lista de itens vazia para contra-proposta.")

    try:
        db = get_supabase_client()

        # Get supplier name
        supplier_result = db.table("supplier_roster").select(
            "name"
        ).eq("id", supplier_id).eq("client_id", cliente_id).maybe_single().execute()
        supplier_name = (
            supplier_result.data.get("name", supplier_id)
            if supplier_result.data else supplier_id
        )

        # Fetch historical responded RFQs for this tenant
        historical_result = db.table("rfq_requests").select(
            "response_data"
        ).eq("client_id", cliente_id).eq("status", "responded").execute()

        # Build historical price database: item_name -> [prices]
        historical_prices: dict[str, list[float]] = {}
        for rfq in (historical_result.data or []):
            resp = rfq.get("response_data") or {}
            for p in resp.get("prices", []):
                name = p.get("name", "").lower().strip()
                price = p.get("unit_price", 0)
                if name and price > 0:
                    historical_prices.setdefault(name, []).append(price)

        suggestions: list[dict] = []
        for item in items:
            item_name = item.get("name", "")
            current_price = float(item.get("unit_price", 0))
            if not item_name or current_price <= 0:
                continue

            key = item_name.lower().strip()
            history = historical_prices.get(key, [])

            suggestion: dict = {
                "name": item_name,
                "current_price": current_price,
                "has_history": bool(history),
            }

            if history:
                sorted_prices = sorted(history)
                median_idx = len(sorted_prices) // 2
                median_price = sorted_prices[median_idx]
                min_price = sorted_prices[0]
                avg_price = sum(sorted_prices) / len(sorted_prices)

                suggestion["historical_median"] = round(median_price, 2)
                suggestion["historical_min"] = round(min_price, 2)
                suggestion["historical_avg"] = round(avg_price, 2)
                suggestion["sample_size"] = len(sorted_prices)

                if current_price > median_price:
                    # Suggest counter at median + 5% buffer
                    target = round(median_price * 1.05, 2)
                    saving = round(current_price - target, 2)
                    suggestion["recommended_counter"] = target
                    suggestion["potential_saving_per_unit"] = saving
                    suggestion["action"] = "counter"
                    suggestion["rationale"] = (
                        f"Preço atual R$ {current_price:.2f} está "
                        f"{((current_price - median_price) / median_price * 100):.0f}% "
                        f"acima da mediana histórica (R$ {median_price:.2f})"
                    )
                else:
                    suggestion["action"] = "accept"
                    suggestion["rationale"] = (
                        f"Preço atual R$ {current_price:.2f} está dentro ou abaixo "
                        f"da mediana histórica (R$ {median_price:.2f})"
                    )
            else:
                suggestion["action"] = "no_data"
                suggestion["rationale"] = "Sem dados históricos para comparação"

            suggestions.append(suggestion)

        counter_items = [s for s in suggestions if s.get("action") == "counter"]
        total_potential_saving = sum(s.get("potential_saving_per_unit", 0) for s in counter_items)

        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "suggestions": suggestions,
            "summary": {
                "total_items_analyzed": len(suggestions),
                "items_to_counter": len(counter_items),
                "items_acceptable": sum(1 for s in suggestions if s.get("action") == "accept"),
                "items_no_data": sum(1 for s in suggestions if s.get("action") == "no_data"),
                "total_potential_saving_per_unit": round(total_potential_saving, 2),
            },
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Counter-offer analysis failed: {e}")
        raise ToolError(f"Erro na análise de contra-proposta: {e}")


# =============================================================================
# GOOGLE SHEETS INTEGRATION (Phase 3 — Step 11)
# =============================================================================


async def _get_google_tokens(cliente_id: str, account_email: str | None = None) -> dict:
    """Retrieve and refresh Google tokens for a client."""
    ctx_service = get_context_service()
    cliente_uuid = UUID(cliente_id)
    token_wrapper = await ctx_service.get_integration_tokens(
        cliente_uuid,
        "google",
        auto_refresh=True,
        account_email=account_email,
    )
    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError(
            "Integração Google não configurada ou expirada. "
            "Reconecte sua conta Google nas configurações."
        )
    return token_wrapper.get_decrypted_tokens()


async def _import_buying_list_from_sheets_logic(
    ctx: Context,
    spreadsheet_id: str,
    range_name: str = "A1:Z1000",
    account_email: str | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    Import a buying list from Google Sheets and parse into structured items.

    Reads rows from the specified spreadsheet range and structures them
    as buying list items (name, qty, specs, unit).

    Args:
        spreadsheet_id: Google Sheets spreadsheet ID (from URL)
        range_name: A1 notation range to read (default: A1:Z1000)
        account_email: Optional Google account email to use

    Returns:
        dict with items, warnings, total_items, source_spreadsheet
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        tokens = await _get_google_tokens(cliente_id, account_email)
        client = GoogleSheetsClient(access_token=tokens["access_token"])

        sheet_result = await client.read_values(spreadsheet_id, range_name)
        rows = sheet_result.values

        if not rows:
            raise ToolError(
                "Planilha vazia ou intervalo sem dados. "
                "Verifique o spreadsheet_id e o range."
            )

        # First row is headers
        headers = [str(h).strip() for h in rows[0]]
        data_rows = rows[1:]

        if not data_rows:
            raise ToolError("Planilha contém apenas cabeçalhos, sem dados.")

        # Convert to dicts
        row_dicts = []
        for row in data_rows:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            row_dicts.append(row_dict)

        items = _extract_items_from_rows(row_dicts, headers)
        warnings: list[str] = []

        # Check for common issues
        empty_names = sum(1 for it in items if not it.get("name"))
        zero_qty = sum(1 for it in items if it.get("qty", 0) <= 0)

        if empty_names:
            warnings.append(f"{empty_names} item(ns) sem nome na planilha")
        if zero_qty:
            warnings.append(f"{zero_qty} item(ns) com quantidade zerada ou ausente")

        logger.info(
            f"[RFQ] Imported {len(items)} items from Google Sheets "
            f"(spreadsheet: {spreadsheet_id})"
        )

        return {
            "items": items,
            "warnings": warnings,
            "total_items": len(items),
            "source": "google_sheets",
            "source_spreadsheet": spreadsheet_id,
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to import from Google Sheets: {e}")
        raise ToolError(f"Erro ao importar planilha Google: {e}")


async def export_po_to_sheets_core(
    *,
    cliente_id: str,
    po_id: str | None = None,
    session_id: str | None = None,
    spreadsheet_id: str | None = None,
    sheet_name: str = "Pedidos de Compra",
    account_email: str | None = None,
) -> dict:
    """
    Core (ctx-free) implementation of `export_po_to_sheets`.

    Exposed so REST handlers (e.g. the dashboard "Exportar para Sheets" button)
    can reuse the same logic without going through the MCP `Context` object.
    """
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()

        # Fetch POs
        query = db.table("purchase_orders").select(
            "id,supplier_id,items,total_amount,currency,status,approved_at,"
            "supplier_roster(name)"
        ).eq("client_id", cliente_id)

        if po_id:
            query = query.eq("id", po_id)
        elif session_id:
            query = query.eq("session_id", session_id).in_(
                "status", ["approved", "draft"]
            )
        else:
            raise ToolError("Forneça po_id ou tenha uma sessão ativa.")

        result = query.execute()
        pos = result.data or []

        if not pos:
            raise ToolError("Nenhum pedido de compra encontrado para exportar.")

        # Build spreadsheet rows
        header = [
            "PO ID", "Fornecedor", "Item", "Qtd", "Preço Unit.",
            "Subtotal", "Total PO", "Moeda", "Status", "Aprovado em"
        ]
        rows: list[list] = [header]

        for po in pos:
            supplier_info = po.get("supplier_roster") or {}
            supplier_name = supplier_info.get("name", "")
            po_items = po.get("items") or []

            for item in po_items:
                rows.append([
                    po["id"],
                    supplier_name,
                    item.get("name", ""),
                    item.get("qty", 0),
                    item.get("unit_price", 0),
                    item.get("subtotal", 0),
                    float(po["total_amount"]),
                    po["currency"],
                    po["status"],
                    po.get("approved_at", ""),
                ])

        tokens = await _get_google_tokens(cliente_id, account_email)
        client = GoogleSheetsClient(access_token=tokens["access_token"])

        if spreadsheet_id:
            # Append to existing spreadsheet
            range_name = f"{sheet_name}!A1"
            write_result = await client.append_values(
                spreadsheet_id, range_name, rows
            )
            spreadsheet_url = (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            )
        else:
            # Create new spreadsheet
            title = f"Pedidos de Compra — {datetime.now(UTC).strftime('%Y-%m-%d')}"
            spreadsheet = await client.create_spreadsheet(title)
            spreadsheet_id = spreadsheet["spreadsheet_id"]
            spreadsheet_url = spreadsheet["spreadsheet_url"]
            await client.append_values(spreadsheet_id, "A1", rows)

        logger.info(
            f"[RFQ] Exported {len(pos)} POs ({len(rows)-1} rows) to Google Sheets"
        )

        return {
            "status": "success",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": spreadsheet_url,
            "sheet_name": sheet_name,
            "rows_written": len(rows) - 1,
            "pos_exported": len(pos),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to export POs to Google Sheets: {e}")
        raise ToolError(f"Erro ao exportar para Google Sheets: {e}")


async def _export_po_to_sheets_logic(
    ctx: Context,
    po_id: str | None = None,
    spreadsheet_id: str | None = None,
    sheet_name: str = "Pedidos de Compra",
    account_email: str | None = None,
    cliente_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """MCP wrapper around :func:`export_po_to_sheets_core`."""
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    session_id = session_id or ctx.request_context.lifespan_context.get("session_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")
    return await export_po_to_sheets_core(
        cliente_id=cliente_id,
        po_id=po_id,
        session_id=session_id,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        account_email=account_email,
    )


# =============================================================================
# SUPPLIER ROSTER MANAGEMENT (Phase 3 — Step 14)
# =============================================================================


async def _add_supplier_logic(
    ctx: Context,
    name: str,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    categories: list[str] | None = None,
    payment_terms: str | None = None,
    delivery_days_avg: int | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    Add a new supplier to the tenant's roster.

    Args:
        name: Supplier company name
        contact_email: Primary contact email
        contact_phone: Primary contact phone (with country code for WhatsApp)
        categories: List of product categories (e.g., ["alimentos", "limpeza"])
        payment_terms: Default payment terms (e.g., "30 dias")
        delivery_days_avg: Average delivery time in days

    Returns:
        dict with supplier_id, name, and status
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    if not name or not name.strip():
        raise ToolError("Nome do fornecedor é obrigatório.")

    try:
        db = get_supabase_client()

        supplier_data = {
            "client_id": cliente_id,
            "name": name.strip(),
            "contact_email": (contact_email or "").strip() or None,
            "contact_phone": (contact_phone or "").strip() or None,
            "categories": categories or [],
            "payment_terms": (payment_terms or "").strip() or "",
            "delivery_days_avg": delivery_days_avg or 0,
            "is_active": True,
        }

        result = db.table("supplier_roster").insert(supplier_data).execute()
        supplier = result.data[0] if result.data else {}

        logger.info(f"[RFQ] Supplier '{name}' added (id={supplier.get('id')})")

        return {
            "supplier_id": supplier.get("id"),
            "name": name.strip(),
            "status": "created",
        }

    except Exception as e:
        logger.error(f"[RFQ] Failed to add supplier: {e}")
        raise ToolError(f"Erro ao adicionar fornecedor: {e}")


async def _update_supplier_logic(
    ctx: Context,
    supplier_id: str,
    name: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    categories: list[str] | None = None,
    payment_terms: str | None = None,
    delivery_days_avg: int | None = None,
    is_active: bool | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    Update an existing supplier's information.

    Only provided fields are updated; omitted fields remain unchanged.

    Args:
        supplier_id: UUID of the supplier to update
        name: New supplier name
        contact_email: New contact email
        contact_phone: New contact phone
        categories: New categories list
        payment_terms: New payment terms
        delivery_days_avg: New average delivery days
        is_active: Set active/inactive status

    Returns:
        dict with supplier_id and updated fields
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()

        # Verify supplier belongs to tenant
        existing = db.table("supplier_roster").select(
            "id"
        ).eq("id", supplier_id).eq("client_id", cliente_id).maybe_single().execute()

        if not existing.data:
            raise ToolError(f"Fornecedor não encontrado: {supplier_id}")

        updates: dict = {"updated_at": datetime.now(UTC).isoformat()}
        if name is not None:
            updates["name"] = name.strip()
        if contact_email is not None:
            updates["contact_email"] = contact_email.strip() or None
        if contact_phone is not None:
            updates["contact_phone"] = contact_phone.strip() or None
        if categories is not None:
            updates["categories"] = categories
        if payment_terms is not None:
            updates["payment_terms"] = payment_terms.strip()
        if delivery_days_avg is not None:
            updates["delivery_days_avg"] = delivery_days_avg
        if is_active is not None:
            updates["is_active"] = is_active

        db.table("supplier_roster").update(updates).eq(
            "id", supplier_id
        ).execute()

        logger.info(f"[RFQ] Supplier {supplier_id} updated: {list(updates.keys())}")

        return {
            "supplier_id": supplier_id,
            "updated_fields": [k for k in updates if k != "updated_at"],
            "status": "updated",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to update supplier: {e}")
        raise ToolError(f"Erro ao atualizar fornecedor: {e}")


async def _remove_supplier_logic(
    ctx: Context,
    supplier_id: str,
    cliente_id: str | None = None,
) -> dict:
    """
    Deactivate a supplier (soft-delete). Sets is_active=False.

    Args:
        supplier_id: UUID of the supplier to deactivate

    Returns:
        dict with supplier_id and status
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")
    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()

        existing = db.table("supplier_roster").select(
            "id,name"
        ).eq("id", supplier_id).eq("client_id", cliente_id).maybe_single().execute()

        if not existing.data:
            raise ToolError(f"Fornecedor não encontrado: {supplier_id}")

        db.table("supplier_roster").update({
            "is_active": False,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", supplier_id).execute()

        logger.info(f"[RFQ] Supplier {supplier_id} deactivated")

        return {
            "supplier_id": supplier_id,
            "name": existing.data.get("name", ""),
            "status": "deactivated",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ] Failed to remove supplier: {e}")
        raise ToolError(f"Erro ao remover fornecedor: {e}")


# =============================================================================
# MODULE REGISTRATION
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register all RFQ/Procurement tools."""

    mcp.tool(
        name="parse_buying_list",
        description=(
            "Analisa uma lista de compras (texto digitado ou arquivo CSV/XLSX enviado) "
            "e retorna itens estruturados com nome, quantidade e especificações.\n\n"
            "Use raw_text para lista digitada ou file_id para arquivo enviado.\n"
            "Exemplo raw_text: 'Parafuso M6, 500, aço inox\\nPorca M6, 500'"
        ),
    )(mcp_inject_cliente_id(get_context_service)(_parse_buying_list_logic))

    mcp.tool(
        name="validate_buying_list",
        description=(
            "Valida a lista de compras parseada: verifica campos obrigatórios, "
            "duplicatas e quantidades. Retorna itens limpos prontos para cotação.\n\n"
            "Use APÓS parse_buying_list."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_validate_buying_list_logic))

    mcp.tool(
        name="list_suppliers",
        description=(
            "Lista fornecedores cadastrados do cliente. "
            "Opcionalmente filtra por categoria.\n\n"
            "Exemplo: list_suppliers(category='alimentos')"
        ),
    )(mcp_inject_cliente_id(get_context_service)(_list_suppliers_logic))

    mcp.tool(
        name="dispatch_rfq",
        description=(
            "Envia uma solicitação de cotação (RFQ) para um fornecedor específico. "
            "Cria o registro e marca como 'sent'.\n\n"
            "⚠️ Fase 1: envio simulado. Use submit_mock_response para simular resposta.\n"
            "Passe os itens limpos de validate_buying_list."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_dispatch_rfq_logic))

    mcp.tool(
        name="check_rfq_responses",
        description=(
            "Verifica o status de todas as cotações enviadas na sessão atual. "
            "Mostra quais fornecedores responderam e quais estão pendentes."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_check_rfq_responses_logic))

    mcp.tool(
        name="submit_mock_response",
        description=(
            "Submete uma resposta simulada de fornecedor (para teste/Fase 1).\n\n"
            "Passe rfq_id e uma lista de preços:\n"
            '[{"name": "Parafuso M6", "unit_price": 0.45, "available": true}]'
        ),
    )(mcp_inject_cliente_id(get_context_service)(_submit_mock_response_logic))

    mcp.tool(
        name="optimize_allocation",
        description=(
            "Otimiza a alocação de itens entre fornecedores com base nas cotações recebidas.\n\n"
            "Algoritmo: menor preço por item, com limite de concentração (padrão 60%) "
            "e redistribuição automática para mitigar risco.\n\n"
            "Restrições opcionais (Fase 2):\n"
            "- max_delivery_days: prazo máximo de entrega em dias\n"
            "- required_payment_terms: ex. '30 dias'\n"
            "- enforce_moq: respeitar quantidades mínimas (MOQ) dos fornecedores\n\n"
            "Requer que ao menos um fornecedor tenha respondido."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_optimize_allocation_logic))

    mcp.tool(
        name="generate_po_report",
        description=(
            "Gera relatório Markdown completo a partir do resultado da otimização.\n\n"
            "Inclui: resumo executivo, tabelas por fornecedor, análise de custos, "
            "racional das decisões e próximos passos.\n\n"
            "Passe o resultado completo de optimize_allocation."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_generate_po_report_logic))

    mcp.tool(
        name="create_purchase_order",
        description=(
            "Cria um Pedido de Compra (PO) em rascunho para um fornecedor.\n\n"
            "Passe supplier_id, items e total_amount do relatório de otimização.\n"
            "O PO começa em status 'draft' e precisa de aprovação."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_create_purchase_order_logic))

    mcp.tool(
        name="approve_purchase_order",
        description=(
            "Aprova um Pedido de Compra (PO), mudando o status de 'draft' para 'approved'.\n\n"
            "⚠️ Ação irreversível. O sistema pedirá confirmação automática via chat.\n"
            "O diálogo de confirmação mostra fornecedor, itens e total antes de aprovar."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_approve_purchase_order_logic))

    mcp.tool(
        name="suggest_counter_offer",
        description=(
            "Analisa preços de um fornecedor e sugere contra-propostas com base em "
            "dados históricos de cotações anteriores.\n\n"
            "Compara preços atuais com medianas e mínimos históricos. "
            "Para cada item, recomenda: aceitar, contra-propor ou sem dados.\n\n"
            "Passe supplier_id e items [{name, unit_price}] da cotação recebida."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_suggest_counter_offer_logic))

    # Phase 3: Google Sheets Integration (Step 11)
    mcp.tool(
        name="import_buying_list_from_sheets",
        description=(
            "Importa lista de compras de uma planilha Google Sheets.\n\n"
            "Lê linhas da planilha e estrutura como itens de compra (nome, qtd, specs).\n"
            "Passe spreadsheet_id (do URL da planilha) e opcionalmente range_name.\n\n"
            "Requer integração Google conectada."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_import_buying_list_from_sheets_logic))

    mcp.tool(
        name="export_po_to_sheets",
        description=(
            "Exporta Pedidos de Compra para uma planilha Google Sheets.\n\n"
            "Se po_id for informado, exporta aquele PO. Caso contrário, exporta todos "
            "os POs aprovados/em rascunho da sessão atual.\n"
            "Se spreadsheet_id não for informado, cria uma nova planilha.\n\n"
            "Requer integração Google conectada."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_export_po_to_sheets_logic))

    # Phase 3: Supplier Roster Management (Step 14)
    mcp.tool(
        name="add_supplier",
        description=(
            "Adiciona um novo fornecedor ao cadastro do cliente.\n\n"
            "Campos: name (obrigatório), contact_email, contact_phone, "
            "categories (lista), payment_terms, delivery_days_avg."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_add_supplier_logic))

    mcp.tool(
        name="update_supplier",
        description=(
            "Atualiza informações de um fornecedor existente.\n\n"
            "Apenas campos informados são alterados. Campos omitidos não são modificados.\n"
            "Passe supplier_id e os campos a atualizar."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_update_supplier_logic))

    mcp.tool(
        name="remove_supplier",
        description=(
            "Desativa um fornecedor do cadastro (soft-delete).\n\n"
            "O fornecedor não é apagado, apenas marcado como inativo. "
            "Ele não aparecerá mais em list_suppliers."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_remove_supplier_logic))

    logger.info(
        "[RFQ Module] Tools registered: parse_buying_list, validate_buying_list, "
        "list_suppliers, dispatch_rfq, check_rfq_responses, submit_mock_response, "
        "optimize_allocation, generate_po_report, create_purchase_order, "
        "approve_purchase_order, suggest_counter_offer, "
        "import_buying_list_from_sheets, export_po_to_sheets, "
        "add_supplier, update_supplier, remove_supplier"
    )

    return [
        "parse_buying_list",
        "validate_buying_list",
        "list_suppliers",
        "dispatch_rfq",
        "check_rfq_responses",
        "submit_mock_response",
        "optimize_allocation",
        "generate_po_report",
        "create_purchase_order",
        "approve_purchase_order",
        "suggest_counter_offer",
        "import_buying_list_from_sheets",
        "export_po_to_sheets",
        "add_supplier",
        "update_supplier",
        "remove_supplier",
    ]
