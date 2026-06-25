"""RED test for behavior F-3-B4 — Preview e download de documentos na
BibliotecaRoom. Usuário deve poder baixar arquivos originais e visualizar
preview inline quando possível.

GOAL:
    AC#1 — Cada card/row de documento deve ter um botão de "Download" que
           baixa o arquivo original do Supabase Storage via signed URL.

    AC#2 — Documentos do tipo PDF, TXT e MD devem ter preview inline (modal
           ou nova aba).

    AC#3 — O download deve usar
           ``supabase.storage.from('knowledge-base').createSignedUrl(storagePath, 60)``
           com TTL de 60s.

BEHAVIOR:
    F-3-B4 — Preview e download de documentos na BibliotecaRoom.

    A BibliotecaRoom atualmente permite upload, exclusão e reprocessamento de
    documentos, mas não oferece:

    - Download do arquivo original do Storage
    - Preview inline (para PDF, TXT, MD)
    - Link direto para abrir o documento

    O fix adiciona:

    1. Função ``getDocumentDownloadUrl()`` em knowledgeBaseService.ts que usa
       ``createSignedUrl`` com TTL de 60s.
    2. Método ``getDownloadUrl()`` em useKnowledgeBase.ts exposto no retorno do hook.
    3. Botão "Download" (⬇) em DocCard e DocRow na BibliotecaRoom.tsx.
    4. Preview inline: PDF abre em nova aba (window.open), TXT/MD abrem modal.

AC (Acceptance Criteria):
    AC#1 — Botão de Download em cada card/row que baixa via signed URL.
    AC#2 — Preview inline para PDF, TXT e MD (modal ou nova aba).
    AC#3 — createSignedUrl(storagePath, 60) com TTL de 60s.

Anti-Goals (must NOT be violated):
    1. NAO usar fetch direto para download — usar sempre createSignedUrl do
       Supabase Storage.
    2. NAO expor o storage_path diretamente na URL — sempre criar signed URL.
    3. NAO remover botoes existentes (Remover, Reprocessar) — apenas adicionar
       o Download.

Estado atual: RED — as tres funcionalidades estao AUSENTES:

    - knowledgeBaseService.ts NAO possui funcao ``getDocumentDownloadUrl``
      nem nenhuma chamada a ``createSignedUrl``.
    - useKnowledgeBase.ts NAO possui metodo ``getDownloadUrl`` e NAO o retorna
      no objeto do hook.
    - BibliotecaRoom.tsx DocCard e DocRow NAO possuem botao de Download.
    - Nao ha preview inline para PDF, TXT ou MD (nem modal, nem nova aba).

    ASSERTIONS INVERTIDAS: cada teste ASSERTA QUE O RECURSO EXISTE — como
    todos estao AUSENTES, todos FALHAM (RED verdadeiro). Quando o coder
    implementar, os testes passarao (GREEN).

Os testes sao pure source inspection (regex no texto TypeScript). Nada eh
mockado, nada eh executado.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

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

HOOK_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useKnowledgeBase.ts"
)

BIBLIOTECA_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)


# ── Read sources once ───────────────────────────────────────────────────

KB_SERVICE_SRC = KB_SERVICE_PATH.read_text("utf-8")
HOOK_SRC = HOOK_PATH.read_text("utf-8")
BIBLIOTECA_SRC = BIBLIOTECA_PATH.read_text("utf-8")


# ── AC#1 — Botao de Download ────────────────────────────────────────────


def test_ac1_get_document_download_url_service_function():
    """AC#1 — knowledgeBaseService.ts MUST export
    ``getDocumentDownloadUrl(storagePath: string): Promise<string>``.

    Currently MISSING — the service has no download functionality at all.
    This test FAILS (RED) because the function does not exist yet.
    """
    has_function = bool(
        re.search(
            r"export\s+async\s+function\s+getDocumentDownloadUrl\s*\(",
            KB_SERVICE_SRC,
        )
    )

    assert has_function, (
        "RED [AC#1] — knowledgeBaseService.ts precisa exportar "
        "getDocumentDownloadUrl(storagePath: string): Promise<string>. "
        "Funcao nao encontrada no source."
    )

    # Verify the function signature includes Promise<string>
    has_promise_return = bool(
        re.search(
            r"getDocumentDownloadUrl\s*\([^)]*\)\s*:\s*Promise\s*<\s*string\s*>",
            KB_SERVICE_SRC,
        )
    )

    assert has_promise_return, (
        "RED [AC#1] — getDocumentDownloadUrl precisa retornar Promise<string>."
    )


def test_ac1_download_button_in_doccard():
    """AC#1 — DocCard in BibliotecaRoom.tsx MUST have a download button (⬇)
    that calls a download handler like onDownload or getDownloadUrl.

    Currently MISSING — DocCard only has "Remover" and "↻ Reprocessar".
    """
    # The download button should reference a download handler
    has_on_download_prop = bool(
        re.search(
            r"onDownload",
            BIBLIOTECA_SRC,
        )
    )

    assert has_on_download_prop, (
        "RED [AC#1] — DocCard precisa receber prop onDownload para o "
        "botao de Download."
    )

    # Regression: existing buttons must still be present
    assert "Remover" in BIBLIOTECA_SRC, (
        "Regression: botao Remover deve continuar existindo em DocCard."
    )
    assert "Reprocessar" in BIBLIOTECA_SRC or "↻" in BIBLIOTECA_SRC, (
        "Regression: botao Reprocessar deve continuar existindo em DocCard."
    )


def test_ac1_download_button_in_docrow():
    """AC#1 — DocRow in BibliotecaRoom.tsx MUST have a download button.

    Currently MISSING — DocRow only has "Remover" and "↻" (reprocess).
    """
    has_on_download_prop = bool(
        re.search(
            r"onDownload",
            BIBLIOTECA_SRC,
        )
    )

    assert has_on_download_prop, (
        "RED [AC#1] — DocRow precisa receber prop onDownload para o "
        "botao de Download."
    )

    # Regression: existing buttons must still be present
    assert "Remover" in BIBLIOTECA_SRC, (
        "Regression: botao Remover deve continuar existindo em DocRow."
    )


def test_ac1_download_url_in_hook():
    """AC#1 — useKnowledgeBase.ts MUST expose ``getDownloadUrl``.

    Currently MISSING — the hook returns only reload, upload, uploadCsv,
    remove, retry, getDocumentProgress.
    """
    has_get_download_url = bool(
        re.search(
            r"getDownloadUrl",
            HOOK_SRC,
        )
    )

    assert has_get_download_url, (
        "RED [AC#1] — useKnowledgeBase precisa ter metodo getDownloadUrl "
        "que chama getDocumentDownloadUrl do service."
    )

    # Regression: existing return keys must still be present
    assert "remove" in HOOK_SRC, (
        "Regression: hook deve continuar retornando 'remove'."
    )
    assert "retry" in HOOK_SRC, (
        "Regression: hook deve continuar retornando 'retry'."
    )
    assert "reload" in HOOK_SRC, (
        "Regression: hook deve continuar retornando 'reload'."
    )


# ── AC#2 — Preview inline (PDF, TXT, MD) ────────────────────────────────


def test_ac2_preview_inline_modal_or_tab():
    """AC#2 — BibliotecaRoom MUST have inline preview for PDF/TXT/MD.

    Currently MISSING — no preview modal, no window.open for PDF, no
    fetch-for-preview of TXT/MD content.
    """
    # For PDF: window.open with a signed URL opens PDF natively in browser
    has_pdf_new_tab = bool(
        re.search(
            r"window\.open\s*\(.*url.*['\"]_blank['\"]",
            BIBLIOTECA_SRC,
        )
    )

    assert has_pdf_new_tab, (
        "RED [AC#2] — BibliotecaRoom precisa abrir PDF em nova aba via "
        "window.open(url, '_blank')."
    )

    # For TXT/MD: a modal component for previewing content
    has_preview_modal = bool(
        re.search(
            r"(PreviewModal|previewModal|preview.*modal|DocumentPreview)",
            BIBLIOTECA_SRC,
        )
    )

    assert has_preview_modal, (
        "RED [AC#2] — BibliotecaRoom precisa ter um modal de preview para "
        "TXT/MD (PreviewModal, DocumentPreview ou similar)."
    )


# ── AC#3 — createSignedUrl com TTL de 60s ───────────────────────────────


def test_ac3_create_signed_url_ttl_60():
    """AC#3 — knowledgeBaseService.ts MUST call
    ``supabase.storage.from('knowledge-base').createSignedUrl(storagePath, 60)``
    with TTL of 60 seconds.

    Currently MISSING — no call to createSignedUrl exists anywhere.
    """
    # Check that createSignedUrl is used with the correct bucket
    has_create_signed_url = bool(
        re.search(
            r"createSignedUrl\s*\(",
            KB_SERVICE_SRC,
        )
    )

    assert has_create_signed_url, (
        "RED [AC#3] — knowledgeBaseService.ts precisa chamar "
        "createSignedUrl(storagePath, 60). Chamada nao encontrada."
    )

    # Verify the bucket name 'knowledge-base'
    has_correct_bucket = bool(
        re.search(
            r"\.from\s*\(\s*['\"]knowledge-base['\"]\s*\)",
            KB_SERVICE_SRC,
        )
    )

    assert has_correct_bucket, (
        "RED [AC#3] — createSignedUrl deve ser chamada no bucket "
        "'knowledge-base'. Bucket nao encontrado."
    )

    # Verify the TTL is 60
    has_ttl_60 = bool(
        re.search(
            r"createSignedUrl\s*\([^,]+,\s*60\s*\)",
            KB_SERVICE_SRC,
        )
    )

    assert has_ttl_60, (
        "RED [AC#3] — createSignedUrl precisa ter TTL de 60 segundos "
        "(createSignedUrl(storagePath, 60))."
    )

    # Regression: existing service functions must still be present
    assert "listDocuments" in KB_SERVICE_SRC, (
        "Regression: listDocuments deve continuar existindo."
    )
    assert "deleteDocument" in KB_SERVICE_SRC, (
        "Regression: deleteDocument deve continuar existindo."
    )
    assert "uploadFile" in KB_SERVICE_SRC, (
        "Regression: uploadFile deve continuar existindo."
    )
