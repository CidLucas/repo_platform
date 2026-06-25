"""RED test for behavior B-2 — Navegacao em Arvore por Categoria (BibliotecaRoom).

GOAL:
    Substituir o filtro flat <select> de categorias (linhas 377-386 de
    BibliotecaRoom.tsx) por uma arvore hierarquica de categorias com
    contagem de documentos por no.

BEHAVIOR:
    B-2 — Arvore de categorias renderiza nos com contagens.

    After the fix (GREEN):
    - BibliotecaRoom.tsx expoe uma arvore de categorias (componente/funcao
      com semantica de tree — recursao, children, ou hierarquia pai/filho).
    - Cada no da arvore exibe, alem do label da categoria, a contagem de
      documentos daquela categoria.
    - O filtro flat <select> com <option> para cada categoria NAO e a
      implementacao alvo.

AC (Acceptance Criteria):
    AC-2 — Arvore renderiza categorias com contagens.

Estado atual (antes da correcao):
    BibliotecaRoom.tsx usa um <select> flat (linhas 377-386) com
    <option> para cada categoria de KB_CATEGORIES, sem arvore
    hierarquica e sem contagens por categoria exibidas na UI.
    O teste deve falhar (RED) ate que a arvore seja implementada.
"""

import pathlib
import re

import pytest


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_BIBLIOTECA_ROOM_PATH = _APP_SRC / "pages" / "app" / "BibliotecaRoom.tsx"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB2ArvoreCategorias:
    """B-2: Arvore de categorias com contagens no BibliotecaRoom."""

    # -----------------------------------------------------------------
    # AC-2 — Arvore renderiza categorias com contagens.
    #   RED no codigo atual: existe um <select> flat (linhas 377-386) e
    #   nenhum componente/funcao de arvore recursiva, e nenhuma
    #   exibicao de contagem por categoria na UI.
    # -----------------------------------------------------------------

    def test_arvore_renderiza_categorias_com_contagens(self):
        """AC-2: a arvore de categorias deve renderizar nos com contagens
        (label da categoria + numero de documentos). Falha (RED) enquanto
        BibliotecaRoom.tsx usar apenas o <select> flat das linhas 377-386.
        """
        source = _read(_BIBLIOTECA_ROOM_PATH)

        # 1) Deve existir um componente/funcao com semantica de arvore.
        #    Procuramos identificadores comuns para nos de arvore
        #    (CategoryTree, CategoryNode, TreeNode, CategoryItem) OU
        #    declaracoes de funcao recursivas (no que se referencia).
        tree_identifiers = [
            "CategoryTree",
            "CategoryNode",
            "TreeNode",
            "CategoryItem",
            "CategoryBranch",
            "CategoryLeaf",
        ]
        has_tree_component = any(name in source for name in tree_identifiers)

        # Como fallback, aceitamos tambem a presenca de uma funcao
        # recursiva: o proprio nome aparece tanto na definicao quanto
        # em uma chamada dentro do mesmo arquivo.
        recursive_match = re.findall(
            r"(?:function|const)\s+([A-Z][A-Za-z0-9]*)\s*[\(=]",
            source,
        )
        defined_names = set(recursive_match)
        call_sites = re.findall(
            r"<\s*([A-Z][A-Za-z0-9]*)\b", source
        )
        recursive_names = {
            name for name in call_sites
            if name in defined_names and name not in {"div", "span", "button"}
        }
        has_recursive_render = bool(recursive_names)

        if not (has_tree_component or has_recursive_render):
            pytest.fail(
                "AC-2 violado: nao foi encontrado nenhum componente/funcao "
                "com semantica de arvore em BibliotecaRoom.tsx. Esperado: "
                "uma funcao recursiva ou um componente nomeado (ex.: "
                "CategoryTree, CategoryNode, TreeNode) que renderize a "
                "hierarquia de categorias. O filtro flat <select> das "
                "linhas 377-386 nao satisfaz o criterio de arvore."
            )

        # 2) Deve haver uma estrutura hierarquica (parent/children).
        #    Procuramos palavras-chave de hierarquia: children, subcategorias,
        #    parent_id, subcategories, etc.
        hierarchy_patterns = [
            r"\bchildren\b",
            r"\bsubcategories?\b",
            r"\bparent_id\b",
            r"\bparentId\b",
            r"\.children\s*\.map",
            r"\.subcategories\s*\.map",
            r"category\.children",
            r"cat\.children",
        ]
        has_hierarchy = any(
            re.search(p, source) is not None for p in hierarchy_patterns
        )

        if not has_hierarchy:
            pytest.fail(
                "AC-2 violado: nao foi encontrada evidencia de hierarquia "
                "(children / subcategories / parent_id) em BibliotecaRoom.tsx. "
                "A arvore precisa expressar a relacao pai/filho entre "
                "categorias (ex.: campo `children` em cada no, ou "
                "lista de subcategorias renderizada recursivamente)."
            )

        # 3) Cada no da arvore deve exibir a contagem de documentos.
        #    Procuramos: uma variavel/constante `catCounts` (ja existe
        #    hoje no fonte) SENDO USADA dentro do bloco da arvore,
        #    ou qualquer expressao que renderize numero entre parenteses
        #    ou sufixo (ex.: "(N)", " N docs", "{count} documentos").
        cat_counts_used_in_tree = bool(
            re.search(
                r"catCounts\s*\[\s*",
                source,
            )
        ) or bool(
            re.search(
                r"catCounts\s*\.\s*\[",
                source,
            )
        )

        count_in_jsx_patterns = [
            r"catCounts\[",
            r"counts\[",
            r"\{\s*count\s*\}",
            r"\{\s*counts\b",
            r"\(\s*\d+\s*\)",
            r"\bdocs\b",
            r"\bdocumentos?\b",
        ]
        # Filtrar matches que sejam apenas de comentarios ou textos
        # descritivos (heuristica: pelo menos um pattern que nao seja
        # puramente '(N)' deve estar presente no JSX em proximidade
        # com a arvore).
        has_count_render = any(
            re.search(p, source) is not None
            for p in count_in_jsx_patterns
        )

        if not (cat_counts_used_in_tree and has_count_render):
            missing = []
            if not cat_counts_used_in_tree:
                missing.append(
                    "uso de `catCounts[...]` no JSX (a contagem por "
                    "categoria calculada em useMemo precisa ser lida "
                    "dentro do no da arvore)"
                )
            if not has_count_render:
                missing.append(
                    "renderizacao explicita da contagem no no da arvore "
                    "(ex.: `{catCounts[cat.value]}` ao lado do label)"
                )
            pytest.fail(
                "AC-2 violado: a arvore ainda nao exibe contagens por "
                "categoria em BibliotecaRoom.tsx. Faltando: "
                + "; ".join(missing)
                + ". A contagem precisa aparecer visualmente ao lado "
                "de cada no da arvore (ex.: 'Dados de Negocio (12)')."
            )

        # 4) O filtro flat <select> com KB_CATEGORIES no escopo do filtro
        #    NAO deve ser a implementacao final. Aceitamos que a
        #    implementacao mantenha o <select> do header (linha 318)
        #    para upload, mas o filtro de listagem (linhas 377-386)
        #    deve ter sido substituido pela arvore.
        # Heuristica: o filtro de listagem (categoria) NAO deve ser
        # um <select> com value={categoryFilter} dentro do bloco de
        # filtros. Como o fonte mistura os dois <select> (upload e
        # filtro), exigimos que exista um bloco claramente distinto
        # (aside/sidebar) onde a arvore e renderizada.
        sidebar_or_tree_block = bool(
            re.search(
                r"className\s*=\s*[\"']\s*(?:sidebar|nav-tree|"
                r"category-tree|cat-tree|tree|kb-tree|kb-sidebar)"
                r"\s*[\"']",
                source,
                re.IGNORECASE,
            )
        ) or bool(
            re.search(
                r"<(?:aside|nav)\b[^>]*className\s*=\s*[\"'][^\"']*"
                r"(?:tree|sidebar|cat)",
                source,
                re.IGNORECASE,
            )
        )

        if not sidebar_or_tree_block:
            pytest.fail(
                "AC-2 violado: nao foi identificado um bloco dedicado "
                "(sidebar/nav/aside) para a arvore de categorias em "
                "BibliotecaRoom.tsx. A arvore deve viver em um "
                "container proprio (ex.: <aside className=\"kb-tree\"> "
                "ou <div className=\"sidebar\">), separada do filtro "
                "<select> flat das linhas 377-386."
            )
