"""RED test for behavior B-3 (BKL-036) — Classificacao automatica por extensao.

GOAL:
    A funcao ``autoClassify`` em ``knowledgeBaseService.ts`` deve inferir
    a categoria correta a partir da EXTENSAO do arquivo quando nenhuma
    keyword no nome bate.  Esta AC (AC#2) complementa a AC#1 (keywords no
    nome) cobrindo o fallback deterministico por extensao:

        .xlsx / .xls       -> "dados_negocio"   (planilha de dados)
        .pptx / .ppt       -> "documentos"      (apresentacao institucional)
        .pdf               -> "contexto_empresa"(documento textual)
        .jpg / .jpeg / .png / .svg / .webp / .gif
                           -> "imagens"         (asset visual)
        extensao ausente / desconhecida
                           -> "sem_categoria"   (fallback neutro)

BEHAVIOR:
    B-3 — Classificacao automatica de categoria (BKL-036).

    AC#2 — ``autoClassify`` DEVE mapear a extensao do arquivo para a
    categoria correta quando nenhum keyword match ocorre.  O
    mapeamento exigido e:

        extensao                -> categoria
        ────────────────────────────────────────
        .xlsx, .xls             -> "dados_negocio"
        .pptx, .ppt             -> "documentos"
        .pdf                    -> "contexto_empresa"
        .jpg, .jpeg, .png,
        .svg, .webp, .gif       -> "imagens"
        outra / ausente         -> "sem_categoria"

AC (Acceptance Criteria):
    AC#2 — A funcao ``autoClassify`` DEVE estar exportada de
           ``apps/blu_v3/src/services/knowledgeBaseService.ts`` e o
           corpo da funcao DEVE conter:

             1. Uma regra que reconheca a extensao ``.xlsx`` (ou
                variantes ``.xls``) e retorne ``"dados_negocio"``.
             2. Uma regra que reconheca a extensao ``.pptx`` (ou
                variantes ``.ppt``) e retorne ``"documentos"``.
             3. Uma regra que reconheca a extensao ``.pdf`` e retorne
                ``"contexto_empresa"``.
             4. Uma regra que reconheca extensoes de imagem
                (``.jpg``, ``.jpeg``, ``.png``, ``.svg``, ``.webp``,
                ``.gif``) e retorne ``"imagens"``.
             5. Um branch de fallback (default) que retorne
                ``"sem_categoria"`` para extensoes ausentes ou
                desconhecidas.

ESTADO ATUAL (RED):
    - ``apps/blu_v3/src/services/knowledgeBaseService.ts`` existe
      (339 linhas) e exporta ``KBCategory``, ``KB_CATEGORIES``,
      ``uploadFile``, ``listDocuments``, etc. — mas NAO exporta
      ``autoClassify``.
    - Nenhuma string ``autoClassify`` aparece no source.
    - Nenhuma das literais exigidas para o fallback por extensao
      (``"imagens"``, ``"sem_categoria"``) aparece no source.
    - As literais ``"dados_negocio"``, ``"documentos"`` e
      ``"contexto_empresa"`` aparecem apenas na constante
      ``KB_CATEGORIES`` (linhas 46-48), nao em uma funcao de
      classificacao.
    - Este teste falha (RED) ate que ``autoClassify`` seja
      implementada com a tabela de mapeamento por extensao descrita
      em AC#2.

ESTADO ALVO (GREEN):
    - Exportar ``autoClassify`` em ``knowledgeBaseService.ts``.
    - Adicionar mapeamento por extensao no corpo da funcao com
      cinco regras (xlsx, pptx, pdf, imagens, fallback).
    - Exemplo de mapeamento:
        if (/\.xlsx?$/i.test(fileName)) return 'dados_negocio'
        if (/\.pptx?$/i.test(fileName)) return 'documentos'
        if (/\.pdf$/i.test(fileName))     return 'contexto_empresa'
        if (/\.(?:jpe?g|png|svg|webp|gif)$/i.test(fileName))
                                            return 'imagens'
        return 'sem_categoria'

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
       -> dados_negocio por keyword) nem por
       ``test_b3_classificacao_auto_categoria.py`` (politica ->
       contexto_empresa por keyword) — esta AC#2 cobre o
       FALLBACK por extensao, nao keywords no nome.
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


def _extract_auto_classify_body(source: str) -> str:
    """Localiza o corpo de ``autoClassify`` em ``source`` e o retorna
    como string.  Emite ``pytest.fail`` se a funcao nao existir ou se
    a assinatura estiver incompleta.

    Estrategia: casamos ``export function autoClassify(...) : KBCategory {``
    e devolvemos tudo a partir do ``{`` de abertura ate o final do
    arquivo.  Como o teste e puramente estatico e o arquivo .ts tem
    escopo bem definido por funcoes top-level, esse ``slice`` e
    suficiente para procurarmos literais com regex.
    """
    export_pattern = re.compile(
        r"^\s*export\s+function\s+autoClassify\s*\(",
        re.MULTILINE,
    )
    if not export_pattern.search(source):
        pytest.fail(
            "AC#2 — RED.  A funcao `autoClassify` NAO esta exportada em "
            "`apps/blu_v3/src/services/knowledgeBaseService.ts`.\n\n"
            "AC#2 exige o mapeamento por extensao:\n"
            "  .xlsx / .xls    -> 'dados_negocio'\n"
            "  .pptx / .ppt    -> 'documentos'\n"
            "  .pdf            -> 'contexto_empresa'\n"
            "  .jpg/.png/.svg/ -> 'imagens'\n"
            "  unknown/empty   -> 'sem_categoria'\n\n"
            "Implemente primeiro a funcao `autoClassify` com a assinatura:\n"
            "  export function autoClassify(\n"
            "      fileName: string,\n"
            "      fileType: string,\n"
            "      metadata?: Record<string, string>,\n"
            "  ): KBCategory { ... }"
        )

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

    return source[func_body_match.end():]


# ── AC#2 — autoClassify mapeia extensao -> categoria ─────────────────────


def test_b3_ac2_classificacao_por_extensao() -> None:
    """AC#2 — ``autoClassify`` DEVE classificar pela extensao do
    arquivo quando nenhum keyword match ocorre.

    Mapeamento exigido (uma regra por extensao / grupo):

        extensao                -> categoria
        ──────────────────────────────────────────────────────
        .xlsx  (ou .xls)        -> "dados_negocio"
        .pptx  (ou .ppt)        -> "documentos"
        .pdf                    -> "contexto_empresa"
        .jpg/.jpeg/.png/.svg/
        .webp/.gif              -> "imagens"
        outra / ausente         -> "sem_categoria"

    Estado atual (RED):
      - ``autoClassify`` NAO esta exportada em
        ``apps/blu_v3/src/services/knowledgeBaseService.ts``.
      - Os literais ``"imagens"`` e ``"sem_categoria"`` NAO aparecem
        em lugar algum do source.
      - Os literais ``"dados_negocio"``, ``"documentos"`` e
        ``"contexto_empresa"`` aparecem apenas em
        ``KB_CATEGORIES`` (linhas 46-48), nao em uma funcao de
        classificacao.

    GREEN deve, no minimo:
      1. Exportar ``autoClassify`` (com assinatura completa).
      2. Adicionar cinco regras no corpo: xlsx->dados_negocio,
         pptx->documentos, pdf->contexto_empresa,
         imagens->imagens e fallback->sem_categoria.
    """
    source = _read_source(KB_SERVICE_PATH)
    body = _extract_auto_classify_body(source)

    # ── Regra 1: .xlsx / .xls -> "dados_negocio" ──────────────────────
    xlsx_pattern = re.compile(
        r"\.xlsx?",
        re.IGNORECASE,
    )
    if not xlsx_pattern.search(body):
        pytest.fail(
            "AC#2 — RED.  Regra 1/5 AUSENTE.  O corpo de `autoClassify` "
            "NAO referencia a extensao `.xlsx` (ou `.xls`).\n\n"
            "AC#2 exige que a extensao `.xlsx` mapeie para a "
            "categoria `'dados_negocio'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/\\.xlsx?$/i.test(fileName)) return 'dados_negocio'"
        )

    if '"dados_negocio"' not in body and "'dados_negocio'" not in body:
        pytest.fail(
            "AC#2 — RED.  Regra 1/5 SEM RETORNO.  Apos detectar `.xlsx`, "
            "o corpo de `autoClassify` nao retorna a string literal "
            "`'dados_negocio'`.\n\n"
            "AC#2 exige que `autoClassify('vendas.xlsx', "
            "'application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet')` retorne `'dados_negocio'`.\n\n"
            "Acrescente um branch que retorne `'dados_negocio'` para "
            "arquivos cuja extensao seja `.xlsx` ou `.xls`."
        )

    # ── Regra 2: .pptx / .ppt -> "documentos" ─────────────────────────
    pptx_pattern = re.compile(
        r"\.pptx?",
        re.IGNORECASE,
    )
    if not pptx_pattern.search(body):
        pytest.fail(
            "AC#2 — RED.  Regra 2/5 AUSENTE.  O corpo de `autoClassify` "
            "NAO referencia a extensao `.pptx` (ou `.ppt`).\n\n"
            "AC#2 exige que a extensao `.pptx` mapeie para a "
            "categoria `'documentos'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/\\.pptx?$/i.test(fileName)) return 'documentos'"
        )

    if '"documentos"' not in body and "'documentos'" not in body:
        pytest.fail(
            "AC#2 — RED.  Regra 2/5 SEM RETORNO.  Apos detectar `.pptx`, "
            "o corpo de `autoClassify` nao retorna a string literal "
            "`'documentos'`.\n\n"
            "AC#2 exige que `autoClassify('deck.pptx', "
            "'application/vnd.openxmlformats-officedocument."
            "presentationml.presentation')` retorne `'documentos'`.\n\n"
            "Acrescente um branch que retorne `'documentos'` para "
            "arquivos cuja extensao seja `.pptx` ou `.ppt`."
        )

    # ── Regra 3: .pdf -> "contexto_empresa" ──────────────────────────
    pdf_pattern = re.compile(
        r"\.pdf",
        re.IGNORECASE,
    )
    if not pdf_pattern.search(body):
        pytest.fail(
            "AC#2 — RED.  Regra 3/5 AUSENTE.  O corpo de `autoClassify` "
            "NAO referencia a extensao `.pdf`.\n\n"
            "AC#2 exige que a extensao `.pdf` mapeie para a "
            "categoria `'contexto_empresa'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/\\.pdf$/i.test(fileName)) return 'contexto_empresa'"
        )

    if '"contexto_empresa"' not in body and "'contexto_empresa'" not in body:
        pytest.fail(
            "AC#2 — RED.  Regra 3/5 SEM RETORNO.  Apos detectar `.pdf`, "
            "o corpo de `autoClassify` nao retorna a string literal "
            "`'contexto_empresa'`.\n\n"
            "AC#2 exige que `autoClassify('manual.pdf', "
            "'application/pdf')` retorne `'contexto_empresa'`.\n\n"
            "Acrescente um branch que retorne `'contexto_empresa'` para "
            "arquivos cuja extensao seja `.pdf`."
        )

    # ── Regra 4: imagens (.jpg/.jpeg/.png/.svg/.webp/.gif) -> "imagens" ──
    #     O pattern aceita tanto a forma string TS (".jpg") quanto a
    #     forma regex TS ("\\.jpe?g") — em ambos os casos a
    #     substring "jpe?g" ou "jpg"/"jpeg" aparece no source.
    image_pattern = re.compile(
        r"(?:jpe\?g|jpe?g|png|svg|webp|gif)",
        re.IGNORECASE,
    )
    if not image_pattern.search(body):
        pytest.fail(
            "AC#2 — RED.  Regra 4/5 AUSENTE.  O corpo de `autoClassify` "
            "NAO referencia nenhuma extensao de imagem "
            "(`.jpg`, `.jpeg`, `.png`, `.svg`, `.webp`, `.gif`).\n\n"
            "AC#2 exige que arquivos com extensao de imagem mapeiem "
            "para a categoria `'imagens'`.\n\n"
            "Exemplo de regra esperada:\n"
            "  if (/\\.(?:jpe?g|png|svg|webp|gif)$/i.test(fileName)) "
            "return 'imagens'"
        )

    if '"imagens"' not in body and "'imagens'" not in body:
        pytest.fail(
            "AC#2 — RED.  Regra 4/5 SEM RETORNO.  Apos detectar uma "
            "extensao de imagem, o corpo de `autoClassify` nao retorna "
            "a string literal `'imagens'`.\n\n"
            "AC#2 exige que `autoClassify('logo.png', 'image/png')`, "
            "`autoClassify('foto.jpg', 'image/jpeg')` e "
            "`autoClassify('icon.svg', 'image/svg+xml')` retornem "
            "`'imagens'`.\n\n"
            "Acrescente um branch que retorne `'imagens'` para "
            "arquivos cuja extensao seja `.jpg`, `.jpeg`, `.png`, "
            "`.svg`, `.webp` ou `.gif`."
        )

    # ── Regra 5: fallback (extensao ausente / desconhecida) -> "sem_categoria" ──
    if '"sem_categoria"' not in body and "'sem_categoria'" not in body:
        pytest.fail(
            "AC#2 — RED.  Regra 5/5 AUSENTE.  O corpo de `autoClassify` "
            "NAO retorna a string literal `'sem_categoria'` em nenhum "
            "caminho.\n\n"
            "AC#2 exige que a categoria `'sem_categoria'` seja o "
            "fallback para arquivos com extensao ausente (ex.: "
            "`'README'`) ou desconhecida (ex.: `'.xyz'`, `'.doc'` "
            "nao mapeado).\n\n"
            "Exemplo de regra esperada:\n"
            "  return 'sem_categoria'\n\n"
            "ou, garantindo que seja o default:\n"
            "  if (/\\.xlsx?$/i.test(fileName)) return 'dados_negocio'\n"
            "  if (/\\.pptx?$/i.test(fileName)) return 'documentos'\n"
            "  if (/\\.pdf$/i.test(fileName))     return "
            "'contexto_empresa'\n"
            "  if (/\\.(?:jpe?g|png|svg|webp|gif)$/i.test(fileName)) "
            "return 'imagens'\n"
            "  return 'sem_categoria'"
        )
