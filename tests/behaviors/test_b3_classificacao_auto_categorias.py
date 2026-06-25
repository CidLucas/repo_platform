"""RED test for behavior B-3 (BKL-036) — Classificacao automatica de categoria.

GOAL:
    A funcao ``autoClassify`` em ``knowledgeBaseService.ts`` deve inferir
    a categoria correta com base no nome do arquivo (keywords) e tipo MIME.
    Esta primeira AC (AC#1) verifica que ``"folha_pagamento_2025.pdf"``
    (folha de pagamento / payroll PDF) deve ser classificado como
    ``"dados_negocio"`` porque a keyword ``folha`` (folha de pagamento /
    payroll) no nome do arquivo mapeia para dados de negocio.

BEHAVIOR:
    B-3 — Classificacao automatica de categoria (BKL-036).

    AC#1 — ``autoClassify("folha_pagamento_2025.pdf", "application/pdf")``
    DEVE retornar ``"dados_negocio"`` porque a keyword ``folha``
    (folha de pagamento / payroll / salario) no nome do arquivo indica
    dados financeiros/folha que pertencem a ``dados_negocio``.

AC (Acceptance Criteria):
    AC#1 — A funcao ``autoClassify`` DEVE estar exportada de
           ``apps/blu_v3/src/services/knowledgeBaseService.ts`` e:

             autoClassify("folha_pagamento_2025.pdf", "application/pdf")
             => "dados_negocio"

           Requisitos:
             1. ``export function autoClassify`` declarada com os parametros
                ``fileName: string``, ``fileType: string``,
                ``metadata?: Record<string, string>`` e retorno ``KBCategory``.
             2. O corpo da funcao DEVE referenciar a keyword ``folha``
                (ou ``pagamento``, ``payroll``, ``salario``) como indicador
                de dados de negocio para arquivos de folha de pagamento.
             3. O literal ``"dados_negocio"`` DEVE aparecer como valor de
                retorno no corpo da funcao (nao apenas em KB_CATEGORIES).

ESTADO ATUAL (RED):
    - ``apps/blu_v3/src/services/knowledgeBaseService.ts`` existe (339 linhas)
      e exporta ``KBCategory``, ``KB_CATEGORIES``, ``uploadFile``,
      ``listDocuments``, etc. — mas NAO exporta ``autoClassify``.
    - Nenhuma string ``autoClassify`` aparece no source.
    - Nenhuma string ``folha_pagamento`` ou keyword ``folha`` como regra
      de classificacao no source.
    - O literal ``"dados_negocio"`` aparece apenas em ``KB_CATEGORIES``,
      nao em uma funcao de classificacao.
    - Este teste falha (RED) ate que ``autoClassify`` seja implementada
      e inclua a regra ``folha|payroll|salario|pagamento`` -> ``"dados_negocio"``.

ESTADO ALVO (GREEN):
    - Exportar ``autoClassify`` em ``knowledgeBaseService.ts``.
    - Adicionar regra de keyword para ``folha`` (ou ``payroll``, ``salario``,
      ``pagamento``) no nome do arquivo que retorne ``"dados_negocio"``.
    - Exemplo de regra:
        if (/folha|payroll|salario|pagamento/i.test(fileName)) {
            return 'dados_negocio'
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


# ── AC#1 — autoClassify("folha_pagamento_2025.pdf") => "dados_negocio" ─────


def test_b3_ac1_folha_pagamento_para_dados_negocio() -> None:
    """AC#1 — ``autoClassify("folha_pagamento_2025.pdf", "application/pdf")``
    DEVE retornar ``"dados_negocio"``.

    Comportamento exigido:

        autoClassify("folha_pagamento_2025.pdf", "application/pdf")
            => "dados_negocio"

    Regras de classificacao necessarias:
      - A keyword ``folha`` (ou ``payroll``, ``salario``, ``pagamento``)
        no ``fileName`` DEVE mapear para a categoria ``"dados_negocio"``.
      - A regra deve ser case-insensitive e buscar no nome do arquivo.

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts``.
      - Nenhuma string ``folha`` aparece como keyword de classificacao
        (a palavra aparece apenas em comentarios, se houver).
      - O literal ``"dados_negocio"`` aparece apenas na constante
        ``KB_CATEGORIES``, nao em uma funcao de classificacao.

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (com assinatura completa).
      2. Adicionar no corpo uma regra que reconheca a keyword ``folha``
         (ou ``payroll``, ``salario``, ``pagamento``) e retorne
         ``"dados_negocio"``.
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
            "  autoClassify('folha_pagamento_2025.pdf', 'application/pdf')\n"
            "  => 'dados_negocio'\n\n"
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

    # ── 3. Verifica que a keyword `folha` aparece no corpo ───────────
    #     Case-insensitive, word-boundary, aceitando variacoes como
    #     `folha`, `folha_pagamento`, `payroll`, `salario`, `pagamento`.
    if not re.search(
        r"\b(?:folha|folha_pagamento|payroll|salario|salário|pagamento)\b",
        body,
        re.IGNORECASE,
    ):
        pytest.fail(
            "AC#1 — RED.  O corpo de `autoClassify` NAO referencia a "
            "keyword `folha` (ou variacoes como `folha_pagamento`, "
            "`payroll`, `salario`, `pagamento`).\n\n"
            "Para que `autoClassify('folha_pagamento_2025.pdf', "
            "'application/pdf')` retorne `'dados_negocio'`, o corpo "
            "da funcao deve inspecionar o `fileName` em busca de "
            "palavras-chave como `folha`, `payroll`, `salario`, etc., "
            "e mapear essa regra para a categoria `'dados_negocio'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/folha|payroll|salario|pagamento/i.test(fileName)) {\n"
            "      return 'dados_negocio'\n"
            "  }"
        )

    # ── 4. Verifica que a string literal "dados_negocio" aparece no corpo ─
    if '"dados_negocio"' not in body and "'dados_negocio'" not in body:
        pytest.fail(
            "AC#1 — RED.  O corpo de `autoClassify` nao retorna a "
            "string literal `'dados_negocio'` em nenhum caminho.\n\n"
            "AC#1 exige que `autoClassify('folha_pagamento_2025.pdf', "
            "'application/pdf')` retorne `'dados_negocio'`.\n\n"
            "Acrescente um branch que retorne `'dados_negocio'` para "
            "arquivos cuja `fileName` contenha a keyword `folha` "
            "(ou `payroll`, `salario`, `pagamento`)."
        )
