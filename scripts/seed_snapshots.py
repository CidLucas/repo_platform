#!/usr/bin/env python3
"""seed_snapshots.py — Populate sample snapshots for all 4 dimensions.

Generates realistic snapshot payloads for financeiro, clientes, agenda,
and compras dimensions and upserts them into shared_business_memory via
the shared_memory_upsert tool.

Usage:
    python scripts/seed_snapshots.py [--client-id UUID]
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot_id() -> str:
    return str(uuid.uuid4())


# ── Financeiro ───────────────────────────────────────────────────────────

FINANCEIRO_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_por": "seed_snapshots",
    "ultimo_update": _iso_now(),
    "versao": 1,
    "template_version": 1,
    "fontes": ["get_cash_position v2", "get_recent_transactions v1"],
    "confianca": 0.95,
}

FINANCEIRO_BODY = {
    "snapshot_id": "",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_em": _iso_now(),
    "vigencia_inicio": "2025-06-12T00:00:00Z",
    "vigencia_fim": "2025-06-19T00:00:00Z",
    "indicadores": [
        {"nome": "saldo_atual", "valor": 152000, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "receita_periodo", "valor": 48700, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "despesa_periodo", "valor": 35200, "unidade": "BRL", "tendencia": "baixa"},
        {"nome": "fluxo_liquido", "valor": 13500, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "contas_a_pagar", "valor": 22000, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "contas_a_receber", "valor": 31000, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "inadimplencia_percentual", "valor": 2.1, "unidade": "%", "tendencia": "baixa"},
    ],
    "alertas": [],
    "resumo_executivo": "Semana positiva com fluxo líquido de BRL 13.500. "
                       "Inadimplência controlada em 2,1%. Contas a receber "
                       "superam contas a pagar.",
}

# ── Clientes ─────────────────────────────────────────────────────────────

CLIENTES_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "clientes",
    "periodo": "diario",
    "gerado_por": "seed_snapshots",
    "ultimo_update": _iso_now(),
    "versao": 1,
    "template_version": 1,
    "fontes": ["get_active_clients", "get_nps_scores v1"],
    "confianca": 0.90,
}

CLIENTES_BODY = {
    "snapshot_id": "",
    "dimensao": "clientes",
    "periodo": "diario",
    "gerado_em": _iso_now(),
    "vigencia_inicio": "2025-06-19T00:00:00Z",
    "vigencia_fim": "2025-06-20T00:00:00Z",
    "indicadores": [
        {"nome": "total_clientes_ativos", "valor": 124, "unidade": "count", "tendencia": "estavel"},
        {"nome": "novos_clientes_periodo", "valor": 2, "unidade": "count", "tendencia": "alta"},
        {"nome": "churn_periodo", "valor": 0, "unidade": "count", "tendencia": "estavel"},
        {"nome": "nps_medio", "valor": 74, "unidade": "score", "tendencia": "alta"},
        {"nome": "ltv_medio", "valor": 8700, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "ticket_medio", "valor": 435, "unidade": "BRL", "tendencia": "alta"},
    ],
    "alertas": [],
    "resumo_executivo": "Dia sem churn. Base ativa estável com 124 clientes. "
                       "NPS em 74, acima da meta de 70.",
}

# ── Agenda ───────────────────────────────────────────────────────────────

AGENDA_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "agenda",
    "periodo": "mensal",
    "gerado_por": "seed_snapshots",
    "ultimo_update": _iso_now(),
    "versao": 1,
    "template_version": 1,
    "fontes": ["get_today_meetings", "get_weekly_meetings v2"],
    "confianca": 0.88,
}

AGENDA_BODY = {
    "snapshot_id": "",
    "dimensao": "agenda",
    "periodo": "mensal",
    "gerado_em": _iso_now(),
    "vigencia_inicio": "2025-06-01T00:00:00Z",
    "vigencia_fim": "2025-06-30T00:00:00Z",
    "indicadores": [
        {"nome": "reunioes_hoje", "valor": 3, "unidade": "count"},
        {"nome": "reunioes_semana", "valor": 16, "unidade": "count"},
        {"nome": "followups_pendentes", "valor": 5, "unidade": "count"},
        {"nome": "contatos_a_cobrar", "valor": 2, "unidade": "count"},
    ],
    "alertas": [],
    "resumo_executivo": "Mês de junho com 16 reuniões na semana atual. "
                       "5 follow-ups pendentes de ação.",
}

# ── Compras ──────────────────────────────────────────────────────────────

COMPRAS_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "compras",
    "periodo": "semanal",
    "gerado_por": "seed_snapshots",
    "ultimo_update": _iso_now(),
    "versao": 1,
    "template_version": 1,
    "fontes": ["get_open_purchase_orders v1", "get_critical_stock v1"],
    "confianca": 0.92,
}

COMPRAS_BODY = {
    "snapshot_id": "",
    "dimensao": "compras",
    "periodo": "semanal",
    "gerado_em": _iso_now(),
    "vigencia_inicio": "2025-06-12T00:00:00Z",
    "vigencia_fim": "2025-06-19T00:00:00Z",
    "indicadores": [
        {"nome": "total_pos_abertas", "valor": 14, "unidade": "count", "tendencia": "estavel"},
        {"nome": "estoque_critico", "valor": 2, "unidade": "count", "tendencia": "baixa"},
        {"nome": "fornecedores_com_pendencia", "valor": 4, "unidade": "count", "tendencia": "estavel"},
        {"nome": "pedidos_em_analise", "valor": 3, "unidade": "count", "tendencia": "baixa"},
    ],
    "alertas": [],
    "resumo_executivo": "Semana estável em compras. 14 POs abertas, 2 itens "
                       "em estoque crítico, 4 fornecedores com pendência.",
}

# ── Seed data ────────────────────────────────────────────────────────────

SEED_ENTRIES = [
    ("financeiro", "semanal", FINANCEIRO_BODY, FINANCEIRO_FRONTMATTER),
    ("clientes", "diario", CLIENTES_BODY, CLIENTES_FRONTMATTER),
    ("agenda", "mensal", AGENDA_BODY, AGENDA_FRONTMATTER),
    ("compras", "semanal", COMPRAS_BODY, COMPRAS_FRONTMATTER),
]


async def main(client_id: str) -> int:
    """Upsert seed snapshots into shared_business_memory."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from tool_pool_api.server.tool_modules.memory_module import (
        _shared_memory_upsert_logic,
    )

    for dimensao, periodo, body, fm in SEED_ENTRIES:
        body["snapshot_id"] = _snapshot_id()
        fm["gerado_em"] = _iso_now()
        fm["ultimo_update"] = fm["gerado_em"]
        entity_name = f"{dimensao}:{periodo}"
        key = body["gerado_em"]

        try:
            result = await _shared_memory_upsert_logic(
                client_id=client_id,
                entity_type="snapshot",
                entity_name=entity_name,
                key=key,
                body=body,
                frontmatter=fm,
                source="migration",
                confidence=fm["confianca"],
            )
            print(f"Upserted: {entity_name}/{key}  v{result['version']}")
        except Exception as exc:
            print(f"Failed upsert {entity_name}: {exc}")
            return 1

    print(f"Done. {len(SEED_ENTRIES)} snapshots seeded for client {client_id}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed snapshot templates into shared_business_memory"
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("BLU_CLIENT_ID", "00000000-0000-0000-0000-000000000000"),
        help="Client UUID to seed snapshots for",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.client_id)))
