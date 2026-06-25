"""RED test for behavior B-5 — Abas Conhecimento + Config.

GOAL:
    Portar BibliotecaRoom para aba Conhecimento + unificar config de rotinas.

BEHAVIOR:
    B-5 — Abas Conhecimento + Config — Portar BibliotecaRoom + unificar
    config de rotinas.

    Antes: EstrategiaRoom.tsx tem tabs 'decisoes', 'analises', 'historico',
    'config' com conteudo antigo. Nao ha aba Conhecimento. A config de
    rotinas usa apenas domain='estrategia' fixo.

    Depois (comportamento esperado):
    - Aba 'conhecimento' exibe grid/lista de documentos (DocCard/DocRow)
      com viewMode toggle ('grid' | 'list'), filtros por categoria/status,
      e upload drag-drop + file input.
    - Aba 'config' mostra RoutineConfigSection de forma unificada
      (nao apenas domain='estrategia' fixo — pelo menos
       abrangendo ambos os dominios ou com selector).
    - Upload de documento funciona: input type=file com accept,
      drag-drop zone, handleUpload.

AC (Acceptance Criteria):
    AC#1 — Aba conhecimento renderiza grid/lista de documentos: existe
            viewMode toggle (setViewMode), DocCard/DocRow, e estado
            'conhecimento' no type Tab.
    AC#2 — Aba conhecimento tem filtros: search input, categoryFilter
            select, statusFilter select — com useMemo para filtrar.
    AC#3 — Upload de documento: input file escondido com accept types,
            drag-drop zone com onDrop/onDragOver, e chamada a upload
            ou uploadCsv.
    AC#4 — Aba config tem RoutineConfigSection unificado (nao apenas
            domain='estrategia' fixo — referencia multiplos dominios
            ou usa domain dinamico/variavel).

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao.
    2. NAO importar ou executar codigo TypeScript/React.
    3. NAO usar fixtures de DB ou rede — teste e pura inspecao de arquivos.
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
        f"O behavior B-5 (Conhecimento + Config) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — Aba conhecimento renderiza grid/lista de documentos ────────────────


def test_b5_ac1_conhecimento_grid_lista_documentos():
    """AC#1: A aba 'conhecimento' DEVE ter viewMode toggle ('grid'|'list'),
    DocCard/DocRow, e o valor 'conhecimento' no type Tab.

    Antes (RED): Nao ha aba conhecimento. O type Tab e
        'decisoes' | 'analises' | 'historico' | 'config'.

    Depois (GREEN): type Tab inclui 'conhecimento', e o template
        renderiza DocCard/DocRow com toggle grid/list.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Verifica que 'conhecimento' esta no type Tab
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
            f"AC#1 violada — RED.  O valor 'conhecimento' NAO esta "
            f"presente no type Tab.\n\n"
            f"Type Tab atual: {tab_type_block.strip()}\n\n"
            f"Era esperado que type Tab incluísse:\n"
            f"  type Tab = 'objetivos' | 'documentos' | "
            f"'conhecimento' | 'config'\n\n"
            f"GREEN deve adicionar 'conhecimento' ao type Tab "
            f"e renderizar DocCard/DocRow com viewMode toggle."
        )

    # 2. Verifica que existe viewMode toggle (setViewMode)
    if not re.search(r"setViewMode\b", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nenhuma chamada a 'setViewMode' "
            f"foi encontrada em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento tivesse toggle "
            f"de visualizacao grid/list via setViewMode.\n\n"
            f"GREEN deve ter:\n"
            f"  const [viewMode, setViewMode] = useState<ViewMode>('grid')"
        )

    # 3. Verifica que existe DocCard ou DocRow
    if not re.search(r"DocCard\b", content) and not re.search(r"DocRow\b", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nenhum componente 'DocCard' ou "
            f"'DocRow' foi encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento renderizasse "
            f"documentos via DocCard (grid) ou DocRow (list), "
            f"conforme o viewMode ativo.\n\n"
            f"GREEN deve portar DocCard e DocRow para o template "
            f"da aba conhecimento."
        )

    # 4. Verifica que a renderizacao condiciona ao tab === 'conhecimento'
    if not re.search(r"tab\s*===\s*['\"]conhecimento['\"]", content):
        pytest.fail(
            f"AC#1 violada — RED.  Nao foi encontrada condicao "
            f"'tab === 'conhecimento'' para exibir o conteudo "
            f"da aba em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um bloco TC panel "
            f"condicionado a tab === 'conhecimento'."
        )


# ── AC#2 — Filtros (search, categoria, status) ────────────────────────────────


def test_b5_ac2_filtros_conhecimento():
    """AC#2: A aba conhecimento DEVE ter filtros: search input,
    categoryFilter select, statusFilter select, aplicados via useMemo.

    Antes (RED): Nao ha filtros de conhecimento no EstrategiaRoom.

    Depois (GREEN): Existem search, categoryFilter, statusFilter
        com useMemo filtrando kb.documents.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Search input com placeholder de busca
    if not re.search(r"['\"]Buscar documento", content, re.IGNORECASE):
        pytest.fail(
            f"AC#2 violada — RED.  Nao foi encontrado placeholder "
            f"de busca de documentos em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba conhecimento tivesse um "
            f"input de busca com placeholder como "
            f"'Buscar documento...'.\n\n"
            f"GREEN deve adicionar search input com onChange "
            f"atualizando estado search."
        )

    # 2. categoryFilter select
    if not re.search(r"categoryFilter\b", content):
        pytest.fail(
            f"AC#2 violada — RED.  'categoryFilter' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um filtro por categoria "
            f"(select com 'Todas as categorias' + opcoes de "
            f"KB_CATEGORIES).\n\n"
            f"GREEN deve adicionar categoryFilter select "
            f"com onChange atualizando o estado."
        )

    # 3. statusFilter select
    if not re.search(r"statusFilter\b", content):
        pytest.fail(
            f"AC#2 violada — RED.  'statusFilter' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um filtro por status "
            f"(select com 'Todos os status' + opcoes de "
            f"completed/processing/pending/failed).\n\n"
            f"GREEN deve adicionar statusFilter select "
            f"com onChange atualizando o estado."
        )

    # 4. useMemo filtrando documentos
    if not re.search(r"useMemo\b.*filter", content, re.DOTALL):
        # fallback: check for useMemo near filtering logic
        memo_blocks = re.findall(r"useMemo\s*\(.*?\)", content, re.DOTALL)
        found_filter_memo = False
        for block in memo_blocks:
            if "filter" in block or "categoryFilter" in block or "statusFilter" in block:
                found_filter_memo = True
                break
        if not found_filter_memo:
            pytest.fail(
                f"AC#2 violada — RED.  Nao foi encontrado useMemo "
                f"com logica de filtragem de documentos em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Era esperado que os filtros fossem aplicados via "
                f"useMemo, filtrando kb.documents por search, "
                f"categoryFilter e statusFilter.\n\n"
                f"GREEN deve ter algo como:\n"
                f"  const filtered = useMemo(() => {{\n"
                f"    return kb.documents.filter(doc => {{\n"
                f"      if (search && !doc.file_name.includes(...)) ..."
            )


# ── AC#3 — Upload de documento ────────────────────────────────────────────────


def test_b5_ac3_upload_documento():
    """AC#3: Upload de documento DEVE funcionar: input file escondido
    com accept types, drag-drop zone com onDrop/onDragOver,
    e chamada a upload ou uploadCsv.

    Antes (RED): Nao ha mecanismo de upload no EstrategiaRoom.

    Depois (GREEN): Existe input type=file, drag-drop zone,
        handleUpload que chama kb.upload/kb.uploadCsv.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Input file escondido (type="file", style="display:none")
    if not re.search(r"type\s*=\s*['\"]file['\"]", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrado input "
            f"type='file' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse um input file oculto "
            f"para selecao de arquivos.\n\n"
            f"GREEN deve adicionar:\n"
            f"  <input ref={{fileInputRef}} type=\"file\" "
            f"style={{display:'none'}} accept=\"...\" />"
        )

    # 2. Accept com extensoes de arquivo
    if not re.search(r"accept\s*=\s*['\"][^'\"]*\.(pdf|doc|docx|csv|xlsx)", content, re.IGNORECASE):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrado atributo "
            f"'accept' com extensoes de arquivo em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o input file tivesse "
            f"accept=\".pdf,.doc,.docx,.txt,.csv,...\""
        )

    # 3. Drag-drop zone onDrop/onDragOver
    if not re.search(r"onDrop\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrado handler "
            f"'onDrop' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que houvesse uma zona drag-drop "
            f"com onDrop para upload de arquivos."
        )

    if not re.search(r"onDragOver\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrado handler "
            f"'onDragOver' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a zona drag-drop tivesse "
            f"onDragOver com preventDefault."
        )

    # 4. handleUpload ou upload/uploadCsv
    if not re.search(r"\bhandleUpload\b", content) and \
       not re.search(r"\bkb\.upload\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nao foi encontrada funcao "
            f"'handleUpload' ou 'kb.upload' em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o upload chamasse handleUpload "
            f"que por sua vez invoca kb.upload ou kb.uploadCsv.\n\n"
            f"GREEN deve ter:\n"
            f"  async function handleUpload(file: File) {{\n"
            f"    if (isCsvFile(file.name)) await kb.uploadCsv(file)\n"
            f"    else await kb.upload(file, false, 'upload', {{...}})"
        )

    # 5. useKnowledgeBase hook
    if not re.search(r"useKnowledgeBase\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  O hook 'useKnowledgeBase' nao "
            f"foi encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o componente usasse useKnowledgeBase "
            f"para gerenciar documentos e uploads.\n\n"
            f"GREEN deve importar e usar useKnowledgeBase:\n"
            f"  const kb = useKnowledgeBase()"
        )


# ── AC#4 — Aba config com RoutineConfigSection unificado ──────────────────────


def test_b5_ac4_config_routineconfig_unificado():
    """AC#4: A aba 'config' DEVE renderizar RoutineConfigSection de
    forma unificada — nao apenas domain='estrategia' fixo, mas
    referenciando multiplos dominios ou usando domain dinamico.

    Antes (RED): <RoutineConfigSection domain='estrategia' /> fixo.

    Depois (GREEN): RoutineConfigSection com configuracao unificada
        (ex: multiplas secoes, loop de dominios, ou selector).
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # 1. Verifica que RoutineConfigSection ainda e usado
    if not re.search(r"RoutineConfigSection\b", content):
        pytest.fail(
            f"AC#4 violada — RED.  'RoutineConfigSection' nao foi "
            f"encontrado em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que a aba config renderizasse "
            f"RoutineConfigSection para configuracao de rotinas."
        )

    # 2. Verifica que NAO e apenas domain='estrategia' fixo —
    #    a config unificada deve referenciar mais de um dominio
    if not re.search(r"RoutineConfigSection.*domain", content):
        # Nao encontrou RoutineConfigSection com domain
        # Pode ser que a interface tenha mudado — verificar se
        # ha multiplas secoes ou alguma indicacao de unificacao
        if re.search(r"domain\s*=\s*['\"]documentos['\"]", content) or \
           re.search(r"domain\s*=\s*['\"]estrategia['\"]", content):
            # Tem domain='documentos' ou 'estrategia' — verificar
            # se ambos estao presentes
            if not (re.search(r"domain\s*=\s*['\"]documentos['\"]", content)
                    and re.search(r"domain\s*=\s*['\"]estrategia['\"]", content)):
                # So tem um dominio — nao esta unificado
                encontrado = "documentos" if re.search(r"domain['\"]*documentos", content) else "estrategia" if re.search(r"domain['\"]*estrategia", content) else "—"
                pytest.fail(
                    f"AC#4 violada — RED.  A config de rotinas ainda "
                    f"usa apenas domain='{encontrado}' fixo em "
                    f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                    f"Era esperado que a config fosse unificada — "
                    f"referenciando ambos os dominios ('documentos' "
                    f"e 'estrategia') ou usando um approach "
                    f"dinamico.\n\n"
                    f"GREEN deve unificar RoutineConfigSection para "
                    f"ambas as salas atuais (DocumentosRoom e "
                    f"EstrategiaRoom)."
                )
        else:
            # Pode ser que tenha mudado de interface — verificar
            # se ha alguma indicacao de config multi-dominio
            if not re.search(r"config.*unif", content, re.IGNORECASE) and \
               not re.search(r"dominio", content, re.IGNORECASE) and \
               not re.search(r"multi", content, re.IGNORECASE):
                pytest.fail(
                    f"AC#4 violada — RED.  A config de rotinas em "
                    f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)} "
                    f"ainda nao parece estar unificada.\n\n"
                    f"Era esperado que a aba config exibisse "
                    f"RoutineConfigSection de forma unificada, "
                    f"nao apenas domain='estrategia' fixo."
                )
    else:
        # Encontrou RoutineConfigSection...domain — verificar se
        # ha mais de um dominio ou domain dinamico
        domain_matches = re.findall(
            r"RoutineConfigSection[^}]*domain\s*=\s*{?['\"]([^'\"]+)['\"]?}?",
            content,
        )
        unique_domains = set(domain_matches)
        if len(unique_domains) <= 1:
            pytest.fail(
                f"AC#4 violada — RED.  RoutineConfigSection ainda usa "
                f"apenas um dominio fixo ({unique_domains}) em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Era esperado configuracao unificada com "
                f"multiplos dominios ('documentos' e 'estrategia')."
            )
