"""RED test for behavior B-2 — Nova estrutura EstrategiaRoom com 4 abas.

GOAL:
    Transformar as abas da EstrategiaRoom de (decisoes, analises, historico, config)
    para (objetivos, documentos, conhecimento, config).

BEHAVIOR:
    B-2 — Nova estrutura EstrategiaRoom com 4 abas (objetivos, documentos, conhecimento, config).

    After the fix:
    - EstrategiaRoom.tsx must have Tab type: 'objetivos' | 'documentos' | 'conhecimento' | 'config'
    - The tab array must render: Objetivos, Documentos, Conhecimento, Config
    - Tab navigation (onClick + setTab) must work
    - Header must still show 🎯 + "Estratégia"

AC (Acceptance Criteria):
    AC#1 — Header exibe "Estratégia" com ícone 🎯
    AC#2 — 4 abas corretas (Objetivos, Documentos, Conhecimento, Config)
    AC#3 — Navegação entre abas funciona (onClick handler em cada aba)

Estado atual: RED — AC#2 will fail on current code (TRUE RED). AC#1 and AC#3
may pass (False RED, regression guards).
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

    # ------------------------------------------------------------------
    # AC#1 — Header
    # ------------------------------------------------------------------

    def test_header_exibe_estrategia_com_emoji_alvo(self):
        """AC#1: Header exibe 'Estratégia' com ícone 🎯."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        assert "🎯" in source, (
            "AC#1 violado: o ícone 🎯 não foi encontrado no arquivo "
            "EstrategiaRoom.tsx. O header deve exibir o emoji 🎯 "
            "para identificar a sala de Estratégia."
        )

        assert "Estratégia" in source, (
            "AC#1 violado: o texto 'Estratégia' não foi encontrado no arquivo "
            "EstrategiaRoom.tsx. O header deve exibir o nome 'Estratégia' "
            "ao lado do ícone 🎯."
        )

    # ------------------------------------------------------------------
    # AC#2 — 4 abas corretas (PRIMARY RED)
    # ------------------------------------------------------------------

    def test_tab_type_deve_ter_objetivos_documentos_conhecimento_config(self):
        """AC#2: type Tab deve ser 'objetivos' | 'documentos' | 'conhecimento' | 'config'.

        This is the PRIMARY RED assertion. The current code has
        'decisoes' | 'analises' | 'historico' | 'config', so this
        test MUST FAIL when run against the CURRENT code.
        """
        source = _read(_ESTRATEGIA_ROOM_PATH)

        tab_type_start = source.find("type Tab = ")
        assert tab_type_start != -1, (
            "AC#2 violado: não foi encontrada a declaração 'type Tab = ' "
            "no EstrategiaRoom.tsx."
        )

        tab_type_end = source.find("\n", tab_type_start)
        tab_type_line = source[tab_type_start:tab_type_end].strip()

        # The new Tab type must contain all 4 expected values
        # Current value is: type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        # This assertion WILL FAIL → TRUE RED
        assert "'objetivos'" in tab_type_line, (
            "AC#2 (RED) violado: type Tab não contém 'objetivos'. "
            "Esperado: type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'\n"
            "Atual: " + tab_type_line + "\n\n"
            "Para corrigir (GREEN):\n"
            "1. Alterar 'type Tab =' para incluir apenas:\n"
            "   type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'\n"
            "2. Remover os valores antigos: 'decisoes', 'analises', 'historico'"
        )

        assert "'documentos'" in tab_type_line, (
            "AC#2 (RED) violado: type Tab não contém 'documentos'. "
            "Esperado: type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'"
        )

        assert "'conhecimento'" in tab_type_line, (
            "AC#2 (RED) violado: type Tab não contém 'conhecimento'. "
            "Esperado: type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'"
        )

        assert "'config'" in tab_type_line, (
            "AC#2 (RED) violado: type Tab não contém 'config'. "
            "Esperado: type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'"
        )

        # Confirm old values are gone
        assert "'decisoes'" not in tab_type_line, (
            "AC#2 violado: type Tab ainda contém 'decisoes'. "
            "As abas antigas devem ser substituídas pelas novas."
        )

        assert "'analises'" not in tab_type_line, (
            "AC#2 violado: type Tab ainda contém 'analises'. "
            "As abas antigas devem ser substituídas pelas novas."
        )

        assert "'historico'" not in tab_type_line, (
            "AC#2 violado: type Tab ainda contém 'historico'. "
            "As abas antigas devem ser substituídas pelas novas."
        )

    def test_tab_array_deve_conter_novas_abas(self):
        """AC#2: O array de abas (.map) deve conter os 4 novos valores.

        O array usado no .map((t) => deve ser:
        ['objetivos', 'documentos', 'conhecimento', 'config']
        """
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Find the tab array used in the .map() — the line that reads:
        # {(['objetivos', 'documentos', 'conhecimento', 'config'] as Tab[]).map((t) => (
        array_marker = "as Tab[]).map((t) =>"
        array_start = source.find(array_marker)
        assert array_start != -1, (
            "AC#2 violado: não foi encontrado o padrão 'as Tab[]).map((t) =>' "
            "no EstrategiaRoom.tsx."
        )

        # Scan backwards to find the array bracket
        bracket_pos = source.rfind("[", 0, array_start)
        assert bracket_pos != -1, (
            "AC#2 violado: não foi possível localizar o array de abas "
            "antes do .map()."
        )

        array_contents = source[bracket_pos:array_start + len(array_marker)]

        # Current: (['decisoes', 'analises', 'historico', 'config'] as Tab[]).map((t) => (
        # Expected: (['objetivos', 'documentos', 'conhecimento', 'config'] as Tab[]).map((t) => (
        assert "'objetivos'" in array_contents, (
            "AC#2 (RED) violado: o array de abas não contém 'objetivos'. "
            "O array deve ser ['objetivos', 'documentos', 'conhecimento', 'config'].\n"
            "Atual: " + array_contents
        )
        assert "'documentos'" in array_contents, (
            "AC#2 (RED) violado: o array de abas não contém 'documentos'."
        )
        assert "'conhecimento'" in array_contents, (
            "AC#2 (RED) violado: o array de abas não contém 'conhecimento'."
        )

        # Old values must be gone from the array
        assert "'decisoes'" not in array_contents, (
            "AC#2 violado: o array de abas ainda contém 'decisoes'."
        )
        assert "'analises'" not in array_contents, (
            "AC#2 violado: o array de abas ainda contém 'analises'."
        )
        assert "'historico'" not in array_contents, (
            "AC#2 violado: o array de abas ainda contém 'historico'."
        )

    def test_tab_labels_sao_objetivos_documentos_conhecimento_config(self):
        """AC#2: Os labels renderizados para cada aba são Objetivos, Documentos, Conhecimento, Config."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        assert "Objetivos" in source, (
            "AC#2 (RED) violado: label 'Objetivos' não encontrado. "
            "Cada aba deve exibir seu label correspondente: "
            "objetivos → 'Objetivos', documentos → 'Documentos', "
            "conhecimento → 'Conhecimento', config → 'Config'."
        )
        assert "Documentos" in source, (
            "AC#2 (RED) violado: label 'Documentos' não encontrado."
        )
        assert "Conhecimento" in source, (
            "AC#2 (RED) violado: label 'Conhecimento' não encontrado."
        )
        assert "Config" in source, (
            "AC#2 violado: label 'Config' não encontrado."
        )

        # Old labels should not appear (may have other references in the file,
        # but at minimum the tab-rendering ternary patterns should be gone)
        old_tab_render_decisoes = source.find("t === 'decisoes'")
        if old_tab_render_decisoes != -1:
            # Check this is actually in the tab rendering section
            assert False, (
                "AC#2 violado: ainda existe renderização condicional "
                "para a aba 'decisoes'. O bloco `t === 'decisoes' ? ( ... Decisões ...)` "
                "deve ser substituído pelos novos labels."
            )

        old_tab_render_analises = source.find("t === 'analises'")
        if old_tab_render_analises != -1:
            assert False, (
                "AC#2 violado: ainda existe renderização condicional "
                "para a aba 'analises'."
            )

    def test_default_state_deve_ser_objetivos(self):
        """AC#2: O estado inicial da aba deve ser 'objetivos'.

        Current: useState<Tab>('decisoes')
        Expected: useState<Tab>('objetivos')
        """
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Find the useState for tab — look for "useState<Tab>("
        use_state_marker = "useState<Tab>("
        idx = source.find(use_state_marker)
        assert idx != -1, (
            "AC#2 violado: não foi encontrado 'useState<Tab>(' "
            "para o estado da aba ativa."
        )

        # Extract the initial value between the parentheses
        paren_start = idx + len(use_state_marker)
        paren_end = source.find(")", paren_start)
        initial_value_raw = source[paren_start:paren_end].strip()

        # Strip quotes
        initial_value = initial_value_raw.strip("'").strip('"')

        assert initial_value == "objetivos", (
            f"AC#2 (RED) violado: estado inicial da aba é '{initial_value}', "
            "mas deveria ser 'objetivos'. "
            "A aba inicial deve ser 'objetivos' após a reestruturação.\n\n"
            "Para corrigir (GREEN):\n"
            f"Alterar: useState<Tab>('{initial_value}')\n"
            "Para:    useState<Tab>('objetivos')"
        )

    # ------------------------------------------------------------------
    # AC#3 — Navegação entre abas
    # ------------------------------------------------------------------

    def test_tab_navigation_tem_onclick_handler(self):
        """AC#3: Cada aba deve ter um onClick handler que chama setTab."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Check that onClick + setTab navigation exists (regardless of tab names)
        assert "onClick={() => setTab(t)}" in source or 'onClick={() => setTab(t)}' in source, (
            "AC#3 violado: não foi encontrado onClick handler com setTab. "
            "Cada aba (Objetivos, Documentos, Conhecimento, Config) deve ter "
            "um onClick={() => setTab(t)} para navegação entre abas."
        )

        # Check that the tab mapping function uses .map((t) => pattern
        assert ".map((t) =>" in source, (
            "AC#3 violado: não foi encontrado o padrão '.map((t) =>' "
            "para renderização das abas. A navegação entre abas depende "
            "da iteração sobre o array de tabs com .map()."
        )
