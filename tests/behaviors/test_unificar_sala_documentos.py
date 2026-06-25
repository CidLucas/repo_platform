"""RED test — Atualizar FEATURE_MAP, rotinas e docs para sala unificada.

GOAL:
    Validar que o Feature Map, sistema de rotinas e documentação foram
    atualizados para refletir a sala unificada. A feature `documentos` deve
    ser mesclada em `estrategia` no Feature Map, e a doc do produto/blu_app
    deve refletir a unificação (Documentos como aba dentro de Estratégia).

BEHAVIOR:
    "Atualizar Feature Map, sistema de rotinas e documentação para refletir
    a sala unificada. A feature `documentos` deve ser mesclada em `estrategia`
    no Feature Map, e a doc do produto/blu_app deve refletir a unificação."

    Arquivos afetados (estado BEFORE — nenhuma alteração feita ainda):
        - docs/llm_wiki/FEATURE_MAP.md:
            linha 61:  `documentos` como feature independente em SME
            linha 162: seção #### documentos com agents/skills/tools próprios
            linha 215: seção #### estrategia com agents/skills/tools próprios
        - docs/system_reference/FEATURE_MAP.md:
            mesma estrutura: documentos separado de estrategia
        - docs/blu_app/blu_app_concept.md:
            linha 36: "Biblioteca" como sala independente (/app/biblioteca)
            linha 35: "Estratégia" não menciona aba de documentos
        - apps/blu_v3/src/pages/app/EstrategiaRoom.tsx:
            linha 332: <RoutineConfigSection domain="estrategia" />
            NÃO possui <RoutineConfigSection domain="documentos" />
        - apps/blu_v3/src/pages/app/DocumentosRoom.tsx:
            existe como componente independente (~526 linhas)

    Após a fase GREEN (implementação):
        1. FEATURE_MAP llm_wiki: `documentos` não é mais feature independente
           no nível SME; seus agents/skills/tools foram absorvidos por
           `estrategia` OU `documentos` aparece como sub-feature/anotação
           dentro de `estrategia`
        2. FEATURE_MAP system_reference: mesma validação
        3. blu_app_concept.md: "Biblioteca" não aparece como sala independente;
           Estratégia menciona que inclui aba de Documentos
        4. EstrategiaRoom.tsx: passou a renderizar
           <RoutineConfigSection domain="documentos" />
        5. DocumentosRoom.tsx: removido OU convertido em redirect

AC (Acceptance Criteria):
    AC#1 — FEATURE_MAP llm_wiki: feature `documentos` absorvida por `estrategia`
    AC#2 — FEATURE_MAP system_reference: feature `documentos` absorvida
    AC#3 — blu_app_concept.md: Biblioteca não é sala independente
    AC#4 — EstrategiaRoom.tsx: renderiza <RoutineConfigSection domain="documentos" />
    AC#5 — DocumentosRoom.tsx: removido ou convertido em redirect

Estado atual: RED — todas as ACs violadas porque nenhuma alteração foi feita
no código de produção. Cada teste falha com AssertionError detalhado em
pt-BR explicando o que está faltando.

Anti-Goals:
    1. NÃO usar mocks, Supabase, browser testing — só source-inspection.
    2. NÃO modificar produção — só escrever testes que comprovam o gap.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent.parent
LLM_WIKI_FM = REPO / "docs" / "llm_wiki" / "FEATURE_MAP.md"
SYS_REF_FM = REPO / "docs" / "system_reference" / "FEATURE_MAP.md"
BLU_APP_CONCEPT = REPO / "docs" / "blu_app" / "blu_app_concept.md"
ESTRATEGIA_ROOM = REPO / "apps" / "blu_v3" / "src" / "pages" / "app" / "EstrategiaRoom.tsx"
DOCUMENTOS_ROOM = REPO / "apps" / "blu_v3" / "src" / "pages" / "app" / "DocumentosRoom.tsx"


# ── Helpers ──────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    assert path.exists(), f"Arquivo não encontrado: {path}"
    return path.read_text(encoding="utf-8")


def feature_table_has_independent_documentos(content: str) -> bool:
    """Checa se a tabela de features (matriz Tier) ainda lista `documentos`
    como linha independente."""
    # A tabela tem formato: | `documentos` | — | — | ✓ | ✓ | ✓ | ✓ |
    return bool(re.search(r'^\|\s*`documentos`\s*\|', content, re.MULTILINE))


def has_estrategia_with_documentos_agents(content: str) -> bool:
    """Checa se a seção `estrategia` menciona agents de documentos
    (context-gatherer, doc-writer) ou se tem anotação sobre sub-feature."""
    # Pega o bloco entre '#### estrategia' e o próximo '####'
    m = re.search(
        r'####\s+estrategia\b.*?(?=####|\Z)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return False
    block = m.group()
    # Deve mencionar context-gatherer OU doc-writer OU 'documentos' como sub
    has_doc_mentions = (
        'context-gatherer' in block or 'doc-writer' in block or 'documentos' in block
    )
    return has_doc_mentions


def documentos_section_still_independent(content: str) -> bool:
    """Checa se ainda existe a seção #### documentos como feature independente
    (não dentro de estrategia). Pode ter backticks: `documentos` ou não."""
    return bool(re.search(
        r'^####\s+`?documentos`?\s*$', content, re.MULTILINE
    ))


def blu_app_has_biblioteca_as_room(content: str) -> bool:
    """Checa se a tabela de salas em blu_app_concept.md ainda lista
    Biblioteca como sala independente."""
    # Tabela de salas: linhas com | Nome | /app/... | agente | ...
    return bool(re.search(r'Biblioteca\s*\|\s*`/app/biblioteca`', content))


def blu_app_estrategia_mentions_documentos(content: str) -> bool:
    """Checa se a linha da Estratégia na tabela menciona aba de Documentos."""
    # Linha: | Estratégia | /app/estrategia | strategy + data-analyst | ...
    m = re.search(r'Estratégia.*?\|.*?`/app/estrategia`.*?\|(.*?)\|', content)
    if not m:
        return False
    desc = m.group(1)
    return 'documentos' in desc.lower() or 'Documentos' in desc


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def llm_wiki_fm() -> str:
    return read(LLM_WIKI_FM)


@pytest.fixture(scope="module")
def sys_ref_fm() -> str:
    return read(SYS_REF_FM)


@pytest.fixture(scope="module")
def blu_app() -> str:
    return read(BLU_APP_CONCEPT)


@pytest.fixture(scope="module")
def estrategia_room() -> str:
    return read(ESTRATEGIA_ROOM)


# ── Tests ────────────────────────────────────────────────────────────────


class TestAC1_FeatureMapLlmWiki:
    """AC#1 — FEATURE_MAP llm_wiki: feature `documentos` absorvida por `estrategia`."""

    def test_documentos_not_independent_feature_in_table(self, llm_wiki_fm: str) -> None:
        """`documentos` não deve aparecer como linha independente na matriz
        Tier da llm_wiki/FEATURE_MAP.md."""
        assert not feature_table_has_independent_documentos(llm_wiki_fm), (
            "FEATURE_MAP llm_wiki: feature `documentos` ainda aparece como "
            "linha independente na matriz Tier→Features (linha 61). "
            "Deveria ter sido absorvida por `estrategia` ou removida da tabela. "
            "A sala unificada requer que Documentos seja aba dentro de "
            "Estratégia, não feature independente no nível SME."
        )

    def test_documentos_section_not_independent(self, llm_wiki_fm: str) -> None:
        """Seção `#### documentos` não deve existir como feature independente."""
        assert not documentos_section_still_independent(llm_wiki_fm), (
            "FEATURE_MAP llm_wiki: a seção `#### documentos` (linha 162) "
            "ainda existe como definição de feature independente. Deveria ter "
            "sido removida OU seus agents/skills/tools movidos para dentro de "
            "`estrategia` como sub-feature/anotação."
        )

    def test_estrategia_includes_documentos_agents(self, llm_wiki_fm: str) -> None:
        """Seção `estrategia` deve mencionar agents de documentos ou sub-feature."""
        assert has_estrategia_with_documentos_agents(llm_wiki_fm), (
            "FEATURE_MAP llm_wiki: a seção `#### estrategia` não menciona "
            "context-gatherer, doc-writer ou 'documentos' como sub-feature. "
            "Com a unificação, os agents de documentos agora servem a sala "
            "Estratégia e devem estar refletidos na definição da feature."
        )

    def test_agent_feature_map_reflects_migration(self, llm_wiki_fm: str) -> None:
        """Mapa Agente→Features (seção de features que habilitam cada agente)
        deve refletir que doc-writer agora serve estrategia."""
        # A seção tem formato: || [[entities/doc-writer]] | features... ||
        doc_writer_row = re.search(
            r'\|\s*\[\[entities/doc-writer\]\].*?\|',
            llm_wiki_fm,
        )
        assert doc_writer_row is not None, (
            "FEATURE_MAP llm_wiki: não foi encontrada a linha do doc-writer "
            "no mapa Agente→Features. O arquivo pode ter sido reestruturado."
        )
        assert 'estrategia' in doc_writer_row.group(), (
            "FEATURE_MAP llm_wiki: o agente doc-writer não lista `estrategia` "
            "entre suas features habilitantes. Com a unificação, doc-writer "
            "agora serve a sala Estratégia."
        )


class TestAC2_FeatureMapSystemReference:
    """AC#2 — FEATURE_MAP system_reference: feature `documentos` absorvida."""

    def test_documentos_not_independent_in_sys_ref(self, sys_ref_fm: str) -> None:
        """`documentos` não deve ser feature independente no system_reference."""
        assert not re.search(
            r'^####\s+`?documentos`?\s*$', sys_ref_fm, re.MULTILINE
        ), (
            "FEATURE_MAP system_reference: a seção `#### documentos` ainda "
            "existe como definição independente. Deveria ter sido removida "
            "ou seus conteúdos movidos para `estrategia`."
        )

    def test_estrategia_has_docs_in_sys_ref(self, sys_ref_fm: str) -> None:
        """Seção `estrategia` no system_reference deve absorver documentos."""
        assert has_estrategia_with_documentos_agents(sys_ref_fm), (
            "FEATURE_MAP system_reference: a seção `#### estrategia` não "
            "menciona context-gatherer, doc-writer ou 'documentos'. Após a "
            "unificação, os recursos de documentos devem estar refletidos "
            "na definição de estrategia."
        )


class TestAC3_BluAppConcept:
    """AC#3 — blu_app_concept.md: Biblioteca não é sala independente."""

    def test_biblioteca_not_independent_room(self, blu_app: str) -> None:
        """Biblioteca não deve aparecer como sala independente na tabela."""
        assert not blu_app_has_biblioteca_as_room(blu_app), (
            "blu_app_concept.md: 'Biblioteca' ainda aparece como sala "
            "independente na tabela de salas (linha 36). Com a unificação, "
            "a sala de documentos/Biblioteca foi removida — ela agora é uma "
            "aba dentro da sala Estratégia. A tabela deve ser atualizada "
            "para remover a linha da Biblioteca e adicionar uma nota na "
            "linha da Estratégia."
        )

    def test_estrategia_mentions_documentos_tab(self, blu_app: str) -> None:
        """Linha da Estratégia na tabela deve mencionar a aba de Documentos."""
        assert blu_app_estrategia_mentions_documentos(blu_app), (
            "blu_app_concept.md: a sala 'Estratégia' não menciona que inclui "
            "uma aba de Documentos. A descrição da sala deve ser atualizada "
            "para refletir que, além dos padrões ocultos e análise "
            "competitiva, a sala agora tem uma aba de Documentos com "
            "doc-writer e context-gatherer."
        )


class TestAC4_EstrategiaRoomRoutineConfig:
    """AC#4 — EstrategiaRoom.tsx renderiza RoutineConfigSection domain='documentos'."""

    def test_has_routine_config_documentos(self, estrategia_room: str) -> None:
        """EstrategiaRoom.tsx deve ter <RoutineConfigSection domain='documentos' />."""
        has_docs_domain = bool(
            re.search(
                r'RoutineConfigSection\s+domain\s*=\s*["\']documentos["\']',
                estrategia_room,
            )
        )
        assert has_docs_domain, (
            "EstrategiaRoom.tsx: não foi encontrado "
            "<RoutineConfigSection domain=\"documentos\" /> no componente. "
            "Como a sala unificada agora inclui a aba de Documentos, as "
            "rotinas de documentos (domain='documentos') precisam ser "
            "renderizadas na configuração da EstrategiaRoom, mantendo "
            "também domain='estrategia' para rotinas de estratégia."
        )

    def test_also_has_routine_config_estrategia(self, estrategia_room: str) -> None:
        """EstrategiaRoom.tsx deve manter <RoutineConfigSection domain='estrategia' />."""
        has_est_domain = bool(
            re.search(
                r'RoutineConfigSection\s+domain\s*=\s*["\']estrategia["\']',
                estrategia_room,
            )
        )
        assert has_est_domain, (
            "EstrategiaRoom.tsx: <RoutineConfigSection domain=\"estrategia\" /> "
            "não foi encontrado. As rotinas de estratégia (hidden_patterns, "
            "competitor_analysis) devem ser mantidas — a unificação adiciona "
            "rotinas de documentos sem remover as existentes."
        )


class TestAC5_DocumentosRoomRemoved:
    """AC#5 — DocumentosRoom.tsx removido ou convertido em redirect."""

    def test_documentos_room_removed_or_redirect(self) -> None:
        """DocumentosRoom.tsx não deve existir como componente independente
        OU deve ser apenas um redirect."""
        if not DOCUMENTOS_ROOM.exists():
            return  # Removido — OK!

        content = DOCUMENTOS_ROOM.read_text(encoding="utf-8")

        # Se existe, deve ser APENAS um redirect (não ter renderização complexa)
        has_redirect = bool(
            re.search(r'(redirect|navigate|replace)\s*\(', content, re.IGNORECASE)
        )
        is_small = len(content) < 200  # Só algumas linhas de import + redirect

        assert has_redirect or is_small, (
            "DocumentosRoom.tsx ainda existe como componente independente "
            f"({len(content)} bytes) e não parece ser apenas um redirect. "
            "Com a unificação da sala, o componente DocumentosRoom deve ser "
            "removido (seu conteúdo foi portado para EstrategiaRoom) OU "
            "convertido em um redirect simples para /app/estrategia."
        )
