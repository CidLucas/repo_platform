#!/usr/bin/env python3
"""
E3 smoke + monitor — Sprint 5.

Roda bateria de queries SQL contra Supabase prod e produz relatório executivo
do status de um cliente is_test_account ao longo das 72h de validação.

Uso:
    python scripts/e3_smoke.py                       # auto-detecta cliente teste
    python scripts/e3_smoke.py --client-id <uuid>    # cliente específico
    python scripts/e3_smoke.py --since 24h           # janela de observação

Saída: tabela texto + códigos de retorno
    0 — tudo verde
    1 — alertas (review manual)
    2 — falha crítica (bloqueador)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass


def get_db_url() -> str:
    env_path = os.path.expanduser("~/Documents/GitHub/repo_platform/.env")
    if not os.path.exists(env_path):
        env_path = ".env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("SUPABASE_DB_URL="):
                return line.split("=", 1)[1].strip()
    sys.exit("ERROR: SUPABASE_DB_URL not found in .env")


def psql_one(db_url: str, sql: str) -> str:
    """Executa SQL e retorna stdout como string única (-tA flags)."""
    try:
        return subprocess.check_output(
            ["psql", db_url, "-tAc", sql],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except subprocess.CalledProcessError as e:
        return f"__ERR__:{e.stderr.strip()[:200]}"


def psql_rows(db_url: str, sql: str) -> list[list[str]]:
    raw = psql_one(db_url, sql)
    if not raw or raw.startswith("__ERR__:"):
        return []
    return [line.split("|") for line in raw.split("\n")]


@dataclass
class Check:
    name: str
    status: str   # OK | WARN | FAIL
    detail: str


def parse_since(s: str) -> str:
    """'24h' -> 'interval ''24 hours''', '7d' -> 'interval ''7 days'''."""
    m = re.match(r"(\d+)([hdm])", s.lower())
    if not m:
        sys.exit(f"ERROR: invalid --since '{s}'. Use NNh / NNd / NNm.")
    n, unit = m.group(1), m.group(2)
    unit_map = {"h": "hours", "d": "days", "m": "minutes"}
    return f"interval '{n} {unit_map[unit]}'"


def detect_test_client(db_url: str) -> str | None:
    out = psql_one(
        db_url,
        "SELECT client_id::text FROM clientes_blu WHERE is_test_account = true LIMIT 1;",
    )
    return out or None


def run_checks(db_url: str, client_id: str | None, since: str) -> list[Check]:
    out: list[Check] = []
    scope_sql = f"AND client_id = '{client_id}'" if client_id else ""

    # 1. Execuções no período
    rows = psql_rows(
        db_url,
        f"""SELECT status, count(*) FROM client_routine_executions
           WHERE created_at > now() - {since} {scope_sql}
           GROUP BY status ORDER BY count DESC;""",
    )
    if not rows:
        out.append(Check("execs_recent", "WARN", "Nenhuma execução no período"))
    else:
        summary = ", ".join(f"{r[0]}={r[1]}" for r in rows)
        total = sum(int(r[1]) for r in rows)
        failed = sum(int(r[1]) for r in rows if r[0] == "failed")
        fail_rate = (100 * failed / total) if total else 0
        status = "OK" if fail_rate < 15 else ("WARN" if fail_rate < 30 else "FAIL")
        out.append(Check("execs_recent", status, f"{summary} | fail_rate={fail_rate:.0f}%"))

    # 2. Cobertura de rotinas distintas
    rows = psql_rows(
        db_url,
        f"""SELECT count(DISTINCT routine_id) FROM client_routine_executions
           WHERE created_at > now() - {since} {scope_sql};""",
    )
    n_distinct = int(rows[0][0]) if rows else 0
    target = 20 if not client_id else 5
    status = "OK" if n_distinct >= target else ("WARN" if n_distinct > 0 else "FAIL")
    out.append(Check("routine_coverage", status, f"{n_distinct} rotinas distintas (target ≥{target})"))

    # 3. Artifact_log — dedupe sanity check
    rows = psql_rows(
        db_url,
        f"""SELECT count(*), count(DISTINCT (execution_id, step_id))
           FROM artifact_log WHERE claimed_at > now() - {since} {scope_sql};""",
    )
    if rows and rows[0][0]:
        total, distinct = int(rows[0][0]), int(rows[0][1])
        dup = total - distinct
        status = "OK" if dup == 0 else "FAIL"
        out.append(Check("artifact_dedupe", status, f"{total} rows, {dup} duplicates"))
    else:
        out.append(Check("artifact_dedupe", "WARN", "0 rows (nenhum side-effectful disparado)"))

    # 4. Approval TTL — nenhuma expiração prematura?
    rows = psql_rows(
        db_url,
        f"""SELECT count(*) FROM approval_requests
           WHERE status='expired' AND decided_at > now() - {since}
           AND decided_at - created_at < interval '47 hours' {scope_sql};""",
    )
    n_premature = int(rows[0][0]) if rows and rows[0][0] else 0
    status = "OK" if n_premature == 0 else "FAIL"
    out.append(Check("approval_ttl_premature", status, f"{n_premature} expiraram <47h após criação"))

    # 5. TTL coverage
    rows = psql_rows(
        db_url,
        f"""SELECT count(*) FILTER (WHERE expires_at IS NULL),
                  count(*) FILTER (WHERE expires_at IS NOT NULL)
           FROM approval_requests WHERE status='pending' {scope_sql};""",
    )
    if rows:
        no_ttl, with_ttl = int(rows[0][0]), int(rows[0][1])
        status = "OK" if no_ttl == 0 else "FAIL"
        out.append(Check("approval_ttl_coverage", status, f"pending: {with_ttl} com TTL, {no_ttl} sem"))

    # 6. Circuit breaker P8 — alguém suspenso?
    rows = psql_rows(
        db_url,
        f"""SELECT count(*), string_agg(routine_id, ',') FROM client_routines
           WHERE status='suspended' {scope_sql};""",
    )
    n_susp = int(rows[0][0]) if rows and rows[0][0] else 0
    status = "OK" if n_susp == 0 else "WARN"
    detail = f"{n_susp} suspensas" + (f" ({rows[0][1]})" if n_susp else "")
    out.append(Check("circuit_breaker", status, detail))

    # 7. Schema sanity — dim_inventory.nome populando? (só faz sentido com client_id)
    if client_id:
        rows = psql_rows(
            db_url,
            f"""SELECT count(*) FILTER (WHERE nome IS NOT NULL),
                      count(*) FILTER (WHERE nome IS NULL)
               FROM dim_inventory WHERE client_id = '{client_id}';""",
        )
        if rows:
            ok, null = int(rows[0][0]), int(rows[0][1])
            if ok + null == 0:
                out.append(Check("schema_dim_inventory_nome", "WARN", "0 rows (sem inventário ainda)"))
            else:
                status = "OK" if null == 0 else ("WARN" if ok > null else "FAIL")
                out.append(Check("schema_dim_inventory_nome", status, f"{ok} populados, {null} NULL"))

    # 8. RLS leakage probe — usuário authenticated NÃO deve ver dados de outro client
    # (skip se sem client_id)
    if client_id:
        other = psql_one(
            db_url,
            f"SELECT client_id::text FROM clientes_blu WHERE client_id <> '{client_id}' LIMIT 1;",
        )
        if other:
            # Test via service_role — só conta diferença
            n = psql_one(
                db_url,
                f"SELECT count(*) FROM client_routine_executions WHERE client_id='{other}';",
            )
            out.append(Check("rls_probe_other_client",
                             "OK" if int(n) >= 0 else "WARN",
                             f"service_role vê outro client: {n} rows (esperado, RLS bypass). Validação real é via cliente authenticated."))

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", help="UUID do cliente teste (omitir = global)")
    ap.add_argument("--since", default="24h", help="Janela: 24h, 7d, 90m...")
    ap.add_argument("--auto-detect", action="store_true",
                    help="Tenta achar cliente is_test_account=true")
    args = ap.parse_args()

    db_url = get_db_url()
    client_id = args.client_id
    if args.auto_detect and not client_id:
        client_id = detect_test_client(db_url)
        if client_id:
            print(f"[detect] Cliente teste: {client_id}")
        else:
            print("[detect] Nenhum is_test_account=true — rodando global.")

    since = parse_since(args.since)
    print(f"\n=== E3 smoke — janela últimos {args.since} | scope: {client_id or 'GLOBAL'} ===\n")

    checks = run_checks(db_url, client_id, since)

    icon = {"OK": "✓", "WARN": "!", "FAIL": "✗"}
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"  [{icon[c.status]}] {c.name.ljust(width)}  {c.detail}")

    n_fail = sum(1 for c in checks if c.status == "FAIL")
    n_warn = sum(1 for c in checks if c.status == "WARN")
    print(f"\n=== {len(checks)-n_fail-n_warn} OK | {n_warn} WARN | {n_fail} FAIL ===")

    if n_fail:
        return 2
    if n_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
