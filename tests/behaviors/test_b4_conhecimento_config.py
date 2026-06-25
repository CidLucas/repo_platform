"""RED test for behavior B-4 — Aba Conhecimento (upload + grid/lista KB)
+ Aba Config (RoutineConfigSection).

GOAL:
    Adicionar a aba "conhecimento" ao EstrategiaRoom.tsx com upload +
    grid/lista + filtros, reusando o hook useKnowledgeBase. Manter
    a aba config com RoutineConfigSection domain='estrategia' fixo
    e a BibliotecaRoom como tela independente.

BEHAVIOR:
    B-4 — Aba Conhecimento (upload+grid/lista KB) +
          Aba Config (RoutineConfigSection).

    Antes: EstrategiaRoom.tsx tem tabs 'decisoes' | 'analises' |
    'historico' | 'config'. Nao ha aba Conhecimento. A config
    usa apenas RoutineConfigSection domain='estrategia' fixo. O
    hook useKnowledgeBase nao e importado no EstrategiaRoom.

    Depois (comportamento esperado):
    - Aba 'conhecimento' exibe zona de upload (file input + drag-drop),
      grid/lista de documentos (DocCard/DocRow com viewMode toggle),
      e filtros (search, categoryFilter, statusFilter) aplicados via
      useMemo. Reutiliza o hook useKnowledgeBase compartilhado.
    - Aba 'config' continua com <RoutineConfigSection domain='estrategia' />
      (apenas este dominio, sem multiplos dominios).
    - BibliotecaRoom permanece como tela independente na sidebar
      (NAV_ITEMS.Screen 'biblioteca' continua).

AC (Acceptance Criteria):
    AC#1 — Aba Conhecimento renderiza zona de upload: input type=file
            com accept, drag-drop zone com onDrop/onDragOver, e
            handleUpload chamando kb.upload ou kb.uploadCsv.
            EstrategiaRoom importa useKnowledgeBase.
    AC#2 — Aba Conhecimento renderiza grid/lista: type Tab inclui
            'conhecimento', viewMode toggle (setViewMode), DocCard
            ou DocRow, condicao tab === 'conhecimento', useMemo
            filtrando documentos.
    AC#3 — Filtros: search input "Buscar documento", categoryFilter
            select, statusFilter select, useMemo aplicando os filtros.
    AC#4 — Aba Config mantem RoutineConfigSection domain='estrategia'
            (apenas este dominio, sem unificacao multi-dominio).
    AC#5 — BibliotecaRoom permanece como tela independente na sidebar
            (NAV_ITEMS inclui 'biblioteca', Screen type contem
            'biblioteca', arquivo BibliotecaRoom.tsx existe).
    AC#6 — EstrategiaRoom.tsx USA o hook useKnowledgeBase (import
            de ../../hooks/useKnowledgeBase) e NAO define DocCard/
            DocRow localmente — o JSX da aba conhecimento reusa
            componentes compartilhados, sem replicar o bloco grande
            de BibliotecaRoom.

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao.
    2. NAO importar ou executar codigo TypeScript/React.
    3. NAO usar fixtures de DB ou rede — teste e pura inspecao de
       arquivos.
"""

import re
from pathlib import Path

import pytest


# ── Constants ──────────────────────────────────────────────────────────────────


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
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

SIDEBAR_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "Sidebar.tsx"
)

APPSTORE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "store"
    / "appStore.ts"
)


# ── Fixture override ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure source inspection, no DB."""
    yield


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-4 (Aba Conhecimento + Config) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — Aba Conhecimento renderiza zona de upload de arquivos ──────────────


def test_b4_ac1_upload():
    """AC#1: A aba 'conhecimento' DEVE renderizar zona de upload de
    arquivos: input type=file com accept, drag-drop zone com
    onDrop/onDragOver, e handleUpload chamando kb.upload ou
    kb.uploadCsv. EstrategiaRoom.tsx deve importar o hook
    useKnowledgeBase.

    Antes (RED): Nao ha input file, drag-drop zone, handleUpload,
        nem import de useKnowledgeBase no EstrategiaRoom.

    Depois (GREEN): Existe <input type='file' accept='...' />,
        zona drag-drop, handleUpload que chama kb.upload/kb.uploadCsv,
        e o componente importa o hook useKnowledgeBase.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Input type=file
    if not re.search(r"type\s*=\s*['\"]file['\"]", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nao foi encontrado input type='file' "
            f"em {ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento tivesse um input "
            f"file oculto para selecao de arquivos.\n\n"
            f"GREEN deve adicionar:\n"
            f"  <input ref={{fileInputRef}} type=\"file\" "
            f"style={{display:'none'}} accept=\"...\" />"
        )

    # 2. Atributo accept com extensoes
    if not re.search(
        r"accept\s*=\s*['\"][^'\"]*\.(pdf|doc|docx|csv|xlsx|txt)",
        content,
        re.IGNORECASE,
    ):
        pytest.fail(
            f"AC#1 violada — RED.  Nao foi encontrado atributo "
            f"'accept' com extensoes de arquivo em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o input file tivesse "
            f"accept=\".pdf,.doc,.docx,.txt,.csv,...\""
        )

    # 3. Drag-drop zone — onDrop
    if not re.search(r"\bonDrop\b", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nao foi encontrado handler "
            f"'onDrop' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse uma zona drag-drop "
            f"com onDrop para upload de arquivos."
        )

    # 4. Drag-drop zone — onDragOver
    if not re.search(r"\bonDragOver\b", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nao foi encontrado handler "
            f"'onDragOver' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a zona drag-drop tivesse "
            f"onDragOver com preventDefault."
        )

    # 5. handleUpload chamando kb.upload ou kb.uploadCsv
    if not re.search(r"\bhandleUpload\b", content) and \
       not re.search(r"\bkb\.upload\b", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nenhuma funcao 'handleUpload' "
            f"ou chamada 'kb.upload'/'kb.uploadCsv' foi encontrada "
            f"em {ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o upload chamasse handleUpload "
            f"que por sua vez invoca kb.upload ou kb.uploadCsv.\n\n"
            f"GREEN deve ter:\n"
            f"  async function handleUpload(file: File) {{\n"
            f"    if (isCsvFile(file.name)) await kb.uploadCsv(file)\n"
            f"    else await kb.upload(file, false, 'upload', {{...}})"
        )

    # 6. Import do hook useKnowledgeBase
    if not re.search(r"import\b[^;]*useKnowledgeBase", content) and \
       not re.search(r"from\s+['\"]\.\.?/hooks/useKnowledgeBase['\"]", content):
        pytest.fail(
            f"AC#1 violada — RED.  O hook 'useKnowledgeBase' nao "
            f"foi importado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o componente importasse useKnowledgeBase "
            f"do caminho '../../hooks/useKnowledgeBase'.\n\n"
            f"GREEN deve adicionar:\n"
            f"  import {{ useKnowledgeBase }} from "
            f"'../../hooks/useKnowledgeBase'\n"
            f"  ...\n"
            f"  const kb = useKnowledgeBase()"
        )


# ── AC#2 — Aba Conhecimento renderiza grid ou lista de documentos ─────────────


def test_b4_ac2_grid_lista():
    """AC#2: A aba 'conhecimento' DEVE renderizar grid/lista de
    documentos: type Tab inclui 'conhecimento', viewMode toggle
    (setViewMode), DocCard ou DocRow, condicao tab === 'conhecimento',
    e useMemo filtrando documentos.

    Antes (RED): Nao ha aba 'conhecimento' no type Tab. Nao ha
        viewMode toggle. Nao ha DocCard/DocRow no EstrategiaRoom.

    Depois (GREEN): type Tab = 'decisoes' | 'analises' | 'historico'
        | 'conhecimento' | 'config', e o template renderiza
        DocCard/DocRow com viewMode toggle.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. 'conhecimento' no type Tab
    tab_match = re.search(
        r"type\s+Tab\s*=\s*([\s\S]*?)(?:;|\n\s*\n)",
        content,
    )
    if not tab_match:
        pytest.fail(
            f"Pre-condicao violada: type Tab nao encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}."
        )
    tab_type_block = tab_match.group(1)

    if not re.search(r"['\"]conhecimento['\"]", tab_type_block):
        pytest.fail(
            f"AC#2 violada — RED.  O valor 'conhecimento' NAO esta "
            f"presente no type Tab de "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Type Tab atual: {tab_type_block.strip()}\n\n"
            f"Era esperado que type Tab incluísse 'conhecimento':\n"
            f"  type Tab = 'decisoes' | 'analises' | 'historico' "
            f"| 'conhecimento' | 'config'\n\n"
            f"GREEN deve adicionar 'conhecimento' ao type Tab "
            f"e renderizar a aba correspondente."
        )

    # 2. viewMode toggle (setViewMode)
    if not re.search(r"\bsetViewMode\b", content):
        pytest.fail(
            f"AC#2 violada — RED.  Nenhuma chamada a 'setViewMode' "
            f"foi encontrada em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento tivesse toggle "
            f"de visualizacao grid/list via setViewMode.\n\n"
            f"GREEN deve ter:\n"
            f"  const [viewMode, setViewMode] = useState<ViewMode>('grid')"
        )

    # 3. DocCard ou DocRow renderizado
    if not re.search(r"\bDocCard\b", content) and \
       not re.search(r"\bDocRow\b", content):
        pytest.fail(
            f"AC#2 violada — RED.  Nenhum componente 'DocCard' ou "
            f"'DocRow' foi encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento renderizasse "
            f"documentos via DocCard (grid) ou DocRow (list), "
            f"conforme o viewMode ativo."
        )

    # 4. Condicao tab === 'conhecimento'
    if not re.search(r"tab\s*===\s*['\"]conhecimento['\"]", content):
        pytest.fail(
            f"AC#2 violada — RED.  Nao foi encontrada condicao "
            f"'tab === 'conhecimento'' para exibir o conteudo "
            f"da aba em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um bloco div className='tc' "
            f"condicionado a tab === 'conhecimento'."
        )

    # 5. useMemo presente (sinal de derivacao/lazy computation)
    if not re.search(r"\buseMemo\b", content):
        pytest.fail(
            f"AC#2 violada — RED.  Nenhuma chamada a 'useMemo' foi "
            f"encontrada em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse useMemo para derivar a "
            f"lista filtrada de documentos."
        )


# ── AC#3 — Aba Conhecimento suporta filtros (tipo, busca) ────────────────────


def test_b4_ac3_filtros():
    """AC#3: A aba 'conhecimento' DEVE suportar filtros: search input
    com placeholder 'Buscar documento', categoryFilter select,
    statusFilter select, e useMemo aplicando os filtros.

    Antes (RED): Nao ha filtros de conhecimento no EstrategiaRoom.

    Depois (GREEN): Existem search, categoryFilter, statusFilter
        com useMemo filtrando kb.documents.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Search input com placeholder de busca
    if not re.search(r"['\"]Buscar documento", content, re.IGNORECASE):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrado placeholder "
            f"de busca de documentos em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento tivesse um "
            f"input de busca com placeholder como "
            f"'Buscar documento...'.\n\n"
            f"GREEN deve adicionar search input com onChange "
            f"atualizando estado search."
        )

    # 2. categoryFilter select
    if not re.search(r"\bcategoryFilter\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  'categoryFilter' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um filtro por categoria "
            f"(select com 'Todas as categorias' + opcoes de "
            f"KB_CATEGORIES).\n\n"
            f"GREEN deve adicionar categoryFilter select "
            f"com onChange atualizando o estado."
        )

    # 3. statusFilter select
    if not re.search(r"\bstatusFilter\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  'statusFilter' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um filtro por status "
            f"(select com 'Todos os status' + opcoes de "
            f"completed/processing/pending/failed).\n\n"
            f"GREEN deve adicionar statusFilter select "
            f"com onChange atualizando o estado."
        )

    # 4. useMemo aplicando os filtros
    if not re.search(r"\buseMemo\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nenhuma chamada a 'useMemo' foi "
            f"encontrada em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que os filtros fossem aplicados via "
            f"useMemo, filtrando kb.documents por search, "
            f"categoryFilter e statusFilter."
        )

    # 5. useMemo com filter aplicado — busca por filter() dentro
    #    de um useMemo OU filter de documents
    memo_blocks = re.findall(r"useMemo\s*\([^)]*\)", content, re.DOTALL)
    found_filter_memo = False
    for block in memo_blocks:
        if "filter" in block:
            found_filter_memo = True
            break

    # fallback mais amplo: verifica uso de filter() em qualquer lugar
    # dentro do arquivo (sinal de filtragem de documentos)
    if not found_filter_memo and not re.search(r"\.filter\(", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nenhuma chamada a '.filter(' foi "
            f"encontrada em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse logica de filtragem "
            f"(kb.documents.filter(...)) dentro de useMemo, "
            f"aplicando search, categoryFilter e statusFilter."
        )


# ── AC#4 — Aba Config mantem RoutineConfigSection com domain='estrategia' ────


def test_b4_ac4_config():
    """AC#4: A aba 'config' DEVE manter RoutineConfigSection com
    domain='estrategia' (apenas este dominio fixo — NAO exige
    multiplos dominios, NAO unifica).

    Antes (RED-para-B-4): EstrategiaRoom ja tem
        <RoutineConfigSection domain='estrategia' />, mas o spec
        do behavior B-4 exige que este estado seja PRESERVADO
        apos a adicao da aba conhecimento. Este teste e uma
        salvaguarda contra regressao.

    Depois (GREEN): Apos adicionar 'conhecimento', a aba config
        continua com <RoutineConfigSection domain='estrategia' />
        (uma unica ocorrencia, sem unificacao multi-dominio).
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. RoutineConfigSection presente
    if not re.search(r"\bRoutineConfigSection\b", content):
        pytest.fail(
            f"AC#4 violada — RED.  'RoutineConfigSection' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba config renderizasse "
            f"RoutineConfigSection para configuracao de rotinas."
        )

    # 2. domain='estrategia' presente (unico, fixo)
    if not re.search(r"domain\s*=\s*['\"]estrategia['\"]", content):
        pytest.fail(
            f"AC#4 violada — RED.  'domain=\"estrategia\"' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba config mantivesse "
            f"<RoutineConfigSection domain='estrategia' />."
        )

    # 3. Garantir que NAO ha outro dominio alem de 'estrategia'
    #    (o spec do B-4 e manter APENAS 'estrategia' fixo)
    other_domain_patterns = [
        r"domain\s*=\s*['\"]documentos['\"]",
        r"domain\s*=\s*['\"]financeiro['\"]",
        r"domain\s*=\s*['\"]compras['\"]",
    ]
    found_other = []
    for pat in other_domain_patterns:
        m = re.search(pat, content)
        if m:
            found_other.append(m.group(0))

    if found_other:
        pytest.fail(
            f"AC#4 violada — RED.  Foram encontrados outros dominios "
            f"alem de 'estrategia' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}: "
            f"{found_other}\n\n"
            f"O spec do B-4 exige manter APENAS domain='estrategia' "
            f"fixo na aba config, sem unificacao multi-dominio."
        )


# ── AC#5 — BibliotecaRoom permanece como tela independente na sidebar ───────


def test_b4_ac5_biblioteca_intact():
    """AC#5: BibliotecaRoom DEVE permanecer como tela independente
    na sidebar. NAV_ITEMS em Sidebar.tsx contem { s: 'biblioteca',
    label: 'Biblioteca' } (ou equivalente). Screen type em
    appStore.ts contem 'biblioteca'. O arquivo BibliotecaRoom.tsx
    ainda existe em pages/app/.

    Antes (RED-para-B-4): Estes elementos ja existem no codigo
        atual, mas o spec do behavior B-4 exige que sejam
        PRESERVADOS apos a adicao da aba conhecimento no
        EstrategiaRoom. Este teste e uma salvaguarda contra
        regressao — a aba conhecimento NAO deve remover a
        BibliotecaRoom como tela independente.

    Depois (GREEN): Sidebar continua com 'biblioteca' em
        NAV_ITEMS, appStore Screen inclui 'biblioteca', e
        BibliotecaRoom.tsx ainda existe.
    """
    # 1. Sidebar.tsx contem { s: 'biblioteca', label: 'Biblioteca' }
    #    em NAV_ITEMS (a ordem dos campos pode variar, e o icon JSX
    #    pode conter '}' no meio, entao usamos .*? com DOTALL).
    sidebar_content = _read_text(SIDEBAR_PATH)
    has_biblioteca_item = (
        re.search(
            r"s\s*:\s*['\"]biblioteca['\"].*?label\s*:\s*['\"]Biblioteca['\"]",
            sidebar_content,
            re.DOTALL,
        )
        is not None
    ) or (
        re.search(
            r"label\s*:\s*['\"]Biblioteca['\"].*?s\s*:\s*['\"]biblioteca['\"]",
            sidebar_content,
            re.DOTALL,
        )
        is not None
    )
    if not has_biblioteca_item:
        pytest.fail(
            f"AC#5 violada — RED.  Nao foi encontrado "
            f"{{ s: 'biblioteca', label: 'Biblioteca' }} (ou ordem "
            f"invertida) em NAV_ITEMS no arquivo "
            f"{SIDEBAR_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a sidebar continuasse expondo "
            f"a BibliotecaRoom como tela independente."
        )

    # 2. appStore.ts contem 'biblioteca' no type Screen
    appstore_content = _read_text(APPSTORE_PATH)
    if not re.search(r"['\"]biblioteca['\"]", appstore_content):
        pytest.fail(
            f"AC#5 violada — RED.  O valor 'biblioteca' NAO esta "
            f"presente no type Screen em "
            f"{APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o Screen type incluísse 'biblioteca' "
            f"para que a BibliotecaRoom permaneca acessivel."
        )

    # 3. BibliotecaRoom.tsx ainda existe
    if not BIBLIOTECA_ROOM_PATH.exists():
        pytest.fail(
            f"AC#5 violada — RED.  O arquivo "
            f"{BIBLIOTECA_ROOM_PATH.relative_to(REPO_ROOT)} nao "
            f"existe mais.\n\n"
            f"Era esperado que BibliotecaRoom.tsx permanecesse "
            f"como tela independente no pages/app/."
        )


# ── AC#6 — Aba Conhecimento NAO duplica JSX da BibliotecaRoom ────────────────


def test_b4_ac6_sem_duplicacao():
    """AC#6: A aba 'conhecimento' no EstrategiaRoom.tsx NAO deve
    duplicar o JSX da BibliotecaRoom. EstrategiaRoom.tsx DEVE
    importar o hook useKnowledgeBase e reusar componentes
    compartilhados (DocCard/DocRow) em vez de defini-los
    localmente.

    Antes (RED): EstrategiaRoom.tsx NAO importa useKnowledgeBase.

    Depois (GREEN): EstrategiaRoom.tsx importa useKnowledgeBase
        do caminho '../../hooks/useKnowledgeBase' e reusa
        DocCard/DocRow compartilhados em vez de duplicar a
        BibliotecaRoom.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. EstrategiaRoom.tsx importa useKnowledgeBase
    if not re.search(
        r"import\b[^;]*useKnowledgeBase",
        content,
    ) and not re.search(
        r"from\s+['\"]\.\.?/hooks/useKnowledgeBase['\"]",
        content,
    ):
        pytest.fail(
            f"AC#6 violada — RED.  O hook 'useKnowledgeBase' nao "
            f"foi importado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que EstrategiaRoom.tsx importasse "
            f"useKnowledgeBase para reusar a logica de KB, em vez "
            f"de duplicar o JSX de BibliotecaRoom.tsx.\n\n"
            f"GREEN deve adicionar:\n"
            f"  import {{ useKnowledgeBase }} from "
            f"'../../hooks/useKnowledgeBase'"
        )

    # 2. EstrategiaRoom.tsx NAO define DocCard/DocRow como funcao
    #    local (devem ser componentes compartilhados/importados)
    local_doc_function_patterns = [
        r"function\s+DocCard\b",
        r"function\s+DocRow\b",
        r"const\s+DocCard\s*=\s*[\(\(]",
        r"const\s+DocRow\s*=\s*[\(\(]",
    ]
    found_local = []
    for pat in local_doc_function_patterns:
        m = re.search(pat, content)
        if m:
            found_local.append(m.group(0))

    if found_local:
        pytest.fail(
            f"AC#6 violada — RED.  EstrategiaRoom.tsx define "
            f"componentes DocCard/DocRow LOCALMENTE: "
            f"{found_local}\n\n"
            f"O spec exige que EstrategiaRoom REUSE DocCard/DocRow "
            f"compartilhados (ja existentes em outro modulo) em vez "
            f"de duplicar a implementacao de BibliotecaRoom.tsx."
        )

    # 3. EstrategiaRoom.tsx NAO deve replicar a constante
    #    KB_CATEGORIES (declarada em BibliotecaRoom) — se a aba
    #    conhecimento precisa das categorias, deve importar do
    #    mesmo modulo compartilhado, nao redefinir localmente.
    if re.search(r"KB_CATEGORIES\s*[:=]", content):
        # se EstrategiaRoom declarar KB_CATEGORIES, isso pode ser
        # aceitavel se vier de import — mas se for assignment/
        # declaracao local, falha
        if re.search(
            r"(?:const|let|var)\s+KB_CATEGORIES\s*=",
            content,
        ):
            pytest.fail(
                f"AC#6 violada — RED.  EstrategiaRoom.tsx declara "
                f"KB_CATEGORIES localmente, em vez de reusar a "
                f"constante compartilhada de BibliotecaRoom.\n\n"
                f"GREEN deve importar KB_CATEGORIES do mesmo "
                f"modulo compartilhado, evitando duplicacao."
            )
