"""RED test — B-1 (BATCH #208): Renomear abas da EstrategiaRoom.

GOAL:
    Trocar as tabs de ``decisoes/analises/historico/config`` para
    ``objetivos/documentos/conhecimento/config`` e mapear o conteudo
    antigo para a nova estrutura.

BEHAVIOR:
    "B-1 — Renomear abas da EstrategiaRoom: type Tab inclui apenas
    objetivos|documentos|conhecimento|config, tabs array renderiza
    headers corretos, activeTab default usa objetivos, old tabs
    removidas."

    A改造 deve:
        1. Substituir ``type Tab`` para os 4 novos valores.
        2. Trocar o default de ``useState<Tab>`` de 'decisoes' para
           'objetivos'.
        3. Substituir o array literal de renderizacao para os novos
           valores.
        4. Remover completamente as tabs antigas ('decisoes',
           'analises', 'historico') como valores de tab.
        5. Atualizar os labels das tabs para Objetivos | Documentos |
           Conhecimento | Config.
        6. Preservar o pattern de visibilidade ``tc${tab === t ? ...}``.
        7. Remover a secao de conteudo ``// DECISOES`` (que renderizava
           o painel antigo de decisoes).

    Estado atual (BEFORE — RED):
        O arquivo ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx``
        AINDA usa a taxonomia antiga:
            - type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
            - useState<Tab>('decisoes')
            - (['decisoes', 'analises', 'historico', 'config'] as Tab[])
            - Labels: Decisoes, Analises, Historico, Config
            - Secao // DECISÕES presente

    Estado esperado (AFTER — GREEN):
        O arquivo estara com a nova taxonomia:
            - type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'
            - useState<Tab>('objetivos')
            - (['objetivos', 'documentos', 'conhecimento', 'config'] as Tab[])
            - Labels: Objetivos, Documentos, Conhecimento, Config

AC (Acceptance Criteria):
    AC#1 - ``type Tab`` inclui 'objetivos' | 'documentos' | 'conhecimento'
           | 'config' (regex: type Tab = ...)
    AC#2 - ``useState<Tab>`` usa 'objetivos' como default
           (useState<Tab>("objetivos"))
    AC#3 - Tabs array usa (["objetivos", "documentos", "conhecimento",
           "config"] as Tab[])
    AC#4 - Tabs antigas (decisoes, analises, historico) NAO existem
           mais como valores de tab
    AC#5 - Tab render labels incluem Objetivos, Documentos,
           Conhecimento, Config
    AC#6 - ``tc`` className pattern preserved (tab === t ternary
           visibility control)
    AC#7 - "decisoes" tab content section (// DECISOES / tab ===
           "decisoes") removida

Anti-Goals:
    1. NAO modificar codigo de producao (EstrategiaRoom.tsx).
    2. NAO executar/transpilar TSX — somente inspecao textual com
       regex.
    3. NAO usar mocks, Supabase ou banco de dados.
    4. NAO quebrar funcionalidade existente.
    5. NAO relaxar o teste para que ele passe — precisa ser TRUE RED
       agora (codigo AINDA usa tabs antigas).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

TARGET_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao textual do arquivo EstrategiaRoom.tsx, sem teardown
    no Supabase, sem rede, sem import/execucao de TSX.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o arquivo TSX como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-1 (BATCH #208) exige que o arquivo "
        "apps/blu_v3/src/pages/app/EstrategiaRoom.tsx exista no repo.  "
        "O coder precisa garantir que EstrategiaRoom.tsx esteja presente "
        "antes que este teste possa passar (GREEN)."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-1 ────────────────


@pytest.mark.behaviors
def test_b1_renomear_abas_estrategiaroom_red() -> None:
    """B-1 (BATCH #208) — RED.  Falha enquanto EstrategiaRoom.tsx ainda
    usar a taxonomia antiga de tabs (decisoes|analises|historico|config)
    em vez da nova (objetivos|documentos|conhecimento|config).

    Esta funcao agrega a verificacao de TODOS os ACs em uma unica
    assercao: coleta todas as deficiencias e dispara ``pytest.fail``
    com mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(TARGET_PATH)

    problemas: list[str] = []

    # ── AC#1 — type Tab = "objetivos" | "documentos" | "conhecimento" | "config" ──
    #     Evidencia esperada: type Tab = com os 4 novos valores
    tab_decl_match = re.search(
        r"type\s+Tab\s*=\s*([^\n]+)",
        source,
    )
    if not tab_decl_match:
        problemas.append(
            "AC#1 — `type Tab = ...` NAO encontrado no arquivo EstrategiaRoom.tsx.  "
            "O behavior B-1 exige que o tipo `Tab` seja declarado com os 4 "
            "novos valores: 'objetivos' | 'documentos' | 'conhecimento' | "
            "'config'."
        )
        tab_decl = ""
    else:
        tab_decl = tab_decl_match.group(1)
        for valor in ["objetivos", "documentos", "conhecimento", "config"]:
            if not re.search(rf"['\"]\s*{valor}\s*['\"]", tab_decl):
                problemas.append(
                    f"AC#1 — valor '{valor}' NAO presente no `type Tab = ...` "
                    f"em EstrategiaRoom.tsx.  "
                    f"Declaracao atual: {tab_decl.strip()}\n"
                    f"Esperado: type Tab = 'objetivos' | 'documentos' | "
                    f"'conhecimento' | 'config'"
                )

    # ── AC#2 — useState<Tab>("objetivos") como default ──────────────
    #     Evidencia esperada: useState<Tab>('objetivos') ou useState<Tab>("objetivos")
    has_default_objetivos = bool(
        re.search(
            r"useState\s*<\s*Tab\s*>\s*\(\s*['\"]\s*objetivos\s*['\"]\s*\)",
            source,
        )
    )

    if not has_default_objetivos:
        problemas.append(
            "AC#2 — `useState<Tab>('objetivos')` NAO presente.  "
            "O default do state de tab precisa ser 'objetivos' (e NAO "
            "'decisoes'), para que ao entrar na sala a primeira aba "
            "ativa seja a de objetivos."
        )

    # ── AC#3 — Tabs array = ["objetivos", "documentos", "conhecimento", "config"] ──
    #     Evidencia esperada: (['objetivos', 'documentos', 'conhecimento', 'config'] as Tab[])
    has_tabs_array = bool(
        re.search(
            r"\[\s*['\"]\s*objetivos\s*['\"]\s*,\s*['\"]\s*documentos\s*['\"]\s*,\s*"
            r"['\"]\s*conhecimento\s*['\"]\s*,\s*['\"]\s*config\s*['\"]\s*\]"
            r"\s*as\s+Tab\s*\[\s*\]",
            source,
        )
    )

    if not has_tabs_array:
        problemas.append(
            "AC#3 — tabs array `(['objetivos', 'documentos', 'conhecimento', "
            "'config'] as Tab[])` NAO presente.  "
            "O array literal que renderiza os headers das abas precisa ser "
            "atualizado para os 4 novos valores na ORDEM: objetivos, "
            "documentos, conhecimento, config."
        )

    # ── AC#4 — Tabs antigas removidas (decisoes, analises, historico) ──
    #     Verifica 2 pontos:
    #       (a) o array literal antigo NAO existe mais
    #       (b) o type Tab NAO contem os valores antigos
    old_tabs_array_pattern = re.search(
        r"\[\s*['\"]\s*decisoes\s*['\"]\s*,\s*['\"]\s*analises\s*['\"]\s*,\s*"
        r"['\"]\s*historico\s*['\"]\s*,\s*['\"]\s*config\s*['\"]\s*\]",
        source,
    )
    if old_tabs_array_pattern:
        problemas.append(
            "AC#4 — array de tabs antigo ['decisoes', 'analises', 'historico', "
            "'config'] AINDA presente no EstrategiaRoom.tsx.  "
            "O coder precisa substituir este array literal pelo novo com "
            "os 4 valores: ['objetivos', 'documentos', 'conhecimento', "
            "'config']."
        )

    for valor_antigo in ["decisoes", "analises", "historico"]:
        # (b) nao pode estar no type Tab
        if tab_decl and re.search(rf"['\"]\s*{valor_antigo}\s*['\"]", tab_decl):
            problemas.append(
                f"AC#4 — valor antigo '{valor_antigo}' AINDA presente no "
                f"`type Tab` em EstrategiaRoom.tsx.  "
                f"Declaracao atual: {tab_decl.strip()}\n"
                f"Os valores antigos (decisoes, analises, historico) devem "
                f"ser removidos do type Tab."
            )
        # (b2) nao pode aparecer como valor de tab no array de renderizacao
        if re.search(
            rf"\[\s*['\"]\s*objetivos\s*['\"].*['\"]\s*{valor_antigo}\s*['\"]",
            source,
        ):
            problemas.append(
                f"AC#4 — valor antigo '{valor_antigo}' encontrado no novo "
                f"array de tabs.  O array de renderizacao deve conter APENAS "
                f"os 4 novos valores: objetivos, documentos, conhecimento, config."
            )

    # ── AC#5 — Labels Objetivos, Documentos, Conhecimento, Config ─────
    #     Evidencia esperada: as strings "Objetivos", "Documentos",
    #     "Conhecimento", "Config" aparecem no template (em aspas
    #     simples ou duplas, ou como filhos JSX entre aspas).
    labels_esperados = ["Objetivos", "Documentos", "Conhecimento", "Config"]
    for label in labels_esperados:
        # Aceita tanto 'Label' quanto "Label" (TS string literal)
        # quanto sem aspas em alguns contextos JSX
        quoted = bool(re.search(rf"['\"]\s*{re.escape(label)}\s*['\"]", source))
        if not quoted:
            problemas.append(
                f"AC#5 — label '{label}' NAO encontrado no template de "
                f"EstrategiaRoom.tsx.  "
                f"O coder precisa atualizar os labels das tabs para: "
                f"Objetivos | Documentos | Conhecimento | Config."
            )

    # ── AC#6 — tc className pattern preserved (tab === t ternary) ────
    #     Evidencia esperada: o pattern `tab === t ?` (com `t` como
    #     variavel, NAO literal) existe em pelo menos um className de
    #     painel condicional.
    has_tab_equals_t = bool(
        re.search(
            r"tab\s*===\s*t\s*\?",
            source,
        )
    )

    if not has_tab_equals_t:
        problemas.append(
            "AC#6 — pattern `tab === t ?` NAO preservado.  "
            "O EstrategiaRoom.tsx precisa manter a visibilidade das "
            "abas via o ternario `tab === t ? ' on' : ''` (onde `t` e a "
            "variavel do .map), garantindo que o controle de visibilidade "
            "dos paineis condicionais continua generico e nao hard-coded "
            "para um valor literal especifico."
        )

    # ── AC#7 — Secao // DECISOES (painel antigo) removida ────────────
    #     Evidencia esperada: o comentario de secao "// DECISOES" (ou
    #     a variante JSX {/* DECISÕES */}) NAO existe mais, e o
    #     ternario `tab === 'decisoes'` NAO existe mais no className
    #     de painel.
    has_decisoes_section_comment = bool(
        re.search(
            r"//\s*DECIS(?:OES|ÕES)\b",
            source,
        )
    )
    has_decisoes_jsx_comment = bool(
        re.search(
            r"\{/\*\s*DECIS(?:OES|ÕES)\s*\*/\}",
            source,
        )
    )
    has_decisoes_panel_ternary = bool(
        re.search(
            r"tab\s*===\s*['\"]\s*decisoes\s*['\"]",
            source,
        )
    )

    if has_decisoes_section_comment or has_decisoes_jsx_comment:
        problemas.append(
            "AC#7 — comentario de secao `// DECISOES` / `// DECISÕES` "
            "(ou variante JSX `{/* DECISÕES */}`) AINDA presente em "
            "EstrategiaRoom.tsx.  "
            "Esta secao renderizava o painel antigo de decisoes; ela precisa "
            "ser removida (ou renomeada) como parte do rename das tabs."
        )
    if has_decisoes_panel_ternary:
        problemas.append(
            "AC#7 — ternario `tab === 'decisoes'` AINDA presente em "
            "EstrategiaRoom.tsx.  "
            "O painel que usava 'decisoes' como valor de visibilidade "
            "precisa ser removido/renomeado para usar os novos valores "
            "(objetivos/documentos/conhecimento/config)."
        )

    # ── Agrega todas as deficiencias ─────────────────────────────────
    if problemas:
        cabecalho = (
            f"[RED] B-1 (BATCH #208) — Renomear abas da EstrategiaRoom — "
            f"{len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  • {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
