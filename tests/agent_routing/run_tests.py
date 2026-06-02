#!/usr/bin/env python3
"""
Blu Agent Routing Test Runner
==============================
Fires all 50 test queries against the agent API and records results.

Usage:
    # Set environment vars first:
    export BLU_API_URL=http://localhost:8003
    export BLU_JWT=<your_supabase_jwt>

    python run_tests.py
    python run_tests.py --layer 1          # only layer 1
    python run_tests.py --layer 2          # only layer 2
    python run_tests.py --ids 1,4,21       # specific query IDs
    python run_tests.py --sleep 3          # custom sleep between requests
    python run_tests.py --dry-run          # print queries without calling API
    python run_tests.py --output results.json

Results are saved to results.json and a summary printed to stdout.
Check traces on Langfuse: filter by tag "routing-test" + session_id prefix "test-".
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = os.environ.get("BLU_API_URL", "http://localhost:8003")
JWT = os.environ.get("BLU_JWT", "")
DEFAULT_SLEEP = 2  # seconds between requests

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    id: int
    layer: int
    query: str
    expected_agent: str   # slug or descriptive label
    note: str = ""        # routing mechanism or risk note

TESTS: list[TestCase] = [
    # --- Layer 1: Routing Coverage -------------------------------------------
    TestCase(1,  1, "Cria uma rotina de digest financeiro toda segunda às 8h",
             "platform", "keyword: 'cria uma rotina'"),
    TestCase(2,  1, "Ativa o monitor de estoque baixo",
             "platform", "keyword: 'ativa'"),
    TestCase(3,  1, "Define uma meta de R$80k de faturamento para junho",
             "platform", "keyword: 'define uma meta'"),
    TestCase(4,  1, "O que está puxando meu custo para cima esse mês?",
             "synthesis", "keyword: 'puxando' in _SYNTHESIS_KEYWORDS"),
    TestCase(5,  1, "Como meu faturamento está afetando minha capacidade de compras?",
             "synthesis", "2 dims: financeiro + compras"),
    TestCase(6,  1, "Qual é o momento certo para fazer um investimento maior em estoque?",
             "synthesis", "keyword: 'investimento'"),
    TestCase(7,  1, "Quero fazer uma cotação de arroz com os fornecedores",
             "compras", "keyword: 'cotação'"),
    TestCase(8,  1, "Manda mensagem no whatsapp pro fornecedor Atacado XYZ",
             "compras", "keyword: 'whatsapp fornecedor'"),
    TestCase(9,  1, "Agenda uma reunião para quinta às 14h",
             "agenda", "keyword: 'agenda uma'"),
    TestCase(10, 1, "Verifica conflito de agenda para semana que vem",
             "agenda", "keyword: 'conflito de agenda'"),
    TestCase(11, 1, "Emite uma nota fiscal para o cliente João Silva, R$1500, serviço de consultoria",
             "fiscal-agent", "keyword: 'nota fiscal'"),
    TestCase(12, 1, "Qual meu regime tributário atual?",
             "fiscal-agent", "keyword: 'regime tributário'"),
    TestCase(13, 1, "Redige um SOP de processo de compras",
             "doc-writer", "keyword: 'sop de'"),
    TestCase(14, 1, "Cria um relatório de performance do time",
             "doc-writer", "keyword: 'cria um relatório'"),
    TestCase(15, 1, "Quais clientes têm maior risco de churn?",
             "crm", "keyword: 'clientes em risco'"),
    TestCase(16, 1, "Analisa o LTV por segmento de clientes",
             "crm", "keyword: 'ltv'"),
    TestCase(17, 1, "Qual é o foco estratégico para o próximo trimestre?",
             "estrategia", "keyword: 'foco estratégico'"),
    TestCase(18, 1, "Monta um plano trimestral para crescimento",
             "estrategia", "keyword: 'plano trimestral'"),
    TestCase(19, 1, "Qual foi meu faturamento do mês passado?",
             "frontdesk", "no keyword match → fallback SQL"),
    TestCase(20, 1, "Quantos clientes ativos tenho?",
             "frontdesk", "no keyword match → fallback SQL"),

    # --- Layer 2: Edge Cases & Gaps ------------------------------------------
    TestCase(21, 2, "Quais clientes devo priorizar essa semana?",
             "synthesis", "RISK: 2 dims (clientes+agenda) may not match if terms differ"),
    TestCase(22, 2, "Quanto meu estoque parado está custando?",
             "synthesis", "RISK: 'custo'+estoque = 2 dims, should trigger synthesis"),
    TestCase(23, 2, "Cria uma meta e me mostra o dashboard de metas",
             "platform", "platform check first — should win"),
    TestCase(24, 2, "Preciso de uma cotação e também verificar a agenda do fornecedor",
             "compras", "first match wins: 'cotação' fires before 'agenda'"),
    TestCase(25, 2, "Agenda uma reunião e define uma meta para o resultado",
             "platform", "RISK: platform check is first but 'agenda' fires scheduler keyword"),
    TestCase(26, 2, "Análise de cohort dos clientes novos",
             "crm", "keyword: 'cohort'"),
    TestCase(27, 2, "Planejamento para o próximo mês",
             "estrategia", "RISK: 'planejamento' is synthesis keyword, not estrategia keyword"),
    TestCase(28, 2, "Qual fornecedor tem melhor histórico de entrega?",
             "compras", "keyword: 'fornecedor'"),
    TestCase(29, 2, "Escreve uma ata da reunião de hoje",
             "doc-writer", "keyword: 'ata da reunião'"),
    TestCase(30, 2, "Qual o prazo da entrega do projeto X?",
             "agenda", "keyword: 'prazo'"),

    # --- Layer 3: Tool Invocation --------------------------------------------
    TestCase(31, 3, "Lista os fornecedores cadastrados",
             "compras", "tool: list_suppliers"),
    TestCase(32, 3, "Verifica minha agenda para amanhã",
             "agenda", "tool: query_calendar"),
    TestCase(33, 3, "Quais rotinas tenho ativas?",
             "platform", "tool: listar_rotinas_catalogo"),
    TestCase(34, 3, "Quais são minhas metas?",
             "platform", "tool: listar_metas"),
    TestCase(35, 3, "Mostra os clientes inativos nos últimos 90 dias",
             "crm", "tool: execute_sql"),
    TestCase(36, 3, "Busca documentos sobre processo de vendas",
             "frontdesk", "tool: executar_rag_cliente"),
    TestCase(37, 3, "Qual meu ticket médio do trimestre?",
             "frontdesk", "tool: execute_sql"),
    TestCase(38, 3, "Quais SKUs estão abaixo do estoque mínimo?",
             "frontdesk", "tool: execute_sql"),
    TestCase(39, 3, "Mostra os boards do Monday",
             "agenda", "tool: monday_list_boards"),
    TestCase(40, 3, "Manda mensagem no Slack para o time comercial sobre a reunião de amanhã",
             "crm", "RISK: 'slack' may not be in crm keywords; may fall to frontdesk"),

    # --- Layer 4: Graceful Failure -------------------------------------------
    TestCase(41, 4, "Emite nota fiscal pro cliente XYZ",
             "fiscal-agent", "should ask for valor and descrição"),
    TestCase(42, 4, "Manda cotação para os fornecedores",
             "compras", "should ask for produto and quantidade"),
    TestCase(43, 4, "Cria uma rotina",
             "platform", "should elicit trigger and objetivo"),
    TestCase(44, 4, "Define uma meta",
             "platform", "should ask for dimensão, valor, prazo"),
    TestCase(45, 4, "O que está acontecendo com meu negócio?",
             "synthesis", "'impacto' missing but broad strategic intent"),
    TestCase(46, 4, "Qual foi o resultado em 1990?",
             "frontdesk", "should return no data without hallucinating"),
    TestCase(47, 4, "Agenda uma reunião amanhã às 99h",
             "agenda", "should reject invalid time"),
    TestCase(48, 4, "Quais clientes no planeta Marte?",
             "frontdesk", "should return no data without hallucinating"),
    TestCase(49, 4, "Cria tudo de uma vez",
             "platform", "should ask for clarification"),
    TestCase(50, 4, "Obrigado",
             "frontdesk", "should respond gracefully with no tool calls"),
]

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    id: int
    layer: int
    query: str
    expected_agent: str
    note: str
    session_id: str
    status: str              # "ok" | "error" | "skipped"
    http_status: Optional[int] = None
    actual_agent: str = ""   # agent slug returned by the API
    passed: bool = False     # actual_agent == expected_agent
    response_preview: str = ""
    error: str = ""
    duration_ms: int = 0
    timestamp: str = ""

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

async def call_agent(client: httpx.AsyncClient, query: str, session_id: str) -> tuple[int, str, str, str, int]:
    """
    POST /v1/chat — returns (http_status, response_text, agent_slug, error, duration_ms).
    Uses the session_id as-is (no pre-creation needed — Redis checkpointer).
    """
    payload = {
        "message": query,
        "session_id": session_id,
        "tags": ["routing-test"],
    }
    headers = {
        "Authorization": f"Bearer {JWT}",
        "Content-Type": "application/json",
    }
    try:
        t0 = time.monotonic()
        r = await client.post(f"{API_URL}/v1/chat", json=payload, headers=headers, timeout=60)
        elapsed = int((time.monotonic() - t0) * 1000)
        if r.status_code == 200:
            data = r.json()
            agent_slug = data.get("agent_slug") or data.get("agent") or data.get("routed_to") or ""
            return r.status_code, data.get("response", "")[:500], agent_slug, "", elapsed
        return r.status_code, "", "", r.text[:200], elapsed
    except Exception as exc:
        return 0, "", "", str(exc), 0

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run(tests: list[TestCase], sleep_s: float, dry_run: bool) -> list[TestResult]:
    results: list[TestResult] = []
    run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    async with httpx.AsyncClient() as client:
        for i, tc in enumerate(tests):
            session_id = f"test-{run_id}-{tc.id:02d}"
            ts = datetime.utcnow().isoformat()

            if dry_run:
                print(f"[DRY] #{tc.id:02d} L{tc.layer} → {tc.expected_agent!r:20s} | {tc.query}")
                results.append(TestResult(
                    id=tc.id, layer=tc.layer, query=tc.query,
                    expected_agent=tc.expected_agent, note=tc.note,
                    session_id=session_id, status="skipped", timestamp=ts,
                ))
                continue

            print(f"[{i+1:02d}/{len(tests)}] #{tc.id:02d} L{tc.layer} → {tc.expected_agent!r:20s} | {tc.query[:70]}")

            http_status, response, actual_agent, error, duration_ms = await call_agent(client, tc.query, session_id)
            passed = http_status == 200 and actual_agent == tc.expected_agent

            if http_status == 200:
                status = "ok"
                mark = "✅" if passed else "⚠️ "
                print(f"         {mark} {duration_ms}ms | agent={actual_agent or '?'} | session={session_id}")
                print(f"         💬 {response[:120]!r}")
            else:
                status = "error"
                passed = False
                print(f"         ❌ HTTP {http_status} | {error[:80]}")

            results.append(TestResult(
                id=tc.id, layer=tc.layer, query=tc.query,
                expected_agent=tc.expected_agent, note=tc.note,
                session_id=session_id, status=status,
                http_status=http_status, actual_agent=actual_agent, passed=passed,
                response_preview=response, error=error,
                duration_ms=duration_ms, timestamp=ts,
            ))

            if i < len(tests) - 1:
                time.sleep(sleep_s)

    return results

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(results: list[TestResult]):
    ok = [r for r in results if r.status == "ok"]
    err = [r for r in results if r.status == "error"]
    skip = [r for r in results if r.status == "skipped"]
    passed = [r for r in ok if r.passed]
    wrong = [r for r in ok if not r.passed]

    print("\n" + "="*60)
    print(f"SUMMARY — {len(results)} queries")
    print(f"  ✅ pass:    {len(passed)}/{len(ok)} (HTTP ok)")
    print(f"  ⚠️  wrong:   {len(wrong)}  (HTTP ok but wrong agent)")
    print(f"  ❌ error:   {len(err)}")
    print(f"  ⏭️  skipped: {len(skip)}")

    if wrong:
        print("\nWrong agent:")
        for r in wrong:
            print(f"  #{r.id:02d} L{r.layer} expected={r.expected_agent!r:20s} got={r.actual_agent!r:20s} | {r.query[:55]}")

    if err:
        print("\nFailed (HTTP error):")
        for r in err:
            print(f"  #{r.id:02d} L{r.layer} [{r.expected_agent}] {r.query[:60]}")
            print(f"       HTTP {r.http_status} | {r.error[:80]}")

    if ok:
        avg_ms = sum(r.duration_ms for r in ok) // len(ok)
        print(f"\nAvg latency (ok): {avg_ms}ms")

    print("\nLangfuse traces: filter by tag 'routing-test' or session_id prefix 'test-'")
    print("="*60)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Blu agent routing test runner")
    p.add_argument("--layer", type=int, choices=[1,2,3,4], help="Run only this layer")
    p.add_argument("--ids", type=str, help="Comma-separated test IDs, e.g. 1,4,21")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Sleep between requests (default: 2s)")
    p.add_argument("--dry-run", action="store_true", help="Print queries without calling API")
    p.add_argument("--output", type=str, default="results.json", help="Output JSON file")
    return p.parse_args()

async def main():
    args = parse_args()

    # Filter tests
    tests = TESTS
    if args.layer:
        tests = [t for t in tests if t.layer == args.layer]
    if args.ids:
        ids = {int(x.strip()) for x in args.ids.split(",")}
        tests = [t for t in tests if t.id in ids]

    if not tests:
        print("No tests match the filter.")
        sys.exit(1)

    if not args.dry_run and not JWT:
        print("ERROR: BLU_JWT environment variable not set.")
        print("  export BLU_JWT=<your_supabase_jwt>")
        sys.exit(1)

    print(f"\nBlu Agent Routing Tests")
    print(f"  API: {API_URL}")
    print(f"  Queries: {len(tests)}")
    print(f"  Sleep: {args.sleep}s between requests")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Output: {args.output}")
    print()

    results = await run(tests, args.sleep, args.dry_run)
    print_summary(results)

    # Save JSON
    out = [asdict(r) for r in results]
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())
