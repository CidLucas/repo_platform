"""RED test — Fix Financial Indicators (DSO, DPO, CCC, Margins) — Behavior 4/5.

GOAL:
    Financial metrics should show real values — not NULL or "carregando".
    Os indicadores financeiros DSO, DPO, CCC, working_capital_ratio e
    margem_operacional_perc precisam ser calculados a partir dos dados
    disponíveis (fato_transacoes) ou tratados graciosamente com fallback
    quando o RPC não existir ou falhar.

BEHAVIOR:
    Fix Financial Indicators (Behavior 4/5).

    No estado atual (RED):
        1. getFinanceIndicators em analytics.ts (linha 434-454) chama
           callDimensionRpc('get_finance_indicators', period) sem try/catch.
        2. Se o RPC get_finance_indicators falhar (função não existe, DB
           indisponível, etc.), callDimensionRpc (linha 131-136) joga erro
           via "if (error) throw new Error(...)".
        3. Isso significa que qualquer falha no RPC derruba o painel
           Analytics do FinanceiroRoom — quebra toda a experiência.
        4. Não há fallback que retorne zeros estruturados com period
           metadata.
        5. public.get_finance_indicators na baseline_v2.sql (linha 2316)
           apenas delega para analytics_v2.get_finance_indicators() —
           que NÃO está definida em nenhuma migration disponível.

    Após a correção (GREEN), deve:
        a) getFinanceIndicators envolver callDimensionRpc em try/catch.
        b) No catch, retornar zeros estruturados com { period } preenchido.
        c) Os campos dso_dias, dpo_dias, ccc_dias, working_capital_ratio,
           margem_operacional_perc virem null no fallback.
        d) A UI do FinanceiroRoom mostrar "—" (null) ou 0 em vez de erro.

AC (Acceptance Criteria):
    AC1 — getFinanceIndicators em analytics.ts deve ter try/catch que trata
          dso_dias graciosamente (retorna null ou 0 em caso de falha).
    AC2 — getFinanceIndicators deve tratar dpo_dias graciosamente com
          fallback.
    AC3 — getFinanceIndicators deve tratar ccc_dias graciosamente com
          fallback.
    AC4 — getFinanceIndicators deve tratar working_capital_ratio
          graciosamente com fallback.
    AC5 — getFinanceIndicators deve tratar margem_operacional_perc
          graciosamente com fallback.
    AC6 — getFinanceIndicators deve ter bloco try/catch que captura erro
          do RPC e retorna structured zeros com metadata (period + campos
          null/zero).
    [AC7 — Documentar gaps conhecidos (tabelas contas a pagar/receber não
           existem — aproximações usadas) — NÃO testável por source-insp.]

Anti-Goals (must NOT be violated):
    1. NÃO introduzir mocks de DB ou rede — teste é source-inspection.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO modificar código de produção.
    4. NÃO escrever asserts que passam no estado atual — deve ser RED.

Estado atual (RED):
    - AC1-AC5: analytics.ts mapeia os 5 campos via numOrNull(r?.campo),
      mas sem try/catch → se o RPC falha, nada retorna (exceção).
    - AC6: NENHUM bloco try/catch envolve a chamada callDimensionRpc.
    - O painel FinanceiroRoom (linha 617) já trata kpiQ.isError com
      "Erro ao carregar. Tentar novamente" — mas o ideal é não chegar
      ao erro, retornando zeros com fallback.
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
FINANCEIRO_ROOM_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx"
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


def _analytics_ts() -> str:
    """Lê o conteúdo de apps/blu_v3/src/api/analytics.ts."""
    return _read_text(ANALYTICS_TS_PATH)


def _baseline_migration_text() -> str:
    """Lê o conteúdo da baseline_v2.sql."""
    return _read_text(BASELINE_V2_PATH)


# ── Testes (6 acceptance criteria) ──────────────────────────────────────


_FINANCIAL_METRICS = {
    "dso_dias": "Days Sales Outstanding (DSO)",
    "dpo_dias": "Days Payable Outstanding (DPO)",
    "ccc_dias": "Cash Conversion Cycle (CCC)",
    "working_capital_ratio": "Working Capital Ratio",
    "margem_operacional_perc": "Margem Operacional (%)",
}


def _check_metric_has_fallback(metric: str, label: str, content: str) -> list[str]:
    """Verifica se ``metric`` é mapeada no fallback (try/catch) de
    getFinanceIndicators.

    Retorna lista de problemas encontrados (vazia = OK).
    """
    issues: list[str] = []

    # 1. O campo deve estar na definição da interface FinanceIndicators
    if not re.search(
        rf"\b{metric}\b",
        content,
    ):
        issues.append(
            f"O campo `{metric}` ({label}) não foi encontrado "
            "na definição de `FinanceIndicators` em analytics.ts."
        )

    # 2. Deve ser mapeado no return de getFinanceIndicators
    if not re.search(
        rf"{metric}\s*:\s*numOrNull\b",
        content,
    ):
        issues.append(
            f"O campo `{metric}` ({label}) não é mapeado "
            "via numOrNull no return de getFinanceIndicators."
        )

    # 3. Deve existir bloco try/catch — se não, não há fallback.
    #    Se houver try/catch, a flag de fallback existe.
    has_try = bool(re.search(r"\btry\s*\{", content))
    has_catch = bool(re.search(r"\}\s*catch\s*\(", content))

    if not has_try or not has_catch:
        issues.append(
            f"O campo `{metric}` ({label}) NÃO tem proteção de try/catch "
            "em getFinanceIndicators. Se o RPC 'get_finance_indicators' "
            "falhar (função inexistente, erro de DB, etc.), todo o painel "
            "financeiro quebra com exceção. "
            "A correção esperada é envolver `callDimensionRpc` em "
            "try { r = await callDimensionRpc(...) } catch { r = { period } } "
            "para que `{metric}` retorne null/zero graciosamente."
        )

    return issues


def _check_metric_has_fallback_test(
    metric: str, label: str, ac_num: int
):
    """Factory de teste para um AC específico."""
    content = _analytics_ts()
    issues = _check_metric_has_fallback(metric, label, content)
    if issues:
        pytest.fail(
            f"AC{ac_num} não implementado: \"{label}\" "
            "não está devidamente tratado com fallback.\n"
            + "\n".join(f"  - {issue}" for issue in issues)
        )


# ── AC1: dso_dias ───────────────────────────────────────────────────────


def test_dso_dias_calculated_or_gracefully_handled():
    """AC1 — ``dso_dias`` (Days Sales Outstanding) deve ser calculado a
    partir de dados disponíveis ou tratado graciosamente com fallback.

    Atualmente getFinanceIndicators (analytics.ts linha 445) mapeia::

        dso_dias: numOrNull(r?.dso_dias),

    Mas se o RPC falhar, callDimensionRpc joga exceção e nenhum fallback
    é executado. O FinanceiroRoom (linha 661) renderiza::

        { label: 'DSO', value: fin?.dso_dias ?? null, ... }

    E quando value é null, o frontend mostra "↳ Sistema de cobrança".

    A correção esperada é que mesmo com RPC falhando, dso_dias retorne
    null (graciosamente) via fallback try/catch com ``{ period }``.
    """
    _check_metric_has_fallback_test("dso_dias", "DSO (Days Sales Outstanding)", 1)


# ── AC2: dpo_dias ───────────────────────────────────────────────────────


def test_dpo_dias_calculated_or_gracefully_handled():
    """AC2 — ``dpo_dias`` (Days Payable Outstanding) deve ser calculado
    de dados disponíveis ou tratado graciosamente com fallback.

    Atualmente mapeado em analytics.ts linha 446::

        dpo_dias: numOrNull(r?.dpo_dias),

    Sem try/catch, se o RPC falhar, a exceção propaga e o painel quebra.
    """
    _check_metric_has_fallback_test("dpo_dias", "DPO (Days Payable Outstanding)", 2)


# ── AC3: ccc_dias ───────────────────────────────────────────────────────


def test_ccc_dias_calculated_or_gracefully_handled():
    """AC3 — ``ccc_dias`` (Cash Conversion Cycle) deve ser calculado ou
    tratado graciosamente com fallback.

    CCC = DSO + DIO - DPO, calculado a partir dos dados de contas a
    receber/pagar (ou aproximações). Mapeado em analytics.ts linha 447::

        ccc_dias: numOrNull(r?.ccc_dias),

    Sem try/catch, a falha do RPC quebra o painel.
    """
    _check_metric_has_fallback_test("ccc_dias", "CCC (Cash Conversion Cycle)", 3)


# ── AC4: working_capital_ratio ──────────────────────────────────────────


def test_working_capital_ratio_calculated_or_gracefully_handled():
    """AC4 — ``working_capital_ratio`` deve ser calculado ou tratado
    graciosamente com fallback.

    Capital de giro = ativo circulante / passivo circulante. Mapeado em
    analytics.ts linha 448::

        working_capital_ratio: numOrNull(r?.working_capital_ratio),

    Sem try/catch, a falha do RPC quebra o painel.
    """
    _check_metric_has_fallback_test(
        "working_capital_ratio",
        "Working Capital Ratio",
        4,
    )


# ── AC5: margem_operacional_perc ────────────────────────────────────────


def test_margem_operacional_perc_calculated_or_gracefully_handled():
    """AC5 — ``margem_operacional_perc`` (Margem Operacional %) deve ser
    calculada ou tratada graciosamente com fallback.

    Margem operacional = (receita - despesas operacionais) / receita.
    Mapeado em analytics.ts linha 440::

        margem_operacional_perc: numOrNull(r?.margem_operacional_perc),

    Sem try/catch, a falha do RPC quebra o painel.
    """
    _check_metric_has_fallback_test(
        "margem_operacional_perc",
        "Margem Operacional (%)",
        5,
    )


# ── AC6: fallback para RPC inexistente ──────────────────────────────────


def test_get_finance_indicators_has_try_catch_fallback():
    """AC6 — ``getFinanceIndicators`` deve ter bloco ``try/catch`` ao
    redor da chamada RPC que retorna ``structured zeros`` com ``period``.

    Atualmente (analytics.ts linha 434-454)::

        export const getFinanceIndicators = async (period = '30d') => {
            const r = await callDimensionRpc<...>('get_finance_indicators',
                                                   period)
            return { ... dso_dias: numOrNull(r?.dso_dias), ... }
        }

    Onde ``callDimensionRpc`` (linha 131-136)::

        const { data, error } = await supabase.rpc(rpc, { p_period: period })
        if (error) throw new Error(...)

    Se o RPC não existir (analytics_v2.get_finance_indicators não está
    definida em nenhuma migration disponível), ou falhar por qualquer
    motivo, a exceção propaga para o React Query, que mostra erro no
    FinanceiroRoom (linha 617-621)::

        kpiQ.isError ? (
            <div>Erro ao carregar. Tentar novamente</div>
        ) : null

    A correção esperada é::

        let r: Record<string, unknown>
        try {
            r = await callDimensionRpc('get_finance_indicators', period)
        } catch {
            r = { period }
        }
        return {
            receita_liquida: num(r?.receita_liquida),
            ...
            period: String(r?.period ?? period),
        }
    """
    content = _analytics_ts()

    has_try = bool(re.search(r"\btry\s*\{", content))
    has_catch = bool(re.search(r"\}\s*catch\s*\(", content))
    has_fallback_zero = bool(
        re.search(
            r"(?:receita_liquida|custo_total|dso_dias|dpo_dias|ccc_dias)\s*[=:]\s*0",
            content,
        )
    )

    missing: list[str] = []
    if not has_try:
        missing.append("bloco try { ... }")
    if not has_catch:
        missing.append("bloco catch (...) { ... }")

    if missing:
        pytest.fail(
            "AC6 não implementado: getFinanceIndicators em analytics.ts "
            "NÃO possui bloco try/catch. "
            "Faltam: " + ", ".join(missing)
            + ". "
            "Atualmente, se o RPC get_finance_indicators falhar (função "
            "inexistente, DB indisponível, etc.), callDimensionRpc "
            "(linha 132-136) joga exceção via "
            "'if (error) throw new Error(...)' "
            "e todo o painel Analytics Financeiro quebra com "
            "'Erro ao carregar'. "
            "Correção esperada: envolver a chamada RPC em "
            "`try { r = await callDimensionRpc(...) } "
            "catch { r = { period } }` "
            "para que em caso de erro os indicadores retornem zeros "
            "com o período preenchido, permitindo que o frontend mostre "
            "'R$ 0' ou '—' em vez de uma tela de erro. "
            f"Arquivo: {ANALYTICS_TS_PATH}"
        )
