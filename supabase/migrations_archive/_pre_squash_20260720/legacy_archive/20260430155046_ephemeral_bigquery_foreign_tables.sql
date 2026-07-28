-- ════════════════════════════════════════════════════════════════════════════
-- Ephemeral BigQuery foreign tables
-- • fdw schema owns all FT objects (never public)
-- • FTs are created inside run_etl_job, scanned, then immediately dropped
-- • Discovery functions become metadata-only (no FT DDL)
-- • drop_bigquery_server no longer needs to loop through FT names
-- ════════════════════════════════════════════════════════════════════════════

-- ── 1. fdw schema ─────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS fdw;
GRANT USAGE ON SCHEMA fdw TO service_role;
GRANT ALL   ON SCHEMA fdw TO service_role;

-- ── 2. Shared column-defs helper ──────────────────────────────────────────────
-- Converts bigquery_foreign_tables.columns JSONB → SQL column definition string
-- Preserves original column order via WITH ORDINALITY
CREATE OR REPLACE FUNCTION public._bq_col_defs_from_jsonb(p_columns jsonb)
RETURNS text
LANGUAGE sql
STABLE
SET search_path TO 'public'
AS $$
  SELECT string_agg(
    format('%I %s', col->>'name', public._bq_type_to_postgres_type(col->>'type')),
    ', '
    ORDER BY ordinality
  )
  FROM jsonb_array_elements(p_columns) WITH ORDINALITY AS t(col, ordinality);
$$;

-- ── 3. Drop all stale bq_ft_* / bq_pending_* from public ─────────────────────
DO $cleanup$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND (tablename LIKE 'bq_ft_%' OR tablename LIKE 'bq_pending_%')
  LOOP
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS public.%I CASCADE', r.tablename);
    RAISE NOTICE 'Dropped stale foreign table: public.%', r.tablename;
  END LOOP;
END
$cleanup$;

-- ── 4. Drop foreign_table_name column — no longer meaningful ─────────────────
ALTER TABLE public.bigquery_foreign_tables
  DROP COLUMN IF EXISTS foreign_table_name;

-- ── 5. create_bigquery_foreign_table_from_schema → metadata only ──────────────
-- Called by the edge function after column discovery.
-- Saves columns to the registry. Creates NO foreign table object.
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table_from_schema(
  p_client_id text,
  p_columns   jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_server_name  TEXT;
  v_project_id   TEXT;
  v_dataset_id   TEXT;
  v_bare_table   TEXT;
  v_col_defs     TEXT;
BEGIN
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  SELECT table_name INTO v_bare_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bare_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);
  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty or contains unmappable types');
  END IF;

  UPDATE public.bigquery_foreign_tables
  SET columns        = p_columns,
      server_name    = v_server_name,
      bigquery_table = public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  WHERE client_id::text = p_client_id::text;

  RETURN jsonb_build_object(
    'success',       true,
    'columns_count', jsonb_array_length(p_columns),
    'bigquery_ref',  public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;

-- ── 6. update_bigquery_foreign_table_columns → metadata only ──────────────────
CREATE OR REPLACE FUNCTION public.update_bigquery_foreign_table_columns(
  p_client_id text,
  p_columns   jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_col_defs TEXT;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.bigquery_foreign_tables WHERE client_id::text = p_client_id::text
  ) THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);
  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty or contains unmappable types');
  END IF;

  UPDATE public.bigquery_foreign_tables
  SET columns = p_columns
  WHERE client_id::text = p_client_id::text;

  RETURN jsonb_build_object('success', true, 'columns_count', jsonb_array_length(p_columns));

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;

-- ── 7. drop_bigquery_server → remove FT loop (nothing to drop) ───────────────
CREATE OR REPLACE FUNCTION public.drop_bigquery_server(p_client_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name  TEXT;
  v_vault_key_id UUID;
  v_secret_name  TEXT;
  v_error_msg    TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name, vault_key_id
    INTO v_server_name, v_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object('success', true, 'message', 'No BigQuery server found for this tenant');
    END IF;

    -- FTs are ephemeral — nothing to DROP here; they only exist during run_etl_job

    BEGIN
      EXECUTE format('DROP USER MAPPING IF EXISTS FOR current_user SERVER %I', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;
      BEGIN
        DELETE FROM vault.decrypted_secrets WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN NULL;
      END;
    END IF;

    DELETE FROM public.client_data_sources
    WHERE client_id::text = v_my_client_id::text AND source_type = 'bigquery';

    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;
    DELETE FROM public.bigquery_servers        WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and registry removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;

-- ── 8. run_etl_job → ephemeral FT lifecycle ───────────────────────────────────
-- FT is created from registry metadata, used for one scan, then immediately dropped.
-- Drop happens in both the success path and the EXCEPTION handler.
CREATE OR REPLACE FUNCTION analytics_v2.run_etl_job(p_job_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout TO '0'
SET search_path TO 'public', 'analytics_v2', 'fdw'
AS $function$
DECLARE
  v_client_id           uuid;
  v_cred_id             bigint;
  v_mapping             jsonb;
  v_ft_bare             text;
  v_server_name         text;
  v_bq_columns          jsonb;
  v_bare_table          text;
  v_col_defs            text;

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
  v_start               timestamptz := clock_timestamp();
  v_rows                bigint  := 0;
  v_staged              bigint  := 0;
  v_duration            numeric;
BEGIN
  SET LOCAL statement_timeout = 0;

  -- ── Fetch job ─────────────────────────────────────────────────────────────────
  SELECT client_id, (input_params->>'credential_id')::bigint
  INTO v_client_id, v_cred_id
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id AND status = 'pending';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job % not found or not in pending state', p_job_id;
  END IF;

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

  -- ── Fetch FDW metadata from registry ─────────────────────────────────────────
  SELECT bft.server_name, bft.columns, bft.table_name
  INTO v_server_name, v_bq_columns, v_bare_table
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = v_client_id::text
  ORDER BY bft.created_at DESC
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery registration found for client_id=%. Connect BigQuery first.', v_client_id;
  END IF;

  IF v_bq_columns IS NULL OR jsonb_array_length(v_bq_columns) = 0 THEN
    RAISE EXCEPTION 'No columns registered for client_id=%. Run column discovery first.', v_client_id;
  END IF;

  -- ── Build and create ephemeral foreign table ──────────────────────────────────
  -- Name is deterministic: one slot per client, no random suffix accumulation
  v_ft_bare  := 'bq_ft_' || SUBSTRING(REPLACE(v_client_id::text, '-', ''), 1, 12);
  v_col_defs := public._bq_col_defs_from_jsonb(v_bq_columns);

  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_ft_bare, v_col_defs, v_server_name, v_bare_table
  );

  RAISE NOTICE '[run_etl_job] job=%: created ephemeral FT fdw.%', p_job_id, v_ft_bare;

  -- ── Invert column mapping ─────────────────────────────────────────────────────
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

  IF c_documento IS NULL THEN
    RAISE EXCEPTION 'Column mapping missing required field "documento". Got mapping: %', v_mapping;
  END IF;

  RAISE NOTICE '[run_etl_job] job=%: mapping resolved — documento=%, valor=%, data=%',
    p_job_id, c_documento, c_valor, c_data_competencia;

  -- ── Build SELECT clause ───────────────────────────────────────────────────────
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

  -- ── Clear leftover staging rows ────────────────────────────────────────────────
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 10, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Single FDW scan → staging ─────────────────────────────────────────────────
  EXECUTE format(
    'INSERT INTO analytics_v2.etl_staging
       (job_id, documento, data_competencia_raw, quantidade_raw, valor_unitario_raw, valor_raw,
        status, cliente_cpf_cnpj, cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
        fornecedor_cnpj, fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
        produto_sku, produto_nome)
     SELECT %L, %s FROM %I.%I',
    p_job_id, v_select, 'fdw', v_ft_bare
  );
  GET DIAGNOSTICS v_staged = ROW_COUNT;

  -- ── Drop ephemeral FT immediately after scan ──────────────────────────────────
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  RAISE NOTICE '[run_etl_job] job=%: dropped ephemeral FT fdw.%, staged % rows', p_job_id, v_ft_bare, v_staged;

  UPDATE analytics_v2.reg_jobs
  SET progress_pct = 55, rows_inserted = v_staged, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Upsert dim_clientes ───────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(cliente_cpf_cnpj, cliente_nome))
    v_client_id,
    COALESCE(cliente_cpf_cnpj, cliente_nome),
    cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(cliente_cpf_cnpj, cliente_nome) IS NOT NULL
  ORDER BY COALESCE(cliente_cpf_cnpj, cliente_nome)
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 65, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_fornecedores ───────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(fornecedor_cnpj, fornecedor_nome))
    v_client_id,
    COALESCE(fornecedor_cnpj, fornecedor_nome),
    fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(fornecedor_cnpj, fornecedor_nome) IS NOT NULL
  ORDER BY COALESCE(fornecedor_cnpj, fornecedor_nome)
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 75, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_inventory ──────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (COALESCE(produto_sku, produto_nome))
    v_client_id, COALESCE(produto_sku, produto_nome), produto_nome, clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(produto_sku, produto_nome) IS NOT NULL
  ORDER BY COALESCE(produto_sku, produto_nome)
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome = EXCLUDED.nome, updated_at = EXCLUDED.updated_at;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 82, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_datas ──────────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    d::date,
    EXTRACT(year  FROM d)::int, EXTRACT(month  FROM d)::int, EXTRACT(day FROM d)::int,
    CASE WHEN EXTRACT(dow FROM d) = 0 THEN 7 ELSE EXTRACT(dow FROM d)::int END,
    EXTRACT(week FROM d)::int,
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

  UPDATE analytics_v2.reg_jobs SET progress_pct = 88, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert fato_transacoes ────────────────────────────────────────────────────
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, client_id, fornecedor_id, produto_id,
     documento, quantidade, valor_unitario, valor, status)
  SELECT
    md5(v_client_id::text || ':' ||
        COALESCE(s.documento, '')            || ':' ||
        COALESCE(s.data_competencia_raw, '') || ':' ||
        COALESCE(s.produto_sku, ''))         AS transacao_id,
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
           THEN (s.data_competencia_raw::timestamptz)::date ELSE NULL END
    )
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.client_id = v_client_id AND dc.cpf_cnpj = COALESCE(s.cliente_cpf_cnpj, s.cliente_nome)
  LEFT JOIN analytics_v2.dim_fornecedores df
    ON df.client_id = v_client_id AND df.cnpj = COALESCE(s.fornecedor_cnpj, s.fornecedor_nome)
  LEFT JOIN analytics_v2.dim_inventory di
    ON di.client_id = v_client_id AND di.sku = COALESCE(s.produto_sku, s.produto_nome)
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

  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'completed',
    completed_at     = clock_timestamp(),
    rows_inserted    = v_rows,
    progress_pct     = 100,
    duration_seconds = v_duration,
    output           = jsonb_build_object(
                         'rows_inserted', v_rows,
                         'rows_staged',   v_staged,
                         'completed_at',  now()::text
                       ),
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;

  RAISE NOTICE '[run_etl_job] job=%: DONE — % fato rows from % staged rows in %.1fs',
    p_job_id, v_rows, v_staged, v_duration;

  -- ── Refresh aggregates (non-fatal) ────────────────────────────────────────────
  BEGIN
    PERFORM analytics_v2.atualizar_agregados(v_client_id);
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[run_etl_job] job=%: aggregate refresh failed (non-fatal): %', p_job_id, SQLERRM;
  END;

EXCEPTION WHEN OTHERS THEN
  -- Always drop the ephemeral FT, even on failure
  IF v_ft_bare IS NOT NULL THEN
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
    RAISE NOTICE '[run_etl_job] job=%: dropped ephemeral FT fdw.% after failure', p_job_id, v_ft_bare;
  END IF;
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;
  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET status = 'failed', completed_at = clock_timestamp(), progress_pct = 0,
      duration_seconds = v_duration, error_message = SQLERRM, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;
  RAISE;
END;
$function$;
