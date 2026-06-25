"""RED test — Finance Indicators (B-4) — Indicadores Financeiros.

GOAL:
    BKL-024 — Cálculo métricas financeiras errado (DSO/DPO/CCC null).
    Indicadores financeiros precisam ser calculados a partir dos dados
    disponíveis ou tratados graciosamente com fallback, sem nunca
    travar o frontend.

BEHAVIOR:
    B-4 Indicadores Financeiros (Behavior 4/5 do BATCH #201).

AC:
    AC1 — get_finance_indicators RPC existe e consulta tabelas reais
          para retornar receita_liquida não-zero quando há dados.
    AC2 — dso_dias, dpo_dias, ccc_dias retornam null quando tabelas
          de contas a pagar/receber não existem, mas fallback zeros
          com period quando a consulta falha.
    AC3 — working_capital_ratio e margem_operacional_perc têm fallback
          (try/catch no TS ou COALESCE no SQL).
    AC4 — Nenhum campo retorna erro que trave o frontend — try/catch
          em getFinanceIndicators() OU retry:0/loading-timeout no hook.

Anti-Goals:
    1. NÃO introduzir mocks de DB ou rede.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO modificar código de produção.
    4. NÃO escrever asserts que passam no estado atual — deve ser RED.

Estado atual (RED):
    - AC1: analytics_v2.get_finance_indicators NÃO está definida na
           baseline_v2.sql. public.get_finance_indicators (linha 2316)
           apenas faz SELECT * FROM analytics_v2.get_finance_indicators(p_period)
           — função que NÃO existe em analytics_v2.
    - AC2: dso_dias/dpo_dias/ccc_dias não têm fallback no SQL.
           getFinanceIndicators() em analytics.ts NÃO tem try/catch.
    - AC3: working_capital_ratio e margem_operacional_perc só têm
           numOrNull — sem fallback caseiro quando RPC falha.
    - AC4: getFinanceIndicators() chama callDimensionRpc sem try/catch.
           useFinanceIndicators em useAnalytics.ts (linha 174-182)
           não tem retry:false nem loading-timeout.
"""

import re
from pathlib import Path

import pytest

# ── Paths ──

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ANALYTICS_TS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "analytics.ts"
BASELINE_V2_PATH = (
    REPO_ROOT / "supabase" / "migrations" / "20260523999999_baseline_v2.sql"
)
USE_ANALYTICS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useAnalytics.ts"


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure source-inspection test, no DB."""
    yield


def _read_text(path: Path) -> str:
    assert path.exists(), f"Arquivo nao encontrado: {path}"
    return path.read_text(encoding="utf-8")


def _baseline_sql() -> str:
    return _read_text(BASELINE_V2_PATH)


def _analytics_ts() -> str:
    return _read_text(ANALYTICS_TS_PATH)


def _use_analytics_ts() -> str:
    return _read_text(USE_ANALYTICS_PATH)


def _extract_function_body(
    source: str, fn_name: str, start_marker: str = "export const"
) -> str:
    """Extrai o corpo de uma arrow function nomeada via brace counting."""
    pattern = (
        re.escape(start_marker)
        + r"\s+"
        + re.escape(fn_name)
        + r"\s*(?:<[^>]+>)?\s*=\s*async\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*=>\s*\{"
    )
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    j = body_start
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            j += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                j += 2
                continue
            j += 1
            continue
        if in_string is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_string:
                in_string = None
                j += 1
                continue
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            j += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    if depth != 0:
        return ""
    return source[body_start : j - 1]


def _extract_public_finance_indicators_body(sql: str) -> str:
    """Extrai o corpo de public.get_finance_indicators do SQL."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.get_finance_indicators"
        r"\s*\([^)]*\)[^$]*\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    if not match:
        return ""

    body_start = match.end()
    close_match = re.search(r"\$function\$\s*;", sql[body_start:], re.IGNORECASE)
    if not close_match:
        return ""
    return sql[body_start : body_start + close_match.start()]


# ══════════════════════════════════════════════════════════════
# AC1 — analytics_v2.get_finance_indicators DEVE existir com
#       consulta a tabelas reais (fato_transacoes, etc.)
# ══════════════════════════════════════════════════════════════


def test_b4_finance_ac1_rpc_must_exist_and_query_real_tables():
    """AC1 — get_finance_indicators RPC DEVE existir em analytics_v2
    e consultar tabelas reais para retornar receita_liquida nao-zero.

    GOAL: BKL-024 — receita_liquida deve vir de fato_transacoes.

    Hoje (RED): public.get_finance_indicators (linha 2316) so faz
    SELECT * FROM analytics_v2.get_finance_indicators(p_period),
    e analytics_v2.get_finance_indicators NAO existe em lugar nenhum
    da baseline.
    """
    sql = _baseline_sql()

    # Procura por analytics_v2.get_finance_indicators definida
    analytics_v2_pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_finance_indicators"
        r"\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = analytics_v2_pattern.search(sql)

    assert match, (
        "AC1 violada — RED. A funcao `analytics_v2.get_finance_indicators` "
        f"NAO esta definida em {BASELINE_V2_PATH}.\n\n"
        "Hoje apenas o wrapper `public.get_finance_indicators` existe (linha 2316), "
        "que delega para `analytics_v2.get_finance_indicators(p_period)` — "
        "funcao que NAO existe no schema analytics_v2. Isso faz o RPC retornar "
        "erro em runtime.\n\n"
        "GREEN: Criar `analytics_v2.get_finance_indicators(p_period text)` "
        "com logica que consulta fato_transacoes para retornar "
        "receita_liquida e demais indicadores financeiros."
    )


# ══════════════════════════════════════════════════════════════
# AC2 — dso_dias/dpo_dias/ccc_dias null se tabelas nao existem,
#       fallback zeros com period
# ══════════════════════════════════════════════════════════════


def test_b4_finance_ac2_dso_dpo_ccc_fallback_zeros_with_period():
    """AC2 — dso_dias/dpo_dias/ccc_dias DEVEM ter fallback.

    GOAL: BKL-024 — DSO/DPO/CCC null nao podem quebrar o frontend.

    Hoje (RED):
        - SQL: public.get_finance_indicators so delega sem fallback
        - TS: getFinanceIndicators() usa numOrNull para estes campos,
          sem try/catch no callDimensionRpc — se RPC falha, throw.
        - NENHUM mecanismo de fallback (COALESCE/UNION ALL/try/catch)
          garante zeros estruturados com period quando tabelas
          contas_a_pagar/receber nao existem.
    """
    # Check SQL fallback
    sql = _baseline_sql()
    sql_body = _extract_public_finance_indicators_body(sql)
    sql_body_normalized = re.sub(r"\s+", " ", sql_body) if sql_body else ""

    sql_has_fallback = bool(
        re.search(
            r"\b(?:COALESCE|UNION\s+ALL|IS\s+NULL|CASE\s+WHEN|IFNULL|NULLIF)\b",
            sql_body_normalized,
            re.IGNORECASE,
        )
    )

    # Check TS fallback (try/catch)
    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getFinanceIndicators")
    ts_has_try = bool(re.search(r"\btry\s*\{", fn_body)) if fn_body else False
    ts_has_catch = (
        bool(re.search(r"\bcatch\s*[({]", fn_body)) if fn_body else False
    )
    ts_has_fallback = ts_has_try and ts_has_catch

    has_any_fallback = sql_has_fallback or ts_has_fallback

    assert has_any_fallback, (
        "AC2 violada — RED. dso_dias/dpo_dias/ccc_dias NAO tem fallback.\n\n"
        "A funcao `getFinanceIndicators()` em analytics.ts (linha 434-453) "
        "chama `callDimensionRpc('get_finance_indicators', period) SEM try/catch.\n"
        f"  SQL fallback (COALESCE/etc): {'SIM' if sql_has_fallback else 'NAO'}\n"
        f"  TS try/catch: {'SIM' if ts_has_fallback else 'NAO'}\n\n"
        "Quando o RPC get_finance_indicators falha (ex: analytics_v2 nao existe, "
        "tabelas contas_a_pagar/receber nao existem), o erro borbulha "
        "sem ser tratado.\n\n"
        "GREEN: Adicionar try/catch em getFinanceIndicators() que retorna "
        "zeros estruturados com period no catch, OU COALESCE no SQL garantindo "
        "que dso_dias/dpo_dias/ccc_dias sejam null ou 0 conforme o caso."
    )


# ══════════════════════════════════════════════════════════════
# AC3 — working_capital_ratio e margem_operacional_perc fallback
# ══════════════════════════════════════════════════════════════


def test_b4_finance_ac3_working_capital_and_margem_operacional_fallback():
    """AC3 — working_capital_ratio e margem_operacional_perc DEVEM
    ter fallback (try/catch no TS ou COALESCE no SQL).

    GOAL: BKL-024 — working_capital_ratio e margem_operacional_perc
    nao podem quebrar o frontend quando dados nao estao disponiveis.

    Hoje (RED):
        - SQL: public.get_finance_indicators so delega — sem fallback
        - TS: numOrNull — retorna null se RPC retorna null, mas throw
          se o RPC nao existe ou falha.
    """
    sql = _baseline_sql()
    sql_body = _extract_public_finance_indicators_body(sql)
    sql_body_normalized = re.sub(r"\s+", " ", sql_body) if sql_body else ""

    sql_has_coalesce = bool(
        re.search(r"\bCOALESCE\s*\(", sql_body_normalized, re.IGNORECASE)
    )
    sql_has_case_when = bool(
        re.search(r"\bCASE\s+WHEN\b", sql_body_normalized, re.IGNORECASE)
    )
    sql_has_fallback = sql_has_coalesce or sql_has_case_when

    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getFinanceIndicators")
    ts_has_try = bool(re.search(r"\btry\s*\{", fn_body)) if fn_body else False
    ts_has_catch = (
        bool(re.search(r"\bcatch\s*[({]", fn_body)) if fn_body else False
    )
    ts_has_fallback = ts_has_try and ts_has_catch

    has_fallback = sql_has_fallback or ts_has_fallback

    assert has_fallback, (
        "AC3 violada — RED. working_capital_ratio e margem_operacional_perc "
        "NAO tem fallback.\n\n"
        f"  SQL fallback (COALESCE/CASE): {'SIM' if sql_has_fallback else 'NAO'}\n"
        f"  TS try/catch: {'SIM' if ts_has_fallback else 'NAO'}\n\n"
        "Hoje ambos os campos usam `numOrNull` que retorna null se o valor "
        "do RPC for null — mas se o RPC lancar erro (funcao nao existe, "
        "query falha), o erro borbulha sem tratamento.\n\n"
        "GREEN: Adicionar try/catch em getFinanceIndicators() que retorna "
        "zeros estruturados, OU COALESCE na funcao SQL para garantir "
        "fallback mesmo que as tabelas auxiliares (ex: contas_a_pagar) "
        "nao existam."
    )


# ══════════════════════════════════════════════════════════════
# AC4 — Nenhum campo retorna erro que trave o frontend
# ══════════════════════════════════════════════════════════════


def test_b4_finance_ac4_must_not_crash_frontend():
    """AC4 — NENHUM campo pode travar o frontend.

    GOAL: BKL-024 — Erro em getFinanceIndicators nao pode quebrar
    a pagina de financas/FinanceiroRoom.

    Hoje (RED):
        - getFinanceIndicators() chama callDimensionRpc sem try/catch
        - useFinanceIndicators nao tem retry:false nem loading-timeout

    GREEN: Adicionar try/catch em getFinanceIndicators() OU
    retry:0/loading-timeout em useFinanceIndicators().
    """
    # Check API layer
    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getFinanceIndicators")
    assert fn_body, (
        f"Nao foi possivel extrair o corpo de `getFinanceIndicators` "
        f"em {ANALYTICS_TS_PATH}."
    )

    api_has_try = bool(re.search(r"\btry\s*\{", fn_body))
    api_has_catch = bool(re.search(r"\bcatch\s*[({]", fn_body))
    api_protected = api_has_try and api_has_catch

    # Check hook layer
    hook_source = _use_analytics_ts()
    hook_has_retry_false = bool(
        re.search(
            r"useFinanceIndicators.*?(?:\breTry\s*:\s*(?:false|0)\b)",
            hook_source,
            re.DOTALL,
        )
    )
    hook_has_loading_timeout = bool(
        re.search(
            r"\b(?:LOADING_TIMEOUT_MS|loadingTimeout|loading_timeout)\b",
            hook_source,
        )
    )
    hook_has_set_timeout = bool(re.search(r"\bsetTimeout\s*\(", hook_source))
    hook_protected = (
        hook_has_retry_false or hook_has_loading_timeout or hook_has_set_timeout
    )

    assert api_protected or hook_protected, (
        "AC4 violada — RED. `getFinanceIndicators()` NAO tem protecao "
        "contra travar o frontend.\n\n"
        f"  API layer (analytics.ts): try/catch={'SIM' if api_protected else 'NAO'}\n"
        f"  Hook layer (useAnalytics.ts): retry:false={'SIM' if hook_has_retry_false else 'NAO'}, "
        f"loading-timeout={'SIM' if hook_has_loading_timeout else 'NAO'}\n\n"
        "Hoje:\n"
        "  1) analytics.ts getFinanceIndicators() (linha 434-453) chama "
        "callDimensionRpc('get_finance_indicators', period) SEM try/catch.\n"
        "  2) callDimensionRpc (linha 131-136) faz `throw new Error(...)` "
        "em caso de erro — sem fallback.\n"
        "  3) useAnalytics.ts useFinanceIndicators (linha 174-182) usa "
        "useQuery sem retry:false e sem loading-timeout.\n\n"
        "GREEN: Adicionar try/catch em getFinanceIndicators() que retorna "
        "zeros estruturados + period no catch, OU adicionar retry:0 "
        "no useQuery do hook."
    )
