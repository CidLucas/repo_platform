"""
RED test for B-5 (BATCH #208) — Gerador de Documentos:
Seleção de template/modelo → editor pré-preenchido → salvar como documento ativo.

GOAL:
    Confirmar que a ``EstrategiaRoom.tsx`` ainda NÃO implementa o gerador
    de documentos — ou seja, não há lógica para selecionar templates,
    criar documentos do zero, preencher o editor com conteúdo de template,
    nem salvar via ``saveDocument``. Teste source-inspection TRUE RED
    — cada AC passa enquanto a feature não foi entregue.

BEHAVIOR:
    B-5 — ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`` deve:

        1. Usar ``fetchDocTemplates`` em um hook/query para listar
           templates disponíveis.
        2. Oferecer opção "Criar do zero" para criar documento vazio.
        3. Oferecer opção de usar template existente (seleção de
           template → preenche editor).
        4. Passar o conteúdo do template (ou vazio) para o
           ``EditorOverlay`` ao abrir o editor.
        5. Salvar o documento via ``saveDocument`` quando o usuário
           salva no editor.

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx``):

        - Linha 21: ``import RoutineConfigSection ...``
        → NÃO há import de ``fetchDocTemplates``, ``createDocument``
          ou ``saveDocument`` (testados pelo B-3 AC#7/AC#8).
        - Linhas 25-27: ``type Tab = 'decisoes' | 'analises' | 'historico' | 'config'``
        → NÃO há tab ``'documentos'`` ainda.
        - NÃO há ``useQuery``/``useQueries`` com ``queryKey``
          relacionado a ``docTemplates``.
        - NÃO há ``useMutation`` para ``createDocument`` nem
          ``saveDocument``.
        - NÃO há state para ``selectedTemplate``,
          ``creatingFromTemplate``, ``editingDocId`` ou similar.
        - NÃO há renderização de botão "Criar do zero" ou lista de
          templates.

AC (Acceptance Criteria):
    AC#1 — EstrategiaRoom.tsx usa ``fetchDocTemplates`` em um hook de
           consulta (``queryKey: ['docTemplates'`` ou similar).
    AC#2 — EstrategiaRoom.tsx tem uma variável de state para controlar
           o fluxo de criação de documento (``creatingDoc``,
           ``selectedTemplate``, ``editingDoc`` ou similar).
    AC#3 — EstrategiaRoom.tsx invoca ``createDocument`` em algum lugar
           (como ``useMutation`` ou callback direto).
    AC#4 — EstrategiaRoom.tsx invoca ``saveDocument`` como callback ou
           mutation (handler ``onSave``/``handleSave`` que chama
           ``saveDocument``).
    AC#5 — EstrategiaRoom.tsx renderiza UI de criação de documento
           (botão "Criar do zero", "Novo documento", ou lista de
           templates).

DECISION:
    Estratégia: estender a ``EstrategiaRoom.tsx`` in-place dentro da
    aba ``documentos`` (que será adicionada via B-3). O gerador pode
    ser um novo sub-componente ou JSX inline.

Test strategy:
    Source-inspection (lê o ``.tsx`` como texto). Cada AC é um método
    da classe ``TestB5GeradorDocumentos``. Se a regex ENCONTRAR o padrão
    esperado no estado GREEN, dispara ``pytest.fail(...)``. Se NÃO
    ENCONTRAR, o teste passa em silêncio (TRUE RED).

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção — apenas escrever o teste.
    2. NÃO transpilar nem executar TSX — source-inspection puro.
    3. NÃO usar mocks, Supabase, banco de dados ou rede.
    4. NÃO testar import de ``fetchDocTemplates`` ou ``createDocument``
       (já cobertos pelo B-3 AC#7, AC#8).
    5. NÃO falhar por whitespace ou indentação — apenas pelos padrões
       textuais das ACs.
    6. A polaridade deve ser TRUE RED: o teste passa AGORA (feature
       ausente) e falha depois que a feature for entregue (GREEN).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (repo root) ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ESTRATEGIA_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Fixture override ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def read_source() -> str:
    """Lê o conteúdo de ``EstrategiaRoom.tsx`` como texto UTF-8."""
    assert ESTRATEGIA_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {ESTRATEGIA_ROOM_TSX}. "
        "O teste B-5 pressupõe que EstrategiaRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return ESTRATEGIA_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB5GeradorDocumentos:
    """RED tests para B-5 (BATCH #208) — Gerador de Documentos.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado e o teste falhará com
    ``pytest.fail("FALSE RED — …")``.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_query_fetch_doc_templates(self) -> None:
        """AC#1 — ``EstrategiaRoom.tsx`` usa ``fetchDocTemplates`` em hook.

        GREEN esperado: ``queryKey`` que inclui ``'docTemplates'`` ou
        ``'doc-templates'``, com ``queryFn`` apontando para
        ``fetchDocTemplates``.

        Hoje não há nenhuma referência a ``fetchDocTemplates`` no
        componente.
        """
        source = read_source()
        # Verifica se fetchDocTemplates é referenciado em algum query hook
        # (useQuery, useQueries, useMutation, ou callback)
        match = re.search(r"\bfetchDocTemplates\b", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#1 violada: `fetchDocTemplates` JÁ é "
                f"referenciado em EstrategiaRoom.tsx (offset {match.start()}). "
                "Esperava-se que o hook de consulta de templates ainda NÃO "
                "existisse. A feature B-5 já foi entregue."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_doc_creation_state_variable(self) -> None:
        """AC#2 — State para controlar fluxo de criação de documento.

        GREEN esperado: uma variável de estado (``useState``) que
        controla o fluxo de criação, como ``creatingDoc``,
        ``selectedTemplate``, ``editingDocId``, ``docToEdit``,
        ``showDocCreator`` ou similar.

        Hoje não há nenhuma variável de estado relacionada à criação
        de documentos.
        """
        source = read_source()
        # Procura por padrões de nomenclatura comuns para state de criação
        match = re.search(
            r"""\b(const|let)\s+(creatingDoc|selectedTemplate|editingDocId|docToEdit|showDocCreator|creatingFromTemplate|docBeingCreated|templateToUse)\b""",
            source,
        )
        if match is not None:
            location = match.start()
            pytest.fail(
                "FALSE RED — AC#2 violada: uma variável de state para "
                f"criação de documento JÁ existe em EstrategiaRoom.tsx "
                f"(offset {location}). Esperava-se que o fluxo de criação "
                "ainda NÃO estivesse implementado."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_uses_create_document(self) -> None:
        """AC#3 — ``EstrategiaRoom.tsx`` invoca ``createDocument``.

        GREEN esperado: ``createDocument`` é chamado via
        ``useMutation`` (ou callback direto) para criar um novo
        documento a partir do gerador.

        Hoje não há referência a ``createDocument`` no componente
        (testado pelo B-3 AC#8 como import ausente).
        """
        source = read_source()
        match = re.search(r"\bcreateDocument\b", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#3 violada: `createDocument` JÁ é chamado "
                f"em EstrategiaRoom.tsx (offset {match.start()}). "
                "Esperava-se que a criação de documentos ainda NÃO "
                "estivesse implementada."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_uses_save_document(self) -> None:
        """AC#4 — ``EstrategiaRoom.tsx`` invoca ``saveDocument``.

        GREEN esperado: ``saveDocument`` é chamado como callback de
        ``onSave``/``handleSave`` ou via ``useMutation``, indicando que
        o gerador salva o documento editado.

        Hoje não há referência a ``saveDocument`` no componente
        (testado pelo B-3 AC#8 como import ausente).
        """
        source = read_source()
        match = re.search(r"\bsaveDocument\b", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#4 violada: `saveDocument` JÁ é chamado "
                f"em EstrategiaRoom.tsx (offset {match.start()}). "
                "Esperava-se que o salvamento de documentos ainda NÃO "
                "estivesse implementado."
            )

    # ── AC#5 ────────────────────────────────────────────────────────────────

    def test_ac5_has_create_ui(self) -> None:
        """AC#5 — UI de criação de documento.

        GREEN esperado: a UI renderiza um botão ou link para criar
        documento do zero, ou lista templates para seleção. Exemplos:
        ``'Criar do zero'``, ``'Novo Documento'``, ``'Novo documento'``,
        ou um map de templates.

        Hoje não há nenhuma UI de criação de documentos.
        """
        source = read_source()
        # Procura por texto de UI relacionado a criar documento
        match = re.search(
            r"""['"]Criar\s+(do\s+)?zero['"]""",
            source,
            re.IGNORECASE,
        )
        match_alt = re.search(
            r"""['"]Novo\s+[Dd]ocumento['"]""",
            source,
        )
        match_templates = re.search(
            r"""['"]Usar\s+(template|modelo)['"]""",
            source,
            re.IGNORECASE,
        )
        if match is not None or match_alt is not None or match_templates is not None:
            location = (
                match.start() if match
                else (match_alt.start() if match_alt
                      else (match_templates.start() if match_templates else 0))
            )
            pytest.fail(
                "FALSE RED — AC#5 violada: UI de criação de documento "
                f"JÁ existe em EstrategiaRoom.tsx (offset {location}). "
                "Esperava-se que o botão/UI 'Criar do zero' ou "
                "'Usar template' ainda NÃO existisse."
            )
