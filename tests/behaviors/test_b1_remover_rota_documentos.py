"""RED test for behavior B-1 — Sidebar + Routing: remove "Documentos", redirect → estrategia.

GOAL:
    Remover entrada "Documentos" da sidebar; redirecionar rota `documentos → estrategia`;
    atualizar Screen type no appStore.

BEHAVIOR:
    B-1 — Sidebar + Roteamento: remover "Documentos" da sidebar, redirect → estrategia,
    limpar Screen type.

    After the fix:
    - NAV_ITEMS in Sidebar.tsx must NOT contain 'documentos'
    - AppShell.tsx must NOT render a 'documentos' screen div
    - Screen type in appStore.ts must NOT include 'documentos'
    - SCREEN_LABELS in appStore.ts must NOT include 'documentos'
    - screenFromHash() must redirect '#room/documentos' → 'estrategia'

AC (Acceptance Criteria):
    AC#1 — Sidebar não exibe mais entrada "Documentos"
    AC#2 — Clicar na entrada "Documentos" da sidebar redireciona para a sala Estrategia
    AC#3 — Navegação mobile também reflete a mudança

Estado atual: RED — the assertions below verify the expected state. If all pass,
the behavior is already GREEN (False RED scenario).
"""

import pathlib


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_SIDEBAR_PATH = _APP_SRC / "components" / "shell" / "Sidebar.tsx"
_APPSHELL_PATH = _APP_SRC / "components" / "shell" / "AppShell.tsx"
_APPSTORE_PATH = _APP_SRC / "store" / "appStore.ts"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB1RemoverRotaDocumentos:
    """AC#1: Sidebar não exibe mais entrada "Documentos"."""

    def test_sidebar_nao_tem_documentos_nav_item(self):
        """AC#1: NAV_ITEMS no Sidebar.tsx não deve conter entrada 'documentos'."""
        source = _read(_SIDEBAR_PATH)

        # Find the NAV_ITEMS array declaration
        nav_start = source.find("const NAV_ITEMS: NavItem[] = [")
        assert nav_start != -1, (
            "AC#1 violado: não foi encontrado 'const NAV_ITEMS: NavItem[] = [' "
            "no Sidebar.tsx. Verificar estrutura do arquivo."
        )

        # Extract the array contents (between [ and ])
        nav_end = source.find("]\n\nconst FOOT_ITEMS", nav_start)
        if nav_end == -1:
            nav_end = source.find("];", nav_start)
        assert nav_end != -1, (
            "AC#1 violado: não foi possível determinar o fim do array NAV_ITEMS."
        )

        nav_section = source[nav_start:nav_end + 1]

        # Check that no 'documentos' screen reference exists
        assert "'documentos'" not in nav_section or '"documentos"' not in nav_section, (
            "AC#1 violado: NAV_ITEMS ainda contém referência a 'documentos'. "
            "A entrada `{ s: 'documentos', icon: ..., label: 'Documentos' }` "
            "deve ser removida do array NAV_ITEMS em Sidebar.tsx."
        )

    def test_sidebar_nao_tem_documentos_nav_item_label(self):
        """AC#1: NAV_ITEMS no Sidebar.tsx não deve conter label 'Documentos'."""
        source = _read(_SIDEBAR_PATH)

        nav_start = source.find("const NAV_ITEMS: NavItem[] = [")
        nav_end = source.find("]", nav_start)

        nav_section = source[nav_start:nav_end + 1]

        assert "Documentos" not in nav_section, (
            "AC#1 violado: NAV_ITEMS ainda contém label 'Documentos'. "
            "A entrada com label: 'Documentos' deve ser removida."
        )

    def test_screen_type_nao_tem_documentos(self):
        """AC#2: Screen type no appStore.ts não deve incluir 'documentos'."""
        source = _read(_APPSTORE_PATH)

        screen_type_start = source.find("export type Screen =")
        assert screen_type_start != -1, (
            "AC#2 violado: não foi encontrado 'export type Screen =' "
            "no appStore.ts."
        )

        # Extract the Screen union type
        pipe_pos = source.find("|", screen_type_start)
        assert pipe_pos != -1, (
            "AC#2 violado: Screen type não parece ser um union type com '|'."
        )

        # Look for 'documentos' in the type definition
        screen_section = source[screen_type_start:pipe_pos + 200]

        assert "'documentos'" not in screen_section, (
            "AC#2 violado: Screen type ainda contém 'documentos'. "
            "O literal 'documentos' deve ser removido do union type Screen "
            "em appStore.ts, já que a rota agora redireciona para 'estrategia'."
        )

    def test_screen_labels_nao_tem_documentos(self):
        """AC#2: SCREEN_LABELS no appStore.ts não deve incluir 'documentos'."""
        source = _read(_APPSTORE_PATH)

        labels_start = source.find("const SCREEN_LABELS: Record<Screen, string> = {")
        assert labels_start != -1, (
            "AC#2 violado: não foi encontrado 'const SCREEN_LABELS' no appStore.ts."
        )

        labels_end = source.find("}", labels_start)
        labels_section = source[labels_start:labels_end + 1]

        assert "documentos:" not in labels_section, (
            "AC#2 violado: SCREEN_LABELS ainda contém 'documentos:'. "
            "A entrada 'documentos: 'Documentos'' deve ser removida do "
            "dicionário SCREEN_LABELS em appStore.ts."
        )

    def test_screen_from_hash_redirects_documentos_to_estrategia(self):
        """AC#2: screenFromHash() deve redirecionar '#room/documentos' → 'estrategia'."""
        source = _read(_APPSTORE_PATH)

        hash_func_start = source.find("function screenFromHash(): Screen {")
        assert hash_func_start != -1, (
            "AC#2 violado: não foi encontrada a função 'screenFromHash()' "
            "no appStore.ts."
        )

        hash_func_end = source.find("return 'home'", hash_func_start)
        assert hash_func_end != -1, (
            "AC#2 violado: não foi encontrado 'return 'home'' "
            "dentro de screenFromHash()."
        )

        hash_section = source[hash_func_start:hash_func_end + 20]

        assert "documentos" in hash_section, (
            "AC#2 violado: screenFromHash() não contém referência a 'documentos'. "
            "Deve haver um redirect de '#room/documentos' para 'estrategia' "
            "para manter compatibilidade com links antigos: "
            "`if (window.location.hash === '#room/documentos') return 'estrategia'`."
        )
        assert "return 'estrategia'" in hash_section, (
            "AC#2 violado: screenFromHash() não retorna 'estrategia' "
            "quando o hash é '#room/documentos'. O redirect deve existir: "
            "`if (window.location.hash === '#room/documentos') return 'estrategia'`."
        )

    def test_appshell_nao_renderiza_screen_documentos(self):
        """AC#3: AppShell.tsx não deve renderizar um bloco screen para 'documentos'."""
        source = _read(_APPSHELL_PATH)

        # Check that there's no screen div for documentos
        assert 'id="s-documentos"' not in source, (
            "AC#3 violado: AppShell.tsx ainda renderiza um bloco "
            "com 'id=\"s-documentos\"'. O bloco completo "
            "`<div className={`screen${on('documentos')}`} id=\"s-documentos\">` "
            "deve ser removido, já que DocumentosRoom não é mais uma tela "
            "independente."
        )

    def test_appshell_nao_importa_documentos_room(self):
        """AC#3: AppShell.tsx não deve importar DocumentosRoom."""
        source = _read(_APPSHELL_PATH)

        assert "DocumentosRoom" not in source, (
            "AC#3 violado: AppShell.tsx ainda importa ou referencia "
            "'DocumentosRoom'. Esse componente foi removido e seu "
            "conteúdo movido para dentro de EstrategiaRoom como uma aba."
        )

    def test_mobile_nav_reflects_change(self):
        """AC#3: A navegação mobile (mobile-nav / mobile-menu) também reflete a mudança.

        Verifica que o componente Sidebar.tsx não renderiza 'documentos'
        na navegação mobile (allItems), já que allItems é composto de
        NAV_ITEMS + visibleFootItems, e NAV_ITEMS já foi limpo.
        """
        source = _read(_SIDEBAR_PATH)

        # Check the allItems array uses NAV_ITEMS (which is already clean)
        all_items_idx = source.find("const allItems = [...NAV_ITEMS, ...visibleFootItems]")
        assert all_items_idx != -1, (
            "AC#3 violado: não foi encontrado o array 'allItems' que combina "
            "NAV_ITEMS e visibleFootItems para a navegação mobile. "
            "Se 'allItems' não usa NAV_ITEMS diretamente, a navegação mobile "
            "pode estar desalinhada com a sidebar desktop."
        )

        # Check that the mobile nav render uses allItems
        mobile_render_idx = source.find("allItems.map(item")
        assert mobile_render_idx != -1, (
            "AC#3 violado: o menu mobile não itera sobre 'allItems'. "
            "Se o mobile nav tem sua própria lista estática de itens, "
            "a entrada 'documentos' pode ainda estar presente na navegação mobile."
        )

    def test_appshell_nao_tem_screen_width_estrategia_replaces_documentos(self):
        """AC#2: AppShell deve exibir EstrategiaRoom normalmente (sem perda de funcionalidade)."""
        source = _read(_APPSHELL_PATH)

        # EstrategiaRoom should still be rendered
        estrategia_import = "EstrategiaRoom" in source
        assert estrategia_import, (
            "AC#2 violado: AppShell.tsx não importa EstrategiaRoom. "
            "Como 'documentos' agora redireciona para 'estrategia', "
            "a sala EstrategiaRoom deve permanecer na renderização."
        )

        estrategia_screen = 'id="s-estrategia"' in source or "s-estrategia" in source
        assert estrategia_screen, (
            "AC#2 violado: AppShell.tsx não renderiza a tela 'estrategia'. "
            "Após remover 'documentos', a sala EstrategiaRoom deve continuar "
            "sendo renderizada normalmente para receber o redirect."
        )
