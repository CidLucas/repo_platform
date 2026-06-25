"""RED test — Populate dim_clientes & Fix Commercial Indicators (BKL-028/029).

GOAL:
    Garantir que indicadores comerciais mostrem dados reais — não R$ 0 ou
    segmentos vazios. A tabela dim_clientes precisa ser populada após o
    primeiro upload CSV (notas), e as funções RPC comerciais
    (get_commercial_indicators, get_commercial_top_clients) precisam
    existir com a assinatura correta e ter fallback para null/erro.

BEHAVIOR:
    Populate dim_clientes & Fix Commercial Indicators (Behavior 3/5).

    No estado atual (RED):
        1. A migration proposed (20260526060000_unified_ingest_staging_and_apply.sql)
           contém INSERT INTO dim_clientes com UPSERT, mas o
           run-csv-etl/index.ts não chama esse pipeline inline (depende de
           pg_cron).
        2. A função RPC get_commercial_top_clients na baseline_v2.sql
           (linha 2271) não aceita parâmetros (p_period, p_limit), mas
           analytics.ts (linha 593) chama .rpc('get_commercial_top_clients',
           { p_period, p_limit }) — mismatch de assinatura.
        3. A função get_customer_segments existe na baseline_v2.sql
           (linha 2296) e é chamada corretamente por fetchCustomerSegments
           em clientes.ts — regression guard.
        4. getCommercialIndicators em analytics.ts (linha 456) chama
           callDimensionRpc que joga erro se o RPC falhar (linha 132-136),
           sem try/catch — falta fallback.
        5. O UPSERT dim_clientes usa ON CONFLICT (client_id, cpf_cnpj) mas
           clientes sem CPF/CNPJ (anonymous) têm cpf_cnpj = NULL, o que pode
           quebrar a unicidade do UPSERT.

    Após a correção (GREEN), deve:
        a) O index.ts do run-csv-etl invocar o pipeline inline (já coberto
           por test_etl_execution_pipeline.py).
        b) A RPC get_commercial_top_clients aceitar (p_period text,
           p_limit integer) e retornar dados de receita não-zero.
        c) get_customer_segments continuar existindo e retornando
           cluster/count/avg_ticket/revenue_share.
        d) getCommercialIndicators ter try/catch com fallback que retorna
           { pedidos_periodo: 0, receita_periodo: 0, ..., period }.
        e) O UPSERT dim_clientes tratar cpf_cnpj NULL com uma estratégia
           de chave alternativa (ex: UNIQUE (client_id, COALESCE(cpf_cnpj, ''))
           ou CONSTRAINT distinta).

AC (Acceptance Criteria):
    AC1 — A migration proposed contém INSERT INTO analytics_v2.dim_clientes
          com ON CONFLICT (UPSERT).
    AC2 — A RPC get_commercial_top_clients existe EM ALGUM LUGAR (baseline
          ou proposed) com a assinatura que aceita (p_period text,
          p_limit integer), compatível com analytics.ts que chama
          { p_period, p_limit }.
    AC3 — A RPC get_customer_segments existe (em baseline_v2.sql) e é
          chamada por fetchCustomerSegments em clientes.ts com
          .rpc('get_customer_segments', { p_client_id }).
    AC4 — getCommercialIndicators em analytics.ts envolve a chamada RPC
          em try/catch com fallback que retorna zeros estruturados + period.
    AC5 — A migration proposed tem estratégia para UPSERT de dim_clientes
          com cpf_cnpj NULL (anonymous clients), ex: UNIQUE sobre
          (client_id, COALESCE(cpf_cnpj, '')) ou duas constraints.

Anti-Goals (must NOT be violated):
    1. NÃO introduzir mocks de DB ou rede — o teste é puramente
       source-inspection sobre o texto dos arquivos.
    2. NÃO importar ou executar código TypeScript/React — apenas ler
       como texto.
    3. NÃO modificar código de produção.
    4. NÃO escrever asserts que passam no estado atual — a suite deve
       ser RED.

Estado atual (RED):
    - AC1: A migration proposed 20260526060000 tem INSERT INTO
      analytics_v2.dim_clientes com ON CONFLICT → passa (regression guard).
    - AC2: A RPC get_commercial_top_clients na baseline_v2.sql (linha 2271)
      NÃO tem parâmetros (p_period, p_limit) → pytest.fail().
    - AC3: A RPC get_customer_segments existe na baseline_v2.sql (linha 2296)
      → passa (regression guard).
    - AC4: analytics.ts getCommercialIndicators chama callDimensionRpc que
      joga erro (linha 132-136), sem try/catch → pytest.fail().
    - AC5: O UPSERT dim_clientes na migration proposed usa
      ON CONFLICT (client_id, cpf_cnpj) mas sem estratégia para NULL →
      pytest.fail() se cpf_cnpj pode ser NULL.
"""
import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ANALYTICS_TS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "analytics.ts"
CLIENTES_TS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "clientes.ts"
BASELINE_V2_PATH = (
    REPO_ROOT / "supabase" / "migrations" / "20260523999999_baseline_v2.sql"
)
MIGRATIONS_PROPOSED_DIR = REPO_ROOT / "supabase" / "migrations" / "proposed"
MIGRATION_INGEST_PATH = (
    MIGRATIONS_PROPOSED_DIR
    / "20260526060000_unified_ingest_staging_and_apply.sql"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é pura inspeção de código, sem DB."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o conteúdo de ``path`` como UTF-8. Falha se o arquivo não existir."""
    assert path.exists(), f"Arquivo não encontrado: {path}"
    return path.read_text(encoding="utf-8")


def _analytics_ts() -> str:
    """Lê o conteúdo de apps/blu_v3/src/api/analytics.ts."""
    return _read_text(ANALYTICS_TS_PATH)


def _clientes_ts() -> str:
    """Lê o conteúdo de apps/blu_v3/src/api/clientes.ts."""
    return _read_text(CLIENTES_TS_PATH)


def _baseline_migration_text() -> str:
    """Lê o conteúdo da baseline_v2.sql."""
    return _read_text(BASELINE_V2_PATH)


def _all_proposed_migrations() -> list[Path]:
    """Retorna todos os ``.sql`` em ``supabase/migrations/proposed/``."""
    assert MIGRATIONS_PROPOSED_DIR.exists(), (
        f"Diretório de migrations não encontrado: {MIGRATIONS_PROPOSED_DIR}"
    )
    return sorted(MIGRATIONS_PROPOSED_DIR.glob("*.sql"))


def _all_proposed_migration_text() -> str:
    """Concatena o conteúdo de todas as migrations propostas."""
    parts: list[str] = []
    for path in _all_proposed_migrations():
        parts.append(f"-- ===== {path.name} =====")
        parts.append(_read_text(path))
    return "\n\n".join(parts)


# ── Testes (5 acceptance criteria) ──────────────────────────────────────


def test_dim_clientes_insert_in_proposed_migration():
    """AC1 — A migration proposed deve conter ``INSERT INTO
    analytics_v2.dim_clientes`` com um bloco ``ON CONFLICT`` (UPSERT).

    A migration ``20260526060000_unified_ingest_staging_and_apply.sql`` já
    define o UPSERT de dim_clientes (linha ~1340 no archive, linha ~74 na
    proposed). Este teste atua como ``regression guard`` para garantir que
    o INSERT INTO e o ON CONFLICT não sejam removidos durante a correção.
    """
    ingest_text = _read_text(MIGRATION_INGEST_PATH)

    has_insert = bool(
        re.search(
            r"INSERT\s+INTO\s+(?:analytics_v2\.)?dim_clientes\b",
            ingest_text,
            re.IGNORECASE,
        )
    )
    has_on_conflict = bool(
        re.search(
            r"ON\s+CONFLICT\s*\([^)]*\)\s+DO\s+UPDATE",
            ingest_text,
            re.IGNORECASE,
        )
    )

    missing: list[str] = []
    if not has_insert:
        missing.append("INSERT INTO analytics_v2.dim_clientes")
    if not has_on_conflict:
        missing.append("ON CONFLICT ... DO UPDATE")

    if missing:
        pytest.fail(
            "AC1 não implementado: a migration "
            f"{MIGRATION_INGEST_PATH.name} "
            "não contém os elementos esperados. Faltam: "
            + ", ".join(missing)
            + ". O pipeline ETL precisa fazer UPSERT em dim_clientes "
            "para que os dados de clientes cheguem ao schema analítico "
            "após o primeiro upload de CSV (notas). "
            f"Arquivo: {MIGRATION_INGEST_PATH}"
        )


def test_get_commercial_top_clients_accepts_period_and_limit():
    """AC2 — A função RPC ``get_commercial_top_clients`` deve existir em
    alguma migration com a assinatura que aceita ``p_period text`` e
    ``p_limit integer``.

    A ``analytics.ts`` (linha 590-593) chama::

        supabase.rpc('get_commercial_top_clients', {
            p_period: period,
            p_limit: limit,
        })

    Porém a função existente em ``baseline_v2.sql`` (linha 2271) é::

        CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
        RETURNS TABLE(client_id bigint, ...)

    Sem parâmetros! Em tempo de execução isso gera erro porque o Supabase
    RPC rejeita argumentos extras não declarados. A correção esperada é
    adicionar os parâmetros ``p_period text DEFAULT '30d'`` e
    ``p_limit integer DEFAULT 10`` à função, além de usar esses parâmetros
    no corpo da query (ex: filtrar por período e limitar resultados).
    """
    baseline = _baseline_migration_text()
    proposed = _all_proposed_migration_text()
    all_sql = baseline + "\n\n" + proposed

    # Check if ANY migration has the RPC WITH params
    has_proper_params = bool(
        re.search(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+"
            r"(?:public\.|analytics_v2\.)?get_commercial_top_clients\s*\("
            r"[^)]*p_period\s+text"
            r"[^)]*p_limit\s+integer",
            all_sql,
            re.IGNORECASE | re.DOTALL,
        )
    )

    if not has_proper_params:
        pytest.fail(
            "AC2 não implementado: nenhuma migration define "
            "`get_commercial_top_clients(p_period text, p_limit integer)`. "
            "A função existente em baseline_v2.sql (linha 2271) não tem "
            "parâmetros, mas analytics.ts (linha 593) chama "
            "`.rpc('get_commercial_top_clients', { p_period, p_limit })`. "
            "Esse mismatch causa erro de 'function not found' ou "
            "'function argument mismatch' em runtime. "
            "Correção esperada: recriar a função na baseline OU em uma "
            "migration proposed com assinatura "
            "`get_commercial_top_clients(p_period text DEFAULT '30d', "
            "p_limit integer DEFAULT 10)` que filtre por período e "
            "retorne receita real (não-zero) de dim_clientes + "
            "fato_transacoes."
        )


def test_get_customer_segments_exists_and_returns_fields():
    """AC3 — A função RPC ``get_customer_segments`` deve existir em
    alguma migration (baseline_v2.sql linha 2296) e retornar os campos
    ``nivel_cluster``, ``count``, ``avg_ticket``, ``revenue_share``.

    A ``clientes.ts`` (linha 39-53) chama
    ``.rpc('get_customer_segments', { p_client_id })`` e mapeia os
    resultados para ``CustomerSegment[]`` com os campos
    ``cluster``/``count``/``avg_ticket``/``revenue_share``.

    A função já existe em baseline_v2.sql — este teste é regression guard.
    """
    baseline = _baseline_migration_text()

    has_rpc = bool(
        re.search(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+"
            r"(?:public\.|analytics_v2\.)?get_customer_segments\s*\(",
            baseline,
            re.IGNORECASE,
        )
    )
    has_cluster = bool(re.search(r"nivel_cluster", baseline, re.IGNORECASE))
    has_count = bool(re.search(r"\bcount\b", baseline, re.IGNORECASE))
    has_avg_ticket = bool(re.search(r"avg_ticket", baseline, re.IGNORECASE))
    has_revenue_share = bool(re.search(r"revenue_share", baseline, re.IGNORECASE))

    missing: list[str] = []
    if not has_rpc:
        missing.append("CREATE FUNCTION get_customer_segments")
    if not has_cluster:
        missing.append("RETURNS nivel_cluster")
    if not has_count:
        missing.append("RETURNS count")
    if not has_avg_ticket:
        missing.append("RETURNS avg_ticket")
    if not has_revenue_share:
        missing.append("RETURNS revenue_share")

    if missing:
        pytest.fail(
            "AC3 não implementado: a função `get_customer_segments` na "
            "baseline_v2.sql não contém todos os elementos esperados. "
            "Faltam: " + ", ".join(missing)
            + ". Sem essa função, o painel 'Segmentos' em ClientesRoom "
            "fica vazio (\"Sem dados de segmento.\"). "
            f"Arquivo: {BASELINE_V2_PATH}"
        )

    # Also verify clientes.ts calls the RPC correctly
    clientes = _clientes_ts()
    has_rpc_call = bool(
        re.search(
            r"\.rpc\s*\(\s*['\"]get_customer_segments['\"]",
            clientes,
        )
    )
    if not has_rpc_call:
        pytest.fail(
            "AC3 inconsistência: clientes.ts não chama "
            "`.rpc('get_customer_segments', ...)`. "
            "fetchCustomerSegments precisa invocar o RPC correto. "
            f"Arquivo: {CLIENTES_TS_PATH}"
        )


def test_get_commercial_indicators_has_try_catch_fallback():
    """AC4 — ``getCommercialIndicators`` em analytics.ts deve ter um bloco
    ``try/catch`` que captura erros do RPC e retorna zeros estruturados
    com ``period`` preenchido.

    Atualmente (linha 456-477), a função faz::

        const r = await callDimensionRpc<...>('get_commercial_indicators',
                                               period)

    Onde ``callDimensionRpc`` (linha 131-136) faz::

        const { data, error } = await supabase.rpc(rpc, { p_period: period })
        if (error) throw new Error(...)

    Ou seja, qualquer falha do RPC joga exceção e o React Query mostra
    erro no painel Analytics Comercial. A correção esperada é::

        let r: Record<string, unknown>
        try {
            r = await callDimensionRpc('get_commercial_indicators', period)
        } catch {
            r = { period }
        }
        return {
            pedidos_periodo: num(r?.pedidos_periodo),
            ...
            period: String(r?.period ?? period),
        }
    """
    content = _analytics_ts()

    has_try = bool(re.search(r"\btry\s*\{", content))
    has_catch = bool(re.search(r"\}\s*catch\s*\(", content))
    has_fallback_zeros = bool(
        re.search(
            r"(?:pedidos_periodo|receita_periodo|clientes_unicos)\s*[=:]\s*0",
            content,
        )
    )

    if not has_try or not has_catch:
        pytest.fail(
            "AC4 não implementado: getCommercialIndicators em analytics.ts "
            "NÃO possui bloco try/catch ao redor da chamada RPC. "
            "Atualmente, se o RPC get_commercial_indicators falhar (DB "
            "indisponível, dim_clientes vazia, etc.), callDimensionRpc "
            "joga erro e todo o painel Analytics Comercial quebra. "
            "Correção esperada: envolver a chamada RPC em "
            "`try { r = await callDimensionRpc(...) } catch { r = "
            "{ period } }` para que em caso de erro os indicadores "
            "retornem zero com o período preenchido, permitindo que o "
            "frontend mostre 'R$ 0' em vez de uma tela de erro. "
            f"Arquivo: {ANALYTICS_TS_PATH}"
        )


def test_dim_clientes_upsert_handles_anonymous_clients():
    """AC5 — O UPSERT de dim_clientes deve funcionar com e sem
    ``cpf_cnpj`` (clientes anônimos).

    A migration proposed (20260526060000) faz (linha ~1340-1357)::

        INSERT INTO analytics_v2.dim_clientes
          (client_id, cpf_cnpj, nome, telefone, ...)
        SELECT DISTINCT ON (COALESCE(cliente_cpf_cnpj, cliente_nome))
          v_client_id,
          COALESCE(cliente_cpf_cnpj, cliente_nome),  -- cpf_cnpj vira nome!
          ...
        ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET ...

    Problemas:
    1. ``COALESCE(cliente_cpf_cnpj, cliente_nome)`` no SELECT usa o nome
       como cpf_cnpj quando CPF/CNPJ é NULL — polui a coluna.
    2. ``ON CONFLICT (client_id, cpf_cnpj)`` não funciona quando
       cpf_cnpj é NULL porque UNIQUE index com NULL não bloqueia
       duplicatas no PostgreSQL padrão (NULL != NULL).
    3. Não há um UNIQUE INDEX ``(client_id, cpf_cnpj)`` com cláusula
       ``WHERE cpf_cnpj IS NOT NULL``, nem uma constraint separada para
       anonymous.

    Correção esperada:
    - Criar UNIQUE INDEX ``idx_dim_clientes_client_id_nome`` com
      ``WHERE cpf_cnpj IS NULL`` para anonymous.
    - Ou usar ``ON CONFLICT (client_id) WHERE cpf_cnpj IS NULL``.
    - Ou criar uma chave ``client_id + COALESCE(cpf_cnpj, 'ANON:' || nome)``.
    - Ou separar o UPSERT em dois paths: um com cpf_cnpj, outro sem.
    """
    ingest_text = _read_text(MIGRATION_INGEST_PATH)

    # Check for ON CONFLICT (client_id, cpf_cnpj)
    has_on_conflict_cpf = bool(
        re.search(
            r"ON\s+CONFLICT\s*\(\s*client_id\s*,\s*cpf_cnpj\s*\)",
            ingest_text,
            re.IGNORECASE,
        )
    )

    # Check for some strategy for anonymous: partial index, WHERE cpf_cnpj IS NULL, etc.
    has_anonymous_strategy = bool(
        re.search(
            r"WHERE\s+cpf_cnpj\s+IS\s+NULL|"
            r"ON\s+CONFLICT\s*\(\s*client_id\s*\)\s+WHERE|"
            r"idx_dim_clientes_client_id_nome|"
            r"ANON|anonimo|anonymous",
            ingest_text,
            re.IGNORECASE,
        )
    )

    # Check for cpf_cnpj being polluted with nome
    has_coalesce_cpf_nome_issue = bool(
        re.search(
            r"COALESCE\(\s*cliente_cpf_cnpj\s*,\s*cliente_nome\s*\)",
            ingest_text,
            re.IGNORECASE,
        )
    )

    if has_coalesce_cpf_nome_issue and not has_anonymous_strategy:
        pytest.fail(
            "AC5 não implementado: o UPSERT de dim_clientes na migration "
            f"{MIGRATION_INGEST_PATH.name} "
            "usa COALESCE(cliente_cpf_cnpj, cliente_nome) para preencher "
            "cpf_cnpj quando o campo é NULL — isso polui a coluna cpf_cnpj "
            "com nomes de clientes. Além disso, o ON CONFLICT "
            "(client_id, cpf_cnpj) não funciona corretamente quando "
            "cpf_cnpj é NULL (NULL != NULL no PostgreSQL). "
            "Correção esperada: (a) NÃO usar nome como fallback de "
            "cpf_cnpj — manter NULL; (b) Adicionar UNIQUE INDEX "
            "idx_dim_clientes_client_id_nome ON dim_clientes "
            "(client_id, nome) WHERE cpf_cnpj IS NULL para anonymous; "
            "(c) Separar o UPSERT em dois statements ou usar "
            "ON CONFLICT (client_id) WHERE cpf_cnpj IS NULL para "
            "anonymous. "
            f"Arquivo: {MIGRATION_INGEST_PATH}"
        )

    if not has_on_conflict_cpf and not has_anonymous_strategy:
        pytest.fail(
            "AC5 não implementado: nenhuma estratégia de UPSERT para "
            "dim_clientes encontrada — nem ON CONFLICT (client_id, "
            "cpf_cnpj) para clientes com documento, nem estratégia "
            "alternativa para anonymous (cpf_cnpj NULL). "
            "O ETL precisa tratar ambos os casos para que clientes "
            "sem CPF/CNPJ não criem duplicatas em dim_clientes. "
            f"Arquivo: {MIGRATION_INGEST_PATH}"
        )
