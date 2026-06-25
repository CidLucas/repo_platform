"""RED test - B-2 (BKL-035): Arvore de categorias exibe categorias com contagem.

GOAL:
    Disponibilizar uma sidebar/arvore de categorias na BibliotecaRoom
    que exiba cada categoria com a contagem de documentos associados,
    organizada em estrutura hierarquica (pais com filhos) e com nos
    que podem ser expandidos/recolhidos.

BEHAVIOR:
    "B-2 (BKL-035) - Behavior 1: a arvore exibe categorias com
    contagem de documentos."

    A arvore de categorias deve:
        1. Importar e renderizar um componente proprio de arvore
           (``CategoryTree``) como sidebar/coluna em
           ``BibliotecaRoom``.
        2. Cada no da arvore exibe o nome da categoria concatenado
           com a contagem de documentos associados, ex.:
           ``Dados de Negocio (5)``.
        3. A arvore tem estrutura hierarquica, com nos pais contendo
           nos filhos (nao apenas uma lista flat de categorias).
        4. O estado de expansao dos nos eh controlado por
           ``useState`` (ex.: ``expanded``, ``expandedIds``).
        5. Existe uma funcao ``toggle`` (ou handler equivalente)
           que adiciona/remove o id do no do estado de expansao.

    Estado atual (BEFORE - RED):
        - O codigo em ``BibliotecaRoom.tsx`` define
          ``KB_CATEGORIES`` como uma lista flat de 4 categorias sem
          campos ``children``/``parent``/``subcategories``.
        - O painel "Por categoria" (``CollapsiblePanel
          id="kb-categories"``) mostra apenas estatisticas flat com
          barras de progresso, NAO uma arvore interativa.
        - ``categoryFilter`` eh controlado por um ``<select>``
          simples, NAO por clique em no de arvore.
        - Nao ha import de ``CategoryTree``.
        - Nao ha ``useState<Set<string>>``/``useState<Record<string,
          boolean>>`` para ``expanded``/``expandedIds``.
        - Nao ha funcao ``toggle`` que altere o estado de expansao.

    Estado esperado (AFTER - GREEN):
        - ``import CategoryTree from '...components/shared/
          CategoryTree'`` no topo do arquivo.
        - ``<CategoryTree ... />`` renderizado em uma sidebar/coluna
          lateral.
        - Cada no da arvore exibe label + contagem, ex.:
          ``{node.label} ({node.count})`` ou template literal
          equivalente.
        - Tipo/estrutura de categoria contem campo ``children`` (ou
          ``subcategories``/``parent``) que modela a hierarquia.
        - ``const [expanded, setExpanded] = useState<Set<string>>
          (new Set())`` (ou ``Record<string, boolean>``) presente
          no corpo de ``BibliotecaRoom``.
        - Funcao ``toggle(id)`` que faz ``setExpanded(prev => ...)``
          para expandir/recolher nos ao clicar.

AC (Acceptance Criteria):
    AC#1 - ``CategoryTree`` importado em ``BibliotecaRoom.tsx``.
    AC#2 - ``<CategoryTree />`` renderizado como sidebar/coluna.
    AC#3 - Nos da arvore exibem label + contagem (padrao
        ``Nome (N)`` ou similar com contagem adjacente ao nome).
    AC#4 - Arvore tem estrutura hierarquica (campo ``children``,
        ``subcategories`` ou ``parent`` em nos/categorias).
    AC#5 - ``useState`` para estado de expansao (``expanded``,
        ``expandedIds`` ou similar).
    AC#6 - Funcao ``toggle``/handler que atualiza o estado de
        expansao ao clicar em um no.

Estado atual: RED - todas as ACs violadas. Cada AC eh verificada por
regex sobre o codigo-fonte lido como texto puro; o teste agrega as
deficiencias e dispara ``pytest.fail`` com mensagem consolidada
em pt-BR listando o que falta para o estado GREEN.

Anti-Goals:
    1. NAO modificar codigo de producao
       (``BibliotecaRoom.tsx``, ``knowledgeBaseService.ts``, etc.).
    2. NAO executar/parsear TypeScript - somente inspecao textual
       com expressoes regulares sobre o source lido como string.
    3. NAO usar mocks, Supabase, browser testing ou jsdom.
    4. NAO quebrar funcionalidade existente (grid/list, busca,
       status, upload, etc.).
    5. NAO relaxar o teste para que ele passe no estado atual - o
       teste precisa ser TRUE RED agora.
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

BIBLIOTECA_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)

KB_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest - este teste e
    pura inspecao textual de ``BibliotecaRoom.tsx`` e
    ``knowledgeBaseService.ts``, sem teardown no Supabase, sem rede,
    sem import/execucao de TypeScript/JSX.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-2 (BKL-035) exige que o arquivo exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) - cobre todos os ACs de B-2 (BKL-035) ──────


def test_b2_arvore_categorias_com_contagem_red() -> None:
    """B-2 (BKL-035) Behavior 1 - RED.  Falha enquanto a arvore de
    categorias com contagem nao estiver implementada em
    ``BibliotecaRoom.tsx`` e/ou ``knowledgeBaseService.ts``.

    Esta funcao agrega a verificacao de TODOS os ACs em uma unica
    assercao para tornar o diagnostico explicito: o teste coleta
    todas as deficiencias e dispara ``pytest.fail`` com uma mensagem
    consolidada em pt-BR, listando o que falta para o estado GREEN.

    ACs verificadas:
        AC#1 - ``CategoryTree`` importado em
            ``BibliotecaRoom.tsx``.
        AC#2 - ``<CategoryTree />`` renderizado como
            sidebar/coluna lateral.
        AC#3 - Nos da arvore exibem label + contagem (padrao
            ``Nome (N)`` ou similar com contagem adjacente).
        AC#4 - Arvore tem estrutura hierarquica (campo
            ``children``/``subcategories``/``parent`` em nos
            ou categorias).
        AC#5 - ``useState`` para estado de expansao.
        AC#6 - Funcao ``toggle``/handler para expandir/recolher
            nos.
    """
    source = _read_source(BIBLIOTECA_PATH)
    kb_source = _read_source(KB_SERVICE_PATH)

    # Lista de deficiencias encontradas - preenchida incrementalmente.
    problemas: list[str] = []

    # ── AC#1 - CategoryTree importado em BibliotecaRoom.tsx ────────
    #     Evidencias esperadas:
    #       - declaracao `import CategoryTree from '...'` no source
    #       - caminho plausivel (components/shared/CategoryTree ou
    #         similar)
    import_category_tree = bool(
        re.search(
            r"""^\s*import\s+CategoryTree\b""",
            source,
            re.MULTILINE,
        )
    )
    import_path_plausible = bool(
        re.search(
            r"""import\s+CategoryTree\s+from\s+['"][^'"]*CategoryTree['"]""",
            source,
        )
    )

    if not import_category_tree:
        problemas.append(
            "AC#1 - `CategoryTree` NAO esta importado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            "    GREEN deve adicionar (no bloco de imports):\n"
            "      import CategoryTree from "
            "'../../components/shared/CategoryTree'\n"
            "    (ou caminho equivalente, desde que o componente "
            "seja reutilizavel e receba props como `nodes`, "
            "`expandedIds`, `onToggle` e `onSelect`)."
        )

    if import_category_tree and not import_path_plausible:
        problemas.append(
            "AC#1 - `import CategoryTree` foi encontrado, mas o "
            "caminho de origem nao parece apontar para um "
            "componente proprio (esperado algo como "
            "`.../components/shared/CategoryTree`).\n"
            "    GREEN deve apontar o import para o modulo do "
            "componente `CategoryTree` que renderiza a arvore."
        )

    # ── AC#2 - <CategoryTree /> renderizado como sidebar/coluna ────
    #     Evidencias esperadas:
    #       - uso de <CategoryTree ... /> no JSX
    #       - presenca de um wrapper de sidebar/coluna lateral
    #         (className/estilo contendo "sidebar", "tree",
    #         "kb-tree", "kb-sidebar", "lcol", etc.) envolvendo o
    #         CategoryTree
    render_category_tree = bool(
        re.search(
            r"<\s*CategoryTree\b",
            source,
        )
    )

    # Wrapper de sidebar/coluna. Aceita:
    #   - className/style com tokens 'sidebar', 'tree', 'kb-tree',
    #     'kb-sidebar', 'tree-col', 'tree-panel', 'lcol'
    #   - string literal identica ('sidebar', 'kb-tree' etc.)
    #   - wrapper com flex + position + width que indique coluna
    #     lateral, desde que usado em conjunto com CategoryTree
    has_sidebar_wrapper = bool(
        re.search(
            r"""(?:className|style)\s*=\s*\{?\{?[^}]*?(?:sidebar|tree[_-]?sidebar|kb[_-]?sidebar|kb[_-]?tree|tree[_-]?col|tree[_-]?panel|lcol|left[_-]?col)""",
            source,
            re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"""['"](?:sidebar|tree[_-]?sidebar|kb[_-]?sidebar|kb[_-]?tree|tree[_-]?col|tree[_-]?panel|lcol|left[_-]?col)['"]""",
            source,
            re.IGNORECASE,
        )
    )

    if not render_category_tree:
        problemas.append(
            "AC#2 - `<CategoryTree />` NAO esta sendo renderizado "
            "no JSX de `BibliotecaRoom.tsx`.\n"
            "    GREEN deve posicionar o componente dentro de uma "
            "coluna/sidebar lateral (tipicamente gridColumn 1 / "
            "flex aside) ao lado do painel principal de documentos."
        )

    if render_category_tree and not has_sidebar_wrapper:
        problemas.append(
            "AC#2 - `<CategoryTree />` foi encontrado, mas nao ha "
            "um wrapper de sidebar/coluna lateral dedicado a ele.\n"
            "    GREEN deve envolver `<CategoryTree />` em um "
            "container com className ou estilo que identifique "
            "uma coluna lateral (ex.: `kb-tree-sidebar`, "
            "`biblioteca-sidebar`, `lcol`, etc.)."
        )

    # ── AC#3 - Nos exibem label + contagem ─────────────────────────
    #     Evidencias esperadas:
    #       - padrao JSX `${...} (${...})` ou `{...} ({...})` ou
    #         template literal com label e count adjacentes
    #       - referencia a um campo `.count` ou `.docCount` ou
    #         `.documentCount` em contexto de no (`node.`, `n.`,
    #         `cat.`, `category.`)
    #       - uso de `categoryTree`/`treeNodes`/`treeItems`/
    #         `tree` mapeado com `count` exibido
    #
    #     Padroes aceitos:
    #       a) {node.label} ({node.count})
    #       b) `{label} (${count})`
    #       c) {cat.label} ({count}) em contexto de arvore
    #       d) `${node.label} (${node.count})`
    label_count_patterns = [
        # {x.label} ({x.count}) ou similar
        r"\{[a-zA-Z_$.]+\.label\}\s*\(\s*\{[a-zA-Z_$.]+\.count\}\s*\)",
        # `x.label` (${x.count}) - template literal
        r"\$\{[a-zA-Z_$.]+\.label\}\s*\(\s*\$\{[a-zA-Z_$.]+\.count\}\s*\)",
        # `x.label} (${count})` - mixed JSX+template
        r"\{[a-zA-Z_$.]+\.label\}\s*\(\s*\$\{[a-zA-Z_$.]+\.count\}\s*\)",
        # `${label} (${count})` - template puro
        r"\$\{[a-zA-Z_$.]+\.label\}\s*\(\s*\$\{count\}\s*\)",
        # {label} ({count}) sem prefixo
        r"\{[a-zA-Z_$.]+\.label\}\s*\(\s*\{count\}\s*\)",
        # `${node.label} (${node.count})` em forma mais ampla
        r"`\$\{[^}]+\.label\}\s*\(\$\{[^}]+\.count\}\)`",
        # Funcao/componente que recebe count em prop: nodeCount, docCount
        r"(?:nodeCount|docCount|documentCount)\s*[=:]\s*\{",
        # No iterando tree: {tree.map(n => (... {n.count} ...))} ou similar
        r"(?:nodes|tree|treeNodes|treeItems|categoryTree)"
        r"(?:\.map|\.filter)",
    ]
    has_label_count = any(
        re.search(p, source) for p in label_count_patterns
    )

    # Evidencia auxiliar: CategoryTree recebendo `count` em props
    ct_count_prop = bool(
        re.search(
            r"<\s*CategoryTree\b[^>]*?(?:docCount|nodeCount|"
            r"documentCount|withCount|showCount)\s*=",
            source,
            re.DOTALL,
        )
    )

    # Evidencia auxiliar: `count` referenciado dentro do source
    # relativo a no/categoria (nao a stats globais como `totalDocs`)
    count_in_tree_context = bool(
        re.search(
            r"(?:node|n|cat|category|item|entry)\.count\b",
            source,
        )
    ) or bool(
        re.search(
            r"\bcount:\s*(?:node|n|cat|category|item)\.count\b",
            source,
        )
    )

    if not (has_label_count or ct_count_prop or count_in_tree_context):
        problemas.append(
            "AC#3 - Nenhum no da arvore exibe label + contagem "
            "adjacente (padrao `Nome (N)`) em "
            "`BibliotecaRoom.tsx`.\n"
            "    GREEN deve renderizar cada no da arvore com a "
            "contagem de documentos associados, ex.:\n"
            "      <span>{node.label} ({node.count})</span>\n"
            "    ou template literal:\n"
            "      `${node.label} (${node.count})`\n"
            "    O codigo atual exibe `{count}` apenas no painel "
            "estatistico flat `kb-categories` (barra de progresso), "
            "NAO em no de arvore interativo."
        )

    # ── AC#4 - Arvore tem estrutura hierarquica (pais com filhos) ──
    #     Evidencias esperadas:
    #       - tipo/interface `CategoryNode`/`TreeNode`/`CategoryTreeNode`
    #         com campo `children` (array)
    #       - ou campo `subcategories`/`subCategories`/`subcats`
    #       - ou campo `parent`/`parentId`/`parent_id`
    #       - KB_CATEGORIES ou tipo KBCategory enriquecido com
    #         algum dos campos acima
    #       - construcao de nos com `children: [...]` no codigo
    #         (ex.: `const tree = KB_CATEGORIES.map(c => ({ ...
    #         children: c.children }))`)
    has_children_field_type = bool(
        re.search(
            r"(?:CategoryNode|TreeNode|CategoryTreeNode|TreeItem|"
            r"KBCategory\s*=)",
            source,
        )
        and re.search(
            r"(?:children|subcategories|subCategories|subcats|"
            r"parentId|parent_id|parent)\s*[\?:]",
            source,
        )
    ) or bool(
        re.search(
            r"(?:children|subcategories|subCategories|subcats)"
            r"\s*:\s*[\w.<>\[\]| &]+",
            source,
        )
    )

    # KB_CATEGORIES enriquecido com children/subcategories
    kb_has_hierarchical = bool(
        re.search(
            r"(?:children|subcategories|subCategories|subcats)"
            r"\s*:\s*\[",
            kb_source,
        )
    ) or bool(
        re.search(
            r"(?:parent|parentId|parent_id)"
            r"\s*:\s*['\"]",
            kb_source,
        )
    )

    # Construcao inline de nos com children
    has_inline_tree_build = bool(
        re.search(
            r"(?:nodes|tree|treeNodes|treeItems|categoryTree)"
            r"\s*[:=]",
            source,
        )
        and re.search(
            r"(?:children|subcategories|subCategories)\s*:",
            source,
        )
    )

    has_hierarchical_structure = (
        has_children_field_type
        or kb_has_hierarchical
        or has_inline_tree_build
    )

    if not has_hierarchical_structure:
        problemas.append(
            "AC#4 - Nao foi encontrada estrutura hierarquica "
            "(campo `children`/`subcategories`/`parent`) em "
            "`BibliotecaRoom.tsx` ou "
            "`knowledgeBaseService.ts`.\n"
            "    GREEN deve introduzir uma estrutura de no com "
            "filhos, ex.:\n"
            "      type CategoryNode = {\n"
            "        id: string\n"
            "        label: string\n"
            "        count: number\n"
            "        children?: CategoryNode[]\n"
            "      }\n"
            "    E popular essa estrutura (em `KB_CATEGORIES` "
            "ou via build inline) para que a arvore tenha pais "
            "com filhos - NAO apenas uma lista flat como a "
            "atual."
        )

    # ── AC#5 - useState para estado de expansao ────────────────────
    #     Evidencias esperadas:
    #       - `useState<Set<string>>(new Set())` ou
    #         `useState<Record<string, boolean>>({})` com variavel
    #         chamada `expanded`/`expandedIds`/`expandedNodes`
    has_expanded_state_strict = bool(
        re.search(
            r"useState\s*<\s*(?:Set\s*<\s*string\s*>|Record\s*<"
            r"\s*string\s*,\s*boolean\s*>)\s*>\s*\(\s*(?:new\s+"
            r"Set\s*\(\s*\)|\{\s*\})",
            source,
        )
    )

    has_expanded_state_loose = bool(
        re.search(
            r"useState\s*(?:<[^>]+>)?\s*\(\s*(?:new\s+Set\s*"
            r"\(\s*\)|\{\s*\})\s*\)",
            source,
        )
        and re.search(
            r"\b(?:expanded|expandedIds|expandedNodes|"
            r"treeExpanded|categoryExpanded|kbExpanded)\b",
            source,
        )
    )

    has_expanded_state = has_expanded_state_strict or has_expanded_state_loose

    if not has_expanded_state:
        problemas.append(
            "AC#5 - Nao foi encontrado um `useState` para "
            "tracking dos nos expandidos da arvore em "
            "`BibliotecaRoom.tsx`.\n"
            "    GREEN deve introduzir (no corpo de "
            "`BibliotecaRoom`):\n"
            "      const [expanded, setExpanded] = "
            "useState<Set<string>>(new Set())\n"
            "    (ou `Record<string, boolean>`, `Map<string, "
            "boolean>`, ou tipo equivalente) com variavel "
            "chamada `expanded`/`expandedIds`/`expandedNodes`."
        )

    # ── AC#6 - Funcao toggle/handler para expandir/recolher nos ───
    #     Evidencias esperadas:
    #       - declaracao de funcao `toggle(...)` ou
    #         `toggleNode(...)` ou `toggleExpand(...)` no source
    #       - corpo que invoca setExpanded/setExpandedIds
    #       - uso do `toggle` passado como prop para
    #         `<CategoryTree />` ou usado em onClick inline
    has_toggle_function_decl = bool(
        re.search(
            r"(?:function|const)\s+toggle(?:Expand|Node|"
            r"Expanded)?\s*(?:<[^>]+>)?\s*\(",
            source,
        )
    ) or bool(
        re.search(
            r"(?:const|let|var)\s+toggle\s*=",
            source,
        )
    )

    has_setter_invocation = bool(
        re.search(
            r"(?:setExpanded|setExpandedIds|setExpandedNodes|"
            r"setTreeExpanded|setCategoryExpanded)\s*\(",
            source,
        )
    )

    toggle_used_in_tree = bool(
        re.search(
            r"<\s*CategoryTree\b[^>]*?(?:onToggle|toggle)\s*=",
            source,
            re.DOTALL,
        )
    ) or bool(
        re.search(
            r"onClick\s*=\s*\{[^}]*?toggle\s*\(",
            source,
        )
    )

    # Se o handler se chama apenas `toggle`, exige o setter
    has_toggle = (
        has_toggle_function_decl
        and (has_setter_invocation or toggle_used_in_tree)
    )

    if not has_toggle:
        if not has_toggle_function_decl:
            problemas.append(
                "AC#6 - Nao foi encontrada uma funcao `toggle` "
                "(ou `toggleExpand`/`toggleNode`/`toggleExpanded`) "
                "no source de `BibliotecaRoom.tsx`.\n"
                "    GREEN deve declarar uma funcao de toggle "
                "que receba o `id` do no e atualize o estado de "
                "expansao, ex.:\n"
                "      const toggle = (id: string) =>\n"
                "        setExpanded(prev => {\n"
                "          const next = new Set(prev)\n"
                "          next.has(id) ? next.delete(id) : "
                "next.add(id)\n"
                "          return next\n"
                "        })"
            )
        if not (has_setter_invocation or toggle_used_in_tree):
            problemas.append(
                "AC#6 - A funcao de toggle existe mas NAO atualiza "
                "o estado de expansao via `setExpanded`/"
                "`setExpandedIds` (nem e passada como prop "
                "`onToggle` para `<CategoryTree />` ou usada em "
                "onClick inline).\n"
                "    GREEN deve conectar o handler ao estado de "
                "expansao e ao componente de arvore (via prop ou "
                "onClick)."
            )

    # ── Agrega o diagnostico e falha ──────────────────────────────
    if problemas:
        cabecalho = (
            "B-2 (BKL-035) Behavior 1 - RED.  Arvore de categorias "
            "com contagem NAO implementada em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx` "
            "(e/ou `apps/blu_v3/src/services/knowledgeBaseService.ts`).\n\n"
            "Estado atual (BEFORE):\n"
            "  - `KB_CATEGORIES` eh uma lista flat de 4 itens, sem "
            "campos `children`/`parent`/`subcategories`.\n"
            "  - O painel `kb-categories` mostra estatisticas flat "
            "com barras de progresso, NAO uma arvore interativa.\n"
            "  - `categoryFilter` eh controlado por um `<select>` "
            "simples, NAO por clique em no de arvore.\n"
            "  - Nenhum import de `CategoryTree`.\n"
            "  - Nenhum `useState<Set<string>>`/`useState<Record<"
            "string, boolean>>` para `expanded`/`expandedIds`.\n"
            "  - Nenhuma funcao `toggle` para expandir/recolher nos.\n\n"
            "Estado esperado (AFTER - GREEN):\n"
            "  - `import CategoryTree from '../../components/shared/"
            "CategoryTree'` (ou equivalente).\n"
            "  - `<CategoryTree />` renderizado em uma "
            "sidebar/coluna lateral.\n"
            "  - Cada no exibe label + contagem, ex.: "
            "`{node.label} ({node.count})` ou `Dados de Negocio "
            "(5)`.\n"
            "  - Estrutura hierarquica com campo `children` (ou "
            "`subcategories`/`parent`) em nos/categorias.\n"
            "  - `useState<Set<string>>` para tracking dos nos "
            "expandidos.\n"
            "  - Funcao `toggle(id)` que adiciona/remove o id do "
            "Set ao clicar no chevron do no.\n\n"
            "Deficiencias encontradas:\n"
        )
        bullets = "\n\n".join(
            f"  - {p}" for p in problemas
        )
        pytest.fail(cabecalho + bullets + "\n")
