"""RED test for behavior B-5 (BKL-032) — Grafo de conhecimento na Biblioteca.

GOAL:
    BibliotecaRoom deve ter view mode "grafo" além dos modos "grid" e "list"
    existentes. O modo grafo mostra nós (documentos) e arestas (relações entre
    categorias/entidades).

BEHAVIOR:
    B-5 — O view mode toggle da BibliotecaRoom deve incluir "grafo" como
    terceiro modo. Quando selecionado, o GraphView deve ser renderizado.

AC (Acceptance Criteria):
    AC#1 — ViewMode type deve incluir 'graph', o toggle deve ter 3 botões
           (grid, list, graph), GraphView deve estar importado e renderizado
           condicionalmente.

ESTADO ATUAL (RED):
    - type ViewMode = 'grid' | 'list' (linha 9) — sem 'graph'
    - Toggle tem 2 botões (linhas 344-355) — sem botão "Grafo"
    - Sem importação de GraphView
    - Sem renderização condicional para modo graph

ESTADO ALVO (GREEN):
    - type ViewMode = 'grid' | 'list' | 'graph'
    - Toggle com 3 botões: grid (⊞), list (≡), graph (➤ ou similar) c/ title="Grafo"
    - import GraphView from '../../components/biblioteca/GraphView'
    - {viewMode === 'graph' && <GraphView .../>}

Anti-Goals:
    1. NAO remover botões grid/list existentes
    2. NAO quebrar filtros (search, category, status)
    3. NAO quebrar upload/lógica existente
    4. NAO introduzir mocks ou dependências de DB
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BIBLIOTECA_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "BibliotecaRoom.tsx"


# ── Source-level helpers ───────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o código-fonte TSX como texto puro."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b5_ac1_viewmode_inclui_graph() -> None:
    """AC#1 — ViewMode type inclui 'graph', toggle tem 3 botões, GraphView importado.

    O type ViewMode deve ser 'grid' | 'list' | 'graph' (não apenas grid|list).
    O view toggle deve ter 3 botões: grid (⊞), list (≡) e graph (title="Grafo").
    GraphView deve estar importado de '../../components/biblioteca/GraphView'.
    O componente <GraphView .../> deve ser renderizado quando viewMode === 'graph'.
    """
    source = _read_source(BIBLIOTECA_PATH)

    # ── 1. Verifica que ViewMode type inclui 'graph' ─────────────────────
    viewmode_match = re.search(r"type\s+ViewMode\s*=", source)
    assert viewmode_match is not None, (
        "RED — AC#1: Declaração 'type ViewMode = ...' não encontrada "
        "em BibliotecaRoom.tsx.\n"
        "  Esperado: type ViewMode = 'grid' | 'list' | 'graph'\n"
        "  O arquivo deve ter a definição do tipo ViewMode."
    )

    # Extrai o conteúdo do type ViewMode
    type_line_start = viewmode_match.start()
    # Pega até o final da linha ou ponto-e-vírgula
    line_end = source.find("\n", type_line_start)
    if line_end == -1:
        line_end = type_line_start + 200
    type_decl = source[type_line_start:line_end].strip()

    has_graph = "'graph'" in type_decl
    assert has_graph, (
        "RED — AC#1: ViewMode type NÃO inclui 'graph'.\n"
        f"  Atual: {type_decl}\n"
        "  Esperado: type ViewMode = 'grid' | 'list' | 'graph'\n"
        "  O Coder deve adicionar ' | graph'' ao type ViewMode.\n"
        "  Localização: linha contendo 'type ViewMode = ' em BibliotecaRoom.tsx."
    )

    # Verifica que 'grid' e 'list' ainda estão presentes (anti-goal #1)
    has_grid = "'grid'" in type_decl
    has_list = "'list'" in type_decl
    if not (has_grid and has_list):
        pytest.fail(
            "RED — AC#1 (anti-goal): ViewMode type PERDEU 'grid' ou 'list'.\n"
            f"  Atual: {type_decl}\n"
            "  ANTI-GOAL VIOLATED: 'grid' e 'list' devem ser PRESERVADOS.\n"
            "  O Coder deve adicionar 'graph' SEM remover grid/list."
        )

    # ── 2. Verifica que o toggle tem 3 botões ────────────────────────────
    # Procura pelo bloco do view toggle (div com botoes grid/list/graph)
    # Padrão: botões com onClick={() => setViewMode('...')}
    toggle_buttons = re.findall(
        r"onClick\s*=\s*\(\s*\)\s*=>\s*setViewMode\s*\(\s*'([^']+)'\s*\)",
        source,
    )

    has_graph_btn = "graph" in toggle_buttons
    assert has_graph_btn, (
        "RED — AC#1: Nenhum botão no view toggle chama setViewMode('graph').\n"
        f"  Botões encontrados: {toggle_buttons}\n"
        "  Esperado: 3 botões chamando setViewMode('grid'), setViewMode('list'), "
        "setViewMode('graph').\n"
        "  O Coder deve adicionar um terceiro botão no view toggle para o modo Grafo.\n"
        "  Localização: div com className='ph' > div com display:flex, gap:2, "
        "marginLeft:'auto' (linhas ~343-356)."
    )

    has_grid_btn = "grid" in toggle_buttons
    has_list_btn = "list" in toggle_buttons
    if not (has_grid_btn and has_list_btn):
        pytest.fail(
            "RED — AC#1 (anti-goal): Botões de grid/list foram REMOVIDOS do toggle.\n"
            f"  Botões encontrados: {toggle_buttons}\n"
            "  ANTI-GOAL VIOLATED: os botões grid e list devem ser PRESERVADOS.\n"
            "  O Coder deve adicionar o botão graph SEM remover grid/list."
        )

    # ── 3. Verifica que o botão graph tem title="Grafo" ──────────────────
    # Procura title="Grafo" associado ao modo graph
    has_grafo_title = bool(re.search(r'title\s*=\s*"Grafo"', source))
    if has_graph_btn and not has_grafo_title:
        # Pode ser que o title ainda não tenha sido adicionado
        pytest.fail(
            "RED — AC#1: Botão para modo graph encontrado, mas sem title='Grafo'.\n"
            "  Esperado: <button ... title='Grafo' ... onClick={...setViewMode('graph')}>\n"
            "    ➤ ou símbolo similar</button>\n"
            "  O Coder deve adicionar title='Grafo' ao botão do modo graph,\n"
            "  consistente com os botões existentes (title='Grade', title='Lista')."
        )

    # ── 4. Verifica importação do GraphView ──────────────────────────────
    has_graphview_import = bool(re.search(
        r"import\s+GraphView\s+from\s+['\"]\.\./\.\./components/biblioteca/GraphView['\"]",
        source,
    ))
    assert has_graphview_import, (
        "RED — AC#1: GraphView não está importado em BibliotecaRoom.tsx.\n"
        "  Esperado: import GraphView from '../../components/biblioteca/GraphView'\n"
        "  O Coder deve importar o componente GraphView da biblioteca de componentes.\n"
        "  Nota: o arquivo components/biblioteca/GraphView.tsx também deve ser criado."
    )

    # ── 5. Verifica renderização condicional de <GraphView> ──────────────
    # Deve haver algo como {viewMode === 'graph' && <GraphView .../>}
    has_graphview_jsx = bool(re.search(
        r"<GraphView[^>]*/>",
        source,
    ))
    assert has_graphview_jsx, (
        "RED — AC#1: <GraphView /> não está sendo renderizado em BibliotecaRoom.tsx.\n"
        "  Esperado: {viewMode === 'graph' && <GraphView .../>} dentro do painel principal,\n"
        "  ao lado (ou substituindo) da renderização condicional de grid/list.\n"
        "  O Coder deve adicionar renderização condicional para o modo graph,\n"
        "  consistente com o padrão: {viewMode === 'grid' ? (...) : (...)}."
    )
