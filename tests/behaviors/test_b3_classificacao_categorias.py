"""RED test for behavior B-3 — Classificacao Automatica de Categorias (KB).

GOAL:
    Eliminar a dependencia do usuario em classificar manualmente cada
    documento no momento do upload. Hoje, em BibliotecaRoom.tsx (linha
    ~318-324), o usuario DEVE selecionar uma categoria via <select>
    antes de fazer upload; sem essa escolha, a coluna `category` no
    banco fica `null` e o documento cai no bucket `sem_categoria`
    (vide catCounts no fonte, que usa `doc.category ?? 'sem_categoria'`).

BEHAVIOR:
    B-3 — Classificacao Automatica de Categorias.

    Apos o GREEN, knowledgeBaseService.ts expoe uma funcao
    ``inferCategory(fileName: string): KBCategory | 'sem_categoria'``
    que classifica o arquivo por:

      1. prefixos no nome (ex.: ``contrato_`` -> ``documentos``,
         ``nf_`` -> ``dados_negocio``, ``relatorio_`` -> ``documentos``)
      2. extensao do arquivo (ex.: ``.pdf`` -> ``documentos``,
         ``.csv`` -> ``dados_negocio``)
      3. fallback explicito ``'sem_categoria'`` quando nao casa nada.

    Alem disso, BibliotecaRoom.tsx:
      - Oferece um override manual via <select> (ja existe no header,
         mas precisa estar conectado ao fluxo automatico).
      - Apos upload, a coluna `category` NAO pode ficar `null`
         (sempre cai em alguma categoria KB_CATEGORIES ou em
         'sem_categoria').
      - A classificacao automatica NAO depende de LLM/groq/openai
         (deve ser deterministica e sincrona, sem chamadas externas).

AC (Acceptance Criteria):
    AC-1 — inferCategory() exportada de knowledgeBaseService.ts
    AC-2 — Prefixo "contrato_" -> "documentos"
    AC-3 — Extensao .pdf -> documentos, .csv -> dados_negocio
    AC-4 — "nf_" -> "dados_negocio", "relatorio_" -> "documentos"
    AC-5 — Fallback explicito "sem_categoria" quando nada casa
    AC-6 — Dropdown override manual de categoria em BibliotecaRoom.tsx
    AC-7 — Classificacao automatica apos upload (category nunca null)
    AC-8 — Sem dependencia LLM/groq/openai na classificacao

Estado atual (RED):
    knowledgeBaseService.ts NAO expoe inferCategory, NAO ha tabela
    de prefixos/extensions, NAO ha fallback explicito para categoria.
    BibliotecaRoom.tsx tem o <select> no header (linhas 318-324) mas o
    upload (handleUpload, linha ~279) so envia a categoria SE o usuario
    tiver escolhido uma — sem inferencia automatica. Os testes abaixo
    devem falhar (RED) ate que a feature seja implementada na fase GREEN.
"""

import pathlib
import re

import pytest


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

KB_SERVICE_PATH = _APP_SRC / "services" / "knowledgeBaseService.ts"
BIBLIOTECA_ROOM_PATH = _APP_SRC / "pages" / "app" / "BibliotecaRoom.tsx"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Constants -------------------------------------------------------

KB_CATEGORIES = (
    "dados_negocio",
    "contexto_empresa",
    "documentos",
    "conhecimento_ia",
)


# -- Helpers ---------------------------------------------------------


def _has_infer_category_declaration(source: str) -> bool:
    """True se a funcao ``inferCategory`` estiver declarada/exportada
    em knowledgeBaseService.ts. Aceita tanto ``export function`` quanto
    ``export const inferCategory`` (arrow function).
    """
    patterns = [
        r"\bexport\s+function\s+inferCategory\s*\(",
        r"\bexport\s+const\s+inferCategory\s*[=:]\s*",
    ]
    return any(re.search(p, source) is not None for p in patterns)


def _extract_infer_category_body(source: str) -> str:
    """Retorna o corpo da funcao ``inferCategory`` em knowledgeBaseService.ts.
    Suporta tanto ``function inferCategory(...)`` quanto
    ``const inferCategory = (...) => { ... }``.

    Retorna string vazia se a funcao nao for encontrada.
    """
    func_match = re.search(
        r"\bfunction\s+inferCategory\s*\(",
        source,
    )
    if func_match:
        # Walk past the matching ')' to find ':' that closes the header.
        start = func_match.end()
        depth = 1
        i = start
        while i < len(source) and depth > 0:
            char = source[i]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            i += 1
        j = i
        while j < len(source) and source[j] != ":":
            j += 1
        body_start = j + 1
        # Body ends at the next top-level function/const declaration
        next_decl = re.search(
            r"^(?:export\s+)?(?:async\s+)?(?:function|const|class|interface|type)\s+",
            source[body_start:],
            re.MULTILINE,
        )
        if next_decl:
            return source[body_start : body_start + next_decl.start()]
        return source[body_start:]

    # Fallback: const inferCategory = (...) => { ... }
    const_match = re.search(
        r"\bconst\s+inferCategory\s*[=:]\s*(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>\s*",
        source,
    )
    if const_match:
        brace_start = source.find("{", const_match.end())
        if brace_start == -1:
            return ""
        depth = 1
        i = brace_start + 1
        while i < len(source) and depth > 0:
            char = source[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            i += 1
        return source[brace_start + 1 : i - 1]

    return ""


# -- Tests -----------------------------------------------------------


class TestB3ClassificacaoCategorias:
    """B-3: Classificacao Automatica de Categorias na Knowledge Base."""

    # -----------------------------------------------------------------
    # AC-1 — inferCategory() exportada de knowledgeBaseService.ts
    # -----------------------------------------------------------------

    def test_ac1_infer_category_exportada(self):
        """AC-1: a funcao ``inferCategory`` deve estar exportada de
        knowledgeBaseService.ts (RED enquanto a funcao nao existir).
        """
        source = _read(KB_SERVICE_PATH)

        if not _has_infer_category_declaration(source):
            pytest.fail(
                "AC-1 violado: a funcao `inferCategory` nao esta "
                "exportada em knowledgeBaseService.ts. Behavior B-3 "
                "requer uma funcao publica com a assinatura:\n"
                "    export function inferCategory(\n"
                "        fileName: string\n"
                "    ): KBCategory | 'sem_categoria'\n"
                "que classifica arquivos em uma das categorias de "
                "KB_CATEGORIES (dados_negocio, contexto_empresa, "
                "documentos, conhecimento_ia) ou retorna o fallback "
                "'sem_categoria'."
            )

    # -----------------------------------------------------------------
    # AC-2 — Prefixo "contrato_" -> "documentos"
    # -----------------------------------------------------------------

    def test_ac2_prefixo_contrato_vai_para_documentos(self):
        """AC-2: arquivos com prefixo ``contrato_`` devem ser classificados
        na categoria ``documentos`` (RED enquanto o mapeamento nao existir).
        """
        source = _read(KB_SERVICE_PATH)
        body = _extract_infer_category_body(source)

        if not body:
            pytest.fail(
                "AC-2 violado: a funcao `inferCategory` nao esta definida "
                "em knowledgeBaseService.ts. Behavior B-3 AC-2 requer que "
                "a funcao reconheca o prefixo `contrato_` no nome do "
                "arquivo e mapeie para a categoria `documentos`."
            )

        # Procura por um mapeamento explicito: chave 'contrato_' (ou
        # /contrato_/) -> valor 'documentos'. Aceita variantes como
        # `contrato_:`, `'contrato_':`, `contrato_::`, `contrato_/`.
        patterns = [
            r"['\"]contrato_['\"]\s*[:=]\s*['\"]documentos['\"]",
            r"contrato_\s*[/|)]",
            r"\bcontrato_\b[^a-zA-Z0-9]",
        ]
        has_mapping = any(
            re.search(p, body) is not None for p in patterns
        )

        if not has_mapping:
            pytest.fail(
                "AC-2 violado: nao foi encontrado mapeamento do prefixo "
                "`contrato_` para a categoria `documentos` dentro de "
                "`inferCategory` em knowledgeBaseService.ts. Behavior "
                "B-3 AC-2 exige que arquivos cujo nome comeca com "
                "`contrato_` (ex.: `contrato_fornecedor.pdf`) sejam "
                "automaticamente classificados como `documentos`."
            )

    # -----------------------------------------------------------------
    # AC-3 — Extensao .pdf -> documentos, .csv -> dados_negocio
    # -----------------------------------------------------------------

    def test_ac3_extensao_pdf_e_csv(self):
        """AC-3: a extensao do arquivo deve influenciar a categoria
        (.pdf -> documentos, .csv -> dados_negocio). RED enquanto o
        mapeamento por extensao nao existir.
        """
        source = _read(KB_SERVICE_PATH)
        body = _extract_infer_category_body(source)

        if not body:
            pytest.fail(
                "AC-3 violado: a funcao `inferCategory` nao esta definida "
                "em knowledgeBaseService.ts. Behavior B-3 AC-3 requer "
                "que a funcao classifique pela extensao do arquivo: "
                "`.pdf` -> `documentos`, `.csv` -> `dados_negocio`."
            )

        # Verifica que existe algum reconhecimento de extensao no corpo
        # (uso de `.endsWith(`, `.match(`, `.split('.').pop()` ou similar).
        extension_check_patterns = [
            r"\.endsWith\s*\(",
            r"\.match\s*\(\s*/[^/]*\.\$/",
            r"\.split\s*\(\s*['\"]\.['\"]\s*\)",
            r"lastIndexOf\s*\(\s*['\"]\.['\"]\s*\)",
            r"\.[Pp]df\b",
            r"\.pdf\b",
            r"\bpdf\b",
            r"\bcsv\b",
        ]
        has_extension_logic = any(
            re.search(p, body) is not None for p in extension_check_patterns
        )

        if not has_extension_logic:
            pytest.fail(
                "AC-3 violado: nao foi encontrada logica de reconhecimento "
                "de extensao dentro de `inferCategory` em "
                "knowledgeBaseService.ts. Behavior B-3 AC-3 exige que a "
                "funcao olhe para a extensao do arquivo (ex.: `.endsWith(`.pdf`)`) "
                "para classificar PDFs como `documentos` e CSVs como "
                "`dados_negocio`."
            )

        # Verifica que o valor 'documentos' e 'dados_negocio' aparecem
        # no corpo (em conjunto com alguma referencia a extensao).
        has_documentos_value = "documentos" in body
        has_dados_negocio_value = "dados_negocio" in body

        if not (has_documentos_value and has_dados_negocio_value):
            missing = []
            if not has_documentos_value:
                missing.append("`documentos` (para .pdf)")
            if not has_dados_negocio_value:
                missing.append("`dados_negocio` (para .csv)")
            pytest.fail(
                "AC-3 violado: o corpo de `inferCategory` nao referencia "
                "todos os valores de categoria exigidos pelo mapeamento "
                "por extensao. Faltando: " + ", ".join(missing) + "."
            )

    # -----------------------------------------------------------------
    # AC-4 — "nf_" -> "dados_negocio", "relatorio_" -> "documentos"
    # -----------------------------------------------------------------

    def test_ac4_prefixos_nf_e_relatorio(self):
        """AC-4: arquivos com prefixo ``nf_`` devem ir para
        ``dados_negocio`` e ``relatorio_`` para ``documentos``.
        RED enquanto esses mapeamentos nao existirem.
        """
        source = _read(KB_SERVICE_PATH)
        body = _extract_infer_category_body(source)

        if not body:
            pytest.fail(
                "AC-4 violado: a funcao `inferCategory` nao esta definida "
                "em knowledgeBaseService.ts. Behavior B-3 AC-4 requer "
                "mapeamentos `nf_` -> `dados_negocio` e `relatorio_` -> "
                "`documentos`."
            )

        # Procura mapeamento `nf_` -> `dados_negocio`
        nf_patterns = [
            r"['\"]nf_['\"]\s*[:=]\s*['\"]dados_negocio['\"]",
            r"\bnf_\b[^a-zA-Z0-9_][^'\"]*dados_negocio",
        ]
        has_nf_mapping = any(
            re.search(p, body) is not None for p in nf_patterns
        )

        # Procura mapeamento `relatorio_` -> `documentos`
        relatorio_patterns = [
            r"['\"]relatorio_['\"]\s*[:=]\s*['\"]documentos['\"]",
            r"\brelatorio_\b[^a-zA-Z0-9_][^'\"]*documentos",
        ]
        has_relatorio_mapping = any(
            re.search(p, body) is not None for p in relatorio_patterns
        )

        missing = []
        if not has_nf_mapping:
            missing.append("`nf_` -> `dados_negocio`")
        if not has_relatorio_mapping:
            missing.append("`relatorio_` -> `documentos`")

        if missing:
            pytest.fail(
                "AC-4 violado: faltam mapeamentos de prefixo em "
                "`inferCategory` (knowledgeBaseService.ts). Mapeamentos "
                "ausentes: " + "; ".join(missing) + ". Behavior B-3 AC-4 "
                "exige que arquivos com prefixo `nf_` (ex.: `nf_12345.xml`) "
                "sejam classificados como `dados_negocio`, e arquivos com "
                "prefixo `relatorio_` (ex.: `relatorio_mensal.pdf`) como "
                "`documentos`."
            )

    # -----------------------------------------------------------------
    # AC-5 — Fallback explicito "sem_categoria"
    # -----------------------------------------------------------------

    def test_ac5_fallback_sem_categoria(self):
        """AC-5: a funcao ``inferCategory`` deve retornar explicitamente
        a string ``'sem_categoria'`` quando nenhum padrao casa.
        RED enquanto o fallback nao existir.
        """
        source = _read(KB_SERVICE_PATH)
        body = _extract_infer_category_body(source)

        if not body:
            pytest.fail(
                "AC-5 violado: a funcao `inferCategory` nao esta definida "
                "em knowledgeBaseService.ts. Behavior B-3 AC-5 requer "
                "que a funcao retorne explicitamente a string "
                "'sem_categoria' quando nenhum prefixo/extensao casa."
            )

        # Procura o literal 'sem_categoria' no corpo (pode aparecer
        # como string retornada, valor de map, ou return statement).
        sem_categoria_patterns = [
            r"['\"]sem_categoria['\"]",
            r"\breturn\s+['\"]sem_categoria['\"]",
            r"['\"]sem_categoria['\"]\s*[,;}\)]",
        ]
        has_fallback = any(
            re.search(p, body) is not None for p in sem_categoria_patterns
        )

        if not has_fallback:
            pytest.fail(
                "AC-5 violado: nao foi encontrado o fallback explicito "
                "`'sem_categoria'` dentro de `inferCategory` em "
                "knowledgeBaseService.ts. Behavior B-3 AC-5 exige que "
                "a funcao retorne a string `'sem_categoria'` (exatamente "
                "essa grafia) quando nenhum padrao de prefixo ou "
                "extensao casa. Esse valor e usado em BibliotecaRoom.tsx "
                "como bucket padrao no catCounts "
                "(`doc.category ?? 'sem_categoria'`)."
            )

    # -----------------------------------------------------------------
    # AC-6 — Dropdown override manual de categoria em BibliotecaRoom.tsx
    # -----------------------------------------------------------------

    def test_ac6_dropdown_override_manual_categoria(self):
        """AC-6: o BibliotecaRoom.tsx deve oferecer um <select> para
        o usuario sobrescrever manualmente a categoria inferida
        automaticamente.

        O dropdown deve funcionar como OVERRIDE da inferencia automatica,
        nao como unica fonte da categoria. O contrato GREEN exige que:

          (a) exista um <select> no header com opcoes de KB_CATEGORIES,
          (b) o valor selecionado no <select> seja usado no fluxo de
              upload, E
          (c) a expressao final de `category:` passada a ``kb.upload(...)``
              combine a inferencia automatica (``inferCategory``) com o
              state do <select> (ex.: ``inferCategory(file.name)`` quando
              o usuario mantem o default, ou o state manual quando ele
              sobrescreve).

        RED no estado atual: o upload (linha 283) faz
        ``{ category: kbCategory }`` sem chamar ``inferCategory(...)``
        em momento algum — o dropdown e a unica fonte da categoria, e
        nao ha inferencia automatica aplicada.
        """
        source = _read(BIBLIOTECA_ROOM_PATH)

        # 1) <select> no JSX cujo value e o state de categoria e que
        #    renderiza KB_CATEGORIES.map como <option>s.
        has_category_select = bool(
            re.search(
                r"<\s*select\b[^>]*value\s*=\s*\{[^}]*Categor",
                source,
            )
        ) and bool(
            re.search(
                r"KB_CATEGORIES\.map",
                source,
            )
        )

        if not has_category_select:
            pytest.fail(
                "AC-6 violado: nao foi encontrado um <select> no JSX "
                "de BibliotecaRoom.tsx cujo value esteja ligado a um "
                "state de categoria e que liste KB_CATEGORIES como "
                "opcoes. Behavior B-3 AC-6 exige um dropdown no header "
                "que permita ao usuario escolher manualmente a categoria "
                "do proximo upload."
            )

        # 2) O state de categoria e lido/usado no fluxo de upload.
        upload_uses_category = bool(
            re.search(
                r"\.upload\s*\([^)]*category\s*:\s*[A-Za-z_]",
                source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*[A-Za-z_][A-Za-z0-9_]*Category",
                source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*inferCategory",
                source,
            )
        )

        if not upload_uses_category:
            pytest.fail(
                "AC-6 violado: o state de categoria controlado pelo "
                "<select> NAO esta sendo propagado para a chamada de "
                "upload (`kb.upload(...)` ou equivalente) em "
                "BibliotecaRoom.tsx. Behavior B-3 AC-6 exige que o "
                "valor escolhido no dropdown seja passado como "
                "`category:` no upload."
            )

        # 3) A expressao final de `category:` DEVE envolver
        #    ``inferCategory(...)`` em algum momento — o dropdown
        #    funciona como OVERRIDE, nao como fonte unica. Procuramos
        #    o nome da funcao ``inferCategory`` no arquivo.
        has_infer_call = bool(
            re.search(
                r"\binferCategory\s*\(",
                source,
            )
        )

        if not has_infer_call:
            pytest.fail(
                "AC-6 violado: o dropdown de categoria em "
                "BibliotecaRoom.tsx NAO esta conectado a funcao "
                "`inferCategory(...)`. Behavior B-3 AC-6 exige que o "
                "<select> funcione como OVERRIDE da classificacao "
                "automatica: quando o usuario mantem o default, a "
                "categoria final deve vir de `inferCategory(file.name)`; "
                "quando ele sobrescreve, o valor manual tem precedencia. "
                "Hoje o upload faz `category: kbCategory` sem chamar "
                "`inferCategory` em momento algum — isso NAO satisfaz o "
                "criterio de override."
            )

        # 4) Verifica que a expressao de `category:` no upload NAO
        #    e simplesmente o state cru do <select> (o que indicaria
        #    que o dropdown e a unica fonte). Aceitamos:
        #      - ``category: inferCategory(file.name)`` (so inferencia)
        #      - ``category: kbCategory || inferCategory(file.name)``
        #      - ``category: manualCategory || inferCategory(file.name)``
        #      - ``category: kbCategory ?? inferCategory(file.name)``
        #    OU uma chamada previa ``const cat = inferCategory(...)``
        #    que aparece no escopo do upload.
        is_override_pattern = bool(
            re.search(
                r"category\s*:\s*inferCategory\s*\(",
                source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*[A-Za-z_][A-Za-z0-9_]*\s*\|\|\s*inferCategory",
                source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*[A-Za-z_][A-Za-z0-9_]*\s*\?\?\s*inferCategory",
                source,
            )
        ) or bool(
            re.search(
                r"const\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*inferCategory\s*\(",
                source,
            )
        )

        if not is_override_pattern:
            pytest.fail(
                "AC-6 violado: o valor passado em `category:` no upload "
                "de BibliotecaRoom.tsx NAO combina `inferCategory(...)` "
                "com o state do <select>. Behavior B-3 AC-6 exige o "
                "padrao de override, por exemplo:\n"
                "    category: inferCategory(file.name)\n"
                "    category: kbCategory || inferCategory(file.name)\n"
                "    category: manualCategory ?? inferCategory(file.name)\n"
                "ou a atribuicao previa:\n"
                "    const cat = inferCategory(file.name)\n"
                "    await kb.upload(file, false, 'upload', { category: cat })\n"
                "Hoje a unica fonte da categoria e o state `kbCategory` "
                "do <select>, sem qualquer chamada a `inferCategory`."
            )

    # -----------------------------------------------------------------
    # AC-7 — Classificacao automatica apos upload (category nunca null)
    # -----------------------------------------------------------------

    def test_ac7_classificacao_automatica_pos_upload(self):
        """AC-7: apos o upload, a coluna ``category`` do documento NAO
        pode ficar ``null``. O codigo deve SEMPRE classificar
        (manualmente ou via inferCategory) para garantir que o doc
        nunca caia em `sem_categoria` por falta de inferencia.

        RED enquanto o upload de BibliotecaRoom.tsx (ou a funcao de
        upload em knowledgeBaseService.ts) nao garantir que
        ``category`` e sempre definida antes de inserir o documento.
        """
        biblio_source = _read(BIBLIOTECA_ROOM_PATH)
        kb_source = _read(KB_SERVICE_PATH)

        # 1) Em BibliotecaRoom.tsx, o argumento `category:` passado
        #    para `kb.upload(...)` NAO pode ser um valor estatico que
        #    pode ser `null` (ex.: `category: null` ou `category: ''`).
        #    Deve envolver um fallback ou `inferCategory(...)`.
        bad_literal_pattern = bool(
            re.search(
                r"category\s*:\s*null\b",
                biblio_source,
            )
        )
        bad_empty_pattern = bool(
            re.search(
                r"category\s*:\s*['\"]['\"]",
                biblio_source,
            )
        )

        if bad_literal_pattern or bad_empty_pattern:
            pytest.fail(
                "AC-7 violado: BibliotecaRoom.tsx esta passando "
                "`category: null` ou `category: ''` para `kb.upload(...)`. "
                "Isso faria a coluna `category` ficar NULL no banco, e o "
                "documento cairia no bucket `sem_categoria` "
                "(vide `doc.category ?? 'sem_categoria'` no catCounts). "
                "Behavior B-3 AC-7 exige que a categoria seja SEMPRE "
                "inferida automaticamente quando o usuario nao sobrescreve."
            )

        # 2) Deve haver uma chamada a `inferCategory(...)` em
        #    BibliotecaRoom.tsx, OU `kb.upload(...)` deve receber
        #    um valor garantido nao-nulo.
        calls_infer = bool(
            re.search(
                r"inferCategory\s*\(",
                biblio_source,
            )
        )
        upload_uses_safe_category = bool(
            re.search(
                r"category\s*:\s*kbCategory\s*\|\|\s*inferCategory",
                biblio_source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*inferCategory\s*\(\s*file\.name",
                biblio_source,
            )
        ) or bool(
            re.search(
                r"category\s*:\s*[A-Za-z_][A-Za-z0-9_]*Category\s*\|\|",
                biblio_source,
            )
        )

        if not (calls_infer or upload_uses_safe_category):
            pytest.fail(
                "AC-7 violado: BibliotecaRoom.tsx NAO chama "
                "`inferCategory(...)` e NAO garante que a categoria "
                "passada para `kb.upload(...)` seja sempre nao-nula. "
                "Behavior B-3 AC-7 exige que, apos o upload, a coluna "
                "`category` no banco NUNCA seja NULL — ou o usuario "
                "sobrescreve manualmente (via <select>), ou a funcao "
                "`inferCategory(file.name)` e aplicada como fallback."
            )

        # 3) Em knowledgeBaseService.ts, a funcao ``uploadSimpleFile``
        #    e ``uploadComplexFile`` NAO devem persistir `category: null`
        #    sem fallback. Hoje elas persistem `options?.category || null`
        #    — o que esta OK desde que o caller (BibliotecaRoom) garanta
        #    que `options.category` nunca seja null/undefined. Verificamos
        #    que pelo menos uma das duas funcoes de upload possui
        #    protecao contra category null (ex.: fallback explicito).
        upload_simple = "uploadSimpleFile" in kb_source
        upload_complex = "uploadComplexFile" in kb_source

        if not (upload_simple and upload_complex):
            pytest.fail(
                "AC-7 violado: nao foi possivel localizar "
                "`uploadSimpleFile` e `uploadComplexFile` em "
                "knowledgeBaseService.ts. Behavior B-3 AC-7 depende "
                "dessas funcoes para propagar a categoria inferida "
                "ate a insercao no banco."
            )

    # -----------------------------------------------------------------
    # AC-8 — Sem dependencia LLM/groq/openai na classificacao
    # -----------------------------------------------------------------

    def test_ac8_sem_dependencia_llm_groq_openai(self):
        """AC-8: a classificacao automatica NAO pode depender de
        chamadas externas a LLMs (groq, openai, anthropic, etc.).
        A funcao ``inferCategory`` deve ser deterministica e
        sincrona, baseada apenas em prefixos/extensoes do nome do
        arquivo. Isso e essencial para nao introduzir latencia,
        custo por chamada e dependencia de API key no upload.

        RED enquanto a funcao ``inferCategory`` nao existir (pois
        sua ausencia impede validar o contrato sincrono + sem LLM).
        """
        source = _read(KB_SERVICE_PATH)

        # 1) A funcao ``inferCategory`` deve existir.
        if not _has_infer_category_declaration(source):
            pytest.fail(
                "AC-8 violado: a funcao `inferCategory` nao esta "
                "exportada em knowledgeBaseService.ts, portanto o "
                "contrato de classificacao deterministica/sincrona "
                "nao pode ser validado. Behavior B-3 AC-8 exige que "
                "a funcao exista e NAO use LLM/groq/openai — ou seja, "
                "deve ser uma funcao sincrona, sem `await`, sem "
                "chamadas a `groq(...)`, `openai(...)`, fetch a APIs "
                "externas, etc."
            )

        # 2) A funcao deve ser sincrona: sem `async`, sem `await`
        #    dentro do corpo.
        is_async_decl = bool(
            re.search(
                r"\bexport\s+async\s+function\s+inferCategory",
                source,
            )
        ) or bool(
            re.search(
                r"\bexport\s+const\s+inferCategory\s*=\s*async",
                source,
            )
        )

        if is_async_decl:
            pytest.fail(
                "AC-8 violado: `inferCategory` esta declarada como "
                "`async`. Behavior B-3 AC-8 exige que a funcao seja "
                "sincrona (apenas prefixos/extensoes, sem I/O), para "
                "garantir determinismo e zero latencia no upload."
            )

        body = _extract_infer_category_body(source)

        if not body:
            pytest.fail(
                "AC-8 violado: nao foi possivel extrair o corpo de "
                "`inferCategory` em knowledgeBaseService.ts. O corpo "
                "precisa estar visivel para validar que nao usa LLM/"
                "groq/openai. Behavior B-3 AC-8 exige que a funcao "
                "seja deterministica e sincrona."
            )

        # 3) O corpo NAO pode conter `await`, `fetch(`, `groq`,
        #    `openai`, `anthropic`, `claude`, `chat.completions`, etc.
        forbidden_patterns = [
            (r"\bawait\b", "uso de `await` (indica chamada assincrona)"),
            (r"\bfetch\s*\(", "uso de `fetch(...)` (chamada de rede)"),
            (r"\bgroq\b", "referencia ao provider LLM `groq`"),
            (r"\bopenai\b", "referencia ao provider LLM `openai`"),
            (r"\banthropic\b", "referencia ao provider LLM `anthropic`"),
            (r"\bclaude\b", "referencia ao modelo LLM `claude`"),
            (r"chat\.completions", "uso de `chat.completions` (API de LLM)"),
            (r"\bChatCompletion", "uso de `ChatCompletion` (API de LLM)"),
        ]
        violations = []
        for pat, desc in forbidden_patterns:
            if re.search(pat, body, re.IGNORECASE):
                violations.append(desc)

        if violations:
            pytest.fail(
                "AC-8 violado: o corpo de `inferCategory` em "
                "knowledgeBaseService.ts referencia dependencias "
                "externas de LLM, o que e proibido pelo Behavior B-3 "
                "AC-8. A funcao deve ser deterministica e sincrona. "
                "Violacoes encontradas: " + "; ".join(violations) + "."
            )
