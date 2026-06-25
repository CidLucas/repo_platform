"""RED test for behavior B-1 — Remover 'documentos' da Sidebar, Screen types e AppShell.

GOAL:
    Remover o screen "documentos" como rota/tela independente no app blu_v3.
    A funcionalidade de documentos agora vive como aba dentro da sala
    "Estratégia" (EstrategiaRoom), que unifica 4 abas.

BEHAVIOR:
    B-1 — Sidebar + Routing — Remover 'documentos' da Sidebar, Screen types
    e AppShell routing.

    Antes: existia um NavItem { s: 'documentos', icon: <PencilSimpleLine...>,
    label: 'Documentos' } na Sidebar, o union type Screen incluía 'documentos',
    e AppShell.tsx tinha um bloco <div className=screen${on('documentos')}>
    que renderizava DocumentosRoom.

    Depois (comportamento esperado):
    - Sidebar.tsx: NAV_ITEMS NÃO tem entrada com s='documentos'
    - appStore.ts: Screen type NÃO inclui 'documentos'
    - appStore.ts: SCREEN_LABELS NÃO inclui 'documentos'
    - appStore.ts: screenFromHash() redireciona '#room/documentos' → 'estrategia'
    - AppShell.tsx: NÃO importa DocumentosRoom
    - 'biblioteca' permanece nos NAV_ITEMS e Screen type

AC (Acceptance Criteria):
    AC#1 — Sidebar.tsx NÃO contém 'documentos' em NAV_ITEMS
    AC#2 — appStore.ts: 'documentos' NÃO está no union type Screen
    AC#3 — appStore.ts: SCREEN_LABELS NÃO inclui 'documentos'
    AC#4 — appStore.ts: screenFromHash() redireciona '#room/documentos'
           → 'estrategia' (hash legado continua funcional)
    AC#5 — AppShell.tsx NÃO importa DocumentosRoom
    AC#6 — 'biblioteca' permanece no Screen type e NAV_ITEMS da Sidebar

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO usar fixtures de DB ou rede — teste é pura inspeção de arquivos.
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface pública sob teste ──────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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

APPSHELL_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "AppShell.tsx"
)


# ── Override do root conftest (teste puramente estático) ────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção ─────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o arquivo e devolve o conteúdo como string única."""
    assert path.exists(), (
        f"Arquivo não encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-1 (remover rota documentos) exige que este "
        f"arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — Sidebar.tsx: NAV_ITEMS não contém 'documentos' ──────────────


def test_b1_ac1_sidebar_sem_documentos():
    """AC#1: Sidebar.tsx NÃO deve conter entrada com s='documentos'
    em NAV_ITEMS.

    Antes (RED): existia `{ s: 'documentos', icon: <PencilSimpleLine...>,
    label: 'Documentos' }` como quarto item (linha 26~).

    Depois (GREEN): NAV_ITEMS não menciona 'documentos'.
    """
    content = _read_text(SIDEBAR_PATH)

    # Verifica se 'documentos' aparece como screen identifier no array NAV_ITEMS
    padrao_documentos_item = r"""['"']documentos['"']"""

    encontrou = re.search(padrao_documentos_item, content)

    if encontrou:
        pytest.fail(
            "AC#1 violada — RED.  A string 'documentos' ainda aparece "
            f"em {SIDEBAR_PATH.relative_to(REPO_ROOT)} como valor de um "
            f"NavItem (s='documentos').\n\n"
            f"Era esperado que o item 'Documentos' tivesse sido removido "
            f"de NAV_ITEMS, já que a funcionalidade agora vive como aba "
            f"dentro da sala Estratégia (EstrategiaRoom).\n\n"
            f"Localização: linha ~26 do Sidebar.tsx.\n\n"
            f"GREEN deve remover:\n"
            f"  {{ s: 'documentos', icon: <PencilSimpleLine ...>, "
            f"label: 'Documentos' }},\n"
            f"do array NAV_ITEMS."
        )

    # Confirma que a Sidebar ainda existe (arquivo válido)
    assert "NAV_ITEMS" in content, (
        "Pré-condição violada: o array NAV_ITEMS não foi encontrado "
        f"em {SIDEBAR_PATH.relative_to(REPO_ROOT)}.  O teste espera que "
        f"a Sidebar tenha NAV_ITEMS, apenas sem 'documentos'."
    )


# ── AC#2 — appStore.ts: Screen type não inclui 'documentos' ────────────


def test_b1_ac2_appstore_screen_sem_documentos():
    """AC#2: appStore.ts — o union type Screen NÃO deve incluir
    'documentos'.

    Antes (RED): Screen = 'home' | 'compras' | ... | 'documentos' | ...
    Depois (GREEN): Screen = 'home' | 'compras' | ... | 'biblioteca' | ...
    sem 'documentos'.
    """
    content = _read_text(APPSTORE_PATH)

    # Procura pelo union type Screen: começa com "export type Screen =" e
    # lista os valores entre |
    # 'documentos' não deve estar entre os valores
    screen_match = re.search(
        r"export\s+type\s+Screen\s*=",
        content,
    )
    assert screen_match, (
        "Pré-condição violada: o union type 'Screen' não foi encontrado "
        f"em {APPSTORE_PATH.relative_to(REPO_ROOT)}."
    )

    # Pega o bloco do type Screen (até o próximo type ou export)
    screen_block = content[screen_match.start():screen_match.start() + 500]
    # Procura por 'documentos' como um dos valores do union
    if re.search(r"['\"]documentos['\"]", screen_block):
        pytest.fail(
            "AC#2 violada — RED.  O string literal 'documentos' ainda "
            f"aparece como valor do union type Screen em "
            f"{APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que 'documentos' tivesse sido removido do "
            f"type Screen, já que não é mais uma tela independente.\n\n"
            f"GREEN deve remover a linha:\n"
            f"  | 'documentos'\n"
            f"do union type Screen (linha ~8 do appStore.ts)."
        )


# ── AC#3 — appStore.ts: SCREEN_LABELS não inclui 'documentos' ──────────


def test_b1_ac3_appstore_screen_labels_sem_documentos():
    """AC#3: appStore.ts — o dicionário SCREEN_LABELS NÃO deve incluir
    a chave 'documentos'.

    Antes (RED): SCREEN_LABELS = { ..., documentos: 'Documentos', ... }
    Depois (GREEN): SCREEN_LABELS não mapeia 'documentos'.
    """
    content = _read_text(APPSTORE_PATH)

    # Procura pelo dicionário SCREEN_LABELS
    labels_match = re.search(
        r"SCREEN_LABELS\s*:\s*Record\s*<Screen\s*,\s*string>\s*=\s*\{",
        content,
    )
    if not labels_match:
        # Tenta um padrão alternativo
        labels_match = re.search(
            r"const\s+SCREEN_LABELS\b",
            content,
        )

    if labels_match:
        labels_block = content[labels_match.start():labels_match.start() + 500]
        if re.search(r"documentos\s*:", labels_block) or \
           re.search(r"['\"]documentos['\"]", labels_block):
            pytest.fail(
                "AC#3 violada — RED.  A chave 'documentos' ainda está "
                f"presente no dicionário SCREEN_LABELS em "
                f"{APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Era esperado que 'documentos: ...' fosse removido de "
                f"SCREEN_LABELS, já que 'documentos' não é mais uma "
                f"tela independente.\n\n"
                f"GREEN deve remover a entrada 'documentos: ...' do "
                f"dicionário SCREEN_LABELS (linha ~72 do appStore.ts)."
            )


# ── AC#4 — appStore.ts: screenFromHash() redireciona 'documentos' → 'estrategia' ────


def test_b1_ac4_appstore_hash_redirect_documentos_para_estrategia():
    """AC#4: appStore.ts — screenFromHash() DEVE redirecionar o hash
    '#room/documentos' → 'estrategia'.

    Isso garante que bookmarks/links antigos para #/documentos continuem
    funcionando, levando o usuário à sala Estratégia (que agora contém
    a aba Documentos como uma das 4 abas unificadas).
    """
    content = _read_text(APPSTORE_PATH)

    # Procura pela função screenFromHash
    hash_fn = re.search(
        r"function\s+screenFromHash\b",
        content,
    )
    assert hash_fn, (
        "Pré-condição violada: a função 'screenFromHash' não foi "
        f"encontrada em {APPSTORE_PATH.relative_to(REPO_ROOT)}."
    )

    # Pega o bloco da função
    fn_block = content[hash_fn.start():hash_fn.start() + 600]

    # Verifica se existe o redirect de '#room/documentos' → 'estrategia'
    redirect_exists = re.search(
        r"['\"]\#room/documentos['\"]\s*\)?\s*(?:return\s+)?['\"]estrategia['\"]",
        fn_block,
    )

    # Ou padrão: `if (window.location.hash === '#room/documentos') return 'estrategia'`
    simple_redirect = re.search(
        r"documentos.*return.*estrategia",
        fn_block,
    ) or re.search(
        r"estrategia.*documentos",
        fn_block,
    )

    if not (redirect_exists or simple_redirect):
        pytest.fail(
            "AC#4 violada — RED.  A função screenFromHash() NÃO "
            f"redireciona '#room/documentos' → 'estrategia' em "
            f"{APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"O hash legado '#/documentos' (que existia antes da "
            f"remoção) precisa ser redirecionado para 'estrategia', "
            f"já que a sala Estratégia agora unifica 4 abas, incluindo "
            f"a aba de documentos.\n\n"
            f"GREEN deve adicionar em screenFromHash():\n\n"
            f"  if (window.location.hash === '#room/documentos')\n"
            f"    return 'estrategia';"
        )


# ── AC#5 — AppShell.tsx não importa DocumentosRoom ─────────────────────


def test_b1_ac5_appshell_sem_documentos_room():
    """AC#5: AppShell.tsx NÃO deve importar DocumentosRoom.

    Como 'documentos' não é mais uma tela independente, o import de
    DocumentosRoom e seu bloco de renderização devem ter sido removidos
    de AppShell.tsx.
    """
    content = _read_text(APPSHELL_PATH)

    # Procura por import de DocumentosRoom
    if re.search(r"import\s+DocumentosRoom", content):
        pytest.fail(
            "AC#5 violada — RED.  AppShell.tsx ainda importa "
            f"DocumentosRoom em {APPSHELL_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Como 'documentos' não é mais uma tela independente, o "
            f"import de DocumentosRoom deve ser removido do AppShell.\n\n"
            f"GREEN deve remover a linha:\n"
            f"  import DocumentosRoom from '../../pages/app/DocumentosRoom'\n"
            f"do AppShell.tsx."
        )

    # Verifica se também não tem bloco de renderização para documentos
    if re.search(r"screen\$\{on\(['\"]documentos['\"]\)\}", content) or \
       re.search(r"id=[\"']s-documentos[\"']", content):
        pytest.fail(
            "AC#5 violada — RED.  AppShell.tsx ainda contém bloco de "
            f"renderização para 'documentos' em "
            f"{APPSHELL_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"O bloco <div className=screen${{on('documentos')}}> deve "
            f"ser removido, já que 'documentos' não é mais uma tela "
            f"independente."
        )


# ── AC#6 — 'biblioteca' permanece no Screen type e NAV_ITEMS ────────────


def test_b1_ac6_biblioteca_continua_acessivel():
    """AC#6: 'biblioteca' DEVE permanecer acessível — tanto no Screen
    type quanto nos NAV_ITEMS da Sidebar.

    A remoção de 'documentos' não deve afetar 'biblioteca', que continua
    sendo uma tela independente.
    """
    # Verifica appStore.ts
    store_content = _read_text(APPSTORE_PATH)

    # Screen type deve conter 'biblioteca'
    screen_match = re.search(
        r"export\s+type\s+Screen\s*=",
        store_content,
    )
    assert screen_match, (
        "Pré-condição violada: type Screen não encontrado."
    )
    screen_block = store_content[screen_match.start():screen_match.start() + 500]
    if not re.search(r"['\"]biblioteca['\"]", screen_block):
        pytest.fail(
            "AC#6 violada — RED.  O union type Screen NÃO contém "
            f"'biblioteca' em {APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"A remoção de 'documentos' não deve remover 'biblioteca', "
            f"que continua sendo uma tela independente."
        )

    # SCREEN_LABELS deve conter 'biblioteca'
    labels_match = re.search(
        r"SCREEN_LABELS\b",
        store_content,
    )
    if labels_match:
        labels_block = store_content[labels_match.start():labels_match.start() + 500]
        if not re.search(r"\bbiblioteca\b", labels_block):
            pytest.fail(
                "AC#6 violada — RED.  'biblioteca' NÃO está em "
                f"SCREEN_LABELS em {APPSTORE_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Biblioteca deve continuar mapeada em SCREEN_LABELS."
            )

    # Verifica Sidebar.tsx
    sidebar_content = _read_text(SIDEBAR_PATH)

    nav_match = re.search(
        r"const\s+NAV_ITEMS\s*(?::\s*NavItem\[\]\s*)?=\s*\[",
        sidebar_content,
    )
    assert nav_match, (
        "Pré-condição violada: NAV_ITEMS não encontrado na Sidebar."
    )
    nav_block = sidebar_content[nav_match.start():nav_match.start() + 1000]
    if not re.search(r"['\"]biblioteca['\"]", nav_block):
        pytest.fail(
            "AC#6 violada — RED.  'biblioteca' NÃO está nos NAV_ITEMS "
            f"da Sidebar em {SIDEBAR_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Biblioteca deve continuar sendo um item na sidebar "
            "(s: 'biblioteca', icon: <Books ...>, label: 'Biblioteca')."
        )
