"""RED test for behavior B-2 — Nova estrutura EstrategiaRoom com 4 abas.

GOAL:
    Criar nova EstrategiaRoom.tsx com 4 abas (objetivos, documentos, conhecimento, config)
    baseada na fusão de DocumentosRoom + antiga EstrategiaRoom.

BEHAVIOR:
    B-2 — Nova estrutura EstrategiaRoom com 4 abas (objetivos, documentos, conhecimento, config).

    After the fix:
    - O header da sala exibe 🎯 com título "Estratégia"
    - O componente possui 4 abas: Objetivos, Documentos, Conhecimento, Config
    - A navegação entre abas funciona via onClick que muda o estado da tab

AC (Acceptance Criteria):
    AC#1 — Header exibe "Estratégia" com ícone 🎯
    AC#2 — 4 abas corretas (Objetivos, Documentos, Conhecimento, Config)
    AC#3 — Navegação entre abas funciona (cada aba tem onClick handler com setTab)

Estado atual (antes da correção):
    O componente EstrategiaRoom.tsx existe com abas:
    'decisoes', 'analises', 'historico', 'config'
    (labels: "Decisões", "Análises", "Histórico", "Config")

    Após a correção (GREEN), deve ter:
    'objetivos', 'documentos', 'conhecimento', 'config'
    (labels: "Objetivos", "Documentos", "Conhecimento", "Config")
"""

import pathlib


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_ESTRATEGIA_ROOM_PATH = _APP_SRC / "pages" / "app" / "EstrategiaRoom.tsx"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB2NovaEstrategiaRoom:
    """B-2: Nova estrutura EstrategiaRoom com 4 abas."""

    # -----------------------------------------------------------------
    # AC#1 — Header exibe "Estratégia" com ícone 🎯
    #   Esse teste pode passar no código atual (False RED) — é um guarda
    #   de regressão para garantir que a refatoração preserva o header.
    # -----------------------------------------------------------------

    def test_header_exibe_icone_estrategia(self):
        """AC#1: O header deve conter 🎯 e o título 'Estratégia'."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Verifica que o ícone da sala está presente
        assert "🎯" in source, (
            "AC#1 violado: O componente EstrategiaRoom não contém o ícone 🎯. "
            "O header deve exibir o emoji 🎯 como ícone da sala de Estratégia."
        )

        # Verifica que o título "Estratégia" está presente
        assert "Estratégia" in source, (
            "AC#1 violado: O componente EstrategiaRoom não contém o texto "
            "'Estratégia'. O header deve exibir 'Estratégia' como nome da sala."
        )

        # Verifica que existe uma estrutura de header (className="rh" ou similar)
        has_rh = 'className="rh"' in source or "className='rh'" in source
        assert has_rh, (
            "AC#1 violado: O componente EstrategiaRoom não possui a estrutura "
            "de header (className=\"rh\"). O header com 🎯 e 'Estratégia' "
            "deve estar dentro de um container com classe 'rh'."
        )

    # -----------------------------------------------------------------
    # AC#2 — 4 abas corretas (Objetivos, Documentos, Conhecimento, Config)
    #   Esse teste é o principal RED — o código atual tem abas diferentes
    #   ('decisoes', 'analises', 'historico', 'config') e NÃO contém
    #   'objetivos', 'documentos', 'conhecimento' como valores de tab.
    # -----------------------------------------------------------------

    def test_possui_quatro_abas_novas_no_tipo_tab(self):
        """AC#2: As 4 novas abas (objetivos, documentos, conhecimento, config)
        devem estar definidas no type/array de tabs."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        novos_tabs = ["'objetivos'", "'documentos'", "'conhecimento'", "'config'"]
        for tab in novos_tabs:
            assert tab in source, (
                f"AC#2 violado: O valor '{tab}' não foi encontrado no "
                f"componente EstrategiaRoom. O tipo Tab (ou array de tabs) "
                f"deve incluir as 4 novas abas: objetivos, documentos, "
                f"conhecimento, config."
            )

    def test_possui_quatro_labels_corretos_no_jsx(self):
        """AC#2: Os 4 labels (Objetivos, Documentos, Conhecimento, Config)
        devem aparecer no JSX renderizado."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        labels = ["Objetivos", "Documentos", "Conhecimento", "Config"]
        for label in labels:
            assert label in source, (
                f"AC#2 violado: O label '{label}' não foi encontrado no JSX "
                f"renderizado. As 4 abas (Objetivos, Documentos, Conhecimento, "
                f"Config) devem aparecer no template da sala."
            )

    # -----------------------------------------------------------------
    # AC#3 — Navegação entre abas funciona (onClick + setTab)
    #   Esse teste pode passar no código atual (False RED) pois o
    #   componente já tem onClick e setTab — é um guarda de regressão
    #   para garantir que a refatoração mantém a navegação funcional.
    # -----------------------------------------------------------------

    def test_abas_possuem_onclick_e_settab(self):
        """AC#3: As abas devem ter onClick handler que chama setTab."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Verifica que existe um estado 'tab' gerenciado por useState
        has_use_state = "useState" in source
        assert has_use_state, (
            "AC#3 violado: O componente EstrategiaRoom não utiliza useState. "
            "É necessário um estado 'tab' para controlar qual aba está ativa."
        )

        # Verifica que existe onClick handler nos elementos de aba
        assert "onClick" in source, (
            "AC#3 violado: Nenhum onClick handler foi encontrado no componente. "
            "Cada aba deve ter um evento onClick que altera a aba ativa via setTab."
        )

        # Verifica que setTab é chamado para navegação
        assert "setTab" in source, (
            "AC#3 violado: O componente não possui setTab para alterar a aba "
            "ativa. A navegação entre abas deve usar setTab(atualizar estado)."
        )

        # Verifica que as NOVAS abas fazem parte da navegação
        # (iteração sobre array de tabs com .map)
        assert ".map((t)" in source or ".map(t" in source, (
            "AC#3 violado: Não foi encontrada iteração (.map) sobre as abas. "
            "As 4 abas devem ser renderizadas via .map com onClick em cada item."
        )
