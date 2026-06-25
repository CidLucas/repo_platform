"""RED test — Fix Supply/Compras Indicators (ETL Loading) — Behavior 5/5.

GOAL:
    Supply/Compras indicators should not be stuck on infinite "carregando".
    Os indicadores de suprimentos (rfqs_abertas, spend_periodo, otif_perc,
    lead_time_medio_dias, cost_savings_perc, etc.) precisam ser calculados
    a partir dos dados disponíveis em fato_transacoes ou tratados
    graciosamente com fallback quando o RPC não existir ou falhar.

BEHAVIOR:
    Fix Supply/Compras Indicators (Behavior 5/5).

    No estado atual (RED):
        1. analytics_v2.get_supply_indicators NÃO está definida no schema
           — apenas o wrapper public.get_supply_indicators existe.
        2. public.get_supply_indicators (baseline_v2.sql linha 2783-2790)
           apenas delega: SELECT * FROM analytics_v2.get_supply_indicators(p_period)
        3. getSupplyIndicators() em analytics.ts (linha 501-523) chama
           callDimensionRpc sem try/catch — qualquer falha joga exceção.
        4. useSupplyIndicators em useAnalytics.ts não tem retry:false nem
           loading-timeout — pode ficar em isLoading para sempre.
        5. Não há fallback que retorne zeros estruturados com period metadata.
        6. promised_delivery_at não existe no schema — lead_time_medio_dias
           precisa de aproximação.
        7. ComprasRoom.tsx mostra "Carregando…" sem timeout.

    Após a correção (GREEN), deve:
        a) analytics_v2.get_supply_indicators existir com lógica que
           consulta fato_transacoes.
        b) getSupplyIndicators() envolver callDimensionRpc em try/catch.
        c) No catch, retornar zeros estruturados com { period } preenchido.
        d) Os campos lead_time_medio_dias, otif_perc, cost_savings_perc
           virem null no fallback.
        e) A UI do ComprasRoom mostrar "—" (null) ou 0 em vez de loading
           eterno.
        f) A lacuna de promised_delivery_at estar documentada e
           lead_time_medio_dias usar colunas disponíveis.

AC (Acceptance Criteria):
    AC1 — get_supply_indicators RPC existe ou é criada com retorno default
          no schema analytics_v2.
    AC2 — getSupplyIndicators() não fica mais em "carregando" — try/catch
          no API ou retry:false/loading-timeout no hook.
    AC3 — Supply indicators retornam dados de fato_transacoes (lead_time,
          otif, cost_savings).
    AC4 — Fallback: se RPC não existe, retornar zeros estruturados com
          period metadata.
    AC5 — Se lead_time requer promised_delivery_at (não existe no schema),
          documentar gap e usar dados disponíveis.

Anti-Goals (must NOT be violated):
    1. NÃO introduzir mocks de DB ou rede — teste é source-inspection.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO modificar código de produção.
    4. NÃO escrever asserts que passam no estado atual — deve ser RED.

Estado atual (RED):
    - AC1: analytics_v2.get_supply_indicators NÃO está definida no
           baseline_v2.sql (apenas public.get_supply_indicators existe).
    - AC2: getSupplyIndicators() NÃO tem try/catch, o hook NÃO tem
           retry:false nem loading-timeout.
    - AC3: public.get_supply_indicators NÃO referencia fato_transacoes
           — apenas delega para analytics_v2 que não existe.
    - AC4: SEM fallback no SQL (SELECT * FROM analytics_v2...) e SEM
           try/catch no TS.
    - AC5: promised_delivery_at NÃO existe no schema — documentado apenas
           em docs/backlog/05_frontend_e_metricas.md.
"""
import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ANALYTICS_TS_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "analytics.ts"
)
BASELINE_V2_PATH = (
    REPO_ROOT / "supabase" / "migrations" / "20260523999999_baseline_v2.sql"
)
USE_ANALYTICS_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useAnalytics.ts"
)
COMPRAS_ROOM_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ComprasRoom.tsx"
)
BACKLOG_METRICAS_PATH = (
    REPO_ROOT / "docs" / "backlog" / "05_frontend_e_metricas.md"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é pura inspeção de código, sem DB."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o conteúdo de ``path`` como UTF-8. Falha se o arquivo não existir."""
    assert path.exists(), f"Arquivo não encontrado: {path}"
    return path.read_text(encoding="utf-8")


def _baseline_sql() -> str:
    """Lê o conteúdo da baseline_v2.sql."""
    return _read_text(BASELINE_V2_PATH)


def _analytics_ts() -> str:
    """Lê o conteúdo de apps/blu_v3/src/api/analytics.ts."""
    return _read_text(ANALYTICS_TS_PATH)


def _use_analytics_ts() -> str:
    """Lê o conteúdo de apps/blu_v3/src/hooks/useAnalytics.ts."""
    return _read_text(USE_ANALYTICS_PATH)


def _compras_room_ts() -> str:
    """Lê o conteúdo de ComprasRoom.tsx."""
    return _read_text(COMPRAS_ROOM_PATH)


def _backlog_metricas_md() -> str:
    """Lê o conteúdo de docs/backlog/05_frontend_e_metricas.md."""
    return _read_text(BACKLOG_METRICAS_PATH)


def _extract_function_body(source: str, fn_name: str, start_marker: str = "export const") -> str:
    """Extrai o corpo de uma arrow function nomeada via brace counting.

    Retorna o texto entre as chaves externas. Vazio se não encontrado.
    """
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


def _extract_public_supply_indicators_body(sql: str) -> str:
    """Extrai o corpo de public.get_supply_indicators do SQL."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.get_supply_indicators"
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


# ── AC1 ──────────────────────────────────────────────────────────────────


def test_fix_supply_ac1_analytics_v2_rpc_must_exist():
    """AC1 — get_supply_indicators RPC DEVE existir no schema analytics_v2.

    GOAL: BKL-019 — Supply indicators não podem ficar em "carregando".

    O baseline ``supabase/migrations/20260523999999_baseline_v2.sql``
    define apenas o wrapper ``public.get_supply_indicators`` (linhas
    2783-2790), que faz ``SELECT * FROM
    analytics_v2.get_supply_indicators(p_period)``. A função
    ``analytics_v2.get_supply_indicators`` NÃO é definida em nenhum
    lugar da migration baseline (zero ``CREATE OR REPLACE FUNCTION
    analytics_v2.get_supply_indicators`` no arquivo).

    Esta asserção procura por uma definição ``CREATE OR REPLACE
    FUNCTION analytics_v2.get_supply_indicators`` (com corpo não
    vazio) no baseline. Como a definição NÃO existe, o teste FALHA (RED).

    GREEN: Criar ``analytics_v2.get_supply_indicators(p_period text)``
    com lógica que consulta dim_fornecedores, dim_materiais e
    fato_transacoes para retornar os indicadores de supply.
    """
    sql = _baseline_sql()

    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators"
        r"\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)

    assert match, (
        "AC1 violada — RED. A função `analytics_v2.get_supply_indicators` "
        f"NÃO está definida em {BASELINE_V2_PATH}. "
        "Hoje apenas o wrapper `public.get_supply_indicators` existe, que "
        "delega para `analytics_v2.get_supply_indicators(p_period)` — função "
        "que NÃO existe no schema analytics_v2. Isso faz o RPC retornar "
        "NULL/falhar em runtime, causando loading eterno no ComprasRoom. "
        "A implementação GREEN deve criar a função em analytics_v2 com "
        "consulta às dim tables (dim_fornecedores, fato_transacoes, etc.) "
        "que retorne os indicadores de supply (rfqs_abertas, spend_periodo, "
        "otif_perc, lead_time_medio_dias, cost_savings_perc, etc.)."
    )


# ── AC2 ──────────────────────────────────────────────────────────────────


def test_fix_supply_ac2_get_supply_indicators_must_not_hang_on_loading():
    """AC2 — getSupplyIndicators() NÃO pode ficar em loading eterno.

    GOAL: BKL-019 — Supply indicators não podem ficar em "carregando".

    Existem duas maneiras de evitar o loading eterno:
        a) **try/catch no API**: ``getSupplyIndicators()`` em analytics.ts
           envolve ``callDimensionRpc`` em try/catch que retorna zeros
           estruturados em caso de falha.
        b) **retry:false ou loading-timeout no hook**: ``useSupplyIndicators``
           em useAnalytics.ts tem ``retry: false`` (ou ``retry: 0``) OU
           um mecanismo de loading-timeout (constante ``LOADING_TIMEOUT_MS``
           + setTimeout).

    Hoje (RED):
        - analytics.ts: getSupplyIndicators() chama callDimensionRpc sem
          try/catch (linha 501-523).
        - useAnalytics.ts: useSupplyIndicators() usa useQuery sem
          retry:false e sem loading-timeout (linha 204-212).

    GREEN: Adicionar try/catch em getSupplyIndicators() **OU** adicionar
    retry:0/loading-timeout em useSupplyIndicators().
    """
    # --- Check API layer ---
    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getSupplyIndicators")
    assert fn_body, (
        "Não foi possível extrair o corpo de `getSupplyIndicators` em "
        f"{ANALYTICS_TS_PATH}."
    )

    api_has_try = bool(re.search(r"\btry\s*\{", fn_body))
    api_has_catch = bool(re.search(r"\bcatch\s*[({]", fn_body))
    api_protected = api_has_try and api_has_catch

    # --- Check hook layer ---
    hook_source = _use_analytics_ts()
    hook_has_retry_false = bool(re.search(
        r"useSupplyIndicators.*?(?:\breTry\s*:\s*(?:false|0)\b)",
        hook_source, re.DOTALL
    ))
    hook_has_loading_timeout = bool(re.search(
        r"\b(?:LOADING_TIMEOUT_MS|loadingTimeout|loading_timeout)\b",
        hook_source
    ))
    hook_has_set_timeout = bool(re.search(r"\bsetTimeout\s*\(", hook_source))
    hook_protected = hook_has_retry_false or hook_has_loading_timeout or hook_has_set_timeout

    assert api_protected or hook_protected, (
        "AC2 violada — RED. `getSupplyIndicators()` NÃO tem proteção "
        "contra loading eterno.\n"
        f"  API layer (analytics.ts): try/catch={'SIM' if api_protected else 'NÃO'}\n"
        f"  Hook layer (useAnalytics.ts): retry:false={'SIM' if hook_has_retry_false else 'NÃO'}, "
        f"loading-timeout={'SIM' if hook_has_loading_timeout else 'NÃO'}\n\n"
        "Hoje:\n"
        "  1) analytics.ts getSupplyIndicators() (linha 501-523) chama "
        "callDimensionRpc('get_supply_indicators', period) sem try/catch.\n"
        "  2) callDimensionRpc (linha 131-136) faz `throw new Error(...)` "
        "em caso de erro — sem fallback.\n"
        "  3) useAnalytics.ts useSupplyIndicators (linha 204-212) usa "
        "useQuery sem retry:false e sem loading-timeout.\n\n"
        "Isso significa que se o RPC get_supply_indicators falhar (função "
        "analytics_v2 não existe, DB indisponível, etc.), o erro borbulha "
        "sem ser tratado e o React Query pode ficar em isLoading:true "
        "para sempre.\n\n"
        "GREEN: Adicionar try/catch em getSupplyIndicators() que retorna "
        "zeros + period no catch, OU adicionar retry:0 no useQuery do hook."
    )


# ── AC3 ──────────────────────────────────────────────────────────────────


def test_fix_supply_ac3_must_return_data_from_fato_transacoes():
    """AC3 — Supply indicators DEVEM retornar dados de fato_transacoes.

    GOAL: BKL-019 — lead_time_medio_dias, otif_perc e cost_savings_perc
    devem ser calculados de fato_transacoes.

    Hoje (RED):
        - O corpo de public.get_supply_indicators é apenas:
          ``SELECT * FROM analytics_v2.get_supply_indicators(p_period);``
        - Não há referência a fato_transacoes, lead_time, otif ou
          cost_savings.
        - analytics_v2.get_supply_indicators NÃO existe.

    Esta asserção valida duas coisas:
        1. Se analytics_v2.get_supply_indicators existe, seu corpo deve
           referenciar fato_transacoes.
        2. Se não existe (esperado RED), public.get_supply_indicators
           não referencia fato_transacoes.

    GREEN: A função analytics_v2.get_supply_indicators (ou uma
    reescrita de public.get_supply_indicators) deve consultar
    fato_transacoes com agregações que produzam lead_time_medio_dias,
    otif_perc e cost_savings_perc.
    """
    sql = _baseline_sql()

    # Check if analytics_v2.get_supply_indicators exists at all
    analytics_v2_pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators"
        r"\s*\([^)]*\)",
        re.DOTALL | re.IGNORECASE,
    )
    analytics_v2_exists = analytics_v2_pattern.search(sql) is not None

    if analytics_v2_exists:
        # If analytics_v2 function exists, check it queries fato_transacoes
        body = _extract_public_supply_indicators_body(sql)
        # Fallback: try to find analytics_v2 function body
        analytics_pattern = re.compile(
            r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators"
            r"\s*\([^)]*\)[^$]*\$function\$([^$]+)\$function\$",
            re.DOTALL | re.IGNORECASE,
        )
        analytics_match = analytics_pattern.search(sql)
        if analytics_match:
            body = analytics_match.group(1)
        else:
            body = ""

        body_normalized = re.sub(r"\s+", " ", body)
        references_fato = bool(re.search(
            r"\bfato_transacoes\b", body_normalized, re.IGNORECASE
        ))
        has_lead_time = bool(re.search(
            r"\blead_time\b", body_normalized, re.IGNORECASE
        ))
        has_otif = bool(re.search(
            r"\botif\b", body_normalized, re.IGNORECASE
        ))
        has_cost_savings = bool(re.search(
            r"\bcost_savings\b", body_normalized, re.IGNORECASE
        ))

        has_supply_metrics = references_fato and (has_lead_time or has_otif or has_cost_savings)

        assert has_supply_metrics, (
            "AC3 violada — RED. analytics_v2.get_supply_indicators existe "
            "mas NÃO consulta fato_transacoes para lead_time, otif ou "
            "cost_savings.\n"
            f"  fato_transacoes: {'SIM' if references_fato else 'NÃO'}\n"
            f"  lead_time: {'SIM' if has_lead_time else 'NÃO'}\n"
            f"  otif: {'SIM' if has_otif else 'NÃO'}\n"
            f"  cost_savings: {'SIM' if has_cost_savings else 'NÃO'}\n\n"
            "A implementação GREEN deve garantir que a função consulte "
            "fato_transacoes e calcule/retorne lead_time_medio_dias, "
            "otif_perc e cost_savings_perc."
        )
    else:
        # analytics_v2 function does NOT exist at all — check public wrapper
        body = _extract_public_supply_indicators_body(sql)
        assert body, (
            "Não foi possível extrair o corpo de public.get_supply_indicators "
            f"em {BASELINE_V2_PATH}."
        )

        body_normalized = re.sub(r"\s+", " ", body)
        references_fato = bool(re.search(
            r"\bfato_transacoes\b", body_normalized, re.IGNORECASE
        ))

        assert references_fato, (
            "AC3 violada — RED. O corpo de `public.get_supply_indicators` em "
            f"{BASELINE_V2_PATH} NÃO consulta `fato_transacoes`.\n\n"
            f"Corpo atual: {body_normalized[:120]}...\n\n"
            "Hoje o corpo apenas faz "
            "`SELECT * FROM analytics_v2.get_supply_indicators(p_period)` "
            "(linha 2788), delegando para analytics_v2 que NÃO existe. "
            "A função NÃO consulta fato_transacoes para calcular "
            "lead_time_medio_dias, otif_perc ou cost_savings_perc.\n\n"
            "GREEN: Reescrever a função para consultar fato_transacoes "
            "com agregações que produzam os 3 indicadores de supply, "
            "ou criar analytics_v2.get_supply_indicators que o faça."
        )


# ── AC4 ──────────────────────────────────────────────────────────────────


def test_fix_supply_ac4_must_have_fallback_zeros_with_period():
    """AC4 — DEVE ter fallback de zeros+period quando RPC não existe.

    GOAL: BKL-019 — Supply indicators não podem quebrar se o RPC falhar.

    Existem duas camadas onde o fallback pode ser implementado:

    1. **SQL fallback**: no corpo de public.get_supply_indicators, usar
       COALESCE, UNION ALL, CASE WHEN, IS NULL, ou IFNULL para garantir
       que a função SQL nunca retorne NULL/vazio — mesmo que as tabelas
       estejam vazias ou o RPC não exista.

    2. **TS fallback**: em getSupplyIndicators() em analytics.ts, usar
       try/catch ao redor de callDimensionRpc que retorna um objeto com
       todos os campos numéricos em 0 (ou null) e period preenchido.

    Hoje (RED):
        - SQL: public.get_supply_indicators é só:
          ``SELECT * FROM analytics_v2.get_supply_indicators(p_period)``
          — sem nenhum fallback.
        - TS: getSupplyIndicators() não tem try/catch — qualquer erro
          vira exceção não tratada.

    GREEN: Adicionar fallback em pelo menos uma das camadas (SQL com
    COALESCE/UNION ALL, ou TS com try/catch retornando zeros+period).
    """
    # --- Check SQL fallback ---
    sql = _baseline_sql()
    sql_body = _extract_public_supply_indicators_body(sql)
    sql_body_normalized = re.sub(r"\s+", " ", sql_body) if sql_body else ""

    sql_has_coalesce = bool(re.search(r"\bCOALESCE\s*\(", sql_body_normalized, re.IGNORECASE))
    sql_has_union_all = bool(re.search(r"\bUNION\s+ALL\b", sql_body_normalized, re.IGNORECASE))
    sql_has_is_null = bool(re.search(r"\bIS\s+NULL\b", sql_body_normalized, re.IGNORECASE))
    sql_has_case_when = bool(re.search(r"\bCASE\s+WHEN\b", sql_body_normalized, re.IGNORECASE))
    sql_has_ifnull = bool(re.search(r"\bIFNULL\s*\(|\bNULLIF\s*\(", sql_body_normalized, re.IGNORECASE))

    sql_has_fallback = (
        sql_has_coalesce or sql_has_union_all or sql_has_is_null
        or sql_has_case_when or sql_has_ifnull
    )

    # --- Check TS fallback ---
    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getSupplyIndicators")
    ts_has_try = bool(re.search(r"\btry\s*\{", fn_body)) if fn_body else False
    ts_has_catch = bool(re.search(r"\bcatch\s*[({]", fn_body)) if fn_body else False
    ts_has_fallback = ts_has_try and ts_has_catch

    has_fallback = sql_has_fallback or ts_has_fallback

    assert has_fallback, (
        "AC4 violada — RED. NENHUMA camada tem fallback de zeros+period.\n\n"
        f"  SQL fallback (COALESCE/UNION ALL/IS NULL/CASE WHEN/IFNULL): "
        f"{'SIM' if sql_has_fallback else 'NÃO'}\n"
        f"  TS fallback (try/catch em getSupplyIndicators): "
        f"{'SIM' if ts_has_fallback else 'NÃO'}\n\n"
        "SQL: O corpo atual de public.get_supply_indicators em "
        f"{BASELINE_V2_PATH} é apenas:\n"
        f"  {sql_body_normalized[:120] if sql_body_normalized else '(vazio)'}\n"
        " — sem COALESCE, UNION ALL, IS NULL, CASE WHEN ou IFNULL.\n\n"
        "TS: analytics.ts getSupplyIndicators() NÃO tem try/catch ao redor "
        "de callDimensionRpc (linha 502). Qualquer falha do RPC joga "
        "exceção que não é tratada pela função.\n\n"
        "GREEN: Adicionar fallback em pelo menos uma das camadas:\n"
        "  1. SQL: usar COALESCE(SUM(...), 0) nas agregações + "
        "UNION ALL SELECT 0, 0, ..., p_period se vazio.\n"
        "  2. TS: envolver callDimensionRpc em try/catch que retorna "
        "{ rfqs_abertas: 0, ..., period: period } em caso de erro."
    )


# ── AC5 ──────────────────────────────────────────────────────────────────


def test_fix_supply_ac5_lead_time_gap_documented_and_available_data_used():
    """AC5 — Se lead_time requer promised_delivery_at, lacuna DEVE estar documentada.

    GOAL: BKL-019 — lead_time_medio_dias deve usar dados disponíveis e
    a lacuna de promised_delivery_at deve estar documentada.

    O cálculo ideal de lead_time_medio_dias usa a diferença entre a data
    de criação da requisição e a data de entrega prometida
    (promised_delivery_at). Como essa coluna NÃO existe no schema atual
    (nem em fato_transacoes, nem em approval_requests), a implementação
    precisa:

    1. **Documentar a lacuna**: mencionar em docs/backlog/05_frontend_e_metricas.md
       que promised_delivery_at não existe e que isso afeta o cálculo de
       lead_time/OTIF.

    2. **Usar dados disponíveis**: calcular lead_time_medio_dias usando
       colunas existentes (ex.: data_criacao, data_aprovacao, etc. em
       fato_transacoes ou approval_requests).

    Hoje (RED):
        - promised_delivery_at NÃO existe no schema (não aparece em
          nenhuma migration SQL).
        - docs/backlog/05_frontend_e_metricas.md menciona a lacuna
          (linha 18: "OTIF requer promised_delivery_at em
          approval_requests (não existe — migration necessária)").
        - Mas a implementação de analytics_v2.get_supply_indicators
          NÃO existe ainda — então não podemos verificar se usa
          dados disponíveis.

    GREEN: Garantir que a lacuna está documentada e que
    analytics_v2.get_supply_indicators calcula lead_time_medio_dias
    usando colunas disponíveis (ex.: data_criacao de fato_transacoes).
    """
    # --- Check docs for promised_delivery_at gap ---
    try:
        backlog_md = _backlog_metricas_md()
    except AssertionError:
        backlog_md = ""

    gap_documented = bool(re.search(
        r"promised_delivery_at",
        backlog_md,
        re.IGNORECASE,
    )) if backlog_md else False

    # --- Check if promised_delivery_at exists in schema ---
    sql = _baseline_sql()
    promised_exists_in_schema = bool(re.search(
        r"\bpromised_delivery_at\b",
        sql,
        re.IGNORECASE,
    ))

    # --- Check if analytics_v2.get_supply_indicators uses available data ---
    analytics_pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators"
        r"\s*\([^)]*\)[^$]*\$function\$([^$]+)\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    analytics_match = analytics_pattern.search(sql)

    uses_available_data = False
    if analytics_match:
        analytics_body = analytics_match.group(1)
        body_normalized = re.sub(r"\s+", " ", analytics_body)
        has_data_criacao = bool(re.search(
            r"\bdata_criacao\b", body_normalized, re.IGNORECASE
        ))
        has_data_aprovacao = bool(re.search(
            r"\bdata_aprovacao\b", body_normalized, re.IGNORECASE
        ))
        has_lead_time_calc = bool(re.search(
            r"\blead_time\b", body_normalized, re.IGNORECASE
        ))
        uses_available_data = has_lead_time_calc and (has_data_criacao or has_data_aprovacao)

    # Asserts — AC5 requires BOTH gap documented AND function using available data
    if not promised_exists_in_schema:  # If promised_delivery_at doesn't exist
        # Condition 1: Gap must be documented
        if not gap_documented:
            pytest.fail(
                "AC5 violada — RED. `promised_delivery_at` NÃO existe no schema "
                f"mas a lacuna NÃO está documentada em "
                f"{BACKLOG_METRICAS_PATH}.\n\n"
                "Hoje `promised_delivery_at` não existe em nenhuma tabela do "
                "schema (baseline_v2.sql). O cálculo de lead_time_medio_dias "
                "e OTIF depende dessa coluna para ser preciso. "
                "A documentação em docs/backlog/05_frontend_e_metricas.md "
                "DEVE mencionar essa lacuna.\n\n"
                "GREEN: Adicionar entrada em docs/backlog/05_frontend_e_metricas.md "
                "documentando que promised_delivery_at não existe e que "
                "lead_time/OTIF usam aproximações com colunas disponíveis "
                "(data_criacao, data_aprovacao, etc.)."
            )

        # Condition 2: Even with the gap, analytics_v2.get_supply_indicators
        # must USE available columns (data_criacao, data_aprovacao) as proxy
        # for lead_time calculation — OR the function must exist.
        # Today the function does NOT exist, so Condition 2 is always RED.
        if analytics_match and uses_available_data:
            # Both conditions met — this would be GREEN
            return

        # Build a detailed failure message for Condition 2
        if not analytics_match:
            condition_details = (
                "analytics_v2.get_supply_indicators NÃO existe — "
                "não é possível usar dados disponíveis (data_criacao, "
                "data_aprovacao) para lead_time_medio_dias."
            )
        else:
            has_data_criacao = bool(re.search(
                r"\bdata_criacao\b", re.sub(r"\s+", " ", analytics_match.group(1)), re.IGNORECASE
            )) if analytics_match else False
            has_data_aprovacao = bool(re.search(
                r"\bdata_aprovacao\b", re.sub(r"\s+", " ", analytics_match.group(1)), re.IGNORECASE
            )) if analytics_match else False
            has_lead_time_calc = bool(re.search(
                r"\blead_time\b", re.sub(r"\s+", " ", analytics_match.group(1)), re.IGNORECASE
            )) if analytics_match else False
            condition_details = (
                f"data_criacao={'SIM' if has_data_criacao else 'NÃO'}, "
                f"data_aprovacao={'SIM' if has_data_aprovacao else 'NÃO'}, "
                f"lead_time calc={'SIM' if has_lead_time_calc else 'NÃO'}"
            )

        pytest.fail(
            "AC5 violada — RED. A lacuna de `promised_delivery_at` está "
            "documentada, mas a função `analytics_v2.get_supply_indicators` "
            "NÃO usa colunas disponíveis como proxy para "
            "lead_time_medio_dias.\n\n"
            f"  promised_delivery_at no schema: NÃO (lacuna conhecida)\n"
            f"  Lacuna documentada em {BACKLOG_METRICAS_PATH.name}: SIM\n"
            f"  analytics_v2.get_supply_indicators: "
            f"{'existe' if analytics_match else 'NÃO existe'}\n"
            f"  {condition_details}\n\n"
            "Hoje a função analytics_v2.get_supply_indicators NÃO está "
            "definida no schema (apenas public.get_supply_indicators existe, "
            "que delega para ela). Mesmo que a lacuna de "
            "promised_delivery_at seja conhecida, a implementação GREEN "
            "deve:\n"
            "  1) Criar analytics_v2.get_supply_indicators que consulta "
            "fato_transacoes.\n"
            "  2) Calcular lead_time_medio_dias usando colunas disponíveis "
            "(data_criacao, data_aprovacao, etc.) como proxy.\n"
            "  3) Documentar a lacuna de promised_delivery_at "
            "separadamente.\n"
            "  4) Não depender de promised_delivery_at para o cálculo prosseguir."
        )
    else:
        # promised_delivery_at DOES exist — this would be a partial GREEN
        # For RED, we just document that this AC should be easier now
        pytest.skip(
            "promised_delivery_at já existe no schema — AC5 não se aplica "
            "como RED (a lacuna foi resolvida)."
        )
