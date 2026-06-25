"""RED test for behavior B-2 — EstrategiaRoom nova estrutura com 4 abas.

GOAL:
    Criar shell da nova sala unificada com sistema de 4 abas:
    Objetivos, Documentos, Conhecimento, Config.

BEHAVIOR:
    B-2 — EstrategiaRoom Nova Estrutura — Shell com 4 abas (Objetivos,
    Documentos, Conhecimento, Config).

    Antes: EstrategiaRoom.tsx tinha type Tab = 'decisoes' | 'analises' |
    'historico' | 'config' com as tabs Decisões, Análises, Histórico, Config.

    Depois (comportamento esperado):
    - type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'
    - 4 abas clicáveis renderizadas: Objetivos, Documentos, Conhecimento, Config
    - Navegação entre abas via useState setTab
    - Estado da aba ativa sincronizado com initialTab via goWithTab

AC (Acceptance Criteria):
    AC#1 — type Tab define os 4 valores: 'objetivos', 'documentos',
            'conhecimento', 'config'
    AC#2 — Template renderiza 4 abas com labels: Objetivos, Documentos,
            Conhecimento, Config
    AC#3 — Navegação entre abas: cada aba tem onClick que chama setTab
    AC#4 — goWithTab sincroniza initialTab da store com estado tab

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO usar fixtures de DB ou rede — teste é pura inspeção de arquivos.
"""

import re
from pathlib import Path

import pytest


# ── Constants: caminhos da interface pública sob teste ──────────────────────

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
        f"O behavior B-2 (EstrategiaRoom 4 abas) exige que este "
        f"arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — type Tab define os 4 novos valores ──────────────────────────


def test_b2_ac1_type_tab_4_novos_valores():
    """AC#1: O type Tab DEVE definir exatamente os 4 valores:
    'objetivos', 'documentos', 'conhecimento', 'config'.

    Antes (RED): type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
    Depois (GREEN): type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # Procura pela definição de type Tab
    tab_match = re.search(
        r"type\s+Tab\s*=\s*([\s\S]*?)(?:;|\n\s*\n)",
        content,
    )
    assert tab_match, (
        f"Pré-condição violada: o type Tab não foi encontrado em "
        f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.  O teste espera "
        f"que exista 'type Tab = ...' definindo os 4 valores."
    )

    tab_type_block = tab_match.group(1)

    # Verifica cada um dos 4 valores esperados
    novos_valores = ["objetivos", "documentos", "conhecimento", "config"]
    for valor in novos_valores:
        if not re.search(rf"['\"]{valor}['\"]", tab_type_block):
            pytest.fail(
                f"AC#1 violada — RED.  O valor '{valor}' NÃO está presente "
                f"no type Tab em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Type Tab atual: {tab_type_block.strip()}\n\n"
                f"Era esperado que type Tab contivesse todos os 4 valores:\n"
                f"  type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'\n\n"
                f"GREEN deve renomear/recriar as tabs do antigo sistema:\n"
                f"  - 'decisoes'/'painel'/'historico' → 'objetivos'\n"
                f"  - 'documentos' → 'documentos'\n"
                f"  - 'base' → 'conhecimento'\n"
                f"  - 'config' → 'config'"
            )

    # Verifica que valores ANTIGOS NÃO estão mais presentes
    valores_antigos = ["decisoes", "analises", "historico", "painel", "base"]
    for antigo in valores_antigos:
        if re.search(rf"['\"]{antigo}['\"]", tab_type_block):
            pytest.fail(
                f"AC#1 violada — RED.  O valor antigo '{antigo}' AINDA está "
                f"presente no type Tab em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Os valores antigos ('decisoes', 'analises', 'historico', "
                f"'painel', 'base') devem ser substituídos pelos novos "
                f"('objetivos', 'documentos', 'conhecimento', 'config')."
            )


# ── AC#2 — Template renderiza 4 abas com labels corretos ────────────────


def test_b2_ac2_4_tabs_renderizadas():
    """AC#2: O template DEVE renderizar 4 abas com os labels:
    Objetivos, Documentos, Conhecimento, Config.

    Antes (RED): tabs 'Decisões', 'Análises', 'Histórico', 'Config'
    Depois (GREEN): tabs 'Objetivos', 'Documentos', 'Conhecimento', 'Config'
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # Procura pelo bloco de tabs (.rtabs)
    rtabs_match = re.search(
        r"className\s*=\s*[\"']rtabs[\"']",
        content,
    )
    assert rtabs_match, (
        f"Pré-condição violada: o container .rtabs não foi encontrado em "
        f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.  O teste espera "
        f"que exista renderização de abas com className 'rtabs'."
    )

    # Verifica cada label renderizado
    labels_esperados = ["Objetivos", "Documentos", "Conhecimento", "Config"]
    for label in labels_esperados:
        if f"'{label}'" not in content and f'"{label}"' not in content:
            pytest.fail(
                f"AC#2 violada — RED.  O label '{label}' NÃO foi encontrado "
                f"no template em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Era esperado que as 4 abas fossem renderizadas como:\n"
                f"  Objetivos | Documentos | Conhecimento | Config\n\n"
                f"GREEN deve substituir os labels antigos:\n"
                f"  'Decisões' → 'Objetivos'\n"
                f"  'Análises' → 'Documentos'\n"
                f"  'Histórico' → 'Conhecimento'\n"
                f"  'Config'  → 'Config'  (mantido)"
            )

    # Verifica que labels antigos NÃO estão presentes
    labels_antigos = ["Decisões", "Análises", "Histórico"]
    for antigo in labels_antigos:
        if f"'{antigo}'" in content or f'"{antigo}"' in content:
            pytest.fail(
                f"AC#2 violada — RED.  O label antigo '{antigo}' AINDA está "
                f"presente no template em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Os labels antigos devem ser substituídos pelos novos: "
                f"'Objetivos', 'Documentos', 'Conhecimento', 'Config'."
            )


# ── AC#3 — Navegação entre abas com setTab ─────────────────────────────


def test_b2_ac3_navegacao_entre_abas():
    """AC#3: Cada aba DEVE ter onClick que chama setTab para navegação,
    usando os NOVOS valores do type Tab ('objetivos', 'documentos',
    'conhecimento', 'config').

    O navegação por abas deve ser via um array/iteração que referencia
    os novos valores Tab, não os antigos ('decisoes', 'analises', 'historico').
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # Verifica que existe um estado 'tab' com setTab
    if not re.search(r"setTab\b", content):
        pytest.fail(
            f"AC#3 violada — RED.  Nenhuma chamada a 'setTab' foi encontrada "
            f"em {ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o componente tivesse um estado 'tab' com "
            f"setTab para controlar qual aba está ativa.\n\n"
            f"GREEN deve ter:\n"
            f"  const [tab, setTab] = useState<Tab>(initialValue)"
        )

    # Verifica que a renderização das tabs referencia os NOVOS valores
    novos_valores = ["objetivos", "documentos", "conhecimento", "config"]
    for valor in novos_valores:
        if f"'{valor}'" not in content and f'"{valor}"' not in content:
            pytest.fail(
                f"AC#3 violada — RED.  O novo valor de aba '{valor}' NÃO "
                f"foi encontrado no template de navegação em "
                f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Era esperado que o array/mapa de navegação usasse os "
                f"novos valores: 'objetivos', 'documentos', 'conhecimento', "
                f"'config'.\n\n"
                f"GREEN deve substituir os valores antigos:\n"
                f"  'decisoes' → 'objetivos'\n"
                f"  'analises' → 'documentos'\n"
                f"  'historico' → 'conhecimento'\n"
                f"  'config'   → 'config' (mantido)"
            )

    # Verifica que valores antigos NÃO estão na renderização de navegação
    valores_antigos = ["decisoes", "analises", "historico"]
    for antigo in valores_antigos:
        if f"'{antigo}'" in content or f'"{antigo}"' in content:
            # Só falha se o valor antigo aparecer no contexto de navegação (.rtabs etc.)
            if re.search(r"rtab", content):
                pytest.fail(
                    f"AC#3 violada — RED.  O valor antigo '{antigo}' AINDA "
                    f"está presente no template de navegação em "
                    f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                    f"Os valores antigos ('decisoes', 'analises', 'historico') "
                    f"devem ser substituídos pelos novos: 'objetivos', "
                    f"'documentos', 'conhecimento'."
                )


# ── AC#4 — goWithTab sincroniza initialTab da store ────────────────────


def test_b2_ac4_gowithtab_integrado():
    """AC#4: goWithTab DEVE sincronizar o initialTab da store com o
    estado local 'tab'.

    A navegação externa via goWithTab deve setar a aba inicial,
    permitindo que links/bookmarks abram em uma aba específica.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    # Verifica que goWithTab é mencionado ou que initialTab é usado
    if not re.search(r"goWithTab\b", content) and \
       not re.search(r"initialTab\b", content):
        pytest.fail(
            f"AC#4 violada — RED.  Nem 'goWithTab' nem 'initialTab' foram "
            f"encontrados em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o componente se integrasse com goWithTab da "
            f"store para permitir navegação entre telas com aba específica.\n\n"
            f"GREEN deve sincronizar o estado local 'tab' com initialTab "
            f"vindo da store (ex: const initialTab = ...)."
        )

    # Verifica que o estado tab é inicializado com initialTab ou goWithTab
    found_initialization = (
        re.search(r"initialTab\b", content) or
        re.search(r"goWithTab\b", content) or
        re.search(r"useState\s*<Tab>\s*\(.*tab.*\)", content)
    )
    if not found_initialization:
        pytest.fail(
            f"AC#4 violada — RED.  Não foi encontrado mecanismo de "
            f"inicialização do estado 'tab' sincronizado com a store em "
            f"{ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Era esperado que o estado 'tab' se inicializasse a partir "
            f"de initialTab ou goWithTab vindos da store "
            f"(useAppStore)."
        )
