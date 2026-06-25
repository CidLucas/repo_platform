"""RED test for behavior B-2 — Aba unificada Transacoes substitui Compromissos+Historico (BKL-021) (NAO implementado).

GOAL:
    Validar que a feature de unificar as abas "Compromissos" e "Historico"
    em uma unica aba "Transacoes" na sala FinanceiroRoom.tsx
    **NAO esta implementada** no estado atual do repositorio.

    O behavior B-2 (a ser entregue em fase GREEN) deve:
      1) Atualizar o type Tab para incluir 'transacoes' e remover
         'compromissos' e 'historico'
      2) Atualizar o array de tabs para conter 'transacoes' (com label
         "Transacoes") e NAO conter 'compromissos' nem 'historico'
      3) Renderizar conteudo unificado na aba transacoes mostrando
         tanto polpBills (faturas) quanto polpTransactions (transacoes)
      4) Adicionar filtro de periodo com 4 opcoes: hoje, 7d, 30d, tudo
      5) Manter o badge de contagem de faturas abertas na aba transacoes

BEHAVIOR:
    B-2 — Aba unificada Transacoes substitui Compromissos+Historico (BKL-021):
    Em FinanceiroRoom.tsx as abas "Compromissos" e "Historico" sao
    substituidas por uma unica aba "Transacoes" que exibe faturas e
    transacoes em listagem unificada, com filtro de periodo (hoje /
    7d / 30d / tudo) e badge de faturas abertas mantido.

    **Estado atual (RED):** nenhum desses pontos esta implementado.
    A sala ainda tem 5 abas (decisoes, compromissos, tarefas, historico,
    config), sem filtro de periodo, e as abas compromissos/historico
    sao totalmente separadas.

AC (Acceptance Criteria):
    AC#1 — O type Tab em FinanceiroRoom.tsx DEVE ser
            'decisoes' | 'transacoes' | 'tarefas' | 'config' (ou seja,
            NAO deve conter 'compromissos' nem 'historico' e DEVE
            conter 'transacoes').
    AC#2 — O array de tabs renderizado em FinanceiroRoom.tsx DEVE
            conter 'transacoes' e NAO conter 'compromissos' nem
            'historico'. O label renderizado da aba transacoes deve
            ser "Transacoes".
    AC#3 — A aba transacoes em FinanceiroRoom.tsx DEVE exibir conteudo
            unificado com polpBills (faturas) E polpTransactions
            (transacoes) em uma unica listagem.
    AC#4 — A aba transacoes em FinanceiroRoom.tsx DEVE oferecer um
            filtro de periodo com 4 opcoes: "hoje", "7d", "30d", "tudo".
    AC#5 — A aba transacoes em FinanceiroRoom.tsx DEVE manter o badge
            de contagem de faturas abertas
            (polpBills.filter(b => b.status !== 'CLOSED').length).

Estado atual: RED — todas as ACs violadas. A sala ainda tem type Tab
com 'compromissos' e 'historico', array de 5 tabs, sem filtro de
periodo, e as duas abas estao separadas. Cada teste falha com
pytest.fail() e mensagem detalhada em pt-BR.

Anti-Goals:
    1. NAO modificar codigo de producao (sao apenas testes estaticos).
    2. NAO executar / parsear TypeScript — so inspecao textual com regex.
    3. NAO usar mocks, Supabase, browser testing, jsdom.
    4. NAO quebrar funcionalidade existente (decisoes, tarefas, config).
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent.parent

FINANCEIRO_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "FinanceiroRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ─────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste eh
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao do TypeScript ────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-2 (aba unificada Transacoes) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _extract_tab_type_union(source: str) -> str | None:
    """Retorna o conteudo do type Tab = '...' | '...' | ... ou None
    se nao encontrado.
    """
    match = re.search(
        r"type\s+Tab\s*=\s*((?:['\"][^'\"]+['\"]\s*\|\s*)+['\"][^'\"]+['\"])",
        source,
    )
    return match.group(1) if match else None


def _tab_union_contains(tab_union: str, value: str) -> bool:
    """Retorna True se a uniao de tipos Tab contem o valor."""
    pattern = rf"['\"]\s*{re.escape(value)}\s*['\"]"
    return bool(re.search(pattern, tab_union))


def _extract_tabs_array(source: str) -> str | None:
    """Retorna o conteudo do array de tabs (ex: ['decisoes', 'compromissos', ...])
    em FinanceiroRoom.tsx, ou None se nao encontrado.
    """
    match = re.search(
        r"\(\[\s*((?:['\"][^'\"]+['\"]\s*,\s*)*['\"][^'\"]+['\"])\s*\]\s+as\s+Tab\[\]\)",
        source,
    )
    return match.group(1) if match else None


def _tabs_array_contains(tabs_array: str, value: str) -> bool:
    """Retorna True se o array de tabs contem o valor como string literal."""
    pattern = rf"['\"]\s*{re.escape(value)}\s*['\"]"
    return bool(re.search(pattern, tabs_array))


def _has_transacoes_tab_block(source: str) -> bool:
    """Retorna True se ha um bloco JSX com id="f-transacoes" ou um
    bloco condicional tab === 'transacoes'.
    """
    return bool(
        re.search(
            r"id=[\"']f-transacoes[\"']|tab\s*===\s*['\"]transacoes['\"]",
            source,
        )
    )


def _extract_transacoes_block(source: str) -> str:
    """Retorna o trecho do arquivo a partir de onde comeca o bloco
    da aba transacoes (ou um fallback de string vazia se nao existir).
    Usado para inspecao do conteudo unificado.
    """
    match = re.search(
        r"(?:id=[\"']f-transacoes[\"']|tab\s*===\s*['\"]transacoes['\"]).*",
        source,
        re.DOTALL,
    )
    return match.group(0) if match else ""


def _has_period_filter_with_4_options(source: str) -> bool:
    """Retorna True se o arquivo define um filtro de periodo com
    as 4 opcoes: hoje, 7d, 30d, tudo.
    """
    today_match = re.search(
        r"['\"]\s*hoje\s*['\"]\s*:\s*['\"][^'\"]*['\"]",
        source,
    )
    seven_d_match = re.search(
        r"['\"]\s*7d\s*['\"]\s*:\s*['\"][^'\"]*['\"]",
        source,
    )
    thirty_d_match = re.search(
        r"['\"]\s*30d\s*['\"]\s*:\s*['\"][^'\"]*['\"]",
        source,
    )
    all_match = re.search(
        r"['\"]\s*tudo\s*['\"]\s*:\s*['\"][^'\"]*['\"]",
        source,
    )
    return all([today_match, seven_d_match, thirty_d_match, all_match])


def _has_open_bills_badge_in_transacoes(source: str) -> bool:
    """Retorna True se existe um badge com a contagem de faturas
    abertas (polpBills.filter(b => b.status !== 'CLOSED').length)
    DENTRO do bloco da aba transacoes.
    """
    block = _extract_transacoes_block(source)
    if not block:
        return False
    return bool(
        re.search(
            r"polpBills\s*\.\s*filter\s*\(\s*b\s*=>\s*b\.status\s*!==\s*['\"]CLOSED['\"]\s*\)\.length",
            block,
        )
    )


# ── AC#1 — type Tab DEVE ser 'decisoes' | 'transacoes' | 'tarefas' | 'config'


def test_b2_ac1_type_tab_com_transacoes_sem_compromissos_sem_historico():
    """AC#1: O type Tab em FinanceiroRoom.tsx DEVE ser
    'decisoes' | 'transacoes' | 'tarefas' | 'config'.

    Ou seja, NAO deve conter 'compromissos' nem 'historico' e DEVE
    conter 'transacoes'.

    Falha (RED) enquanto o type Tab ainda tiver 'compromissos' e/ou
    'historico', ou nao tiver 'transacoes'.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    tab_union = _extract_tab_type_union(source)
    if tab_union is None:
        pytest.fail(
            "FinanceiroRoom.tsx NAO declara um type Tab = '...' | '...' | ...  "
            "Esperado: type Tab = 'decisoes' | 'transacoes' | 'tarefas' | 'config'"
        )

    has_transacoes = _tab_union_contains(tab_union, "transacoes")
    has_compromissos = _tab_union_contains(tab_union, "compromissos")
    has_historico = _tab_union_contains(tab_union, "historico")

    if has_transacoes and not has_compromissos and not has_historico:
        return  # GREEN — implementado

    erros: list[str] = []
    if not has_transacoes:
        erros.append(
            "FinanceiroRoom.tsx type Tab NAO contem 'transacoes'.  "
            f"Tipo atual: {tab_union}.  "
            "Esperado: type Tab = 'decisoes' | 'transacoes' | 'tarefas' | 'config'"
        )
    if has_compromissos:
        erros.append(
            "FinanceiroRoom.tsx type Tab AINDA contem 'compromissos'.  "
            "Esperado: a aba 'compromissos' deve ser removida e substituida "
            "pela nova aba unificada 'transacoes'."
        )
    if has_historico:
        erros.append(
            "FinanceiroRoom.tsx type Tab AINDA contem 'historico'.  "
            "Esperado: a aba 'historico' deve ser removida e substituida "
            "pela nova aba unificada 'transacoes'."
        )

    pytest.fail("\n".join(erros))


# ── AC#2 — Array de tabs DEVE conter 'transacoes' e NAO conter 'compromissos' nem 'historico'


def test_b2_ac2_tabs_array_contem_transacoes_label_transacoes():
    """AC#2: O array de tabs renderizado em FinanceiroRoom.tsx DEVE
    conter 'transacoes' e NAO conter 'compromissos' nem 'historico'.
    O label da aba transacoes deve ser renderizado como "Transacoes".

    Falha (RED) enquanto o array ainda tiver 'compromissos' e/ou
    'historico', ou nao tiver 'transacoes'.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    tabs_array = _extract_tabs_array(source)
    if tabs_array is None:
        pytest.fail(
            "FinanceiroRoom.tsx NAO declara um array de tabs no formato "
            "(['...', '...'] as Tab[]).map(t => ...).  "
            "Esperado: (['decisoes', 'transacoes', 'tarefas', 'config'] as Tab[]).map(t => ...)"
        )

    has_transacoes = _tabs_array_contains(tabs_array, "transacoes")
    has_compromissos = _tabs_array_contains(tabs_array, "compromissos")
    has_historico = _tabs_array_contains(tabs_array, "historico")

    if has_transacoes and not has_compromissos and not has_historico:
        # Verificar label "Transacoes" no JSX
        if not re.search(r"['\"]Trans[^\"']*ções['\"]", source, re.IGNORECASE):
            pytest.fail(
                "FinanceiroRoom.tsx tem a aba 'transacoes' no array, mas o "
                "label renderizado NAO contem 'Transações'.  "
                "Esperado: o label visivel da aba deve ser 'Transações'."
            )
        return  # GREEN — implementado

    erros: list[str] = []
    if not has_transacoes:
        erros.append(
            "FinanceiroRoom.tsx array de tabs NAO contem 'transacoes'.  "
            f"Array atual: [{tabs_array}].  "
            "Esperado: ['decisoes', 'transacoes', 'tarefas', 'config']"
        )
    if has_compromissos:
        erros.append(
            "FinanceiroRoom.tsx array de tabs AINDA contem 'compromissos'.  "
            "Esperado: a aba 'compromissos' deve ser removida e mesclada "
            "na nova aba 'transacoes'."
        )
    if has_historico:
        erros.append(
            "FinanceiroRoom.tsx array de tabs AINDA contem 'historico'.  "
            "Esperado: a aba 'historico' deve ser removida e mesclada "
            "na nova aba 'transacoes'."
        )

    pytest.fail("\n".join(erros))


# ── AC#3 — Conteudo unificado: aba transacoes DEVE exibir polpBills E polpTransactions


def test_b2_ac3_conteudo_unificado_bills_e_transactions():
    """AC#3: A aba transacoes em FinanceiroRoom.tsx DEVE exibir
    conteudo unificado com polpBills (faturas) E polpTransactions
    (transacoes) em uma unica listagem.

    Falha (RED) enquanto a aba transacoes nao existir ou nao
    referenciar ambas as fontes de dados.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    if not _has_transacoes_tab_block(source):
        pytest.fail(
            "FinanceiroRoom.tsx NAO tem um bloco JSX para a aba 'transacoes'.  "
            "Esperado: um bloco com id=\"f-transacoes\" ou um bloco "
            "condicional tab === 'transacoes' que renderiza conteudo unificado."
        )

    block = _extract_transacoes_block(source)
    if not block:
        pytest.fail(
            "Nao foi possivel extrair o bloco da aba 'transacoes' em "
            "FinanceiroRoom.tsx para inspecao do conteudo unificado."
        )

    has_polp_bills = bool(re.search(r"polpBills", block))
    has_polp_transactions = bool(re.search(r"polpTransactions", block))

    if has_polp_bills and has_polp_transactions:
        return  # GREEN — implementado

    erros: list[str] = []
    if not has_polp_bills:
        erros.append(
            "FinanceiroRoom.tsx aba 'transacoes' NAO referencia polpBills "
            "(faturas).  "
            "Esperado: a listagem unificada deve incluir as faturas de "
            "polpBills alem das transacoes de polpTransactions."
        )
    if not has_polp_transactions:
        erros.append(
            "FinanceiroRoom.tsx aba 'transacoes' NAO referencia polpTransactions "
            "(transacoes).  "
            "Esperado: a listagem unificada deve incluir as transacoes de "
            "polpTransactions alem das faturas de polpBills."
        )

    pytest.fail("\n".join(erros))


# ── AC#4 — Filtro de periodo com 4 opcoes: hoje, 7d, 30d, tudo


def test_b2_ac4_filtro_periodo_4_opcoes_hoje_7d_30d_tudo():
    """AC#4: A aba transacoes em FinanceiroRoom.tsx DEVE oferecer um
    filtro de periodo com 4 opcoes: "hoje", "7d", "30d", "tudo".

    Falha (RED) enquanto nao houver um objeto/array/literal no arquivo
    que defina as 4 opcoes de periodo.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    if _has_period_filter_with_4_options(source):
        return  # GREEN — implementado

    pytest.fail(
        "FinanceiroRoom.tsx NAO define um filtro de periodo com as 4 opcoes "
        "obrigatorias: 'hoje', '7d', '30d', 'tudo'.  "
        "Esperado: um literal/objeto/const no arquivo (ex: "
        "const TX_PERIODS = { hoje: 'Hoje', '7d': '7 dias', '30d': '30 dias', tudo: 'Tudo' } "
        "ou similar) que defina as 4 opcoes de periodo usadas na aba transacoes."
    )


# ── AC#5 — Badge de contagem de faturas abertas mantido na aba transacoes


def test_b2_ac5_badge_faturas_abertas_na_aba_transacoes():
    """AC#5: A aba transacoes em FinanceiroRoom.tsx DEVE manter o
    badge de contagem de faturas abertas
    (polpBills.filter(b => b.status !== 'CLOSED').length).

    Falha (RED) enquanto a aba transacoes nao existir ou nao tiver
    o badge com a contagem de faturas abertas.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    if not _has_transacoes_tab_block(source):
        pytest.fail(
            "FinanceiroRoom.tsx NAO tem um bloco JSX para a aba 'transacoes'.  "
            "Esperado: a nova aba unificada deve manter o badge de contagem "
            "de faturas abertas (polpBills.filter(b => b.status !== 'CLOSED').length) "
            "que existia na antiga aba 'compromissos'."
        )

    if _has_open_bills_badge_in_transacoes(source):
        return  # GREEN — implementado

    pytest.fail(
        "FinanceiroRoom.tsx aba 'transacoes' NAO mantem o badge de contagem "
        "de faturas abertas.  "
        "Esperado: dentro do bloco da aba transacoes deve aparecer a expressao "
        "polpBills.filter(b => b.status !== 'CLOSED').length (ou equivalente) "
        "associada a um badge/contador, preservando o comportamento que existia "
        "na antiga aba 'compromissos'."
    )
