"""RED test for behavior B-3 AC#2 — getCommercialTopClients com dados não-zero.

GOAL:
    Garantir que a função ``getCommercialTopClients`` em
    ``apps/blu_v3/src/api/analytics.ts`` chama a RPC
    ``get_commercial_top_clients`` com os parâmetros corretos e que
    a RPC retorna colunas compatíveis com a interface ``TopClientRow``
    (``client_id``, ``nome``, ``receita``, ``pedidos``, ``share_perc``, ``period``).

BEHAVIOR:
    B-3 — AC#2: getCommercialTopClients() retorna dados de receita
    não-zero.

AC (Acceptance Criteria):
    AC#2 — A RPC ``get_commercial_top_clients`` (definida no baseline)
    deve aceitar os parâmetros ``p_period`` e ``p_limit`` e retornar
    colunas compatíveis com o mapeamento em ``analytics.ts``:
      - ``client_id`` (bigint)
      - ``nome`` (text, mapeado de ``cliente_nome`` ou ``nome``)
      - ``receita`` (numeric, mapeado de ``total_revenue`` ou ``receita``)
      - ``pedidos`` (bigint, mapeado de ``total_volume`` ou ``pedidos``)
      - ``share_perc`` (numeric | null) — share de receita sobre o total
      - ``period`` (text) — periodo da consulta

DECISÃO:
    Estratégia: source_inspection (regex sobre arquivos .sql e .ts)
    Arquivos alvo:
      - supabase/migrations/20260523999999_baseline_v2.sql (definição RPC)
      - apps/blu_v3/src/api/analytics.ts (código TS)

Estado atual (TRUE RED):
    A RPC ``get_commercial_top_clients`` no baseline (linha ~2271) é
    definida SEM parâmetros e retorna colunas diferentes das esperadas
    pelo TypeScript:
      - RPC: ``cliente_nome`` | TS espera: ``nome``
      - RPC: ``total_revenue`` | TS espera: ``receita``
      - RPC: ``total_volume``  | TS espera: ``pedidos``
      - RPC sem: ``share_perc``, ``period``
    A assinatura ``()`` vs ``(p_period, p_limit)`` também é incompatível.

Anti-Goals:
    1. NÃO modificar arquivos de produção.
    2. NÃO exigir execução real do Supabase.
    3. NÃO depender de fixtures de banco de dados.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)
ANALYTICS_TS_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "analytics.ts"
)

TARGET_RPC = "get_commercial_top_clients"
TARGET_TS_FN = "getCommercialTopClients"


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    yield


def _baseline_text() -> str:
    assert BASELINE_PATH.exists(), f"Baseline não encontrado em {BASELINE_PATH}"
    return BASELINE_PATH.read_text()


def _analytics_text() -> str:
    assert ANALYTICS_TS_PATH.exists(), f"analytics.ts não encontrado em {ANALYTICS_TS_PATH}"
    return ANALYTICS_TS_PATH.read_text()


def _extract_rpc_signature(sql: str, rpc_name: str) -> str:
    """Extrai a declaração completa da RPC (CREATE OR REPLACE FUNCTION
    até o primeiro $function$;) ou string vazia."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\."
        + re.escape(rpc_name)
        + r".*?\$function\$\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    return match.group(0) if match else ""


def _extract_rpc_return_columns(signature: str) -> list[str]:
    """Extrai os nomes das colunas do RETURNS TABLE(...) de uma RPC."""
    m = re.search(
        r"RETURNS\s+TABLE\s*\(([^)]+)\)",
        signature,
        re.IGNORECASE,
    )
    if not m:
        return []
    cols_raw = m.group(1)
    return [c.split()[0].strip().lower() for c in cols_raw.split(",")]


def _extract_rpc_params(signature: str) -> list[str]:
    """Extrai os nomes dos parâmetros declarados na RPC."""
    m = re.search(
        r"FUNCTION\s+public\." + re.escape(TARGET_RPC) + r"\s*\(([^)]*)\)",
        signature,
        re.IGNORECASE,
    )
    if not m:
        return []
    params_text = m.group(1).strip()
    if not params_text:
        return []
    return [p.split()[0].strip().lower() for p in params_text.split(",")]


def _extract_function_body(ts_code: str, fn_name: str) -> str:
    """Extrai o corpo da arrow function ``export const <fn_name> = async (…) => { … }``
    de analytics.ts, devolvendo o bloco entre { } mais externo, ou string vazia."""
    # Aceita: export const fnName = async (...) => {
    # Ou: export const fnName = (...) => {
    pattern = re.compile(
        r"export\s+const\s+"
        + re.escape(fn_name)
        + r"\s*=\s*(?:async\s+)?\([^)]*\)\s*:\s*Promise<TopClientRow\[\]>\s*=>\s*\{",
        re.DOTALL,
    )
    match = pattern.search(ts_code)
    if not match:
        return ""
    start = match.end()  # primeiro caractere APÓS o {
    # Precisa encontrar o } de fechamento no nível correto
    depth = 1
    i = start
    while i < len(ts_code) and depth > 0:
        if ts_code[i] == "{":
            depth += 1
        elif ts_code[i] == "}":
            depth -= 1
        i += 1
    return ts_code[start : i - 1] if depth == 0 else ""


def _extract_ts_mapping(ts_code: str, fn_name: str) -> dict[str, str]:
    """Extrai o mapeamento coluna SQL → campo TS do return map do
    ``getCommercialTopClients`` em analytics.ts."""
    body = _extract_function_body(ts_code, fn_name)
    if not body:
        return {}

    # Extrai o .map((r) => ({ ... }))
    # Pattern: .map( ... ) => ({ fields })
    map_pattern = re.compile(
        r"\.map\s*\([^)]*\)\s*=>\s*\(\{",
        re.DOTALL,
    )
    map_match = map_pattern.search(body)
    if not map_match:
        return {}
    start = map_match.end()
    # Encontra o } que fecha o objeto
    depth = 1
    i = start
    while i < len(body) and depth > 0:
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
        i += 1
    mapping_text = body[start : i - 1] if depth == 0 else ""

    # Extrai pares nome_campo: num(r?.coluna_sql)
    mapping: dict[str, str] = {}
    for line in mapping_text.split(","):
        line = line.strip()
        m2 = re.match(
            r"(\w+)\s*:\s*(?:num|numOrNull|String|Boolean)\(r\?\.(\w+)\)",
            line,
        )
        if m2:
            mapping[m2.group(2)] = m2.group(1)  # sql_col → ts_field
    return mapping


def _extract_rpc_call_params(ts_code: str, fn_name: str) -> list[str]:
    """Extrai os parâmetros passados na chamada .rpc() dentro da
    função getCommercialTopClients."""
    body = _extract_function_body(ts_code, fn_name)
    if not body:
        return []

    # Procura .rpc('get_commercial_top_clients', { ... })
    rpc_pattern = re.compile(
        r"\.rpc\s*\(\s*['\"]" + re.escape(TARGET_RPC) + r"['\"]\s*,\s*\{([^}]+)\}",
        re.DOTALL,
    )
    rpc_match = rpc_pattern.search(body)
    if not rpc_match:
        return []
    params_text = rpc_match.group(1)
    return [p.strip().split(":")[0].strip() for p in params_text.split(",") if ":" in p]


def test_b3_ac2_commercial_top_clients_rpc_compativel():
    """AC#2: A RPC get_commercial_top_clients deve ter parâmetros e
    colunas de retorno compatíveis com o que analytics.ts espera.

    Falha (RED) se:
      - A RPC não aceita p_period (vindo do TS)
      - As colunas que o TS mapeia não existem no RETURNS TABLE da RPC
      - A RPC retorna valores null (sem COALESCE/fallback) para
        colunas críticas como receita
    """
    sql = _baseline_text()
    ts_code = _analytics_text()

    # ── (1) Extrai definições ──────────────────────────────────────

    rpc_sig = _extract_rpc_signature(sql, TARGET_RPC)
    assert rpc_sig, (
        f"RPC {TARGET_RPC} não encontrada no baseline "
        f"{BASELINE_PATH.relative_to(REPO_ROOT)}."
    )

    rpc_params = _extract_rpc_params(rpc_sig)
    rpc_cols = _extract_rpc_return_columns(rpc_sig)
    ts_mapping = _extract_ts_mapping(ts_code, TARGET_TS_FN)
    ts_call_params = _extract_rpc_call_params(ts_code, TARGET_TS_FN)

    # ── (2) Verifica parâmetros ────────────────────────────────────

    missing_params = [
        p for p in ts_call_params if p not in rpc_params
    ]
    if missing_params:
        pytest.fail(
            "AC#2 violado: a RPC "
            f"public.{TARGET_RPC} (baseline "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)}) é declarada "
            f"com os parâmetros {rpc_params}, mas "
            f"getCommercialTopClients em analytics.ts chama "
            f".rpc('{TARGET_RPC}', {{ {', '.join(ts_call_params)} "
            f"— parâmetros {missing_params} não declarados na RPC.\n\n"
            "A chamada .schema(ANALYTICS_SCHEMA).rpc(...) do Supabase "
            "pode ignorar parâmetros extras silenciosamente, fazendo "
            "com que a RPC retorne dados SEM o filtro de período "
            "esperado (resultado: dados de todos os períodos, ou "
            "erro silencioso → R$ 0 no frontend — ver BKL-028).\n\n"
            "Correção (GREEN): adicionar os parâmetros à RPC:\n"
            "  CREATE OR REPLACE FUNCTION "
            "public.get_commercial_top_clients(\n"
            "    p_period text DEFAULT '30d',\n"
            "    p_limit integer DEFAULT 10\n"
            "  )\n"
            "  RETURNS TABLE(...)\n"
            "  LANGUAGE ... AS ..."
        )

    # ── (3) Verifica colunas de retorno ────────────────────────────

    # O TS espera (via .map()): r?.client_id, r?.nome, r?.receita,
    # r?.pedidos, r?.share_perc, r?.period
    # A RPC retorna: client_id, cliente_nome, total_volume,
    # total_revenue, last_purchase
    missing_cols = [
        sql_col
        for sql_col, ts_field in ts_mapping.items()
        if sql_col not in rpc_cols
    ]
    if missing_cols:
        pytest.fail(
            "AC#2 violado: a RPC "
            f"public.{TARGET_RPC} (baseline "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)}) "
            f"retorna as colunas {rpc_cols}, mas "
            f"getCommercialTopClients em analytics.ts espera "
            f"acessar as colunas {list(ts_mapping.keys())} "
            f"(via r?.<coluna> no .map()).  "
            f"As colunas {missing_cols} NÃO existem no RETURNS "
            "TABLE da RPC.\n\n"
            "Isto significa que o mapeamento em analytics.ts "
            "sempre receberá undefined para estas colunas, "
            "resultando em zeros (via num(undefined)=0) em vez "
            "dos valores reais do banco — explicando BKL-028 "
            "(Top clientes por receita R$ 0).\n\n"
            "Correção (GREEN): alinhar as colunas da RPC com o "
            "que o TypeScript espera:\n"
            "  RETURNS TABLE(\n"
            "    client_id bigint,\n"
            "    nome text,\n"
            "    receita numeric,\n"
            "    pedidos bigint,\n"
            "    share_perc numeric,\n"
            "    period text\n"
            "  )\n"
            "Ou atualizar o .map() em analytics.ts para usar os "
            "nomes reais das colunas da RPC."
        )

    # ── (4) Verifica fallback para valores null ────────────────────
    # Se a RPC não usa COALESCE nas colunas de receita, dados
    # ausentes retornam NULL em vez de 0.
    if "total_revenue" in rpc_cols:
        # Verifica se total_revenue tem COALESCE na query
        query_pattern = re.compile(
            r"SELECT.*?" + re.escape(TARGET_RPC) + r".*?\$function\$",
            re.DOTALL,
        )
        query_match = query_pattern.search(sql)
        # ... continua no próximo teste específico
