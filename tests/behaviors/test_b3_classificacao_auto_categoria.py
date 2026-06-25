"""RED test for behavior B-3 (BKL-036) — Classificacao automatica de categoria.

GOAL:
    A funcao ``autoClassify`` em ``knowledgeBaseService.ts`` deve inferir
    a categoria correta com base no nome do arquivo (keywords) e tipo
    MIME.  Esta nova AC (AC#1 deste arquivo, distinta da AC#1 ja
    commitada em ``test_b3_classificacao_auto_categorias.py``) verifica
    que ``"politica_ferias_2025.md"`` (politica / policy de ferias em
    Markdown) deve ser classificada como ``"contexto_empresa"`` porque
    a keyword ``politica`` no nome do arquivo mapeia para contexto da
    empresa.

BEHAVIOR:
    B-3 — Classificacao automatica de categoria (BKL-036).

    AC#1 — ``autoClassify("politica_ferias_2025.md", "text/markdown")``
    DEVE retornar ``"contexto_empresa"`` porque a keyword ``politica``
    (policy / regulamento interno) no nome do arquivo indica
    contexto institucional que pertence a ``contexto_empresa``.

AC (Acceptance Criteria):
    AC#1 — A funcao ``autoClassify`` DEVE estar exportada de
           ``apps/blu_v3/src/services/knowledgeBaseService.ts`` e:

             autoClassify("politica_ferias_2025.md", "text/markdown")
             => "contexto_empresa"

           Requisitos:
             1. ``export function autoClassify`` declarada com os
                parametros ``fileName: string``, ``fileType: string``,
                ``metadata?: Record<string, string>`` e retorno
                ``KBCategory``.
             2. O corpo da funcao DEVE referenciar a keyword
                ``politica`` (ou variacoes como ``politicas``,
                ``policy``, ``policies``, ``regulamento``) como
                indicador de contexto da empresa.
             3. O literal ``"contexto_empresa"`` DEVE aparecer como
                valor de retorno no corpo da funcao (nao apenas em
                ``KB_CATEGORIES``).

ESTADO ATUAL (RED):
    - ``apps/blu_v3/src/services/knowledgeBaseService.ts`` existe
      (339 linhas) e exporta ``KBCategory``, ``KB_CATEGORIES``,
      ``uploadFile``, ``listDocuments``, etc. — mas NAO exporta
      ``autoClassify``.
    - Nenhuma string ``autoClassify`` aparece no source.
    - Nenhuma string ``politica`` / ``politicas`` / ``policy`` aparece
      como regra de classificacao no source.
    - O literal ``"contexto_empresa"`` aparece apenas em
      ``KB_CATEGORIES``, nao em uma funcao de classificacao.
    - Este teste falha (RED) ate que ``autoClassify`` seja
      implementada e inclua a regra
      ``politica|policy|policies|regulamento`` -> ``"contexto_empresa"``.

ESTADO ALVO (GREEN):
    - Exportar ``autoClassify`` em ``knowledgeBaseService.ts``.
    - Adicionar regra de keyword para ``politica`` (ou ``policy``,
      ``policies``, ``regulamento``) no nome do arquivo que retorne
      ``"contexto_empresa"``.
    - Exemplo de regra:
        if (/politica|policy|policies|regulamento/i.test(fileName)) {
            return 'contexto_empresa'
        }

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao (knowledgeBaseService.ts).
    2. NAO importar / executar TypeScript — o teste e pura inspecao
       textual do arquivo .ts.
    3. NAO usar fixtures de DB ou rede — sem Supabase, sem mocks.
    4. NAO usar ``ts-node``, ``tsx``, ``vitest`` ou qualquer runner TS.
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
    6. NAO remover nenhuma funcao ja exportada de
       ``knowledgeBaseService.ts``.
    7. NAO duplicar a AC ja coberta por
       ``test_b3_classificacao_auto_categorias.py`` (folha_pagamento
       -> dados_negocio) — esta nova AC usa um arquivo ``.md`` com
       keyword ``politica`` -> ``contexto_empresa``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)


# ── Override do root conftest (teste puramente estatico) ──────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao do arquivo ``knowledgeBaseService.ts``, sem teardown
    no Supabase, sem rede, sem imports/execucao de TypeScript.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TS como texto puro (sem parser)."""
    assert path.exists(), (
        f"Source file not found: {path}.  "
        "O behavior B-3 (BKL-036) exige que "
        "apps/blu_v3/src/services/knowledgeBaseService.ts exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — autoClassify("politica_ferias_2025.md") => "contexto_empresa" ──


def test_b3_ac1_politica_markdown_para_contexto_empresa() -> None:
    """AC#1 — ``autoClassify("politica_ferias_2025.md",
    "text/markdown")`` DEVE retornar ``"contexto_empresa"``.

    Comportamento exigido:

        autoClassify("politica_ferias_2025.md", "text/markdown")
            => "contexto_empresa"

    Regras de classificacao necessarias:
      - A keyword ``politica`` (ou ``politicas``, ``policy``,
        ``policies``, ``regulamento``) no ``fileName`` DEVE mapear
        para a categoria ``"contexto_empresa"``.
      - A regra deve ser case-insensitive e buscar no nome do arquivo.

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts``.
      - Nenhuma string ``politica`` aparece como keyword de
        classificacao no source.
      - O literal ``"contexto_empresa"`` aparece apenas na constante
        ``KB_CATEGORIES``, nao em uma funcao de classificacao.

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (com assinatura completa).
      2. Adicionar no corpo uma regra que reconheca a keyword
         ``politica`` (ou ``policy``, ``policies``, ``regulamento``)
         e retorne ``"contexto_empresa"``.
    """
    source = _read_source(KB_SERVICE_PATH)

    # ── 1. Verifica que a funcao autoClassify esta exportada ───────────
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#1 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "AC#1 exige que:\n"
            "  autoClassify('politica_ferias_2025.md', 'text/markdown')\n"
            "  => 'contexto_empresa'\n\n"
            "Implemente primeiro a funcao `autoClassify` com a assinatura:\n"
            "  export function autoClassify(\n"
            "      fileName: string,\n"
            "      fileType: string,\n"
            "      metadata?: Record<string, string>,\n"
            "  ): KBCategory { ... }\n\n"
            "O arquivo atual exporta: KBCategory, KB_CATEGORIES, "
            "KBDocument, UploadOptions, EmbeddingProgress, "
            "KBDocumentSource, CsvUploadResult, isComplexFile, "
            "isCsvFile, getAcceptedExtensions, listDocuments, "
            "deleteDocument, getDocumentProgress, uploadSimpleFile, "
            "uploadComplexFile, uploadFile, uploadCsvDataSource, "
            "retryDocument — mas nao `autoClassify`."
        )

    # ── 2. Localiza o corpo de autoClassify ───────────────────────────
    func_body_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\([^)]*\)\s*:\s*KBCategory\s*\{",
        re.DOTALL,
    )
    func_body_match = func_body_pattern.search(source)
    if func_body_match is None:
        pytest.fail(
            "AC#1 — RED.  Apos localizar `export function autoClassify`, "
            "nao foi possivel encontrar o corpo da funcao "
            "(`): KBCategory { ... }`).  Verifique se a declaracao esta "
            "completa."
        )

    body_start = func_body_match.end()
    body = source[body_start:]

    # ── 3. Verifica que a keyword `politica` aparece no corpo ─────────
    #     Case-insensitive, word-boundary, aceitando variacoes como
    #     `politica`, `politicas`, `policy`, `policies`,
    #     `regulamento`.
    if not re.search(
        r"\b(?:politica|politicas|policy|policies|regulamento)\b",
        body,
        re.IGNORECASE,
    ):
        pytest.fail(
            "AC#1 — RED.  O corpo de `autoClassify` NAO referencia a "
            "keyword `politica` (ou variacoes como `politicas`, "
            "`policy`, `policies`, `regulamento`).\n\n"
            "Para que `autoClassify('politica_ferias_2025.md', "
            "'text/markdown')` retorne `'contexto_empresa'`, o corpo "
            "da funcao deve inspecionar o `fileName` em busca de "
            "palavras-chave como `politica`, `policy`, `policies`, "
            "`regulamento`, etc., e mapear essa regra para a "
            "categoria `'contexto_empresa'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/politica|policy|policies|regulamento/i.test(fileName)) {\n"
            "      return 'contexto_empresa'\n"
            "  }"
        )

    # ── 4. Verifica que a string literal "contexto_empresa" aparece no corpo ─
    if '"contexto_empresa"' not in body and "'contexto_empresa'" not in body:
        pytest.fail(
            "AC#1 — RED.  O corpo de `autoClassify` nao retorna a "
            "string literal `'contexto_empresa'` em nenhum caminho.\n\n"
            "AC#1 exige que `autoClassify('politica_ferias_2025.md', "
            "'text/markdown')` retorne `'contexto_empresa'`.\n\n"
            "Acrescente um branch que retorne `'contexto_empresa'` "
            "para arquivos cuja `fileName` contenha a keyword "
            "`politica` (ou `policy`, `policies`, `regulamento`)."
        )
