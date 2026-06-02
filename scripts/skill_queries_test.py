#!/usr/bin/env python3
"""
skill_queries_test.py — 20 queries para testar as skills do Blu.

Executa sequencialmente contra POST http://localhost:8003/v1/chat
usando o token gerado por get_test_token.py.

Uso:
  python3 scripts/skill_queries_test.py
  python3 scripts/skill_queries_test.py --only crm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")

API_BASE = "http://localhost:8003"

# ---------------------------------------------------------------------------
# 20 queries cobrindo as skills do sistema
# ---------------------------------------------------------------------------
QUERIES = [
    # --- L1: communication ---
    {"tag": "communication", "msg": "Preciso rascunhar um e-mail de resposta para um cliente que reclamou da entrega atrasada do pedido #1042. Tom: cordial e proativo."},
    {"tag": "communication", "msg": "Crie uma mensagem de WhatsApp para enviar ao fornecedor Metalúrgica Silva pedindo cotação de 500 unidades do parafuso M8x30."},

    # --- L1: ledger ---
    {"tag": "ledger", "msg": "Registre no ledger uma entrada de R$4.800 referente a pagamento do cliente Padaria Estrela, recebido hoje via PIX."},
    {"tag": "ledger", "msg": "Anote uma saída de R$1.200 de aluguel do galpão pago em 01/06/2026, categoria despesa_operacional."},

    # --- L1: data_access (SQL) ---
    {"tag": "data_access", "msg": "Qual foi o total de vendas em maio de 2026? Agrupa por categoria de produto."},
    {"tag": "data_access", "msg": "Mostre os 5 clientes com maior valor em aberto (contas a receber) neste momento."},

    # --- L1: document_io ---
    {"tag": "document_io", "msg": "Leia o contrato do cliente João Silva e me diga qual é a data de vencimento e o valor mensal."},

    # --- L3: morning_plan ---
    {"tag": "morning_plan", "msg": "Gere o plano do dia para hoje. Empresa: Metalúrgica Pinheiro. Temos 3 entregas agendadas, DRE de maio fechado ontem e 2 reuniões na parte da tarde."},

    # --- L3: end_of_day_digest ---
    {"tag": "end_of_day_digest", "msg": "Faça o digest de encerramento de hoje: vendas foram R$12.400, 4 novos pedidos, 1 reclamação resolvida e equipe completou o inventário do estoque."},

    # --- L3: weekly_summary ---
    {"tag": "weekly_summary", "msg": "Gere o resumo semanal da semana 23/05 a 30/05/2026. Receita total R$58k, 12 novos clientes, ticket médio R$4.800, taxa de inadimplência 3%."},

    # --- L3: collection_messages ---
    {"tag": "collection_messages", "msg": "Preciso de 3 mensagens de cobrança para o cliente Restaurante Bom Sabor que está 15 dias em atraso com R$2.300. Tom: amigável mas firme."},

    # --- L3: followup_draft ---
    {"tag": "followup_draft", "msg": "Escreva um follow-up para a proposta enviada há 5 dias para a Construtora Horizonte. Proposta era de sistema de gestão por R$890/mês."},

    # --- L3: reactivation_proposal ---
    {"tag": "reactivation_proposal", "msg": "Monte uma proposta de reativação para o cliente Farmácia Central que não compra há 4 meses. Última compra foi de suprimentos de escritório R$780."},

    # --- L3: satisfaction_survey ---
    {"tag": "satisfaction_survey", "msg": "Crie uma pesquisa de satisfação rápida (3 perguntas) para enviar após a conclusão de um serviço de manutenção."},

    # --- L3: meeting_brief ---
    {"tag": "meeting_brief", "msg": "Prepare um brief para reunião com o fornecedor Distribuidora Norte amanhã às 14h. Pauta: renegociação de prazo de pagamento e novo catálogo 2026."},

    # --- L3: hidden_patterns ---
    {"tag": "hidden_patterns", "msg": "Analise os padrões ocultos nas vendas dos últimos 90 dias. Temos queda toda segunda-feira e pico nas quintas. O que pode estar causando isso?"},

    # --- L3: competitor_analysis ---
    {"tag": "competitor_analysis", "msg": "Faça uma análise de concorrentes para uma metalúrgica de médio porte no interior de SP que compete com importados chineses em parafusos e fixadores."},

    # --- L3: reconciliation_report ---
    {"tag": "reconciliation_report", "msg": "Preciso de um relatório de conciliação para maio/2026. Saldo bancário: R$47.200. Saldo no sistema: R$45.800. Diferença de R$1.400."},

    # --- L3: insights_synthesis ---
    {"tag": "insights_synthesis", "msg": "Sintetize os insights estratégicos do dia: financeiro positivo (+12% vs semana passada), 2 clientes em risco de churn, agenda com gap na sexta-feira, estoque de produto A em nível crítico."},

    # --- L3: inventory_digest ---
    {"tag": "inventory_digest", "msg": "Gere o digest de estoque e compras: produto Parafuso M6 com 50 unidades (mínimo 200), 3 pedidos de compra em aberto com Fornecedor X atrasado 10 dias."},
]

# ---------------------------------------------------------------------------


def get_token() -> str:
    token_file = Path("/tmp/blu_test_jwt.txt")
    if not token_file.exists():
        sys.exit("Token não encontrado. Rode: python3 tests/agent_routing/get_test_token.py")
    return token_file.read_text().strip()


def chat(message: str, token: str, session_id: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/v1/chat",
        json={"message": message, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    return {"status": resp.status_code, "body": resp.json() if resp.content else {}}


def truncate(text: str, n: int = 300) -> str:
    return text[:n] + "..." if len(text) > n else text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Filtrar por tag (ex: crm, ledger)")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay entre requests (s)")
    args = parser.parse_args()

    token = get_token()
    queries = [q for q in QUERIES if not args.only or args.only in q["tag"]]

    print(f"\n{'='*70}")
    print(f"Blu Skill Queries Test — {len(queries)} queries")
    print(f"API: {API_BASE}")
    print(f"{'='*70}\n")

    results = []
    for i, q in enumerate(queries, 1):
        session_id = str(uuid.uuid4())
        print(f"[{i:02d}/{len(queries)}] tag={q['tag']}")
        print(f"  Q: {truncate(q['msg'], 120)}")

        t0 = time.monotonic()
        try:
            result = chat(q["msg"], token, session_id)
            elapsed = time.monotonic() - t0
            status = result["status"]
            body = result["body"]

            if status == 200:
                reply = body.get("message") or body.get("response") or str(body)
                agent = body.get("agent_type") or body.get("agent") or "?"
                print(f"  A ({agent}, {elapsed:.1f}s): {truncate(reply, 300)}")
                results.append({"tag": q["tag"], "ok": True, "agent": agent, "elapsed": elapsed})
            else:
                err = body.get("detail") or str(body)[:200]
                print(f"  ❌ HTTP {status}: {err}")
                results.append({"tag": q["tag"], "ok": False, "error": f"HTTP {status}: {err}"})
        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"  ❌ Erro: {e}")
            results.append({"tag": q["tag"], "ok": False, "error": str(e)})

        print()
        time.sleep(args.delay)

    # Summary
    ok = sum(1 for r in results if r["ok"])
    fail = len(results) - ok
    avg = sum(r.get("elapsed", 0) for r in results if r["ok"]) / max(ok, 1)

    print(f"{'='*70}")
    print(f"RESULTADO: {ok}/{len(results)} ok  |  {fail} falhas  |  avg {avg:.1f}s por query")

    if fail:
        print("\nFalhas:")
        for r in results:
            if not r["ok"]:
                print(f"  [{r['tag']}] {r.get('error', '?')}")

    # Write JSON report
    report_path = Path("/tmp/blu_skill_test_results.json")
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nReport salvo em: {report_path}")
    print(f"{'='*70}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
