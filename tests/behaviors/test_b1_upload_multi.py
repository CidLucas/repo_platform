"""RED test for behavior B-1 — Upload Múltiplos Arquivos e Pastas.

GOAL:
    Adicionar suporte a upload em lote (multi-arquivo e/ou pasta inteira)
    na knowledge base, através de uma nova função ``uploadMulti`` exportada
    como ``async`` a partir de ``knowledgeBaseService.ts``.

BEHAVIOR:
    B-1 — Upload Múltiplos Arquivos e Pastas.

    After the fix:
    - O arquivo ``apps/blu_v3/src/services/knowledgeBaseService.ts`` deve
      exportar uma função assíncrona chamada ``uploadMulti``, capaz de
      receber uma coleção de arquivos (e/ou estruturas equivalentes a
      "pastas") e iniciar o fluxo de upload apropriado.

AC (Acceptance Criteria):
    AC#1 — A função ``uploadMulti`` deve estar EXPORTADA como
           ``async function`` em
           ``apps/blu_v3/src/services/knowledgeBaseService.ts``.

Estado atual (antes da correção):
    O arquivo ``knowledgeBaseService.ts`` exporta hoje apenas:
        - ``uploadSimpleFile``
        - ``uploadComplexFile``
        - ``uploadFile`` (wrapper que despacha para simple/complex)
        - ``uploadCsvDataSource``
        - ``retryDocument``
    Nenhuma dessas funções cobre o cenário de múltiplos arquivos / pasta
    inteira. A função ``uploadMulti`` ainda NÃO existe no fonte, então o
    teste abaixo falha (RED) até que ela seja adicionada na fase GREEN.
"""

import pathlib
import re

import pytest


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_KB_SERVICE_PATH = _APP_SRC / "services" / "knowledgeBaseService.ts"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB1UploadMulti:
    """B-1: Upload Múltiplos Arquivos e Pastas — export de ``uploadMulti``."""

    def test_uploadmulti_e_exportado(self):
        """AC#1: ``uploadMulti`` deve ser exportada como função ``async`` de
        ``knowledgeBaseService.ts``.

        Contrato:
            - O fonte deve conter ``export async function uploadMulti``
              (a sintaxe canônica usada pelas demais funções do arquivo,
              como ``uploadSimpleFile``, ``uploadComplexFile``, ``uploadFile``,
              ``uploadCsvDataSource`` e ``retryDocument``).
            - A função ``uploadMulti`` ainda NÃO existe no fonte atual,
              portanto este teste falha (RED) até que a fase GREEN a
              adicione.
        """
        # Garante que o arquivo-alvo existe — sanity check, não é a AC.
        assert _KB_SERVICE_PATH.is_file(), (
            f"Arquivo de produção não encontrado em "
            f"{_KB_SERVICE_PATH}. O teste de behavior B-1 pressupõe a "
            f"existência do serviço de knowledge base."
        )

        source = _read(_KB_SERVICE_PATH)

        # Padrão canônico: "export async function uploadMulti("
        # Aceita também variações triviais de espaçamento entre tokens,
        # mas exige:
        #   1. o identificador "uploadMulti" estar presente;
        #   2. estar declarado como "async function" (não arrow, não const);
        #   3. estar precedido pelo modificador "export".
        export_async_fn_pattern = re.compile(
            r"^\s*export\s+async\s+function\s+uploadMulti\s*\(",
            re.MULTILINE,
        )

        has_upload_multi_decl = export_async_fn_pattern.search(source) is not None
        has_upload_multi_id = "uploadMulti" in source

        if not has_upload_multi_decl:
            missing = []
            if not has_upload_multi_id:
                missing.append(
                    "o identificador 'uploadMulti' em "
                    "knowledgeBaseService.ts"
                )
            else:
                missing.append(
                    "a assinatura 'export async function uploadMulti(' "
                    "em knowledgeBaseService.ts — o identificador "
                    "aparece no arquivo, mas não como função async "
                    "exportada (verifique se está declarado como "
                    "'export async function uploadMulti(...)' no mesmo "
                    "padrão usado por 'uploadSimpleFile', "
                    "'uploadComplexFile' e 'uploadFile')"
                )

            pytest.fail(
                "AC#1 violado: o behavior B-1 (Upload Múltiplos Arquivos e "
                "Pastas) exige que knowledgeBaseService.ts exporte uma "
                "função assíncrona chamada 'uploadMulti'. "
                "Faltando: " + "; ".join(missing) + ". "
                "Adicione em apps/blu_v3/src/services/knowledgeBaseService.ts "
                "uma declaração no formato "
                "'export async function uploadMulti(...)' que receba a "
                "coleção de arquivos/pastas e orquestre o upload (pode "
                "reusar 'uploadFile' / 'uploadSimpleFile' / "
                "'uploadComplexFile' internamente). O teste atual é RED e "
                "deve passar (GREEN) assim que a função for adicionada."
            )
