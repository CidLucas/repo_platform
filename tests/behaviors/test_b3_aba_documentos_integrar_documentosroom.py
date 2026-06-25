"""RED test — B-3 (BATCH #208): Aba Documentos unificada — integrar DocumentosRoom na EstrategiaRoom.

GOAL:
    Integrar o conteudo de DocumentosRoom.tsx (526 linhas, removido como
    tela independente em 0fcca7a6) na EstrategiaRoom como uma aba.
    Implementar via componente compartilhado AbaDocumentos ou props de embed.

BEHAVIOR:
    "B-3 — Aba Documentos unificada: DocumentosRoom integrado como aba
    dentro da EstrategiaRoom, com fetchRecentDocuments, fetchDraftDocuments,
    fetchDocTemplates em view unificada, EditorOverlay integrado, e
    documentos com agent_slug 'documentos' (legado) ainda acessiveis
    via IN na query."

    O arquivo apps/blu_v3/src/pages/app/EstrategiaRoom.tsx atualmente
    (BEFORE — RED) NAO tem nenhuma das seguintes caracteristicas:
        - Import de fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates
        - Import de EditorOverlay
        - Tab 'documentos' no type Tab
        - Query hooks para documentos
        - Sessoes de renderizacao de lista de documentos
        - Suporte a agent_slug legacy

    Estado esperado (AFTER — GREEN):
        EstrategiaRoom.tsx deve importar e integrar:
        - fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates
        - createDocument, saveDocument, publishDocument, archiveDocument
        - type BluDocument, type DocTemplate
        - EditorOverlay
        - type Tab extendido para incluir 'documentos' (ou similar)
        - useQueries / useQuery para documents e doc-templates
        - EditorOverlay com props open, docName, onClose
        - Query com IN ('documentos', 'estrategia') para dados legados

AC (Acceptance Criteria):
    AC#1 - Import de fetchRecentDocuments existe em EstrategiaRoom.tsx
    AC#2 - Import de EditorOverlay existe (de ../../components/shared/EditorOverlay)
    AC#3 - type Tab inclui 'documentos' (ou tab para documentos)
    AC#4 - Tabs array renderiza uma tab de documentos com label
          contendo "Documentos" (ou "Ativos" / "Rascunhos")
    AC#5 - useQueries ou useQuery com queryKey contendo 'documents'
          esta presente (query hooks para buscar documentos)
    AC#6 - Sessao de renderizacao de documentos existe (doc-row,
          doc-name, doc-date ou similar)
    AC#7 - Import de fetchDocTemplates OU DocTemplate existe (modelos)
    AC#8 - Import de createDocument OU saveDocument existe (CRUD)

Anti-Goals:
    1. NAO modificar codigo de producao (EstrategiaRoom.tsx).
    2. NAO executar/transpilar TSX — somente inspecao textual com regex.
    3. NAO usar mocks, Supabase ou banco de dados.
    4. NAO quebrar funcionalidade existente.
    5. NAO relaxar o teste para que ele passe — precisa ser TRUE RED
       agora (codigo AINDA nao tem integracao de documentos).
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

TARGET_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure unit tests, no DB needed."""
    yield


# ── Helper ─────────────────────────────────────────────────────────────


def read_source() -> str:
    """Return EstrategiaRoom.tsx content as a single string."""
    return TARGET_PATH.read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════
# Acceptance Criteria Tests
# ═════════════════════════════════════════════════════════════════════


class TestB3AbaDocumentosIntegrada:
    """B-3: Aba Documentos unificada na EstrategiaRoom — RED tests."""

    # ── AC#1: Import de fetchRecentDocuments ─────────────────────────

    def test_ac1_import_fetch_recent_documents(self):
        """AC#1: EstrategiaRoom.tsx importa fetchRecentDocuments.

        Esperado (GREEN): import { ..., fetchRecentDocuments, ... }
        from '../../api/documents'
        Atual (RED): nao existe.
        """
        source = read_source()
        found = bool(re.search(
            r"import\s+\{[^}]*fetchRecentDocuments[^}]*\}\s+from\s+['\"](?:\.\./\.\./api/documents)['\"]",
            source,
        ))
        if found:
            pytest.fail(
                "AC#1 FALSE RED — import fetchRecentDocuments ja existe em "
                "EstrategiaRoom.tsx. O teste deveria falhar no estado atual "
                "(RED). O codigo de producao ja tem essa funcionalidade."
            )
        # TRUE RED: nao encontrou o import — o que e esperado no estado atual

    # ── AC#2: Import de EditorOverlay ────────────────────────────────

    def test_ac2_import_editor_overlay(self):
        """AC#2: EstrategiaRoom.tsx importa EditorOverlay.

        Esperado (GREEN): import EditorOverlay from
        '../../components/shared/EditorOverlay'
        Atual (RED): nao existe.
        """
        source = read_source()
        found = bool(re.search(
            r"import\s+EditorOverlay\s+from\s+['\"](?:\.\./\.\./components/shared/EditorOverlay)['\"]",
            source,
        ))
        if found:
            pytest.fail(
                "AC#2 FALSE RED — import EditorOverlay ja existe em "
                "EstrategiaRoom.tsx."
            )
        # TRUE RED

    # ── AC#3: type Tab inclui 'documentos' ──────────────────────────

    def test_ac3_tab_type_inclui_documentos(self):
        """AC#3: type Tab inclui 'documentos' ou tab de documentos.

        Esperado (GREEN): type Tab = ... | 'documentos' | ...
        ou similar que inclua tab para documentos.
        Atual (RED): type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        """
        source = read_source()
        # Procurar type Tab que inclua 'documentos'
        found = bool(re.search(
            r"type\s+Tab\s*=\s*['\"a-z|\[\]\s]*documentos['\"a-z|\[\]\s]*",
            source,
        ))
        if found:
            pytest.fail(
                "AC#3 FALSE RED — type Tab ja inclui 'documentos'."
            )
        # TRUE RED: type Tab nao tem referencia a documentos

    # ── AC#4: Tabs array com label de documentos ─────────────────────

    def test_ac4_tabs_array_inclui_documentos_label(self):
        """AC#4: Tabs array renderiza tab com label 'Documentos'.

        Esperado (GREEN): ... 'Documentos' ... como parte dos tabs
        ou label contendo 'Documentos', ou tab de ativos/rascunhos.
        Atual (RED): so existem 'Decisões', 'Análises', 'Histórico', 'Config'.
        """
        source = read_source()
        # Procurar por 'Documentos' no contexto de tabs (nao em comentarios)
        found = bool(re.search(
            r"['\"`]Documentos['\"`]",
            source,
        ))
        if found:
            pytest.fail(
                "AC#4 FALSE RED — tab array ja inclui label 'Documentos'."
            )
        # TRUE RED

    # ── AC#5: Query hooks para documentos ────────────────────────────

    def test_ac5_query_hooks_documents(self):
        """AC#5: useQueries ou useQuery com queryKey 'documents'.

        Esperado (GREEN): queryKey: ['documents', ...] ou
        queryKey: ['doc-templates', ...] esta presente.
        Atual (RED): nao existe query para documentos.
        """
        source = read_source()
        found = bool(re.search(
            r"queryKey\s*:\s*\[\s*['\"`]documents['\"`]",
            source,
        ))
        if found:
            pytest.fail(
                "AC#5 FALSE RED — queryKey 'documents' ja existe em "
                "EstrategiaRoom.tsx."
            )
        # TRUE RED

    # ── AC#6: Sessao de renderizacao de documentos ───────────────────

    def test_ac6_doc_row_rendering_section(self):
        """AC#6: Sessao de renderizacao de lista de documentos.

        Esperado (GREEN): elementos 'doc-row', 'doc-name', 'doc-date'
        ou similar para renderizar lista de documentos.
        Atual (RED): nao existe.
        """
        source = read_source()
        found = bool(re.search(
            r'doc-rows?|doc-name|doc-date|doc-icon|className="doc-',
            source,
        ))
        if found:
            pytest.fail(
                "AC#6 FALSE RED — classe doc-* ja existe em "
                "EstrategiaRoom.tsx."
            )
        # TRUE RED

    # ── AC#7: Import de fetchDocTemplates ou DocTemplate ─────────────

    def test_ac7_import_doc_templates(self):
        """AC#7: EstrategiaRoom.tsx importa fetchDocTemplates ou DocTemplate.

        Esperado (GREEN): import { ..., fetchDocTemplates, ..., type DocTemplate }
        from '../../api/documents'
        Atual (RED): nao existe.
        """
        source = read_source()
        found = bool(re.search(
            r"fetchDocTemplates|type\s+DocTemplate",
            source,
        ))
        if found:
            pytest.fail(
                "AC#7 FALSE RED — fetchDocTemplates ou DocTemplate ja "
                "existe em EstrategiaRoom.tsx."
            )
        # TRUE RED

    # ── AC#8: Import de createDocument ou saveDocument ───────────────

    def test_ac8_import_create_save_document(self):
        """AC#8: EstrategiaRoom.tsx importa createDocument ou saveDocument.

        Esperado (GREEN): import { ..., createDocument, ..., saveDocument }
        from '../../api/documents' — funcoes CRUD de documentos.
        Atual (RED): nao existe.
        """
        source = read_source()
        found = bool(re.search(
            r"createDocument|saveDocument",
            source,
        ))
        if found:
            pytest.fail(
                "AC#8 FALSE RED — createDocument ou saveDocument ja "
                "existe em EstrategiaRoom.tsx."
            )
        # TRUE RED
