"""RED test for behavior B-5 — corrigir metricas financeiras com dados parciais.

GOAL:
    B-5 — get_finance_indicators: dso/dpo/ccc_dias e working_capital devem
    retornar null (nao erro) quando dados parciais. UI deve exibir "Sem dados"
    em vez de null cru / fallback de fonte ``↳ {src}``.

BEHAVIOR:
    Hoje a migration ``*fix_finance_indicators*`` ja existe e implementa
    ``analytics_v2.get_finance_indicators`` com formulas para os 5 indicadores.
    Porem o tratamento de dados parciais (tabelas dim_contas_receber e
    dim_contas_pagar ausentes ou vazias) precisa ser testado explicitamente:

        1. SQL: a RPC NAO deve lancar excecao quando as tabelas
           dim_contas_receber / dim_contas_pagar nao existem — deve usar
           ``BEGIN ... EXCEPTION WHEN OTHERS THEN NULL; END;`` para engolir
           o erro e retornar null nos campos dependentes (dso_dias, dpo_dias,
           ccc_dias).

        2. Frontend: ``FinanceiroRoom.tsx`` atualmente renderiza
           ``↳ {src}`` (ex: ``↳ Sistema de cobranca``, ``↳ ERP / AP``,
           ``↳ DSO + DPO + estoque``) quando os valores sao null.
           O DESIRED behavior e exibir **"Sem dados"** no lugar.

AC (Acceptance Criteria):
    AC-4 — getFinanceIndicators() retorna dso/dpo/ccc_dias como null
           (nao erro), UI exibe "Sem dados"

Anti-Goals (must NOT be violated):
    1. NAO alterar a interface TypeScript ``FinanceIndicators`` ou
       ``getFinanceIndicators()`` em ``apps/blu_v3/src/api/analytics.ts``.
    2. NAO alterar a assinatura do RPC (parametros e tipo de retorno
       do ``public.get_finance_indicators``).
    3. NAO lancar excecao quando dados estruturais estao ausentes —
       retornar null com ``period``.
    4. NAO criar novas tabelas (dim_contas_pagar, dim_contas_receber)
       sem aprovacao explicita do analista.

Estado atual: FALSE RED para SQL (migration ja tem EXCEPTION), TRUE RED
para frontend (FinanceiroRoom.tsx NAO exibe "Sem dados" — mostra ``↳ {src}``
no lugar). O teste vai falhar no AC de frontend.
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
FRONTEND_PATH = (
    REPO_ROOT
    / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── SQL helpers ──────────────────────────────────────────────────────────


def _read_fix_migration() -> str:
    """Return the full text of the ``*fix_finance_indicators*`` migration.

    Raises ``AssertionError`` if ZERO or MORE THAN ONE migration match
    the glob pattern.
    """
    matches = sorted(MIGRATIONS_DIR.glob("*fix_finance_indicators*"))
    assert len(matches) == 1, (
        f"No migration file matching *fix_finance_indicators* found in "
        f"{MIGRATIONS_DIR}. Expected exactly 1 file. "
        f"Found {len(matches)} matches: {[m.name for m in matches]}."
    )
    return matches[0].read_text(encoding="utf-8")


def _extract_function_body(sql: str) -> str:
    """Return the body of ``analytics_v2.get_finance_indicators`` in the migration."""
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
    return sql[body_start: body_start + close_match.start()]


def _read_financeiro_room() -> str:
    """Return the full text of FinanceiroRoom.tsx."""
    assert FRONTEND_PATH.exists(), (
        f"FinanceiroRoom.tsx not found at {FRONTEND_PATH}"
    )
    return FRONTEND_PATH.read_text(encoding="utf-8")


# ── AC4 — SQL: EXCEPTION handling for missing tables ────────────────────


def test_b5_ac4_sql_exception_handling():
    """AC4 (SQL) — RPC deve engolir erro de tabelas ausentes via EXCEPTION.

    Verifica que a funcao ``analytics_v2.get_finance_indicators`` contem
    blocos ``BEGIN ... EXCEPTION WHEN OTHERS THEN NULL; END;`` que
    protegem as queries contra tabelas inexistentes
    (dim_contas_receber, dim_contas_pagar).
    """
    sql = _read_fix_migration()
    body = _extract_function_body(sql)

    # 1. Nao pode ter RAISE EXCEPTION
    has_raise = bool(re.search(r"\bRAISE\s+EXCEPTION\b", body, re.IGNORECASE))
    assert not has_raise, (
        "AC4 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "contem `RAISE EXCEPTION`. A implementacao NAO deve lancar excecao "
        "quando dados estruturais estao ausentes."
    )

    # 2. Deve ter EXCEPTION block protegendo dim_contas_receber
    has_exception_dcr = (
        "dim_contas_receber" in body
        and bool(re.search(
            r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s+NULL",
            body,
            re.DOTALL | re.IGNORECASE,
        ))
    )

    assert has_exception_dcr, (
        "AC4 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO contem um bloco `EXCEPTION WHEN OTHERS THEN NULL` protegendo "
        "a query `dim_contas_receber`. A implementacao GREEN deve usar "
        "`BEGIN ... SELECT FROM dim_contas_receber ... EXCEPTION WHEN OTHERS "
        "THEN NULL; END;` para retornar null silenciosamente quando a tabela "
        "nao existe."
    )

    # 3. Deve ter EXCEPTION block protegendo dim_contas_pagar
    has_exception_dcp = (
        "dim_contas_pagar" in body
        and bool(re.search(
            r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s+NULL",
            body,
            re.DOTALL | re.IGNORECASE,
        ))
    )

    assert has_exception_dcp, (
        "AC4 violada — RED. O corpo de `analytics_v2.get_finance_indicators` "
        "NAO contem um bloco `EXCEPTION WHEN OTHERS THEN NULL` protegendo "
        "a query `dim_contas_pagar`. A implementacao GREEN deve usar "
        "`BEGIN ... SELECT FROM dim_contas_pagar ... EXCEPTION WHEN OTHERS "
        "THEN NULL; END;` para retornar null silenciosamente quando a tabela "
        "nao existe."
    )


# ── AC4 — Frontend: UI exibe "Sem dados" ────────────────────────────────


def test_b5_ac4_frontend_sem_dados():
    """AC4 (Frontend) — UI deve exibir 'Sem dados' no lugar de ``↳ {src}``.

    Atualmente o FinanceiroRoom.tsx renderiza:

        ) : (
          <span ...>↳ {src}</span>
        )}

    para TODOS os indicadores quando o valor e null. O DESIRED behavior e
    que os indicadores DSO, DPO e CCC exibam "Sem dados" no lugar do
    fallback ``↳ {src}``.

    Esta abordagem e pratica porque:
    1. A branch de renderizacao null e COMPARTILHADA no callback ``.map()``
       — mudar para "Sem dados" afeta todos os 7 indicadores, o que e
       semanticamente correto (se nao ha dados, mostrar "Sem dados" em
       vez do nome da fonte).
    2. Para ser ainda mais especifico, o coder pode usar um condicional:
       ``{'DSO','DPO','CCC'}.includes(label) ? 'Sem dados' : \`↳ ${src}\``

    O teste busca o conteudo do <span> na branch null do callback .map()
    — se encontrar "↳" ou "src", significa que a UI ainda NAO exibe
    "Sem dados" (RED). Se encontrar "Sem dados", o teste passa (GREEN).
    """
    tsx = _read_financeiro_room()

    # Find the grid section that renders DSO/DPO/CCC
    # Lines 628-652: the grid with borderTop: 1px solid var(--gb)
    border_marker = "borderTop: '1px solid var(--gb)'"
    assert border_marker in tsx, (
        "AC4 violada — RED. Nao foi encontrada a secao de grid de KPIs "
        f"em FinanceiroRoom.tsx (esperado '{border_marker}')."
    )

    idx = tsx.find(border_marker)
    grid_text = tsx[idx:idx + 2500]

    # Verify that DSO/DPO/CCC entries exist in the data array
    assert "'DSO'" in grid_text, (
        "AC4 violada — RED. Entrada 'DSO' nao encontrada no grid de KPIs. "
        "Esperada em FinanceiroRoom.tsx ~linha 633."
    )
    assert "'DPO'" in grid_text, (
        "AC4 violada — RED. Entrada 'DPO' nao encontrada no grid de KPIs. "
        "Esperada em FinanceiroRoom.tsx ~linha 634."
    )
    assert "'CCC'" in grid_text, (
        "AC4 violada — RED. Entrada 'CCC' nao encontrada no grid de KPIs. "
        "Esperada em FinanceiroRoom.tsx ~linha 635."
    )

    # Check the null-rendering branch.
    # The null <span> is inside the map callback:
    #   ) : (
    #     <span ...>↳ {src}</span>
    #   )}
    # Simple approach: look for the literal string "↳ {src}" inside grid_text
    has_source_fallback = "↳ {src}" in grid_text

    # Also check if "Sem dados" already appears in the grid section
    has_sem_dados = "Sem dados" in grid_text

    if not has_sem_dados and has_source_fallback:
        # TRUE RED: frontend still uses ↳ {src}, not "Sem dados"
        pytest.fail(
            "AC4 violada — TRUE RED. O FinanceiroRoom.tsx renderiza "
            "`↳ {src}` na branch null do callback .map() (linha 648), "
            "mas deveria exibir 'Sem dados' para os indicadores DSO, DPO e CCC. "
            "Implementacao GREEN: alterar o conteudo do <span> na linha 648 "
            "de `↳ {src}` para `Sem dados`."
        )
    elif has_sem_dados:
        # GREEN: already implemented
        pass
    else:
        # Neither ↳ {src} nor Sem dados found — structure might have changed
        pytest.fail(
            "AC4 violada — RED. Nao foi encontrado nem 'Sem dados' nem "
            "'↳ {src}' no grid de KPIs. A estrutura do componente pode "
            "ter mudado. Verifique FinanceiroRoom.tsx linhas 628-652."
        )
