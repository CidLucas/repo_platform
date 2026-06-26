"""RED test for behavior B-1 — Remove dead code e unifica upload.

GOAL:
    Remover ``uploadComplexFile()`` (duplicata de ``uploadSimpleFile()``)
    e unificar a rota de upload em ``uploadFile()``, que deve chamar
    ``supabase.functions.invoke('process-document', ...)`` diretamente
    sem delegar para uma segunda funcao.

BEHAVIOR:
    B-1 — Remove dead code e unifica upload.

    After the fix:
    - ``uploadComplexFile()`` NAO deve mais ser exportada do arquivo
      (foi removida como dead code).
    - ``uploadFile()`` deve chamar ``supabase.functions.invoke('process-document', ...)``
      diretamente, SEM delegar para ``uploadComplexFile``.
    - Upload de .pptx/.xlsx resulta em ``processing_mode: 'complex'`` e
      invocacao de ``process-document``, nao ficando ``pending`` eterno.
    - Upload de .pdf simples continua funcionando com ``processing_mode: 'simple'``
      tambem chamando ``process-document``.

AC (Acceptance Criteria):
    AC#1 — Upload de .pptx/.xlsx resulta em documento processado (completed),
           nao fica pendente. A funcao ``uploadComplexFile`` NAO deve mais
           existir como export separada (dead code removido). ``uploadFile()``
           deve chamar ``process-document`` diretamente.

Estado atual (antes da correcao) — o teste falha (RED) porque:
    - ``uploadComplexFile`` AINDA existe como export separada
    - ``uploadFile()`` AINDA delega para ``uploadComplexFile``
    - ``uploadFile()`` NAO chama ``process-document`` diretamente
"""

import pathlib
import re

import pytest

# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path("/home/ec2-user/repo_platform")
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_KB_SERVICE_PATH = _APP_SRC / "services" / "knowledgeBaseService.ts"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB1RemoveDeadCodeUnificaUpload:
    """B-1: Remove dead code e unifica upload — AC#1."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Sanity: production file must exist."""
        assert _KB_SERVICE_PATH.is_file(), (
            f"Arquivo de produção não encontrado em "
            f"{_KB_SERVICE_PATH}. O teste de behavior B-1 pressupõe a "
            f"existência do serviço de knowledge base."
        )
        self._source = _read(_KB_SERVICE_PATH)

    # ── RED 1: uploadComplexFile NAO deve mais existir ────────────

    def test_upload_complex_file_removido(self):
        """RED — AC#1: ``uploadComplexFile`` NAO deve ser exportada.

        No estado DESEJADO (apos GREEN), a exportacao
        ``export async function uploadComplexFile`` DEVE ter sido removida
        (dead code eliminado).

        No estado ATUAL (RED), esta exportacao AINDA existe, portanto
        ``re.search()`` retorna um match e o ``assert not`` falha — TRUE RED.
        """
        pattern = r"export\s+async\s+function\s+uploadComplexFile\s*\("
        match = re.search(pattern, self._source)
        assert not match, (
            "AC#1 FAIL (RED): uploadComplexFile ainda esta exportada como "
            "funcao separada no arquivo knowledgeBaseService.ts. "
            "Dead code deve ser removido. "
            f"Encontrado em: linha ~{self._source[:match.start()].count(chr(10)) + 1}"
        )

    # ── RED 2: uploadFile() NAO deve delegar para uploadComplexFile ──

    def test_upload_file_nao_delega_para_complex(self):
        """RED — AC#1: ``uploadFile()`` NAO deve conter ``uploadComplexFile``.

        No estado DESEJADO (apos GREEN), ``uploadFile()`` deve chamar
        ``supabase.functions.invoke('process-document', ...)`` diretamente,
        SEM delegar para ``uploadComplexFile``. A string literal
        ``uploadComplexFile(`` NAO deve aparecer no corpo de ``uploadFile``.

        No estado ATUAL (RED), ``uploadFile()`` contem
        ``return uploadComplexFile(file, clientId, source, ...)``
        — portanto a string ``uploadComplexFile(`` aparece e o teste falha.
        """
        assert "uploadComplexFile(" not in self._source, (
            "AC#1 FAIL (RED): uploadFile() ainda delega para "
            "uploadComplexFile. O codigo deve ser unificado para chamar "
            "process-document diretamente."
        )

    # ── RED 3: uploadFile() DEVE chamar process-document diretamente ──

    def test_upload_file_chama_process_document_direto(self):
        """RED — AC#1: ``uploadFile()`` DEVE invocar ``process-document`` diretamente.

        No estado DESEJADO (apos GREEN), o codigo de ``uploadFile()`` deve
        conter ``supabase.functions.invoke('process-document', ...)``
        diretamente (sem passar por ``uploadComplexFile``).

        No estado ATUAL (RED), a invocacao de ``process-document`` esta
        DENTRO de ``uploadComplexFile``, nao em ``uploadFile()``.
        """
        # Extrai o corpo de uploadFile() para analise
        start_match = re.search(
            r"export\s+async\s+function\s+uploadFile\s*\(",
            self._source,
        )
        assert start_match is not None, (
            "Nao encontrou 'export async function uploadFile' no fonte. "
            "Sanity check falhou."
        )

        body_start = start_match.start()
        # Procura a proxima export function depois de uploadFile
        next_func = re.search(
            r"\n\s*export\s+(?:async\s+)?function\s+",
            self._source[body_start + 1:],
        )
        body_end = (
            next_func.start() + body_start + 1
            if next_func
            else len(self._source)
        )
        upload_file_body = self._source[body_start:body_end]

        # DESIRED: uploadFile() DEVE conter 'process-document' direto
        has_direct = (
            "supabase.functions.invoke('process-document'" in upload_file_body
            or 'supabase.functions.invoke("process-document"' in upload_file_body
        )
        assert has_direct, (
            "AC#1 FAIL (RED): uploadFile() NAO invoca process-document "
            "diretamente. A chamada esta dentro de uploadComplexFile, "
            "que deve ser removida e substituida por invocacao direta "
            "em uploadFile()."
        )

    # ── RED 4: process-document invocado para .pptx/.xlsx ──────────

    def test_pptx_xlsx_chamam_process_document(self):
        """RED — AC#1: upload de .pptx/.xlsx deve chamar process-document.

        No estado DESEJADO (apos GREEN), uploadFile() deve chamar
        ``supabase.functions.invoke('process-document', ...)`` para
        arquivos .pptx e .xlsx (ALWAYS_COMPLEX_EXTENSIONS),
        resultando em status ``completed`` (nao ``pending`` eterno).

        No estado ATUAL (RED), a invocacao de process-document para
        .pptx/.xlsx esta dentro de uploadComplexFile. O teste falha
        porque uploadComplexFile ainda existe como intermediario.

        Verificacao indireta: se uploadComplexFile NAO existe, entao
        .pptx/.xlsx sao atendidos por uploadFile() via process-document.
        Se uploadComplexFile AINDA existe, entao .pptx/.xlsx passam
        por ele (nao unificado).
        """
        pattern = r"export\s+async\s+function\s+uploadComplexFile\s*\("
        match = re.search(pattern, self._source)

        # Tambem verifica que process-document existe no arquivo
        # (para .pptx/.xlsx, independente de estar em qual funcao)
        assert "process-document" in self._source, (
            "ERRO: 'process-document' nao encontrado no arquivo inteiro. "
            "Sem edge function, .pptx/.xlsx ficariam pending eterno. "
        )

        if match:
            # AINDA existe — .pptx/.xlsx passam por uploadComplexFile
            # Este teste falha (RED) porque queremos uploadComplexFile
            # removido e a chamada direta em uploadFile()
            pytest.fail(
                "AC#1 FAIL (RED): upload de .pptx/.xlsx passa por "
                "uploadComplexFile (dead code). A rota nao esta unificada. "
                "uploadComplexFile deve ser removida e uploadFile() deve "
                "chamar process-document diretamente."
            )

    # ── Verificacao: .pdf simples ainda funciona ────────────────────

    def test_upload_simple_file_continua_funcionando(self):
        """Verificacao: upload de .pdf simples continua funcionando.

        O upload de .pdf simples (sem forceComplex) deve continuar
        chamando process-document. ``uploadSimpleFile`` existe e invoca
        ``process-document`` com ``processing_mode: 'simple'``.

        NOTA: Este teste NAO falha em RED — ele verifica que a funcao
        de upload simples e process-document continuam presentes.
        """
        pattern = r"export\s+async\s+function\s+uploadSimpleFile\s*\("
        assert re.search(pattern, self._source), (
            "uploadSimpleFile nao encontrado. Upload de .pdf simples "
            "quebraria. Isso precisa existir."
        )
