"""RED test for behavior BKL-028 / BKL-029 — Commercial (Clientes) indicators
populated end-to-end.

GOAL:
    BKL-028 / BKL-029 — Corrigir os indicadores Comerciais (Clientes) para
    que reflitam dados reais do ETL, e não arrays zerados / RPCs quebradas.

    O stack de "Comercial / Clientes" hoje está furado em três camadas:

        1. ``supabase/migrations/20260523999999_baseline_v2.sql`` define
           apenas o wrapper ``public.get_commercial_indicators`` (linha
           2241) e o wrapper ``public.get_commercial_top_clients``
           (linha 2271) — e o primeiro delega para
           ``analytics_v2.get_commercial_indicators(p_period)`` (linha
           2246) que NÃO está definida em nenhum lugar do baseline.

        2. NÃO existe uma função ``analytics_v2.popular_dim_clientes``
           (a tabela ``dim_clientes`` não é populada pelo ETL baseline
           — é populada de forma ad-hoc em outras migrations / scripts
           fora deste arquivo, e por isso, em produção, fica vazia).

        3. O frontend ``apps/blu_v3/src/api/analytics.ts`` (linhas
           456-477) tem ``getCommercialIndicators()`` chamando
           ``callDimensionRpc`` sem ``try`` / ``catch`` — quando o RPC
           retorna ``data: null`` (porque ``analytics_v2.get_commercial_indicators``
           não existe), o React Query vira ``isError: true`` e o usuário
           vê um card de erro / loading eterno.

        4. O frontend ``apps/blu_v3/src/api/clientes.ts`` (linhas 39-54)
           tem ``fetchCustomerSegments()`` que retorna ``[]`` em caso de
           erro e usa ``data ?? []`` em caso de sucesso — o que, quando
           ``dim_clientes`` está vazio, faz o "Box de Segmentos" no
           ``ClientesRoom`` ficar completamente em branco (sem nenhuma
           linha fallback de Alto / Médio / Baixo com zeros).

BEHAVIOR:
    BKL-028 / BKL-029 — Os indicadores comerciais (segmentos,
    top-clientes, receita) devem refletir dados reais do ETL. Quando
    as dim tables estão vazias, o sistema DEVE cair em fallback
    graceful (zeros + period, ou box de segmentos preenchido com
    Alto/Médio/Baixo zerados) — nunca um card em branco / erro
    inexplicável.

AC (Acceptance Criteria):
    AC1 — Função ``analytics_v2.popular_dim_clientes`` existe no
          baseline e popula ``analytics_v2.dim_clientes`` a partir das
          fontes (ex.: ``public.clientes`` ou ``fato_transacoes``).
    AC2 — ``analytics_v2.get_commercial_top_clients(p_period text,
          p_limit integer)`` existe no baseline — permitindo que o
          wrapper ``public.get_commercial_top_clients`` aceite
          ``period`` e ``limit`` como parâmetros e retorne receita
          real (não 0).
    AC3 — ``fetchCustomerSegments()`` em ``clientes.ts`` DEVE ter um
          fallback explícito para o caso de ``dim_clientes`` vazio —
          retornando pelo menos uma linha default para cada cluster
          (Alto / Médio / Baixo) com ``count: 0``.
    AC4 — ``analytics_v2.get_commercial_indicators(p_period text)``
          existe no baseline com a lógica que consulta as dim tables
          (``dim_clientes``, ``fato_transacoes``) e retorna dados
          reais.
    AC5 — ``getCommercialIndicators()`` em ``analytics.ts`` DEVE ter
          ``try`` / ``catch`` (ou ``Promise.allSettled``) que, em
          falha, retorna um objeto com zeros e ``period = period``
          (mesmo padrão de ``getSupplyIndicators`` de BKL-019).

Anti-Goals (must NOT be violated):
    1. NÃO remover os wrappers ``public.get_commercial_indicators`` e
       ``public.get_commercial_top_clients`` — eles podem ser
       refatorados para delegar para ``analytics_v2``, mas DEVE
       continuar existindo para o frontend não quebrar.
    2. NÃO alterar a interface pública de ``fetchCustomerSegments()``
       (assinatura: ``(clientId: string) => Promise<CustomerSegment[]>``).
    3. NÃO introduzir dependências novas — usar ``try`` / ``catch``
       nativo e pattern matching já presente no resto do codebase.
    4. NÃO alterar o shape de ``CustomerSegment`` /
       ``CommercialIndicators`` / ``TopClientRow``.

Estado atual: RED. Cada teste abaixo valida que a feature DESIRED
NÃO EXISTE hoje — portanto todos falham com ``AssertionError`` até
a GREEN phase. A leitura é puramente ``source-inspection`` (texto
de ``.sql`` e ``.ts``), sem Supabase real e sem mocks.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

BASELINE_SQL_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

ANALYTICS_API_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "analytics.ts"
)

CLIENTES_API_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "clientes.ts"
)

CLIENTES_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "ClientesRoom.tsx"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_baseline_sql() -> str:
    """Return the full text of the baseline migration SQL file.

    Raises an ``AssertionError`` if the file is missing — the test
    should fail loudly with a clear message rather than silently
    passing on a missing file.
    """
    assert BASELINE_SQL_PATH.exists(), (
        f"Source file not found: {BASELINE_SQL_PATH}"
    )
    return BASELINE_SQL_PATH.read_text(encoding="utf-8")


def _read_analytics_api_source() -> str:
    """Return the full text of ``apps/blu_v3/src/api/analytics.ts``."""
    assert ANALYTICS_API_PATH.exists(), (
        f"Source file not found: {ANALYTICS_API_PATH}"
    )
    return ANALYTICS_API_PATH.read_text(encoding="utf-8")


def _read_clientes_api_source() -> str:
    """Return the full text of ``apps/blu_v3/src/api/clientes.ts``."""
    assert CLIENTES_API_PATH.exists(), (
        f"Source file not found: {CLIENTES_API_PATH}"
    )
    return CLIENTES_API_PATH.read_text(encoding="utf-8")


def _read_clientes_room_source() -> str:
    """Return the full text of ``ClientesRoom.tsx``."""
    assert CLIENTES_ROOM_PATH.exists(), (
        f"Source file not found: {CLIENTES_ROOM_PATH}"
    )
    return CLIENTES_ROOM_PATH.read_text(encoding="utf-8")


def _extract_function_body(source: str, fn_name: str, start_marker: str = "export const") -> str:
    """Return the body of the named const/function using brace counting.

    Searches for ``start_marker + fn_name`` then brace-counts to find
    the body. Returns the body text (content between outer braces).
    Returns an empty string if not found.
    """
    pattern = (
        re.escape(start_marker)
        + r"\s+"
        + re.escape(fn_name)
        + r"\s*(?:<[^>]+>)?\s*=\s*async\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*=>\s*\{"
    )
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    j = body_start
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

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
        if in_string is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_string:
                in_string = None
                j += 1
                continue
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
        if ch in ('"', "'", "`"):
            in_string = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    if depth != 0:
        return ""
    return source[body_start : j - 1]


def _extract_function_body_async_decl(source: str, fn_name: str) -> str:
    """Extract the body of an ``async function`` / ``export async function`` decl.

    Mirrors ``_extract_function_body`` but targets declarations like
    ``export async function fetchCustomerSegments(...) { ... }``.
    """
    pattern = (
        r"export\s+async\s+function\s+"
        + re.escape(fn_name)
        + r"\s*(?:<[^>]+>)?\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{"
    )
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    j = body_start
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

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
        if in_string is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_string:
                in_string = None
                j += 1
                continue
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
        if ch in ('"', "'", "`"):
            in_string = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    if depth != 0:
        return ""
    return source[body_start : j - 1]


# ── AC1 ──────────────────────────────────────────────────────────────────


def test_ac1_dim_clientes_populado_pelo_etl():
    """AC1 — ``analytics_v2.popular_dim_clientes`` DEVE existir no baseline.

    A tabela ``analytics_v2.dim_clientes`` é a base de todos os
    indicadores comerciais (segmentos, top-clientes, recência,
    frequência, churn, etc.). Sem ela populada, todos os cards do
    ``ClientesRoom`` ficam zerados / vazios.

    Hoje o baseline
    ``supabase/migrations/20260523999999_baseline_v2.sql`` NÃO define
    nenhuma ``CREATE OR REPLACE FUNCTION analytics_v2.popular_dim_clientes``
    (zero matches), o que significa que a ``dim_clientes`` só é
    populada por migrations ad-hoc / scripts manuais fora do baseline
    — e em produção, em clientes novos, fica vazia. Por isso, AC2 /
    AC4 / AC5 ficam todos com dados zerados.

    GREEN phase deve adicionar ao baseline uma função
    ``analytics_v2.popular_dim_clientes(p_client_id uuid)`` que
    carrega ``dim_clientes`` a partir de ``public.clientes`` /
    ``fato_transacoes`` (campos ``nome``, ``customer_id``,
    ``nivel_cluster``, ``created_at`` etc.).

    Esta asserção procura por uma definição
    ``CREATE OR REPLACE FUNCTION analytics_v2.popular_dim_clientes``
    (com corpo não vazio) no baseline. Como a definição NÃO existe,
    o teste FALHA (RED).
    """
    sql = _read_baseline_sql()

    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.popular_dim_clientes"
        r"\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)

    assert match, (
        "AC1 violada — RED. A função `analytics_v2.popular_dim_clientes` "
        f"NÃO está definida em {BASELINE_SQL_PATH}. "
        "Behavior BKL-028/029 requer que o schema `analytics_v2` exponha "
        "uma função `popular_dim_clientes(p_client_id uuid)` que popula "
        "`analytics_v2.dim_clientes` a partir de `public.clientes` (ou de "
        "`fato_transacoes` agregado) — com colunas `customer_id`, `nome`, "
        "`nivel_cluster`, `created_at`, etc. "
        "Hoje a `dim_clientes` não tem nenhum ETL no baseline (zero "
        "`CREATE OR REPLACE FUNCTION analytics_v2.popular_dim_clientes` "
        "no arquivo), o que faz com que clientes novos fiquem sem "
        "nenhuma linha na `dim_clientes` e todos os cards de "
        "Comercial / Clientes no `ClientesRoom` apareçam zerados ou "
        "em branco."
    )


# ── AC2 ──────────────────────────────────────────────────────────────────


def test_ac2_commercial_top_clients_retorna_receita_real():
    """AC2 — ``analytics_v2.get_commercial_top_clients(p_period, p_limit)`` DEVE existir.

    O wrapper ``public.get_commercial_top_clients()`` (linha 2271 do
    baseline) hoje não aceita parâmetros e retorna
    ``COUNT(*)::NUMERIC AS total_volume`` e ``SUM(ft.valor)::NUMERIC AS
    total_revenue`` — mas o valor ``ft.valor`` da ``fato_transacoes``
    nem sempre reflete a receita real (pode ser valor bruto sem
    desconto, ou valor de item sem frete, dependendo do schema).

    O que AC2 exige é que exista uma função
    ``analytics_v2.get_commercial_top_clients(p_period text, p_limit integer)``
    no schema ``analytics_v2`` que o wrapper ``public`` possa
    referenciar — retornando top-N clientes por receita real
    (``SUM(ft.valor_total)`` ou campo equivalente) filtrado pelo
    período (``p_period``) e limitado por ``p_limit``.

    Hoje o baseline define APENAS
    ``CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()``
    (linha 2271, ZERO parâmetros) e ZERO definições de
    ``analytics_v2.get_commercial_top_clients``. O resultado é que
    o card "Top Clientes" no ``ClientesRoom`` mostra receita
    zerada ou que não respeita o filtro de período selecionado.

    Esta asserção procura por uma definição
    ``CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_top_clients``
    no baseline. Como ela NÃO existe, o teste FALHA (RED).
    """
    sql = _read_baseline_sql()

    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_commercial_top_clients"
        r"\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)

    assert match, (
        "AC2 violada — RED. A função `analytics_v2.get_commercial_top_clients` "
        f"NÃO está definida em {BASELINE_SQL_PATH}. "
        "Behavior BKL-028/029 requer que o schema `analytics_v2` exponha "
        "`get_commercial_top_clients(p_period text, p_limit integer)` "
        "RETURNS TABLE(client_id, cliente_nome, total_volume, "
        "total_revenue, last_purchase) com a lógica que consulta "
        "`analytics_v2.fato_transacoes` (com `ft.valor_total` ou campo "
        "de receita real) e `analytics_v2.dim_clientes` filtrado por "
        "`p_period` (ex.: '30d' → `data_transacao >= NOW() - INTERVAL "
        "'30 days'`) e `p_limit`. "
        "Hoje o baseline define apenas "
        "`public.get_commercial_top_clients()` (linha 2271, sem "
        "parâmetros) — não há nenhuma "
        "`analytics_v2.get_commercial_top_clients` (zero matches). "
        "Por isso, o card 'Top Clientes' no `ClientesRoom` retorna "
        "todos os clientes sem respeitar o filtro de período e pode "
        "mostrar receita zerada ou distorcida."
    )


# ── AC3 ──────────────────────────────────────────────────────────────────


def test_ac3_segmentos_box_populado():
    """AC3 — ``fetchCustomerSegments()`` DEVE ter fallback para ``dim_clientes`` vazia.

    Quando a ``dim_clientes`` está vazia (ETL não rodou, ou o
    cliente é novo), a RPC ``get_customer_segments`` retorna 0
    linhas. O frontend recebe ``data = []`` e o "Box de Segmentos"
    no ``ClientesRoom`` aparece completamente em branco — sem
    nenhuma linha para ``Alto``, ``Médio`` ou ``Baixo``.

    AC3 exige que ``fetchCustomerSegments()`` em
    ``apps/blu_v3/src/api/clientes.ts`` tenha um fallback explícito
    para esse caso: se ``data`` é vazio / null, retornar uma lista
    com as 3 entradas default
    (``{cluster: 'Alto', count: 0, avg_ticket: null, revenue_share: null}``,
    ``{cluster: 'Médio', count: 0, ...}``,
    ``{cluster: 'Baixo', count: 0, ...}``) — garantindo que o Box
    de Segmentos sempre mostre as 3 categorias (mesmo que zeradas).

    Hoje o corpo de ``fetchCustomerSegments`` (linhas 39-54) é:

        const { data, error } = await supabase.rpc('get_customer_segments', { ... })
        if (error) {
          console.warn(...)
          return []
        }
        return (data ?? []).map(...)

    Não há NENHUMA referência a ``'Alto'``, ``'Médio'`` ou
    ``'Baixo'`` no corpo da função (esses literais só aparecem na
    definição de tipo ``CustomerCluster`` na linha 3, FORA do
    corpo). Por isso, o teste FALHA (RED).
    """
    source = _read_clientes_api_source()

    has_fn = re.search(
        r"export\s+async\s+function\s+fetchCustomerSegments\b", source
    ) is not None
    assert has_fn, (
        f"Não foi possível encontrar a definição de `fetchCustomerSegments` "
        f"em {CLIENTES_API_PATH}. A função pode ter sido removida ou "
        f"renomeada — BKL-028/029 não pode ser validado sem ela."
    )

    body = _extract_function_body_async_decl(source, "fetchCustomerSegments")
    assert body, (
        f"Não foi possível extrair o corpo de `fetchCustomerSegments` em "
        f"{CLIENTES_API_PATH}. A função pode ter sido refatorada de uma "
        f"forma que o parser regex não consegue seguir — ex.: destructuring "
        f"complexo nos params ou nested arrow function."
    )

    has_alto = "'Alto'" in body or '"Alto"' in body
    has_medio = "'Médio'" in body or '"Médio"' in body
    has_baixo = "'Baixo'" in body or '"Baixo"' in body

    has_zero_default_count = re.search(
        r"count\s*:\s*0\b", body
    ) is not None

    has_fallback = has_alto and has_medio and has_baixo and has_zero_default_count

    assert has_fallback, (
        "AC3 violada — RED. A função `fetchCustomerSegments()` em "
        f"{CLIENTES_API_PATH} NÃO tem fallback explícito para o caso "
        "de `dim_clientes` vazia. "
        "Hoje o corpo (linhas 39-54) faz apenas `return (data ?? []).map(...)` "
        "e, em erro, `return []` — sem nenhum default para as 3 "
        "categorias (Alto / Médio / Baixo). "
        f"Encontrado no corpo: 'Alto'={has_alto}, 'Médio'={has_medio}, "
        f"'Baixo'={has_baixo}, `count: 0` default={has_zero_default_count}. "
        "A implementação GREEN deve adicionar um fallback que, quando "
        "`data` é vazio/null, retorna uma lista com 3 entradas zeradas — "
        "uma para cada cluster — para que o Box de Segmentos no "
        "`ClientesRoom` sempre mostre as 3 linhas (mesmo que com "
        "`count: 0`)."
    )


# ── AC4 ──────────────────────────────────────────────────────────────────


def test_ac4_commercial_indicators_retorna_dados_reais():
    """AC4 — ``analytics_v2.get_commercial_indicators(p_period)`` DEVE existir.

    O wrapper ``public.get_commercial_indicators`` (linha 2241 do
    baseline) tem corpo:

        SELECT * FROM analytics_v2.get_commercial_indicators(p_period);

    Esta função ``analytics_v2.get_commercial_indicators`` NÃO está
    definida em nenhum lugar do baseline (zero matches para
    ``CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_indicators``
    no arquivo). Por isso, quando o frontend chama o wrapper, ele
    tenta resolver ``analytics_v2.get_commercial_indicators`` e
    falha com "function does not exist" — fazendo o React Query
    virar ``isError: true`` e o card "Indicadores de Comercial" no
    ``ClientesRoom`` mostrar erro / loading infinito.

    GREEN phase deve adicionar ao baseline uma função
    ``analytics_v2.get_commercial_indicators(p_period text)``
    RETURNS TABLE(... 17 colunas ...) LANGUAGE sql com a lógica
    que consulta ``analytics_v2.fato_transacoes`` e
    ``analytics_v2.dim_clientes`` — com fallback de zeros + period
    via ``COALESCE`` quando as dim tables estão vazias.

    Esta asserção procura por uma definição
    ``CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_indicators``
    (com corpo não vazio) no baseline. Como a definição NÃO existe,
    o teste FALHA (RED).
    """
    sql = _read_baseline_sql()

    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_commercial_indicators"
        r"\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)

    assert match, (
        "AC4 violada — RED. A função `analytics_v2.get_commercial_indicators` "
        f"NÃO está definida em {BASELINE_SQL_PATH}. "
        "Behavior BKL-028/029 requer que o schema `analytics_v2` exponha "
        "`get_commercial_indicators(p_period text)` RETURNS TABLE com as "
        "17 colunas (pedidos_periodo, receita_periodo, ticket_medio, "
        "clientes_unicos, clientes_novos, clientes_recorrentes, "
        "recencia_media_dias, frequencia_media_mensal, churn_60d_perc, "
        "crescimento_receita_perc, win_rate_perc, ciclo_venda_dias, "
        "nrr_perc, clv, checkout_conversion_perc, nps, period) e que "
        "consulte `analytics_v2.fato_transacoes` e "
        "`analytics_v2.dim_clientes`. "
        "Hoje o baseline define apenas o wrapper `public.get_commercial_indicators` "
        "(linha 2241) que delega (linha 2246) para "
        "`analytics_v2.get_commercial_indicators(p_period)` — função que "
        "NÃO está definida no baseline. Por isso, em runtime, o RPC "
        "retorna null / falha, o React Query vira `isError: true` e "
        "o card 'Indicadores de Comercial' no `ClientesRoom` mostra "
        "erro / loading infinito."
    )


# ── AC5 ──────────────────────────────────────────────────────────────────


def test_ac5_fallback_dim_clientes_vazio():
    """AC5 — ``getCommercialIndicators()`` DEVE ter fallback de zeros+period em falha.

    Em ``apps/blu_v3/src/api/analytics.ts`` (linhas 456-477), a
    função ``getCommercialIndicators()`` chama
    ``callDimensionRpc('get_commercial_indicators', period)`` (linha
    457) que, em erro, faz ``throw new Error`` (helper ``callDimensionRpc``
    no topo do arquivo). Sem ``try`` / ``catch`` ao redor da chamada,
    o erro borbulha para o React Query, que vira ``isError: true`` e
    o card no ``ClientesRoom`` mostra erro / loading eterno — mesmo
    padrão buggy que BKL-019 corrigiu em ``getSupplyIndicators``.

    AC5 exige que ``getCommercialIndicators()`` envolva a chamada
    com ``try`` / ``catch`` (ou use ``Promise.allSettled``) que, em
    falha, retorna um objeto com todos os campos numéricos em 0 e
    ``period = period`` — mesmo padrão do AC4 de BKL-019.

    Hoje o corpo de ``getCommercialIndicators`` (linhas 456-477) é:

        const r = await callDimensionRpc<Record<string, unknown>>(
            'get_commercial_indicators', period
        )
        return { pedidos_periodo: num(r?.pedidos_periodo), ... }

    Não há ``try`` / ``catch`` nem ``allSettled``. Esta asserção
    valida que o corpo da função contém ``try`` / ``catch`` ou usa
    ``Promise.allSettled``. Como nenhum dos dois está presente, o
    teste FALHA (RED).
    """
    source = _read_analytics_api_source()

    has_get_commercial_indicators = re.search(
        r"export\s+const\s+getCommercialIndicators\b", source
    ) is not None
    assert has_get_commercial_indicators, (
        f"Não foi possível encontrar a definição de `getCommercialIndicators` "
        f"em {ANALYTICS_API_PATH}. A função pode ter sido removida ou "
        f"renomeada — BKL-028/029 não pode ser validado sem ela."
    )

    body = _extract_function_body(source, "getCommercialIndicators")
    assert body, (
        f"Não foi possível extrair o corpo de `getCommercialIndicators` em "
        f"{ANALYTICS_API_PATH}. A função pode ter sido refatorada de uma "
        f"forma que o parser regex não consegue seguir — ex.: arrow "
        f"function aninhada ou destructuring complexo nos params."
    )

    has_try = re.search(r"\btry\s*\{", body) is not None
    has_catch = re.search(r"\bcatch\s*[({]", body) is not None
    has_all_settled = re.search(r"\ballSettled\s*\(", body) is not None

    has_fallback = (has_try and has_catch) or has_all_settled

    assert has_fallback, (
        "AC5 violada — RED. A função `getCommercialIndicators()` em "
        f"{ANALYTICS_API_PATH} NÃO tem `try` / `catch` nem "
        "`Promise.allSettled` ao redor da chamada do RPC. "
        "Hoje ela chama `callDimensionRpc('get_commercial_indicators', period)` "
        "(linha 457) que, em caso de erro, faz `throw new Error` (helper "
        "`callDimensionRpc` no topo de `analytics.ts`). Sem `try` / "
        "`catch` na função, o erro borbulha para o React Query que fica "
        "em `isLoading: true` para sempre (especialmente quando o RPC "
        "retorna `data: null` sem jogar erro) ou vira `isError: true` "
        "sem fallback — o card 'Indicadores de Comercial' no "
        "`ClientesRoom` mostra spinner / erro eterno. "
        "A implementação GREEN deve envolver a chamada com `try` / "
        "`catch` que, em falha, retorna um objeto com todos os campos "
        "numéricos em 0 e `period = period` (mesmo padrão do AC4 de "
        "BKL-019 / `getSupplyIndicators`)."
    )
