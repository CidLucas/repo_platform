"""RED test — B-3 (BKL-035): Navegacao em arvore por categoria.

GOAL:
    Disponibilizar uma sidebar de arvore de categorias na BibliotecaRoom
    que permita ao usuario navegar hierarquicamente pelos documentos da
    Knowledge Base, com nos expansivos/recolheis, breadcrumb do caminho
    percorrido e tratamento de documentos sem categoria.

BEHAVIOR:
    "B-3 (BKL-035) — Navegacao em arvore por categoria."

    A arvore de categorias deve permitir:
        1. Renderizar uma sidebar esquerda com a arvore de categorias
           (componente CategoryTree).
        2. Nos da arvore que expandem/recolhem ao clicar (useState para
           controlar o estado de expansao).
        3. Clicar em um no da arvore atualiza o filtro de categoria
           (setCategoryFilter).
        4. Breadcrumb acima da area de documentos mostrando o caminho
           hierarquico percorrido, ex.: "Notas 2025 > Fornecedores >".
        5. Documentos com doc.category === null agrupados em um no
           "Sem categoria".

    Estado atual (BEFORE — RED):
        - type ViewMode = "grid" | "list"
        - type CategoryFilter = "all" | string
        - A "arvore" e um <select> simples com KB_CATEGORIES.
        - NAO existe sidebar de arvore (CategoryTree nao importado).
        - NAO existe breadcrumb.
        - Documentos sem categoria sao ignorados pelo filtro.

    Estado esperado (AFTER — GREEN):
        - import CategoryTree from '...' (componente local de arvore)
        - <CategoryTree ... /> renderizado em uma sidebar/coluna
          esquerda com estilo de arvore.
        - useState<Set<string>>(new Set()) ou useState<Record<string,
          boolean>>({}) para tracking dos nos expandidos.
        - Cada no da arvore possui onClick que invoca setCategoryFilter
          com o valor do no clicado.
        - <Breadcrumb path={...} /> ou JSX equivalente exibindo o
          caminho atual (ex.: "Notas 2025 > Fornecedores >").
        - A arvore inclui um no "Sem categoria" onde doc.category
          === null.

AC (Acceptance Criteria):
    AC#1 — CategoryTree importado e renderizado como sidebar esquerda.
    AC#2 — Nos da arvore expandem/recolhem (useState para expandido).
    AC#3 — onClick no no atualiza categoryFilter.
    AC#4 — Breadcrumb mostra caminho hierarquico.
    AC#5 — No "Sem categoria" para doc.category === null.

Estado atual: RED — todas as ACs violadas. O codigo atual usa um
<select> simples para categoryFilter e nao tem sidebar, breadcrumb,
nem no "Sem categoria". Cada teste falha com pytest.fail() e mensagem
detalhada em pt-BR.

Anti-Goals:
    1. NAO modificar codigo de producao (BibliotecaRoom.tsx).
    2. NAO executar / parsear TypeScript — so inspecao textual.
    3. NAO usar mocks, Supabase, browser testing, jsdom.
    4. NAO quebrar funcionalidade existente (grid/list, busca, status,
       upload, etc.).
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

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


# ── Override do root conftest (teste puramente estatico) ──────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao textual de ``BibliotecaRoom.tsx``, sem teardown no
    Supabase, sem rede, sem import/execucao de TypeScript/JSX.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TSX como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-3 (BKL-035) exige que "
        "apps/blu_v3/src/pages/app/BibliotecaRoom.tsx exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-3 (BKL-035) ──────────


def test_b3_navegacao_arvore_categorias_red() -> None:
    """B-3 (BKL-035) — RED.  Falha enquanto a navegacao em arvore por
    categoria nao estiver implementada em ``BibliotecaRoom.tsx``.

    Esta funcao agrega a verificacao de TODOS os ACs em uma unica
    assercao para tornar o diagnostico explicito: o teste coleta todas
    as deficiencias e dispara ``pytest.fail`` com uma mensagem
    consolidada em pt-BR, listando o que falta para o estado GREEN.

    ACs verificadas:
        AC#1 — CategoryTree importado e renderizado como sidebar.
        AC#2 — Nos expandem/recolhem (useState para expandido).
        AC#3 — onClick no no atualiza categoryFilter.
        AC#4 — Breadcrumb mostra caminho hierarquico.
        AC#5 — No "Sem categoria" para doc.category === null.
    """
    source = _read_source(BIBLIOTECA_PATH)

    # Lista de deficiencias encontradas — preenchida incrementalmente.
    problemas: list[str] = []

    # ── AC#1 — CategoryTree importado e renderizado como sidebar ──────
    #     Evidencias esperadas:
    #       - declaracao `import CategoryTree from '...'` no source
    #       - uso de <CategoryTree ... /> em algum lugar do JSX
    #       - presenca de um wrapper de sidebar (className contendo
    #         "sidebar", "tree", "kb-tree", "kb-sidebar" etc.)
    import_category_tree = bool(
        re.search(
            r"""^\s*import\s+CategoryTree\b""",
            source,
            re.MULTILINE,
        )
    )
    render_category_tree = bool(
        re.search(
            r"<\s*CategoryTree\b",
            source,
        )
    )
    has_sidebar_wrapper = bool(
        re.search(
            r"""(?:className|style)\s*=\s*\{?\{?[^}]*?(?:sidebar|tree[_-]?sidebar|kb[_-]?sidebar|kb[_-]?tree)""",
            source,
            re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"""['"](?:sidebar|tree[_-]?sidebar|kb[_-]?sidebar|kb[_-]?tree)['"]""",
            source,
            re.IGNORECASE,
        )
    )

    if not import_category_tree:
        problemas.append(
            "AC#1 — `CategoryTree` NAO esta importado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            "    GREEN deve adicionar (no bloco de imports):\n"
            "      import CategoryTree from '../../components/shared/CategoryTree'\n"
            "    (ou caminho equivalente, desde que o componente seja "
            "    reutilizavel e receba props como `selectedId`, `onSelect`, "
            "    `expandedIds`, `onToggle` e `nodes`)."
        )

    if not render_category_tree:
        problemas.append(
            "AC#1 — `<CategoryTree />` NAO esta sendo renderizado como "
            "sidebar esquerda no JSX.\n"
            "    GREEN deve posicionar a arvore em uma coluna/sidebar "
            "esquerda (tipicamente gridColumn 1 / flex aside) acima ou "
            "ao lado do painel principal de documentos."
        )

    if not has_sidebar_wrapper:
        problemas.append(
            "AC#1 — Nao foi encontrado um wrapper de sidebar/column "
            "esquerda dedicado para a arvore.\n"
            "    GREEN deve envolver `<CategoryTree />` em um container "
            "com className ou estilo que identifique uma coluna lateral "
            "(ex.: `kb-tree-sidebar`, `biblioteca-sidebar`, etc.)."
        )

    # ── AC#2 — Nos expandem/recolhem (useState para expandido) ───────
    #     Evidencias esperadas:
    #       - useState<Set<string>>(new Set()) ou
    #         useState<Record<string, boolean>>({}) com variavel
    #         chamada `expanded` / `expandedIds` / `expandedNodes`
    #       - handlers que atualizam esse estado (toggle/setExpanded)
    #       - renderizacao condicional de filhos de um no com base
    #         nesse estado
    has_expanded_state = bool(
        re.search(
            r"useState\s*<\s*(?:Set\s*<\s*string\s*>|Record\s*<\s*string\s*,\s*boolean\s*>)"
            r"\s*>\s*\(\s*(?:new\s+Set\s*\(\s*\)|\{\s*\})",
            source,
        )
    ) or bool(
        re.search(
            r"useState\s*(?:<[^>]+>)?\s*\(\s*(?:new\s+Set\s*\(\s*\)|\{\s*\})"
            r"\s*\)",
            source,
        )
        and re.search(
            r"\b(?:expanded|expandedIds|expandedNodes|treeExpanded)\b",
            source,
        )
    )

    has_toggle_handler = bool(
        re.search(
            r"(?:setExpanded|setExpandedIds|setExpandedNodes|setTreeExpanded)"
            r"\s*\(",
            source,
        )
    ) or bool(
        re.search(
            r"\btoggle(?:Expand|Node|Expanded)\s*\(",
            source,
        )
    )

    # Renderizacao condicional de filhos com base no estado expanded
    has_conditional_children = bool(
        re.search(
            r"expanded[^&|]*?(?:&&|\?)\s*[^&|]*?(?:children|childNodes|\.children)",
            source,
        )
    ) or bool(
        re.search(
            r"(?:expanded|expandedIds|expandedNodes|treeExpanded)"
            r"(?:\.has|\[[^\]]+\])",
            source,
        )
    )

    if not has_expanded_state:
        problemas.append(
            "AC#2 — Nao foi encontrado um `useState` para tracking dos "
            "nos expandidos da arvore.\n"
            "    GREEN deve introduzir (no corpo de `BibliotecaRoom`):\n"
            "      const [expanded, setExpanded] = useState<Set<string>>"
            "(new Set())\n"
            "    (ou `Record<string, boolean>`, `Map<string, boolean>`, "
            "    ou tipo equivalente) e expor uma funcao `toggle(id)` "
            "que adiciona/remove o id do estado."
        )

    if not has_toggle_handler:
        problemas.append(
            "AC#2 — Nao foi encontrado um handler que atualize o estado "
            "de expansao (ex.: `setExpanded`, `setExpandedIds`, "
            "`toggle`).\n"
            "    GREEN deve implementar a funcao de toggle e conecta-la "
            "ao `onClick` do chevron/arrow de cada no da arvore."
        )

    if not has_conditional_children:
        problemas.append(
            "AC#2 — Nao foi encontrada renderizacao condicional dos "
            "filhos de um no com base no estado de expansao.\n"
            "    GREEN deve usar o estado `expanded` (ou similar) para "
            "decidir se os filhos de um no sao renderizados — ex.:\n"
            "      {expanded.has(node.id) && node.children?.map(...)}\n"
            "    ou `expanded[node.id] && ...`."
        )

    # ── AC#3 — onClick no no atualiza categoryFilter ──────────────────
    #     Evidencias esperadas:
    #       - padrao `onClick={...} setCategoryFilter(` ou
    #         `onClick={() => setCategoryFilter(`
    #       - ou `onSelect={(id) => setCategoryFilter(id)}` no
    #         <CategoryTree />
    has_onclick_set_category_filter = bool(
        re.search(
            r"onClick\s*=\s*\{[^}]*?setCategoryFilter\s*\(",
            source,
        )
    ) or bool(
        re.search(
            r"onSelect\s*=\s*\{[^}]*?setCategoryFilter\s*\(",
            source,
        )
    ) or bool(
        re.search(
            r"onNodeClick\s*=\s*\{[^}]*?setCategoryFilter\s*\(",
            source,
        )
    )

    # Tambem aceitamos se setCategoryFilter for passada como prop para
    # o componente CategoryTree, e o componente internamente chamar
    # via onSelect/onClick — nesse caso a chamada fica dentro de
    # CategoryTree.tsx, mas a prop precisa ser passada.
    category_filter_passed_as_prop = bool(
        re.search(
            r"<\s*CategoryTree\b[^>]*?setCategoryFilter\s*=",
            source,
            re.DOTALL,
        )
    ) or bool(
        re.search(
            r"<\s*CategoryTree\b[^>]*?onSelect\s*=",
            source,
            re.DOTALL,
        )
    )

    if not (has_onclick_set_category_filter or category_filter_passed_as_prop):
        problemas.append(
            "AC#3 — `setCategoryFilter` NAO e invocado a partir de um "
            "handler de clique em no da arvore.\n"
            "    GREEN deve garantir que clicar em um no da arvore "
            "chame `setCategoryFilter(<id-do-no>)`. Padroes aceitos:\n"
            "      a) Inline em `BibliotecaRoom.tsx`:\n"
            "         <div onClick={() => setCategoryFilter(node.id)}>\n"
            "      b) Via prop passada para `<CategoryTree />`:\n"
            "         <CategoryTree onSelect={setCategoryFilter} ... />\n"
            "    O importante e que a interacao do usuario com o no da "
            "arvore atualize o filtro de categoria exibido."
        )

    # ── AC#4 — Breadcrumb mostra caminho hierarquico ─────────────────
    #     Evidencias esperadas:
    #       - importacao ou definicao de um componente Breadcrumb
    #       - uso de <Breadcrumb ... /> no JSX
    #       - classe/estilo com nome `breadcrumb`
    #       - separador " > " ou "›" ou "→" usado para concatenar o
    #         caminho (ex.: "Notas 2025 > Fornecedores >")
    has_breadcrumb_import = bool(
        re.search(
            r"""^\s*import\s+Breadcrumb\b""",
            source,
            re.MULTILINE,
        )
    )
    has_breadcrumb_render = bool(
        re.search(
            r"<\s*Breadcrumb\b",
            source,
        )
    )
    has_breadcrumb_class = bool(
        re.search(
            r"""['"](?:breadcrumb|breadcrumb[_-]?path|crumb[_-]?nav)['"]""",
            source,
            re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"""className\s*=\s*\{?\{?[^}]*?breadcrumb""",
            source,
            re.IGNORECASE,
        )
    )

    has_path_separator = bool(
        re.search(
            r"['\"]\s*>\s*['\"]",
            source,
        )
    ) or bool(
        re.search(
            r"\bjoin\s*\(\s*['\"]\s*>\s*['\"]\s*\)",
            source,
        )
    ) or bool(
        re.search(
            r"\bjoin\s*\(\s*['\"][›→]['\"]\s*\)",
            source,
        )
    )

    if not (has_breadcrumb_import or has_breadcrumb_render or has_breadcrumb_class):
        problemas.append(
            "AC#4 — Nao foi encontrado nenhum componente, importacao ou "
            "elemento JSX de Breadcrumb em `BibliotecaRoom.tsx`.\n"
            "    GREEN deve introduzir um breadcrumb (componente "
            "proprio `<Breadcrumb />`, importacao de "
            "`apps/.../components/shared/Breadcrumb`, ou bloco JSX "
            "inline) que exibe o caminho hierarquico da categoria "
            "selecionada, ex.: `Notas 2025 > Fornecedores >`."
        )

    if not has_path_separator:
        problemas.append(
            "AC#4 — Nao foi encontrado um separador de caminho "
            "(` > `, `›`, `→` ou `join('>')`) que indicaria a "
            "construcao do breadcrumb a partir de uma lista de "
            "categorias ancestrais.\n"
            "    GREEN deve montar o breadcrumb juntando os nomes das "
            "categorias do no raiz ate o no selecionado usando um "
            "desses separadores, ex.:\n"
            "      <Breadcrumb items={path} separator=' > ' />\n"
            "    ou equivalente inline."
        )

    # ── AC#5 — No "Sem categoria" para doc.category === null ─────────
    #     Evidencias esperadas:
    #       - string "Sem categoria" presente no source
    #       - associacao com a condicao `category === null` ou
    #         `!category` ou `doc.category == null` no mesmo contexto
    #         (mesmo bloco, funcao de build, etc.)
    tem_label_sem_categoria = "Sem categoria" in source

    # Procura por uma condicao que verifica category === null perto de
    # "Sem categoria" (maximo 400 chars de distancia). Como o source
    # pode estar formatado de varias formas, procuramos tanto a forma
    # `category === null` quanto `!doc.category` e `category == null`.
    has_null_category_check = bool(
        re.search(
            r"\b(?:doc|node|item)\.category\s*(?:===?|!==?)\s*null\b",
            source,
        )
    ) or bool(
        re.search(
            r"\b!?(?:doc|node|item)\.category\b",
            source,
        )
    ) or bool(
        re.search(
            r"\bcategory\s*===\s*null\b",
            source,
        )
    ) or bool(
        re.search(
            r"\bcategory\s*\?\?\s*['\"]Sem categoria['\"]",
            source,
        )
    ) or bool(
        re.search(
            r"\b(?:doc|node|item)\.category\s*\?\?\s*['\"]Sem categoria['\"]",
            source,
        )
    )

    # Caso a implementacao use o valor "sem_categoria" (ja presente em
    # catCounts no codigo atual), aceitamos isso como evidencia
    # parcial. Mas ainda exigimos o label "Sem categoria" renderizado.
    tem_valor_sem_categoria = "sem_categoria" in source

    if not tem_label_sem_categoria:
        problemas.append(
            "AC#5 — A string literal `Sem categoria` NAO aparece em "
            "`BibliotecaRoom.tsx`.\n"
            "    GREEN deve renderizar um no com label `Sem categoria` "
            "para agrupar documentos com `doc.category === null` "
            "(ou `doc.category == null`, ou `!doc.category`).\n"
            "    O codigo atual possui apenas a chave `sem_categoria` "
            "no `catCounts` (estatistica) — o que NAO satisfaz este AC, "
            "pois nao ha no de arvore nem filtro para esse bucket."
        )

    if not has_null_category_check:
        problemas.append(
            "AC#5 — Nenhuma verificacao de `category === null` (ou "
            "`!doc.category`, `category == null`, ou fallback via `??`) "
            "foi encontrada proxima ao label `Sem categoria`.\n"
            "    GREEN deve garantir que a construcao da arvore (ou a "
            "filtragem) trate explicitamente o caso em que "
            "`doc.category` e `null`, atribuindo esses documentos ao no "
            "`Sem categoria`."
        )

    # Se o codigo NAO tem o label "Sem categoria" E nao tem o valor
    # "sem_categoria" usado para o no, e o teste ainda nao falhou,
    # falhamos explicitamente.
    if not tem_label_sem_categoria and not tem_valor_sem_categoria:
        problemas.append(
            "AC#5 — Nem o label `Sem categoria` nem o valor "
            "`sem_categoria` foram encontrados no source.\n"
            "    GREEN deve introduzir um bucket/no para documentos "
            "sem categoria — escolha entre label renderizado "
            "(`Sem categoria`) e/ou chave interna (`sem_categoria`)."
        )

    # ── Agrega o diagnostico e falha ──────────────────────────────────
    if problemas:
        cabecalho = (
            "B-3 (BKL-035) — RED.  Navegacao em arvore por categoria "
            "NAO implementada em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n\n"
            "Estado atual (BEFORE):\n"
            "  - `type ViewMode = 'grid' | 'list'` (sem tipo de no de "
            "arvore).\n"
            "  - `type CategoryFilter = 'all' | string` (sem tipo de "
            "no hierarquico).\n"
            "  - Filtro de categoria e um `<select>` simples iterando "
            "sobre `KB_CATEGORIES`.\n"
            "  - Nenhuma sidebar de arvore, nenhum breadcrumb, nenhum "
            "no `Sem categoria` para `doc.category === null`.\n\n"
            "Estado esperado (AFTER — GREEN):\n"
            "  - Sidebar esquerda com `<CategoryTree />` (componente "
            "proprio em `apps/.../components/shared/CategoryTree.tsx`).\n"
            "  - `useState<Set<string>>` para controlar nos expandidos.\n"
            "  - `onClick` em cada no chama `setCategoryFilter(id)`.\n"
            "  - `<Breadcrumb />` mostra caminho "
            "`Notas 2025 > Fornecedores >`.\n"
            "  - No `Sem categoria` para `doc.category === null`.\n\n"
            "Deficiencias encontradas:\n"
        )
        bullets = "\n\n".join(
            f"  • {p}" for p in problemas
        )
        pytest.fail(cabecalho + bullets + "\n")


# ── Testes secundarios por AC (granulares, opcionalmente ativos) ─────────
# Estes testes existem para diagnostico rapido de um AC especifico.
# Caso a implementacao GREEN seja feita em PRs separados, eles dao
# feedback imediato sobre qual AC ainda falta.


def test_b3_ac1_category_tree_importado_renderizado() -> None:
    """AC#1 — granular.  Falha com mensagem focada apenas na
    importacao e renderizacao de ``CategoryTree`` como sidebar.
    """
    source = _read_source(BIBLIOTECA_PATH)

    import_ct = bool(
        re.search(r"^\s*import\s+CategoryTree\b", source, re.MULTILINE)
    )
    render_ct = bool(re.search(r"<\s*CategoryTree\b", source))

    if not (import_ct and render_ct):
        pytest.fail(
            "AC#1 (granular) — RED.  `CategoryTree` precisa ser "
            "importado e renderizado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            f"    import CategoryTree presente: {import_ct}\n"
            f"    <CategoryTree ... /> presente: {render_ct}\n"
            "    GREEN deve adicionar o import e posicionar "
            "<CategoryTree /> em uma sidebar/coluna esquerda."
        )


def test_b3_ac2_estado_expandido_useState() -> None:
    """AC#2 — granular.  Falha com mensagem focada apenas no
    ``useState`` para tracking de nos expandidos.
    """
    source = _read_source(BIBLIOTECA_PATH)

    has_state = bool(
        re.search(
            r"useState\s*(?:<[^>]+>)?\s*\(\s*(?:new\s+Set\s*\(\s*\)|\{\s*\})\s*\)",
            source,
        )
    ) and bool(
        re.search(
            r"\b(?:expanded|expandedIds|expandedNodes|treeExpanded)\b",
            source,
        )
    )

    has_toggle = bool(
        re.search(
            r"(?:setExpanded|setExpandedIds|setExpandedNodes|setTreeExpanded)"
            r"\s*\(",
            source,
        )
    ) or bool(re.search(r"\btoggle(?:Expand|Node|Expanded)\s*\(", source))

    if not (has_state and has_toggle):
        pytest.fail(
            "AC#2 (granular) — RED.  Estado de expansao dos nos da "
            "arvore nao encontrado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            f"    useState para nos expandidos: {has_state}\n"
            f"    handler de toggle presente:  {has_toggle}\n"
            "    GREEN deve introduzir:\n"
            "      const [expanded, setExpanded] = useState<Set<string>>"
            "(new Set())\n"
            "    e uma funcao `toggle(id)` que adiciona/remove o id do "
            "Set ao clicar no chevron/arrow de um no."
        )


def test_b3_ac3_onclick_atualiza_category_filter() -> None:
    """AC#3 — granular.  Falha com mensagem focada apenas na
    ligacao entre clique no no da arvore e ``setCategoryFilter``.
    """
    source = _read_source(BIBLIOTECA_PATH)

    padrao_inline = bool(
        re.search(
            r"onClick\s*=\s*\{[^}]*?setCategoryFilter\s*\(",
            source,
        )
    )
    padrao_prop = bool(
        re.search(
            r"<\s*CategoryTree\b[^>]*?(?:setCategoryFilter|onSelect|onNodeClick)\s*=",
            source,
            re.DOTALL,
        )
    )

    if not (padrao_inline or padrao_prop):
        pytest.fail(
            "AC#3 (granular) — RED.  Nenhum `onClick` (ou prop) em "
            "no da arvore chama `setCategoryFilter` em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            "    GREEN deve garantir que o no de arvore, ao ser "
            "clicado, invoque `setCategoryFilter(idDoNo)` — seja "
            "inline, seja via prop passada para `<CategoryTree />`."
        )


def test_b3_ac4_breadcrumb_caminho_hierarquico() -> None:
    """AC#4 — granular.  Falha com mensagem focada apenas no
    breadcrumb de caminho hierarquico.
    """
    source = _read_source(BIBLIOTECA_PATH)

    tem_breadcrumb = (
        bool(re.search(r"^\s*import\s+Breadcrumb\b", source, re.MULTILINE))
        or bool(re.search(r"<\s*Breadcrumb\b", source))
        or bool(
            re.search(
                r"""['"](?:breadcrumb|breadcrumb[_-]?path)['"]""",
                source,
                re.IGNORECASE,
            )
        )
    )
    tem_separador = bool(
        re.search(r"['\"]\s*>\s*['\"]", source)
    ) or bool(re.search(r"\bjoin\s*\(\s*['\"]\s*>\s*['\"]\s*\)", source))

    if not (tem_breadcrumb and tem_separador):
        pytest.fail(
            "AC#4 (granular) — RED.  Breadcrumb de caminho "
            "hierarquico nao encontrado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            f"    Breadcrumb presente: {tem_breadcrumb}\n"
            f"    Separador de caminho presente: {tem_separador}\n"
            "    GREEN deve renderizar um breadcrumb (componente "
            "proprio, importacao, ou JSX inline) que exibe o caminho "
            "ate a categoria selecionada, ex.: `Notas 2025 > "
            "Fornecedores >`, usando ` > ` ou similar como separador."
        )


def test_b3_ac5_no_sem_categoria() -> None:
    """AC#5 — granular.  Falha com mensagem focada apenas no
    no `Sem categoria` para `doc.category === null`.
    """
    source = _read_source(BIBLIOTECA_PATH)

    tem_label = "Sem categoria" in source
    tem_check_null = bool(
        re.search(
            r"\b(?:doc|node|item)\.category\s*(?:===?|!==?)\s*null\b",
            source,
        )
    ) or bool(re.search(r"\b!?(?:doc|node|item)\.category\b", source))
    tem_fallback = bool(
        re.search(
            r"\bcategory\s*\?\?\s*['\"]Sem categoria['\"]",
            source,
        )
    )

    if not (tem_label and (tem_check_null or tem_fallback)):
        pytest.fail(
            "AC#5 (granular) — RED.  No `Sem categoria` para "
            "`doc.category === null` nao encontrado em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n"
            f"    Label `Sem categoria` presente: {tem_label}\n"
            f"    Check `category === null` ou `!doc.category`: "
            f"{tem_check_null}\n"
            f"    Fallback `category ?? 'Sem categoria'`: "
            f"{tem_fallback}\n"
            "    GREEN deve introduzir um no com label "
            "`Sem categoria` que agrupa documentos com `doc.category` "
            "`null`."
        )
