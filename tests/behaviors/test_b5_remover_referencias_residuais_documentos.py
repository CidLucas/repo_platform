"""RED test for behavior B-5 — Remover referências residuais a 'documentos' como screen independente.

GOAL:
    Remover todas as referências residuais ao slug 'documentos' como screen/agente
    independente em toda a codebase do blu_v3. A funcionalidade de documentos agora
    vive como aba dentro da sala "Estratégia" (EstrategiaRoom), que unifica 4 abas,
    e portanto não deve mais aparecer como entrada própria em nenhum lugar.

BEHAVIOR:
    B-5 — Referências Residuais — Remover entradas 'documentos' de todos os
    lugares que ainda referenciam o slug como um agente/screen independente.

    Antes: 'documentos' aparecia em DOMAIN_SCREEN, BASE_ITEMS, DecisionCard navigation,
    AdminScreen (AGENT_PROVIDERS, ICONS, NAMES, MAP, domainData, permissoes),
    AtividadeScreen (AGENT_CATALOG), AgentesScreen (AGENT_META), constants (AGENT_COLORS),
    useOnboardingDraft (DEFAULT_AGENTS), e api/documents.ts (createDocument).

    Depois (comportamento esperado):
    - HomePage.tsx: DOMAIN_SCREEN NÃO tem entry 'documentos'
    - SpotlightSearch.tsx: BASE_ITEMS NÃO tem item s='documentos'
    - DecisionCard.tsx: NÃO chama go('documentos', ...)
    - AdminScreen.tsx: AGENT_PROVIDERS, ICONS, NAMES, MAP NÃO contêm 'documentos'
    - AdminScreen.tsx: domainData NÃO usa statusPct('documentos')
    - AdminScreen.tsx: permissoes de agente NÃO lista 'documentos'
    - AtividadeScreen.tsx: AGENT_CATALOG NÃO contém entry 'documentos'
    - AgentesScreen.tsx: AGENT_META NÃO contém key 'documentos' como agente visível
    - utils/constants.ts: AGENT_COLORS NÃO contém 'documentos'
    - useOnboardingDraft.ts: DEFAULT_AGENTS NÃO contém 'documentos'
    - api/documents.ts: createDocument usa agent_slug: 'estrategia'

AC (Acceptance Criteria):
    AC#1 — HomePage.tsx: DOMAIN_SCREEN NÃO contém entry 'documentos'
    AC#2 — SpotlightSearch.tsx: BASE_ITEMS NÃO contém item s='documentos'
    AC#3 — DecisionCard.tsx: NÃO chama go('documentos', ...)
    AC#4 — AdminScreen.tsx: AGENT_PROVIDERS, ICONS, NAMES, MAP NÃO contêm 'documentos'
    AC#5 — AdminScreen.tsx: domainData NÃO usa statusPct('documentos')
    AC#6 — AdminScreen.tsx: permissoes de agente NÃO lista 'documentos'
    AC#7 — AtividadeScreen.tsx: AGENT_CATALOG NÃO contém entry 'documentos'
    AC#8 — AgentesScreen.tsx: AGENT_META NÃO contém key 'documentos'
    AC#9 — utils/constants.ts: AGENT_COLORS NÃO contém 'documentos'
    AC#10 — useOnboardingDraft.ts: DEFAULT_AGENTS NÃO contém 'documentos'
    AC#11 — api/documents.ts: createDocument usa agent_slug: 'estrategia'

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

HOMEPAGE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "HomePage.tsx"
)

SPOTLIGHT_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "SpotlightSearch.tsx"
)

DECISION_CARD_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "DecisionCard.tsx"
)

ADMIN_SCREEN_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AdminScreen.tsx"
)

ATIVIDADE_SCREEN_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AtividadeScreen.tsx"
)

AGENTES_SCREEN_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AgentesScreen.tsx"
)

CONSTANTS_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "utils"
    / "constants.ts"
)

ONBOARDING_DRAFT_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useOnboardingDraft.ts"
)

DOCUMENTS_API_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "documents.ts"
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
        f"O behavior B-5 (remover referências residuais documentos) exige que este "
        f"arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — HomePage.tsx: DOMAIN_SCREEN não contém entry 'documentos' ────


def test_b5_ac1_homepage_domain_screen_sem_documentos():
    """AC#1: HomePage.tsx — DOMAIN_SCREEN NÃO deve conter entrada com
    a chave 'documentos'.

    Antes (RED): linha 29 tem
      documentos: { screen: 'documentos', label: 'Documentos' },

    Depois (GREEN): DOMAIN_SCREEN não menciona 'documentos'.
    """
    content = _read_text(HOMEPAGE_PATH)

    # Procura pela chave 'documentos' dentro do bloco DOMAIN_SCREEN
    # O bloco começa com "export const DOMAIN_SCREEN" ou similar
    domain_match = re.search(
        r"DOMAIN_SCREEN\s*(?::\s*Record\s*<[^>]*>\s*)?=\s*\{",
        content,
    )
    assert domain_match, (
        "Pré-condição violada: o objeto DOMAIN_SCREEN não foi encontrado "
        f"em {HOMEPAGE_PATH.relative_to(REPO_ROOT)}."
    )

    domain_block = content[domain_match.start() : domain_match.start() + 600]

    # Verifica se 'documentos:' aparece como chave no bloco
    padrao_chave_documentos = r"\bdocumentos\s*:"
    if re.search(padrao_chave_documentos, domain_block):
        pytest.fail(
            "AC#1 violada — RED.  A chave 'documentos' ainda aparece "
            f"no objeto DOMAIN_SCREEN em {HOMEPAGE_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linha atual (RED):\n"
            f"  documentos: {{ screen: 'documentos', label: 'Documentos' }},\n\n"
            f"Esperado (GREEN): a entrada inteira deve ser removida, já que "
            f"'documentos' não é mais um screen/agente independente — a "
            f"funcionalidade agora vive como aba dentro da sala Estratégia."
        )

    # Confirma que DOMAIN_SCREEN ainda existe (arquivo válido)
    assert "DOMAIN_SCREEN" in content, (
        "Pré-condição violada: DOMAIN_SCREEN não encontrado "
        f"em {HOMEPAGE_PATH.relative_to(REPO_ROOT)}."
    )


# ── AC#2 — SpotlightSearch.tsx: BASE_ITEMS não contém s='documentos' ────


def test_b5_ac2_spotlight_base_items_sem_documentos():
    """AC#2: SpotlightSearch.tsx — BASE_ITEMS NÃO deve conter item com
    s='documentos'.

    Antes (RED): linha 18 tem
      { s: 'documentos', label: 'Documentos', desc: ... , icon: '📝' },

    Depois (GREEN): BASE_ITEMS não menciona 'documentos'.
    """
    content = _read_text(SPOTLIGHT_PATH)

    # Procura pelo array BASE_ITEMS
    base_items_match = re.search(
        r"BASE_ITEMS\s*(?::\s*[A-Za-z[\]\s]*\s*)?=\s*\[",
        content,
    )
    assert base_items_match, (
        "Pré-condição violada: o array BASE_ITEMS não foi encontrado "
        f"em {SPOTLIGHT_PATH.relative_to(REPO_ROOT)}."
    )

    items_block = content[base_items_match.start() : base_items_match.start() + 1000]

    # Verifica se existe um item com s: 'documentos'
    padrao_item_documentos = r"""['"]documentos['"]"""
    if re.search(padrao_item_documentos, items_block):
        pytest.fail(
            "AC#2 violada — RED.  A string 'documentos' ainda aparece "
            f"como valor de 's' em um item do array BASE_ITEMS em "
            f"{SPOTLIGHT_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linha atual (RED):\n"
            f"  {{ s: 'documentos', label: 'Documentos', desc: ..., icon: '📝' }},\n\n"
            f"Esperado (GREEN): o item 'documentos' deve ser removido de "
            f"BASE_ITEMS, já que não é mais um agente/screen independente."
        )


# ── AC#3 — DecisionCard.tsx: não chama go('documentos', ...) ────────────


def test_b5_ac3_decision_card_sem_go_documentos():
    """AC#3: DecisionCard.tsx — NÃO deve conter chamada a go('documentos', ...).

    Antes (RED): linhas 157 e 188 têm
      go('documentos', 'Documentos')

    Depois (GREEN): deve ser substituído por
      go('estrategia', 'Estratégia')
    """
    content = _read_text(DECISION_CARD_PATH)

    # Procura pelo padrão go('documentos', ...)
    padrao_go_documentos = r"""go\s*\(\s*['"]documentos['"]"""
    if re.search(padrao_go_documentos, content):
        pytest.fail(
            "AC#3 violada — RED.  A função go('documentos', ...) ainda é "
            f"chamada em {DECISION_CARD_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linhas atuais (RED):\n"
            f"  go('documentos', 'Documentos') nas linhas ~157 e ~188\n\n"
            f"Esperado (GREEN): substituir ambas por:\n"
            f"  go('estrategia', 'Estratégia')\n\n"
            f"Já que a funcionalidade de documentos agora faz parte da "
            f"sala Estratégia (EstrategiaRoom), o clique no card deve "
            f"navegar para 'estrategia' em vez de 'documentos'."
        )

    # Verifica também a chave 'documentos:' no mapeamento de nomes (linha ~17)
    padrao_key_documentos = r"\bdocumentos\s*:\s*['\"]Documentos['\"]"
    if re.search(padrao_key_documentos, content):
        pytest.fail(
            "AC#3 violada — RED (adicional).  O mapeamento "
            f"'documentos: 'Documentos'' ainda existe no início de "
            f"{DECISION_CARD_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Esperado (GREEN): remover a entrada 'documentos: 'Documentos',' "
            f"do mapeamento de nomes de agente (~linha 17)."
        )


# ── AC#4 — AdminScreen.tsx: AGENT_PROVIDERS, ICONS, NAMES, MAP sem 'documentos' ────


def test_b5_ac4_admin_screen_sem_documentos():
    """AC#4: AdminScreen.tsx — AGENT_PROVIDERS, ICONS, NAMES e MAP
    NÃO devem conter entrada com chave 'documentos'.

    Antes (RED): linhas 154, 162, 165, 182 têm entradas 'documentos'.

    Depois (GREEN): todas as quatro estruturas não mencionam 'documentos'.
    """
    content = _read_text(ADMIN_SCREEN_PATH)

    # AGENT_PROVIDERS: procura por 'documentos:' como chave
    if re.search(r"\bdocumentos\s*:", content):
        pytest.fail(
            "AC#4 violada — RED.  A chave 'documentos:' ainda aparece "
            f"em {ADMIN_SCREEN_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Entradas atuais (RED):\n"
            f"  AGENT_PROVIDERS['documentos'] (linha ~154)\n"
            f"  ICONS['documentos'] (linha ~162)\n"
            f"  NAMES['documentos'] (linha ~165)\n"
            f"  MAP['documentos'] (linha ~182)\n\n"
            f"Esperado (GREEN): remover todas as quatro entradas com "
            f"chave 'documentos' destes objetos/dicionários, já que "
            f"'documentos' não é mais um agente/screen independente."
        )


# ── AC#5 — AdminScreen.tsx: domainData não usa statusPct('documentos') ──


def test_b5_ac5_admin_screen_domain_data_sem_documentos():
    """AC#5: AdminScreen.tsx — domainData NÃO deve usar statusPct('documentos').

    Antes (RED): linha 460 tem
      statusPct('documentos')

    Depois (GREEN): o cálculo de Operações (ou qualquer domainData) não
    deve incluir statusPct('documentos').
    """
    content = _read_text(ADMIN_SCREEN_PATH)

    # Procura pelo bloco domainData
    domain_data_match = re.search(
        r"const\s+domainData\s*(?::\s*[A-Za-z[\]{}\s]*\s*)?=\s*\[",
        content,
    )
    if not domain_data_match:
        # Tenta padrão alternativo
        domain_data_match = re.search(
            r"domainData\s*=\s*\[",
            content,
        )

    if domain_data_match:
        domain_data_block = content[domain_data_match.start() : domain_data_match.start() + 800]

        padrao_status_pct = r"""statusPct\s*\(\s*['"]documentos['"]\s*\)"""
        if re.search(padrao_status_pct, domain_data_block):
            pytest.fail(
                "AC#5 violada — RED.  statusPct('documentos') ainda é "
                f"usado no cálculo de domainData em "
                f"{ADMIN_SCREEN_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Linha atual (RED):\n"
                f"  statusPct('documentos') no cálculo de Operações (linha ~460)\n\n"
                f"Esperado (GREEN): remover statusPct('documentos') do cálculo, "
                f"já que 'documentos' não é mais um agente independente."
            )

    # Segurança: verifica também se 'documentos' aparece como string literal
    # no contexto de domainData (mesmo sem domainData_match)
    padrao_literal_domain = r"""['"]documentos['"]"""
    if re.search(padrao_literal_domain, content):
        # Verifica se está associado a domainData ou statusPct
        for m in re.finditer(re.escape("'documentos'"), content):
            start = max(0, m.start() - 200)
            snippet = content[start : m.end() + 50]
            if "statusPct" in snippet or "domainData" in snippet or "domain" in snippet.lower():
                pytest.fail(
                    "AC#5 violada — RED.  A string 'documentos' aparece em "
                    f"um contexto relacionado a domainData em "
                    f"{ADMIN_SCREEN_PATH.relative_to(REPO_ROOT)}, posição ~{m.start()}.\n\n"
                    f"O esperado (GREEN) é que nenhum cálculo de domainData "
                    f"referencie 'documentos'."
                )


# ── AC#6 — AdminScreen.tsx: permissoes de agente não lista 'documentos' ─


def test_b5_ac6_admin_screen_agent_permissions_sem_documentos():
    """AC#6: AdminScreen.tsx — a lista de agentes nas permissões NÃO deve
    conter 'documentos'.

    Antes (RED): linha 567 tem
      ['compras', 'financeiro', 'agenda', 'documentos', 'estrategia', 'clientes']

    Depois (GREEN): 'documentos' é removido da lista.
    """
    content = _read_text(ADMIN_SCREEN_PATH)

    # Procura pelo padrão de array de agentes nas permissões
    # Tem que ser 'documentos' como elemento de um array com outros slugs
    # Vamos procurar pelo padrão que inclui 'compras', 'financeiro', etc.
    padrao_perm_array = r"""\[\s*['"]compras['"]\s*,\s*['"]financeiro['"]"""
    perm_match = re.search(padrao_perm_array, content)

    if perm_match:
        perm_block = content[perm_match.start() : perm_match.start() + 400]

        if re.search(r"""['"]documentos['"]""", perm_block):
            pytest.fail(
                "AC#6 violada — RED.  A string 'documentos' ainda está "
                f"presente no array de permissões de agente em "
                f"{ADMIN_SCREEN_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Linha atual (RED):\n"
                f"  ['compras', 'financeiro', 'agenda', 'documentos', 'estrategia', 'clientes']\n\n"
                f"Esperado (GREEN): remover 'documentos' do array:\n"
                f"  ['compras', 'financeiro', 'agenda', 'estrategia', 'clientes']"
            )

    # Fallback: procura por 'documentos' em qualquer array com .map(agent =>
    # que é o padrão usado na renderização de permissões
    for m in re.finditer(r"""['"]documentos['"]""", content):
        start = max(0, m.start() - 100)
        snippet = content[start : m.end() + 100]
        if ".map" in snippet and "permissions" in snippet.lower():
            pytest.fail(
                "AC#6 violada — RED.  'documentos' aparece em um array "
                f"mapeado com .map() no contexto de permissões em "
                f"{ADMIN_SCREEN_PATH.relative_to(REPO_ROOT)}, posição ~{m.start()}.\n\n"
                f"Esperado (GREEN): remover 'documentos' da lista de agentes "
                f"nas permissões de usuário."
            )


# ── AC#7 — AtividadeScreen.tsx: AGENT_CATALOG sem 'documentos' ──────────


def test_b5_ac7_atividade_screen_sem_documentos():
    """AC#7: AtividadeScreen.tsx — AGENT_CATALOG NÃO deve conter entry
    com slug: 'documentos'.

    Antes (RED): linha 15 tem
      { slug: 'documentos', icon: '✍️', name: 'Documentos', color: '#f472b6' }

    Depois (GREEN): AGENT_CATALOG não contém entry 'documentos'.
    """
    content = _read_text(ATIVIDADE_SCREEN_PATH)

    # Procura pelo array AGENT_CATALOG
    catalog_match = re.search(
        r"AGENT_CATALOG\s*(?::\s*[A-Za-z[\]{}\s]*\s*)?=\s*\[",
        content,
    )
    if not catalog_match:
        # Tenta padrão alternativo
        catalog_match = re.search(
            r"const\s+\w+\s*=\s*\[\s*\{?\s*slug\s*:",
            content,
        )

    assert catalog_match, (
        "Pré-condição violada: AGENT_CATALOG não foi encontrado "
        f"em {ATIVIDADE_SCREEN_PATH.relative_to(REPO_ROOT)}."
    )

    catalog_block = content[catalog_match.start() : catalog_match.start() + 800]

    # Verifica se existe um objeto com slug: 'documentos'
    padrao_slug_documentos = r"""slug\s*:\s*['"]documentos['"]"""
    if re.search(padrao_slug_documentos, catalog_block):
        pytest.fail(
            "AC#7 violada — RED.  A entry com slug: 'documentos' ainda "
            f"existe em AGENT_CATALOG em "
            f"{ATIVIDADE_SCREEN_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linha atual (RED):\n"
            f"  {{ slug: 'documentos', icon: '✍️', name: 'Documentos', color: '#f472b6' }},\n\n"
            f"Esperado (GREEN): remover a entry de 'documentos' de "
            f"AGENT_CATALOG, já que não é mais um agente independente."
        )


# ── AC#8 — AgentesScreen.tsx: AGENT_META sem 'documentos' como key ──────


def test_b5_ac8_agentes_screen_sem_documentos_visivel():
    """AC#8: AgentesScreen.tsx — AGENT_META NÃO deve conter a chave
    'documentos' como agente visível.

    Antes (RED): linhas 32-36 têm
      documentos: {
        icon: '✍️',
        color: '#f472b6',
        description: 'Cria, revisa e organiza documentos...',
      },

    Depois (GREEN): AGENT_META não tem entry 'documentos' como agente visível.
    """
    content = _read_text(AGENTES_SCREEN_PATH)

    # Procura pelo bloco AGENT_META
    meta_match = re.search(
        r"AGENT_META\s*(?::\s*Record\s*<[^>]*>\s*)?=\s*\{",
        content,
    )
    assert meta_match, (
        "Pré-condição violada: AGENT_META não foi encontrado "
        f"em {AGENTES_SCREEN_PATH.relative_to(REPO_ROOT)}."
    )

    meta_block = content[meta_match.start() : meta_match.start() + 800]

    # Verifica se 'documentos:' aparece como chave no bloco AGENT_META
    padrao_key_documentos = r"\bdocumentos\s*:"
    if re.search(padrao_key_documentos, meta_block):
        pytest.fail(
            "AC#8 violada — RED.  A entry 'documentos' ainda está presente "
            f"em AGENT_META em {AGENTES_SCREEN_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Bloco atual (RED):\n"
            f"  documentos: {{\n"
            f"    icon: '✍️',\n"
            f"    color: '#f472b6',\n"
            f"    description: 'Cria, revisa e organiza documentos...',\n"
            f"  }},\n\n"
            f"Esperado (GREEN): remover a entry 'documentos' de AGENT_META, "
            f"já que 'documentos' não é mais um agente visível. Pode ser "
            f"mantido apenas como background/oculto se for necessário, "
            f"mas não como entrada direta em AGENT_META."
        )


# ── AC#9 — utils/constants.ts: AGENT_COLORS sem 'documentos' ────────────


def test_b5_ac9_constants_sem_documentos():
    """AC#9: utils/constants.ts — AGENT_COLORS NÃO deve conter a chave
    'documentos'.

    Antes (RED): linha 6 tem
      documentos: '#2dd4bf',

    Depois (GREEN): AGENT_COLORS não mapeia 'documentos'.
    """
    content = _read_text(CONSTANTS_PATH)

    # Procura pelo objeto AGENT_COLORS
    colors_match = re.search(
        r"AGENT_COLORS\s*(?::\s*Record\s*<[^>]*>\s*)?=\s*\{",
        content,
    )
    if not colors_match:
        # Tenta padrão mais flexível
        colors_match = re.search(
            r"export\s+(const\s+)?\w*COLORS?\w*\s*(?::\s*[A-Za-z<>[\]{}\s,]*\s*)?=\s*\{",
            content,
        )

    if colors_match:
        colors_block = content[colors_match.start() : colors_match.start() + 500]

        padrao_key_documentos = r"\bdocumentos\s*:"
        if re.search(padrao_key_documentos, colors_block):
            pytest.fail(
                "AC#9 violada — RED.  A chave 'documentos:' ainda está "
                f"presente em AGENT_COLORS em "
                f"{CONSTANTS_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Linha atual (RED):\n"
                f"  documentos: '#2dd4bf',\n\n"
                f"Esperado (GREEN): remover a entrada 'documentos: '#2dd4bf'' "
                f"de AGENT_COLORS, já que 'documentos' não é mais um "
                f"agente/screen independente."
            )
    else:
        # Fallback: procura diretamente por 'documentos:' no arquivo
        if re.search(r"\bdocumentos\s*:", content):
            pytest.fail(
                "AC#9 violada — RED.  A string 'documentos:' aparece "
                f"em {CONSTANTS_PATH.relative_to(REPO_ROOT)}.\n\n"
                f"Esperado (GREEN): remover a entrada 'documentos: ...' "
                f"do objeto de constantes."
            )


# ── AC#10 — useOnboardingDraft.ts: DEFAULT_AGENTS sem 'documentos' ──────


def test_b5_ac10_onboarding_draft_sem_documentos():
    """AC#10: useOnboardingDraft.ts — DEFAULT_AGENTS NÃO deve conter
    'documentos'.

    Antes (RED): linha 39 tem
      const DEFAULT_AGENTS = ['compras', 'financeiro', 'clientes', 'agenda', 'documentos', 'estrategia']

    Depois (GREEN): DEFAULT_AGENTS não lista 'documentos'.
    """
    content = _read_text(ONBOARDING_DRAFT_PATH)

    # Procura pelo array DEFAULT_AGENTS
    agents_match = re.search(
        r"DEFAULT_AGENTS\s*(?::\s*string\[\]\s*)?=\s*\[",
        content,
    )
    assert agents_match, (
        "Pré-condição violada: DEFAULT_AGENTS não foi encontrado "
        f"em {ONBOARDING_DRAFT_PATH.relative_to(REPO_ROOT)}."
    )

    agents_block = content[agents_match.start() : agents_match.start() + 400]

    # Verifica se 'documentos' aparece como elemento do array
    padrao_documentos = r"""['"]documentos['"]"""
    if re.search(padrao_documentos, agents_block):
        pytest.fail(
            "AC#10 violada — RED.  A string 'documentos' ainda está "
            f"presente no array DEFAULT_AGENTS em "
            f"{ONBOARDING_DRAFT_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linha atual (RED):\n"
            f"  const DEFAULT_AGENTS = ['compras', 'financeiro', 'clientes', 'agenda', 'documentos', 'estrategia']\n\n"
            f"Esperado (GREEN): remover 'documentos' do array:\n"
            f"  const DEFAULT_AGENTS = ['compras', 'financeiro', 'clientes', 'agenda', 'estrategia']"
        )


# ── AC#11 — api/documents.ts: createDocument usa agent_slug: 'estrategia' ──


def test_b5_ac11_documents_api_create_uses_estrategia():
    """AC#11: api/documents.ts — createDocument DEVE usar
    agent_slug: 'estrategia', NÃO agent_slug: 'documentos'.

    Antes (RED): linha 86 tem
      agent_slug: 'documentos',

    Depois (GREEN): createDocument usa agent_slug: 'estrategia'.
    """
    content = _read_text(DOCUMENTS_API_PATH)

    # Procura pela função createDocument
    create_fn_match = re.search(
        r"(export\s+)?(async\s+)?function\s+createDocument\b",
        content,
    )
    if not create_fn_match:
        # Tenta encontrar arrow function
        create_fn_match = re.search(
            r"(export\s+)?const\s+createDocument\s*=",
            content,
        )

    assert create_fn_match, (
        "Pré-condição violada: a função/const createDocument não foi "
        f"encontrada em {DOCUMENTS_API_PATH.relative_to(REPO_ROOT)}."
    )

    fn_block = content[create_fn_match.start() : create_fn_match.start() + 1000]

    # Verifica se agent_slug: 'documentos' aparece no bloco da função
    padrao_slug_documentos = r"""agent_slug\s*:\s*['"]documentos['"]"""
    if re.search(padrao_slug_documentos, fn_block):
        pytest.fail(
            "AC#11 violada — RED.  A função createDocument ainda usa "
            f"agent_slug: 'documentos' em "
            f"{DOCUMENTS_API_PATH.relative_to(REPO_ROOT)}.\n\n"
            f"Linha atual (RED):\n"
            f"  agent_slug: 'documentos',\n\n"
            f"Esperado (GREEN): alterar para:\n"
            f"  agent_slug: 'estrategia',\n\n"
            f"Já que a funcionalidade de documentos agora vive como aba "
            f"dentro da sala Estratégia (EstrategiaRoom), novos documentos "
            f"devem ser criados com agent_slug 'estrategia'."
        )

    # Verificação adicional: confirma que agent_slug: 'documentos' não aparece
    # em nenhum lugar do arquivo (não só em createDocument)
    if re.search(padrao_slug_documentos, content):
        pytest.fail(
            "AC#11 violada — RED (adicional).  agent_slug: 'documentos' "
            f"aparece em {DOCUMENTS_API_PATH.relative_to(REPO_ROOT)} fora "
            f"ou dentro de createDocument.\n\n"
            f"Todas as referências a agent_slug: 'documentos' neste arquivo "
            f"devem ser alteradas para 'estrategia', já que 'documentos' "
            f"não é mais um agente independente."
        )
