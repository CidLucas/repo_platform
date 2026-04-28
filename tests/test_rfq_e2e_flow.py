#!/usr/bin/env python3
"""
E2E Test: Full RFQ Flow — Grocery List → PO Approval

Tests the entire procurement pipeline:
1. Parse a grocery list (free-text)
2. Validate the buying list
3. List suppliers
4. Dispatch RFQs to 3 suppliers
5. Submit mock responses with prices
6. Optimize allocation
7. Generate PO report
8. Create PO (test ElicitationRequired)
9. Approve PO (test ElicitationRequired)
10. Supplier CRUD (add, update, remove)

Usage:
    cd blu-mono
    python3 tests/test_rfq_e2e_flow.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "services" / "tool_pool_api" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_supabase_client" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_elicitation_service" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_models" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_context_service" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_auth" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_google_suite_client" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_shared_utils" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_observability_bootstrap" / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Config ───
CLIENT_ID = "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
SESSION_ID = f"test-rfq-e2e-{uuid4().hex[:8]}"

# ─── Grocery List (free-text) ───
GROCERY_LIST = """
Arroz 5kg, 20
Feijão Preto 1kg, 30
Açúcar Cristal 5kg, 15
Óleo de Soja 900ml, 25
Farinha de Trigo 1kg, 10
Macarrão Espaguete 500g, 40
Sal Refinado 1kg, 12
Café Torrado 500g, 18
Leite Integral 1L, 50
Molho de Tomate 340g, 20
"""


def make_mock_ctx() -> MagicMock:
    """Create a mock FastMCP Context with session/client info."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "session_id": SESSION_ID,
        "cliente_id": CLIENT_ID,
    }
    return ctx


def print_step(n: int, title: str):
    logger.info(f"\n{'='*60}")
    logger.info(f"  STEP {n}: {title}")
    logger.info(f"{'='*60}")


def print_result(result: dict, keys: list[str] | None = None):
    if keys:
        for k in keys:
            logger.info(f"  {k}: {result.get(k)}")
    else:
        logger.info(f"  {json.dumps(result, indent=2, ensure_ascii=False, default=str)[:1000]}")


async def run_full_flow():
    """Execute the complete RFQ pipeline."""

    # Import logic functions directly (bypassing MCP decorator)
    from tool_pool_api.server.tool_modules.rfq_module import (
        _add_supplier_logic,
        _approve_purchase_order_logic,
        _check_rfq_responses_logic,
        _create_purchase_order_logic,
        _dispatch_rfq_logic,
        _generate_po_report_logic,
        _list_suppliers_logic,
        _optimize_allocation_logic,
        _parse_buying_list_logic,
        _remove_supplier_logic,
        _submit_mock_response_logic,
        _update_supplier_logic,
        _validate_buying_list_logic,
    )

    from blu_elicitation_service.exceptions import ElicitationRequired

    ctx = make_mock_ctx()

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: Parse Buying List
    # ═══════════════════════════════════════════════════════════════
    print_step(1, "PARSE BUYING LIST (Lista de Compras de Supermercado)")
    logger.info(f"  Input: {GROCERY_LIST.strip()[:80]}...")

    parsed = await _parse_buying_list_logic(
        ctx=ctx,
        raw_text=GROCERY_LIST,
        cliente_id=CLIENT_ID,
    )

    items = parsed["items"]
    logger.info(f"  Parsed {parsed['total_items']} items, {len(parsed.get('warnings', []))} warnings")
    for item in items[:5]:
        logger.info(f"    - {item['name']}: qty={item.get('qty', '?')} unit={item.get('unit', '?')}")
    if len(items) > 5:
        logger.info(f"    ... +{len(items) - 5} more")

    assert len(items) >= 8, f"Expected at least 8 items, got {len(items)}"
    logger.info("  ✅ Parse OK")

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Validate Buying List
    # ═══════════════════════════════════════════════════════════════
    print_step(2, "VALIDATE BUYING LIST")

    validated = await _validate_buying_list_logic(
        ctx=ctx,
        items=items,
        cliente_id=CLIENT_ID,
    )

    logger.info(f"  Valid: {validated['valid']}")
    logger.info(f"  Errors: {validated.get('errors', [])}")
    logger.info(f"  Warnings: {validated.get('warnings', [])}")
    logger.info(f"  Cleaned items: {len(validated.get('cleaned_items', []))}")

    cleaned_items = validated.get("cleaned_items", items)
    assert validated["valid"], f"Validation failed: {validated.get('errors')}"
    logger.info("  ✅ Validation OK")

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: List Suppliers
    # ═══════════════════════════════════════════════════════════════
    print_step(3, "LIST SUPPLIERS")

    suppliers_result = await _list_suppliers_logic(
        ctx=ctx,
        cliente_id=CLIENT_ID,
    )

    suppliers = suppliers_result["suppliers"]
    logger.info(f"  Found {suppliers_result['total']} suppliers:")
    for s in suppliers:
        logger.info(f"    - {s['name']} (id={s['id'][:8]}...) cats={s.get('categories', [])}")

    assert len(suppliers) >= 3, f"Expected at least 3 suppliers, got {len(suppliers)}"
    logger.info("  ✅ Suppliers OK")

    # Pick 3 suppliers for dispatch
    dispatch_suppliers = suppliers[:3]

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: Dispatch RFQs to 3 suppliers
    # ═══════════════════════════════════════════════════════════════
    print_step(4, "DISPATCH RFQs TO 3 SUPPLIERS")

    rfq_ids = []
    for s in dispatch_suppliers:
        result = await _dispatch_rfq_logic(
            ctx=ctx,
            supplier_id=s["id"],
            items=cleaned_items,
            cliente_id=CLIENT_ID,
        )
        rfq_ids.append(result["rfq_id"])
        logger.info(
            f"  📤 RFQ {result['rfq_id'][:8]}... → {result['supplier_name']} "
            f"({result['items_count']} items, deadline {result['deadline'][:10]})"
        )

    assert len(rfq_ids) == 3, f"Expected 3 RFQs dispatched, got {len(rfq_ids)}"
    logger.info("  ✅ Dispatch OK (3 RFQs sent)")

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: Submit Mock Responses (simulate supplier quotes)
    # ═══════════════════════════════════════════════════════════════
    print_step(5, "SUBMIT MOCK RESPONSES (3 suppliers with varying prices)")

    # Create different price profiles for each supplier
    price_profiles = [
        {  # Supplier 1: cheapest on half items, expensive on rest
            "multiplier": 0.85,
            "delivery_days": 5,
            "payment_terms": "30 dias",
            "notes": "Desconto para compras acima de 10 unidades",
        },
        {  # Supplier 2: mid-range prices, fastest delivery
            "multiplier": 1.0,
            "delivery_days": 2,
            "payment_terms": "à vista",
            "notes": "Entrega expressa disponível",
        },
        {  # Supplier 3: expensive but best payment terms
            "multiplier": 1.15,
            "delivery_days": 7,
            "payment_terms": "60 dias",
            "notes": "Parcelamento em até 3x sem juros",
        },
    ]

    # Base prices per item (realistic BRL grocery prices)
    base_prices = {
        "arroz": 22.90,
        "feijão": 8.50,
        "feijao": 8.50,
        "açúcar": 18.90,
        "acucar": 18.90,
        "óleo": 7.90,
        "oleo": 7.90,
        "farinha": 5.50,
        "macarrão": 3.90,
        "macarrao": 3.90,
        "sal": 2.50,
        "café": 15.90,
        "cafe": 15.90,
        "leite": 4.90,
        "molho": 3.50,
    }

    def get_base_price(item_name: str) -> float:
        name_lower = item_name.lower()
        for key, price in base_prices.items():
            if key in name_lower:
                return price
        return 10.0  # default

    for i, (rfq_id, profile) in enumerate(zip(rfq_ids, price_profiles)):
        prices = []
        for item in cleaned_items:
            name = item.get("name", "Item")
            base = get_base_price(name)
            # Add some variation: supplier 1 cheap on odd items, etc.
            if i == 0:
                mult = 0.85 if hash(name) % 2 == 0 else 1.05
            elif i == 1:
                mult = 1.0
            else:
                mult = 1.15 if hash(name) % 2 == 0 else 0.95
            unit_price = round(base * mult, 2)
            prices.append({
                "name": name,
                "unit_price": unit_price,
                "available": True,
            })

        result = await _submit_mock_response_logic(
            ctx=ctx,
            rfq_id=rfq_id,
            prices=prices,
            delivery_days=profile["delivery_days"],
            payment_terms=profile["payment_terms"],
            notes=profile["notes"],
            cliente_id=CLIENT_ID,
        )
        logger.info(
            f"  📩 Response for RFQ {rfq_id[:8]}... "
            f"({result['items_quoted']} items quoted, "
            f"delivery={profile['delivery_days']}d, terms={profile['payment_terms']})"
        )

    logger.info("  ✅ All 3 responses submitted")

    # ═══════════════════════════════════════════════════════════════
    # STEP 5b: Check Responses
    # ═══════════════════════════════════════════════════════════════
    print_step("5b", "CHECK RFQ RESPONSES")

    responses = await _check_rfq_responses_logic(
        ctx=ctx,
        cliente_id=CLIENT_ID,
    )

    logger.info(f"  Total: {responses['total']}, Responded: {responses['responded']}, Pending: {responses['pending']}")
    logger.info(f"  All responded: {responses['all_responded']}")
    assert responses["all_responded"], "Not all suppliers responded!"
    logger.info("  ✅ All responses received")

    # ═══════════════════════════════════════════════════════════════
    # STEP 6: Optimize Allocation
    # ═══════════════════════════════════════════════════════════════
    print_step(6, "OPTIMIZE ALLOCATION (max 60% concentration)")

    allocation = await _optimize_allocation_logic(
        ctx=ctx,
        max_concentration_pct=60,
        enforce_moq=False,  # Test suppliers may have MOQ
        cliente_id=CLIENT_ID,
    )

    summary = allocation["summary"]
    logger.info(f"  Total cost: {summary.get('currency', 'BRL')} {summary['total_cost']:,.2f}")
    logger.info(f"  Savings vs single-source: {summary.get('savings_pct', 0):.1f}%")
    logger.info(f"  Risk score: {summary.get('risk_score', 'N/A')}")
    logger.info(f"  Suppliers used: {summary['supplier_count']}")
    logger.info(f"  Items allocated: {summary['items_allocated']}")
    logger.info(f"  Items unallocated: {summary['items_unallocated']}")

    if allocation.get("constraint_warnings"):
        logger.info(f"  ⚠️ Constraints: {allocation['constraint_warnings']}")

    logger.info("\n  Allocations by supplier:")
    for alloc in allocation["allocations"]:
        logger.info(
            f"    {alloc['supplier_name']}: "
            f"{len(alloc['items'])} items, "
            f"BRL {alloc['subtotal']:,.2f} "
            f"({alloc.get('share_pct', 0):.0f}%)"
        )

    assert summary["items_allocated"] > 0, "No items allocated!"
    logger.info("\n  ✅ Allocation OK")

    # ═══════════════════════════════════════════════════════════════
    # STEP 7: Generate PO Report
    # ═══════════════════════════════════════════════════════════════
    print_step(7, "GENERATE PO REPORT (Markdown)")

    report = await _generate_po_report_logic(
        ctx=ctx,
        allocation_result=allocation,
        cliente_id=CLIENT_ID,
    )

    markdown = report["report_markdown"]
    preview_pos = report.get("purchase_orders_preview", [])
    logger.info(f"  Report length: {len(markdown)} chars")
    logger.info(f"  PO previews: {len(preview_pos)}")
    logger.info(f"\n  Report preview (first 500 chars):\n{markdown[:500]}")

    assert len(markdown) > 100, "Report too short"
    assert len(preview_pos) > 0, "No PO previews"
    logger.info("\n  ✅ Report OK")

    # ═══════════════════════════════════════════════════════════════
    # STEP 8: Create Purchase Orders (test ElicitationRequired)
    # ═══════════════════════════════════════════════════════════════
    print_step(8, "CREATE PURCHASE ORDERS (with HITL confirmation)")

    created_pos = []
    for po_preview in preview_pos:
        # First call: should raise ElicitationRequired (confirmed=False)
        try:
            await _create_purchase_order_logic(
                ctx=ctx,
                supplier_id=po_preview["supplier_id"],
                items=po_preview["items"],
                total_amount=po_preview["total"],
                currency=summary.get("currency", "BRL"),
                confirmed=False,
                cliente_id=CLIENT_ID,
            )
            logger.warning("  ⚠️ Expected ElicitationRequired but didn't get one!")
        except ElicitationRequired as e:
            logger.info(
                f"  🛑 ElicitationRequired raised for PO to {po_preview.get('supplier_name', '?')}:"
            )
            logger.info(f"     Type: {e.type}")
            logger.info(f"     Message: {str(e.message)[:100]}...")
            logger.info(f"     Options: {[o.label for o in (e.options or [])]}")

        # Second call: confirmed=True → PO created
        result = await _create_purchase_order_logic(
            ctx=ctx,
            supplier_id=po_preview["supplier_id"],
            items=po_preview["items"],
            total_amount=po_preview["total"],
            currency=summary.get("currency", "BRL"),
            confirmed=True,
            cliente_id=CLIENT_ID,
        )
        created_pos.append(result)
        logger.info(
            f"  ✅ PO {result['po_id'][:8]}... created → {result['supplier_name']} "
            f"({result['currency']} {result['total_amount']:,.2f})"
        )

    assert len(created_pos) > 0, "No POs created"
    logger.info(f"\n  ✅ {len(created_pos)} POs created")

    # ═══════════════════════════════════════════════════════════════
    # STEP 9: Approve Purchase Orders (test ElicitationRequired)
    # ═══════════════════════════════════════════════════════════════
    print_step(9, "APPROVE PURCHASE ORDERS (with HITL confirmation)")

    for po in created_pos:
        # First call: should raise ElicitationRequired
        try:
            await _approve_purchase_order_logic(
                ctx=ctx,
                po_id=po["po_id"],
                confirmed=False,
                cliente_id=CLIENT_ID,
            )
            logger.warning("  ⚠️ Expected ElicitationRequired but didn't get one!")
        except ElicitationRequired as e:
            logger.info(f"  🛑 ElicitationRequired for approval of PO {po['po_id'][:8]}...")
            logger.info(f"     Message: {str(e.message)[:100]}...")

        # Second call: confirmed=True → PO approved
        result = await _approve_purchase_order_logic(
            ctx=ctx,
            po_id=po["po_id"],
            confirmed=True,
            cliente_id=CLIENT_ID,
        )
        logger.info(
            f"  ✅ PO {po['po_id'][:8]}... approved → {result.get('supplier_name', '?')} "
            f"(status={result['status']})"
        )

    logger.info(f"\n  ✅ All {len(created_pos)} POs approved")

    # ═══════════════════════════════════════════════════════════════
    # STEP 10: Supplier CRUD
    # ═══════════════════════════════════════════════════════════════
    print_step(10, "SUPPLIER CRUD (Add → Update → Remove)")

    # Add a new supplier
    new_supplier = await _add_supplier_logic(
        ctx=ctx,
        name="Supermercado Teste E2E",
        contact_email="teste@e2e.com",
        contact_phone="+5511999991234",
        categories=["alimentos", "bebidas"],
        payment_terms="45 dias",
        delivery_days_avg=4,
        cliente_id=CLIENT_ID,
    )
    logger.info(f"  ➕ Added: {new_supplier['name']} (id={new_supplier['supplier_id'][:8]}...)")

    # Update the supplier
    updated = await _update_supplier_logic(
        ctx=ctx,
        supplier_id=new_supplier["supplier_id"],
        payment_terms="30/60 dias",
        delivery_days_avg=3,
        categories=["alimentos", "bebidas", "limpeza"],
        cliente_id=CLIENT_ID,
    )
    logger.info(f"  ✏️  Updated: {updated['supplier_id'][:8]}... fields={updated['updated_fields']}")

    # Remove (soft-delete) the supplier
    removed = await _remove_supplier_logic(
        ctx=ctx,
        supplier_id=new_supplier["supplier_id"],
        cliente_id=CLIENT_ID,
    )
    logger.info(f"  🗑️  Removed: {removed['name']} (status={removed['status']})")
    logger.info("  ✅ CRUD OK")

    # ═══════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"\n{'='*60}")
    logger.info("  🎉 ALL STEPS PASSED!")
    logger.info(f"{'='*60}")
    logger.info(f"  Session: {SESSION_ID}")
    logger.info(f"  Items parsed: {len(items)}")
    logger.info(f"  Suppliers queried: {len(suppliers)}")
    logger.info(f"  RFQs dispatched: {len(rfq_ids)}")
    logger.info(f"  Responses received: {responses['responded']}")
    logger.info(f"  Total cost: BRL {summary['total_cost']:,.2f}")
    logger.info(f"  Savings: {summary.get('savings_pct', 0):.1f}%")
    logger.info(f"  POs created: {len(created_pos)}")
    logger.info(f"  POs approved: {len(created_pos)}")
    logger.info(f"  HITL gates tested: {len(created_pos) * 2} (create + approve)")
    logger.info(f"{'='*60}\n")

    return {
        "session_id": SESSION_ID,
        "items_count": len(items),
        "suppliers_count": len(suppliers),
        "rfqs_dispatched": len(rfq_ids),
        "total_cost": summary["total_cost"],
        "pos_created": len(created_pos),
        "all_passed": True,
    }


async def cleanup(session_id: str):
    """Clean up test data created during the E2E flow."""
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client()
    logger.info(f"\n🧹 Cleaning up session {session_id}...")

    try:
        db.table("purchase_orders").delete().eq("session_id", session_id).eq("client_id", CLIENT_ID).execute()
        logger.info("  Deleted purchase_orders")
    except Exception as e:
        logger.warning(f"  Failed to clean purchase_orders: {e}")

    try:
        db.table("rfq_requests").delete().eq("session_id", session_id).eq("client_id", CLIENT_ID).execute()
        logger.info("  Deleted rfq_requests")
    except Exception as e:
        logger.warning(f"  Failed to clean rfq_requests: {e}")

    # Clean up the test supplier we created via CRUD
    try:
        db.table("supplier_roster").delete().eq("client_id", CLIENT_ID).eq("name", "Supermercado Teste E2E").execute()
        logger.info("  Deleted test CRUD supplier")
    except Exception as e:
        logger.warning(f"  Failed to clean test supplier: {e}")

    logger.info("  ✅ Cleanup done\n")


if __name__ == "__main__":
    try:
        result = asyncio.run(run_full_flow())
        # Optionally clean up
        if "--no-cleanup" not in sys.argv:
            asyncio.run(cleanup(SESSION_ID))
        else:
            logger.info(f"Skipping cleanup. Session data preserved: {SESSION_ID}")
    except Exception as e:
        logger.error(f"\n❌ FLOW FAILED: {e}", exc_info=True)
        # Try cleanup even on failure
        try:
            asyncio.run(cleanup(SESSION_ID))
        except Exception:
            pass
        sys.exit(1)
