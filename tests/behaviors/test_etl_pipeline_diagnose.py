"""RED test for Behavior 1/5 — Diagnose ETL Pipeline Infrastructure.

GOAL:
    Verificar end-to-end o pipeline de ETL no baseline atual do Supabase:
    ``pg_cron`` para disparar jobs CSV, função ``sincronizar_csv_cliente``
    com a nova lógica de inferência, tabelas ``dim_clientes`` /
    ``fato_transacoes`` no schema ``analytics_v2``, tabela ``reg_jobs``
    com o ``CHECK (job_type)`` aceitando ``csv_sync``, e o schema
    ``analytics_v2`` exposto na API.

BEHAVIOR:
    1/5 — Diagnose ETL Pipeline Infrastructure.

    O pipeline de ETL do Blu depende de cinco peças encadeadas:

      1. Um job ``pg_cron`` que dispara o processamento de jobs CSV em
         background.
      2. A função ``public.sincronizar_csv_cliente`` com a inferência de
         ``tipo_transacao`` + ``entry_type`` (proposta na migration
         ``20260527010000_csv_etl_tipo_transacao_inference.sql``).
      3. As tabelas ``analytics_v2.dim_clientes`` e
         ``analytics_v2.fato_transacoes`` declaradas como ``CREATE TABLE``
         no schema ``analytics_v2``.
      4. A tabela ``analytics_v2.reg_jobs`` com ``CHECK (job_type)``
         permitindo o valor ``csv_sync``.
      5. O schema ``analytics_v2`` exposto em ``[api] schemas`` do
         ``supabase/config.toml``.

AC (Acceptance Criteria):
    AC#1 — Existe um job ``pg_cron`` registrado no baseline
           (``20260523999999_baseline_v2.sql``) com nome contendo
           ``csv_sync`` que executa periodicamente.
    AC#2 — A função ``public.sincronizar_csv_cliente`` declarada no
           baseline contém a inferência de ``tipo_transacao`` e
           ``entry_type`` (lógica de cascade: keyword match, CNPJ hit,
           dim_clientes hit, dim_fornecedores hit, fallback contextual,
           default 'despesa').
    AC#3 — O baseline contém ``CREATE TABLE`` para
           ``analytics_v2.dim_clientes`` E
           ``analytics_v2.fato_transacoes`` (schema ``analytics_v2``
           materializado, não apenas referenciado em views).
    AC#4 — A tabela ``analytics_v2.reg_jobs`` no baseline possui
           ``CHECK (job_type)`` que aceita o valor ``csv_sync``.
    AC#5 — O schema ``analytics_v2`` está listado em
           ``[api] schemas`` no ``supabase/config.toml``.

Anti-Goals (must NOT be violated):
    1. NÃO consultar o DB real — apenas inspeção de arquivos
       ``.sql``/``.toml``.
    2. NÃO introduzir mocks — as fixtures de RED tests são puras.
    3. NÃO usar arquivos em ``supabase/migrations_archive/`` como
       fonte de verdade — eles foram arquivados; o baseline atual é
       ``20260523999999_baseline_v2.sql``.
    4. NÃO contar arquivos em ``supabase/migrations/proposed/`` como
       já aplicados — eles são rascunhos pendentes de merge.

Estado atual: RED. Cada AC abaixo está violado no baseline atual:

  AC#1 — ``20260523999999_baseline_v2.sql`` NÃO contém nenhum
         ``cron.schedule(...)`` (zero ``pg_cron`` no baseline).
  AC#2 — A função ``sincronizar_csv_cliente`` está no baseline, mas SEM
         a inferência de ``tipo_transacao``/``entry_type`` — esse lógica
         só existe em ``proposed/20260527010000_csv_etl_tipo_transacao_inference.sql``.
  AC#3 — O baseline referencia ``analytics_v2.dim_clientes`` e
         ``analytics_v2.fato_transacoes`` em views, mas NÃO contém
         ``CREATE TABLE`` para essas tabelas (estão em
         ``migrations_archive/20260428143000_phase2_analytics_v2_tables.sql``).
  AC#4 — O ``CHECK (job_type)`` em ``analytics_v2.reg_jobs`` aceita
         ``('bigquery_sync','connector_sync','analytics_etl','custom')``,
         SEM ``csv_sync``. A migration proposta
         ``proposed/20260526075000_g5_refresh_dashboards_job.sql``
         amplia o CHECK, mas não está aplicada.
  AC#5 — PASS (documenta-se mesmo assim como AC). ``config.toml`` já
         expõe ``analytics_v2`` em ``[api] schemas``.

Os 5 testes abaixo devem FALHAR (RED) com mensagens detalhadas em
pt-BR explicando o que está faltando no baseline para cada AC. Quando
a fase GREEN aplicar as migrations propostas, todos os 5 devem virar
PASS simultaneamente.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

BASELINE_V2_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

ARCHIVE_PHASE2_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations_archive"
    / "20260428143000_phase2_analytics_v2_tables.sql"
)

PROPOSED_CSV_INFERENCE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "proposed"
    / "20260527010000_csv_etl_tipo_transacao_inference.sql"
)

PROPOSED_REG_JOBS_CHECK_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "proposed"
    / "20260526075000_g5_refresh_dashboards_job.sql"
)

CONFIG_TOML_PATH = REPO_ROOT / "supabase" / "config.toml"


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é pura inspeção de fonte,
    sem teardown de DB. O conftest em ``tests/behaviors/conftest.py``
    já faz isso, mas mantemos a fixture local para autodocumentação
    e isolamento de qualquer mudança futura no conftest.
    """
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_baseline() -> str:
    """Retorna o conteúdo do baseline v2 atual.

    Esta é a ÚNICA fonte de verdade para os ACs 1-4: o que está em
    ``migrations_archive/`` ou ``migrations/proposed/`` não conta como
    aplicado.
    """
    assert BASELINE_V2_PATH.exists(), (
        f"Baseline v2 não encontrado em {BASELINE_V2_PATH}. "
        f"Verifique se o arquivo de migração inicial foi renomeado."
    )
    return BASELINE_V2_PATH.read_text(encoding="utf-8")


def _read_config_toml() -> str:
    """Retorna o conteúdo do ``supabase/config.toml``."""
    assert CONFIG_TOML_PATH.exists(), (
        f"config.toml não encontrado em {CONFIG_TOML_PATH}."
    )
    return CONFIG_TOML_PATH.read_text(encoding="utf-8")


# ── AC#1: pg_cron job para csv_sync no baseline ──────────────────────────


def test_etl_ac1_baseline_has_pg_cron_job_for_csv_sync():
    """AC#1 — O baseline DEVE registrar um job ``pg_cron`` cujo nome
    contenha ``csv_sync`` e que chame ``analytics_v2`` / função de
    processamento de jobs CSV periodicamente.

    Atualmente (RED) o baseline ``20260523999999_baseline_v2.sql`` NÃO
    contém nenhum ``cron.schedule(...)`` — zero agendamentos
    ``pg_cron``. O único ``cron.schedule`` existente está em
    ``proposed/20260526070000_etl_dispatcher_via_pg_net.sql`` (job
    ``process-pending-bigquery-jobs``, não ``csv_sync``).

    Esta asserção testa que JÁ existe um bloco ``cron.schedule`` com
    nome contendo ``csv_sync`` no baseline — como não há, o teste
    FALHA (RED).
    """
    baseline = _read_baseline()

    # Procura por qualquer chamada cron.schedule(...) no baseline.
    cron_schedule_matches = re.findall(
        r"cron\.schedule\s*\(",
        baseline,
        re.IGNORECASE,
    )
    assert cron_schedule_matches, (
        "AC#1 violada — RED. O baseline `20260523999999_baseline_v2.sql` "
        "NÃO contém nenhuma chamada a `cron.schedule(...)`. "
        "A implementação GREEN deve adicionar (na fase de migrations) "
        "um job `pg_cron` que dispare o processamento de jobs CSV em "
        "background, ex.: `cron.schedule('process-csv-sync-jobs', "
        "'*/5 * * * *', $$ SELECT public.process_csv_sync_jobs(); $$)`. "
        "Sem esse job, o pipeline de ETL não roda sozinho."
    )

    # Procura pelo nome do job csv_sync. Aceita variações de aspas
    # (simples/duplas/$$) e o prefixo job_name => opcional.
    csv_sync_job_pattern = re.compile(
        r"cron\.schedule\s*\("
        r"\s*(?:job_name\s*=>\s*)?"
        r"['\"\$]{1,2}\s*[A-Za-z0-9_-]*csv[_-]?sync[A-Za-z0-9_-]*\s*['\"\$]{1,2}",
        re.IGNORECASE,
    )
    csv_sync_match = csv_sync_job_pattern.search(baseline)
    assert csv_sync_match, (
        f"AC#1 violada — RED. O baseline contém {len(cron_schedule_matches)} "
        f"chamada(s) a `cron.schedule(...)`, mas NENHUMA com nome "
        f"contendo `csv_sync`. A implementação GREEN deve registrar um "
        f"job `pg_cron` cujo nome identifique que ele processa jobs "
        f"`csv_sync` (ex.: `process-csv-sync-jobs` ou `csv_sync_dispatcher`). "
        f"Sem isso, o scheduler `pg_cron` não está conectado ao pipeline "
        f"de ETL de CSV."
    )


# ── AC#2: sincronizar_csv_cliente com inferência tipo_transacao/entry_type ─


def test_etl_ac2_sincronizar_csv_cliente_has_tipo_transacao_inference():
    """AC#2 — A função ``public.sincronizar_csv_cliente`` no baseline
    DEVE implementar a inferência de ``tipo_transacao`` e
    ``entry_type`` (cascade de 7 níveis documentada no header da
    migration proposta).

    Atualmente (RED) a função existe no baseline (linha ~4284) mas
    é a versão "v0" — SEM a inferência. A versão nova só existe em
    ``proposed/20260527010000_csv_etl_tipo_transacao_inference.sql``,
    arquivo que ainda não foi aplicado.

    Esta asserção testa que o corpo da função no baseline JÁ contém
    sinais textuais da inferência (``v_tipo_transacao``, ``entry_type``
    ou mapeamento por keyword) — como a versão atual não os contém,
    o teste FALHA (RED).
    """
    baseline = _read_baseline()

    # Localiza a CREATE OR REPLACE FUNCTION public.sincronizar_csv_cliente
    func_match = re.search(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.sincronizar_csv_cliente"
        r"\s*\([^)]*\)\s*RETURNS[\s\S]+?LANGUAGE\s+\w+[\s\S]+?AS\s+\$function\$"
        r"([\s\S]+?)\$function\$\s*;",
        baseline,
        re.IGNORECASE,
    )
    assert func_match is not None, (
        "AC#2 violada: não foi possível localizar a função "
        "`public.sincronizar_csv_cliente(...)` no baseline "
        f"{BASELINE_V2_PATH}."
    )

    func_body = func_match.group(1)

    # Sinais textuais que a inferência de tipo_transacao/entry_type
    # foi implementada:
    #   1. declaração de variável v_tipo_transacao ou v_entry_type
    #   2. bloco de cascade (CASE WHEN) que classifica venda/compra/despesa
    #   3. fallback explícito para 'despesa'
    has_tipo_transacao_var = bool(
        re.search(r"\bv_tipo_transacao\b", func_body, re.IGNORECASE)
    )
    has_entry_type_var = bool(
        re.search(r"\bentry_type\b", func_body, re.IGNORECASE)
    )
    has_cascade_or_keyword_match = bool(
        re.search(
            r"keyword|LOWER\s*\(\s*v_tipo_lancamento|"
            r"CASE\s+WHEN[\s\S]{0,200}'compra'[\s\S]{0,200}'venda'",
            func_body,
            re.IGNORECASE,
        )
    )
    has_despesa_fallback = bool(
        re.search(r"'despesa'", func_body, re.IGNORECASE)
    )

    missing_signals = []
    if not has_tipo_transacao_var:
        missing_signals.append("declaração `v_tipo_transacao`")
    if not has_entry_type_var:
        missing_signals.append("uso de `entry_type`")
    if not has_cascade_or_keyword_match:
        missing_signals.append(
            "bloco de cascade (keyword match / CASE WHEN classificando "
            "venda/compra)"
        )
    if not has_despesa_fallback:
        missing_signals.append("fallback explícito para 'despesa'")

    assert not missing_signals, (
        "AC#2 violada — RED. A função `public.sincronizar_csv_cliente` "
        f"existe no baseline ({BASELINE_V2_PATH}) mas é a versão SEM "
        f"inferência de `tipo_transacao`/`entry_type`. "
        f"Sinais textuais ausentes no corpo da função: "
        f"{', '.join(missing_signals)}. "
        f"A implementação GREEN deve substituir a versão atual pela "
        f"lógica de cascade documentada em "
        f"`proposed/20260527010000_csv_etl_tipo_transacao_inference.sql` "
        f"(7 níveis: keyword match → CNPJ hit → dim_clientes hit → "
        f"dim_fornecedores hit → contexto → 'despesa')."
    )


# ── AC#3: dim_clientes e fato_transacoes materializadas no baseline ──────


def test_etl_ac3_baseline_has_create_table_for_dim_clientes_and_fato_transacoes():
    """AC#3 — O baseline DEVE conter ``CREATE TABLE`` para
    ``analytics_v2.dim_clientes`` E ``analytics_v2.fato_transacoes``.

    Atualmente (RED) o baseline referencia essas tabelas em views e
    funções (ex.: linha 2147, 2284, 2732), mas NÃO contém
    ``CREATE TABLE analytics_v2.dim_clientes`` nem
    ``CREATE TABLE analytics_v2.fato_transacoes``. O ``CREATE TABLE``
    está apenas em
    ``supabase/migrations_archive/20260428143000_phase2_analytics_v2_tables.sql``
    — arquivo arquivado, portanto não conta como aplicado.

    Esta asserção testa que o baseline JÁ contém ambos os
    ``CREATE TABLE`` no schema ``analytics_v2`` — como não contém,
    o teste FALHA (RED).
    """
    baseline = _read_baseline()

    # Sanity: a migration archive existe (para contexto da mensagem de erro).
    archive_note = ""
    if ARCHIVE_PHASE2_PATH.exists():
        archive_note = (
            f" (a definição original está em `{ARCHIVE_PHASE2_PATH.relative_to(REPO_ROOT)}`, "
            f"arquivo arquivado que não conta como aplicado)."
        )

    has_dim_clientes = bool(
        re.search(
            r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?"
            r"analytics_v2\.dim_clientes\b",
            baseline,
            re.IGNORECASE,
        )
    )
    has_fato_transacoes = bool(
        re.search(
            r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?"
            r"analytics_v2\.fato_transacoes\b",
            baseline,
            re.IGNORECASE,
        )
    )

    missing = []
    if not has_dim_clientes:
        missing.append("dim_clientes")
    if not has_fato_transacoes:
        missing.append("fato_transacoes")

    missing_qualified = [f"analytics_v2.{name}" for name in missing]

    assert not missing, (
        "AC#3 violada — RED. O baseline `20260523999999_baseline_v2.sql` "
        "NÃO contém `CREATE TABLE` para a(s) tabela(s) "
        f"{', '.join(missing_qualified)}"
        f"{archive_note} "
        "A implementação GREEN deve trazer essas definições de volta "
        "para o baseline (mover de `migrations_archive/` para "
        "`migrations/20260523999999_baseline_v2.sql`, ou criar uma "
        "migration adicional que faça o `CREATE TABLE IF NOT EXISTS`). "
        "Sem isso, o schema `analytics_v2` está apenas referenciado "
        "em views mas não materializado, e qualquer deploy limpo "
        "vai quebrar com `relation does not exist`."
    )


# ── AC#4: reg_jobs CHECK (job_type) aceita csv_sync ─────────────────────


def test_etl_ac4_baseline_reg_jobs_check_constraint_allows_csv_sync():
    """AC#4 — A tabela ``analytics_v2.reg_jobs`` no baseline DEVE ter
    ``CHECK (job_type)`` que aceita o valor ``csv_sync``.

    Atualmente (RED) o ``CHECK (job_type)`` em ``reg_jobs`` aceita
    apenas ``('bigquery_sync','connector_sync','analytics_etl','custom')``,
    definido em
    ``supabase/migrations_archive/20260428143000_phase2_analytics_v2_tables.sql``.
    A migration proposta
    ``supposed/20260526075000_g5_refresh_dashboards_job.sql`` amplia
    o CHECK para incluir ``csv_sync``, mas não foi aplicada.

    Esta asserção testa que o CHECK do ``reg_jobs`` no baseline JÁ
    contém o literal ``'csv_sync'`` — como não contém, o teste
    FALHA (RED).
    """
    baseline = _read_baseline()

    # Sanity: a migration proposta existe (para contexto da mensagem).
    proposed_note = ""
    if PROPOSED_REG_JOBS_CHECK_PATH.exists():
        proposed_note = (
            f" A migration `{PROPOSED_REG_JOBS_CHECK_PATH.relative_to(REPO_ROOT)}` "
            f"amplia o CHECK para incluir `csv_sync`, mas está em "
            f"`proposed/` e ainda não foi aplicada ao baseline."
        )

    # Procura por uma definição de CHECK para job_type que mencione csv_sync.
    # Aceita tanto a sintaxe `CHECK (job_type IN (...))` quanto
    # `CHECK (job_type = ANY (ARRAY[...]))` (a migration proposta
    # usa a segunda forma).
    has_check_with_csv_sync = bool(
        re.search(
            r"CHECK\s*\(\s*job_type\b[\s\S]{0,400}?['\"]csv_sync['\"]",
            baseline,
            re.IGNORECASE,
        )
    )
    assert has_check_with_csv_sync, (
        "AC#4 violada — RED. O baseline `20260523999999_baseline_v2.sql` "
        "NÃO contém nenhum `CHECK (job_type ...)` que aceite o valor "
        "`csv_sync`. A constraint atual (em `migrations_archive/`) "
        "aceita apenas `('bigquery_sync','connector_sync','analytics_etl',"
        "'custom')`, e essa definição nem sequer está no baseline — "
        "vive apenas no arquivo arquivado. "
        f"{proposed_note} "
        "A implementação GREEN deve materializar a tabela "
        "`analytics_v2.reg_jobs` no baseline COM o `CHECK (job_type)` "
        "ampliado para incluir `csv_sync` (e idealmente também "
        "`refresh_dashboards`, que vem na mesma migration). "
        "Sem isso, qualquer INSERT de job CSV em `reg_jobs` será "
        "rejeitado pela constraint."
    )


# ── AC#5: schema analytics_v2 exposto em [api] schemas ──────────────────


def test_etl_ac5_config_toml_exposes_analytics_v2_schema():
    """AC#5 — O schema ``analytics_v2`` DEVE estar listado em
    ``[api] schemas`` no ``supabase/config.toml``.

    Atualmente (PASS — documenta-se como AC) a linha 10 de
    ``supabase/config.toml`` já contém:

        schemas = ["public", "analytics_v2", "vector_db"]

    Esta asserção testa que ``"analytics_v2"`` está presente na
    lista de schemas. Como JÁ está, o teste PASSA (verde), e a
    AC#5 fica documentada como parte do contrato end-to-end do
    pipeline de ETL.
    """
    config = _read_config_toml()

    # Localiza a seção [api] e o atributo schemas dentro dela.
    api_section_match = re.search(
        r"\[api\]([\s\S]+?)(?=^\[|\Z)",
        config,
        re.MULTILINE | re.IGNORECASE,
    )
    assert api_section_match is not None, (
        "AC#5 violada: não foi possível localizar a seção `[api]` em "
        f"{CONFIG_TOML_PATH}."
    )

    api_section = api_section_match.group(1)

    # Localiza schemas = [ ... ]
    schemas_match = re.search(
        r"^\s*schemas\s*=\s*\[([^\]]*)\]",
        api_section,
        re.MULTILINE | re.IGNORECASE,
    )
    assert schemas_match is not None, (
        "AC#5 violada: não foi possível localizar o atributo `schemas = [...]` "
        f"dentro da seção `[api]` em {CONFIG_TOML_PATH}."
    )

    schemas_list_raw = schemas_match.group(1)

    # Extrai os itens da lista (string literals) e normaliza aspas.
    items = [
        m.group(1).strip()
        for m in re.finditer(r"['\"]([^'\"]+)['\"]", schemas_list_raw)
    ]

    assert "analytics_v2" in items, (
        "AC#5 violada — RED. O schema `analytics_v2` NÃO está listado "
        f"em `[api] schemas` no {CONFIG_TOML_PATH}. "
        f"Schemas atualmente expostos: {items}. "
        f"A implementação GREEN deve adicionar `\"analytics_v2\"` à "
        f"lista `schemas = [\"public\", \"analytics_v2\", \"vector_db\"]` "
        f"para que tabelas, views e stored procedures desse schema "
        f"gerem endpoints da PostgREST API."
    )
