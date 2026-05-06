-- Migration: replace process-job-async Edge Function with a PL/pgSQL ETL function.
--
-- Root cause of the edge function timeout: the default statement_timeout was
-- cancelling the FDW scan at ~2100 rows. A SECURITY DEFINER function with
-- SET statement_timeout = 0 bypasses that limit entirely.
--
-- Architecture after this migration:
--   1. run-sync-etl creates the reg_jobs record (status=pending) and returns job_id.
--   2. pg_cron fires every minute, calls process_pending_etl_jobs().
--   3. process_pending_etl_jobs() picks one pending job (SKIP LOCKED) and calls
--      run_etl_job(job_id).
--   4. run_etl_job does the full ETL:
--        a. Single FDW scan → _etl_staging temp table (no timeout)
--        b. Bulk upserts: dim_clientes, dim_fornecedores, dim_inventory, dim_datas
--        c. Bulk upsert: fato_transacoes (with dimension ID lookups via JOINs)
--        d. Progress updates to reg_jobs throughout


-- ── 1. Main ETL function ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.run_etl_job(p_job_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = 0        -- no timeout: FDW scans can take several minutes
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_client_id   uuid;
  v_cred_id     bigint;
  v_mapping     jsonb;
  v_ft_name     text;
  v_start       timestamptz := clock_timestamp();
  v_rows        bigint := 0;
  v_duration    numeric;

  -- Source column names resolved from the column_mapping JSONB
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

  v_select text;
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

  -- ── Resolve source column names from mapping ──────────────────────────────────
  c_documento           := v_mapping->>'documento';
  c_data_competencia    := v_mapping->>'data_competencia_id';
  c_quantidade          := v_mapping->>'quantidade';
  c_valor_unitario      := v_mapping->>'valor_unitario';
  c_valor               := v_mapping->>'valor';
  c_status              := v_mapping->>'status';
  c_cliente_cpf_cnpj    := v_mapping->>'cliente_cpf_cnpj';
  c_cliente_nome        := v_mapping->>'cliente_nome';
  c_cliente_telefone    := v_mapping->>'cliente_telefone';
  c_cliente_cidade      := v_mapping->>'cliente_cidade';
  c_cliente_uf          := v_mapping->>'cliente_uf';
  c_fornecedor_cnpj     := v_mapping->>'fornecedor_cnpj';
  c_fornecedor_nome     := v_mapping->>'fornecedor_nome';
  c_fornecedor_telefone := v_mapping->>'fornecedor_telefone';
  c_fornecedor_cidade   := v_mapping->>'fornecedor_cidade';
  c_fornecedor_uf       := v_mapping->>'fornecedor_uf';
  c_produto_sku         := v_mapping->>'produto_sku';
  c_produto_nome        := v_mapping->>'produto_nome';

  -- ── Build dynamic SELECT: source column → canonical name (NULL if unmapped) ───
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
    CASE WHEN c_documento IS NOT NULL THEN format('%I', c_documento) ELSE 'NULL' END,
    CASE WHEN c_data_competencia IS NOT NULL THEN format('%I', c_data_competencia) ELSE 'NULL' END,
    CASE WHEN c_quantidade IS NOT NULL THEN format('%I', c_quantidade) ELSE 'NULL' END,
    CASE WHEN c_valor_unitario IS NOT NULL THEN format('%I', c_valor_unitario) ELSE 'NULL' END,
    CASE WHEN c_valor IS NOT NULL THEN format('%I', c_valor) ELSE 'NULL' END,
    CASE WHEN c_status IS NOT NULL THEN format('%I', c_status) ELSE 'NULL' END,
    CASE WHEN c_cliente_cpf_cnpj IS NOT NULL THEN format('%I', c_cliente_cpf_cnpj) ELSE 'NULL' END,
    CASE WHEN c_cliente_nome IS NOT NULL THEN format('%I', c_cliente_nome) ELSE 'NULL' END,
    CASE WHEN c_cliente_telefone IS NOT NULL THEN format('%I', c_cliente_telefone) ELSE 'NULL' END,
    CASE WHEN c_cliente_cidade IS NOT NULL THEN format('%I', c_cliente_cidade) ELSE 'NULL' END,
    CASE WHEN c_cliente_uf IS NOT NULL THEN format('%I', c_cliente_uf) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cnpj IS NOT NULL THEN format('%I', c_fornecedor_cnpj) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_nome IS NOT NULL THEN format('%I', c_fornecedor_nome) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_telefone IS NOT NULL THEN format('%I', c_fornecedor_telefone) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cidade IS NOT NULL THEN format('%I', c_fornecedor_cidade) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_uf IS NOT NULL THEN format('%I', c_fornecedor_uf) ELSE 'NULL' END,
    CASE WHEN c_produto_sku IS NOT NULL THEN format('%I', c_produto_sku) ELSE 'NULL' END,
    CASE WHEN c_produto_nome IS NOT NULL THEN format('%I', c_produto_nome) ELSE 'NULL' END
  );

  -- ── Load entire FT into staging temp table (single scan, bypasses timeout) ───
  DROP TABLE IF EXISTS _etl_staging;  -- safety: discard leftovers from failed sessions
  EXECUTE format(
    'CREATE TEMP TABLE _etl_staging ON COMMIT DROP AS SELECT %s FROM %I',
    v_select, v_ft_name
  );
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  RAISE NOTICE '[run_etl_job] job=%: read % rows from %', p_job_id, v_rows, v_ft_name;

  UPDATE analytics_v2.reg_jobs
  SET progress_pct = 20, rows_inserted = v_rows, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

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
  FROM _etl_staging
  WHERE COALESCE(cliente_cpf_cnpj, cliente_nome) IS NOT NULL
  ORDER BY COALESCE(cliente_cpf_cnpj, cliente_nome)
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 40, updated_at = clock_timestamp() WHERE job_id = p_job_id;

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
  FROM _etl_staging
  WHERE COALESCE(fornecedor_cnpj, fornecedor_nome) IS NOT NULL
  ORDER BY COALESCE(fornecedor_cnpj, fornecedor_nome)
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 55, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_inventory ──────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (COALESCE(produto_sku, produto_nome))
    v_client_id,
    COALESCE(produto_sku, produto_nome),
    produto_nome,
    clock_timestamp()
  FROM _etl_staging
  WHERE COALESCE(produto_sku, produto_nome) IS NOT NULL
  ORDER BY COALESCE(produto_sku, produto_nome)
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome       = EXCLUDED.nome,
    updated_at = EXCLUDED.updated_at;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 65, updated_at = clock_timestamp() WHERE job_id = p_job_id;

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
    FROM _etl_staging
    WHERE data_competencia_raw IS NOT NULL
      AND data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
  ) t
  ON CONFLICT (data) DO NOTHING;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 72, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert fato_transacoes (dimension IDs resolved via JOINs) ────────────────
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, cliente_id, fornecedor_id, produto_id,
     documento, quantidade, valor_unitario, valor, status)
  SELECT
    md5(v_client_id::text || ':' ||
        COALESCE(s.documento, '')             || ':' ||
        COALESCE(s.data_competencia_raw, '')  || ':' ||
        COALESCE(s.produto_sku, ''))          AS transacao_id,
    v_client_id,
    dd.data_id,
    dc.cliente_id,
    df.fornecedor_id,
    di.inventory_id,
    s.documento,
    CASE WHEN s.quantidade_raw     ~ '^-?\d+(\.\d+)?$' THEN s.quantidade_raw::numeric     ELSE NULL END,
    CASE WHEN s.valor_unitario_raw ~ '^-?\d+(\.\d+)?$' THEN s.valor_unitario_raw::numeric ELSE NULL END,
    CASE WHEN s.valor_raw          ~ '^-?\d+(\.\d+)?$' THEN s.valor_raw::numeric          ELSE NULL END,
    s.status
  FROM _etl_staging s
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
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    cliente_id          = EXCLUDED.cliente_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    documento           = EXCLUDED.documento,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status;

  GET DIAGNOSTICS v_rows = ROW_COUNT;

  -- ── Complete ──────────────────────────────────────────────────────────────────
  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'completed',
    completed_at     = clock_timestamp(),
    rows_inserted    = v_rows,
    progress_pct     = 100,
    duration_seconds = v_duration,
    output           = jsonb_build_object('rows_inserted', v_rows, 'completed_at', now()::text),
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;

  RAISE NOTICE '[run_etl_job] job=%: completed % fato rows in %.1fs', p_job_id, v_rows, v_duration;

EXCEPTION WHEN OTHERS THEN
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


-- ── 2. Dispatcher (called by pg_cron) ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.process_pending_etl_jobs()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_job_id uuid;
BEGIN
  -- One pending job at a time; SKIP LOCKED prevents double-processing if
  -- the previous cron tick is still running.
  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE status = 'pending' AND job_type = 'bigquery_sync'
  ORDER BY created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_job_id IS NOT NULL THEN
    RAISE NOTICE '[process_pending_etl_jobs] dispatching job %', v_job_id;
    PERFORM analytics_v2.run_etl_job(v_job_id);
  END IF;
END;
$$;


-- ── 3. pg_cron schedule (every minute) ────────────────────────────────────────

SELECT cron.schedule(
  'process-pending-etl-jobs',
  '* * * * *',
  $$SELECT analytics_v2.process_pending_etl_jobs()$$
);
