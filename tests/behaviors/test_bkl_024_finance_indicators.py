"""RED test for behavior BKL-024 — Corrigir metricas financeiras que retornam null.

GOAL:
    BKL-024 — Os 5 indicadores financeiros abaixo retornam ``null`` quando
    o frontend chama ``analytics_v2.get_finance_indicators()`` (via wrapper
    ``public.get_finance_indicators``) porque o corpo da funcao em
    ``analytics_v2`` nao esta implementado:

        - dso_dias                  (Days Sales Outstanding)
        - dpo_dias                  (Days Payable Outstanding)
        - ccc_dias                  (Cash Conversion Cycle)
        - working_capital_ratio     (Ativo circulante / Passivo circulante)
        - margem_operacional_perc   ((Receita - Custo - Despesas) / Receita)

BEHAVIOR:
    Hoje, em ``supabase/migrations/20260523999999_baseline_v2.sql``
    (linhas 2316-2323), existe apenas o WRAPPER publico:

        CREATE OR REPLACE FUNCTION public.get_finance_indicators(p_period text)
        LANGUAGE sql
        AS $function$
          SELECT * FROM analytics_v2.get_finance_indicators(p_period);
        $function$;

    Ou seja, o wrapper delega para ``analytics_v2.get_finance_indicators``
    — funcao que NAO esta definida no schema ``analytics_v2`` (zero
    ``CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators``
    no baseline). O resultado e que a RPC retorna ``null`` / falha
    silenciosa, e o frontend exibe ``—`` ou vazio para os 5 indicadores.

    A GREEN phase deve criar uma migration em
    ``supabase/migrations/*fix_finance_indicators*`` que faca
    ``CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators``
    com o corpo que implementa as 5 formulas acima. A migration deve:

        1. NAO alterar a interface (parametros, tipo de retorno) do
           wrapper ``public.get_finance_indicators``.
        2. NAO lancar excecao quando dados estruturais estao ausentes —
           retornar ``null`` (ou 0) com ``period`` populado.
        3. NAO criar novas tabelas (dim_contas_pagar, dim_contas_receber)
           sem aprovacao do analista — usar apenas as dim tables
           existentes (``dim_datas``, ``fato_transacoes``) ou variaveis
           locais no proprio corpo da funcao.
        4. Usar ``NULLIF`` para evitar divisao por zero.

AC (Acceptance Criteria):
    AC1 — dso_dias: formula DSO = (contas_receber / receita_liquida) * dias_periodo
    AC2 — dpo_dias: formula DPO = (contas_pagar / custo_total) * dias_periodo
    AC3 — ccc_dias: formula CCC = dso_dias - dpo_dias
    AC4 — working_capital_ratio: ativo_circulante / passivo_circulante
    AC5 — margem_operacional_perc: (receita - custo - despesas_operacionais) / receita
    AC6 — RPC nunca levanta erro: usa NULLIF, NAO tem RAISE EXCEPTION,
          e sempre retorna ``period`` (mesmo que as outras colunas sejam null)

Anti-Goals (must NOT be violated):
    1. NAO alterar a interface TypeScript ``FinanceIndicators`` ou
       ``getFinanceIndicators()`` em ``apps/blu_v3/src/api/analytics.ts``.
    2. NAO alterar a assinatura do RPC (parametros e tipo de retorno
       do ``public.get_finance_indicators``).
    3. NAO lancar excecao quando dados estruturais estao ausentes —
       retornar null com ``period``.
    4. NAO criar novas tabelas (dim_contas_pagar, dim_contas_receber)
       sem aprovacao explicita do analista.

Estado atual: RED. O teste asserta o DESIRED behavior (que NAO existe
ainda — a migration ``*fix_finance_indicators*`` NAO foi criada).
O helper ``_read_fix_migration()`` falha com ``AssertionError`` porque
nao ha nenhum arquivo matching ``*fix_finance_indicators*`` em
``supabase/migrations/``. Como CADA teste chama ``_read_fix_migration()``
no inicio, TODOS falham (RED) — o que e o estado esperado antes da
GREEN phase. A leitura e puramente ``source-inspection`` (texto de
``.sql``), sem Supabase real e sem mocks.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_fix_migration() -> str:
    """Return the full text of the ``*fix_finance_indicators*`` migration.

    Raises ``AssertionError`` if ZERO or MORE THAN ONE migration match
    the glob pattern — the test should fail loudly with a clear message
    rather than silently passing on a missing file. In the current RED
    state, this helper fails because no such migration has been created
    yet, which is the expected behavior before the GREEN phase.
    """
    matches = sorted(MIGRATIONS_DIR.glob("*fix_finance_indicators*"))
    assert len(matches) == 1, (
        f"No migration file matching *fix_finance_indicators* found in "
        f"{MIGRATIONS_DIR}. Expected exactly 1 file (e.g. "
        f"`20260625000000_fix_finance_indicators.sql`) that contains "
        f"`CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators(...)`. "
        f"Found {len(matches)} matches: {[m.name for m in matches]}."
    )
    return matches[0].read_text(encoding="utf-8")


def _extract_function_body(sql: str) -> str:
    """Return the body of ``analytics_v2.get_finance_indicators`` in the migration.

    Searches for ``CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators``
    and returns the text between the outer ``AS $function$ ... $function$``
    dollar-quoted markers. Returns an empty string if the function is
    not found.
    """
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_finance_indicators"
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


# ── AC1: dso_dias ────────────────────────────────────────────────────────


def test_bkl_024_ac1_dso_dias():
    """AC1 — ``dso_dias`` deve ser calculado no corpo da funcao.

    Formula esperada (DSO — Days Sales Outstanding):

        dso_dias = (contas_receber / receita_liquida) * dias_periodo

    A migration DEVE:
        - declarar ``dso_dias`` como coluna retornada (wrapper public);
        - calcular ``dso_dias`` usando ``contas_receber`` no corpo;
        - multiplicar por um fator de dias (``dias_periodo`` ou similar).

    Esta assercao testa a PRESENCA das 3 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED) — o que e o estado esperado.
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Column dso_dias must appear in the migration (returned by wrapper or function)
    assert "dso_dias" in sql, (
        "AC1 violada — RED. A migration `*fix_finance_indicators*` NAO contem "
        "a coluna `dso_dias` em nenhum lugar. "
        "A implementacao GREEN deve declarar `dso_dias` no `RETURNS TABLE` "
        "do wrapper `public.get_finance_indicators` E calcular `dso_dias` "
        "no corpo de `analytics_v2.get_finance_indicators`."
    )

    # 2. The function body must reference contas_receber (the numerator)
    assert "contas_receber" in body, (
        "AC1 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO referencia `contas_receber`. "
        "A implementacao GREEN deve calcular `dso_dias` usando "
        "`contas_receber` (saldo de contas a receber) no numerador da formula "
        "`dso_dias = (contas_receber / receita_liquida) * dias_periodo`."
    )

    # 3. The function body must reference a period-in-days factor
    has_dias_periodo = bool(re.search(r"dias_periodo|dias_no_periodo|period_days", body, re.IGNORECASE))
    assert has_dias_periodo, (
        "AC1 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO contem um fator de dias do periodo (`dias_periodo`, "
        "`dias_no_periodo` ou `period_days`). "
        "A implementacao GREEN deve multiplicar a razao `contas_receber / "
        "receita_liquida` por `dias_periodo` (ex.: 30 para '30d')."
    )


# ── AC2: dpo_dias ────────────────────────────────────────────────────────


def test_bkl_024_ac2_dpo_dias():
    """AC2 — ``dpo_dias`` deve ser calculado no corpo da funcao.

    Formula esperada (DPO — Days Payable Outstanding):

        dpo_dias = (contas_pagar / custo_total) * dias_periodo

    A migration DEVE:
        - declarar ``dpo_dias`` como coluna retornada;
        - calcular ``dpo_dias`` usando ``contas_pagar`` no corpo.

    Esta assercao testa a PRESENCA das 2 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Column dpo_dias must appear in the migration
    assert "dpo_dias" in sql, (
        "AC2 violada — RED. A migration `*fix_finance_indicators*` NAO contem "
        "a coluna `dpo_dias` em nenhum lugar. "
        "A implementacao GREEN deve declarar `dpo_dias` no `RETURNS TABLE` "
        "do wrapper `public.get_finance_indicators` E calcular `dpo_dias` "
        "no corpo de `analytics_v2.get_finance_indicators`."
    )

    # 2. The function body must reference contas_pagar (the numerator)
    assert "contas_pagar" in body, (
        "AC2 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO referencia `contas_pagar`. "
        "A implementacao GREEN deve calcular `dpo_dias` usando "
        "`contas_pagar` (saldo de contas a pagar) no numerador da formula "
        "`dpo_dias = (contas_pagar / custo_total) * dias_periodo`."
    )


# ── AC3: ccc_dias ────────────────────────────────────────────────────────


def test_bkl_024_ac3_ccc_dias():
    """AC3 — ``ccc_dias`` deve ser derivado de ``dso_dias - dpo_dias``.

    Formula esperada (CCC — Cash Conversion Cycle):

        ccc_dias = dso_dias - dpo_dias

    A migration DEVE:
        - declarar ``ccc_dias`` como coluna retornada;
        - calcular ``ccc_dias`` a partir de ``dso_dias`` e ``dpo_dias``
          (a subtracao explicita OU o uso das duas variaveis no corpo).

    Esta assercao testa a PRESENCA das 2 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Column ccc_dias must appear in the migration
    assert "ccc_dias" in sql, (
        "AC3 violada — RED. A migration `*fix_finance_indicators*` NAO contem "
        "a coluna `ccc_dias` em nenhum lugar. "
        "A implementacao GREEN deve declarar `ccc_dias` no `RETURNS TABLE` "
        "do wrapper `public.get_finance_indicators` E calcular `ccc_dias` "
        "no corpo de `analytics_v2.get_finance_indicators`."
    )

    # 2. The function body must reference BOTH dso_dias and dpo_dias,
    #    and either use them in a subtraction or have the formula present.
    has_dso = "dso_dias" in body
    has_dpo = "dpo_dias" in body
    has_subtraction = bool(re.search(r"dso_dias\s*-\s*dpo_dias|dpo_dias\s*-\s*dso_dias", body))

    assert has_dso and has_dpo, (
        "AC3 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        f"NAO referencia ambos `dso_dias` e `dpo_dias` "
        f"(encontrados: dso_dias={has_dso}, dpo_dias={has_dpo}). "
        "A implementacao GREEN deve calcular `ccc_dias` como "
        "`dso_dias - dpo_dias` no corpo da funcao."
    )

    assert has_subtraction, (
        "AC3 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "referencia `dso_dias` e `dpo_dias`, mas NAO contem a subtracao "
        "explicita `dso_dias - dpo_dias` (ou `dpo_dias - dso_dias`). "
        "A implementacao GREEN deve expressar `ccc_dias` como "
        "`dso_dias - dpo_dias` no SELECT final."
    )


# ── AC4: working_capital_ratio ──────────────────────────────────────────


def test_bkl_024_ac4_working_capital_ratio():
    """AC4 — ``working_capital_ratio`` deve ser calculado como AC / PC.

    Formula esperada (Working Capital Ratio):

        working_capital_ratio = ativo_circulante / passivo_circulante

    A migration DEVE:
        - declarar ``working_capital_ratio`` como coluna retornada;
        - calcular ``working_capital_ratio`` usando
          ``ativo_circulante`` e ``passivo_circulante`` no corpo.

    Esta assercao testa a PRESENCA das 3 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Column working_capital_ratio must appear in the migration
    assert "working_capital_ratio" in sql, (
        "AC4 violada — RED. A migration `*fix_finance_indicators*` NAO contem "
        "a coluna `working_capital_ratio` em nenhum lugar. "
        "A implementacao GREEN deve declarar `working_capital_ratio` no "
        "`RETURNS TABLE` do wrapper `public.get_finance_indicators` E "
        "calcula-lo no corpo de `analytics_v2.get_finance_indicators`."
    )

    # 2. The function body must reference both ativo_circulante and passivo_circulante
    assert "ativo_circulante" in body, (
        "AC4 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO referencia `ativo_circulante`. "
        "A implementacao GREEN deve calcular `working_capital_ratio` usando "
        "`ativo_circulante` (numerador) e `passivo_circulante` (denominador)."
    )

    assert "passivo_circulante" in body, (
        "AC4 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO referencia `passivo_circulante`. "
        "A implementacao GREEN deve calcular `working_capital_ratio` como "
        "`ativo_circulante / passivo_circulante`."
    )


# ── AC5: margem_operacional_perc ─────────────────────────────────────────


def test_bkl_024_ac5_margem_operacional_perc():
    """AC5 — ``margem_operacional_perc`` deve ser calculado com despesas.

    Formula esperada (Operating Margin %):

        margem_operacional_perc =
            ((receita_liquida - custo_total - despesas_operacionais) / receita_liquida) * 100

    A migration DEVE:
        - declarar ``margem_operacional_perc`` como coluna retornada;
        - referenciar ``despesas_operacionais`` no corpo (o que difere
          esta margem da margem_bruta_perc, que NAO subtrai despesas).

    Esta assercao testa a PRESENCA das 2 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Column margem_operacional_perc must appear in the migration
    assert "margem_operacional_perc" in sql, (
        "AC5 violada — RED. A migration `*fix_finance_indicators*` NAO contem "
        "a coluna `margem_operacional_perc` em nenhum lugar. "
        "A implementacao GREEN deve declarar `margem_operacional_perc` no "
        "`RETURNS TABLE` do wrapper `public.get_finance_indicators` E "
        "calcula-lo no corpo de `analytics_v2.get_finance_indicators`."
    )

    # 2. The function body must reference despesas_operacionais
    assert "despesas_operacionais" in body, (
        "AC5 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO referencia `despesas_operacionais`. "
        "A implementacao GREEN deve calcular `margem_operacional_perc` como "
        "`((receita_liquida - custo_total - despesas_operacionais) / "
        "receita_liquida) * 100`."
    )


# ── AC6: RPC nunca levanta erro e sempre retorna period ─────────────────


def test_bkl_024_ac6_rpc_never_errors():
    """AC6 — A RPC NAO deve levantar excecao e sempre retorna ``period``.

    A migration DEVE:
        1. NAO conter ``RAISE EXCEPTION`` nem ``RAISE`` no corpo de
           ``analytics_v2.get_finance_indicators`` (a funcao deve
           retornar null/zeros, NAO lancar excecao).
        2. Sempre retornar a coluna ``period`` (via ``COALESCE`` ou
           similar) mesmo quando os dados estruturais estao ausentes.
        3. Usar ``NULLIF`` para evitar divisao por zero nas formulas.

    Esta assercao testa a PRESENCA das 3 sub-features. Como a
    migration ainda NAO existe, o teste FALHA em
    ``_read_fix_migration()`` (RED).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # Helper: split body into code lines (drop comment-only lines starting with --)
    code_lines = [
        ln for ln in body.splitlines()
        if ln.strip() and not ln.strip().startswith("--")
    ]
    code_text = "\n".join(code_lines)

    # 1. NO RAISE EXCEPTION / RAISE in the function body
    has_raise = bool(re.search(r"\bRAISE\s+EXCEPTION\b|\bRAISE\b", code_text, re.IGNORECASE))
    assert not has_raise, (
        "AC6 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "contem `RAISE EXCEPTION` (ou `RAISE`). "
        "A implementacao GREEN NAO deve lancar excecao quando dados "
        "estruturais estao ausentes — deve retornar null/zeros com "
        "`period` populado. Use `COALESCE` e retorne null silenciosamente."
    )

    # 2. The function must always return ``period`` (use COALESCE around it,
    #    or hardcode p_period in the last column of the SELECT).
    has_period_coalesce = bool(re.search(
        r"COALESCE\s*\([^)]*\bperiod\b[^)]*\)|period\s*(?:::text)?\s*AS\s+period",
        body,
        re.IGNORECASE,
    )) or "AS period" in body.lower() or "as period" in body.lower()

    assert has_period_coalesce, (
        "AC6 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO garante o retorno da coluna `period`. "
        "A implementacao GREEN deve sempre retornar `period` (ex.: "
        "`COALESCE(p_period, '30d') AS period` ou `p_period::text AS period`) "
        "mesmo quando as outras colunas sao null/zero."
    )

    # 3. The function must use NULLIF to avoid division by zero
    assert "NULLIF" in body.upper(), (
        "AC6 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO usa `NULLIF` em nenhum lugar. "
        "A implementacao GREEN deve usar `NULLIF(denominador, 0)` para "
        "evitar `division by zero` em pelo menos uma das formulas "
        "(dso_dias, dpo_dias, working_capital_ratio, margem_operacional_perc)."
    )
