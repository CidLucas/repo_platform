-- Migration: rewrite run_etl_job with batch FDW reads and correct mapping inversion
--
-- Root causes fixed:
--   1. Column mapping inversion bug: mapping is stored as {source_col: canonical},
--      but the old code read v_mapping->>'documento' (looking for key "documento").
--      All 18 columns resolved to NULL → no data was ever written correctly.
--      Fix: use SELECT key FROM jsonb_each_text(v_mapping) WHERE value = 'canonical'
--
--   2. Single FDW scan timeout: CREATE TEMP TABLE ... AS SELECT * FROM bq_ft_...
--      on 100k rows takes >30s, hitting the statement timeout even with SET statement_timeout=0
--      on the outer function (the 30s timer starts fresh for each statement).
--      Fix: LIMIT/OFFSET batch loop — each iteration reads 15k rows (~few seconds each).
--
--   3. TEMP TABLE limitation: temp tables are session-scoped and invisible across
--      nested function calls / pg_cron sessions. Replaced with persistent
--      analytics_v2.etl_staging table keyed by job_id.
--
-- Architecture after this migration:
--   1. run-sync-etl edge function creates reg_jobs record (status=pending), returns job_id
--   2. pg_cron fires every minute → process_pending_etl_jobs() → run_etl_job(job_id)
--   3. run_etl_job:
--        a. Inverts column mapping to resolve source column names
--        b. Loops: LIMIT 15000 OFFSET v_offset → INSERT into analytics_v2.etl_staging
--        c. After all batches: upsert dim_clientes, dim_fornecedores, dim_inventory, dim_datas
--        d. Upsert fato_transacoes (dimension IDs resolved via JOINs from staging)
--        e. DELETE staging rows (both success and failure paths)


-- ── 1. Persistent staging table (replaces TEMP TABLE) ─────────────────────────
CREATE TABLE IF NOT EXISTS analytics_v2.etl_staging (
  id                    bigserial PRIMARY KEY,
  job_id                uuid        NOT NULL,
  documento             text,
  data_competencia_raw  text,
  quantidade_raw        text,
  valor_unitario_raw    text,
  valor_raw             text,
  status                text,
  cliente_cpf_cnpj      text,
  cliente_nome          text,
  cliente_telefone      text,
  cliente_cidade        text,
  cliente_uf            text,
  fornecedor_cnpj       text,
  fornecedor_nome       text,
  fornecedor_telefone   text,
  fornecedor_cidade     text,
  fornecedor_uf         text,
  produto_sku           text,
  produto_nome          text
);

CREATE INDEX IF NOT EXISTS etl_staging_job_id_idx ON analytics_v2.etl_staging (job_id);


-- ── 2. run_etl_job: batch FDW reads + correct mapping inversion ───────────────
CREATE OR REPLACE FUNCTION analytics_v2.run_etl_job(p_job_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = 0
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_client_id           uuid;
  v_cred_id             bigint;
  v_mapping             jsonb;
  v_ft_name             text;

  -- Source column names resolved by inverting the mapping
  -- (stored as {source_col: canonical} → find key WHERE value = canonical)
  c_documento           text;
  c_data_competencia    text;
  c_quantidade          text;
  c_valor_unitario      text;
  c_valor               text;
  c_status              text;
  c_cliente_cpf_cnpj    text;
  c_cliente_nome        text;
  c_cliente_telefone    text;
  c_cliente_cidade      text;
  c_cliente_uf          text;
  c_fornecedor_cnpj     text;
  c_fornecedor_nome     text;
  c_fornecedor_telefone text;
  c_fornecedor_cidade   text;
  c_fornecedor_uf       text;
  c_produto_sku         text;
  c_produto_nome        text;

  v_select              text;
  v_batch_size          int     := 15000;
  v_offset              bigint  := 0;
  v_batch_rows          bigint  := 0;
  v_total_rows          bigint  := 0;
  v_start               timestamptz := clock_timestamp();
  v_rows                bigint  := 0;
  v_duration            numeric;
BEGIN
  -- ── Fetch job ────────────────────────────────────────────────────────────────
  SELECT client_id, (input_params->>'credential_id')::bigint
  INTO v_client_id, v_cred_id
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id AND status = 'pending';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job % not found or not in pending state', p_job_id;
  END IF;

  -- ── Mark running ─────────────────────────────────────────────────────────────
  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = clock_timestamp(), progress_pct = 5, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Fetch column mapping ──────────────────────────────────────────────────────
  SELECT column_mapping INTO v_mapping
  FROM public.client_data_sources
  WHERE client_id = v_client_id::text AND credential_id = v_cred_id
  ORDER BY atualizado_em DESC NULLS LAST
  LIMIT 1;

  IF v_mapping IS NULL OR v_mapping = '{}'::jsonb THEN
    RAISE EXCEPTION 'No column mapping found for client_id=% credential_id=%', v_client_id, v_cred_id;
  END IF;

  -- ── Fetch foreign table name ──────────────────────────────────────────────────
  SELECT foreign_table_name INTO v_ft_name
  FROM public.bigquery_foreign_tables
  WHERE client_id = v_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_ft_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery foreign table found for client_id=%', v_client_id;
  END IF;

  -- ── Resolve source column names (mapping is {source_col: canonical}) ──────────
  -- We invert: find the key (source col) whose value is the canonical name.
  SELECT key INTO c_documento           FROM jsonb_each_text(v_mapping) WHERE value = 'documento'           LIMIT 1;
  SELECT key INTO c_data_competencia    FROM jsonb_each_text(v_mapping) WHERE value = 'data_competencia_id' LIMIT 1;
  SELECT key INTO c_quantidade          FROM jsonb_each_text(v_mapping) WHERE value = 'quantidade'          LIMIT 1;
  SELECT key INTO c_valor_unitario      FROM jsonb_each_text(v_mapping) WHERE value = 'valor_unitario'      LIMIT 1;
  SELECT key INTO c_valor               FROM jsonb_each_text(v_mapping) WHERE value = 'valor'               LIMIT 1;
  SELECT key INTO c_status              FROM jsonb_each_text(v_mapping) WHERE value = 'status'              LIMIT 1;
  SELECT key INTO c_cliente_cpf_cnpj    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cpf_cnpj'   LIMIT 1;
  SELECT key INTO c_cliente_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_nome'        LIMIT 1;
  SELECT key INTO c_cliente_telefone    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_telefone'    LIMIT 1;
  SELECT key INTO c_cliente_cidade      FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cidade'      LIMIT 1;
  SELECT key INTO c_cliente_uf          FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_uf'          LIMIT 1;
  SELECT key INTO c_fornecedor_cnpj     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cnpj'     LIMIT 1;
  SELECT key INTO c_fornecedor_nome     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_nome'     LIMIT 1;
  SELECT key INTO c_fornecedor_telefone FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_telefone' LIMIT 1;
  SELECT key INTO c_fornecedor_cidade   FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cidade'   LIMIT 1;
  SELECT key INTO c_fornecedor_uf       FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_uf'       LIMIT 1;
  SELECT key INTO c_produto_sku         FROM jsonb_each_text(v_mapping) WHERE value = 'produto_sku'         LIMIT 1;
  SELECT key INTO c_produto_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'produto_nome'        LIMIT 1;

  -- At least documento must be mapped or the ETL is useless
  IF c_documento IS NULL THEN
    RAISE EXCEPTION 'Column mapping missing required field "documento". Got mapping: %', v_mapping;
  END IF;

  RAISE NOTICE '[run_etl_job] job=%: resolved mapping — documento=%, valor=%, data=%',
    p_job_id, c_documento, c_valor, c_data_competencia;

  -- ── Build SELECT clause (source column → canonical alias) ─────────────────────
  v_select := format(
    $sel$
      %s::text AS documento,
      %s::text AS data_competencia_raw,
      %s::text AS quantidade_raw,
      %s::text AS valor_unitario_raw,
      %s::text AS valor_raw,
      %s::text AS status,
      %s::text AS cliente_cpf_cnpj,
      %s::text AS cliente_nome,
      %s::text AS cliente_telefone,
      %s::text AS cliente_cidade,
      %s::text AS cliente_uf,
      %s::text AS fornecedor_cnpj,
      %s::text AS fornecedor_nome,
      %s::text AS fornecedor_telefone,
      %s::text AS fornecedor_cidade,
      %s::text AS fornecedor_uf,
      %s::text AS produto_sku,
      %s::text AS produto_nome
    $sel$,
    CASE WHEN c_documento           IS NOT NULL THEN format('%I', c_documento)           ELSE 'NULL' END,
    CASE WHEN c_data_competencia    IS NOT NULL THEN format('%I', c_data_competencia)    ELSE 'NULL' END,
    CASE WHEN c_quantidade          IS NOT NULL THEN format('%I', c_quantidade)          ELSE 'NULL' END,
    CASE WHEN c_valor_unitario      IS NOT NULL THEN format('%I', c_valor_unitario)      ELSE 'NULL' END,
    CASE WHEN c_valor               IS NOT NULL THEN format('%I', c_valor)               ELSE 'NULL' END,
    CASE WHEN c_status              IS NOT NULL THEN format('%I', c_status)              ELSE 'NULL' END,
    CASE WHEN c_cliente_cpf_cnpj    IS NOT NULL THEN format('%I', c_cliente_cpf_cnpj)    ELSE 'NULL' END,
    CASE WHEN c_cliente_nome        IS NOT NULL THEN format('%I', c_cliente_nome)        ELSE 'NULL' END,
    CASE WHEN c_cliente_telefone    IS NOT NULL THEN format('%I', c_cliente_telefone)    ELSE 'NULL' END,
    CASE WHEN c_cliente_cidade      IS NOT NULL THEN format('%I', c_cliente_cidade)      ELSE 'NULL' END,
    CASE WHEN c_cliente_uf          IS NOT NULL THEN format('%I', c_cliente_uf)          ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cnpj     IS NOT NULL THEN format('%I', c_fornecedor_cnpj)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_nome     IS NOT NULL THEN format('%I', c_fornecedor_nome)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_telefone IS NOT NULL THEN format('%I', c_fornecedor_telefone) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cidade   IS NOT NULL THEN format('%I', c_fornecedor_cidade)   ELSE 'NULL' END,
    CASE WHEN c_fornecedor_uf       IS NOT NULL THEN format('%I', c_fornecedor_uf)       ELSE 'NULL' END,
    CASE WHEN c_produto_sku         IS NOT NULL THEN format('%I', c_produto_sku)         ELSE 'NULL' END,
    CASE WHEN c_produto_nome        IS NOT NULL THEN format('%I', c_produto_nome)        ELSE 'NULL' END
  );

  -- ── Clear any leftover staging rows from a previous failed attempt ────────────
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  -- ── Batch loop: read FDW in chunks, INSERT into staging ───────────────────────
  -- Each iteration is one short SQL statement (LIMIT rows), not a full table scan.
  -- With statement_timeout=0 on this function, no individual batch can be cancelled.
  LOOP
    EXECUTE format(
      'INSERT INTO analytics_v2.etl_staging (job_id, %s)
       SELECT %L, %s FROM %I LIMIT %s OFFSET %s',
      'documento, data_competencia_raw, quantidade_raw, valor_unitario_raw, valor_raw,
       status, cliente_cpf_cnpj, cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
       fornecedor_cnpj, fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
       produto_sku, produto_nome',
      p_job_id,
      v_select,
      v_ft_name,
      v_batch_size,
      v_offset
    );

    GET DIAGNOSTICS v_batch_rows = ROW_COUNT;
    v_total_rows := v_total_rows + v_batch_rows;
    v_offset     := v_offset     + v_batch_rows;

    RAISE NOTICE '[run_etl_job] job=%: batch offset=% loaded % rows (total=%)',
      p_job_id, v_offset - v_batch_rows, v_batch_rows, v_total_rows;

    -- Progress: 5% → 60% during loading phase
    UPDATE analytics_v2.reg_jobs
    SET
      progress_pct = LEAST(60, 5 + (v_total_rows / GREATEST(v_batch_size, 1))::int * 8),
      rows_inserted = v_total_rows,
      updated_at   = clock_timestamp()
    WHERE job_id = p_job_id;

    -- Fewer rows than batch size → we reached the end of the foreign table
    EXIT WHEN v_batch_rows < v_batch_size;
  END LOOP;

  RAISE NOTICE '[run_etl_job] job=%: finished loading % rows in % batches from %',
    p_job_id, v_total_rows, ceil(v_total_rows::float / v_batch_size), v_ft_name;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 62, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_clientes ───────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(cliente_cpf_cnpj, cliente_nome))
    v_client_id,
    COALESCE(cliente_cpf_cnpj, cliente_nome),
    cliente_nome,
    cliente_telefone,
    cliente_cidade,
    cliente_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id
    AND COALESCE(cliente_cpf_cnpj, cliente_nome) IS NOT NULL
  ORDER BY COALESCE(cliente_cpf_cnpj, cliente_nome)
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 72, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_fornecedores ───────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(fornecedor_cnpj, fornecedor_nome))
    v_client_id,
    COALESCE(fornecedor_cnpj, fornecedor_nome),
    fornecedor_nome,
    fornecedor_telefone,
    fornecedor_cidade,
    fornecedor_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id
    AND COALESCE(fornecedor_cnpj, fornecedor_nome) IS NOT NULL
  ORDER BY COALESCE(fornecedor_cnpj, fornecedor_nome)
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 80, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_inventory ──────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (COALESCE(produto_sku, produto_nome))
    v_client_id,
    COALESCE(produto_sku, produto_nome),
    produto_nome,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id
    AND COALESCE(produto_sku, produto_nome) IS NOT NULL
  ORDER BY COALESCE(produto_sku, produto_nome)
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome       = EXCLUDED.nome,
    updated_at = EXCLUDED.updated_at;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 85, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_datas ──────────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    d::date,
    EXTRACT(year    FROM d)::int,
    EXTRACT(month   FROM d)::int,
    EXTRACT(day     FROM d)::int,
    CASE WHEN EXTRACT(dow FROM d) = 0 THEN 7 ELSE EXTRACT(dow FROM d)::int END,
    EXTRACT(week    FROM d)::int,
    CASE WHEN EXTRACT(month FROM d) <= 6 THEN 1 ELSE 2 END,
    'Q' || EXTRACT(quarter FROM d)::text
  FROM (
    SELECT data_competencia_raw::timestamptz AS d
    FROM analytics_v2.etl_staging
    WHERE job_id = p_job_id
      AND data_competencia_raw IS NOT NULL
      AND data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
  ) t
  ON CONFLICT (data) DO NOTHING;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 90, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert fato_transacoes ────────────────────────────────────────────────────
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, client_id, fornecedor_id, produto_id,
     documento, quantidade, valor_unitario, valor, status)
  SELECT
    md5(v_client_id::text || ':' ||
        COALESCE(s.documento, '')          || ':' ||
        COALESCE(s.data_competencia_raw, '') || ':' ||
        COALESCE(s.produto_sku, ''))       AS transacao_id,
    v_client_id,
    dd.data_id,
    dc.client_id,
    df.fornecedor_id,
    di.inventory_id,
    s.documento,
    analytics_v2.safe_to_numeric(s.quantidade_raw),
    analytics_v2.safe_to_numeric(s.valor_unitario_raw),
    analytics_v2.safe_to_numeric(s.valor_raw),
    s.status
  FROM analytics_v2.etl_staging s
  LEFT JOIN analytics_v2.dim_datas dd
    ON dd.data = (
      CASE WHEN s.data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
           THEN (s.data_competencia_raw::timestamptz)::date
           ELSE NULL END
    )
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.client_id = v_client_id
   AND dc.cpf_cnpj  = COALESCE(s.cliente_cpf_cnpj, s.cliente_nome)
  LEFT JOIN analytics_v2.dim_fornecedores df
    ON df.client_id = v_client_id
   AND df.cnpj      = COALESCE(s.fornecedor_cnpj, s.fornecedor_nome)
  LEFT JOIN analytics_v2.dim_inventory di
    ON di.client_id = v_client_id
   AND di.sku       = COALESCE(s.produto_sku, s.produto_nome)
  WHERE s.job_id = p_job_id
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    client_id          = EXCLUDED.client_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    documento           = EXCLUDED.documento,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status;

  GET DIAGNOSTICS v_rows = ROW_COUNT;

  -- ── Clean up staging ──────────────────────────────────────────────────────────
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  -- ── Complete ──────────────────────────────────────────────────────────────────
  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'completed',
    completed_at     = clock_timestamp(),
    rows_inserted    = v_rows,
    progress_pct     = 100,
    duration_seconds = v_duration,
    output           = jsonb_build_object(
                         'rows_inserted',  v_rows,
                         'rows_staged',    v_total_rows,
                         'batches',        ceil(v_total_rows::float / v_batch_size),
                         'batch_size',     v_batch_size,
                         'completed_at',   now()::text
                       ),
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;

  RAISE NOTICE '[run_etl_job] job=%: DONE — % fato rows inserted in %.1fs', p_job_id, v_rows, v_duration;

EXCEPTION WHEN OTHERS THEN
  -- Clean up staging on failure too
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'failed',
    completed_at     = clock_timestamp(),
    progress_pct     = 0,
    duration_seconds = v_duration,
    error_message    = SQLERRM,
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;
  RAISE;
END;
$$;
