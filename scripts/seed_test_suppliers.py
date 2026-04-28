#!/usr/bin/env python3
"""
Seed test suppliers into supplier_roster for RFQ Agent testing.

Creates sample suppliers with categories, contact info, MOQ rules,
and payment terms for Phase 1 & 2 testing.

Prerequisites:
    - RFQ tables created (supabase/migrations/20260413_create_rfq_tables.sql)
    - Phase 2 columns added (supabase/migrations/20260413_phase2_rfq_enhancements.sql)
    - Environment: SUPABASE_URL, SUPABASE_SERVICE_KEY

Usage:
    # From repo root, with .env loaded:
    python scripts/seed_test_suppliers.py

    # Specify a client_id:
    python scripts/seed_test_suppliers.py --client-id YOUR_CLIENT_UUID

    # Dry-run:
    python scripts/seed_test_suppliers.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_supabase_client" / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Test suppliers data
TEST_SUPPLIERS = [
    {
        "name": "Distribuidora ABC Materiais",
        "contact_email": "vendas@abcmateriais.com.br",
        "contact_phone": "+5511999990001",
        "categories": ["construção", "ferragens", "materiais"],
        "payment_terms": "30 dias",
        "delivery_days_avg": 5,
        "moq_rules": {"default": 50, "Parafuso M6": 500, "Porca M6": 500},
        "metadata": {"cnpj": "12.345.678/0001-01", "rating": 4.5},
    },
    {
        "name": "Fornecedor XYZ Industrial",
        "contact_email": "cotacoes@xyzindustrial.com.br",
        "contact_phone": "+5511999990002",
        "categories": ["industrial", "ferragens", "EPI"],
        "payment_terms": "30/60 dias",
        "delivery_days_avg": 7,
        "moq_rules": {"default": 100},
        "metadata": {"cnpj": "98.765.432/0001-02", "rating": 4.2},
    },
    {
        "name": "Casa do Parafuso Premium",
        "contact_email": "orcamento@casadoparafuso.com.br",
        "contact_phone": "+5511999990003",
        "categories": ["ferragens", "fixadores", "construção"],
        "payment_terms": "à vista / 15 dias",
        "delivery_days_avg": 3,
        "moq_rules": {"default": 0},
        "metadata": {"cnpj": "11.222.333/0001-03", "rating": 4.8},
    },
    {
        "name": "Mega Suprimentos Ltda",
        "contact_email": "compras@megasuprimentos.com.br",
        "contact_phone": "+5511999990004",
        "categories": ["escritório", "limpeza", "materiais"],
        "payment_terms": "60 dias",
        "delivery_days_avg": 10,
        "moq_rules": {"default": 200},
        "metadata": {"cnpj": "44.555.666/0001-04", "rating": 3.9},
    },
    {
        "name": "TechParts Componentes",
        "contact_email": "vendas@techparts.com.br",
        "contact_phone": "+5511999990005",
        "categories": ["eletrônicos", "industrial", "automação"],
        "payment_terms": "30 dias",
        "delivery_days_avg": 14,
        "moq_rules": {"default": 10, "Sensor de temperatura": 5},
        "metadata": {"cnpj": "77.888.999/0001-05", "rating": 4.6},
    },
]


def get_default_client_id() -> str | None:
    """Try to find a client_id from clientes_blu."""
    try:
        from supabase import create_client

        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        db = create_client(url, key)

        result = db.table("clientes_blu").select("client_id").limit(1).execute()
        if result.data:
            return result.data[0]["client_id"]
    except Exception as e:
        logger.warning(f"Could not auto-detect client_id: {e}")
    return None


def seed_suppliers(client_id: str, dry_run: bool = False) -> int:
    """Seed test suppliers for the given client_id."""
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    db = create_client(url, key)

    count = 0
    for supplier in TEST_SUPPLIERS:
        record = {
            "id": str(uuid4()),
            "client_id": client_id,
            "name": supplier["name"],
            "contact_email": supplier["contact_email"],
            "contact_phone": supplier["contact_phone"],
            "categories": supplier["categories"],
            "payment_terms": supplier.get("payment_terms", ""),
            "delivery_days_avg": supplier.get("delivery_days_avg", 0),
            "moq_rules": supplier.get("moq_rules", {}),
            "metadata": supplier.get("metadata", {}),
            "is_active": True,
        }

        if dry_run:
            logger.info(f"  [DRY-RUN] Would insert: {record['name']}")
        else:
            try:
                db.table("supplier_roster").insert(record).execute()
                logger.info(f"  ✅ {record['name']}")
                count += 1
            except Exception as e:
                logger.error(f"  ❌ {record['name']}: {e}")

    return count


def main():
    parser = argparse.ArgumentParser(description="Seed test suppliers for RFQ Agent")
    parser.add_argument("--client-id", help="Client UUID to seed suppliers for")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    args = parser.parse_args()

    client_id = args.client_id
    if not client_id:
        client_id = get_default_client_id()
        if not client_id:
            logger.error(
                "No client_id provided and none found in clientes_blu.\n"
                "Usage: python scripts/seed_test_suppliers.py --client-id YOUR_UUID"
            )
            sys.exit(1)
        logger.info(f"Auto-detected client_id: {client_id}")

    logger.info(f"\nSeeding {len(TEST_SUPPLIERS)} test suppliers for client {client_id}...\n")
    count = seed_suppliers(client_id, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"DRY-RUN: Would insert {len(TEST_SUPPLIERS)} suppliers")
    else:
        print(f"✅ Seeded {count}/{len(TEST_SUPPLIERS)} suppliers successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
