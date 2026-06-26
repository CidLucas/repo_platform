"""RED test for behavior B-5 — Exibe error_message do documento no frontend
com fallback "Erro desconhecido".

GOAL:
    Garantir que documentos da Biblioteca de Conhecimento com
    status ``failed`` ou ``partially_failed`` exibam SEMPRE uma
    indicação de erro visível para o usuário, mesmo quando o
    backend não fornece ``error_message`` (campo null/undefined).

    Comportamento esperado em
    ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``:
      - Se ``doc.error_message`` está preenchido  → renderiza
        ``doc.error_message`` (já funciona).
      - Se ``doc.error_message`` é null/undefined  → renderiza o
        texto canônico ``Erro desconhecido`` (FALTA — RED).

BEHAVIOR:
    B-5 — Exibe error_message do documento no frontend.

    O componente ``BibliotecaRoom.tsx`` contém dois sub-componentes
    que renderizam cada linha/card de documento:

    1. ``DocCard`` (linhas 69-211) — view em grade.
       Bloco de erro atual (linhas 171-175):
         {(doc.status === 'failed' || doc.status === 'partially_failed')
             && doc.error_message && (
           <div ...>{doc.error_message}</div>
         )}
       O operador ``&& doc.error_message`` curto-circuita a render
       quando a string é vazia/null.  Nenhum fallback é mostrado.

    2. ``DocRow`` (linhas 215-275) — view em lista.
       Bloco de erro atual (linhas 252-256): mesmo padrão.

    O usuário final vê um card/linha "Processado em dd-mm-yyyy" sem
    nenhuma pista de que o upload falhou quando o backend não
    embute a mensagem técnica.  O behavior B-5 elimina esse caso
    adicionando o fallback ``Erro desconhecido``.

    **Estado atual (RED):**
      - ``DocCard`` e ``DocRow`` NAO contêm a string "Erro
        desconhecido" em nenhum lugar.
      - O usuário fica sem informação quando ``error_message`` é
        null.

    **Estado alvo (GREEN):**
      - Em ``DocCard`` (linhas ~171-175) e ``DocRow`` (linhas
        ~252-256), o bloco de erro deve ramificar a renderização:
            doc.error_message
              ? doc.error_message
              : "Erro desconhecido"
        (ou lógica equivalente que produza a string literal
        "Erro desconhecido" no output JSX).

AC (Acceptance Criteria):
    AC#1 — ``DocCard`` em ``BibliotecaRoom.tsx`` renderiza
            ``doc.error_message`` quando o campo está preenchido.
            (GREEN, já existe — protege a feature atual de regressão.)
    AC#2 — ``DocCard`` em ``BibliotecaRoom.tsx`` possui fallback
            ``"Erro desconhecido"`` para o caso
            ``doc.error_message`` null/undefined.  (RED — não
            existe no código atual.)
    AC#3 — ``DocRow`` em ``BibliotecaRoom.tsx`` renderiza
            ``doc.error_message`` quando o campo está preenchido.
            (GREEN, já existe — protege a feature atual de regressão.)
    AC#4 — ``DocRow`` em ``BibliotecaRoom.tsx`` possui fallback
            ``"Erro desconhecido"`` para o caso
            ``doc.error_message`` null/undefined.  (RED — não
            existe no código atual.)

DECISAO:
    Estratégia: source_inspection (regex textual, sem parser TS).
    Arquivo alvo: apps/blu_v3/src/pages/app/BibliotecaRoom.tsx

    Os corpos de ``DocCard`` e ``DocRow`` são extraídos por uma
    rotina de contagem de chaves (matching braces) a partir de
    ``function DocCard({…}) {`` e ``function DocRow({…}) {``.
    Cada AC#k então roda regex somente sobre o corpo do
    componente relevante — evita falso-positivo caso a string
    "Erro desconhecido" seja adicionada em outro lugar do
    arquivo (ex.: tooltip, docstring).

Anti-Goals (must NOT be violated):
    1. NAO modificar código de produção — o teste é puramente
       estático.  A implementação será feita na fase GREEN.
    2. NAO importar ou executar código TypeScript/React — apenas
       leitura de texto via ``Path.read_text()``.
    3. NAO usar fixtures de DB ou rede — o teste é determinístico
       e roda offline.
    4. NAO usar ``assert`` — toda falha é reportada via
       ``pytest.fail()`` com mensagem em pt-BR, conforme
       convenção deste projeto.
    5. NAO checar a string "Erro desconhecido" no arquivo inteiro
       (pode gerar falso-positivo se aparecer em comentário fora
       do componente).  A inspeção é sempre escopada ao corpo do
       componente.
"""

import re
from pathlib import Path

import pytest


# ── Paths da interface pública sob teste ────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

BIBLIOTECA_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)


# ── Override do root conftest (teste puramente estático) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste
    é pura inspeção de arquivos, sem necessidade de teardown no
    Supabase.
    """
    yield


# ── Helpers de inspeção ─────────────────────────────────────────────


def _biblioteca_source() -> str:
    """Lê o arquivo ``BibliotecaRoom.tsx`` como texto único (utf-8).

    Raises:
        pytest.Failed: se o arquivo não existir.
    """
    if not BIBLIOTECA_PATH.exists():
        pytest.fail(
            "Pre-condicao violada: arquivo "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)} NAO encontrado.  "
            "O behavior B-5 (exibicao de error_message com fallback) "
            "exige que este arquivo exista no repositorio."
        )
    return BIBLIOTECA_PATH.read_text(encoding="utf-8")


def _extract_function_body(src: str, function_name: str) -> str:
    """Devolve o corpo (entre chaves) da primeira definicao de
    ``function <function_name>(...)`` encontrada em ``src``.

    Implementa contagem manual de parenteses para localizar o
    final da lista de parametros (necessario porque a assinatura
    pode conter ``()`` aninhados em tipos como
    ``(id: string) => Promise<void>``) e, depois, contagem
    manual de chaves para delimitar o corpo da funcao (com
    tratamento de strings e comentarios para nao confundir
    chaves em literais).

    Retorna ``""`` se a funcao NAO for encontrada ou se a
    extracao falhar — os testes que dependem do corpo tratam
    isso como falha explicita via ``pytest.fail()``.

    Args:
        src:        texto completo do arquivo TSX.
        function_name: nome da funcao (ex.: ``"DocCard"``).

    Returns:
        String com o conteudo entre ``{`` e o ``}`` de fechamento
        da funcao, sem incluir as proprias chaves delimitadoras.
        Retorna ``""`` se a funcao nao for encontrada.
    """
    # 1. Localizar a string "function <name>(" no source
    sig_match = re.search(
        rf"function\s+{re.escape(function_name)}\s*\(",
        src,
    )
    if sig_match is None:
        return ""

    # 2. A partir do '(' da lista de parametros, contar parenteses
    #    (aninhados) para achar o ')' que fecha a lista de
    #    parametros.  Ignora conteudo de strings/comentarios.
    paren_open_pos = sig_match.end() - 1
    n = len(src)

    def _find_matching_paren(start: int) -> int:
        """Retorna o indice do ')' que fecha o '(' em ``start``.
        Retorna -1 se nao encontrar.
        """
        depth = 1
        i = start + 1
        in_single = False
        in_double = False
        in_template = False
        in_line_comment = False
        in_block_comment = False
        while i < n:
            ch = src[i]
            nxt = src[i + 1] if i + 1 < n else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_single:
                if ch == "\\":
                    i += 2
                    continue
                if ch == "'":
                    in_single = False
                i += 1
                continue
            if in_double:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_double = False
                i += 1
                continue
            if in_template:
                if ch == "\\":
                    i += 2
                    continue
                if ch == "`":
                    in_template = False
                i += 1
                continue
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == "'":
                in_single = True
                i += 1
                continue
            if ch == '"':
                in_double = True
                i += 1
                continue
            if ch == "`":
                in_template = True
                i += 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    paren_close_pos = _find_matching_paren(paren_open_pos)
    if paren_close_pos < 0:
        return ""

    # 3. A partir do ')' que fecha a lista de parametros, pular
    #    qualquer tipo de retorno anotado (ate ': TypeName') ate
    #    encontrar o '{' que abre o corpo da funcao.  O ':' e o
    #    '{' estao na mesma linha, possivelmente separados por
    #    espacos / tipo.
    i = paren_close_pos + 1
    while i < n and src[i] != "{":
        i += 1
    if i >= n:
        return ""
    body_open_pos = i  # posicao do '{' que abre o corpo

    # 4. Contar chaves a partir do '{' de abertura do corpo, com
    #    tratamento de strings/comentarios, ate fechar depth=0.
    depth = 1
    j = body_open_pos + 1
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False
    while j < n and depth > 0:
        ch = src[j]
        nxt = src[j + 1] if j + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            j += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                j += 2
                continue
            j += 1
            continue
        if in_single:
            if ch == "\\":
                j += 2
                continue
            if ch == "'":
                in_single = False
            j += 1
            continue
        if in_double:
            if ch == "\\":
                j += 2
                continue
            if ch == '"':
                in_double = False
            j += 1
            continue
        if in_template:
            if ch == "\\":
                j += 2
                continue
            if ch == "`":
                in_template = False
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            j += 2
            continue
        if ch == "'":
            in_single = True
            j += 1
            continue
        if ch == '"':
            in_double = True
            j += 1
            continue
        if ch == "`":
            in_template = True
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[body_open_pos + 1:j]
        j += 1
    return ""


# ── AC#1 — DocCard renderiza error_message quando presente ─────────


def test_b5_ac1_doccard_renders_error_message_when_present():
    """AC#1: o componente ``DocCard`` em ``BibliotecaRoom.tsx``
    DEVE renderizar ``doc.error_message`` quando o campo tem
    valor (protecao de feature existente — GREEN).

    Verifica que o corpo de ``DocCard`` contem o padrao de
    curto-circuito ``doc.error_message && ( ... <JSX> ... )`` ou
    ternario ``doc.error_message ? ... : ...`` referenciando
    ``doc.error_message`` como children de um elemento JSX.

    Estado atual (GREEN): DocCard (linhas 171-175) ja faz isso:
        {(doc.status === 'failed' || doc.status === 'partially_failed')
            && doc.error_message && (
          <div ...>{doc.error_message}</div>
        )}
    """
    src = _biblioteca_source()
    body = _extract_function_body(src, "DocCard")

    if not body:
        pytest.fail(
            "AC#1 — pre-condicao violada: nao foi possivel extrair o "
            "corpo de ``function DocCard(…)`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)}.  O componente "
            "DocCard deve estar presente no arquivo para o behavior "
            "B-5 funcionar."
        )

    # Procura referencia a doc.error_message no JSX (nao em
    # atributo, mas como children ou como condicional).
    # Aceita os dois padroes mais provaveis: curto-circuito && ou
    # ternario ?:.  O teste passa se doc.error_message aparece
    # dentro de uma expressao JSX condicional e tambem e usado
    # como conteudo a ser renderizado.
    has_reference = bool(re.search(r"doc\.error_message", body))
    has_conditional_render = bool(
        re.search(
            r"doc\.error_message\s*[?:&]|\{\s*doc\.error_message\s*[,}]"
            r"|doc\.error_message\s*\?",
            body,
        )
    )

    if not (has_reference and has_conditional_render):
        pytest.fail(
            "AC#1 violada — feature atual quebrada.  O componente "
            "``DocCard`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)} NAO esta "
            "renderizando ``doc.error_message`` quando o campo esta "
            "preenchido.  O usuario nao ve a mensagem de erro tecnica "
            "fornecida pelo backend.\n\n"
            "Esperado (padrao atual, GREEN):\n"
            "  {(doc.status === 'failed' || doc.status === 'partially_failed')\n"
            "      && doc.error_message && (\n"
            "    <div title={doc.error_message} ...>\n"
            "      {doc.error_message}\n"
            "    </div>\n"
            "  )}\n\n"
            "Reimplante essa logica de renderizacao condicional "
            "baseada em doc.error_message dentro do JSX de DocCard."
        )


# ── AC#2 — DocCard tem fallback "Erro desconhecido" (RED) ───────────


def test_b5_ac2_doccard_has_unknown_error_fallback():
    """AC#2: o componente ``DocCard`` em ``BibliotecaRoom.tsx``
    DEVE possuir o fallback textual ``"Erro desconhecido"`` que
    aparece quando ``doc.error_message`` e null/undefined.

    Verifica que a string literal ``Erro desconhecido`` aparece
    no corpo de ``DocCard``.  O RED atual e que o componente
    silenciosamente NAO renderiza nada quando error_message
    esta vazio — o usuario nao sabe que houve erro.

    Estado atual (RED): DocCard (linhas 171-175) usa
    ``&& doc.error_message`` que curto-circuita a render quando
    a string e vazia/null.  A string ``Erro desconhecido`` NAO
    aparece em lugar nenhum do componente.

    Depois (GREEN): o codigo deve ramificar a renderizacao,
    por exemplo:

        {doc.error_message
          ? doc.error_message
          : 'Erro desconhecido'}

    OU usar operador ``||`` com string literal:

        {(doc.error_message || 'Erro desconhecido')}

    O importante e que ``Erro desconhecido`` (case-sensitive)
    seja parte do JSX/condicional de DocCard.
    """
    src = _biblioteca_source()
    body = _extract_function_body(src, "DocCard")

    if not body:
        pytest.fail(
            "AC#2 — pre-condicao violada: nao foi possivel extrair o "
            "corpo de ``function DocCard(…)`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)}.  "
            "Implemente o componente DocCard antes de adicionar o "
            "fallback de erro."
        )

    # A string literal alvo: "Erro desconhecido" (case-sensitive).
    # Aceita aspas simples, duplas ou crase; com ou sem espacos
    # ao redor (e improvavel ter escape no meio).
    pattern = r"""['"`]Erro\s+desconhecido['"`]"""
    if not re.search(pattern, body):
        pytest.fail(
            "AC#2 violada — RED.  O componente ``DocCard`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)} NAO possui o "
            "fallback ``\"Erro desconhecido\"`` para o caso em que "
            "``doc.error_message`` e null/undefined.\n\n"
            "Estado atual: o bloco de erro de DocCard (linhas "
            "171-175) usa ``&& doc.error_message`` que curto-circuita "
            "a renderizacao quando a string e vazia.  O usuario final "
            "ve um card sem nenhuma indicacao de que o upload "
            "falhou.\n\n"
            "GREEN deve ramificar a renderizacao em DocCard, por "
            "exemplo:\n"
            "  // Opcao 1: ternario\n"
            "  {doc.error_message\n"
            "    ? doc.error_message\n"
            "    : 'Erro desconhecido'}\n\n"
            "  // Opcao 2: operador ||\n"
            "  {(doc.error_message || 'Erro desconhecido')}\n\n"
            "  // Opcao 3: helper externo que retorna um dos dois\n"
            "  {formatErrorMessage(doc.error_message)}\n\n"
            "A string literal ``Erro desconhecido`` (case-sensitive) "
            "deve aparecer no corpo de ``function DocCard(…)``.  "
            "Adicionar a string em outro componente (ex.: DocRow) "
            "ou em comentario NAO satisfaz este AC."
        )


# ── AC#3 — DocRow renderiza error_message quando presente ──────────


def test_b5_ac3_docrow_renders_error_message_when_present():
    """AC#3: o componente ``DocRow`` em ``BibliotecaRoom.tsx``
    DEVE renderizar ``doc.error_message`` quando o campo tem
    valor (protecao de feature existente — GREEN).

    Verifica que o corpo de ``DocRow`` contem o padrao de
    curto-circuito ``doc.error_message && ( ... <JSX> ... )`` ou
    ternario ``doc.error_message ? ... : ...`` referenciando
    ``doc.error_message``.

    Estado atual (GREEN): DocRow (linhas 252-256) ja faz isso:
        {(doc.status === 'failed' || doc.status === 'partially_failed')
            && doc.error_message && (
          <span title={doc.error_message} ...>
            {doc.error_message}
          </span>
        )}
    """
    src = _biblioteca_source()
    body = _extract_function_body(src, "DocRow")

    if not body:
        pytest.fail(
            "AC#3 — pre-condicao violada: nao foi possivel extrair o "
            "corpo de ``function DocRow(…)`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)}.  O componente "
            "DocRow deve estar presente no arquivo para o behavior "
            "B-5 funcionar."
        )

    has_reference = bool(re.search(r"doc\.error_message", body))
    has_conditional_render = bool(
        re.search(
            r"doc\.error_message\s*[?:&]|\{\s*doc\.error_message\s*[,}]"
            r"|doc\.error_message\s*\?",
            body,
        )
    )

    if not (has_reference and has_conditional_render):
        pytest.fail(
            "AC#3 violada — feature atual quebrada.  O componente "
            "``DocRow`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)} NAO esta "
            "renderizando ``doc.error_message`` quando o campo esta "
            "preenchido.  O usuario nao ve a mensagem de erro tecnica "
            "fornecida pelo backend na view em lista.\n\n"
            "Esperado (padrao atual, GREEN):\n"
            "  {(doc.status === 'failed' || doc.status === 'partially_failed')\n"
            "      && doc.error_message && (\n"
            "    <span title={doc.error_message} ...>\n"
            "      {doc.error_message}\n"
            "    </span>\n"
            "  )}\n\n"
            "Reimplante essa logica de renderizacao condicional "
            "baseada em doc.error_message dentro do JSX de DocRow."
        )


# ── AC#4 — DocRow tem fallback "Erro desconhecido" (RED) ────────────


def test_b5_ac4_docrow_has_unknown_error_fallback():
    """AC#4: o componente ``DocRow`` em ``BibliotecaRoom.tsx``
    DEVE possuir o fallback textual ``"Erro desconhecido"`` que
    aparece quando ``doc.error_message`` e null/undefined.

    Verifica que a string literal ``Erro desconhecido`` aparece
    no corpo de ``DocRow``.  Mesma logica do AC#2 aplicada a
    view em lista.

    Estado atual (RED): DocRow (linhas 252-256) usa o mesmo
    padrao de curto-circuito que DocCard.  A string
    ``Erro desconhecido`` NAO aparece em lugar nenhum do
    componente.

    Depois (GREEN): a mesma ramificacao do AC#2 deve ser
    aplicada a DocRow.
    """
    src = _biblioteca_source()
    body = _extract_function_body(src, "DocRow")

    if not body:
        pytest.fail(
            "AC#4 — pre-condicao violada: nao foi possivel extrair o "
            "corpo de ``function DocRow(…)`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)}.  "
            "Implemente o componente DocRow antes de adicionar o "
            "fallback de erro."
        )

    pattern = r"""['"`]Erro\s+desconhecido['"`]"""
    if not re.search(pattern, body):
        pytest.fail(
            "AC#4 violada — RED.  O componente ``DocRow`` em "
            f"{BIBLIOTECA_PATH.relative_to(REPO_ROOT)} NAO possui o "
            "fallback ``\"Erro desconhecido\"`` para o caso em que "
            "``doc.error_message`` e null/undefined.\n\n"
            "Estado atual: o bloco de erro de DocRow (linhas "
            "252-256) usa ``&& doc.error_message`` que curto-circuita "
            "a renderizacao quando a string e vazia.  O usuario final "
            "ve uma linha sem nenhuma indicacao de que o upload "
            "falhou.\n\n"
            "GREEN deve ramificar a renderizacao em DocRow, por "
            "exemplo:\n"
            "  // Opcao 1: ternario\n"
            "  {doc.error_message\n"
            "    ? doc.error_message\n"
            "    : 'Erro desconhecido'}\n\n"
            "  // Opcao 2: operador ||\n"
            "  {(doc.error_message || 'Erro desconhecido')}\n\n"
            "  // Opcao 3: helper externo\n"
            "  {formatErrorMessage(doc.error_message)}\n\n"
            "A string literal ``Erro desconhecido`` (case-sensitive) "
            "deve aparecer no corpo de ``function DocRow(…)``.  "
            "Adicionar a string em outro componente (ex.: DocCard) "
            "ou em comentario NAO satisfaz este AC."
        )
