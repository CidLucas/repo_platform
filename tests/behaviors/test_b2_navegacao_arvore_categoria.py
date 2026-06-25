"""RED test — B-2 (BKL-035): Navegacao em arvore por categoria na BibliotecaRoom.

GOAL:
    Substituir a listagem plana de categorias no painel "Por categoria"
    (CollapsiblePanel id="kb-categories", linhas 512-535) da
    BibliotecaRoom.tsx por uma arvore hierarquica, com:
        - Servico `getCategoryTree` que retorna `CategoryNode[]`
          (cada no: name, count, children, value/ref).
        - Itens de categoria com onClick que abrem/selecionam a categoria.
        - Breadcrumb de navegacao no header do painel de documentos
          (caminho da categoria + botao "voltar para").
        - Renderizacao de subcategorias aninhadas com indentacao
          (mapa de `children` no painel de categorias).

BEHAVIOR:
    "B-2 (BKL-035): Navegacao em arvore por categoria na BibliotecaRoom.
    O usuario pode clicar em uma categoria para ver apenas os documentos
    daquela categoria; categorias com subcategorias expandem em arvore;
    o header do painel de documentos exibe o caminho (breadcrumb) da
    categoria atual; clicar em 'voltar para' retorna para o nivel
    anterior."

    O codigo de producao atualmente (BEFORE — RED) NAO tem nenhuma das
    seguintes caracteristicas:
        - Funcao `getCategoryTree` em knowledgeBaseService.ts.
        - Tipo `CategoryNode` em knowledgeBaseService.ts.
        - Import de `getCategoryTree` ou `CategoryNode` em BibliotecaRoom.tsx.
        - Itens de categoria com onClick / cursor:pointer na sidebar de
          categorias (apenas divs planas de display).
        - Breadcrumb no header do painel de documentos
          (sem texto 'breadcrumb', 'caminho' ou 'voltar para').
        - Renderizacao aninhada de subcategorias (sem `children` mapeado
          no contexto do painel de categorias, sem indentacao por nivel).

    Estado esperado (AFTER — GREEN):
        knowledgeBaseService.ts deve exportar:
        - type CategoryNode { name; value?; count; children?: CategoryNode[] }
        - async function getCategoryTree(clientId): Promise<CategoryNode[]>
        BibliotecaRoom.tsx deve:
        - Importar getCategoryTree e CategoryNode.
        - Renderizar a arvore com .children map() recursivo.
        - Tornar os itens de categoria clicaveis (onClick, cursor pointer).
        - Exibir breadcrumb no header (Documentos > [categoria] > [sub]).

AC (Acceptance Criteria):
    AC#1 - knowledgeBaseService.ts exporta `getCategoryTree` (funcao).
    AC#2 - knowledgeBaseService.ts define o tipo `CategoryNode` com
           campos `name`, `count` e `children`.
    AC#3 - BibliotecaRoom.tsx importa `getCategoryTree` ou `CategoryNode`
           a partir de knowledgeBaseService.
    AC#4 - Itens de categoria no painel "Por categoria" sao clicaveis
           (existem onClick handlers ou `cursor: 'pointer'` em divs
           que renderizam categorias, ou useState de categoria selecionada).
    AC#5 - O header do painel de documentos exibe breadcrumb de
           navegacao (texto como "breadcrumb", "caminho", "voltar para",
           ou `> ` separador de categoria atual).
    AC#6 - Renderizacao de subcategorias aninhadas (mapa `.children`
           com indentacao, ou padding-left incremental) no painel de
           categorias.

Anti-Goals:
    1. NAO modificar codigo de producao (BibliotecaRoom.tsx ou
       knowledgeBaseService.ts) — o teste so INSPECIONA o codigo.
    2. NAO executar/transpilar TSX — somente inspecao textual com regex.
    3. NAO usar mocks, Supabase ou banco de dados.
    4. NAO testar funcionalidade ja existente (precisa ser TRUE RED).
    5. NAO relaxar o teste para que ele passe — precisa ser TRUE RED
       agora (codigo AINDA nao tem arvore de navegacao por categoria).
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

KB_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)

BIBLIOTECA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure unit tests, no DB needed."""
    yield


# ── Helpers ───────────────────────────────────────────────────────────


def read_kb_service_source() -> str:
    """Return knowledgeBaseService.ts content as a single string."""
    return KB_SERVICE_PATH.read_text(encoding="utf-8")


def read_biblioteca_source() -> str:
    """Return BibliotecaRoom.tsx content as a single string."""
    return BIBLIOTECA_ROOM_PATH.read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════
# Acceptance Criteria Tests
# ═════════════════════════════════════════════════════════════════════


class TestB2NavegacaoArvoreCategoria:
    """B-2: Navegacao em arvore por categoria — RED tests."""

    # ── AC#1: knowledgeBaseService.ts exporta getCategoryTree ───────

    def test_ac1_get_category_tree_exists(self):
        """AC#1: knowledgeBaseService.ts exporta `getCategoryTree`.

        Esperado (GREEN): export async function getCategoryTree(...) ou
        export function getCategoryTree(...) presente no servico.
        Atual (RED): nao existe — somente listDocuments, deleteDocument,
        getDocumentProgress, uploadFile, retryDocument etc.
        """
        source = read_kb_service_source()
        # Procura declaracao de funcao getCategoryTree (exportada ou nao)
        found = bool(re.search(
            r"(?:export\s+)?(?:async\s+)?function\s+getCategoryTree\b",
            source,
        ))
        if found:
            pytest.fail(
                "AC#1 FALSE RED — funcao getCategoryTree ja existe em "
                "knowledgeBaseService.ts. O teste deveria falhar no estado "
                "atual (RED). O codigo de producao ja tem essa funcionalidade."
            )
        # TRUE RED: getCategoryTree nao foi declarado — o que e esperado
        # no estado atual

    # ── AC#2: tipo CategoryNode com name, count, children ──────────

    def test_ac2_category_node_type_exists(self):
        """AC#2: knowledgeBaseService.ts define o tipo `CategoryNode`.

        Esperado (GREEN): type/interface CategoryNode { name; count;
        children?: CategoryNode[]; value?: string } (ou ref).
        Atual (RED): nao existe. Tipos atuais: KBDocument, UploadOptions,
        EmbeddingProgress, KBDocumentSource, KBCategory.
        """
        source = read_kb_service_source()
        # Procura a declaracao do tipo CategoryNode
        found = bool(re.search(
            r"(?:type|interface)\s+CategoryNode\b",
            source,
        ))
        if found:
            pytest.fail(
                "AC#2 FALSE RED — tipo CategoryNode ja existe em "
                "knowledgeBaseService.ts."
            )
        # TRUE RED

    # ── AC#3: BibliotecaRoom.tsx importa getCategoryTree/CategoryNode ─

    def test_ac3_imports_get_category_tree(self):
        """AC#3: BibliotecaRoom.tsx importa getCategoryTree ou CategoryNode.

        Esperado (GREEN): import { ..., getCategoryTree, ... } from
        '../../services/knowledgeBaseService' ou similar com CategoryNode.
        Atual (RED): import atual (linha 5) so traz KB_CATEGORIES,
        isCsvFile, type KBDocument, type KBCategory.
        """
        source = read_biblioteca_source()
        # Procura import a partir de knowledgeBaseService que inclua
        # getCategoryTree ou CategoryNode
        found = bool(re.search(
            r"import\s+\{[^}]*(?:getCategoryTree|CategoryNode)[^}]*\}\s+from\s+['\"][^'\"]*knowledgeBaseService['\"]",
            source,
        ))
        if found:
            pytest.fail(
                "AC#3 FALSE RED — BibliotecaRoom.tsx ja importa "
                "getCategoryTree ou CategoryNode de knowledgeBaseService."
            )
        # TRUE RED

    # ── AC#4: Itens de categoria clicaveis (onClick / cursor pointer) ─

    def test_ac4_clickable_category_items(self):
        """AC#4: Itens de categoria no painel "Por categoria" sao
        clicaveis (onClick em divs de categoria, ou cursor: pointer,
        ou state de categoria selecionada para clique).

        Esperado (GREEN): dentro do bloco do CollapsiblePanel
        "kb-categories" (linhas 512-535) ha divs de categoria com
        onClick, cursor: pointer, ou um state de categoria clicada.
        Atual (RED): o painel atual e uma listagem plana sem nenhum
        onClick, sem cursor:pointer nas divs internas, e sem state
        de categoria clicada. (Outros elementos da pagina, como o
        dropzone ou dropdowns, podem ter cursor:pointer, mas isso
        NAO conta — o teste checa EXPLICITAMENTE o bloco de
        categorias.)
        """
        source = read_biblioteca_source()
        # Isola o bloco do CollapsiblePanel "kb-categories" — entre
        # a abertura do id="kb-categories" e o </CollapsiblePanel>
        # correspondente. Usa busca nao-gulosa.
        panel_match = re.search(
            r"id=[\"']kb-categories[\"'].*?</CollapsiblePanel>",
            source,
            flags=re.DOTALL,
        )
        if panel_match is None:
            # Nao encontrou o painel — improvavel, mas trata
            pytest.fail(
                "AC#4 setup error — nao foi possivel localizar o "
                "CollapsiblePanel id='kb-categories' em BibliotecaRoom.tsx."
            )
        category_block = panel_match.group(0)

        # Dentro do bloco, procura sinais de interatividade
        has_onclick = bool(re.search(
            r"onClick\s*=",
            category_block,
        ))
        has_cursor_pointer = bool(re.search(
            r"cursor:\s*['\"]?pointer['\"]?",
            category_block,
        ))

        # Fora do painel, mas em todo o arquivo, verifica se existe
        # um state novo para a categoria clicada via interacao
        has_click_state = bool(re.search(
            r"selectedCategory|categorySelected|activeCategory|categoriaSelecionada|activeCat",
            source,
        ))

        found = has_onclick or has_cursor_pointer or has_click_state
        if found:
            pytest.fail(
                "AC#4 FALSE RED — o painel 'Por categoria' ja tem itens "
                "clicaveis (onClick / cursor:pointer dentro do bloco "
                "kb-categories, ou state de categoria selecionada)."
            )
        # TRUE RED: o painel atual e estatico, sem onClick/cursor pointer
        # nas divs de categoria e sem state de categoria clicada

    # ── AC#5: Breadcrumb no header do painel de documentos ──────────

    def test_ac5_breadcrumb_in_documents_header(self):
        """AC#5: Header do painel "Documentos" exibe breadcrumb de
        navegacao (caminho da categoria + botao "voltar para").

        Esperado (GREEN): no header (linhas 339-357) ha um breadcrumb
        com texto do tipo "breadcrumb", "caminho", "voltar para" ou
        separador ">" entre niveis de categoria.
        Atual (RED): o header atual mostra apenas "Documentos" + count
        + toggle de view (grid/list). Nao ha breadcrumb.
        """
        source = read_biblioteca_source()
        # Procura referencias textuais a breadcrumb / caminho / voltar
        found = bool(re.search(
            r"(?:breadcrumb|caminho|voltar\s+para|trilha|navegac[aã]o\s+de\s+categoria)",
            source,
            flags=re.IGNORECASE,
        ))
        if found:
            pytest.fail(
                "AC#5 FALSE RED — BibliotecaRoom.tsx ja tem texto de "
                "breadcrumb (breadcrumb/caminho/voltar para) no header "
                "de documentos."
            )
        # TRUE RED

    # ── AC#6: Renderizacao aninhada de subcategorias (children map) ─

    def test_ac6_nested_subcategory_rendering(self):
        """AC#6: O painel "Por categoria" renderiza subcategorias
        aninhadas com indentacao (mapa `.children` ou padding-left
        incremental).

        Esperado (GREEN): existe um .map() sobre `node.children` (ou
        `cat.children`) ou padding-left condicional para indicar
        profundidade. Pode ser combinado com recursao (componente
        CategoryTreeNode) que mapeia .children.
        Atual (RED): o painel atual so itera KB_CATEGORIES plano,
        sem nenhum .children.
        """
        source = read_biblioteca_source()
        # Procura acesso a .children no contexto de categorias
        has_children_map = bool(re.search(
            r"(?:node|cat|categoria|category)\.children\.map\s*\(",
            source,
        ))
        has_children_access = bool(re.search(
            r"\.children\b",
            source,
        ))
        # Tambem verificar recursao explicita de um componente de arvore
        has_recursive_tree = bool(re.search(
            r"CategoryTree(?:Node|Item)|renderTree|renderNode|TreeNode",
            source,
        ))
        found = has_children_map or has_children_access or has_recursive_tree
        if found:
            pytest.fail(
                "AC#6 FALSE RED — BibliotecaRoom.tsx ja renderiza "
                "subcategorias aninhadas (.children map ou componente "
                "de arvore)."
            )
        # TRUE RED: renderizacao ainda e plana, sem .children
