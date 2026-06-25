"""RED test for behavior B-2 (BKL-036) — Classificacao automatica de categorias.

GOAL:
    Disponibilizar uma funcao ``autoClassify`` que recebe o nome e o tipo
    MIME de um arquivo (mais metadata opcional) e retorna a categoria
    (``KBCategory``) que o documento deve receber ao ser inserido na
    Knowledge Base da blu_v3.  Hoje a UI e o ``uploadFile`` exigem que o
    usuario escolha manualmente a categoria em um ``<select>``; a ideia e
    que o sistema ja sugira/categorize arquivos comuns automaticamente
    (ex.: notas fiscais em PDF devem cair em ``"documentos"``).

BEHAVIOR:
    B-2 — Funcao ``autoClassify`` em ``knowledgeBaseService.ts``.

    A funcao deve ter a seguinte assinatura TypeScript:

        export function autoClassify(
            fileName: string,
            fileType: string,
            metadata?: Record<string, string>,
        ): KBCategory

    Regras de classificacao (referencia — GREEN deve implementar ao menos
    estas):
        - ``.pdf`` (fileType ``application/pdf``)           -> ``"documentos"``
        - ``.docx`` / ``application/vnd.openxmlformats...`` -> ``"documentos"``
        - ``.csv`` / ``.tsv`` / arquivos de dado estruturado -> ``"dados_negocio"``
        - ``.md`` / ``.txt`` de contexto institucional       -> ``"contexto_empresa"``
        - Fallback seguro                                  -> ``"conhecimento_ia"``

    O retorno DEVE ser um valor valido de ``KBCategory`` (uniao das
    4 categorias exportadas por ``KB_CATEGORIES``):
        ``"dados_negocio"`` | ``"contexto_empresa"`` |
        ``"documentos"``    | ``"conhecimento_ia"``

AC (Acceptance Criteria):
    AC#1 — A funcao ``autoClassify`` DEVE ser exportada de
           ``apps/blu_v3/src/services/knowledgeBaseService.ts`` com a
           assinatura:

               export function autoClassify(
                   fileName: string,
                   fileType: string,
                   metadata?: Record<string, string>,
               ): KBCategory

           Quando chamada com ``fileName="nf_2025_01.pdf"`` e
           ``fileType="application/pdf"``, DEVE retornar
           ``"documentos"``.

ESTADO ATUAL (RED):
    - O arquivo ``apps/blu_v3/src/services/knowledgeBaseService.ts``
      existe (339 linhas) e exporta ``KBCategory``, ``KB_CATEGORIES``,
      ``KBDocument``, ``isComplexFile``, ``isCsvFile``, ``uploadFile``,
      ``listDocuments``, etc. — mas NAO exporta ``autoClassify``.
    - Nenhuma string ``autoClassify`` aparece no source.
    - Este teste falha (RED) ate que a funcao seja adicionada na fase
      GREEN.

ESTADO ALVO (GREEN):
    - Acrescentar em ``knowledgeBaseService.ts``:

          export function autoClassify(
              fileName: string,
              fileType: string,
              metadata?: Record<string, string>,
          ): KBCategory {
              const ext = getExtension(fileName)
              if (ext === '.pdf' || ext === '.docx' ||
                  fileType === 'application/pdf' ||
                  fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
                  return 'documentos'
              }
              // ... outras regras
              return 'conhecimento_ia'
          }

    - A funcao deve continuar sendo um ``export`` top-level (nao apenas
      ``function`` local) e referenciar o tipo ``KBCategory`` ja exportado.

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao (knowledgeBaseService.ts).
    2. NAO importar / executar TypeScript — o teste e pura inspecao
       textual do arquivo .ts.
    3. NAO usar fixtures de DB ou rede — sem Supabase, sem mocks.
    4. NAO usar ``ts-node``, ``tsx``, ``vitest`` ou qualquer runner TS.
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
    6. NAO remover nenhuma funcao ja exportada de
       ``knowledgeBaseService.ts`` (``listDocuments``, ``uploadFile``,
       ``isComplexFile``, ``isCsvFile``, ``getAcceptedExtensions``, etc.).
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
        "O behavior B-2 (BKL-036) exige que "
        "apps/blu_v3/src/services/knowledgeBaseService.ts exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — autoClassify deve ser exportada e classificar nf_*.pdf ─────────


def test_b2_ac1_autoclassify_exportada() -> None:
    """AC#1 — ``autoClassify`` exportada de knowledgeBaseService.ts.

    Comportamento exigido:

        export function autoClassify(
            fileName: string,
            fileType: string,
            metadata?: Record<string, string>,
        ): KBCategory

    Quando chamada com:

        autoClassify("nf_2025_01.pdf", "application/pdf")

    DEVE retornar a string ``"documentos"``.

    Estado atual (RED): a funcao ``autoClassify`` NAO esta exportada em
    ``apps/blu_v3/src/services/knowledgeBaseService.ts``.  O teste
    procura:

      1. A declaracao ``export function autoClassify(`` no source.
      2. Os tres parametros ``fileName``, ``fileType`` e ``metadata?``
         na assinatura.
      3. O tipo de retorno ``KBCategory``.
      4. A evidencia textual de que a constante ``"documentos"`` aparece
         como um valor de retorno possivel (de modo estatico — sem
         executar o codigo TS).

    Se qualquer um desses requisitos falhar, o teste chama
    ``pytest.fail(...)`` com mensagem detalhada em pt-BR.
    """
    source = _read_source(KB_SERVICE_PATH)

    # ── 1. Verifica que a funcao esta exportada ────────────────────────
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#1 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "Assinatura esperada (GREEN):\n"
            "  export function autoClassify(\n"
            "      fileName: string,\n"
            "      fileType: string,\n"
            "      metadata?: Record<string, string>,\n"
            "  ): KBCategory {\n"
            "      // ... regras de classificacao\n"
            "  }\n\n"
            "O arquivo atual exporta: KBCategory, KB_CATEGORIES, "
            "KBDocument, UploadOptions, EmbeddingProgress, "
            "KBDocumentSource, CsvUploadResult, isComplexFile, "
            "isCsvFile, getAcceptedExtensions, listDocuments, "
            "deleteDocument, getDocumentProgress, uploadSimpleFile, "
            "uploadComplexFile, uploadFile, uploadCsvDataSource, "
            "retryDocument — mas nao `autoClassify`.\n\n"
            "GREEN deve adicionar a funcao `autoClassify` no arquivo "
            "citado, mantendo o tipo `KBCategory` ja exportado como "
            "tipo de retorno."
        )

    # ── 2. Verifica os tres parametros da assinatura ───────────────────
    #     fileName, fileType, metadata?  — nesta ordem.
    sig_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\(([^)]*)\)",
        re.DOTALL,
    )
    sig_match = sig_pattern.search(source)
    assert sig_match is not None, (
        "RED — AC#1: a funcao `autoClassify` nao foi encontrada com a "
        "assinatura `export function autoClassify(...)`.  Verifique se "
        "a declaracao esta completa (com os parenteses de abertura e "
        "fechamento)."
    )

    params_block = sig_match.group(1)
    has_file_name = bool(
        re.search(r"\bfileName\s*:\s*string\b", params_block)
    )
    has_file_type = bool(
        re.search(r"\bfileType\s*:\s*string\b", params_block)
    )
    has_metadata = bool(
        re.search(
            r"\bmetadata\s*\?\s*:\s*Record\s*<\s*string\s*,\s*string\s*>",
            params_block,
        )
    )

    if not (has_file_name and has_file_type and has_metadata):
        missing = []
        if not has_file_name:
            missing.append("`fileName: string`")
        if not has_file_type:
            missing.append("`fileType: string`")
        if not has_metadata:
            missing.append(
                "`metadata?: Record<string, string>` (opcional, "
                "com o `?` de optional)"
            )
        pytest.fail(
            "AC#1 — RED.  A funcao `autoClassify` esta exportada mas a "
            "assinatura NAO corresponde ao contrato de B-2 (BKL-036).\n"
            "  Faltando: " + ", ".join(missing) + "\n\n"
            "Assinatura exigida:\n"
            "  export function autoClassify(\n"
            "      fileName: string,\n"
            "      fileType: string,\n"
            "      metadata?: Record<string, string>,\n"
            "  ): KBCategory\n\n"
            "Encontrei a seguinte lista de parametros:\n"
            f"  {params_block.strip()!r}\n"
        )

    # ── 3. Verifica o tipo de retorno ``KBCategory`` ───────────────────
    return_type_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\([^)]*\)\s*:\s*([A-Za-z_][\w<>,\s\[\]|&]*)",
        re.DOTALL,
    )
    return_match = return_type_pattern.search(source)
    assert return_match is not None, (
        "RED — AC#1: nao foi possivel extrair o tipo de retorno de "
        "`autoClassify`.  Verifique se a declaracao segue o formato "
        "`export function autoClassify(...): TipoDeRetorno`."
    )
    return_type = return_match.group(1).strip()
    if return_type != "KBCategory":
        pytest.fail(
            "AC#1 — RED.  O tipo de retorno de `autoClassify` deve ser "
            f"`KBCategory`, mas foi encontrado `{return_type}`.\n\n"
            "O tipo `KBCategory` ja esta exportado em "
            "`knowledgeBaseService.ts` (linha ~52) como uniao das 4 "
            "categorias validas: `dados_negocio`, `contexto_empresa`, "
            "`documentos`, `conhecimento_ia`.\n\n"
            "GREEN deve declarar:\n"
            "  export function autoClassify(...): KBCategory\n"
        )

    # ── 4. Verifica a regra de classificacao nf_*.pdf -> "documentos" ──
    #     Como nao executamos o TS, validamos por inspecao textual:
    #     a string literal "documentos" deve aparecer no source de
    #     `autoClassify` (ou no corpo da funcao).
    func_body_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\([^)]*\)\s*:\s*KBCategory\s*\{",
        re.DOTALL,
    )
    func_body_match = func_body_pattern.search(source)
    if func_body_match is None:
        pytest.fail(
            "AC#1 — RED.  Apos validar export/parametros/retorno, nao "
            "foi possivel localizar o corpo de `autoClassify`.  "
            "Verifique se a sintaxe esta completa "
            "(`export function autoClassify(...): KBCategory { ... }`)."
        )

    # Pega o trecho a partir da chave de abertura ate o fim do arquivo
    # e checa se "documentos" aparece.  Como pode haver varios returns
    # em uma funcao, esta heuristica cobre o caso comum.
    body_start = func_body_match.end()
    body = source[body_start:]
    if '"documentos"' not in body and "'documentos'" not in body:
        pytest.fail(
            "AC#1 — RED.  A funcao `autoClassify` nao retorna a string "
            "literal `\"documentos\"` em nenhum caminho do seu corpo.\n\n"
            "Para o caso de teste:\n"
            "  autoClassify('nf_2025_01.pdf', 'application/pdf')\n"
            "o retorno DEVE ser a string `\"documentos\"`.\n\n"
            "Implemente ao menos uma regra do tipo:\n"
            "  if (ext === '.pdf' || fileType === 'application/pdf') {\n"
            "      return 'documentos'\n"
            "  }\n\n"
            "Certifique-se tambem de que `'documentos'` (com aspas) "
            "aparece como literal no corpo da funcao (e nao apenas como "
            "chave de KB_CATEGORIES)."
        )


# ── AC#2 — autoClassify("contrato_fornecedor.pdf", "application/pdf") ──────


def test_b2_ac2_contrato_pdf_para_documentos() -> None:
    """AC#2 — ``autoClassify("contrato_fornecedor.pdf", "application/pdf")``
    deve retornar ``"documentos"`` porque a keyword ``contrato`` no nome do
    arquivo mapeia para a categoria ``documentos``.

    Comportamento exigido:

        autoClassify("contrato_fornecedor.pdf", "application/pdf")
            => "documentos"

    Regras de classificacao necessarias (referencia — GREEN deve
    implementar ao menos estas):

      - Keyword ``contrato`` (case-insensitive, em ``fileName`` ou
        ``metadata``)  -> ``"documentos"``
      - A regra de extensao ``.pdf`` / ``application/pdf`` ja cobre o
        caso como fallback, mas o ponto central do AC#2 e a presenca da
        keyword ``contrato`` no corpo da funcao.

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts``.
      - Nenhuma string ``contrato`` aparece no corpo (porque o corpo
        nem existe).
      - O literal ``"documentos"`` aparece apenas na constante
        ``KB_CATEGORIES``, nao em uma funcao de classificacao.

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (mesma assinatura da AC#1).
      2. Adicionar no corpo da funcao uma regra do tipo
         ``/contrato|contract|acordo/i.test(fileName)`` que retorne
         ``"documentos"``.
    """
    source = _read_source(KB_SERVICE_PATH)

    # ── 1. Prerequisito: autoClassify deve estar exportada ─────────────
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#2 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "AC#2 exige que:\n"
            "  autoClassify('contrato_fornecedor.pdf', 'application/pdf')\n"
            "  => 'documentos'\n\n"
            "Implemente primeiro a funcao `autoClassify` (veja AC#1) e "
            "depois adicione a regra de keyword `contrato` -> "
            "`'documentos'` no corpo da funcao."
        )

    # ── 2. Localiza o corpo de autoClassify ───────────────────────────
    func_body_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\([^)]*\)\s*:\s*KBCategory\s*\{",
        re.DOTALL,
    )
    func_body_match = func_body_pattern.search(source)
    if func_body_match is None:
        pytest.fail(
            "AC#2 — RED.  Apos localizar `export function autoClassify`, "
            "nao foi possivel encontrar o corpo da funcao "
            "(`): KBCategory { ... }`).  Verifique se a declaracao esta "
            "completa."
        )

    body_start = func_body_match.end()
    body = source[body_start:]

    # ── 3. Verifica que a keyword `contrato` aparece no corpo ─────────
    #     Case-insensitive, word-boundary, aceitando plural / variacoes
    #     como `contratos`, `Contract`, `Acordo` etc.
    if not re.search(
        r"\b(?:contrato|contratos|contract|acordo|acordos)\b",
        body,
        re.IGNORECASE,
    ):
        pytest.fail(
            "AC#2 — RED.  O corpo de `autoClassify` NAO referencia a "
            "keyword `contrato` (ou variacoes como `contratos`, "
            "`contract`, `acordo`).\n\n"
            "Para que `autoClassify('contrato_fornecedor.pdf', "
            "'application/pdf')` retorne `'documentos'`, o corpo da "
            "funcao deve inspecionar o `fileName` (ou `metadata`) em "
            "busca de palavras-chave como `contrato`, `contract`, "
            "`acordo`, etc., e mapear essa regra para a categoria "
            "`'documentos'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/contrato|contract|acordo/i.test(fileName)) {\n"
            "      return 'documentos'\n"
            "  }\n"
        )

    # ── 4. Verifica que a string literal "documentos" aparece no corpo ─
    if '"documentos"' not in body and "'documentos'" not in body:
        pytest.fail(
            "AC#2 — RED.  O corpo de `autoClassify` nao retorna a "
            "string literal `'documentos'` em nenhum caminho.\n\n"
            "AC#2 exige que `autoClassify('contrato_fornecedor.pdf', "
            "'application/pdf')` retorne `'documentos'`.\n\n"
            "Acrescente um branch que retorne a string `'documentos'` "
            "para arquivos cuja `fileName` bata na keyword `contrato` "
            "(ou variacoes)."
        )


# ── AC#3 — autoClassify("planilha_rh.xlsx", "...spreadsheetml.sheet") ─────


def test_b2_ac3_xlsx_rh_para_dados_negocio() -> None:
    """AC#3 —
    ``autoClassify("planilha_rh.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")``
    deve retornar ``"dados_negocio"`` porque a keyword ``rh`` no nome do
    arquivo E a extensao ``.xlsx`` mapeiam para a categoria
    ``dados_negocio``.

    Comportamento exigido:

        autoClassify(
            "planilha_rh.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
            => "dados_negocio"

    Regras de classificacao necessarias (referencia — GREEN deve
    implementar ao menos estas):

      - Keyword ``rh`` (case-insensitive, em ``fileName`` ou
        ``metadata``)  -> ``"dados_negocio"``
      - Extensao ``.xlsx`` (combinada com keyword ``rh`` ou sozinha, em
        planilhas de RH / funcionarios / payroll) -> ``"dados_negocio"``

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts``.
      - Nenhuma string ``rh`` aparece como keyword de classificacao
        (apenas ``.xlsx`` aparece dentro de
        ``ALWAYS_COMPLEX_EXTENSIONS`` na linha 57, mas isso nao
        classifica em categoria).
      - O literal ``"dados_negocio"`` aparece apenas na constante
        ``KB_CATEGORIES``, nao em uma funcao de classificacao.

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (mesma assinatura da AC#1).
      2. Adicionar no corpo da funcao uma regra que combine a keyword
         ``rh`` com a extensao ``.xlsx`` (ou de modo mais amplo:
         planilhas com ``rh``/``funcionarios``/``payroll`` no nome) e
         retorne ``"dados_negocio"``.
    """
    source = _read_source(KB_SERVICE_PATH)

    # ── 1. Prerequisito: autoClassify deve estar exportada ─────────────
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#3 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "AC#3 exige que:\n"
            "  autoClassify(\n"
            "      'planilha_rh.xlsx',\n"
            "      'application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet',\n"
            "  )\n"
            "  => 'dados_negocio'\n\n"
            "Implemente primeiro a funcao `autoClassify` (veja AC#1) e "
            "depois adicione a regra combinando keyword `rh` + extensao "
            "`.xlsx` que retorne `'dados_negocio'`."
        )

    # ── 2. Localiza o corpo de autoClassify ───────────────────────────
    func_body_pattern = re.compile(
        r"export\s+function\s+autoClassify\s*\([^)]*\)\s*:\s*KBCategory\s*\{",
        re.DOTALL,
    )
    func_body_match = func_body_pattern.search(source)
    if func_body_match is None:
        pytest.fail(
            "AC#3 — RED.  Apos localizar `export function autoClassify`, "
            "nao foi possivel encontrar o corpo da funcao "
            "(`): KBCategory { ... }`)."
        )

    body_start = func_body_match.end()
    body = source[body_start:]

    # ── 3. Verifica que a keyword `rh` aparece no corpo ──────────────
    if not re.search(
        r"\b(?:rh|recursos\s+humanos|funcionarios|funcion[aá]rios|"
        r"employees|payroll|folha)\b",
        body,
        re.IGNORECASE,
    ):
        pytest.fail(
            "AC#3 — RED.  O corpo de `autoClassify` NAO referencia a "
            "keyword `rh` (ou variacoes como `recursos humanos`, "
            "`funcionarios`, `employees`, `payroll`, `folha`).\n\n"
            "Para que `autoClassify('planilha_rh.xlsx', "
            "'application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet')` retorne `'dados_negocio'`, o corpo "
            "da funcao deve inspecionar o `fileName` em busca de "
            "palavras-chave como `rh`, `funcionarios`, `payroll`, etc."
        )

    # ── 4. Verifica que a extensao `.xlsx` e' tratada no corpo ────────
    if not re.search(r"\.xlsx", body, re.IGNORECASE):
        pytest.fail(
            "AC#3 — RED.  O corpo de `autoClassify` NAO referencia a "
            "extensao `.xlsx`.\n\n"
            "AC#3 combina a keyword `rh` COM a extensao `.xlsx`.  A "
            "funcao deve inspecionar `getExtension(fileName)` ou "
            "comparar contra `.xlsx` explicitamente para classificar "
            "planilhas de RH em `'dados_negocio'`."
        )

    # ── 5. Verifica que a string literal "dados_negocio" aparece ──────
    if '"dados_negocio"' not in body and "'dados_negocio'" not in body:
        pytest.fail(
            "AC#3 — RED.  O corpo de `autoClassify` nao retorna a "
            "string literal `'dados_negocio'` em nenhum caminho.\n\n"
            "AC#3 exige que `autoClassify('planilha_rh.xlsx', "
            "'application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet')` retorne `'dados_negocio'`.\n\n"
            "Acrescente um branch que retorne `'dados_negocio'` para "
            "arquivos cuja `fileName` combine a keyword `rh` (ou "
            "variacoes) com a extensao `.xlsx`."
        )


# ── AC#4 — manual override (options?.category) ainda funciona ────────────


def test_b2_ac4_manual_override_funcional() -> None:
    """AC#4 — Manual override via ``options?.category`` deve continuar
    funcional apos a introducao de ``autoClassify``.

    Comportamento exigido:

      1. ``uploadFile`` (e/ou ``uploadSimpleFile``/``uploadComplexFile``)
         DEVE continuar aceitando o parametro
         ``options?: UploadOptions`` com o campo ``category`` (manual).
      2. Quando ``options?.category`` for fornecido explicitamente, esse
         valor DEVE prevalecer sobre a categoria retornada por
         ``autoClassify``.
      3. O fluxo de upload NAO deve quebrar ao adicionar
         ``autoClassify`` — a integracao deve usar ``autoClassify``
         apenas como fallback (quando ``options?.category`` nao e'
         fornecido).

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts`.
      - A integracao entre ``autoClassify`` e ``uploadFile`` NAO existe.
      - Embora ``uploadFile`` ja aceite ``options?: UploadOptions``
        hoje, a regra de fallback para ``autoClassify`` ainda nao foi
        adicionada (e nao pode ser adicionada enquanto a funcao nao
        existir).

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (mesma assinatura da AC#1).
      2. Em ``uploadFile`` (ou em ``uploadSimpleFile``/``uploadComplexFile``),
         usar a categoria manual quando ``options?.category`` for
         fornecido e cair para ``autoClassify(file.name, file.type)``
         quando nao for.
      3. Preservar a assinatura ``options?: UploadOptions`` em
         ``uploadFile``, ``uploadSimpleFile`` e ``uploadComplexFile``.
    """
    source = _read_source(KB_SERVICE_PATH)

    # ── 1. Prerequisito: autoClassify deve estar exportada ─────────────
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#4 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "AC#4 exige que a integracao entre `autoClassify` e "
            "`uploadFile`/`uploadSimpleFile`/`uploadComplexFile` "
            "esteja implementada de forma que `options?.category` "
            "(manual) prevaleça sobre a classificacao automatica.\n\n"
            "GREEN deve:\n"
            "  1. Exportar `autoClassify(fileName, fileType, metadata?)` "
            "— mesma assinatura da AC#1.\n"
            "  2. Em `uploadFile` (ou em seus delegates), usar "
            "`options?.category` quando fornecido e cair para "
            "`autoClassify(file.name, file.type)` como fallback.\n"
            "  3. Preservar a assinatura `options?: UploadOptions` em "
            "`uploadFile`, `uploadSimpleFile` e `uploadComplexFile`."
        )

    # ── 2. uploadFile deve continuar aceitando options?: UploadOptions
    upload_func_pattern = re.compile(
        r"export\s+async\s+function\s+uploadFile\s*\(([^)]*)\)",
        re.DOTALL,
    )
    upload_match = upload_func_pattern.search(source)
    if upload_match is None:
        pytest.fail(
            "AC#4 — RED.  Nao foi possivel localizar a funcao "
            "`uploadFile` em `knowledgeBaseService.ts`."
        )

    upload_params = upload_match.group(1)
    if not re.search(r"\boptions\s*\?\s*:\s*UploadOptions\b", upload_params):
        pytest.fail(
            "AC#4 — RED.  A funcao `uploadFile` NAO aceita o parametro "
            "`options?: UploadOptions`.\n\n"
            "O manual override exige que `options?.category` continue "
            "sendo aceito por `uploadFile`.  GREEN deve preservar a "
            "assinatura:\n"
            "  export async function uploadFile(\n"
            "      file: File,\n"
            "      clientId: string,\n"
            "      forceComplex?: boolean,\n"
            "      source?: KBDocumentSource,\n"
            "      options?: UploadOptions,\n"
            "  ): Promise<string>\n"
        )

    # ── 3. Corpo de uploadFile deve referenciar autoClassify ─────────
    #     (integracao via fallback: options?.category || autoClassify(...))
    func_body_pattern = re.compile(
        r"export\s+async\s+function\s+uploadFile\s*\([^)]*\)\s*:\s*"
        r"Promise\s*<\s*string\s*>\s*\{",
        re.DOTALL,
    )
    func_body_match = func_body_pattern.search(source)
    if func_body_match is None:
        pytest.fail(
            "AC#4 — RED.  Nao foi possivel localizar o corpo de "
            "`uploadFile` apos validar a assinatura "
            "(`): Promise<string> { ... }`)."
        )

    body_start = func_body_match.end()
    body = source[body_start:]

    if "autoClassify" not in body:
        pytest.fail(
            "AC#4 — RED.  O corpo de `uploadFile` NAO referencia "
            "`autoClassify`.\n\n"
            "Para que o manual override funcione em conjunto com a "
            "auto-classificacao, `uploadFile` (ou seus delegates "
            "`uploadSimpleFile` / `uploadComplexFile`) deve usar "
            "`autoClassify` como fallback quando `options?.category` "
            "NAO for fornecido, e usar `options?.category` (manual) "
            "quando estiver presente.\n\n"
            "Exemplo de logica esperada em `uploadFile`:\n"
            "  const category = options?.category\n"
            "      || autoClassify(file.name, file.type)\n"
            "  // ... usar `category` no insert do documento\n"
        )

    # ── 4. uploadSimpleFile / uploadComplexFile tambem devem aceitar
    #     `options?: UploadOptions` (sao os caminhos internos que
    #     efetivamente persistem a categoria no banco).
    for func_name in ("uploadSimpleFile", "uploadComplexFile"):
        simple_pattern = re.compile(
            rf"export\s+async\s+function\s+{func_name}\s*\(([^)]*)\)",
            re.DOTALL,
        )
        m = simple_pattern.search(source)
        if m is None:
            continue
        params = m.group(1)
        if not re.search(
            r"\boptions\s*\?\s*:\s*UploadOptions\b",
            params,
        ):
            pytest.fail(
                f"AC#4 — RED.  A funcao `{func_name}` NAO aceita o "
                f"parametro `options?: UploadOptions`.\n\n"
                f"O manual override deve ser honrado tambem em "
                f"`{func_name}` (chamada internamente por `uploadFile`). "
                f"GREEN deve preservar a assinatura "
                f"`options?: UploadOptions` em ambos os caminhos."
            )

    # ── 5. Verifica o padrao de fallback: options?.category || autoClassify
    #     Aceita `||` (coalescing com falsy) ou `??` (nullish coalescing).
    fallback_pattern = re.compile(
        r"options\s*\?\s*\.category\s*(?:\|\||\?\?)\s*autoClassify\s*\(",
        re.DOTALL,
    )
    if not fallback_pattern.search(source):
        pytest.fail(
            "AC#4 — RED.  Nao foi encontrada a logica de fallback que "
            "combina `options?.category` (manual) com `autoClassify(...)` "
            "(auto).\n\n"
            "O manual override so funciona corretamente se o codigo "
            "implementar um fallback do tipo:\n"
            "  const category = options?.category || autoClassify(\n"
            "      file.name, file.type,\n"
            "  )\n\n"
            "ou equivalentemente:\n"
            "  const category = options?.category ?? autoClassify(\n"
            "      file.name, file.type,\n"
            "  )\n\n"
            "Sem esse padrao, ou o manual override nao tera efeito "
            "(se `autoClassify` for usado direto), ou a auto-"
            "classificacao nao acontecera (se `options?.category` for "
            "usado direto sem fallback)."
        )
