"""RED test for behavior B-5 — Grafo de conhecimento na Biblioteca (NAO implementado).

GOAL:
    Garantir que a BibliotecaRoom ofereca um terceiro modo de visualizacao
    "grafo" (graph) ao lado dos modos "grid" e "list" ja existentes. O modo
    grafo deve renderizar um componente DocGraph que exibe nos (documentos,
    categorias, entidades) e arestas (relacionamentos) entre eles.

BEHAVIOR:
    B-5 — Grafo de conhecimento na Biblioteca:
    A BibliotecaRoom deve ter 3 modos de visualizacao: "grid", "list" e
    "graph". Quando o modo "graph" estiver ativo, o componente DocGraph
    deve ser renderizado em vez da grade/lista.

AC (Acceptance Criteria):
    AC-5 — BibliotecaRoom com view mode "grafo" funcional exibindo
            relacionamentos entre documentos, categorias e entidades.

Estado atual (RED):
    - Linha 9:  type ViewMode = 'grid' | 'list'   →  sem 'graph'
    - Linhas 343-356: 2 botoes de toggle (⊞ grid, ≡ list)  →  sem 3o botao
    - Sem import de DocGraph em BibliotecaRoom.tsx
    - Sem renderizacao condicional de <DocGraph .../> para viewMode === 'graph'

Estado alvo (GREEN):
    - type ViewMode = 'grid' | 'list' | 'graph'
    - Toggle com 3 botoes: grid (title="Grade"), list (title="Lista"),
      graph (title="Grafo" ou "graph")
    - import DocGraph from '../../components/biblioteca/DocGraph' (ou caminho similar)
    - {viewMode === 'graph' && <DocGraph .../>} (ou ternario) renderizando
      o componente de grafo

Anti-Goals:
    1. NAO modificar codigo de producao (so testes estaticos com regex).
    2. NAO usar mocks, DB, browser testing, jsdom.
    3. NAO remover os botoes grid/list existentes (devem ser preservados).
    4. NAO relaxar o teste para passar no estado atual — TRUE RED.
    5. NAO modificar o conftest.py existente em tests/behaviors/conftest.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BIBLIOTECA_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "BibliotecaRoom.tsx"
)


# ── Source helpers ─────────────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TSX como texto puro."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_viewmode_decl(source: str) -> str | None:
    """Extrai o conteudo da declaracao `type ViewMode = ...` ate a quebra de linha.

    Retorna None se a declaracao nao for encontrada.
    """
    match = re.search(r"type\s+ViewMode\s*=", source)
    if match is None:
        return None
    start = match.start()
    line_end = source.find("\n", start)
    if line_end == -1:
        line_end = start + 200
    return source[start:line_end].strip()


def _count_viewmode_buttons(source: str) -> list[str]:
    """Coleta os modos chamados por setViewMode('...') em botoes de toggle.

    Aceita tanto `onClick={() => setViewMode('grid')}` (JSX, com chaves)
    quanto `onClick=() => setViewMode('grid')` (raro, sem chaves).
    """
    return re.findall(
        r"onClick\s*=\s*\{?\s*\(\s*\)\s*=>\s*setViewMode\s*\(\s*'([^']+)'\s*\)\s*\}?",
        source,
    )


# ── Test ───────────────────────────────────────────────────────────────────


def test_b5_ac5_grafo_conhecimento() -> None:
    """AC-5 — BibliotecaRoom expoe view mode "grafo" com DocGraph renderizado.

    Verifica tres condicoes:

    1. O type ViewMode em BibliotecaRoom.tsx inclui o literal 'graph'
       (esperado: type ViewMode = 'grid' | 'list' | 'graph').
    2. Existem 3 botoes de toggle (grid, list, graph) no painel de
       documentos da BibliotecaRoom.
    3. O componente DocGraph esta presente (importado e/ou renderizado
       condicionalmente quando viewMode === 'graph').

    Se qualquer condicao falhar no estado atual, o teste falha (RED).
    """
    source = _read_source(BIBLIOTECA_PATH)

    falhas: list[str] = []

    # ── 1. ViewMode type inclui "graph" ──────────────────────────────────
    viewmode_decl = _extract_viewmode_decl(source)
    if viewmode_decl is None:
        falhas.append(
            "  - Declaracao `type ViewMode = ...` nao encontrada em "
            "BibliotecaRoom.tsx.\n"
            "    Esperado: type ViewMode = 'grid' | 'list' | 'graph'"
        )
    else:
        has_graph_in_type = "'graph'" in viewmode_decl
        if not has_graph_in_type:
            falhas.append(
                f"  - ViewMode type NAO inclui 'graph'.\n"
                f"    Atual:   {viewmode_decl}\n"
                f"    Esperado: type ViewMode = 'grid' | 'list' | 'graph'"
            )
        else:
            # anti-goal: garantir que grid e list continuam presentes
            for kept in ("'grid'", "'list'"):
                if kept not in viewmode_decl:
                    falhas.append(
                        f"  - ViewMode type PERDEU {kept} ao adicionar 'graph'.\n"
                        f"    Atual:   {viewmode_decl}\n"
                        f"    ANTI-GOAL: 'grid' e 'list' devem ser PRESERVADOS."
                    )

    # ── 2. Existem 3 botoes de toggle (grid, list, graph) ───────────────
    toggle_buttons = _count_viewmode_buttons(source)
    distinct_modes = set(toggle_buttons)
    required_modes = {"grid", "list", "graph"}
    missing_modes = required_modes - distinct_modes

    if missing_modes:
        detalhes_btn = (
            ", ".join(toggle_buttons) if toggle_buttons else "(nenhum botao encontrado)"
        )
        falhas.append(
            f"  - View toggle NAO tem botoes para os 3 modos exigidos.\n"
            f"    Botoes encontrados (setViewMode): {detalhes_btn}\n"
            f"    Faltando: {sorted(missing_modes)}\n"
            f"    Esperado: 3 botoes chamando setViewMode('grid'), "
            f"setViewMode('list') e setViewMode('graph').\n"
            f"    O terceiro botao (graph) deve ter title='Grafo' "
            f"ou title='graph'."
        )

    # ── 3. DocGraph presente (import e/ou renderizacao) ──────────────────
    has_docgraph = "DocGraph" in source
    if not has_docgraph:
        falhas.append(
            "  - Componente DocGraph NAO encontrado em BibliotecaRoom.tsx.\n"
            "    Esperado: `import DocGraph from "
            "'../../components/biblioteca/DocGraph'`\n"
            "    e renderizacao condicional `{viewMode === 'graph' && "
            "<DocGraph .../>}` (ou ternario) para o modo grafo."
        )
    else:
        # Se existe o identificador, verificar que ha renderizacao condicional
        # vinculada ao viewMode === 'graph'
        if not re.search(
            r"viewMode\s*===\s*['\"]graph['\"]", source
        ) and not re.search(
            r"viewMode\s*==\s*['\"]graph['\"]", source
        ):
            falhas.append(
                "  - BibliotecaRoom.tsx menciona 'DocGraph' mas NAO ha "
                "renderizacao condicional `viewMode === 'graph'`.\n"
                "    Esperado: bloco JSX "
                "`{viewMode === 'graph' && <DocGraph .../>}` "
                "ou ternario equivalente, ao lado da renderizacao grid/list."
            )

    # ── Reporta falhas (TRUE RED) ────────────────────────────────────────
    if falhas:
        msg = (
            "RED — AC-5: BibliotecaRoom NAO expoe view mode 'grafo' "
            "com DocGraph. Foram encontradas as seguintes deficiencias:\n\n"
            + "\n".join(falhas)
            + "\n\n"
            "Esperado (GREEN):\n"
            "  1. type ViewMode = 'grid' | 'list' | 'graph' "
            "(linha ~9 de BibliotecaRoom.tsx)\n"
            "  2. View toggle com 3 botoes: "
            "grid (title='Grade'), list (title='Lista'), "
            "graph (title='Grafo')\n"
            "  3. import DocGraph from "
            "'../../components/biblioteca/DocGraph'\n"
            "  4. Renderizacao condicional "
            "`{viewMode === 'graph' && <DocGraph .../>}` no painel "
            "principal de documentos.\n\n"
            "O Coder deve adicionar o terceiro modo de visualizacao 'graph' "
            "a BibliotecaRoom, criando o componente DocGraph "
            "(em apps/blu_v3/src/components/biblioteca/DocGraph.tsx) "
            "que renderize nos e arestas entre documentos, categorias "
            "e entidades, sem remover os botoes grid/list existentes."
        )
        pytest.fail(msg)
