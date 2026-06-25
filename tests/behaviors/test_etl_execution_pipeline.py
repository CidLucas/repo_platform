"""RED test — Correção do pipeline de execução ETL CSV.

GOAL:
    AC#1 (pipeline-csv) — O Edge Function ``run-csv-etl`` deve executar o
    ETL **inline** (chamando ``sincronizar_csv_cliente`` ou
    ``apply_staging_to_facts`` via ``svc.rpc(...)``) em vez de depender
    exclusivamente de ``pg_cron`` para disparar o job. Quando o pipeline
    realmente roda, os dados fluem de ``csv_import_staging`` (staging) →
    ``dim_clientes`` / ``dim_fornecedores`` / ``dim_inventory`` /
    ``dim_datas`` → ``fato_transacoes`` e o ``reg_jobs`` correspondente
    é marcado como ``completed`` com ``progress_pct = 100``.

BEHAVIOR:
    Pipeline-CSV — Corrigir ``run-csv-etl`` para não depender de pg_cron.

    No estado atual (RED), ``supabase/functions/run-csv-etl/index.ts``:
        1. NÃO chama nenhum RPC inline após inserir o ``reg_jobs``.
        2. Retorna ``"CSV sync job queued. ETL will start within ~1
           minute."`` deixando todo o trabalho pesado para o ``pg_cron``.
        3. Em ambientes onde ``pg_cron`` está desabilitado, o job fica
           preso em ``status='pending'`` e ``fato_transacoes`` nunca é
           populada.

    Após a correção (GREEN), o handler deve:
        a) Invocar ``svc.rpc('sincronizar_csv_cliente', { p_job_id })``
           ou ``svc.rpc('apply_staging_to_facts', { p_job_id })``
           **inline**, após a inserção de ``reg_jobs`` (AC1).
        b) Confiar na presença de ``CREATE OR REPLACE FUNCTION ... 
           sincronizar_csv_cliente`` em alguma migration ``proposed``
           (AC2).
        c) Garantir que o pipeline faz ``INSERT INTO`` em todas as 4
           dimensões e em ``fato_transacoes`` (AC3).
        d) Garantir que o pipeline faz ``UPDATE reg_jobs SET
           status='completed', progress_pct=100`` ao final (AC4).
        e) Envolver a chamada RPC em ``try/catch`` com fallback que
           retorna ``{success: true, rows_inserted: 0, period: ...}``
           para que o frontend receba um 200 amigável mesmo quando o
           inline falhar (AC5).

AC (Acceptance Criteria):
    AC1 — ``run-csv-etl/index.ts`` contém um caminho de execução inline
          que chama ``sincronizar_csv_cliente`` ou
          ``apply_staging_to_facts`` diretamente (via ``svc.rpc(...)``).
    AC2 — Existe ``CREATE OR REPLACE FUNCTION sincronizar_csv_cliente``
          em alguma migration de ``supabase/migrations/proposed/``.
    AC3 — O pipeline (em alguma das migrations propostas) faz
          ``INSERT INTO dim_clientes``, ``INSERT INTO
          dim_fornecedores``, ``INSERT INTO dim_inventory``, ``INSERT
          INTO dim_datas`` e ``INSERT INTO fato_transacoes``.
    AC4 — O pipeline faz ``UPDATE reg_jobs SET status='completed',
          progress_pct=100`` ao final da execução bem-sucedida.
    AC5 — ``run-csv-etl/index.ts`` envolve a chamada RPC em ``try/catch``
          com fallback que retorna ``{success: true, rows_inserted: 0,
          period: ...}`` caso o inline falhe.

Anti-Goals (must NOT be violated):
    1. NÃO introduzir mocks de DB ou rede — o teste é puramente
       ``source-inspection`` sobre o texto dos arquivos.
    2. NÃO alterar a assinatura pública do ``run-csv-etl`` — apenas
       adicionar o caminho de execução inline antes do ``return``.
    3. NÃO remover o insert em ``reg_jobs`` (linha ~264 do index.ts) —
       o job continua sendo criado para fins de auditoria e como
       fallback de execução caso o inline falhe.
    4. NÃO substituir ``sincronizar_csv_cliente`` por uma função nova —
       a migration ``20260527010000_csv_etl_tipo_transacao_inference.sql``
       já define essa função; o index.ts deve apenas chamá-la.

Estado atual (RED):
    - AC1: ``index.ts`` não chama nenhum RPC inline → pytest.fail().
    - AC2: ``sincronizar_csv_cliente`` JÁ EXISTE em
      ``20260527010000_csv_etl_tipo_transacao_inference.sql`` (linha 11)
      → este teste passa no estado atual (regression guard).
    - AC3: ``INSERT INTO`` em todas as 4 dims e em ``fato_transacoes`` JÁ
      EXISTE nas duas migrations → este teste passa no estado atual.
    - AC4: ``UPDATE reg_jobs SET status='completed', progress_pct=100``
      JÁ EXISTE em ambas as migrations → este teste passa no estado
      atual.
    - AC5: ``index.ts`` NÃO tem ``try/catch`` ao redor de uma chamada
      RPC, nem o fallback ``{success:true, rows_inserted:0, period:...}``
      → pytest.fail().

A suíte como um todo é RED (AC1 e AC5 falham). Quando a fase GREEN
adicionar a chamada RPC inline + try/catch fallback em
``index.ts``, todas as 5 verificações passarão.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

RUN_CSV_ETL_PATH = (
    REPO_ROOT / "supabase" / "functions" / "run-csv-etl" / "index.ts"
)
MIGRATIONS_PROPOSED_DIR = REPO_ROOT / "supabase" / "migrations" / "proposed"
MIGRATION_INGEST_PATH = (
    MIGRATIONS_PROPOSED_DIR
    / "20260526060000_unified_ingest_staging_and_apply.sql"
)
MIGRATION_INFERENCE_PATH = (
    MIGRATIONS_PROPOSED_DIR
    / "20260527010000_csv_etl_tipo_transacao_inference.sql"
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


def _index_ts() -> str:
    """Lê o conteúdo de ``run-csv-etl/index.ts``."""
    return _read_text(RUN_CSV_ETL_PATH)


def _all_proposed_migrations() -> list[Path]:
    """Retorna todos os ``.sql`` em ``supabase/migrations/proposed/``."""
    assert MIGRATIONS_PROPOSED_DIR.exists(), (
        f"Diretório de migrations não encontrado: {MIGRATIONS_PROPOSED_DIR}"
    )
    return sorted(MIGRATIONS_PROPOSED_DIR.glob("*.sql"))


def _all_proposed_migration_text() -> str:
    """Concatena o conteúdo de todas as migrations propostas (separadas
    por uma linha em branco) para permitir busca transversal."""
    parts: list[str] = []
    for path in _all_proposed_migrations():
        parts.append(f"-- ===== {path.name} =====")
        parts.append(_read_text(path))
    return "\n\n".join(parts)


# ── Testes (5 acceptance criteria) ──────────────────────────────────────


def test_pg_cron_fallback_inline_execution():
    """AC1 — ``run-csv-etl/index.ts`` deve chamar ``sincronizar_csv_cliente``
    ou ``apply_staging_to_facts`` inline (via ``svc.rpc(...)``).

    No estado atual (RED), o handler cria o ``reg_jobs`` e retorna —
    sem nenhuma chamada RPC — deixando toda a execução do ETL para o
    ``pg_cron``. Em ambientes sem ``pg_cron`` habilitado isso significa
    que ``fato_transacoes`` nunca é populada.

    A correção deve adicionar, **após** o insert em ``reg_jobs`` (linha
    ~264) e **antes** do ``return json({ success: true, ... })``
    (linha ~287), uma chamada do tipo::

        const { data: rpcResult, error: rpcErr } = await svc.rpc(
            "sincronizar_csv_cliente",
            { p_job_id: job.job_id },
        );

    ou equivalentemente ``svc.rpc("apply_staging_to_facts", ...)``.
    """
    content = _index_ts()

    has_inline_rpc = bool(
        re.search(
            r"\.rpc\s*\(\s*['\"](?:sincronizar_csv_cliente|apply_staging_to_facts)['\"]",
            content,
        )
    )

    if not has_inline_rpc:
        pytest.fail(
            "AC1 não implementado: supabase/functions/run-csv-etl/index.ts "
            "NÃO contém uma chamada RPC inline para `sincronizar_csv_cliente` "
            "nem para `apply_staging_to_facts`. O handler apenas cria o "
            "reg_jobs (linha ~264) e retorna, dependendo 100% do pg_cron "
            "para popular fato_transacoes. Correção esperada: adicionar "
            "logo após o `svc.schema('analytics_v2').from('reg_jobs').insert(...)` "
            "uma chamada do tipo "
            "`await svc.rpc('sincronizar_csv_cliente', { p_job_id: job.job_id })` "
            "(ou `svc.rpc('apply_staging_to_facts', { p_job_id: job.job_id })`), "
            "seguida de try/catch com fallback (ver AC5). "
            f"Arquivo: {RUN_CSV_ETL_PATH}"
        )


def test_sincronizar_csv_cliente_exists():
    """AC2 — Deve existir ``CREATE OR REPLACE FUNCTION sincronizar_csv_cliente``
    em alguma migration de ``supabase/migrations/proposed/``.

    Esta função é o pipeline ETL canônico para CSV (espelha
    ``apply_staging_to_facts`` mas opera sobre ``csv_import_staging``).
    Sem ela, a chamada RPC inline do AC1 não teria um corpo para
    executar.

    A migration ``20260527010000_csv_etl_tipo_transacao_inference.sql``
    já define essa função (linha 11) — este teste atua como
    ``regression guard`` para garantir que ela não seja removida.
    """
    all_migrations = _all_proposed_migration_text()

    has_function = bool(
        re.search(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:public\.|analytics_v2\.)?sincronizar_csv_cliente\s*\(",
            all_migrations,
            re.IGNORECASE,
        )
    )

    if not has_function:
        pytest.fail(
            "AC2 não implementado: nenhuma migration em "
            "supabase/migrations/proposed/ define `CREATE OR REPLACE "
            "FUNCTION sincronizar_csv_cliente(...)`. Esta função é o "
            "pipeline ETL canônico para CSV (lê de csv_import_staging, "
            "faz UPSERT em dim_* e insere em fato_transacoes). "
            "Correção esperada: criar a função em uma nova migration "
            "proposed, por exemplo "
            "`20260527XXXXXX_create_sincronizar_csv_cliente.sql`, com "
            "assinatura `sincronizar_csv_cliente(p_job_id uuid) "
            "RETURNS jsonb` e a lógica de UPSERT espelhada de "
            "`analytics_v2.apply_staging_to_facts`. "
            f"Diretório: {MIGRATIONS_PROPOSED_DIR}"
        )


def test_data_flows_staging_to_dim_facts():
    """AC3 — O pipeline ETL deve fazer ``INSERT INTO`` em todas as 4
    dimensões (``dim_clientes``, ``dim_fornecedores``, ``dim_inventory``,
    ``dim_datas``) e em ``fato_transacoes``.

    A correção do pipeline só faz sentido se os dados realmente
    fluírem: staging → dimensões → fato. Cada um dos 5 ``INSERT INTO``
    deve aparecer em alguma das migrations ``proposed`` (em particular
    em ``20260526060000_unified_ingest_staging_and_apply.sql`` e/ou
    ``20260527010000_csv_etl_tipo_transacao_inference.sql``).

    As referências devem ser qualificadas pelo schema
    (``analytics_v2.dim_clientes`` etc.) para evitar ambiguidade.
    """
    all_migrations = _all_proposed_migration_text()

    required_inserts: dict[str, str] = {
        "dim_clientes": r"INSERT\s+INTO\s+(?:analytics_v2\.)?dim_clientes\b",
        "dim_fornecedores": r"INSERT\s+INTO\s+(?:analytics_v2\.)?dim_fornecedores\b",
        "dim_inventory": r"INSERT\s+INTO\s+(?:analytics_v2\.)?dim_inventory\b",
        "dim_datas": r"INSERT\s+INTO\s+(?:analytics_v2\.)?dim_datas\b",
        "fato_transacoes": r"INSERT\s+INTO\s+(?:analytics_v2\.)?fato_transacoes\b",
    }

    missing: list[str] = []
    for label, pattern in required_inserts.items():
        if not re.search(pattern, all_migrations, re.IGNORECASE):
            missing.append(label)

    if missing:
        pytest.fail(
            "AC3 não implementado: o pipeline ETL nas migrations "
            "propostas NÃO faz `INSERT INTO` em todas as tabelas "
            "esperadas. Faltam: "
            + ", ".join(missing)
            + ". O pipeline deve popular as 4 dimensões "
            "(dim_clientes, dim_fornecedores, dim_inventory, dim_datas) "
            "e a tabela fato (fato_transacoes) para que o dado de "
            "csv_import_staging chegue ao schema analítico. "
            f"Diretório: {MIGRATIONS_PROPOSED_DIR}"
        )


def test_reg_jobs_completes_successfully():
    """AC4 — O pipeline ETL deve fazer ``UPDATE reg_jobs SET
    status='completed', progress_pct=100`` ao final da execução
    bem-sucedida.

    Esta é a única forma de o frontend distinguir um job que
    realmente terminou de um job preso em ``pending`` (estado
    causado pela ausência de ``pg_cron``).

    A query pode ser qualificada (``analytics_v2.reg_jobs``) ou não,
    contanto que atualize ``status`` para ``completed`` e
    ``progress_pct`` para ``100``.
    """
    all_migrations = _all_proposed_migration_text()

    has_completed_update = bool(
        re.search(
            r"UPDATE\s+(?:analytics_v2\.)?reg_jobs\b"
            r"(?:(?!;).)*?"
            r"status\s*=\s*['\"]completed['\"]"
            r"(?:(?!;).)*?"
            r"progress_pct\s*=\s*100",
            all_migrations,
            re.IGNORECASE | re.DOTALL,
        )
    )

    if not has_completed_update:
        pytest.fail(
            "AC4 não implementado: nenhuma migration em "
            "supabase/migrations/proposed/ contém um `UPDATE reg_jobs "
            "SET status='completed', progress_pct=100` ao final do "
            "pipeline ETL. Sem essa atualização, o frontend não tem "
            "como distinguir um job que realmente terminou de um job "
            "preso em pending (cenário atual quando pg_cron está "
            "desabilitado). Correção esperada: garantir que o bloco de "
            "sucesso (EXCEPTION WHEN OTHERS ... END) faça o UPDATE com "
            "`status = 'completed'`, `progress_pct = 100` e "
            "`completed_at = now()`. "
            f"Diretório: {MIGRATIONS_PROPOSED_DIR}"
        )


def test_rpc_fallback_returns_zeros_with_period():
    """AC5 — ``run-csv-etl/index.ts`` deve envolver a chamada RPC
    inline em ``try/catch`` com fallback que retorna
    ``{success: true, rows_inserted: 0, period: ...}``.

    A correção do AC1 adiciona uma chamada RPC que pode falhar
    (RPC indisponível, timeout, permissão). Para o frontend não
    quebrar com um 500 e para o usuário não pensar que o upload
    falhou (afinal, o ``reg_jobs`` foi criado e ``pg_cron`` ainda
    pode pegar como fallback), o handler deve capturar a exceção e
    retornar 200 com::

        { success: true, rows_inserted: 0, period: "<YYYY-MM>" }

    A presença de uma chave ``period`` (qualquer string não-vazia)
    na resposta de fallback é obrigatória.
    """
    content = _index_ts()

    has_rpc_call = bool(
        re.search(
            r"\.rpc\s*\(\s*['\"](?:sincronizar_csv_cliente|apply_staging_to_facts)['\"]",
            content,
        )
    )

    has_try_block = bool(re.search(r"\btry\s*\{", content))
    has_catch_block = bool(
        re.search(r"\}\s*catch\s*\(", content)
    )

    has_fallback_shape = bool(
        re.search(
            r"\{\s*[^{}]*?success\s*:\s*true"
            r"[^{}]*?rows_inserted\s*:\s*0"
            r"[^{}]*?period\s*:",
            content,
            re.DOTALL,
        )
    )

    if not has_rpc_call:
        pytest.fail(
            "AC5 não implementado: supabase/functions/run-csv-etl/index.ts "
            "NÃO faz nenhuma chamada RPC inline (pré-requisito do AC1). "
            "Sem a chamada RPC, o try/catch com fallback é impossível. "
            "Implemente primeiro o AC1 e depois envolva a chamada em "
            "`try { ... } catch (err) { ... return json({ success: true, "
            "rows_inserted: 0, period: '<YYYY-MM>' }, 200); }`. "
            f"Arquivo: {RUN_CSV_ETL_PATH}"
        )
    elif not (has_try_block and has_catch_block):
        pytest.fail(
            "AC5 não implementado: run-csv-etl/index.ts faz a chamada "
            "RPC inline (AC1 OK) mas NÃO a envolve em `try/catch`. "
            "Qualquer falha do RPC retornaria 500 para o frontend, "
            "quebrando a UX do upload. Correção esperada: envolver a "
            "chamada RPC em `try { ... } catch (err) { ... return "
            "json({ success: true, rows_inserted: 0, period: '<YYYY-MM>' "
            "}, 200); }` para que o frontend receba um 200 amigável "
            "caso o inline falhe (o job continua na fila do pg_cron "
            "como backup). "
            f"Arquivo: {RUN_CSV_ETL_PATH}"
        )
    elif not has_fallback_shape:
        pytest.fail(
            "AC5 não implementado: run-csv-etl/index.ts tem a chamada "
            "RPC inline e o try/catch, mas o bloco `catch` NÃO retorna "
            "a forma de fallback esperada `{ success: true, "
            "rows_inserted: 0, period: ... }`. O frontend precisa "
            "dessas 3 chaves para diferenciar 'inline rodou com zero "
            "linhas' de 'inline falhou'. Correção esperada: o `return` "
            "dentro do `catch` deve ser "
            "`return json({ success: true, rows_inserted: 0, period: "
            "'<YYYY-MM>' }, 200)` (ou shape equivalente com as 3 chaves: "
            "`success` true, `rows_inserted` 0 e `period` preenchido). "
            f"Arquivo: {RUN_CSV_ETL_PATH}"
        )
