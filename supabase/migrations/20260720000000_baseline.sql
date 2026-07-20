-- =====================================================================
-- BASELINE — espelho do schema de PRODUÇÃO (project haruewffnubdgyofftut)
-- Gerado em 2026-07-20 via `supabase db dump` (pg_dump 17, servidor 17.6).
-- Squash de 121 migrations históricas (ver supabase/migrations_archive/).
--
-- Conteúdo: schemas public, analytics_v2, vector_db, _trace, admin,
-- bigquery, fdw, util — tabelas, funções, views, matviews, triggers,
-- RLS policies, índices, grants, extensões e publicação de realtime.
-- Cron jobs (pg_cron) reconstruídos no bloco ao final.
--
-- NÃO editar à mão para "corrigir" prod: este arquivo reflete o estado
-- real do banco. Mudanças de schema vão em migrations novas posteriores.
-- =====================================================================





SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "_trace";


ALTER SCHEMA "_trace" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "admin";


ALTER SCHEMA "admin" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "analytics_v2";


ALTER SCHEMA "analytics_v2" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "bigquery";


ALTER SCHEMA "bigquery" OWNER TO "postgres";


COMMENT ON SCHEMA "bigquery" IS 'Schema for BigQuery foreign tables via Supabase FDW';



CREATE EXTENSION IF NOT EXISTS "pg_cron" WITH SCHEMA "pg_catalog";






CREATE SCHEMA IF NOT EXISTS "fdw";


ALTER SCHEMA "fdw" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE SCHEMA IF NOT EXISTS "util";


ALTER SCHEMA "util" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "vector_db";


ALTER SCHEMA "vector_db" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "hypopg" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "index_advisor" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "wrappers" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "_trace"."capture"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_payload jsonb;
  v_pk text;
  v_client uuid;
  v_changed text[];
  v_row record;
BEGIN
  IF TG_OP = 'DELETE' THEN v_row := OLD; ELSE v_row := NEW; END IF;
  v_payload := to_jsonb(v_row);

  -- Sanitiza secret value
  IF TG_TABLE_NAME = 'secrets' THEN
    v_payload := v_payload - 'secret' - 'decrypted_secret';
  END IF;

  -- PK best-effort
  v_pk := COALESCE(v_payload->>'id', v_payload->>'client_id', v_payload->>'name');
  v_client := NULLIF(v_payload->>'client_id','')::uuid;

  IF TG_OP = 'UPDATE' THEN
    SELECT array_agg(key) INTO v_changed
    FROM jsonb_each(to_jsonb(NEW)) n
    WHERE n.value IS DISTINCT FROM (to_jsonb(OLD)->n.key);
  END IF;

  INSERT INTO _trace.onboarding_events(table_name, op, pk, client_id, changed_cols, payload)
  VALUES (TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME, TG_OP, v_pk, v_client, v_changed, v_payload);

  RETURN v_row;
EXCEPTION WHEN OTHERS THEN
  -- nunca quebrar fluxo principal
  RETURN v_row;
END $$;


ALTER FUNCTION "_trace"."capture"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "admin"."_table_has_client"("p_schema" "text", "p_table" "text", "p_fk" "text", "p_client_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    AS $_$
DECLARE v_exists boolean;
BEGIN
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I.%I WHERE %I = $1 LIMIT 1)',
                 p_schema, p_table, p_fk)
    USING p_client_id INTO v_exists;
  RETURN v_exists;
END;
$_$;


ALTER FUNCTION "admin"."_table_has_client"("p_schema" "text", "p_table" "text", "p_fk" "text", "p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "admin"."request_client_deletion"("p_client_id" "uuid", "p_reason" "text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'admin'
    AS $$
DECLARE
  v_job_id uuid;
  v_existing_job uuid;
BEGIN
  -- Validações
  IF p_client_id IS NULL THEN
    RAISE EXCEPTION 'client_id is required';
  END IF;
  IF p_reason IS NULL OR length(trim(p_reason)) < 5 THEN
    RAISE EXCEPTION 'reason must be at least 5 chars';
  END IF;

  -- Cliente existe?
  IF NOT EXISTS (SELECT 1 FROM public.clientes_blu WHERE client_id = p_client_id) THEN
    RAISE EXCEPTION 'client_id % not found in clientes_blu', p_client_id;
  END IF;

  -- Job ativo já existente?
  SELECT job_id INTO v_existing_job
  FROM admin.tenant_wipe_jobs
  WHERE client_id = p_client_id AND status IN ('queued','running')
  LIMIT 1;

  IF v_existing_job IS NOT NULL THEN
    RAISE NOTICE 'Wipe already scheduled: %', v_existing_job;
    RETURN v_existing_job;
  END IF;

  -- Soft-delete: bloqueia logins/rotinas imediatamente
  UPDATE public.clientes_blu
     SET deletion_status = 'deleting',
         deletion_requested_at = now()
   WHERE client_id = p_client_id;

  -- Enfileira
  INSERT INTO admin.tenant_wipe_jobs (client_id, reason, requested_by, status)
  VALUES (p_client_id, p_reason, auth.uid(), 'queued')
  RETURNING job_id INTO v_job_id;

  RETURN v_job_id;
END;
$$;


ALTER FUNCTION "admin"."request_client_deletion"("p_client_id" "uuid", "p_reason" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "admin"."tenant_wipe_tick"("p_batch_size" integer DEFAULT 5000, "p_max_seconds" integer DEFAULT 25) RETURNS TABLE("job_id" "uuid", "table_fqn" "text", "rows_deleted" integer, "finished" boolean)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'admin'
    AS $_$
DECLARE
  v_job          admin.tenant_wipe_jobs%ROWTYPE;
  v_target       record;
  v_rows         int;
  v_total_rows   int := 0;
  v_t0           timestamptz := clock_timestamp();
  v_t_batch      timestamptz;
  v_batch_no     int := 0;
  v_finished_job boolean := false;
  v_sql          text;
BEGIN
  SELECT * INTO v_job
  FROM admin.tenant_wipe_jobs
  WHERE status IN ('queued','running')
  ORDER BY (status='queued') DESC, COALESCE(started_at, created_at) ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF v_job.status = 'queued' THEN
    UPDATE admin.tenant_wipe_jobs
       SET status='running', started_at=now(), updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;
    v_job.status := 'running';
    v_job.started_at := now();
  END IF;

  FOR v_target IN
    SELECT t.*
    FROM admin.v_wipe_target_tables t
    WHERE (v_job.current_table IS NULL)
       OR (t.table_fqn >= v_job.current_table)
    ORDER BY t.priority, t.table_fqn
  LOOP
    LOOP
      IF EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds THEN
        EXIT;
      END IF;

      v_t_batch := clock_timestamp();
      v_batch_no := v_batch_no + 1;

      v_sql := format(
        'WITH victim AS (
           SELECT ctid FROM %I.%I
           WHERE %I = $1
           LIMIT $2
         )
         DELETE FROM %I.%I t USING victim WHERE t.ctid = victim.ctid',
        v_target.child_schema, v_target.child_table, v_target.fk_column,
        v_target.child_schema, v_target.child_table
      );

      EXECUTE v_sql USING v_job.client_id, p_batch_size;
      GET DIAGNOSTICS v_rows = ROW_COUNT;
      v_total_rows := v_total_rows + v_rows;

      INSERT INTO admin.tenant_wipe_audit(job_id, table_name, batch_no, rows_deleted, duration_ms)
      VALUES (
        v_job.job_id, v_target.table_fqn, v_batch_no, v_rows,
        EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_t_batch))::int
      );

      job_id := v_job.job_id;
      table_fqn := v_target.table_fqn;
      rows_deleted := v_rows;
      finished := false;
      RETURN NEXT;

      EXIT WHEN v_rows = 0;

      PERFORM pg_sleep(0.05);
    END LOOP;

    UPDATE admin.tenant_wipe_jobs
       SET current_table = v_target.table_fqn,
           rows_deleted_total = rows_deleted_total + v_total_rows,
           updated_at = now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    EXIT WHEN EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds;
  END LOOP;

  PERFORM 1
    FROM admin.v_wipe_target_tables t
    WHERE admin._table_has_client(t.child_schema, t.child_table, t.fk_column, v_job.client_id)
    LIMIT 1;

  IF NOT FOUND THEN
    DROP TABLE IF EXISTS _users_to_delete;
    CREATE TEMP TABLE _users_to_delete ON COMMIT DROP AS
      SELECT auth_user_id AS user_id FROM public.client_users WHERE client_id = v_job.client_id AND auth_user_id IS NOT NULL;

    DELETE FROM vault.secrets
      WHERE name LIKE 'oauth_google_'    || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'oauth_%_'         || v_job.client_id || '\_%' ESCAPE '\'
         OR name = 'bigquery_service_account_' || v_job.client_id
         OR name LIKE 'bigquery_'        || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'integration_%\_'  || v_job.client_id || '%' ESCAPE '\';

    DELETE FROM public.clientes_blu WHERE client_id = v_job.client_id;

    DELETE FROM auth.users WHERE id IN (SELECT user_id FROM _users_to_delete);

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS bigquery_%s CASCADE', v_job.client_id);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Skipping FDW server drop for %: %', v_job.client_id, SQLERRM;
    END;

    UPDATE admin.tenant_wipe_jobs
       SET status='completed',
           progress_pct=100,
           completed_at=now(),
           updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    v_finished_job := true;
  END IF;

  job_id := v_job.job_id;
  table_fqn := COALESCE(v_target.table_fqn, '(end)');
  rows_deleted := 0;
  finished := v_finished_job;
  RETURN NEXT;
END;
$_$;


ALTER FUNCTION "admin"."tenant_wipe_tick"("p_batch_size" integer, "p_max_seconds" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."_period_range"("p_period" "text") RETURNS TABLE("start_date" "date", "prev_start" "date", "prev_end" "date")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
  SELECT
    CASE p_period
      WHEN '7d'  THEN CURRENT_DATE - 7
      WHEN '30d' THEN CURRENT_DATE - 30
      WHEN '90d' THEN CURRENT_DATE - 90
      WHEN '1y'  THEN CURRENT_DATE - 365
      WHEN 'mtd' THEN date_trunc('month', CURRENT_DATE)::date
      WHEN 'ytd' THEN date_trunc('year',  CURRENT_DATE)::date
      ELSE CURRENT_DATE - 30
    END,
    CASE p_period
      WHEN '7d'  THEN CURRENT_DATE - 14
      WHEN '30d' THEN CURRENT_DATE - 60
      WHEN '90d' THEN CURRENT_DATE - 180
      WHEN '1y'  THEN CURRENT_DATE - 730
      WHEN 'mtd' THEN (date_trunc('month', CURRENT_DATE) - INTERVAL '1 month')::date
      WHEN 'ytd' THEN (date_trunc('year',  CURRENT_DATE) - INTERVAL '1 year')::date
      ELSE CURRENT_DATE - 60
    END,
    CASE p_period
      WHEN '7d'  THEN CURRENT_DATE - 7
      WHEN '30d' THEN CURRENT_DATE - 30
      WHEN '90d' THEN CURRENT_DATE - 90
      WHEN '1y'  THEN CURRENT_DATE - 365
      WHEN 'mtd' THEN date_trunc('month', CURRENT_DATE)::date
      WHEN 'ytd' THEN date_trunc('year',  CURRENT_DATE)::date
      ELSE CURRENT_DATE - 30
    END;
$$;


ALTER FUNCTION "analytics_v2"."_period_range"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."apply_staging_to_facts"("p_job_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_client_id           uuid;
  v_source_id           uuid;
  v_mapping             jsonb;
  v_watermark_col       text;
  v_watermark_canonical text;
  v_last_watermark      text;
  v_force_full          boolean;
  v_client_cpf_cnpj     text;
  v_row_count           bigint := 0;
  v_new_watermark       text;
  v_start_time          timestamptz := clock_timestamp();
BEGIN
  -- 1. Resolve job → client + source + mapping
  SELECT j.client_id,
         (j.input_params->>'source_id')::uuid,
         COALESCE((j.input_params->>'force_full_sync')::boolean, false)
    INTO v_client_id, v_source_id, v_force_full
    FROM analytics_v2.reg_jobs j
   WHERE j.job_id = p_job_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION '[apply_staging] job % not found', p_job_id;
  END IF;
  IF v_source_id IS NULL THEN
    RAISE EXCEPTION '[apply_staging] job % has no source_id in input_params', p_job_id;
  END IF;

  SELECT cds.column_mapping,
         cds.watermark_column,
         cds.last_watermark_value
    INTO v_mapping, v_watermark_col, v_last_watermark
    FROM public.client_data_sources cds
   WHERE cds.id = v_source_id AND cds.client_id = v_client_id;

  IF v_mapping IS NULL OR v_mapping = 'null'::jsonb THEN v_mapping := '{}'::jsonb; END IF;

  -- Resolve watermark canonical name (the user-facing key in raw_data).
  -- column_mapping maps source_column → canonical_name. Watermark column is
  -- stored as source_column on cds, so we look it up.
  IF v_watermark_col IS NOT NULL THEN
    v_watermark_canonical := COALESCE(v_mapping->>v_watermark_col, v_watermark_col);
  END IF;

  SELECT cpf_cnpj INTO v_client_cpf_cnpj
    FROM public.clientes_blu WHERE client_id = v_client_id;

  -- 2. Sanity: rows present?
  SELECT count(*) INTO v_row_count
    FROM analytics_v2.ingest_staging
   WHERE job_id = p_job_id;

  IF v_row_count = 0 THEN
    UPDATE analytics_v2.reg_jobs
       SET status        = 'completed',
           completed_at  = now(),
           rows_inserted = 0,
           progress_pct  = 100,
           error_message = 'No staged rows for this job',
           updated_at    = now()
     WHERE job_id = p_job_id;
    RETURN jsonb_build_object('success', true, 'job_id', p_job_id, 'rows_inserted', 0);
  END IF;

  -- 3. Build canonical view of staging once via CTE expansion. column_mapping
  --    is source_column → canonical_name. We apply it inline so downstream
  --    UPSERTs read by canonical name regardless of source.
  --    raw_data already arrives with source_column keys, so we rename via
  --    jsonb_object_agg.
  CREATE TEMP TABLE IF NOT EXISTS _apply_canonical (
    row_index   integer,
    documento   text,
    data_comp   text,
    data_date   date,
    quantidade  numeric,
    valor_un    numeric,
    valor       numeric,
    status      text,
    tipo_lanc   text,
    categoria   text,
    subcat      text,
    tipo_trans  text,
    c_cpfcnpj   text, c_nome text, c_tel text, c_cidade text, c_uf text,
    f_cnpj      text, f_nome text, f_tel text, f_cidade text, f_uf text,
    p_sku       text, p_nome text,
    canonical   jsonb
  ) ON COMMIT DROP;

  TRUNCATE _apply_canonical;

  INSERT INTO _apply_canonical
  SELECT
    s.row_index,
    NULLIF(canonical->>'documento', ''),
    canonical->>'data_competencia_id',
    analytics_v2.parse_ingest_date(canonical->>'data_competencia_id'),
    NULLIF(canonical->>'quantidade','')::numeric,
    NULLIF(canonical->>'valor_unitario','')::numeric,
    NULLIF(canonical->>'valor','')::numeric,
    NULLIF(canonical->>'status',''),
    NULLIF(canonical->>'tipo_lancamento',''),
    NULLIF(canonical->>'categoria',''),
    NULLIF(canonical->>'subcategoria',''),
    NULLIF(canonical->>'tipo_transacao',''),
    NULLIF(canonical->>'cliente_cpf_cnpj',''),
    NULLIF(canonical->>'cliente_nome',''),
    NULLIF(canonical->>'cliente_telefone',''),
    NULLIF(canonical->>'cliente_cidade',''),
    NULLIF(canonical->>'cliente_uf',''),
    NULLIF(canonical->>'fornecedor_cnpj',''),
    NULLIF(canonical->>'fornecedor_nome',''),
    NULLIF(canonical->>'fornecedor_telefone',''),
    NULLIF(canonical->>'fornecedor_cidade',''),
    NULLIF(canonical->>'fornecedor_uf',''),
    NULLIF(canonical->>'produto_sku',''),
    NULLIF(canonical->>'produto_nome',''),
    canonical
  FROM (
    SELECT
      row_index,
      raw_data,
      -- Rename source_columns → canonical names using mapping. Keys not in
      -- the mapping pass through unchanged (so canonical-named keys from
      -- non-mapped sources still work).
      ( SELECT COALESCE(jsonb_object_agg(COALESCE(v_mapping->>k, k), v), '{}'::jsonb)
          FROM jsonb_each(raw_data) AS kv(k, v)
      ) AS canonical
    FROM analytics_v2.ingest_staging
    WHERE job_id = p_job_id
  ) s;

  -- 4. Upsert dim_clientes
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (c_cpfcnpj, c_nome)
    v_client_id,
    c_cpfcnpj,
    c_nome,
    c_tel,
    c_cidade,
    c_uf,
    now()
  FROM _apply_canonical
  WHERE c_cpfcnpj IS NOT NULL OR c_nome IS NOT NULL
  ORDER BY c_cpfcnpj, c_nome, row_index
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_clientes.nome),
    telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_clientes.telefone),
    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
    endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_clientes.endereco_uf),
    atualizado_em   = now();

  -- 5. Upsert dim_fornecedores
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (f_cnpj, f_nome)
    v_client_id, f_cnpj, f_nome, f_tel, f_cidade, f_uf, now()
  FROM _apply_canonical
  WHERE f_cnpj IS NOT NULL OR f_nome IS NOT NULL
  ORDER BY f_cnpj, f_nome, row_index
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_fornecedores.nome),
    telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_fornecedores.telefone),
    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
    endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_fornecedores.endereco_uf),
    atualizado_em   = now();

  -- 6. Upsert dim_inventory
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (p_sku, p_nome)
    v_client_id, p_sku, p_nome, now()
  FROM _apply_canonical
  WHERE p_sku IS NOT NULL OR p_nome IS NOT NULL
  ORDER BY p_sku, p_nome, row_index
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome       = COALESCE(EXCLUDED.nome, analytics_v2.dim_inventory.nome),
    updated_at = now();

  -- 7. Ensure dim_datas rows
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    data_date,
    EXTRACT(year    FROM data_date)::int,
    EXTRACT(month   FROM data_date)::int,
    EXTRACT(day     FROM data_date)::int,
    EXTRACT(isodow  FROM data_date)::int,
    EXTRACT(week    FROM data_date)::int,
    CASE WHEN EXTRACT(month FROM data_date) <= 6 THEN 1 ELSE 2 END,
    'Q' || EXTRACT(quarter FROM data_date)::text
  FROM _apply_canonical
  WHERE data_date IS NOT NULL
  ON CONFLICT (data) DO NOTHING;

  -- 8. Upsert fato_transacoes with cascading tipo_transacao classification
  --
  --   transacao_id = md5(client_id || source_id || documento || data || sku || row_index)
  --     - idempotent on re-runs
  --     - tolerates duplicate documento across files
  --     - row_index disambiguates rows that share everything else
  --
  --   tipo_transacao cascade:
  --     1. explicit mapping value
  --     2. cpf_cnpj match against client cpf_cnpj
  --        - fornecedor_cnpj == client.cpf_cnpj → 'venda'
  --        - cliente_cpf_cnpj == client.cpf_cnpj → 'compra'
  --     3. dimensional presence
  --        - dim_clientes hit → 'venda'
  --        - dim_fornecedores hit → 'compra'
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, customer_id, fornecedor_id,
     produto_id, documento, quantidade, valor_unitario, valor, status,
     tipo_transacao, tipo_lancamento, categoria, subcategoria)
  SELECT
    md5(
      v_client_id::text || ':' || v_source_id::text || ':' ||
      COALESCE(a.documento, '') || ':' ||
      COALESCE(a.data_comp, '') || ':' ||
      COALESCE(a.p_sku, '')    || ':' ||
      a.row_index::text
    ),
    v_client_id,
    dd.data_id,
    dc.customer_id,
    df.fornecedor_id,
    di.inventory_id,
    a.documento,
    a.quantidade,
    a.valor_un,
    a.valor,
    a.status,
    COALESCE(
      a.tipo_trans,
      CASE
        WHEN v_client_cpf_cnpj IS NOT NULL
         AND regexp_replace(COALESCE(a.f_cnpj, ''), '[^0-9]', '', 'g')
           = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'venda'
        WHEN v_client_cpf_cnpj IS NOT NULL
         AND regexp_replace(COALESCE(a.c_cpfcnpj, ''), '[^0-9]', '', 'g')
           = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'compra'
        WHEN dc.customer_id   IS NOT NULL THEN 'venda'
        WHEN df.fornecedor_id IS NOT NULL THEN 'compra'
        ELSE NULL
      END
    ),
    a.tipo_lanc,
    a.categoria,
    a.subcat
  FROM _apply_canonical a
  LEFT JOIN analytics_v2.dim_datas        dd ON dd.data      = a.data_date
  LEFT JOIN analytics_v2.dim_clientes     dc ON dc.client_id = v_client_id AND dc.cpf_cnpj = a.c_cpfcnpj
  LEFT JOIN analytics_v2.dim_fornecedores df ON df.client_id = v_client_id AND df.cnpj     = a.f_cnpj
  LEFT JOIN analytics_v2.dim_inventory    di ON di.client_id = v_client_id AND di.sku      = a.p_sku
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    customer_id         = EXCLUDED.customer_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status,
    tipo_transacao      = COALESCE(EXCLUDED.tipo_transacao,  analytics_v2.fato_transacoes.tipo_transacao),
    tipo_lancamento     = COALESCE(EXCLUDED.tipo_lancamento, analytics_v2.fato_transacoes.tipo_lancamento),
    categoria           = COALESCE(EXCLUDED.categoria,       analytics_v2.fato_transacoes.categoria),
    subcategoria        = COALESCE(EXCLUDED.subcategoria,    analytics_v2.fato_transacoes.subcategoria);

  -- 9. Advance watermark (only if source defines one — i.e. BigQuery)
  IF v_watermark_canonical IS NOT NULL THEN
    SELECT MAX(canonical->>v_watermark_canonical) INTO v_new_watermark
      FROM _apply_canonical;

    IF v_new_watermark IS NOT NULL THEN
      UPDATE public.client_data_sources
         SET last_watermark_value = v_new_watermark,
             sync_status          = 'synced',
             last_synced_at       = now(),
             updated_at           = now()
       WHERE id = v_source_id;
    ELSE
      UPDATE public.client_data_sources
         SET sync_status    = 'synced',
             last_synced_at = now(),
             updated_at     = now()
       WHERE id = v_source_id;
    END IF;
  ELSE
    UPDATE public.client_data_sources
       SET sync_status    = 'synced',
           last_synced_at = now(),
           updated_at     = now()
     WHERE id = v_source_id;
  END IF;

  -- 10. Clean staging + mark job complete
  DELETE FROM analytics_v2.ingest_staging WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs
     SET status           = 'completed',
         completed_at     = now(),
         rows_inserted    = v_row_count,
         progress_pct     = 100,
         duration_seconds = EXTRACT(epoch FROM (clock_timestamp() - v_start_time)),
         output           = jsonb_build_object(
                              'rows_inserted', v_row_count,
                              'new_watermark', v_new_watermark
                            ),
         updated_at       = now()
   WHERE job_id = p_job_id;

  -- 11. Enqueue refresh_dashboards job (debounce: skip if one is already pending for this client)
  --     Race-safe: unique partial index uq_reg_jobs_refresh_pending prevents duplicates
  --     even under concurrent apply_staging calls for the same client.
  INSERT INTO analytics_v2.reg_jobs (job_type, client_id, status, input_params)
  VALUES (
    'refresh_dashboards',
    v_client_id,
    'pending',
    jsonb_build_object('source_job_id', p_job_id)
  )
  ON CONFLICT (client_id, job_type)
  WHERE job_type = 'refresh_dashboards' AND status = 'pending'
  DO NOTHING;

  RETURN jsonb_build_object(
    'success',          true,
    'job_id',           p_job_id,
    'rows_inserted',    v_row_count,
    'new_watermark',    v_new_watermark,
    'duration_seconds', EXTRACT(epoch FROM (clock_timestamp() - v_start_time))
  );

EXCEPTION WHEN OTHERS THEN
  DELETE FROM analytics_v2.ingest_staging WHERE job_id = p_job_id;
  UPDATE analytics_v2.reg_jobs
     SET status        = 'failed',
         completed_at  = now(),
         error_message = SQLERRM,
         updated_at    = now()
   WHERE job_id = p_job_id;

  UPDATE public.client_data_sources
     SET sync_status   = 'sync_failed',
         error_message = SQLERRM,
         updated_at    = now()
   WHERE id = v_source_id;

  RETURN jsonb_build_object('success', false, 'job_id', p_job_id, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION "analytics_v2"."apply_staging_to_facts"("p_job_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."apply_staging_to_facts"("p_job_id" "uuid") IS 'Canonical UPSERT for ingested raw rows. Reads analytics_v2.ingest_staging rows for the given job, renames source columns to canonical names via client_data_sources.column_mapping, upserts dim_*, then fato_transacoes with cascading tipo_transacao classification. Used by both CSV/xlsx and BigQuery pipelines.';



CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_agregados"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_start timestamptz := clock_timestamp();
BEGIN
  RAISE NOTICE '[atualizar_agregados] client=%: updating dim aggregates', p_client_id;

  -- Dim updates run outside any exception handler so failures propagate correctly.
  PERFORM analytics_v2.atualizar_dim_clientes(p_client_id);
  PERFORM analytics_v2.atualizar_dim_fornecedores(p_client_id);
  PERFORM analytics_v2.atualizar_dim_inventory(p_client_id);

  RAISE NOTICE '[atualizar_agregados] client=%: dims done in %.1fs, refreshing MVs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);

  -- MV refresh in its own sub-block so a failure here does NOT roll back
  -- the dim updates above (which were already committed to the savepoint).
  BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[atualizar_agregados] client=%: MV refresh failed (non-fatal, dims already saved): %',
      p_client_id, SQLERRM;
  END;

  RAISE NOTICE '[atualizar_agregados] client=%: all done in %.1fs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);
END;
$$;


ALTER FUNCTION "analytics_v2"."atualizar_agregados"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_clientes"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
BEGIN
  WITH agg AS (
    SELECT ft.customer_id,
      COUNT(DISTINCT ft.transacao_id) AS total_pedidos,
      COALESCE(SUM(ft.valor), 0) AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END AS ticket_medio,
      COALESCE(SUM(ft.quantidade), 0) AS quantidade_total,
      MIN(dd.data) AS data_primeira_compra,
      MAX(dd.data) AS data_ultima_compra,
      (CURRENT_DATE - MAX(dd.data)) AS dias_recencia,
      CASE WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric / GREATEST(1,
               EXTRACT(YEAR FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
               EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia    DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal ASC  NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total     ASC  NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_clientes dc SET
    total_pedidos = s.total_pedidos, receita_total = s.receita_total,
    ticket_medio = s.ticket_medio, quantidade_total = s.quantidade_total,
    data_primeira_compra = s.data_primeira_compra, data_ultima_compra = s.data_ultima_compra,
    dias_recencia = s.dias_recencia, frequencia_mensal = s.frequencia_mensal,
    pontuacao_cluster = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster = CASE WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                         WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                         ELSE 'Baixo' END,
    atualizado_em = clock_timestamp()
  FROM scored s
  WHERE dc.client_id = p_client_id AND dc.customer_id = s.customer_id;
  RAISE NOTICE '[atualizar_dim_clientes] client=%: done', p_client_id;
END; $$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_clientes"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_fornecedores"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
BEGIN
  WITH agg AS (
    SELECT
      ft.fornecedor_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos_recebidos,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS ticket_medio,
      COUNT(DISTINCT ft.produto_id)                                       AS total_produtos_fornecidos,
      MIN(dd.data)                                                        AS data_primeira_transacao,
      MAX(dd.data)                                                        AS data_ultima_transacao,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id     = p_client_id
      AND ft.fornecedor_id IS NOT NULL
      AND ft.tipo_transacao = 'compra'
    GROUP BY ft.fornecedor_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_fornecedores df
  SET
    total_pedidos_recebidos   = s.total_pedidos_recebidos,
    receita_total             = s.receita_total,
    ticket_medio              = s.ticket_medio,
    total_produtos_fornecidos = s.total_produtos_fornecidos,
    data_primeira_transacao   = s.data_primeira_transacao,
    data_ultima_transacao     = s.data_ultima_transacao,
    dias_recencia             = s.dias_recencia,
    frequencia_mensal         = s.frequencia_mensal,
    pontuacao_cluster         = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster             = CASE
                                  WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                  WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                  ELSE 'Baixo'
                                END,
    atualizado_em             = clock_timestamp()
  FROM scored s
  WHERE df.client_id     = p_client_id
    AND df.fornecedor_id = s.fornecedor_id;

  RAISE NOTICE '[atualizar_dim_fornecedores] client=%: done', p_client_id;
END;
$$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_fornecedores"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_inventory"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
BEGIN
  WITH agg AS (
    SELECT
      ft.produto_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos,
      COALESCE(SUM(ft.quantidade), 0)                                     AS quantidade_total_vendida,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COALESCE(SUM(ft.quantidade), 0) > 0
           THEN COALESCE(SUM(ft.valor), 0) / SUM(ft.quantidade)
           ELSE 0 END                                                     AS preco_medio,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.quantidade), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS quantidade_media_por_pedido,
      MAX(dd.data)                                                        AS data_ultima_venda,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.produto_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.produto_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_inventory di
  SET
    quantidade_total_vendida    = s.quantidade_total_vendida,
    receita_total               = s.receita_total,
    preco_medio                 = s.preco_medio,
    total_pedidos               = s.total_pedidos,
    quantidade_media_por_pedido = s.quantidade_media_por_pedido,
    data_ultima_venda           = s.data_ultima_venda,
    dias_recencia               = s.dias_recencia,
    frequencia_mensal           = s.frequencia_mensal,
    pontuacao_cluster           = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster               = CASE
                                    WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                    WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                    ELSE 'Baixo'
                                  END,
    updated_at                  = clock_timestamp()
  FROM scored s
  WHERE di.client_id   = p_client_id
    AND di.inventory_id = s.produto_id;

  RAISE NOTICE '[atualizar_dim_inventory] client=%: done', p_client_id;
END;
$$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_inventory"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."batch_sync_polp"("p_client_id" "uuid", "p_batch_size" integer DEFAULT 500) RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  v_last_id    bigint := 0;
  v_batch_synced int;
  v_synced     int := 0;
BEGIN
  -- Find last synced polp_transaction_id
  SELECT COALESCE(MAX(NULLIF(regexp_replace(transacao_id, 'polp_', ''), '')::bigint), 0)
  INTO   v_last_id
  FROM   analytics_v2.fato_transacoes
  WHERE  client_id = p_client_id
    AND  transacao_id LIKE 'polp_%';

  LOOP
    INSERT INTO analytics_v2.fato_transacoes (
        transacao_id,
        client_id,
        data_competencia_id,
        customer_id,
        fornecedor_id,
        produto_id,
        documento,
        quantidade,
        valor_unitario,
        valor,
        status,
        tipo_transacao,
        tipo_lancamento,
        entry_type,
        categoria,
        subcategoria,
        updated_at
    )
    SELECT
        'polp_' || pt.polp_transaction_id::text,
        pt.client_id,
        dd.data_id,
        NULL::bigint,
        NULL::bigint,
        NULL::bigint,
        'polp_' || pt.polp_transaction_id::text,
        1,
        ABS(pt.amount),
        ABS(pt.amount),
        COALESCE(pt.status, 'confirmed'),
        -- tipo_transacao: label from Polp type
        CASE
          WHEN pt.type = 'CREDIT' THEN 'venda'
          WHEN pt.type = 'DEBIT'  THEN 'compra'
          ELSE NULL
        END,
        'bancario',
        -- entry_type: banking direction
        CASE
          WHEN pt.type = 'CREDIT' THEN 'revenue'
          WHEN pt.type = 'DEBIT'  THEN 'expense'
          ELSE 'banking'
        END,
        pt.category->>'name',
        pt.category->>'description',
        NOW()
    FROM public.polp_transactions pt
    LEFT JOIN analytics_v2.dim_datas dd
        ON dd.data_id = to_char(pt.date, 'YYYYMMDD')::bigint
    WHERE pt.client_id = p_client_id
      AND pt.status IS DISTINCT FROM 'deleted'
      AND pt.polp_transaction_id > v_last_id
    ORDER BY pt.polp_transaction_id
    LIMIT p_batch_size
    ON CONFLICT (transacao_id, client_id) DO UPDATE SET
        valor          = EXCLUDED.valor,
        valor_unitario = EXCLUDED.valor_unitario,
        status         = EXCLUDED.status,
        tipo_transacao = COALESCE(analytics_v2.fato_transacoes.tipo_transacao, EXCLUDED.tipo_transacao),
        entry_type     = COALESCE(analytics_v2.fato_transacoes.entry_type,     EXCLUDED.entry_type),
        categoria      = COALESCE(analytics_v2.fato_transacoes.categoria,      EXCLUDED.categoria),
        subcategoria   = COALESCE(analytics_v2.fato_transacoes.subcategoria,   EXCLUDED.subcategoria),
        updated_at     = NOW();

    GET DIAGNOSTICS v_batch_synced = ROW_COUNT;
    v_synced := v_synced + v_batch_synced;

    EXIT WHEN v_batch_synced < p_batch_size;

    SELECT MAX(NULLIF(regexp_replace(transacao_id, 'polp_', ''), '')::bigint)
    INTO   v_last_id
    FROM   analytics_v2.fato_transacoes
    WHERE  client_id = p_client_id
      AND  transacao_id LIKE 'polp_%';
  END LOOP;

  RETURN v_synced;
END;
$$;


ALTER FUNCTION "analytics_v2"."batch_sync_polp"("p_client_id" "uuid", "p_batch_size" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."batch_sync_polp"("p_client_id" "uuid", "p_batch_size" integer) IS 'Syncs polp_transactions -> fato_transacoes in batches. entry_type: CREDIT→revenue, DEBIT→expense, else banking. tipo_lancamento always bancario for Polp rows.';



CREATE OR REPLACE FUNCTION "analytics_v2"."enqueue_incremental_syncs"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_count integer := 0;
  v_row   record;
BEGIN
  FOR v_row IN
    SELECT cds.client_id,
           cds.credential_id::bigint AS credential_id
    FROM   public.client_data_sources cds
    WHERE  cds.sync_status IN ('synced', 'mapping_confirmed')
      AND (
        cds.last_synced_at IS NULL
        OR cds.last_synced_at < now() - interval '12 hours'
      )
      -- No in-flight job for this client
      AND NOT EXISTS (
        SELECT 1
        FROM   analytics_v2.reg_jobs rj
        WHERE  rj.client_id = cds.client_id
          AND  rj.job_type  = 'bigquery_sync'
          AND  rj.status    IN ('pending', 'running')
      )
      -- Credential must still exist and be active
      AND EXISTS (
        SELECT 1
        FROM   public.credencial_servico_externo cse
        WHERE  cse.id     = cds.credential_id
          AND  cse.ativo  = true
      )
  LOOP
    INSERT INTO analytics_v2.reg_jobs
      (client_id, job_type, status, sync_mode, input_params)
    VALUES (
      v_row.client_id,
      'bigquery_sync',
      'pending',
      'incremental',
      jsonb_build_object(
        'credential_id',   v_row.credential_id,
        'force_full_sync', false
      )
    );
    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END;
$$;


ALTER FUNCTION "analytics_v2"."enqueue_incremental_syncs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."enqueue_polp_sync"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_cid uuid;
BEGIN
  FOR v_cid IN
    SELECT DISTINCT client_id
    FROM public.polp_integrations
    WHERE status != 'DELETED'
  LOOP
    PERFORM analytics_v2.sync_polp_transactions(v_cid);
  END LOOP;
END;
$$;


ALTER FUNCTION "analytics_v2"."enqueue_polp_sync"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."etl_resource_to_doc_type"("p_resource_type" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  SELECT CASE lower(trim(p_resource_type))
    WHEN 'orders'           THEN 'historico_pedidos'
    WHEN 'pedidos'          THEN 'historico_pedidos'
    WHEN 'products'         THEN 'catalogo_produtos'
    WHEN 'produtos'         THEN 'catalogo_produtos'
    WHEN 'inventory'        THEN 'controle_inventario'
    WHEN 'estoque'          THEN 'controle_inventario'
    WHEN 'customers'        THEN 'ficha_cliente'
    WHEN 'clientes'         THEN 'ficha_cliente'
    WHEN 'fornecedores'     THEN 'cadastro_fornecedores'
    WHEN 'suppliers'        THEN 'cadastro_fornecedores'
    WHEN 'financial'        THEN 'dre_mensal'
    WHEN 'dre'              THEN 'dre_mensal'
    WHEN 'fluxo_caixa'      THEN 'fluxo_caixa_diario'
    WHEN 'cashflow'         THEN 'fluxo_caixa_diario'
    ELSE NULL
  END;
$$;


ALTER FUNCTION "analytics_v2"."etl_resource_to_doc_type"("p_resource_type" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_admin_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("aprovacoes_pendentes" bigint, "lead_time_aprovacao_h" numeric, "sla_aprovacao_perc" numeric, "documentos_pendentes" bigint, "cobertura_rotinas_perc" numeric, "frescor_dados_h" numeric, "audit_coverage_perc" numeric, "period" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
BEGIN
  RETURN QUERY
  WITH approvals AS (
    SELECT
      COUNT(*) FILTER (WHERE status = 'pending')                                           AS pendentes,
      ROUND(AVG(EXTRACT(epoch FROM (decided_at - created_at)) / 3600)
            FILTER (WHERE decided_at IS NOT NULL)::numeric, 1)                             AS lead_time_h,
      ROUND(COUNT(*) FILTER (WHERE decided_at <= expires_at AND decided_at IS NOT NULL)
            ::numeric / NULLIF(COUNT(*) FILTER (WHERE decided_at IS NOT NULL), 0) * 100, 1) AS sla_perc
    FROM public.approval_requests
    WHERE client_id = v_client_id
  ),
  docs AS (
    SELECT COUNT(*) AS pendentes
    FROM public.client_knowledge_documents
    WHERE client_id = v_client_id AND status != 'complete'
  ),
  freshness AS (
    SELECT ROUND(EXTRACT(epoch FROM (now() - MAX(last_synced_at))) / 3600, 1) AS h
    FROM public.client_data_sources
    WHERE client_id = v_client_id
  )
  SELECT
    approvals.pendentes,
    approvals.lead_time_h,
    approvals.sla_perc,
    docs.pendentes,
    NULL::numeric, -- cobertura_rotinas_perc
    freshness.h,
    NULL::numeric, -- audit_coverage_perc
    p_period
  FROM approvals, docs, freshness;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_admin_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") RETURNS TABLE("ano" integer, "receita" numeric, "total_pedidos" bigint, "clientes_unicos" bigint, "clientes_novos" bigint, "ticket_medio" numeric, "fornecedores_ativos" bigint, "skus_ativos" bigint, "quantidade_vendida" numeric, "is_partial" boolean, "yoy_receita_pct" numeric, "receita_anualizada" numeric)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
WITH years AS (
  SELECT EXTRACT(YEAR FROM dd.data)::integer AS ano,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS receita,
    COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS total_pedidos,
    COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS clientes_unicos,
    COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') AS fornecedores_ativos,
    COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS skus_ativos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS quantidade_vendida,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY EXTRACT(YEAR FROM dd.data)::integer
),
first_purchases AS (
  SELECT ft.customer_id, EXTRACT(YEAR FROM MIN(dd.data))::integer AS first_year
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_ano AS (SELECT first_year AS ano, COUNT(*)::bigint AS clientes_novos FROM first_purchases GROUP BY first_year),
current_year_months AS (
  SELECT COUNT(DISTINCT date_trunc('month', dd.data)) AS months_with_data
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
    AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE)
),
with_yoy AS (
  SELECT y.ano, ROUND(y.receita, 2) AS receita, y.total_pedidos, y.clientes_unicos,
    COALESCE(n.clientes_novos, 0) AS clientes_novos, ROUND(y.ticket_medio, 2) AS ticket_medio,
    y.fornecedores_ativos, y.skus_ativos, y.quantidade_vendida,
    (y.ano = EXTRACT(YEAR FROM CURRENT_DATE)::integer) AS is_partial,
    CASE WHEN LAG(y.receita) OVER (ORDER BY y.ano) > 0
         THEN ROUND((y.receita - LAG(y.receita) OVER (ORDER BY y.ano)) / LAG(y.receita) OVER (ORDER BY y.ano) * 100, 1)
         ELSE NULL END AS yoy_receita_pct,
    y.receita AS raw_receita
  FROM years y LEFT JOIN novos_por_ano n ON n.ano = y.ano
)
SELECT w.ano, w.receita, w.total_pedidos, w.clientes_unicos, w.clientes_novos,
  w.ticket_medio, w.fornecedores_ativos, w.skus_ativos, w.quantidade_vendida, w.is_partial,
  w.yoy_receita_pct,
  CASE WHEN w.is_partial AND m.months_with_data > 0
       THEN ROUND(w.raw_receita / m.months_with_data * 12, 2) ELSE NULL END AS receita_anualizada
FROM with_yoy w CROSS JOIN current_year_months m ORDER BY w.ano DESC;
$$;


ALTER FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_commercial_indicators"("p_period" "text") RETURNS TABLE("total_pedidos" bigint, "receita" numeric, "ticket_medio" numeric, "clientes_unicos" bigint, "clientes_novos" bigint, "clientes_recorrentes" bigint, "recencia_media_dias" numeric, "frequencia_media_mensal" numeric, "churn_60d_perc" numeric, "crescimento_receita_pct" numeric, "n1" numeric, "n2" numeric, "n3" numeric, "n4" numeric, "n5" numeric, "n6" numeric, "periodo" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date; v_prev_start date; v_prev_end date;
  v_pedidos bigint := 0; v_receita numeric := 0; v_prev_rev numeric := 0;
  v_clientes_unicos bigint := 0; v_clientes_novos bigint := 0;
  v_recencia numeric := 0; v_frequencia numeric := 0;
  v_churn numeric := 0;
  v_m1 numeric := 0; v_m2 numeric := 0; v_m3 numeric := 0;
  v_m4 numeric := 0; v_m5 numeric := 0; v_m6 numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO v_start, v_prev_start, v_prev_end
  FROM analytics_v2._period_range(p_period) r;

  SELECT
    COUNT(DISTINCT ft.transacao_id),
    COALESCE(SUM(ft.valor), 0),
    COUNT(DISTINCT ft.customer_id)
  INTO v_pedidos, v_receita, v_clientes_unicos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND ft.customer_id IS NOT NULL
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  SELECT COUNT(DISTINCT ft.customer_id)
  INTO v_clientes_novos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND ft.customer_id IS NOT NULL
    AND dd.data >= v_start AND dd.data < CURRENT_DATE
    AND NOT EXISTS (
      SELECT 1 FROM analytics_v2.fato_transacoes ft2
      JOIN analytics_v2.dim_datas dd2 ON ft2.data_competencia_id = dd2.data_id
      WHERE ft2.client_id = v_client_id
        AND ft2.tipo_transacao = 'venda'
        AND ft2.customer_id = ft.customer_id
        AND dd2.data < v_start
    );

  SELECT COALESCE(AVG(CURRENT_DATE - last_date), 0)
  INTO v_recencia
  FROM (
    SELECT ft.customer_id, MAX(dd.data) AS last_date
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
    GROUP BY ft.customer_id
  ) sub;

  -- FIX: (date - date) retorna integer em PG — cast para numeric direto, sem DATE_PART
  v_frequencia := CASE WHEN v_clientes_unicos > 0
    THEN ROUND(v_pedidos::numeric / v_clientes_unicos
         / GREATEST((CURRENT_DATE - v_start)::numeric / 30.0, 1), 2)
    ELSE 0 END;

  WITH active_prev AS (
    SELECT DISTINCT ft.customer_id
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
      AND dd.data >= (CURRENT_DATE - INTERVAL '120 days')::date
      AND dd.data <  (CURRENT_DATE - INTERVAL '60 days')::date
  ),
  active_recent AS (
    SELECT DISTINCT ft.customer_id
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
      AND dd.data >= (CURRENT_DATE - INTERVAL '60 days')::date
      AND dd.data < CURRENT_DATE
  )
  SELECT ROUND(
    100.0 * COUNT(p.customer_id) FILTER (WHERE r.customer_id IS NULL)
    / NULLIF(COUNT(p.customer_id), 0), 1)
  INTO v_churn
  FROM active_prev p LEFT JOIN active_recent r USING (customer_id);

  SELECT COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  SELECT
    COALESCE(SUM(CASE WHEN dd.data >= DATE_TRUNC('month', CURRENT_DATE)::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date
                       AND dd.data <   DATE_TRUNC('month', CURRENT_DATE)::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '4 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '4 months')::date THEN ft.valor END), 0)
  INTO v_m1, v_m2, v_m3, v_m4, v_m5, v_m6
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months')::date
    AND dd.data < CURRENT_DATE;

  RETURN QUERY SELECT
    v_pedidos,
    ROUND(v_receita, 2),
    CASE WHEN v_pedidos > 0 THEN ROUND(v_receita / v_pedidos, 2) ELSE 0 END,
    v_clientes_unicos,
    v_clientes_novos,
    v_clientes_unicos - v_clientes_novos,
    ROUND(v_recencia, 0),
    v_frequencia,
    v_churn,
    CASE WHEN v_prev_rev > 0 THEN ROUND((v_receita - v_prev_rev) / v_prev_rev * 100, 1) ELSE NULL END,
    v_m1, v_m2, v_m3, v_m4, v_m5, v_m6,
    p_period;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_commercial_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_commercial_revenue_by_channel"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("channel" "text", "receita" numeric, "pedidos" bigint, "share_perc" numeric, "period" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start     date;
BEGIN
  SELECT r.start_date INTO v_start FROM analytics_v2._period_range(p_period) r;

  RETURN QUERY
  WITH by_status AS (
    SELECT
      COALESCE(ft.status, 'sem_status')   AS channel,
      COALESCE(SUM(ft.valor), 0)          AS receita,
      COUNT(DISTINCT ft.transacao_id)     AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.status
  ),
  total AS (SELECT NULLIF(SUM(receita), 0) AS total FROM by_status)
  SELECT
    b.channel,
    b.receita,
    b.pedidos,
    ROUND(b.receita / t.total * 100, 1),
    p_period
  FROM by_status b, total t
  ORDER BY b.receita DESC;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_commercial_revenue_by_channel"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_commercial_top_clients"("p_period" "text", "p_limit" integer DEFAULT 10) RETURNS TABLE("customer_id" bigint, "nome" "text", "receita" numeric, "pedidos" bigint, "participacao_pct" numeric, "periodo" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date;
BEGIN
  SELECT r.start_date INTO v_start FROM analytics_v2._period_range(p_period) r;
  RETURN QUERY
  WITH by_customer AS (
    SELECT ft.customer_id, COALESCE(SUM(ft.valor), 0) AS receita,
      COUNT(DISTINCT ft.transacao_id) AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND dd.data >= v_start AND dd.data < CURRENT_DATE
      AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id ORDER BY receita DESC LIMIT p_limit
  ),
  total AS (SELECT NULLIF(SUM(receita), 0) AS total FROM by_customer)
  SELECT b.customer_id, dc.nome, b.receita, b.pedidos,
    ROUND(b.receita / t.total * 100, 1), p_period
  FROM by_customer b
  JOIN analytics_v2.dim_clientes dc ON dc.customer_id = b.customer_id AND dc.client_id = v_client_id
  CROSS JOIN total t ORDER BY b.receita DESC;
END; $$;


ALTER FUNCTION "analytics_v2"."get_commercial_top_clients"("p_period" "text", "p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") RETURNS TABLE("dimension" "text", "kpi" "text", "label" "text", "unit" "text", "current_value" numeric, "prev_month_value" numeric, "avg_6m" numeric, "mom_pct" numeric, "vs_6m_avg_pct" numeric, "streak_months" integer)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
WITH
all_monthly AS (
  SELECT date_trunc('month', dd.data)::date AS mes,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS receita,
    (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS total_pedidos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS quantidade,
    (COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS clientes_unicos,
    (COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric AS fornecedores_ativos,
    (COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS skus_ativos,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS frequencia_media,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_cliente,
    CASE WHEN COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_sku,
    CASE WHEN COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
              / COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra')
         ELSE 0 END AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY date_trunc('month', dd.data)::date
),
monthly_buyers AS (
  SELECT DISTINCT date_trunc('month', dd.data)::date AS mes, ft.customer_id
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
),
first_purchases AS (
  SELECT ft.customer_id, date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_mes AS (SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos FROM first_purchases GROUP BY first_month),
recorrentes_por_mes AS (
  SELECT a.mes, COUNT(*)::numeric AS clientes_recorrentes FROM monthly_buyers a
  JOIN monthly_buyers b ON b.customer_id = a.customer_id AND b.mes = (a.mes - INTERVAL '1 month')::date
  GROUP BY a.mes
),
monthly_rev_per_entity AS (
  SELECT date_trunc('month', dd.data)::date AS mes, ft.customer_id, ft.produto_id, ft.fornecedor_id, ft.valor, ft.tipo_transacao
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
),
rev_por_cliente AS (SELECT mes, customer_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE customer_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, customer_id),
rev_por_produto AS (SELECT mes, produto_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE produto_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, produto_id),
rev_por_fornecedor AS (SELECT mes, fornecedor_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE fornecedor_id IS NOT NULL AND tipo_transacao = 'compra' GROUP BY mes, fornecedor_id),
concentracao_top3_clientes AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_cliente) x GROUP BY mes
),
concentracao_top3_produtos AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_produto) x GROUP BY mes
),
concentracao_top3_fornecedores AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_fornecedor) x GROUP BY mes
),
top1_clean AS (SELECT mes, ROUND(MAX(rev) / NULLIF(SUM(rev), 0) * 100, 1) AS concentracao_top1_perc FROM rev_por_fornecedor GROUP BY mes),
enriched AS (
  SELECT am.mes, am.receita, am.ticket_medio, am.total_pedidos, am.quantidade,
    am.clientes_unicos, am.frequencia_media, am.receita_por_cliente,
    am.skus_ativos, am.receita_por_sku, am.fornecedores_ativos, am.receita_por_fornecedor,
    COALESCE(np.clientes_novos, 0) AS clientes_novos,
    COALESCE(rp.clientes_recorrentes, 0) AS clientes_recorrentes,
    CASE WHEN COALESCE(am_prev.clientes_unicos, 0) > 0
         THEN ROUND(COALESCE(rp.clientes_recorrentes, 0) / am_prev.clientes_unicos * 100, 1) ELSE 0 END AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc, 0) AS concentracao_top1_fornecedor_perc,
    COALESCE(c3c.perc, 0) AS concentracao_top3_clientes_perc,
    COALESCE(c3p.perc, 0) AS concentracao_top3_produtos_perc,
    COALESCE(c3s.perc, 0) AS concentracao_top3_fornecedores_perc
  FROM all_monthly am
  LEFT JOIN all_monthly am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes np ON np.mes = am.mes
  LEFT JOIN recorrentes_por_mes rp ON rp.mes = am.mes
  LEFT JOIN top1_clean t1 ON t1.mes = am.mes
  LEFT JOIN concentracao_top3_clientes c3c ON c3c.mes = am.mes
  LEFT JOIN concentracao_top3_produtos c3p ON c3p.mes = am.mes
  LEFT JOIN concentracao_top3_fornecedores c3s ON c3s.mes = am.mes
),
ref_month AS (
  SELECT COALESCE(
    (SELECT mes FROM enriched WHERE mes = date_trunc('month', CURRENT_DATE)::date LIMIT 1),
    (SELECT mes FROM enriched WHERE mes < date_trunc('month', CURRENT_DATE)::date ORDER BY mes DESC LIMIT 1)
  ) AS mes
),
complete_months AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes < r.mes),
current_month AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes = r.mes),
long_complete AS (
  SELECT mes, 'receita_liquida' AS kpi, receita AS val FROM complete_months UNION ALL
  SELECT mes, 'ticket_medio', ticket_medio FROM complete_months UNION ALL
  SELECT mes, 'total_pedidos', total_pedidos FROM complete_months UNION ALL
  SELECT mes, 'quantidade_vendida', quantidade FROM complete_months UNION ALL
  SELECT mes, 'clientes_unicos', clientes_unicos FROM complete_months UNION ALL
  SELECT mes, 'clientes_novos', clientes_novos FROM complete_months UNION ALL
  SELECT mes, 'clientes_recorrentes', clientes_recorrentes FROM complete_months UNION ALL
  SELECT mes, 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM complete_months UNION ALL
  SELECT mes, 'receita_por_cliente', receita_por_cliente FROM complete_months UNION ALL
  SELECT mes, 'frequencia_media', frequencia_media FROM complete_months UNION ALL
  SELECT mes, 'skus_ativos', skus_ativos FROM complete_months UNION ALL
  SELECT mes, 'receita_por_sku', receita_por_sku FROM complete_months UNION ALL
  SELECT mes, 'fornecedores_ativos', fornecedores_ativos FROM complete_months UNION ALL
  SELECT mes, 'receita_por_fornecedor', receita_por_fornecedor FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM complete_months
),
long_current AS (
  SELECT 'receita_liquida' AS kpi, receita AS val FROM current_month UNION ALL
  SELECT 'ticket_medio', ticket_medio FROM current_month UNION ALL
  SELECT 'total_pedidos', total_pedidos FROM current_month UNION ALL
  SELECT 'quantidade_vendida', quantidade FROM current_month UNION ALL
  SELECT 'clientes_unicos', clientes_unicos FROM current_month UNION ALL
  SELECT 'clientes_novos', clientes_novos FROM current_month UNION ALL
  SELECT 'clientes_recorrentes', clientes_recorrentes FROM current_month UNION ALL
  SELECT 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM current_month UNION ALL
  SELECT 'receita_por_cliente', receita_por_cliente FROM current_month UNION ALL
  SELECT 'frequencia_media', frequencia_media FROM current_month UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM current_month UNION ALL
  SELECT 'receita_por_sku', receita_por_sku FROM current_month UNION ALL
  SELECT 'fornecedores_ativos', fornecedores_ativos FROM current_month UNION ALL
  SELECT 'receita_por_fornecedor', receita_por_fornecedor FROM current_month UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM current_month
),
ranked AS (SELECT kpi, mes, val, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
prev_month AS (SELECT kpi, val AS prev_val FROM ranked WHERE rn = 1),
avg_6m AS (SELECT kpi, ROUND(AVG(val), 2) AS avg_val FROM ranked WHERE rn BETWEEN 1 AND 6 GROUP BY kpi),
with_dir AS (SELECT kpi, mes, val, SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
latest_dir AS (SELECT kpi, dir FROM with_dir WHERE rn = 1 AND dir IS NOT NULL),
streak_tagged AS (
  SELECT w.kpi, l.dir AS streak_dir,
    SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END) OVER (PARTITION BY w.kpi ORDER BY w.rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS breaks
  FROM with_dir w JOIN latest_dir l USING (kpi) WHERE w.dir IS NOT NULL
),
streak AS (SELECT kpi, (MAX(streak_dir) * COUNT(*))::integer AS streak_months FROM streak_tagged WHERE breaks = 0 GROUP BY kpi),
assembled AS (
  SELECT lc.kpi, ROUND(lc.val, 2) AS current_value, ROUND(pm.prev_val, 2) AS prev_month_value,
    a6.avg_val AS avg_6m,
    CASE WHEN COALESCE(pm.prev_val, 0) <> 0 THEN ROUND((lc.val - pm.prev_val) / pm.prev_val * 100, 1) ELSE NULL END AS mom_pct,
    CASE WHEN COALESCE(a6.avg_val, 0) <> 0 THEN ROUND((lc.val - a6.avg_val) / a6.avg_val * 100, 1) ELSE NULL END AS vs_6m_avg_pct,
    COALESCE(st.streak_months, 0) AS streak_months
  FROM long_current lc LEFT JOIN prev_month pm USING (kpi) LEFT JOIN avg_6m a6 USING (kpi) LEFT JOIN streak st USING (kpi)
)
SELECT m.dimension, m.kpi, m.label, m.unit,
       a.current_value, a.prev_month_value, a.avg_6m, a.mom_pct, a.vs_6m_avg_pct, a.streak_months
FROM assembled a
JOIN (VALUES
  ('receita_liquida','finance','Receita Líquida','BRL'),('ticket_medio','finance','Ticket Médio','BRL'),
  ('total_pedidos','finance','Total de Pedidos','count'),('clientes_unicos','commercial','Clientes Únicos','count'),
  ('clientes_novos','commercial','Clientes Novos','count'),('clientes_recorrentes','commercial','Clientes Recorrentes','count'),
  ('taxa_recorrencia_perc','commercial','Taxa de Recorrência','%'),('receita_por_cliente','commercial','Receita por Cliente','BRL'),
  ('frequencia_media','commercial','Frequência Média de Compra','count'),('concentracao_top3_clientes_perc','commercial','Concentração Top 3 Clientes','%'),
  ('skus_ativos','inventory','SKUs Ativos no Mês','count'),('quantidade_vendida','inventory','Quantidade Vendida','count'),
  ('receita_por_sku','inventory','Receita por SKU Ativo','BRL'),('concentracao_top3_produtos_perc','inventory','Concentração Top 3 Produtos','%'),
  ('fornecedores_ativos','supply','Fornecedores Ativos','count'),('receita_por_fornecedor','supply','Receita por Fornecedor','BRL'),
  ('concentracao_top1_fornecedor_perc','supply','Concentração Top Fornecedor','%'),('concentracao_top3_fornecedores_perc','supply','Concentração Top 3 Fornecedores','%')
) AS m(kpi, dimension, label, unit) ON m.kpi = a.kpi
UNION ALL SELECT 'finance','receita_ytd','Receita Acumulada (YTD)','BRL',ROUND(COALESCE(SUM(ft.valor),0)::numeric,2),NULL,NULL,NULL,NULL,0
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
  AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE) AND dd.data < CURRENT_DATE
UNION ALL SELECT 'inventory','skus_total','Total de SKUs (catálogo)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_inventory WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_base_total','Total de Clientes (base)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_ativos_90d','Clientes Ativos (últimos 90 dias)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL AND dias_recencia <= 90
UNION ALL SELECT 'commercial','recencia_media_dias','Recência Média da Base (dias)','days',ROUND(AVG(dias_recencia)::numeric,0),NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL
ORDER BY dimension, kpi;
$$;


ALTER FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid", "p_period" "text") RETURNS TABLE("dimension" "text", "kpi" "text", "label" "text", "unit" "text", "current_value" numeric, "prev_month_value" numeric, "avg_6m" numeric, "mom_pct" numeric, "vs_6m_avg_pct" numeric, "streak_months" integer)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
WITH
all_monthly AS (
  SELECT date_trunc('month', dd.data)::date AS mes,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS receita,
    (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS total_pedidos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS quantidade,
    (COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS clientes_unicos,
    (COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric AS fornecedores_ativos,
    (COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS skus_ativos,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS frequencia_media,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_cliente,
    CASE WHEN COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_sku,
    CASE WHEN COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
              / COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra')
         ELSE 0 END AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY date_trunc('month', dd.data)::date
),
monthly_buyers AS (
  SELECT DISTINCT date_trunc('month', dd.data)::date AS mes, ft.customer_id
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
),
first_purchases AS (
  SELECT ft.customer_id, date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_mes AS (SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos FROM first_purchases GROUP BY first_month),
recorrentes_por_mes AS (
  SELECT a.mes, COUNT(*)::numeric AS clientes_recorrentes FROM monthly_buyers a
  JOIN monthly_buyers b ON b.customer_id = a.customer_id AND b.mes = (a.mes - INTERVAL '1 month')::date GROUP BY a.mes
),
monthly_rev_per_entity AS (
  SELECT date_trunc('month', dd.data)::date AS mes, ft.customer_id, ft.produto_id, ft.fornecedor_id, ft.valor, ft.tipo_transacao
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
),
rev_por_cliente AS (SELECT mes, customer_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE customer_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, customer_id),
rev_por_produto AS (SELECT mes, produto_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE produto_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, produto_id),
rev_por_fornecedor AS (SELECT mes, fornecedor_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE fornecedor_id IS NOT NULL AND tipo_transacao = 'compra' GROUP BY mes, fornecedor_id),
concentracao_top3_clientes AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_cliente) x GROUP BY mes),
concentracao_top3_produtos AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_produto) x GROUP BY mes),
concentracao_top3_fornecedores AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_fornecedor) x GROUP BY mes),
top1_clean AS (SELECT mes, ROUND(MAX(rev) / NULLIF(SUM(rev),0)*100,1) AS concentracao_top1_perc FROM rev_por_fornecedor GROUP BY mes),
enriched AS (
  SELECT am.mes, am.receita, am.ticket_medio, am.total_pedidos, am.quantidade,
    am.clientes_unicos, am.frequencia_media, am.receita_por_cliente,
    am.skus_ativos, am.receita_por_sku, am.fornecedores_ativos, am.receita_por_fornecedor,
    COALESCE(np.clientes_novos, 0) AS clientes_novos, COALESCE(rp.clientes_recorrentes, 0) AS clientes_recorrentes,
    CASE WHEN COALESCE(am_prev.clientes_unicos,0) > 0 THEN ROUND(COALESCE(rp.clientes_recorrentes,0)/am_prev.clientes_unicos*100,1) ELSE 0 END AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc,0) AS concentracao_top1_fornecedor_perc,
    COALESCE(c3c.perc,0) AS concentracao_top3_clientes_perc, COALESCE(c3p.perc,0) AS concentracao_top3_produtos_perc, COALESCE(c3s.perc,0) AS concentracao_top3_fornecedores_perc
  FROM all_monthly am
  LEFT JOIN all_monthly am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes np ON np.mes = am.mes LEFT JOIN recorrentes_por_mes rp ON rp.mes = am.mes
  LEFT JOIN top1_clean t1 ON t1.mes = am.mes LEFT JOIN concentracao_top3_clientes c3c ON c3c.mes = am.mes
  LEFT JOIN concentracao_top3_produtos c3p ON c3p.mes = am.mes LEFT JOIN concentracao_top3_fornecedores c3s ON c3s.mes = am.mes
),
ref_month AS (SELECT COALESCE((SELECT mes FROM enriched WHERE mes = date_trunc('month', CURRENT_DATE)::date LIMIT 1),(SELECT mes FROM enriched WHERE mes < date_trunc('month', CURRENT_DATE)::date ORDER BY mes DESC LIMIT 1)) AS mes),
period_months AS (SELECT CASE p_period WHEN '90d' THEN 3 WHEN '1y' THEN 12 ELSE 1 END AS n),
current_window AS (SELECT e.* FROM enriched e, ref_month r, period_months pm WHERE e.mes <= r.mes AND e.mes > (r.mes - (pm.n || ' months')::interval)::date),
prev_window AS (SELECT e.* FROM enriched e, ref_month r, period_months pm WHERE e.mes <= (r.mes - (pm.n || ' months')::interval)::date AND e.mes > (r.mes - (pm.n*2 || ' months')::interval)::date),
current_latest AS (SELECT * FROM current_window ORDER BY mes DESC LIMIT 1),
prev_latest AS (SELECT * FROM prev_window ORDER BY mes DESC LIMIT 1),
long_current AS (
  SELECT 'receita_liquida' AS kpi, SUM(receita) AS val FROM current_window UNION ALL SELECT 'total_pedidos', SUM(total_pedidos) FROM current_window UNION ALL
  SELECT 'quantidade_vendida', SUM(quantidade) FROM current_window UNION ALL SELECT 'clientes_novos', SUM(clientes_novos) FROM current_window UNION ALL
  SELECT 'clientes_recorrentes', SUM(clientes_recorrentes) FROM current_window UNION ALL SELECT 'clientes_unicos', clientes_unicos FROM current_latest UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM current_latest UNION ALL SELECT 'fornecedores_ativos', fornecedores_ativos FROM current_latest UNION ALL
  SELECT 'ticket_medio', CASE WHEN SUM(total_pedidos) > 0 THEN SUM(receita)/SUM(total_pedidos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'frequencia_media', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(total_pedidos)::numeric/MAX(clientes_unicos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_cliente', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(receita)/MAX(clientes_unicos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_sku', CASE WHEN MAX(skus_ativos) > 0 THEN SUM(receita)/MAX(skus_ativos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_fornecedor', CASE WHEN MAX(fornecedores_ativos) > 0 THEN SUM(receita_por_fornecedor * fornecedores_ativos)/MAX(fornecedores_ativos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'taxa_recorrencia_perc', AVG(taxa_recorrencia_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_clientes_perc', AVG(concentracao_top3_clientes_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_produtos_perc', AVG(concentracao_top3_produtos_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', AVG(concentracao_top1_fornecedor_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', AVG(concentracao_top3_fornecedores_perc) FROM current_window
),
long_prev AS (
  SELECT 'receita_liquida' AS kpi, SUM(receita) AS val FROM prev_window UNION ALL SELECT 'total_pedidos', SUM(total_pedidos) FROM prev_window UNION ALL
  SELECT 'quantidade_vendida', SUM(quantidade) FROM prev_window UNION ALL SELECT 'clientes_novos', SUM(clientes_novos) FROM prev_window UNION ALL
  SELECT 'clientes_recorrentes', SUM(clientes_recorrentes) FROM prev_window UNION ALL SELECT 'clientes_unicos', clientes_unicos FROM prev_latest UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM prev_latest UNION ALL SELECT 'fornecedores_ativos', fornecedores_ativos FROM prev_latest UNION ALL
  SELECT 'ticket_medio', CASE WHEN SUM(total_pedidos) > 0 THEN SUM(receita)/SUM(total_pedidos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'frequencia_media', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(total_pedidos)::numeric/MAX(clientes_unicos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_cliente', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(receita)/MAX(clientes_unicos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_sku', CASE WHEN MAX(skus_ativos) > 0 THEN SUM(receita)/MAX(skus_ativos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_fornecedor', CASE WHEN MAX(fornecedores_ativos) > 0 THEN SUM(receita_por_fornecedor * fornecedores_ativos)/MAX(fornecedores_ativos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'taxa_recorrencia_perc', AVG(taxa_recorrencia_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_clientes_perc', AVG(concentracao_top3_clientes_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_produtos_perc', AVG(concentracao_top3_produtos_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', AVG(concentracao_top1_fornecedor_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', AVG(concentracao_top3_fornecedores_perc) FROM prev_window
),
complete_months AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes < r.mes),
long_complete AS (
  SELECT mes, 'receita_liquida' AS kpi, receita AS val FROM complete_months UNION ALL SELECT mes, 'ticket_medio', ticket_medio FROM complete_months UNION ALL
  SELECT mes, 'total_pedidos', total_pedidos FROM complete_months UNION ALL SELECT mes, 'quantidade_vendida', quantidade FROM complete_months UNION ALL
  SELECT mes, 'clientes_unicos', clientes_unicos FROM complete_months UNION ALL SELECT mes, 'clientes_novos', clientes_novos FROM complete_months UNION ALL
  SELECT mes, 'clientes_recorrentes', clientes_recorrentes FROM complete_months UNION ALL SELECT mes, 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM complete_months UNION ALL
  SELECT mes, 'receita_por_cliente', receita_por_cliente FROM complete_months UNION ALL SELECT mes, 'frequencia_media', frequencia_media FROM complete_months UNION ALL
  SELECT mes, 'skus_ativos', skus_ativos FROM complete_months UNION ALL SELECT mes, 'receita_por_sku', receita_por_sku FROM complete_months UNION ALL
  SELECT mes, 'fornecedores_ativos', fornecedores_ativos FROM complete_months UNION ALL SELECT mes, 'receita_por_fornecedor', receita_por_fornecedor FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM complete_months
),
ranked AS (SELECT kpi, mes, val, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
avg_6m AS (SELECT kpi, ROUND(AVG(val),2) AS avg_val FROM ranked WHERE rn BETWEEN 1 AND 6 GROUP BY kpi),
with_dir AS (SELECT kpi, mes, val, SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
latest_dir AS (SELECT kpi, dir FROM with_dir WHERE rn = 1 AND dir IS NOT NULL),
streak_tagged AS (SELECT w.kpi, l.dir AS streak_dir, SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END) OVER (PARTITION BY w.kpi ORDER BY w.rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS breaks FROM with_dir w JOIN latest_dir l USING (kpi) WHERE w.dir IS NOT NULL),
streak AS (SELECT kpi, (MAX(streak_dir)*COUNT(*))::integer AS streak_months FROM streak_tagged WHERE breaks = 0 GROUP BY kpi),
assembled AS (
  SELECT lc.kpi, ROUND(lc.val,2) AS current_value, ROUND(lp.val,2) AS prev_month_value, a6.avg_val AS avg_6m,
    CASE WHEN COALESCE(lp.val,0) <> 0 THEN ROUND((lc.val-lp.val)/lp.val*100,1) ELSE NULL END AS mom_pct,
    CASE WHEN COALESCE(a6.avg_val,0) <> 0 THEN ROUND((lc.val-a6.avg_val)/a6.avg_val*100,1) ELSE NULL END AS vs_6m_avg_pct,
    COALESCE(st.streak_months,0) AS streak_months
  FROM long_current lc LEFT JOIN long_prev lp USING (kpi) LEFT JOIN avg_6m a6 USING (kpi) LEFT JOIN streak st USING (kpi)
)
SELECT m.dimension, m.kpi, m.label, m.unit, a.current_value, a.prev_month_value, a.avg_6m, a.mom_pct, a.vs_6m_avg_pct, a.streak_months
FROM assembled a
JOIN (VALUES
  ('receita_liquida','finance','Receita Líquida','BRL'),('ticket_medio','finance','Ticket Médio','BRL'),
  ('total_pedidos','finance','Total de Pedidos','count'),('clientes_unicos','commercial','Clientes Únicos','count'),
  ('clientes_novos','commercial','Clientes Novos','count'),('clientes_recorrentes','commercial','Clientes Recorrentes','count'),
  ('taxa_recorrencia_perc','commercial','Taxa de Recorrência','%'),('receita_por_cliente','commercial','Receita por Cliente','BRL'),
  ('frequencia_media','commercial','Frequência Média de Compra','count'),('concentracao_top3_clientes_perc','commercial','Concentração Top 3 Clientes','%'),
  ('skus_ativos','inventory','SKUs Ativos no Mês','count'),('quantidade_vendida','inventory','Quantidade Vendida','count'),
  ('receita_por_sku','inventory','Receita por SKU Ativo','BRL'),('concentracao_top3_produtos_perc','inventory','Concentração Top 3 Produtos','%'),
  ('fornecedores_ativos','supply','Fornecedores Ativos','count'),('receita_por_fornecedor','supply','Receita por Fornecedor','BRL'),
  ('concentracao_top1_fornecedor_perc','supply','Concentração Top Fornecedor','%'),('concentracao_top3_fornecedores_perc','supply','Concentração Top 3 Fornecedores','%')
) AS m(kpi, dimension, label, unit) ON m.kpi = a.kpi
UNION ALL SELECT 'finance','receita_ytd','Receita Acumulada (YTD)','BRL',ROUND(COALESCE(SUM(ft.valor),0)::numeric,2),NULL,NULL,NULL,NULL,0
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
  AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE) AND dd.data < CURRENT_DATE
UNION ALL SELECT 'inventory','skus_total','Total de SKUs (catálogo)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_inventory WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_base_total','Total de Clientes (base)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_ativos_90d','Clientes Ativos (últimos 90 dias)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL AND dias_recencia <= 90
UNION ALL SELECT 'commercial','recencia_media_dias','Recência Média da Base (dias)','days',ROUND(AVG(dias_recencia)::numeric,0),NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL
ORDER BY dimension, kpi;
$$;


ALTER FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid", "p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") RETURNS TABLE("entity" "text", "total_receita" numeric)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  SELECT 'clients'::text,   COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_clientes    WHERE client_id = p_client_id
  UNION ALL
  SELECT 'products'::text,  COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_inventory   WHERE client_id = p_client_id
  UNION ALL
  SELECT 'suppliers'::text, COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_fornecedores WHERE client_id = p_client_id;
$$;


ALTER FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_finance_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("receita_liquida" numeric, "custo_total" numeric, "despesas_total" numeric, "margem_bruta_perc" numeric, "margem_operacional_perc" numeric, "ticket_medio" numeric, "receita_yoy_perc" numeric, "crescimento_receita_perc" numeric, "total_pedidos" bigint, "dso_dias" numeric, "dpo_dias" numeric, "ccc_dias" numeric, "working_capital_ratio" numeric, "burn_rate_mensal" numeric, "runway_meses" numeric, "cash_flow_30d" numeric, "period" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id   uuid    := public.get_my_client_id();
  v_start       date;
  v_prev_start  date;
  v_prev_end    date;
  v_receita     numeric := 0;
  v_custo       numeric := 0;
  v_despesas    numeric := 0;
  v_pedidos     bigint  := 0;
  v_prev_rev    numeric := 0;
  v_yoy_rev     numeric := 0;
  v_margem_bruta numeric;
  v_margem_oper  numeric;
  v_cash_30d    numeric := 0;
  v_burn        numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  -- Receita líquida (vendas), custo (compras), despesas + contagem de pedidos
  SELECT
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0),
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0),
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'despesa'), 0),
    COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
  INTO v_receita, v_custo, v_despesas, v_pedidos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  -- Cash flow 30d fixo: vendas - compras - despesas
  SELECT
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  - COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
  - COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'despesa'), 0)
  INTO v_cash_30d
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (CURRENT_DATE - INTERVAL '30 days')::date
    AND dd.data < CURRENT_DATE;

  -- Burn rate mensal = média de saídas (compras + despesas) dos últimos 90 dias / 3
  SELECT COALESCE(SUM(ft.valor), 0) / 3.0
  INTO v_burn
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao IN ('compra', 'despesa')
    AND dd.data >= (CURRENT_DATE - INTERVAL '90 days')::date
    AND dd.data < CURRENT_DATE;

  -- Receita período anterior
  SELECT COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  -- Receita YoY
  SELECT COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  INTO v_yoy_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (v_start - INTERVAL '1 year')::date
    AND dd.data <  (CURRENT_DATE - INTERVAL '1 year')::date;

  v_margem_bruta := CASE WHEN v_receita > 0
    THEN ROUND((v_receita - v_custo) / v_receita * 100, 1)
    ELSE NULL END;

  v_margem_oper := CASE WHEN v_receita > 0
    THEN ROUND((v_receita - v_custo - v_despesas) / v_receita * 100, 1)
    ELSE NULL END;

  RETURN QUERY SELECT
    v_receita,
    v_custo,
    v_despesas,
    v_margem_bruta,
    v_margem_oper,
    CASE WHEN v_pedidos > 0 THEN ROUND(v_receita / v_pedidos, 2) ELSE 0 END,
    CASE WHEN v_yoy_rev  > 0 THEN ROUND((v_receita - v_yoy_rev)  / v_yoy_rev  * 100, 1) ELSE NULL END,
    CASE WHEN v_prev_rev > 0 THEN ROUND((v_receita - v_prev_rev) / v_prev_rev * 100, 1) ELSE NULL END,
    v_pedidos,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    ROUND(v_burn, 2),
    CASE WHEN v_burn > 0 THEN ROUND(v_cash_30d / v_burn, 1) ELSE NULL END,
    ROUND(v_cash_30d, 2),
    p_period;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_finance_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text" DEFAULT '30d'::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_days int; v_start date; v_prev_start date; v_result jsonb := '{}'::jsonb;
  v_receita numeric; v_prev_receita numeric; v_pedidos bigint; v_ticket numeric;
  v_clientes_ativos bigint; v_novos_clientes bigint; v_recorrentes bigint;
  v_skus_ativos bigint; v_giro numeric; v_rfqs bigint; v_pos_aprovadas bigint;
BEGIN
  v_days := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_start := CURRENT_DATE - (v_days * INTERVAL '1 day')::interval;
  v_prev_start := v_start - (v_days * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;
    v_result := jsonb_build_object('receita_liquida', v_receita, 'custo_total', NULL,
      'margem_bruta_perc', NULL, 'ticket_medio', v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2) ELSE NULL END);

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start
      GROUP BY ft.customer_id HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;
    v_result := jsonb_build_object('total_pedidos', v_pedidos, 'ticket_medio', v_ticket,
      'novos_clientes', v_novos_clientes, 'clientes_ativos', v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END);

  ELSIF p_dimension = 'inventory' THEN
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2) INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory WHERE client_id = p_client_id AND dias_recencia <= 90;
    v_result := jsonb_build_object('skus_ativos', v_skus_ativos, 'skus_sem_estoque', NULL,
      'stockout_rate_perc', NULL, 'giro_estoque', v_giro, 'dias_cobertura', NULL);

  ELSIF p_dimension = 'supply' THEN
    SELECT COUNT(DISTINCT fc.documento), COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas FROM analytics_v2.fato_compras fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id AND dd.data >= v_start;
    v_result := jsonb_build_object('rfqs_abertas', v_rfqs, 'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL, 'pos_aprovadas', v_pos_aprovadas);

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;
  RETURN v_result;
END; $$;


ALTER FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text" DEFAULT '30d'::"text", "p_offset_days" integer DEFAULT 0) RETURNS "jsonb"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_days      int;
  v_end       date;
  v_start     date;
  v_prev_start date;
  v_result    jsonb := '{}'::jsonb;

  v_receita       numeric;
  v_prev_receita  numeric;
  v_pedidos       bigint;
  v_ticket        numeric;
  v_clientes_ativos bigint;
  v_novos_clientes  bigint;
  v_recorrentes     bigint;
  v_skus_ativos   bigint;
  v_giro          numeric;
  v_rfqs          bigint;
  v_pos_aprovadas bigint;
BEGIN
  v_days       := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_end        := CURRENT_DATE - (p_offset_days * INTERVAL '1 day')::interval;
  v_start      := v_end      - (v_days        * INTERVAL '1 day')::interval;
  v_prev_start := v_start    - (v_days        * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;

    v_result := jsonb_build_object(
      'receita_liquida',         v_receita,
      'custo_total',             NULL,
      'margem_bruta_perc',       NULL,
      'ticket_medio',            v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2)
        ELSE NULL END
    );

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
        AND dd.data >= v_start AND dd.data <= v_end
      GROUP BY ft.customer_id
      HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;

    v_result := jsonb_build_object(
      'total_pedidos',        v_pedidos,
      'ticket_medio',         v_ticket,
      'novos_clientes',       v_novos_clientes,
      'clientes_ativos',      v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END
    );

  ELSIF p_dimension = 'inventory' THEN
    -- dim_inventory is a current-state snapshot (no time-series), offset has no effect
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2)
    INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory
    WHERE client_id = p_client_id AND dias_recencia <= 90;

    v_result := jsonb_build_object(
      'skus_ativos',       v_skus_ativos,
      'skus_sem_estoque',  NULL,
      'stockout_rate_perc', NULL,
      'giro_estoque',      v_giro,
      'dias_cobertura',    NULL
    );

  ELSIF p_dimension = 'supply' THEN
    SELECT
      COUNT(DISTINCT fc.documento),
      COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas
    FROM analytics_v2.fato_compras fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id
      AND dd.data >= v_start AND dd.data <= v_end;

    v_result := jsonb_build_object(
      'rfqs_abertas',           v_rfqs,
      'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL,
      'pos_aprovadas',          v_pos_aprovadas
    );

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;

  RETURN v_result;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text", "p_offset_days" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_inventory_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("skus_ativos" bigint, "skus_total" bigint, "quantidade_vendida_periodo" numeric, "receita_skus_periodo" numeric, "giro_estimado" numeric, "ticket_medio_sku" numeric, "cobertura_top20_perc" numeric, "stockout_rate_perc" numeric, "crescimento_quantidade_perc" numeric, "dio_dias" numeric, "cobertura_dias" numeric, "fill_rate_perc" numeric, "sell_through_perc" numeric, "gmroi" numeric, "acuracidade_perc" numeric, "period" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start     date;
  v_prev_start date;
  v_prev_end  date;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  RETURN QUERY
  WITH period_data AS (
    SELECT
      ft.produto_id,
      SUM(ft.quantidade) AS qtd,
      SUM(ft.valor)      AS rev
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.produto_id
  ),
  prev_data AS (
    SELECT SUM(ft.quantidade) AS qtd
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_prev_end
  ),
  top20_rev AS (
    SELECT SUM(rev) AS top_rev
    FROM (SELECT rev FROM period_data ORDER BY rev DESC LIMIT GREATEST(1, (SELECT COUNT(*) FROM period_data) * 20 / 100)) t
  ),
  agg AS (
    SELECT
      COUNT(*)                    AS skus_ativos,
      COALESCE(SUM(p.qtd), 0)   AS quantidade,
      COALESCE(SUM(p.rev), 0)   AS receita
    FROM period_data p
  )
  SELECT
    agg.skus_ativos,
    (SELECT COUNT(*) FROM analytics_v2.dim_inventory WHERE client_id = v_client_id),
    agg.quantidade,
    agg.receita,
    NULL::numeric, -- giro_estimado
    CASE WHEN agg.skus_ativos > 0 THEN ROUND(agg.receita / agg.skus_ativos, 2) ELSE 0 END,
    CASE WHEN agg.receita > 0 THEN ROUND((SELECT top_rev FROM top20_rev) / agg.receita * 100, 1) ELSE NULL END,
    NULL::numeric, -- stockout_rate_perc
    CASE WHEN (SELECT qtd FROM prev_data) > 0
         THEN ROUND((agg.quantidade - (SELECT qtd FROM prev_data)) / (SELECT qtd FROM prev_data) * 100, 1)
         ELSE NULL END,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    p_period
  FROM agg;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_inventory_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_kpi_mtd_comparison"() RETURNS TABLE("kpi" "text", "valor_atual" numeric, "valor_anterior" numeric, "variacao_pct" numeric, "tendencia" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id  uuid := public.get_my_client_id();
  v_mtd_start  date := DATE_TRUNC('month', CURRENT_DATE)::date;
  v_prev_start date := (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date;
  v_prev_end   date := DATE_TRUNC('month', CURRENT_DATE)::date;
  -- MTD
  v_receita_mtd numeric := 0; v_custo_mtd  numeric := 0;
  -- Prev month
  v_receita_prev numeric := 0; v_custo_prev numeric := 0;
BEGIN
  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda'  THEN ft.valor ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'compra' THEN ft.valor ELSE 0 END), 0)
  INTO v_receita_mtd, v_custo_mtd
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_mtd_start AND dd.data < CURRENT_DATE;

  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda'  THEN ft.valor ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'compra' THEN ft.valor ELSE 0 END), 0)
  INTO v_receita_prev, v_custo_prev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  RETURN QUERY
  WITH kpis(kpi, atual, anterior) AS (VALUES
    ('receita_liquida',   v_receita_mtd,  v_receita_prev),
    ('custo_mercadorias', v_custo_mtd,    v_custo_prev),
    ('margem_bruta',
      CASE WHEN v_receita_mtd  > 0 THEN ROUND((v_receita_mtd  - v_custo_mtd)  / v_receita_mtd  * 100, 1) ELSE 0::numeric END,
      CASE WHEN v_receita_prev > 0 THEN ROUND((v_receita_prev - v_custo_prev) / v_receita_prev * 100, 1) ELSE 0::numeric END),
    ('fluxo_caixa',
      v_receita_mtd  - v_custo_mtd,
      v_receita_prev - v_custo_prev)
  )
  SELECT
    k.kpi,
    k.atual,
    k.anterior,
    CASE WHEN k.anterior <> 0 THEN ROUND((k.atual - k.anterior) / ABS(k.anterior) * 100, 1) ELSE NULL END,
    CASE
      WHEN k.anterior = 0 THEN 'neutral'
      WHEN k.atual > k.anterior THEN 'up'
      WHEN k.atual < k.anterior THEN 'down'
      ELSE 'neutral'
    END
  FROM kpis k;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_kpi_mtd_comparison"() OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."get_kpi_mtd_comparison"() IS 'Cards de KPI MTD vs mês anterior: receita_liquida, custo_mercadorias, margem_bruta, fluxo_caixa. Usa tipo_transacao para separar venda/compra.';



CREATE OR REPLACE FUNCTION "analytics_v2"."get_kpi_mtd_comparison"("p_client_id" "uuid") RETURNS TABLE("dimension" "text", "kpi" "text", "label" "text", "unit" "text", "current_value" numeric, "prev_period_value" numeric, "avg_3m" numeric, "mom_pct" numeric, "vs_3m_avg_pct" numeric)
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_today     date := CURRENT_DATE;
  v_day       int  := EXTRACT(day FROM CURRENT_DATE);
  v_cur_start date := date_trunc('month', CURRENT_DATE)::date;
  v_m1_start date; v_m1_end date;
  v_m2_start date; v_m2_end date;
  v_m3_start date; v_m3_end date;
BEGIN
  v_m1_start := date_trunc('month', v_today - INTERVAL '1 month')::date;
  v_m1_end   := LEAST(v_m1_start + (v_day - 1), (v_m1_start + INTERVAL '1 month - 1 day')::date);
  v_m2_start := date_trunc('month', v_today - INTERVAL '2 months')::date;
  v_m2_end   := LEAST(v_m2_start + (v_day - 1), (v_m2_start + INTERVAL '1 month - 1 day')::date);
  v_m3_start := date_trunc('month', v_today - INTERVAL '3 months')::date;
  v_m3_end   := LEAST(v_m3_start + (v_day - 1), (v_m3_start + INTERVAL '1 month - 1 day')::date);

  RETURN QUERY
  WITH
  periods(tag, d_start, d_end) AS (
    VALUES ('cur'::text, v_cur_start, v_today),
           ('m1', v_m1_start, v_m1_end),
           ('m2', v_m2_start, v_m2_end),
           ('m3', v_m3_start, v_m3_end)
  ),
  raw AS (
    SELECT p.tag,
      COALESCE(SUM(ft.valor), 0)            AS receita,
      COUNT(DISTINCT ft.documento)           AS pedidos,
      COUNT(DISTINCT ft.customer_id)         AS clientes
    FROM periods p
    JOIN dim_datas dd ON dd.data BETWEEN p.d_start AND p.d_end
    JOIN fato_transacoes ft
      ON ft.data_competencia_id = dd.data_id
     AND ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
    GROUP BY p.tag
  ),
  base AS (
    SELECT p.tag,
      COALESCE(r.receita,  0) AS receita,
      COALESCE(r.pedidos,  0) AS pedidos,
      COALESCE(r.clientes, 0) AS clientes
    FROM periods p LEFT JOIN raw r USING (tag)
  ),
  agg AS (
    SELECT
      MAX(receita)  FILTER (WHERE tag='cur') AS cur_receita,
      MAX(pedidos)  FILTER (WHERE tag='cur') AS cur_pedidos,
      MAX(clientes) FILTER (WHERE tag='cur') AS cur_clientes,
      MAX(receita)  FILTER (WHERE tag='m1')  AS m1_receita,
      MAX(pedidos)  FILTER (WHERE tag='m1')  AS m1_pedidos,
      MAX(clientes) FILTER (WHERE tag='m1')  AS m1_clientes,
      ROUND((MAX(receita)  FILTER (WHERE tag='m1') + MAX(receita)  FILTER (WHERE tag='m2') + MAX(receita)  FILTER (WHERE tag='m3')) / 3, 2) AS avg_receita,
      ROUND((MAX(pedidos)  FILTER (WHERE tag='m1') + MAX(pedidos)  FILTER (WHERE tag='m2') + MAX(pedidos)  FILTER (WHERE tag='m3'))::numeric / 3, 1) AS avg_pedidos,
      ROUND((MAX(clientes) FILTER (WHERE tag='m1') + MAX(clientes) FILTER (WHERE tag='m2') + MAX(clientes) FILTER (WHERE tag='m3'))::numeric / 3, 1) AS avg_clientes
    FROM base
  ),
  novos AS (
    SELECT COUNT(*) AS cnt FROM (
      SELECT ft.customer_id FROM fato_transacoes ft
      JOIN dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id
        AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) BETWEEN v_cur_start AND v_today
    ) s
  ),
  recorrentes AS (
    SELECT COUNT(*) AS cnt FROM (
      SELECT ft.customer_id FROM fato_transacoes ft
      JOIN dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id
        AND ft.tipo_transacao = 'venda'
        AND dd.data BETWEEN v_cur_start AND v_today
      GROUP BY ft.customer_id HAVING COUNT(DISTINCT ft.documento) > 1
    ) s
  )
  SELECT 'finance'::text, 'receita_liquida', 'Receita MTD', 'BRL',
    ROUND(a.cur_receita, 2), ROUND(a.m1_receita, 2), a.avg_receita,
    CASE WHEN a.m1_receita > 0 THEN ROUND((a.cur_receita - a.m1_receita) / a.m1_receita * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_receita  > 0 THEN ROUND((a.cur_receita - a.avg_receita)  / a.avg_receita  * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'finance', 'ticket_medio', 'Ticket Médio', 'BRL',
    CASE WHEN a.cur_pedidos > 0 THEN ROUND(a.cur_receita / a.cur_pedidos, 2) ELSE NULL END,
    CASE WHEN a.m1_pedidos  > 0 THEN ROUND(a.m1_receita  / a.m1_pedidos,  2) ELSE NULL END,
    CASE WHEN a.avg_pedidos > 0 THEN ROUND(a.avg_receita / a.avg_pedidos, 2) ELSE NULL END,
    CASE WHEN a.m1_pedidos > 0 AND a.cur_pedidos > 0
         THEN ROUND(((a.cur_receita/a.cur_pedidos) - (a.m1_receita/a.m1_pedidos)) / (a.m1_receita/a.m1_pedidos) * 100, 1)
         ELSE NULL END,
    NULL
  FROM agg a
  UNION ALL
  SELECT 'commercial'::text, 'total_pedidos', 'Pedidos MTD', 'count',
    a.cur_pedidos::numeric, a.m1_pedidos::numeric, a.avg_pedidos,
    CASE WHEN a.m1_pedidos > 0 THEN ROUND((a.cur_pedidos - a.m1_pedidos)::numeric / a.m1_pedidos * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_pedidos > 0 THEN ROUND((a.cur_pedidos - a.avg_pedidos) / a.avg_pedidos * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'commercial', 'clientes_ativos', 'Clientes Ativos MTD', 'count',
    a.cur_clientes::numeric, a.m1_clientes::numeric, a.avg_clientes,
    CASE WHEN a.m1_clientes > 0 THEN ROUND((a.cur_clientes - a.m1_clientes)::numeric / a.m1_clientes * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_clientes > 0 THEN ROUND((a.cur_clientes - a.avg_clientes) / a.avg_clientes * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'commercial', 'novos_clientes', 'Novos Clientes MTD', 'count',
    novos.cnt::numeric, NULL, NULL, NULL, NULL FROM novos
  UNION ALL
  SELECT 'commercial', 'taxa_recorrencia_perc', 'Taxa de Recorrência', '%',
    CASE WHEN a.cur_clientes > 0 THEN ROUND(recorrentes.cnt::numeric / a.cur_clientes * 100, 1) ELSE NULL END,
    NULL, NULL, NULL, NULL
  FROM agg a, recorrentes;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_kpi_mtd_comparison"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_marketing_indicators"("p_period" "text") RETURNS TABLE("clientes_novos" bigint, "receita_novos_clientes" numeric, "n1" numeric, "n2" numeric, "n3" numeric, "n4" numeric, "n5" numeric, "n6" numeric, "n7" numeric, "n8" numeric, "n9" numeric, "periodo" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date; v_prev_start date; v_prev_end date;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end INTO v_start, v_prev_start, v_prev_end
  FROM analytics_v2._period_range(p_period) r;
  RETURN QUERY
  WITH first_purchases AS (
    SELECT ft.customer_id, MIN(dd.data) AS first_date FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id
  ),
  new_customers AS (
    SELECT fp.customer_id FROM first_purchases fp
    WHERE fp.first_date >= v_start AND fp.first_date < CURRENT_DATE
  ),
  new_customer_rev AS (
    SELECT COALESCE(SUM(ft.valor), 0) AS rev FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    JOIN new_customers nc ON nc.customer_id = ft.customer_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
  )
  SELECT (SELECT COUNT(*) FROM new_customers), (SELECT rev FROM new_customer_rev),
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, p_period;
END; $$;


ALTER FUNCTION "analytics_v2"."get_marketing_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_supply_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("rfqs_abertas" bigint, "rfqs_enviadas" bigint, "rfqs_respondidas" bigint, "taxa_resposta_perc" numeric, "tempo_resposta_medio_h" numeric, "pos_aprovadas" bigint, "pos_pendentes_aprovacao" bigint, "spend_periodo" numeric, "fornecedores_ativos" bigint, "concentracao_top_perc" numeric, "cycle_time_medio_h" numeric, "cost_savings_perc" numeric, "ppv" numeric, "otif_perc" numeric, "lead_time_medio_dias" numeric, "maverick_spend_perc" numeric, "spend_under_management_perc" numeric, "period" "text")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start     date;
  v_prev_start date;
  v_prev_end  date;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  RETURN QUERY
  WITH period_forn AS (
    SELECT
      ft.fornecedor_id,
      SUM(ft.valor) AS spend
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'compra'   -- ← FILTRO ADICIONADO
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.fornecedor_id
  ),
  total_spend AS (
    SELECT COALESCE(SUM(spend), 0) AS total FROM period_forn
  ),
  top_supplier AS (
    SELECT COALESCE(MAX(spend), 0) AS top FROM period_forn
  ),
  rfqs AS (
    SELECT
      COUNT(*) FILTER (WHERE status = 'pending')                              AS abertas,
      COUNT(*) FILTER (WHERE status IN ('pending','approved','rejected'))      AS enviadas,
      COUNT(*) FILTER (WHERE status IN ('approved','rejected'))                AS respondidas,
      COUNT(*) FILTER (WHERE status = 'approved')                             AS aprovadas,
      ROUND(AVG(EXTRACT(epoch FROM (decided_at - created_at)) / 3600)
            FILTER (WHERE decided_at IS NOT NULL)::numeric, 1)               AS tempo_resp_h,
      ROUND(AVG(EXTRACT(epoch FROM (decided_at - created_at)) / 3600)
            FILTER (WHERE status = 'approved' AND decided_at IS NOT NULL)::numeric, 1) AS cycle_h
    FROM public.approval_requests
    WHERE client_id = v_client_id
      AND created_at >= v_start
  )
  SELECT
    rfqs.abertas,
    rfqs.enviadas,
    rfqs.respondidas,
    CASE WHEN rfqs.enviadas > 0 THEN ROUND(rfqs.respondidas::numeric / rfqs.enviadas * 100, 1) ELSE NULL END,
    rfqs.tempo_resp_h,
    rfqs.aprovadas,
    rfqs.abertas,
    (SELECT total FROM total_spend),
    (SELECT COUNT(DISTINCT fornecedor_id) FROM period_forn),
    CASE WHEN (SELECT total FROM total_spend) > 0
         THEN ROUND((SELECT top FROM top_supplier) / (SELECT total FROM total_spend) * 100, 1)
         ELSE NULL END,
    rfqs.cycle_h,
    NULL::numeric,  -- cost_savings_perc (requer preço de referência)
    NULL::numeric,  -- ppv
    NULL::numeric,  -- otif_perc (requer data de entrega prometida)
    NULL::numeric,  -- lead_time_medio_dias
    NULL::numeric,  -- maverick_spend_perc
    NULL::numeric,  -- spend_under_management_perc
    p_period
  FROM rfqs;
END;
$$;


ALTER FUNCTION "analytics_v2"."get_supply_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."on_etl_job_completed"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_doc_type_id text;
BEGIN
  IF NEW.status <> 'completed' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = 'completed' THEN
    RETURN NEW;
  END IF;
  IF NEW.job_type <> 'bigquery_sync' THEN
    RETURN NEW;
  END IF;
  IF NEW.client_id IS NULL OR NEW.resource_type IS NULL THEN
    RETURN NEW;
  END IF;

  v_doc_type_id := analytics_v2.etl_resource_to_doc_type(NEW.resource_type);

  IF v_doc_type_id IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (NEW.client_id, v_doc_type_id, 'complete', 'erp_sync', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'erp_sync',
          updated_at = now()
      WHERE client_knowledge_documents.status <> 'complete';
  END IF;

  RETURN NEW;
EXCEPTION
  WHEN others THEN
    RAISE WARNING '[knowledge] ETL hook failed for job %: %', NEW.job_id, SQLERRM;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "analytics_v2"."on_etl_job_completed"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."parse_ingest_date"("p_value" "text") RETURNS "date"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $_$
DECLARE
  v_date date;
BEGIN
  IF p_value IS NULL OR p_value = '' THEN
    RETURN NULL;
  END IF;

  -- Tier 1: ISO / standard Postgres DATE cast (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, etc.)
  BEGIN
    v_date := p_value::date;
    RETURN v_date;
  EXCEPTION WHEN OTHERS THEN NULL; END;

  -- Tier 2: DD/MM/YYYY Brazilian format
  BEGIN
    v_date := to_date(p_value, 'DD/MM/YYYY');
    RETURN v_date;
  EXCEPTION WHEN OTHERS THEN NULL; END;

  -- Tier 3: Excel date serial (integer text). Uses 1899-12-30 epoch to handle
  -- Excel's 1900 leap-year bug. Sanity-bound to [1970, 2100].
  IF p_value ~ '^\d+$' THEN
    BEGIN
      v_date := DATE '1899-12-30' + p_value::integer;
      IF v_date BETWEEN DATE '1970-01-01' AND DATE '2100-01-01' THEN
        RETURN v_date;
      END IF;
    EXCEPTION WHEN OTHERS THEN NULL; END;
  END IF;

  RETURN NULL;
END;
$_$;


ALTER FUNCTION "analytics_v2"."parse_ingest_date"("p_value" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."parse_ingest_date"("p_value" "text") IS '3-tier date parser: ISO → DD/MM/YYYY → Excel serial. Used by apply_staging_to_facts.';



CREATE OR REPLACE FUNCTION "analytics_v2"."process_etl_job"("p_job_id" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  v_client_id           uuid;
  v_cred_id             uuid;
  v_source_type         text;
  v_watermark_canonical text;
  v_client_cpf_cnpj     text;
  v_new_watermark       text;
BEGIN
  -- Resolve job metadata
  SELECT j.client_id, j.credential_id, j.source_type
  INTO   v_client_id, v_cred_id, v_source_type
  FROM   analytics_v2.reg_jobs j
  WHERE  j.job_id = p_job_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job not found: %', p_job_id;
  END IF;

  -- Read client cpf_cnpj for classification
  SELECT cpf_cnpj
  INTO   v_client_cpf_cnpj
  FROM   public.clientes_blu
  WHERE  client_id = v_client_id
  LIMIT  1;

  -- Watermark column (source-specific)
  SELECT watermark_column
  INTO   v_watermark_canonical
  FROM   public.client_data_sources
  WHERE  client_id = v_client_id AND credential_id = v_cred_id;

  -- Upsert dim_clientes from staging
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf)
  SELECT DISTINCT ON (raw_data->>'cliente_cpf_cnpj')
    v_client_id,
    raw_data->>'cliente_cpf_cnpj',
    raw_data->>'cliente_nome',
    raw_data->>'cliente_telefone',
    raw_data->>'cliente_cidade',
    raw_data->>'cliente_uf'
  FROM fdw.staging_transacoes
  WHERE job_id = p_job_id AND raw_data->>'cliente_cpf_cnpj' IS NOT NULL
  ORDER BY raw_data->>'cliente_cpf_cnpj'
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome            = COALESCE(EXCLUDED.nome,            analytics_v2.dim_clientes.nome),
    telefone        = COALESCE(EXCLUDED.telefone,        analytics_v2.dim_clientes.telefone),
    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
    endereco_uf     = COALESCE(EXCLUDED.endereco_uf,     analytics_v2.dim_clientes.endereco_uf);

  -- Upsert dim_fornecedores from staging
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf)
  SELECT DISTINCT ON (raw_data->>'fornecedor_cnpj')
    v_client_id,
    raw_data->>'fornecedor_cnpj',
    raw_data->>'fornecedor_nome',
    raw_data->>'fornecedor_telefone',
    raw_data->>'fornecedor_cidade',
    raw_data->>'fornecedor_uf'
  FROM fdw.staging_transacoes
  WHERE job_id = p_job_id AND raw_data->>'fornecedor_cnpj' IS NOT NULL
  ORDER BY raw_data->>'fornecedor_cnpj'
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome            = COALESCE(EXCLUDED.nome,            analytics_v2.dim_fornecedores.nome),
    telefone        = COALESCE(EXCLUDED.telefone,        analytics_v2.dim_fornecedores.telefone),
    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
    endereco_uf     = COALESCE(EXCLUDED.endereco_uf,     analytics_v2.dim_fornecedores.endereco_uf);

  -- Ensure dim_datas coverage
  INSERT INTO analytics_v2.dim_datas (data_id, data, mes, ano, semestre, trimestre)
  SELECT DISTINCT
    to_char(d::date, 'YYYYMMDD')::bigint,
    d::date,
    EXTRACT(month  FROM d::date)::int,
    EXTRACT(year   FROM d::date)::int,
    CASE WHEN EXTRACT(month FROM d::date) <= 6 THEN 1 ELSE 2 END,
    CEIL(EXTRACT(month FROM d::date) / 3.0)::int
  FROM (
    SELECT (raw_data->>'data_competencia_id')::date AS d
    FROM fdw.staging_transacoes
    WHERE job_id = p_job_id AND raw_data->>'data_competencia_id' IS NOT NULL
  ) dates
  ON CONFLICT (data_id) DO NOTHING;

  -- Upsert fato_transacoes with entry_type classification
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, customer_id, fornecedor_id,
     produto_id, documento, quantidade, valor_unitario, valor, status,
     tipo_transacao, tipo_lancamento, entry_type, categoria, subcategoria)
  SELECT
    s.raw_data->>'documento',
    v_client_id,
    dd.data_id,
    dc.customer_id,
    df.fornecedor_id,
    di.inventory_id,
    s.raw_data->>'documento',
    (s.raw_data->>'quantidade')::numeric,
    (s.raw_data->>'valor_unitario')::numeric,
    (s.raw_data->>'valor')::numeric,
    s.raw_data->>'status',
    -- tipo_transacao: source label or CNPJ-derived fallback
    COALESCE(
      NULLIF(s.raw_data->>'tipo_transacao', ''),
      CASE
        WHEN v_client_cpf_cnpj IS NOT NULL
          AND regexp_replace(s.raw_data->>'fornecedor_cnpj', '[^0-9]', '', 'g')
            = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'venda'
        WHEN v_client_cpf_cnpj IS NOT NULL
          AND regexp_replace(s.raw_data->>'cliente_cpf_cnpj', '[^0-9]', '', 'g')
            = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'compra'
        ELSE NULL
      END
    ),
    -- tipo_lancamento: legacy field from raw source (CSV mapped)
    NULLIF(s.raw_data->>'tipo_lancamento', ''),
    -- entry_type: system-derived direction (revenue/purchase/expense/banking)
    CASE
      WHEN v_client_cpf_cnpj IS NOT NULL
        AND regexp_replace(s.raw_data->>'fornecedor_cnpj', '[^0-9]', '', 'g')
          = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
        THEN 'revenue'
      WHEN v_client_cpf_cnpj IS NOT NULL
        AND regexp_replace(s.raw_data->>'cliente_cpf_cnpj', '[^0-9]', '', 'g')
          = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
        THEN 'purchase'
      ELSE 'revenue'   -- safe default for NF-e without CNPJ match
    END,
    NULLIF(s.raw_data->>'categoria', ''),
    NULLIF(s.raw_data->>'subcategoria', '')
  FROM (
    SELECT DISTINCT ON (raw_data->>'documento') raw_data
    FROM fdw.staging_transacoes
    WHERE job_id = p_job_id AND raw_data->>'documento' IS NOT NULL
    ORDER BY raw_data->>'documento'
  ) s
  LEFT JOIN analytics_v2.dim_datas        dd ON dd.data      = (s.raw_data->>'data_competencia_id')::date
  LEFT JOIN analytics_v2.dim_clientes     dc ON dc.client_id = v_client_id AND dc.cpf_cnpj  = s.raw_data->>'cliente_cpf_cnpj'
  LEFT JOIN analytics_v2.dim_fornecedores df ON df.client_id = v_client_id AND df.cnpj      = s.raw_data->>'fornecedor_cnpj'
  LEFT JOIN analytics_v2.dim_inventory    di ON di.client_id = v_client_id AND di.sku       = s.raw_data->>'produto_sku'
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    customer_id         = EXCLUDED.customer_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status,
    tipo_transacao      = COALESCE(EXCLUDED.tipo_transacao,  analytics_v2.fato_transacoes.tipo_transacao),
    tipo_lancamento     = COALESCE(EXCLUDED.tipo_lancamento, analytics_v2.fato_transacoes.tipo_lancamento),
    entry_type          = COALESCE(EXCLUDED.entry_type,      analytics_v2.fato_transacoes.entry_type),
    categoria           = COALESCE(EXCLUDED.categoria,       analytics_v2.fato_transacoes.categoria),
    subcategoria        = COALESCE(EXCLUDED.subcategoria,    analytics_v2.fato_transacoes.subcategoria);

  -- Advance watermark
  IF v_watermark_canonical IS NOT NULL THEN
    EXECUTE format(
      'SELECT MAX(raw_data->>%L) FROM fdw.staging_transacoes WHERE job_id = %L',
      v_watermark_canonical, p_job_id
    ) INTO v_new_watermark;
  END IF;

  UPDATE public.client_data_sources
  SET last_watermark_value = COALESCE(v_new_watermark, last_watermark_value),
      sync_status          = 'synced',
      last_synced_at       = now(),
      updated_at           = now()
  WHERE client_id = v_client_id AND credential_id = v_cred_id;

  -- Clean staging + mark job completed
  DELETE FROM fdw.staging_transacoes WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs
  SET status     = 'completed',
      updated_at = now()
  WHERE job_id = p_job_id;

EXCEPTION WHEN OTHERS THEN
  UPDATE analytics_v2.reg_jobs
  SET status     = 'failed',
      error_msg  = SQLERRM,
      updated_at = now()
  WHERE job_id = p_job_id;
  RAISE;
END;
$$;


ALTER FUNCTION "analytics_v2"."process_etl_job"("p_job_id" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."process_pending_csv_jobs"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_job_id UUID;
BEGIN
  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE job_type = 'csv_sync'
    AND (
      status = 'pending'
      OR (
        status = 'failed'
        AND retry_count < 3
        AND completed_at < now() - interval '5 minutes'
      )
    )
  ORDER BY
    CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
    created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs
    SET
      status        = 'pending',
      retry_count   = retry_count + 1,
      error_message = NULL,
      updated_at    = clock_timestamp()
    WHERE job_id = v_job_id AND status = 'failed';

    RAISE NOTICE '[process_pending_csv_jobs] dispatching job %', v_job_id;
    PERFORM public.sincronizar_csv_cliente(v_job_id);
  END IF;
END;
$$;


ALTER FUNCTION "analytics_v2"."process_pending_csv_jobs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."process_pending_etl_jobs"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_job_id uuid;
BEGIN
  -- Pick one job: pending jobs first, then failed jobs eligible for retry
  -- (failed < 3 times, last attempt > 5 minutes ago)
  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE job_type = 'bigquery_sync'
    AND (
      status = 'pending'
      OR (
        status = 'failed'
        AND retry_count < 3
        AND completed_at < now() - interval '5 minutes'
      )
    )
  ORDER BY
    CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
    created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_job_id IS NOT NULL THEN
    -- If this is a retry, reset back to pending and increment counter
    UPDATE analytics_v2.reg_jobs
    SET
      status        = 'pending',
      retry_count   = retry_count + 1,
      error_message = NULL,
      updated_at    = clock_timestamp()
    WHERE job_id = v_job_id AND status = 'failed';

    RAISE NOTICE '[process_pending_etl_jobs] dispatching job %', v_job_id;
    PERFORM analytics_v2.run_etl_job(v_job_id);
  END IF;
END;
$$;


ALTER FUNCTION "analytics_v2"."process_pending_etl_jobs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."process_pending_jobs"() RETURNS TABLE("job_id" "uuid", "request_id" bigint)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'vault', 'extensions'
    AS $$
DECLARE
  v_base_url text := 'https://haruewffnubdgyofftut.supabase.co/functions/v1';
  v_jwt      text;
  v_job      RECORD;
  v_request  bigint;
BEGIN
  -- Lê service_role_key exclusivamente do Vault (criptografado at rest)
  SELECT decrypted_secret INTO v_jwt
  FROM vault.decrypted_secrets
  WHERE name = 'app_service_role_key'
  LIMIT 1;

  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] vault.secrets app_service_role_key not found';
  END IF;

  FOR v_job IN
    UPDATE analytics_v2.reg_jobs rj
    SET status     = 'running',
        started_at = now(),
        updated_at = now()
    WHERE rj.job_id IN (
      SELECT j2.job_id FROM analytics_v2.reg_jobs j2
      WHERE j2.status   = 'pending'
        AND j2.job_type IN ('bigquery_sync', 'refresh_dashboards')
      ORDER BY j2.created_at
      LIMIT 15
      FOR UPDATE SKIP LOCKED
    )
    RETURNING rj.job_id, rj.job_type
  LOOP
    SELECT net.http_post(
      url := v_base_url || CASE v_job.job_type
               WHEN 'refresh_dashboards' THEN '/etl-refresh-dashboards'
               ELSE '/etl-bigquery-ingest'
             END,
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || v_jwt
      ),
      body := jsonb_build_object('job_id', v_job.job_id),
      timeout_milliseconds := 5000
    ) INTO v_request;

    job_id     := v_job.job_id;
    request_id := v_request;
    RETURN NEXT;
  END LOOP;

  RETURN;
END;
$$;


ALTER FUNCTION "analytics_v2"."process_pending_jobs"() OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."process_pending_jobs"() IS 'Cron dispatcher — lê JWT exclusivamente do Vault (app_service_role_key). Claims até 15 jobs pending (bigquery_sync | refresh_dashboards) por tick via pg_net. SECURITY: nunca lê segredos de public.app_config.';



CREATE OR REPLACE FUNCTION "analytics_v2"."reset_stuck_running_jobs"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  affected integer;
BEGIN
  UPDATE analytics_v2.reg_jobs
     SET status = 'pending',
         error_message = COALESCE(error_message, '')
                       || CASE WHEN error_message IS NULL OR error_message = ''
                               THEN '' ELSE E'\n' END
                       || 'watchdog: reset from running (updated_at='
                       || updated_at::text || ')',
         updated_at = now()
   WHERE status = 'running'
     AND updated_at < now() - interval '3 minutes';

  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$;


ALTER FUNCTION "analytics_v2"."reset_stuck_running_jobs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."run_etl_job"("p_job_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2', 'fdw'
    AS $_$
DECLARE
  v_client_id           uuid;
  v_cred_id             bigint;
  v_force_full          boolean;
  v_mapping             jsonb;
  v_watermark_col       text;
  v_last_watermark      text;
  v_watermark_canonical text;
  v_server_name         text;
  v_ft_name             text;
  v_columns             jsonb;
  v_col_defs            text;
  v_col                 text;
  v_canonical           text;
  v_select_parts        text[] := '{}';
  v_select_sql          text;
  v_row_count           bigint := 0;
  v_new_watermark       text;
  v_client_cpf_cnpj     text;
BEGIN
  -- 1. Claim job
  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = now()
  WHERE job_id = p_job_id AND status = 'pending'
  RETURNING client_id,
            (input_params->>'credential_id')::bigint,
            COALESCE((input_params->>'force_full_sync')::boolean, false)
  INTO v_client_id, v_cred_id, v_force_full;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job % not found or not pending', p_job_id;
  END IF;

  -- 2. Read config + FDW metadata
  SELECT cds.column_mapping,
         cds.watermark_column,
         cds.last_watermark_value,
         bft.table_name,
         bft.server_name,
         bft.columns
  INTO   v_mapping, v_watermark_col, v_last_watermark,
         v_ft_name, v_server_name, v_columns
  FROM   public.client_data_sources       cds
  JOIN   public.bigquery_foreign_tables   bft
         ON bft.client_id    = cds.client_id
        AND bft.credential_id = cds.credential_id
  WHERE  cds.client_id    = v_client_id
    AND  cds.credential_id = v_cred_id
  LIMIT 1;

  IF v_ft_name IS NULL THEN
    RAISE EXCEPTION 'No foreign table metadata for client % / credential %', v_client_id, v_cred_id;
  END IF;
  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery server configured for client % / credential %', v_client_id, v_cred_id;
  END IF;

  -- 2b. Read client cpf_cnpj for income/expense classification
  SELECT cpf_cnpj
  INTO   v_client_cpf_cnpj
  FROM   public.clientes_blu
  WHERE  client_id = v_client_id;

  IF v_mapping IS NULL OR v_mapping = 'null'::jsonb THEN v_mapping := '{}'::jsonb; END IF;
  IF v_force_full THEN v_last_watermark := NULL; END IF;

  IF v_last_watermark IS NOT NULL THEN
    v_last_watermark := regexp_replace(v_last_watermark, '[+-]\d{2}:?\d{2}$', '');
  END IF;

  -- 3. Ensure FDW foreign table
  v_col_defs := COALESCE(NULLIF(public._bq_col_defs_from_jsonb(v_columns), ''), '_raw text');
  EXECUTE 'CREATE SCHEMA IF NOT EXISTS fdw';
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I', v_ft_name);
  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_ft_name, v_col_defs, v_server_name, v_ft_name
  );

  -- 4. Build SELECT list from column_mapping
  FOR v_col, v_canonical IN
    SELECT key, value #>> '{}' FROM jsonb_each(v_mapping)
  LOOP
    v_select_parts := array_append(v_select_parts, format('%I AS %I', v_col, v_canonical));
    IF v_col = v_watermark_col THEN v_watermark_canonical := v_canonical; END IF;
  END LOOP;

  -- 5. Build SELECT SQL (incremental when watermark available)
  IF array_length(v_select_parts, 1) IS NULL THEN
    v_select_sql          := format('SELECT * FROM fdw.%I', v_ft_name);
    v_watermark_canonical := v_watermark_col;
  ELSIF v_watermark_col IS NOT NULL AND v_last_watermark IS NOT NULL AND NOT v_force_full THEN
    v_select_sql := format(
      'SELECT %s FROM fdw.%I WHERE %I > %L',
      array_to_string(v_select_parts, ', '), v_ft_name, v_watermark_col, v_last_watermark
    );
  ELSE
    v_select_sql := format(
      'SELECT %s FROM fdw.%I',
      array_to_string(v_select_parts, ', '), v_ft_name
    );
  END IF;

  -- 6. Clean leftover staging rows
  DELETE FROM fdw.staging_transacoes WHERE job_id = p_job_id;

  -- 7. Stage FDW rows
  EXECUTE format('
    INSERT INTO fdw.staging_transacoes (job_id, client_id, raw_data)
    SELECT %L::uuid, %L::uuid, row_to_json(t)::jsonb
    FROM (%s) t
  ', p_job_id, v_client_id, v_select_sql);

  GET DIAGNOSTICS v_row_count = ROW_COUNT;

  IF v_row_count = 0 THEN
    UPDATE analytics_v2.reg_jobs
    SET status = 'completed', completed_at = now(), rows_inserted = 0, progress_pct = 100,
        error_message = 'No new rows since last sync'
    WHERE job_id = p_job_id;
    RETURN;
  END IF;

  -- 8. Upsert dim_clientes
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf)
  SELECT DISTINCT ON (raw_data->>'cliente_cpf_cnpj')
    v_client_id,
    raw_data->>'cliente_cpf_cnpj',
    raw_data->>'cliente_nome',
    raw_data->>'cliente_telefone',
    raw_data->>'cliente_cidade',
    raw_data->>'cliente_uf'
  FROM fdw.staging_transacoes
  WHERE job_id = p_job_id AND raw_data->>'cliente_cpf_cnpj' IS NOT NULL
  ORDER BY raw_data->>'cliente_cpf_cnpj'
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = now();

  -- 9. Upsert dim_fornecedores
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf)
  SELECT DISTINCT ON (raw_data->>'fornecedor_cnpj')
    v_client_id,
    raw_data->>'fornecedor_cnpj',
    raw_data->>'fornecedor_nome',
    raw_data->>'fornecedor_telefone',
    raw_data->>'fornecedor_cidade',
    raw_data->>'fornecedor_uf'
  FROM fdw.staging_transacoes
  WHERE job_id = p_job_id AND raw_data->>'fornecedor_cnpj' IS NOT NULL
  ORDER BY raw_data->>'fornecedor_cnpj'
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome            = EXCLUDED.nome,
    telefone        = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade,
    endereco_uf     = EXCLUDED.endereco_uf,
    atualizado_em   = now();

  -- 10. Upsert dim_inventory
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome)
  SELECT DISTINCT ON (raw_data->>'produto_sku')
    v_client_id,
    raw_data->>'produto_sku',
    raw_data->>'produto_nome'
  FROM fdw.staging_transacoes
  WHERE job_id = p_job_id AND raw_data->>'produto_sku' IS NOT NULL
  ORDER BY raw_data->>'produto_sku'
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome       = EXCLUDED.nome,
    updated_at = now();

  -- 11. Ensure dim_datas rows
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    d::date,
    EXTRACT(year    FROM d::date)::int,
    EXTRACT(month   FROM d::date)::int,
    EXTRACT(day     FROM d::date)::int,
    EXTRACT(dow     FROM d::date)::int,
    EXTRACT(week    FROM d::date)::int,
    CASE WHEN EXTRACT(month FROM d::date) <= 6 THEN 1 ELSE 2 END,
    'Q' || EXTRACT(quarter FROM d::date)::text
  FROM (
    SELECT raw_data->>'data_competencia_id' AS d
    FROM fdw.staging_transacoes
    WHERE job_id = p_job_id
      AND raw_data->>'data_competencia_id' IS NOT NULL
      AND raw_data->>'data_competencia_id' ~ '^\d{4}-\d{2}-\d{2}'
  ) sub
  ON CONFLICT (data) DO NOTHING;

  -- 12. Upsert fato_transacoes com classificação em cascata
  --
  --   Prioridade de tipo_transacao:
  --     1. Valor mapeado explicitamente na fonte
  --     2. cpf_cnpj direto (fornecedor = client → venda; cliente = client → compra)
  --     3. Join dimensional: dc (dim_clientes) populado no step 8 → venda
  --                          df (dim_fornecedores) populado no step 9 → compra
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, customer_id, fornecedor_id,
     produto_id, documento, quantidade, valor_unitario, valor, status,
     tipo_transacao, tipo_lancamento, categoria, subcategoria)
  SELECT
    s.raw_data->>'documento',
    v_client_id,
    dd.data_id,
    dc.customer_id,
    df.fornecedor_id,
    di.inventory_id,
    s.raw_data->>'documento',
    (s.raw_data->>'quantidade')::numeric,
    (s.raw_data->>'valor_unitario')::numeric,
    (s.raw_data->>'valor')::numeric,
    s.raw_data->>'status',
    COALESCE(
      NULLIF(s.raw_data->>'tipo_transacao', ''),
      CASE
        WHEN v_client_cpf_cnpj IS NOT NULL
          AND regexp_replace(s.raw_data->>'fornecedor_cnpj',   '[^0-9]', '', 'g')
            = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'venda'
        WHEN v_client_cpf_cnpj IS NOT NULL
          AND regexp_replace(s.raw_data->>'cliente_cpf_cnpj', '[^0-9]', '', 'g')
            = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
          THEN 'compra'
        WHEN dc.customer_id   IS NOT NULL THEN 'venda'
        WHEN df.fornecedor_id IS NOT NULL THEN 'compra'
        ELSE NULL
      END
    ),
    NULLIF(s.raw_data->>'tipo_lancamento', ''),
    NULLIF(s.raw_data->>'categoria', ''),
    NULLIF(s.raw_data->>'subcategoria', '')
  FROM (
    SELECT DISTINCT ON (raw_data->>'documento') raw_data
    FROM fdw.staging_transacoes
    WHERE job_id = p_job_id AND raw_data->>'documento' IS NOT NULL
    ORDER BY raw_data->>'documento'
  ) s
  LEFT JOIN analytics_v2.dim_datas        dd ON dd.data      = (s.raw_data->>'data_competencia_id')::date
  LEFT JOIN analytics_v2.dim_clientes     dc ON dc.client_id = v_client_id AND dc.cpf_cnpj  = s.raw_data->>'cliente_cpf_cnpj'
  LEFT JOIN analytics_v2.dim_fornecedores df ON df.client_id = v_client_id AND df.cnpj      = s.raw_data->>'fornecedor_cnpj'
  LEFT JOIN analytics_v2.dim_inventory    di ON di.client_id = v_client_id AND di.sku       = s.raw_data->>'produto_sku'
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    customer_id         = EXCLUDED.customer_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status,
    tipo_transacao      = COALESCE(EXCLUDED.tipo_transacao,  analytics_v2.fato_transacoes.tipo_transacao),
    tipo_lancamento     = COALESCE(EXCLUDED.tipo_lancamento, analytics_v2.fato_transacoes.tipo_lancamento),
    categoria           = COALESCE(EXCLUDED.categoria,       analytics_v2.fato_transacoes.categoria),
    subcategoria        = COALESCE(EXCLUDED.subcategoria,    analytics_v2.fato_transacoes.subcategoria);

  -- 13. Advance watermark
  IF v_watermark_canonical IS NOT NULL THEN
    EXECUTE format(
      'SELECT MAX(raw_data->>%L) FROM fdw.staging_transacoes WHERE job_id = %L',
      v_watermark_canonical, p_job_id
    ) INTO v_new_watermark;
  END IF;

  UPDATE public.client_data_sources
  SET last_watermark_value = COALESCE(v_new_watermark, last_watermark_value),
      sync_status          = 'synced',
      last_synced_at       = now(),
      updated_at           = now()
  WHERE client_id = v_client_id AND credential_id = v_cred_id;

  -- 14. Clean staging + mark completed
  DELETE FROM fdw.staging_transacoes WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs
  SET status        = 'completed',
      completed_at  = now(),
      rows_inserted = v_row_count,
      progress_pct  = 100
  WHERE job_id = p_job_id;

  -- 15. Refresh materialized views (best-effort)
  BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[run_etl_job] MV refresh failed for client %: %', v_client_id, SQLERRM;
  END;

EXCEPTION WHEN OTHERS THEN
  DELETE FROM fdw.staging_transacoes WHERE job_id = p_job_id;
  UPDATE analytics_v2.reg_jobs
  SET status        = 'failed',
      completed_at  = now(),
      error_message = SQLERRM
  WHERE job_id = p_job_id;
END;
$_$;


ALTER FUNCTION "analytics_v2"."run_etl_job"("p_job_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."safe_to_numeric"("p_text" "text") RETURNS numeric
    LANGUAGE "plpgsql" IMMUTABLE
    AS $_$
DECLARE
  v_text text;
BEGIN
  IF p_text IS NULL OR trim(p_text) = '' THEN
    RETURN NULL;
  END IF;
  v_text := trim(p_text);

  -- Direct cast: plain integers and standard decimals (1234, 1234.56, -1234.56)
  BEGIN
    RETURN v_text::numeric;
  EXCEPTION WHEN OTHERS THEN NULL;
  END;

  -- Brazilian format: period = thousands sep, comma = decimal ("1.234,56")
  IF v_text ~ '^-?[\d.]+,\d+$' THEN
    BEGIN
      RETURN replace(replace(v_text, '.', ''), ',', '.')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  -- US format: comma = thousands sep, period = decimal ("1,234.56")
  IF v_text ~ '^-?[\d,]+\.\d+$' THEN
    BEGIN
      RETURN replace(v_text, ',', '')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  RETURN NULL;
END;
$_$;


ALTER FUNCTION "analytics_v2"."safe_to_numeric"("p_text" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_synced  int := 0;
  v_skipped int := 0;
BEGIN
  INSERT INTO analytics_v2.fato_transacoes (
    transacao_id,
    client_id,
    data_competencia_id,
    customer_id,
    fornecedor_id,
    produto_id,
    documento,
    quantidade,
    valor_unitario,
    valor,
    status,
    tipo_transacao,
    tipo_lancamento,
    categoria,
    subcategoria,
    updated_at
  )
  SELECT
    'polp_' || pt.polp_transaction_id::text,
    pt.client_id,
    dd.data_id,
    NULL::bigint,
    NULL::bigint,
    NULL::bigint,
    'polp_' || pt.polp_transaction_id::text,
    1,
    ABS(pt.amount),
    ABS(pt.amount),
    COALESCE(pt.status, 'confirmed'),
    CASE
      WHEN pt.type = 'CREDIT' THEN 'venda'
      WHEN pt.type = 'DEBIT'  THEN 'compra'
      ELSE NULL
    END,
    'bancario',
    pt.category->>'name',
    pt.category->>'description',
    NOW()
  FROM public.polp_transactions pt
  LEFT JOIN analytics_v2.dim_datas dd
    ON dd.data_id = to_char(pt.date, 'YYYYMMDD')::bigint
  WHERE pt.client_id = p_client_id
    AND pt.status IS DISTINCT FROM 'deleted'
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    valor          = EXCLUDED.valor,
    valor_unitario = EXCLUDED.valor_unitario,
    status         = EXCLUDED.status,
    tipo_transacao = COALESCE(analytics_v2.fato_transacoes.tipo_transacao, EXCLUDED.tipo_transacao),
    categoria      = COALESCE(analytics_v2.fato_transacoes.categoria,      EXCLUDED.categoria),
    subcategoria   = COALESCE(analytics_v2.fato_transacoes.subcategoria,   EXCLUDED.subcategoria),
    updated_at     = NOW();

  GET DIAGNOSTICS v_synced = ROW_COUNT;

  RETURN jsonb_build_object('synced', v_synced, 'client_id', p_client_id);
END;
$$;


ALTER FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid", "p_batch_size" integer DEFAULT 500) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_synced        int := 0;
    v_batch_synced  int;
    v_last_id       bigint := 0;
BEGIN
    LOOP
        INSERT INTO analytics_v2.fato_transacoes (
            transacao_id,
            client_id,
            data_competencia_id,
            customer_id,
            fornecedor_id,
            produto_id,
            documento,
            quantidade,
            valor_unitario,
            valor,
            status,
            tipo_transacao,
            tipo_lancamento,
            categoria,
            subcategoria,
            updated_at
        )
        SELECT
            'polp_' || pt.polp_transaction_id::text,
            pt.client_id,
            dd.data_id,
            NULL::bigint,
            NULL::bigint,
            NULL::bigint,
            'polp_' || pt.polp_transaction_id::text,
            1,
            ABS(pt.amount),
            ABS(pt.amount),
            COALESCE(pt.status, 'confirmed'),
            CASE
              WHEN pt.type = 'CREDIT' THEN 'venda'
              WHEN pt.type = 'DEBIT'  THEN 'compra'
              ELSE NULL
            END,
            'bancario',
            pt.category->>'name',
            pt.category->>'description',
            NOW()
        FROM public.polp_transactions pt
        LEFT JOIN analytics_v2.dim_datas dd
            ON dd.data_id = to_char(pt.date, 'YYYYMMDD')::bigint
        WHERE pt.client_id = p_client_id
          AND pt.status IS DISTINCT FROM 'deleted'
          AND pt.polp_transaction_id > v_last_id
        ORDER BY pt.polp_transaction_id
        LIMIT p_batch_size
        ON CONFLICT (transacao_id, client_id) DO UPDATE SET
            valor          = EXCLUDED.valor,
            valor_unitario = EXCLUDED.valor_unitario,
            status         = EXCLUDED.status,
            tipo_transacao = COALESCE(analytics_v2.fato_transacoes.tipo_transacao, EXCLUDED.tipo_transacao),
            categoria      = COALESCE(analytics_v2.fato_transacoes.categoria,      EXCLUDED.categoria),
            subcategoria   = COALESCE(analytics_v2.fato_transacoes.subcategoria,   EXCLUDED.subcategoria),
            updated_at     = NOW();

        GET DIAGNOSTICS v_batch_synced = ROW_COUNT;
        v_synced := v_synced + v_batch_synced;

        EXIT WHEN v_batch_synced < p_batch_size;

        -- Advance cursor: find the max polp_transaction_id processed in this batch
        SELECT MAX(pt.polp_transaction_id)
          INTO v_last_id
          FROM public.polp_transactions pt
         WHERE pt.client_id = p_client_id
           AND pt.status IS DISTINCT FROM 'deleted'
           AND pt.polp_transaction_id > v_last_id
         ORDER BY pt.polp_transaction_id
         LIMIT p_batch_size;
    END LOOP;

    RETURN jsonb_build_object('synced', v_synced, 'client_id', p_client_id);
END;
$$;


ALTER FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid", "p_batch_size" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid", "p_batch_size" integer) IS 'Syncs polp_transactions -> fato_transacoes in batches. Use direct connection (port 5432) for large volumes. Caller: enqueue_polp_sync or edge function polp-sync-worker.';



CREATE OR REPLACE FUNCTION "analytics_v2"."trigger_context_report_on_etl"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  _supabase_url   text := current_setting('app.supabase_url', true);
  _service_key    text := current_setting('app.service_role_key', true);
  _existing_count int;
BEGIN
  IF NEW.status <> 'completed' THEN
    RETURN NEW;
  END IF;

  SELECT count(*) INTO _existing_count
  FROM vector_db.documents
  WHERE client_id = NEW.client_id
    AND source    = 'generated'
    AND category  = 'business_context';

  IF _supabase_url IS NOT NULL AND _service_key IS NOT NULL THEN
    PERFORM net.http_post(
      url     := _supabase_url || '/functions/v1/generate-context-report',
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || _service_key
      ),
      body    := jsonb_build_object('client_id', NEW.client_id)
    );
  END IF;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "analytics_v2"."trigger_context_report_on_etl"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE
    AS $$
  SELECT p_project_id || '.' || p_dataset_id || '.' || p_table_name;
$$;


ALTER FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") RETURNS "text"
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
  SELECT string_agg(
    format('%I %s', col->>'name', public._bq_type_to_postgres_type(col->>'type')),
    ', '
    ORDER BY ordinality
  )
  FROM jsonb_array_elements(p_columns) WITH ORDINALITY AS t(col, ordinality);
$$;


ALTER FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") RETURNS "text"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
DECLARE
  v_bq_type_lower TEXT := LOWER(p_bq_type);
BEGIN
  CASE v_bq_type_lower
    -- Numeric types
    WHEN 'int64', 'integer' THEN RETURN 'bigint';
    WHEN 'int32' THEN RETURN 'integer';
    WHEN 'float64', 'float' THEN RETURN 'double precision';
    WHEN 'float32' THEN RETURN 'real';
    WHEN 'numeric', 'decimal' THEN RETURN 'numeric';

    -- String types
    WHEN 'string' THEN RETURN 'text';
    WHEN 'bytes' THEN RETURN 'bytea';

    -- Boolean
    WHEN 'bool', 'boolean' THEN RETURN 'boolean';

    -- Temporal types
    WHEN 'date' THEN RETURN 'date';
    WHEN 'time', 'time64' THEN RETURN 'time';
    WHEN 'datetime', 'timestamp' THEN RETURN 'timestamp with time zone';

    -- Complex types (stored as JSON)
    WHEN 'record', 'struct' THEN RETURN 'jsonb';
    WHEN 'array' THEN RETURN 'jsonb';
    WHEN 'geography', 'bignumeric' THEN RETURN 'jsonb';

    -- Default fallback
    ELSE RETURN 'text';
  END CASE;
END;
$$;


ALTER FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") IS 'Helper function to map BigQuery data types to PostgreSQL equivalents.
Used by async discovery to generate CREATE FOREIGN TABLE DDL.';



CREATE OR REPLACE FUNCTION "public"."auto_enroll_catalog_routines"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  insert into public.client_routines (
    client_id, routine_id, source, status, active,
    config, trigger_type, trigger_config
  )
  select
    new.client_id,
    r.id,
    'catalog',
    'inactive',
    false,
    '{}'::jsonb,
    r.trigger_type,
    r.trigger_config
  from public.cross_agent_routines r
  where r.visibility in ('user', 'builtin', 'optional')
  on conflict do nothing;

  return new;
end;
$$;


ALTER FUNCTION "public"."auto_enroll_catalog_routines"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."auto_enroll_system_routines"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  INSERT INTO public.client_routines (
    id, client_id, routine_id, notify_channel, config,
    source, status, trigger_type, trigger_config, created_at
  )
  SELECT
    gen_random_uuid(),
    NEW.client_id,
    r.id,
    'app',
    '{}'::jsonb,
    'system',
    'active',
    r.trigger_type,
    r.trigger_config,
    now()
  FROM public.cross_agent_routines r
  WHERE r.visibility = 'system'
  ON CONFLICT DO NOTHING;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."auto_enroll_system_routines"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vector_db'
    AS $$
DECLARE
  v_cp        jsonb;
  v_ts        jsonb;
  v_seeded    int := 0;
BEGIN
  SELECT company_profile, team_structure
    INTO v_cp, v_ts
    FROM public.clientes_blu
   WHERE client_id = p_client_id;

  IF (v_cp->>'legal_name') IS NOT NULL OR (v_cp->>'industry') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF (v_cp->>'industry') IS NOT NULL AND (v_cp->>'employee_count_range') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'perfil_empresarial', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF EXISTS (
    SELECT 1 FROM vector_db.documents
     WHERE client_id = p_client_id AND source = 'onboarding.website_context'
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'posicionamento', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF jsonb_array_length(COALESCE(v_ts->'key_contacts', '[]'::jsonb)) > 0 THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'organograma', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny','shopify','vtex','nuvemshop')
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'historico_pedidos',  'partial', 'erp'),
      (p_client_id, 'catalogo_produtos',  'partial', 'erp'),
      (p_client_id, 'fluxo_caixa_diario', 'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 3;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny')
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'cadastro_fornecedores', 'partial', 'erp'),
      (p_client_id, 'controle_inventario',   'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 2;
  END IF;

  -- FIX (Mai/2026): client_data_sources.client_id é uuid (não text).
  -- Cast ::text quebrava o UPDATE e fazia a função inteira abortar em ~250ms.
  UPDATE public.client_knowledge_documents ckd
     SET status     = 'complete',
         source     = 'erp_synced',
         updated_at = now()
    FROM public.client_data_sources cds
   WHERE cds.client_id = p_client_id
     AND cds.sync_status IN ('ready','success')
     AND ckd.client_id = p_client_id
     AND ckd.document_type_id = CASE cds.resource_type
           WHEN 'orders'       THEN 'historico_pedidos'
           WHEN 'pedidos'      THEN 'historico_pedidos'
           WHEN 'products'     THEN 'catalogo_produtos'
           WHEN 'inventory'    THEN 'controle_inventario'
           WHEN 'estoque'      THEN 'controle_inventario'
           WHEN 'customers'    THEN 'ficha_cliente'
           WHEN 'clientes'     THEN 'ficha_cliente'
           WHEN 'fornecedores' THEN 'cadastro_fornecedores'
           ELSE NULL
         END
     AND ckd.status != 'complete';

  RETURN jsonb_build_object('client_id', p_client_id, 'docs_seeded', v_seeded);
END;
$$;


ALTER FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."client_routine_executions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "routine_id" "text" NOT NULL,
    "triggered_by" "text" NOT NULL,
    "trigger_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "dispatched_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "result_text" "text",
    "result_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "completed_at" timestamp with time zone,
    "worker_slug" "text",
    "heartbeat_at" timestamp with time zone,
    "failure_count" integer DEFAULT 0 NOT NULL
);


ALTER TABLE "public"."client_routine_executions" OWNER TO "postgres";


COMMENT ON COLUMN "public"."client_routine_executions"."heartbeat_at" IS 'Atualizado pelo agent_api a cada step do grafo. Reaper usa este campo para detectar execuções travadas com mais precisão.';



COMMENT ON COLUMN "public"."client_routine_executions"."failure_count" IS 'Número de tentativas falhadas desta execução específica (para retry futuro).';



CREATE OR REPLACE FUNCTION "public"."claim_routine_executions"("p_batch_size" integer DEFAULT 10) RETURNS SETOF "public"."client_routine_executions"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN QUERY
  UPDATE public.client_routine_executions
    SET status = 'executing'
  WHERE id IN (
    SELECT id
    FROM   public.client_routine_executions
    WHERE  status = 'dispatched'
    ORDER  BY dispatched_at
    LIMIT  p_batch_size
    FOR    UPDATE SKIP LOCKED
  )
  RETURNING *;
END;
$$;


ALTER FUNCTION "public"."claim_routine_executions"("p_batch_size" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."cleanup_auth_user_if_orphaned"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'auth'
    AS $$
DECLARE
  v_remaining int;
BEGIN
  IF OLD.auth_user_id IS NULL THEN
    RETURN OLD;
  END IF;

  -- Contar quantos outros clientes esse user ainda tem
  SELECT count(*) INTO v_remaining
  FROM public.client_users
  WHERE auth_user_id = OLD.auth_user_id
    AND client_id != OLD.client_id;  -- excluir o que está sendo deletado

  IF v_remaining = 0 THEN
    -- Sem outros vínculos: deletar o usuário de auth.users
    DELETE FROM auth.users WHERE id = OLD.auth_user_id;
  END IF;

  RETURN OLD;
END;
$$;


ALTER FUNCTION "public"."cleanup_auth_user_if_orphaned"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cleanup_auth_user_if_orphaned"() IS 'AFTER DELETE ON client_users. Deleta auth.users se o user não tiver mais nenhum vínculo com outro cliente (user zumbi sem tenant).';



CREATE OR REPLACE FUNCTION "public"."cleanup_credential_vault_secret"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vault'
    AS $$
BEGIN
  IF OLD.vault_key_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = OLD.vault_key_id;
  END IF;
  RETURN OLD;
END;
$$;


ALTER FUNCTION "public"."cleanup_credential_vault_secret"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cleanup_credential_vault_secret"() IS 'BEFORE DELETE ON credencial_servico_externo. Limpa o vault.secret correspondente (vault_key_id). Chamada via CASCADE quando o cliente é deletado.';



CREATE OR REPLACE FUNCTION "public"."cleanup_datasource_storage_object"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'storage'
    AS $$
DECLARE
  v_bucket text;
  v_path   text;
BEGIN
  IF OLD.storage_location IS NULL THEN
    RETURN OLD;
  END IF;

  -- Inferir bucket pelo prefixo do path
  -- Padrões conhecidos:
  --   csv_uploads/{client_id}/...    → bucket: csv_datasets
  --   drive_imports/{client_id}/...  → bucket: csv_datasets
  --   knowledge-base/... onboarding/... → bucket: knowledge-base
  IF OLD.storage_location LIKE 'csv_uploads/%' OR OLD.storage_location LIKE 'drive_imports/%' THEN
    v_bucket := 'csv_datasets';
    v_path   := OLD.storage_location;
  ELSIF OLD.storage_location LIKE 'knowledge-base/%' OR OLD.storage_location LIKE 'onboarding/%' THEN
    v_bucket := 'knowledge-base';
    v_path   := OLD.storage_location;
  ELSE
    -- Path desconhecido — não tenta deletar para evitar deleção acidental
    RETURN OLD;
  END IF;

  -- storage.protect_delete bloqueia DELETE em storage.objects a menos que este
  -- GUC esteja setado (é o mesmo mecanismo usado pela Storage API). set_config
  -- com is_local=true reverte no fim da transação.
  PERFORM set_config('storage.allow_delete_query', 'true', true);

  DELETE FROM storage.objects
  WHERE bucket_id = v_bucket AND name = v_path;

  PERFORM set_config('storage.allow_delete_query', 'false', true);

  RETURN OLD;
END;
$$;


ALTER FUNCTION "public"."cleanup_datasource_storage_object"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cleanup_datasource_storage_object"() IS 'BEFORE DELETE ON client_data_sources. Remove arquivo físico do Storage (csv_uploads/*, drive_imports/*, knowledge-base/*) quando a data source é deletada.';



CREATE OR REPLACE FUNCTION "public"."cleanup_storage_object"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'storage'
    AS $$
BEGIN
  -- Deleta o objeto físico do bucket. Ignora erro se já não existir.
  DELETE FROM storage.objects
  WHERE bucket_id = OLD.bucket
    AND name = OLD.storage_path;
  RETURN OLD;
END;
$$;


ALTER FUNCTION "public"."cleanup_storage_object"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cleanup_storage_object"() IS 'BEFORE DELETE ON uploaded_files_metadata. Remove o objeto físico do Storage quando o registro de metadata é deletado (ex: via CASCADE de cliente).';



CREATE OR REPLACE FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text" DEFAULT 'US'::"text", "p_timeout_ms" integer DEFAULT 300000, "p_credential_id" bigint DEFAULT NULL::bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id   uuid;
  v_data_source_id uuid;
  v_server_name    text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  BEGIN
    SELECT server_name INTO v_server_name
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, bigquery_table, server_name, columns, location, created_at, credential_id
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, now(), p_credential_id
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      bigquery_table = EXCLUDED.bigquery_table,
      server_name    = EXCLUDED.server_name,
      location       = EXCLUDED.location,
      columns        = '[]'::jsonb,
      credential_id  = EXCLUDED.credential_id;

    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_credential_id,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', now(), now()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      credential_id  = EXCLUDED.credential_id,
      updated_at     = now()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending'
    );

  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
  END;
END;
$$;


ALTER FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
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


ALTER FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text" DEFAULT 'US'::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id          uuid;
  v_server_name           text;
  v_vault_key_id          uuid;
  v_secret_name           text;
  v_name_uuid             uuid;
  v_existing_server_name  text;
  v_existing_vault_key_id uuid;
  v_error_msg             text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  -- p_client_id intentionally ignored — tenant ALWAYS comes from JWT.

  IF p_service_account_key IS NULL
     OR (p_service_account_key->>'type') != 'service_account'
     OR (p_service_account_key->>'project_id') IS NULL
     OR (p_service_account_key->>'private_key') IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key';
  END IF;

  BEGIN
    v_server_name := 'bigquery_' || v_my_client_id::text;

    SELECT server_name, vault_key_id
      INTO v_existing_server_name, v_existing_vault_key_id
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_existing_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    v_name_uuid   := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_name_uuid::text;

    SELECT vault.create_secret(p_service_account_key::text, v_secret_name)
      INTO v_vault_key_id;

    IF v_vault_key_id IS NULL THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    EXECUTE format(
      'CREATE SERVER IF NOT EXISTS %I FOREIGN DATA WRAPPER bigquery_wrapper OPTIONS (project_id %L, dataset_id %L, location %L, sa_key_id %L)',
      v_server_name, p_project_id, p_dataset_id, p_location, v_vault_key_id::text
    );

    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id, v_server_name, p_project_id, p_dataset_id,
      v_vault_key_id, p_location, now(), now()
    )
    ON CONFLICT (client_id) DO NOTHING;

    RETURN jsonb_build_object(
      'success',      true,
      'server_name',  v_server_name,
      'vault_key_id', v_vault_key_id
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    BEGIN EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL; END;
    IF v_vault_key_id IS NOT NULL THEN
      BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL; END;
    END IF;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;


ALTER FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") IS 'Creates a BigQuery foreign server for a client using Supabase Wrappers (bigquery_wrapper)';



CREATE TABLE IF NOT EXISTS "public"."client_routines" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "routine_id" "text" NOT NULL,
    "notify_channel" "text" DEFAULT 'app'::"text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_run_at" timestamp with time zone,
    "source" "text" DEFAULT 'catalog'::"text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "name" "text",
    "description" "text",
    "steps" "jsonb" DEFAULT '[]'::"jsonb",
    "trigger_type" "text" DEFAULT 'manual'::"text",
    "trigger_config" "jsonb" DEFAULT '{}'::"jsonb",
    "created_by_ai" boolean DEFAULT false NOT NULL,
    "consecutive_failures" integer DEFAULT 0 NOT NULL,
    CONSTRAINT "client_routines_notify_channel_check" CHECK (("notify_channel" = ANY (ARRAY['email'::"text", 'whatsapp'::"text", 'app'::"text"]))),
    CONSTRAINT "client_routines_source_check" CHECK (("source" = ANY (ARRAY['catalog'::"text", 'custom'::"text", 'system'::"text"]))),
    CONSTRAINT "client_routines_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'inactive'::"text", 'pending_approval'::"text", 'draft'::"text", 'suspended'::"text"]))),
    CONSTRAINT "client_routines_trigger_type_check" CHECK (("trigger_type" = ANY (ARRAY['manual'::"text", 'document'::"text", 'schedule'::"text", 'cron'::"text", 'event'::"text", 'numeric'::"text"])))
);


ALTER TABLE "public"."client_routines" OWNER TO "postgres";


COMMENT ON COLUMN "public"."client_routines"."status" IS 'Valores: active | inactive | suspended. suspended = circuit breaker ativado (>= 3 falhas consecutivas). Resetar com SELECT public.reset_routine_failures(client_id, routine_id).';



CREATE TABLE IF NOT EXISTS "public"."cross_agent_routines" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "trigger_domain" "text",
    "trigger_document_id" "text",
    "trigger_status" "text",
    "trigger_condition" "text",
    "steps" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "room" "text" NOT NULL,
    "config_schema" "jsonb" DEFAULT '[]'::"jsonb",
    "trigger_type" "text" DEFAULT 'manual'::"text" NOT NULL,
    "trigger_config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "visibility" "text" DEFAULT 'user'::"text",
    CONSTRAINT "cross_agent_routines_trigger_type_check" CHECK (("trigger_type" = ANY (ARRAY['manual'::"text", 'cron'::"text", 'event'::"text", 'numeric'::"text"]))),
    CONSTRAINT "cross_agent_routines_visibility_check" CHECK (("visibility" = ANY (ARRAY['builtin'::"text", 'optional'::"text", 'hidden'::"text", 'user'::"text", 'system'::"text"])))
);


ALTER TABLE "public"."cross_agent_routines" OWNER TO "postgres";


COMMENT ON COLUMN "public"."cross_agent_routines"."room" IS 'Room/domain this routine belongs to (matches rooms in the app: estrategia, agenda, clientes, financeiro, operacoes, compras, home, biblioteca). Used by get_unified_tasks() to map routines to Gantt domains.';



COMMENT ON COLUMN "public"."cross_agent_routines"."config_schema" IS 'Array of {key, label, type, default, required} describing params the client can configure for this routine.';



COMMENT ON COLUMN "public"."cross_agent_routines"."trigger_type" IS 'How this routine fires: manual (admin/user), cron (scheduled), event (hook), numeric (metric threshold).';



COMMENT ON COLUMN "public"."cross_agent_routines"."trigger_config" IS 'Trigger-specific config: {expression} for cron, {event_type} for event, {metric, threshold, window_months} for numeric.';



CREATE OR REPLACE FUNCTION "public"."cross_agent_routines"("public"."client_routines") RETURNS SETOF "public"."cross_agent_routines"
    LANGUAGE "sql" STABLE ROWS 1
    AS $_$
  select * from public.cross_agent_routines where id = $1.routine_id
$_$;


ALTER FUNCTION "public"."cross_agent_routines"("public"."client_routines") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cross_agent_routines"("public"."client_routines") IS 'Computed relationship PostgREST: substitui a FK client_routines_routine_id_fkey removida em 20260707000004 para manter o embed cross_agent_routines(...) do frontend.';



CREATE OR REPLACE FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text" DEFAULT NULL::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  UPDATE public.approval_requests
  SET status     = p_decision,
      decided_by = auth.uid()::text,
      decided_at = now(),
      payload    = payload || jsonb_build_object('reason', p_reason)
  WHERE id = p_request_id
    AND client_id = public.get_my_client_id()
    AND status = 'pending';

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'Not found or already decided');
  END IF;
  RETURN jsonb_build_object('success', true, 'status', p_decision);
END;
$$;


ALTER FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") RETURNS "void"
    LANGUAGE "sql"
    AS $$
  UPDATE public.client_insights
  SET dismissed = true, dismissed_at = now()
  WHERE id = p_insight_id
    AND client_id = public.get_my_client_id();
$$;


ALTER FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."dispatch_context_report_on_ingestion"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_cr             RECORD;
  v_in_flight      integer;
  v_cooldown_hours integer;
BEGIN
  -- Only on status transition TO 'completed'
  IF NEW.status != 'completed' OR OLD.status = 'completed' THEN
    RETURN NEW;
  END IF;

  FOR v_cr IN
    SELECT id, last_run_at, trigger_config
    FROM public.client_routines
    WHERE routine_id = 'context_report_post_ingestion'
      AND client_id  = NEW.client_id
      AND active     = true
      AND status     = 'active'
  LOOP
    -- Cooldown guard
    v_cooldown_hours := COALESCE(
      (v_cr.trigger_config->>'cooldown_hours')::integer, 1
    );
    IF v_cr.last_run_at IS NOT NULL AND
       extract(epoch FROM (now() - v_cr.last_run_at)) / 3600 < v_cooldown_hours
    THEN
      CONTINUE;
    END IF;

    -- In-flight guard
    SELECT count(*) INTO v_in_flight
    FROM public.client_routine_executions
    WHERE client_id  = NEW.client_id
      AND routine_id = 'context_report_post_ingestion'
      AND status     IN ('pending', 'dispatched', 'executing');

    IF v_in_flight > 0 THEN
      CONTINUE;
    END IF;

    -- Dispatch
    INSERT INTO public.client_routine_executions (
      id, client_id, routine_id, triggered_by, trigger_data,
      status, dispatched_at, created_at
    ) VALUES (
      gen_random_uuid(),
      NEW.client_id,
      'context_report_post_ingestion',
      'event',
      jsonb_build_object('event_type', 'ingestion_completed', 'job_id', NEW.job_id),
      'dispatched',
      now(),
      now()
    );

    -- Stamp last_run_at to enforce cooldown
    UPDATE public.client_routines
    SET last_run_at = now()
    WHERE id = v_cr.id;

  END LOOP;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."dispatch_context_report_on_ingestion"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."dispatch_routine_event"("p_routine_id" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_exec_id       uuid;
  v_now           timestamptz := now();
  v_routine_exists boolean;
  v_subscription  record;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM public.cross_agent_routines
    WHERE id = p_routine_id
      AND trigger_type = 'event'
  ) INTO v_routine_exists;

  IF NOT v_routine_exists THEN
    RAISE WARNING '[dispatch_routine_event] routine % not found or not event-triggered', p_routine_id;
    RETURN NULL;
  END IF;

  SELECT id INTO v_subscription
  FROM public.client_routines
  WHERE routine_id = p_routine_id
    AND client_id  = p_client_id
    AND active     = true
    AND status     = 'active'
  LIMIT 1;

  IF NOT FOUND THEN
    RAISE WARNING '[dispatch_routine_event] no active subscription for routine % / client %', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND status IN ('pending', 'dispatched', 'executing')
  ) THEN
    RAISE NOTICE '[dispatch_routine_event] in-flight execution exists for routine % / client % — skipping', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data, status, dispatched_at)
  VALUES
    (p_client_id, p_routine_id, 'event', p_trigger_data, 'dispatched', v_now)
  RETURNING id INTO v_exec_id;

  UPDATE public.client_routines
  SET last_run_at = v_now
  WHERE id = v_subscription.id;

  RETURN v_exec_id;
END;
$$;


ALTER FUNCTION "public"."dispatch_routine_event"("p_routine_id" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."dispatch_routine_executions"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'net'
    AS $$
DECLARE
  _url   text;
  _token text;
BEGIN
  SELECT value INTO _url
  FROM   public.app_config
  WHERE  key = 'agent_api_core_url';

  SELECT value INTO _token
  FROM   public.app_config
  WHERE  key = 'agent_api_routine_dispatch_token';

  IF _url IS NULL OR _url = '' OR _token IS NULL OR _token = '' THEN
    RAISE WARNING '[dispatch_routine_executions] app_config not configured — '
                  'set agent_api_core_url and agent_api_routine_dispatch_token '
                  'in public.app_config to enable automatic routine execution.';
    RETURN;
  END IF;

  PERFORM net.http_post(
    url                  := _url || '/internal/routines/run-dispatched',
    headers              := jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', 'Bearer ' || _token
    ),
    body                 := '{}'::jsonb,
    timeout_milliseconds := 30000
  );
END;
$$;


ALTER FUNCTION "public"."dispatch_routine_executions"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."dispatch_routine_executions"() IS 'Called by pg_cron every minute. Invokes POST /internal/routines/run-dispatched on the Python agent_api so it can (a) evaluate cron/numeric triggers and (b) claim + execute dispatched routine executions. Requires agent_api_core_url and agent_api_routine_dispatch_token in app_config.';



CREATE OR REPLACE FUNCTION "public"."drop_bigquery_fdw_server"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- Drops the FDW server and all dependent foreign tables in the fdw schema.
  -- EXECUTE is required because server name is dynamic.
  EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', OLD.server_name);
  RETURN OLD;
END;
$$;


ALTER FUNCTION "public"."drop_bigquery_fdw_server"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id uuid;
  v_server_name  text;
  v_vault_key_id uuid;
  v_error_msg    text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  -- p_client_id intentionally ignored.

  BEGIN
    SELECT server_name, vault_key_id
      INTO v_server_name, v_vault_key_id
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object('success', true, 'message', 'No BigQuery server found for this tenant');
    END IF;

    BEGIN EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL; END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL; END;
    END IF;

    DELETE FROM public.client_data_sources
     WHERE client_id = v_my_client_id AND source_type = 'bigquery';
    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;
    DELETE FROM public.bigquery_servers        WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and registry removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;


ALTER FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") IS 'Drops BigQuery foreign server and all its tables';



CREATE OR REPLACE FUNCTION "public"."enqueue_custom_routine"("p_client_routine_id" "uuid", "p_triggered_by" "text", "p_trigger_data" "jsonb" DEFAULT '{}'::"jsonb", "p_cooldown_h" integer DEFAULT 24) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_cr      record;
  v_exec_id uuid;
BEGIN
  SELECT * INTO v_cr
  FROM public.client_routines
  WHERE id = p_client_routine_id;

  IF NOT FOUND THEN RETURN NULL; END IF;

  IF v_cr.active = false OR v_cr.status <> 'active' THEN
    RETURN NULL;
  END IF;

  IF p_cooldown_h > 0 AND EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = v_cr.client_id
      AND routine_id = v_cr.id::text
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (v_cr.client_id, v_cr.id::text, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_exec_id;

  RETURN v_exec_id;
END;
$$;


ALTER FUNCTION "public"."enqueue_custom_routine"("p_client_routine_id" "uuid", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."enqueue_monthly_close"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_last_day date;
  v_today    date := current_date;
  v_enqueued integer := 0;
  v_client_id uuid;
BEGIN
  -- Calculate last day of current month
  v_last_day := (date_trunc('month', now()) + interval '1 month' - interval '1 day')::date;

  IF v_today <> v_last_day THEN
    RETURN 0;  -- not last day of month
  END IF;

  FOR v_client_id IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    IF public.enqueue_routine(
      v_client_id,
      'monthly_close',
      'cron',
      jsonb_build_object('month', to_char(now(), 'YYYY-MM')),
      -- Cooldown 25 days so it can't fire twice in one month
      600
    ) IS NOT NULL THEN
      v_enqueued := v_enqueued + 1;
    END IF;
  END LOOP;

  RETURN v_enqueued;
END;
$$;


ALTER FUNCTION "public"."enqueue_monthly_close"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb" DEFAULT '{}'::"jsonb", "p_cooldown_h" integer DEFAULT 24) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id uuid;
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.client_routines
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND (active = false OR status <> 'active')
  ) THEN
    RETURN NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (p_client_id, p_routine_id, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."enqueue_routine_for_me"("p_routine_id" "text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $_$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_is_uuid   boolean;
BEGIN
  v_is_uuid := (p_routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

  IF v_is_uuid THEN
    RETURN public.enqueue_custom_routine(
      p_routine_id::uuid,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  ELSE
    RETURN public.enqueue_routine(
      v_client_id,
      p_routine_id,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  END IF;
END;
$_$;


ALTER FUNCTION "public"."enqueue_routine_for_me"("p_routine_id" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ensure_bigquery_fdw_table"("p_client_id" "uuid", "p_cred_id" bigint) RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'fdw'
    AS $$
DECLARE
  v_server_name text;
  v_table_name  text;
  v_bq_table    text;
  v_columns     jsonb;
  v_col_defs    text;
BEGIN
  -- Resolve metadata
  SELECT bft.server_name, bft.table_name, bft.bigquery_table, bft.columns
  INTO v_server_name, v_table_name, v_bq_table, v_columns
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = p_client_id
    AND bft.credential_id = p_cred_id
  LIMIT 1;

  IF v_table_name IS NULL THEN
    RAISE EXCEPTION 'No foreign table metadata for client % / credential %', p_client_id, p_cred_id;
  END IF;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No server_name found for client % / credential %', p_client_id, p_cred_id;
  END IF;

  -- Ensure fdw schema exists
  EXECUTE 'CREATE SCHEMA IF NOT EXISTS fdw';

  -- Build column definitions from stored schema
  IF v_columns IS NOT NULL AND jsonb_array_length(v_columns) > 0 THEN
    v_col_defs := public._bq_col_defs_from_jsonb(v_columns);
  END IF;

  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    -- Fallback: single text column — allows the table to be created even without schema
    v_col_defs := '_raw text';
  END IF;

  -- Drop and recreate to pick up any schema changes
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I', v_table_name);

  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_table_name,
    v_col_defs,
    v_server_name,
    v_bq_table
  );
END;
$$;


ALTER FUNCTION "public"."ensure_bigquery_fdw_table"("p_client_id" "uuid", "p_cred_id" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ensure_client_approval_stats"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO public.client_approval_stats (client_id)
  VALUES (NEW.client_id)
  ON CONFLICT (client_id) DO NOTHING;
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."ensure_client_approval_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ensure_tenant_row"() RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_user_id text := auth.uid()::text;
  v_email   text;
  v_client_id uuid;
  v_api_key text;
BEGIN
  SELECT client_id INTO v_client_id FROM public.clientes_blu
  WHERE external_user_id = v_user_id;
  
  IF v_client_id IS NULL THEN
    SELECT email INTO v_email FROM auth.users WHERE id = auth.uid();
    v_api_key := gen_random_uuid()::text;
    
    INSERT INTO public.clientes_blu (external_user_id, nome_empresa, api_key)
    VALUES (v_user_id, COALESCE(v_email, 'Empresa'), v_api_key)
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;
  END IF;
  
  -- Ensure api_key exists (fill in for existing rows without one)
  IF v_client_id IS NOT NULL THEN
    UPDATE public.clientes_blu
    SET api_key = COALESCE(api_key, gen_random_uuid()::text)
    WHERE client_id = v_client_id AND api_key IS NULL;
  END IF;
  
  RETURN jsonb_build_object('client_id', v_client_id);
END;
$$;


ALTER FUNCTION "public"."ensure_tenant_row"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."exec_sql"("p_query" "text") RETURNS TABLE("result" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- session_user is the actual calling role, not the definer
  IF session_user NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION 'exec_sql: permission denied for role %', session_user;
  END IF;

  RETURN QUERY EXECUTE format(
    'SELECT to_jsonb(t) FROM (%s) t', p_query
  );
EXCEPTION WHEN OTHERS THEN
  RETURN QUERY SELECT jsonb_build_object('error', SQLERRM, 'detail', SQLSTATE)::JSONB;
END;
$$;


ALTER FUNCTION "public"."exec_sql"("p_query" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."expire_pending_approvals"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  _expired int := 0;
  _row record;
BEGIN
  FOR _row IN
    SELECT id, client_id, action_type, agent_slug,
           COALESCE(NULLIF(title,''), action_type) AS friendly_title
    FROM public.approval_requests
    WHERE status = 'pending'
      AND expires_at IS NOT NULL
      AND expires_at < now()
    FOR UPDATE SKIP LOCKED
  LOOP
    UPDATE public.approval_requests
    SET status     = 'expired',
        decided_at = now(),
        decided_by = 'system_ttl'
    WHERE id = _row.id;

    -- Notificar dono (in_app apenas — operacional, sem email)
    INSERT INTO public.notifications (
      client_id, type, title, body,
      agent_slug, related_entity_type, related_entity_id,
      urgency_level, channels
    ) VALUES (
      _row.client_id,
      'approval_expired',
      'Aprovação expirou sem resposta',
      format('A aprovação "%s" expirou após 48h sem decisão.', _row.friendly_title),
      COALESCE(_row.agent_slug, 'system'),
      'approval_request',
      _row.id,
      'normal',
      ARRAY['in_app']::text[]
    );

    _expired := _expired + 1;
  END LOOP;

  IF _expired > 0 THEN
    RAISE NOTICE '[approval_ttl] expired % approvals at %', _expired, now();
  END IF;

  RETURN _expired;
END;
$$;


ALTER FUNCTION "public"."expire_pending_approvals"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."expire_pending_approvals"() IS 'Marca approval_requests pendentes vencidas (expires_at < now()) como "expired" e cria notification in_app. Chamada por pg_cron a cada 10 min.';



CREATE OR REPLACE FUNCTION "public"."expire_stale_insights"("p_days_old" integer DEFAULT 30) RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_count INT;
BEGIN
  UPDATE public.client_insights
  SET dismissed_at = NOW()
  WHERE dismissed_at IS NULL
    AND created_at < NOW() - (p_days_old || ' days')::INTERVAL
    AND severity != 'critical';

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;


ALTER FUNCTION "public"."expire_stale_insights"("p_days_old" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."finalize_onboarding"() RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_client_id      uuid := public.get_my_client_id();
  v_completed_at   timestamptz;
  v_was_already    boolean := false;
  v_dispatch_exec  uuid;
BEGIN
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'finalize_onboarding: no client_id for caller (JWT sub=%)', (auth.jwt() ->> 'sub');
  END IF;

  SELECT onboarding_completed_at INTO v_completed_at
  FROM public.clientes_blu
  WHERE client_id = v_client_id;

  IF v_completed_at IS NOT NULL THEN
    v_was_already := true;
  ELSE
    UPDATE public.clientes_blu
       SET onboarding_completed_at = now(),
           updated_at = now()
     WHERE client_id = v_client_id
       AND onboarding_completed_at IS NULL
    RETURNING onboarding_completed_at INTO v_completed_at;
  END IF;

  -- Dispara routine onboarding_complete (best-effort). Antes era waitUntil
  -- na edge function, mas o frontend timeoutava no seed Langfuse e o
  -- waitUntil era abortado. Síncrono aqui resolve.
  IF NOT v_was_already THEN
    BEGIN
      -- Garante subscription ativa para a rotina de sistema onboarding_complete
      -- ANTES do dispatch. dispatch_routine_event() exige active+'active';
      -- não podemos depender do enrollment (visibility) ter deixado ativo.
      INSERT INTO public.client_routines
        (client_id, routine_id, notify_channel, active, status, source, trigger_type, trigger_config)
      SELECT
        v_client_id, r.id, 'app', true, 'active', 'system', r.trigger_type, r.trigger_config
      FROM public.cross_agent_routines r
      WHERE r.id = 'onboarding_complete'
      ON CONFLICT (client_id, routine_id) DO UPDATE SET
        active = true,
        status = 'active';

      SELECT public.dispatch_routine_event(
        'onboarding_complete',
        v_client_id,
        jsonb_build_object('event_type', 'onboarding_completed')
      ) INTO v_dispatch_exec;
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'finalize_onboarding: dispatch_routine_event failed for %: %', v_client_id, SQLERRM;
    END;
  END IF;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'onboarding_completed_at', v_completed_at,
    'was_already_completed', v_was_already,
    'routine_execution_id', v_dispatch_exec
  );
END;
$$;


ALTER FUNCTION "public"."finalize_onboarding"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."finalize_onboarding"() IS 'Marca o onboarding como concluído (clientes_blu.onboarding_completed_at) e dispara a routine onboarding_complete. Chamada pelo frontend no submit do passo 4 (Mapeamento). Idempotente.';



CREATE OR REPLACE FUNCTION "public"."fire_event_for_client"("p_event_type" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb" DEFAULT '{}'::"jsonb") RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_count            integer := 0;
  v_exec_id          uuid;
  r                  record;
  v_category_filter  text;
  v_incoming_category text;
BEGIN
  v_incoming_category := p_trigger_data->>'category';

  FOR r IN
    SELECT
      car.id            AS routine_id,
      cr.trigger_config AS client_trigger_config
    FROM public.cross_agent_routines car
    JOIN public.client_routines cr
      ON  cr.routine_id = car.id
      AND cr.client_id  = p_client_id
      AND cr.active     = true
      AND cr.status     = 'active'
    WHERE car.trigger_type              = 'event'
      AND car.trigger_config->>'event_type' = p_event_type
  LOOP
    v_category_filter := r.client_trigger_config->>'category';

    IF v_category_filter IS NOT NULL
       AND v_category_filter <> ''
       AND v_category_filter IS DISTINCT FROM v_incoming_category
    THEN
      CONTINUE;
    END IF;

    v_exec_id := public.dispatch_routine_event(r.routine_id, p_client_id, p_trigger_data);
    IF v_exec_id IS NOT NULL THEN
      v_count := v_count + 1;
    END IF;
  END LOOP;

  RETURN v_count;
END;
$$;


ALTER FUNCTION "public"."fire_event_for_client"("p_event_type" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_admin_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("aprovacoes_pendentes" bigint, "lead_time_aprovacao_h" numeric, "sla_aprovacao_perc" numeric, "documentos_pendentes" bigint, "cobertura_rotinas_perc" numeric, "frescor_dados_h" numeric, "audit_coverage_perc" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_admin_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_admin_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_result      jsonb;
  v_client_tier text;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read readiness for another client';
  END IF;

  -- Look up client tier; default to FREE if not found or NULL
  SELECT UPPER(COALESCE(tier, 'FREE'))
  INTO v_client_tier
  FROM public.clientes_blu
  WHERE client_id = p_client_id;

  v_client_tier := COALESCE(v_client_tier, 'FREE');

  WITH agent_doc_status AS (
    SELECT
      kar.agent_slug,
      kar.document_type_id,
      kar.requirement_type,
      kar.coverage_threshold,
      kdt.name            AS doc_name,
      kdt.coverage_weight,
      COALESCE(ckd.status, 'missing') AS client_doc_status,
      CASE COALESCE(ckd.status, 'missing')
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS status_score
    FROM public.knowledge_agent_requirements kar
    JOIN public.knowledge_document_types kdt
      ON  kdt.id = kar.document_type_id
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kar.document_type_id
      AND ckd.client_id        = p_client_id
  ),
  agent_scores AS (
    SELECT
      agent_slug,
      requirement_type,
      MAX(coverage_threshold) AS coverage_threshold,
      ROUND(
        SUM(status_score * coverage_weight) / NULLIF(SUM(coverage_weight), 0) * 100
      )::int AS weighted_pct,
      array_agg(doc_name ORDER BY doc_name)
        FILTER (WHERE requirement_type = 'minimum' AND client_doc_status = 'missing')
        AS missing_doc_names
    FROM agent_doc_status
    GROUP BY agent_slug, requirement_type
  ),
  agent_summary AS (
    SELECT
      s.agent_slug,
      cat.name          AS agent_name,
      cat.tier_required,
      (cea.enabled_at IS NOT NULL) AS is_enabled,
      MAX(CASE WHEN s.requirement_type = 'minimum'      THEN s.weighted_pct   ELSE 0   END) AS min_pct,
      MAX(CASE WHEN s.requirement_type = 'nice_to_have' THEN s.weighted_pct   ELSE 0   END) AS nice_pct,
      MAX(s.coverage_threshold) AS coverage_threshold,
      array_remove(
        array_agg(DISTINCT elem)
          FILTER (WHERE s.requirement_type = 'minimum'),
        NULL
      ) AS missing_names
    FROM agent_scores s
    CROSS JOIN LATERAL unnest(COALESCE(s.missing_doc_names, ARRAY[]::text[])) AS elem
    JOIN public.agent_catalog cat ON cat.slug = s.agent_slug
    LEFT JOIN public.client_enabled_agents cea
      ON cea.agent_slug = s.agent_slug AND cea.client_id = p_client_id
    GROUP BY s.agent_slug, cat.name, cat.tier_required, cea.enabled_at
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'agent_slug',       agent_slug,
      'agent_name',       agent_name,
      'tier_required',    tier_required,
      'is_enabled',       is_enabled,
      -- tier_blocked: client's subscription tier is below what this agent requires
      'tier_blocked',     CASE
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN true
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN true
                            ELSE false
                          END,
      'status',           CASE
                            -- Tier gate takes priority over document coverage
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN 'blocked'
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN 'blocked'
                            WHEN min_pct >= (coverage_threshold * 100)                                    THEN 'ready'
                            WHEN min_pct > 0                                                              THEN 'partial'
                            ELSE                                                                               'blocked'
                          END,
      'capability',       CASE WHEN nice_pct >= 70 THEN 'full' ELSE 'partial' END,
      'min_coverage_pct', min_pct,
      'nice_coverage_pct',nice_pct,
      'missing_docs',     COALESCE(to_jsonb(missing_names), '[]'::jsonb)
    ) ORDER BY agent_slug
  )
  INTO v_result
  FROM agent_summary;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


ALTER FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_agent_runs_today"() RETURNS TABLE("total" integer, "by_agent" "jsonb")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2'
    AS $$
SELECT
  COUNT(*)::INT AS total,
  JSONB_OBJECT_AGG(
    COALESCE(resource_type, 'unknown'),
    run_count
  ) AS by_agent
FROM (
  SELECT
    resource_type,
    COUNT(*)::INT AS run_count
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
    AND job_type LIKE '%agent%'
    AND DATE(created_at) = CURRENT_DATE
  GROUP BY resource_type
) subquery;
$$;


ALTER FUNCTION "public"."get_agent_runs_today"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_churn_rate_monthly"("p_client_id" "uuid", "p_window_months" integer DEFAULT 1) RETURNS TABLE("current_churn_rate" numeric, "avg_churn_rate" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_current_rate numeric;
  v_avg_rate     numeric;
  v_now          date := date_trunc('month', now())::date;
  v_prev_month   date := (v_now - interval '1 month')::date;

  v_active_last_month  bigint;
  v_churned_this_month bigint;
BEGIN
  SELECT COUNT(DISTINCT ft.customer_id)
    INTO v_active_last_month
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND ft.customer_id IS NOT NULL
     AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer;

  IF v_active_last_month = 0 THEN
    current_churn_rate := 0;
    avg_churn_rate     := 0;
    RETURN NEXT;
    RETURN;
  END IF;

  SELECT COUNT(DISTINCT prev_buyers.customer_id)
    INTO v_churned_this_month
    FROM (
      SELECT DISTINCT ft.customer_id
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND ft.customer_id IS NOT NULL
         AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
         AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer
    ) prev_buyers
   WHERE prev_buyers.customer_id NOT IN (
      SELECT DISTINCT ft2.customer_id
        FROM analytics_v2.fato_transacoes ft2
        JOIN analytics_v2.dim_datas        dd2 ON dd2.data_id = ft2.data_competencia_id
       WHERE ft2.client_id = p_client_id
         AND ft2.tipo_transacao = 'venda'
         AND ft2.customer_id IS NOT NULL
         AND dd2.ano = EXTRACT(YEAR  FROM v_now)::integer
         AND dd2.mes = EXTRACT(MONTH FROM v_now)::integer
   );

  v_current_rate := ROUND(v_churned_this_month::numeric / v_active_last_month, 4);

  WITH month_series AS (
    SELECT generate_series(1, p_window_months) AS offset_n
  ),
  month_pairs AS (
    SELECT
      (v_now - (offset_n       || ' months')::interval)::date AS m_current,
      (v_now - ((offset_n + 1) || ' months')::interval)::date AS m_prev
    FROM month_series
  ),
  monthly_churn AS (
    SELECT
      mp.m_current,
      mp.m_prev,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.customer_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_t.tipo_transacao = 'venda'
             AND prev_t.customer_id IS NOT NULL
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
        ), 0) AS base_count,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.customer_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_t.tipo_transacao = 'venda'
             AND prev_t.customer_id IS NOT NULL
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
             AND prev_t.customer_id NOT IN (
               SELECT DISTINCT cur_t.customer_id
                 FROM analytics_v2.fato_transacoes cur_t
                 JOIN analytics_v2.dim_datas        cur_dd ON cur_dd.data_id = cur_t.data_competencia_id
                WHERE cur_t.client_id = p_client_id
                  AND cur_t.tipo_transacao = 'venda'
                  AND cur_t.customer_id IS NOT NULL
                  AND cur_dd.ano = EXTRACT(YEAR  FROM mp.m_current)::integer
                  AND cur_dd.mes = EXTRACT(MONTH FROM mp.m_current)::integer
             )
        ), 0) AS churned_count
    FROM month_pairs mp
  )
  SELECT COALESCE(AVG(
    CASE WHEN base_count = 0 THEN 0
         ELSE churned_count::numeric / base_count
    END), 0)
    INTO v_avg_rate
    FROM monthly_churn;

  current_churn_rate := v_current_rate;
  avg_churn_rate     := ROUND(COALESCE(v_avg_rate, 0), 4);

  RETURN NEXT;
END;
$$;


ALTER FUNCTION "public"."get_churn_rate_monthly"("p_client_id" "uuid", "p_window_months" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_churn_rate_monthly"("p_client_id" "uuid", "p_window_months" integer) IS 'Numeric trigger metric: returns (current_churn_rate, avg_churn_rate) as fractions [0-1]. Churn = buyers in month M-1 who did not buy in month M. For spike detection set threshold > 1 (e.g. 1.5 = fires when churn is 50% above avg).';



CREATE OR REPLACE FUNCTION "public"."get_commercial_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("pedidos_periodo" bigint, "receita_periodo" numeric, "ticket_medio" numeric, "clientes_unicos" bigint, "clientes_novos" bigint, "clientes_recorrentes" bigint, "recencia_media_dias" numeric, "frequencia_media_mensal" numeric, "churn_60d_perc" numeric, "crescimento_receita_perc" numeric, "win_rate_perc" numeric, "ciclo_venda_dias" numeric, "nrr_perc" numeric, "clv" numeric, "checkout_conversion_perc" numeric, "nps" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_commercial_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_commercial_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_commercial_revenue_by_channel"() RETURNS TABLE("channel" "text", "total_revenue" numeric, "transaction_count" integer, "avg_transaction_value" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    COALESCE(ft.status, 'sem_status')::TEXT AS channel,
    SUM(ft.valor)::NUMERIC                  AS total_revenue,
    COUNT(*)::INT                           AS transaction_count,
    AVG(ft.valor)::NUMERIC                  AS avg_transaction_value
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
  WHERE ft.client_id = public.get_my_client_id()
    AND ft.tipo_transacao = 'venda'
    AND dd.data >= (CURRENT_DATE - INTERVAL '90 days')::date
  GROUP BY ft.status
  ORDER BY total_revenue DESC;
END;
$$;


ALTER FUNCTION "public"."get_commercial_revenue_by_channel"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_commercial_top_clients"() RETURNS TABLE("client_id" bigint, "cliente_nome" "text", "total_volume" numeric, "total_revenue" numeric, "last_purchase" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.customer_id,
    dc.nome::TEXT,
    COUNT(ft.transacao_id)::NUMERIC AS total_volume,
    SUM(ft.valor)::NUMERIC          AS total_revenue,
    MAX(ft.created_at)              AS last_purchase
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON ft.customer_id = dc.customer_id
   AND ft.client_id   = dc.client_id
  WHERE ft.client_id = public.get_my_client_id()
    AND ft.tipo_transacao = 'venda'
  GROUP BY dc.customer_id, dc.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$$;


ALTER FUNCTION "public"."get_commercial_top_clients"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vault'
    AS $$
DECLARE
  v_vault_key uuid;
  v_secret    text;
BEGIN
  SELECT vault_key_id INTO v_vault_key
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_vault_key IS NULL THEN
    RAISE EXCEPTION 'credencial_servico_externo % has no vault_key_id', p_credential_id;
  END IF;

  SELECT decrypted_secret INTO v_secret
  FROM vault.decrypted_secrets
  WHERE id = v_vault_key;

  IF v_secret IS NULL THEN
    RAISE EXCEPTION 'vault entry % not found for credential %', v_vault_key, p_credential_id;
  END IF;

  RETURN v_secret::jsonb;
END;
$$;


ALTER FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) IS 'SECURITY DEFINER helper for the etl-bigquery-ingest edge function. Returns the decrypted service_account_json for a credencial_servico_externo row. service_role only — never expose to authenticated/anon.';



CREATE OR REPLACE FUNCTION "public"."get_customer_segments"("p_client_id" "uuid") RETURNS TABLE("nivel_cluster" "text", "count" bigint, "avg_ticket" numeric, "revenue_share" numeric)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public', 'pg_catalog'
    AS $$
  SELECT
    COALESCE(dc.nivel_cluster, 'Indefinido')        AS nivel_cluster,
    COUNT(*)                                         AS count,
    ROUND(AVG(dc.ticket_medio)::numeric, 2)          AS avg_ticket,
    ROUND(
      SUM(dc.receita_total) / NULLIF(SUM(SUM(dc.receita_total)) OVER (), 0) * 100,
      2
    )                                                AS revenue_share
  FROM analytics_v2.dim_clientes dc
  WHERE dc.client_id = p_client_id
  GROUP BY dc.nivel_cluster
  ORDER BY SUM(dc.receita_total) DESC;
$$;


ALTER FUNCTION "public"."get_customer_segments"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_finance_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("receita_liquida" numeric, "custo_total" numeric, "despesas_total" numeric, "margem_bruta_perc" numeric, "margem_operacional_perc" numeric, "ticket_medio" numeric, "receita_yoy_perc" numeric, "crescimento_receita_perc" numeric, "total_pedidos" bigint, "dso_dias" numeric, "dpo_dias" numeric, "ccc_dias" numeric, "working_capital_ratio" numeric, "burn_rate_mensal" numeric, "runway_meses" numeric, "cash_flow_30d" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_finance_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_finance_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_inventory_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("skus_ativos" bigint, "skus_total" bigint, "quantidade_vendida_periodo" numeric, "receita_skus_periodo" numeric, "giro_estimado" numeric, "ticket_medio_sku" numeric, "cobertura_top20_perc" numeric, "stockout_rate_perc" numeric, "crescimento_quantidade_perc" numeric, "dio_dias" numeric, "cobertura_dias" numeric, "fill_rate_perc" numeric, "sell_through_perc" numeric, "gmroi" numeric, "acuracidade_perc" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_inventory_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_inventory_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vector_db'
    AS $$
DECLARE
  v_result jsonb;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read coverage for another client';
  END IF;

  WITH doc_status AS (
    SELECT
      kdt.id              AS document_type_id,
      kdt.domain_id,
      kdt.subdomain_id,
      kdt.name,
      kdt.type,
      kdt.status          AS doc_status,
      kdt.coverage_weight,
      kdt.tags,
      kdt.consumed_by,
      COALESCE(ckd.status, 'missing') AS client_status
    FROM public.knowledge_document_types kdt
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kdt.id
      AND ckd.client_id        = p_client_id
  ),
  weighted AS (
    SELECT
      domain_id,
      subdomain_id,
      document_type_id,
      name,
      doc_status,
      client_status,
      tags,
      consumed_by,
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END AS effective_weight,
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END * CASE client_status
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS earned_weight
    FROM doc_status
  ),
  group_scores AS (
    SELECT
      domain_id,
      subdomain_id,
      ROUND(
        CASE WHEN SUM(effective_weight) = 0 THEN 0
             ELSE SUM(earned_weight) / SUM(effective_weight)
        END * 100
      )::int AS coverage_pct,
      jsonb_agg(
        jsonb_build_object(
          'id',            document_type_id,
          'name',          name,
          'type',          doc_status,
          'client_status', client_status,
          'tags',          tags,
          'consumed_by',   consumed_by
        ) ORDER BY document_type_id
      ) AS documents
    FROM weighted
    GROUP BY domain_id, subdomain_id
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'domain_id',    domain_id,
      'subdomain_id', subdomain_id,
      'coverage_pct', coverage_pct,
      'is_covered',   (coverage_pct >= 60),
      'documents',    documents
    ) ORDER BY domain_id, COALESCE(subdomain_id, '')
  )
  INTO v_result
  FROM group_scores;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


ALTER FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_marketing_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("novos_clientes_periodo" bigint, "receita_novos_clientes" numeric, "conversao_campanha_perc" numeric, "engajamento_whatsapp_perc" numeric, "taxa_optout_perc" numeric, "cac" numeric, "ltv_cac_ratio" numeric, "roas" numeric, "ctr_perc" numeric, "cac_payback_meses" numeric, "share_of_voice_perc" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_marketing_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_marketing_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_client_id"() RETURNS "uuid"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  SELECT COALESCE(
    -- 1. app_metadata (backend-authoritative)
    (auth.jwt() -> 'app_metadata' ->> 'client_id')::uuid,
    -- 2. user_metadata (social/onboarding path)
    (auth.jwt() -> 'user_metadata' ->> 'client_id')::uuid,
    -- 3. DB lookup (legacy accounts without JWT claim)
    (SELECT client_id
     FROM public.clientes_blu
     WHERE external_user_id = (auth.jwt() ->> 'sub')
     LIMIT 1)
  );
$$;


ALTER FUNCTION "public"."get_my_client_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_context_metrics"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("dimension" "text", "kpi" "text", "label" "text", "unit" "text", "current_value" numeric, "prev_month_value" numeric, "avg_6m" numeric, "mom_pct" numeric, "vs_6m_avg_pct" numeric, "streak_months" integer)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT *
  FROM analytics_v2.get_context_metrics_for_client(
    (SELECT client_id FROM public.clientes_blu
     WHERE external_user_id = auth.uid()::text
     LIMIT 1),
    p_period
  );
$$;


ALTER FUNCTION "public"."get_my_context_metrics"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_dashboard_kpis"() RETURNS TABLE("dimension" "text", "slot_index" integer, "slug" "text", "label" "text", "unit" "text", "formula" "text", "data_status" "text", "tier_required" "text", "is_enabled" boolean)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  kc.dimension,
  ROW_NUMBER() OVER (PARTITION BY kc.dimension ORDER BY COALESCE(kc.sort_order, 999)) AS slot_index,
  kc.slug,
  kc.label,
  kc.unit,
  kc.formula,
  kc.data_status,
  kc.tier_required,
  COALESCE(ck.slug IS NOT NULL, FALSE) AS is_enabled
FROM public.kpi_catalog kc
LEFT JOIN public.client_dimension_kpis ck
  ON ck.slug = kc.slug
  AND ck.client_id = public.get_my_client_id()
  AND ck.dimension = kc.dimension
ORDER BY kc.dimension, COALESCE(kc.sort_order, 999);
$$;


ALTER FUNCTION "public"."get_my_dashboard_kpis"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_insights"("p_limit" integer DEFAULT 5, "p_status" "text" DEFAULT 'active'::"text") RETURNS TABLE("id" "uuid", "run_date" timestamp with time zone, "dimension" "text", "kpi" "text", "severity" "text", "title" "text", "observation" "text", "recommendation" "text", "metric_value" numeric, "baseline_value" numeric, "variance_pct" numeric, "status" "text", "created_at" timestamp with time zone)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at)  AS run_date,
  ci.dimension,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')                 AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                       AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_insights"("p_limit" integer DEFAULT 5, "p_status" "text" DEFAULT 'active'::"text", "p_room" "text" DEFAULT NULL::"text") RETURNS TABLE("id" "uuid", "run_date" timestamp with time zone, "room" "text", "kpi" "text", "severity" "text", "title" "text", "observation" "text", "recommendation" "text", "metric_value" numeric, "baseline_value" numeric, "variance_pct" numeric, "status" "text", "created_at" timestamp with time zone)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at) AS run_date,
  ci.room,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')               AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                     AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
  AND (p_room IS NULL OR ci.room = p_room)
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text", "p_room" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer DEFAULT 12) RETURNS TABLE("current_month_count" bigint, "avg_monthly_count" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_current bigint;
  v_total   bigint;
BEGIN
  SELECT count(*) INTO v_current
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= 30;

  SELECT count(*) INTO v_total
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= (p_window_months * 30);

  current_month_count := COALESCE(v_current, 0);
  avg_monthly_count   := ROUND(COALESCE(v_total, 0)::numeric / GREATEST(p_window_months, 1), 2);

  RETURN NEXT;
END;
$$;


ALTER FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_nps_score"("p_window_days" integer DEFAULT 90) RETURNS TABLE("score" numeric, "total_responses" bigint, "promoters" bigint, "passives" bigint, "detractors" bigint)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  CASE
    WHEN COUNT(*) > 0
    THEN ROUND(
      ((COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::NUMERIC -
        COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::NUMERIC) /
       COUNT(*)::NUMERIC * 100), 1)
    ELSE NULL::NUMERIC
  END AS score,
  COUNT(*)::BIGINT AS total_responses,
  COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::BIGINT AS promoters,
  COALESCE(SUM(CASE WHEN score >= 7 AND score <= 8 THEN 1 ELSE 0 END), 0)::BIGINT AS passives,
  COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::BIGINT AS detractors
FROM public.nps_responses
WHERE client_id = public.get_my_client_id()
  AND created_at >= CURRENT_TIMESTAMP - (p_window_days || ' days')::INTERVAL;
$$;


ALTER FUNCTION "public"."get_nps_score"("p_window_days" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_pedidos_monthly_rate"("p_client_id" "uuid", "p_window_months" integer DEFAULT 1) RETURNS TABLE("current_pedidos" numeric, "avg_pedidos" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_current bigint;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current month order count
  SELECT COALESCE(COUNT(DISTINCT ft.transacao_id), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  -- Average monthly order count over prior window
  SELECT COALESCE(AVG(monthly_count), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, COUNT(DISTINCT ft.transacao_id) AS monthly_count
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_pedidos := v_current::numeric;
  avg_pedidos     := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;
$$;


ALTER FUNCTION "public"."get_pedidos_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_pedidos_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) IS 'Numeric trigger metric: returns (current_pedidos, avg_pedidos). Counts distinct transacao_id per calendar month.';



CREATE OR REPLACE FUNCTION "public"."get_pendencias"() RETURNS TABLE("kind" "text", "title" "text", "severity" "text", "occurred_at" timestamp with time zone, "target_route" "text")
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
SELECT
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync'  THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl'  THEN 'etl_issue'
    ELSE 'system_issue'
  END AS kind,
  INITCAP(REPLACE(rj.job_type, '_', ' ')) || ': ' || COALESCE(rj.resource_type, 'Unknown') AS title,
  CASE
    WHEN rj.status = 'failed'  THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,
  rj.created_at AS occurred_at,
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type IN ('bigquery_sync', 'analytics_etl') THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route
FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;
$$;


ALTER FUNCTION "public"."get_pendencias"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_platform_google_oauth_config"() RETURNS "jsonb"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT decrypted_secret::jsonb FROM vault.decrypted_secrets
  WHERE name = 'google_oauth_config' LIMIT 1;
$$;


ALTER FUNCTION "public"."get_platform_google_oauth_config"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_recent_activity"("p_limit" integer DEFAULT 10) RETURNS TABLE("kind" "text", "title" "text", "subtitle" "text", "occurred_at" timestamp with time zone, "severity" "text")
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  CASE
    WHEN action = 'CREATE' THEN 'ingestion'
    WHEN action = 'UPDATE' THEN 'agent_session'
    WHEN action = 'DELETE' THEN 'error'
    ELSE 'info'
  END AS kind,
  UPPER(entity_type) || ' ' || action AS title,
  (payload->>'description')::TEXT AS subtitle,
  created_at AS occurred_at,
  CASE
    WHEN action = 'DELETE' THEN 'error'
    WHEN action = 'UPDATE' THEN 'warning'
    ELSE 'info'
  END AS severity
FROM public.audit_log
WHERE client_id = public.get_my_client_id()
ORDER BY created_at DESC
LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_recent_activity"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_recent_transactions"("p_client_id" "uuid", "p_limit" integer DEFAULT 10) RETURNS TABLE("id" "text", "customer_id" bigint, "nome" "text", "descricao" "text", "valor" numeric, "data" timestamp with time zone, "status" "text")
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT
    ft.transacao_id,
    ft.customer_id,
    COALESCE(dc.nome, 'Cliente')        AS nome,
    COALESCE(ft.documento, 'Transação') AS descricao,
    ft.valor,
    ft.created_at                       AS data,
    ft.status
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.customer_id = ft.customer_id
   AND dc.client_id   = ft.client_id
  WHERE ft.client_id = p_client_id
    AND ft.tipo_transacao = 'venda'
  ORDER BY ft.created_at DESC
  LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_recent_transactions"("p_client_id" "uuid", "p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_revenue_monthly_rate"("p_client_id" "uuid", "p_window_months" integer DEFAULT 1) RETURNS TABLE("current_month_revenue" numeric, "avg_monthly_revenue" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  SELECT COALESCE(SUM(ft.valor), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND dd.ano  = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes  = EXTRACT(MONTH FROM v_now)::integer;

  SELECT COALESCE(AVG(monthly_total), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, SUM(ft.valor) AS monthly_total
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_month_revenue := v_current;
  avg_monthly_revenue   := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;
$$;


ALTER FUNCTION "public"."get_revenue_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_revenue_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) IS 'Numeric trigger metric: returns (current_month_revenue, avg_monthly_revenue). Fires when current < threshold * avg (e.g. threshold=0.85 → queda > 15%).';



CREATE OR REPLACE FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer DEFAULT 10) RETURNS TABLE("key" "text", "value" "jsonb", "created_at" timestamp with time zone, "updated_at" timestamp with time zone)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
    SELECT key, value, created_at, updated_at
    FROM public.shared_business_memory
    WHERE entity_type = 'routine'
      AND entity_name = p_routine_id
    ORDER BY updated_at DESC
    LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer) IS 'Retorna os últimos N checkpoints de uma rotina para debugging. Ordenado por updated_at DESC. Útil para inspecionar o histórico de execução.';



CREATE OR REPLACE FUNCTION "public"."get_supply_indicators"("p_period" "text" DEFAULT '30d'::"text") RETURNS TABLE("rfqs_abertas" bigint, "rfqs_enviadas" bigint, "rfqs_respondidas" bigint, "taxa_resposta_perc" numeric, "tempo_resposta_medio_h" numeric, "pos_aprovadas" bigint, "pos_pendentes_aprovacao" bigint, "spend_periodo" numeric, "fornecedores_ativos" bigint, "concentracao_top_perc" numeric, "cycle_time_medio_h" numeric, "cost_savings_perc" numeric, "ppv" numeric, "otif_perc" numeric, "lead_time_medio_dias" numeric, "maverick_spend_perc" numeric, "spend_under_management_perc" numeric, "period" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT * FROM analytics_v2.get_supply_indicators(p_period);
$$;


ALTER FUNCTION "public"."get_supply_indicators"("p_period" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_ticket_medio_monthly_rate"("p_client_id" "uuid", "p_window_months" integer DEFAULT 1) RETURNS TABLE("current_ticket" numeric, "avg_ticket" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  SELECT COALESCE(
           CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
           END, 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  SELECT COALESCE(AVG(monthly_ticket), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes,
             CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                  ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
             END AS monthly_ticket
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_ticket := ROUND(COALESCE(v_current, 0), 2);
  avg_ticket     := ROUND(COALESCE(v_avg,     0), 2);

  RETURN NEXT;
END;
$$;


ALTER FUNCTION "public"."get_ticket_medio_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_ticket_medio_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) IS 'Numeric trigger metric: returns (current_ticket, avg_ticket). Ticket = total revenue / distinct orders in the month.';



CREATE OR REPLACE FUNCTION "public"."get_top_customers"("p_client_id" "uuid", "p_limit" integer DEFAULT 10) RETURNS TABLE("customer_id" bigint, "nome" "text", "nivel_cluster" "text", "total_purchases" bigint, "last_purchase_at" timestamp with time zone, "avg_ticket" numeric)
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
  SELECT
    dc.customer_id,
    dc.nome,
    dc.nivel_cluster,
    dc.total_pedidos      AS total_purchases,
    dc.data_ultima_compra AS last_purchase_at,
    ROUND(dc.ticket_medio::numeric, 2) AS avg_ticket
  FROM analytics_v2.dim_clientes dc
  WHERE dc.client_id = p_client_id
  ORDER BY dc.receita_total DESC
  LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_top_customers"("p_client_id" "uuid", "p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") RETURNS TABLE("task_id" "text", "title" "text", "domain" "text", "start_date" "date", "due_date" "date", "status" "text", "source" "text", "schedule_cron" "text")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN QUERY
  SELECT * FROM (
    -- Approval requests (decisões pendentes)
    SELECT
      'apr_' || ar.id::text           AS task_id,
      ar.title                         AS title,
      CASE ar.agent_slug
        WHEN 'compras'    THEN 'Compras'
        WHEN 'financeiro' THEN 'Financeiro'
        WHEN 'agenda'     THEN 'Agenda'
        WHEN 'documentos' THEN 'Documentos'
        WHEN 'estrategia' THEN 'Estratégia'
        WHEN 'clientes'   THEN 'Clientes'
        ELSE 'Estratégia'
      END                              AS domain,
      ar.created_at::date              AS start_date,
      COALESCE(ar.scheduled_for::date, (ar.created_at + interval '7 days')::date) AS due_date,
      ar.status                        AS status,
      'approval'::text                 AS source,
      NULL::text                       AS schedule_cron
    FROM public.approval_requests ar
    WHERE ar.client_id = p_client_id AND ar.status = 'pending'

    UNION ALL

    -- Rotinas ativas do cliente
    -- Para rotinas cron: start_date = hoje (próxima ocorrência estimada), due_date = null (pin)
    -- Para rotinas event/manual: start_date = last_run_at, due_date = null
    SELECT
      'rtn_' || cr.id::text,
      COALESCE(NULLIF(cr.name, ''), car.name, cr.routine_id),
      CASE car.room
        WHEN 'compras'    THEN 'Compras'
        WHEN 'financeiro' THEN 'Financeiro'
        WHEN 'agenda'     THEN 'Agenda'
        WHEN 'documentos' THEN 'Documentos'
        WHEN 'estrategia' THEN 'Estratégia'
        WHEN 'clientes'   THEN 'Clientes'
        WHEN 'operacoes'  THEN 'Compras'
        WHEN 'home'       THEN 'Estratégia'
        ELSE 'Estratégia'
      END,
      -- start_date: para cron usa hoje como ancora; para event usa last_run_at ou amanhã
      CASE
        WHEN cr.trigger_type = 'cron' THEN CURRENT_DATE
        ELSE COALESCE(cr.last_run_at::date, CURRENT_DATE + 1)
      END AS start_date,
      -- due_date: null = pin pontual, sem barra de duração
      NULL::date AS due_date,
      CASE WHEN cr.active THEN 'active' ELSE 'paused' END,
      'routine'::text,
      -- schedule_cron: expressão cron para o frontend gerar ocorrências periódicas
      CASE
        WHEN cr.trigger_type = 'cron' THEN cr.trigger_config->>'expression'
        ELSE NULL
      END AS schedule_cron
    FROM public.client_routines cr
    LEFT JOIN public.cross_agent_routines car ON car.id = cr.routine_id
    WHERE cr.client_id = p_client_id AND cr.active = true
  ) t
  ORDER BY t.start_date ASC NULLS LAST;
END;
$$;


ALTER FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") IS 'Retorna tarefas unificadas (approvals + routines) para o Gantt. 
   schedule_cron: expressão cron para rotinas periódicas (o frontend gera pins múltiplos).
   due_date=null em rotinas indica pin pontual (sem barra de duração).
   Atualizado: 2026-05-22 — adicionado schedule_cron, corrigido shape de rotinas.';



CREATE OR REPLACE FUNCTION "public"."get_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text" DEFAULT NULL::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    AS $$
DECLARE
  v_row       public.integration_tokens%ROWTYPE;
  v_decrypted text;
BEGIN
  SELECT * INTO v_row FROM public.integration_tokens
  WHERE client_id = p_client_id
    AND provider  = p_provider
    AND (p_account_email IS NULL OR account_email = lower(p_account_email))
  ORDER BY is_default DESC, updated_at DESC LIMIT 1;

  IF NOT FOUND OR v_row.vault_secret_name IS NULL THEN RETURN NULL; END IF;

  SELECT decrypted_secret INTO v_decrypted
  FROM vault.decrypted_secrets WHERE name = v_row.vault_secret_name;

  IF v_decrypted IS NULL THEN RETURN NULL; END IF;

  RETURN (v_decrypted::jsonb) || jsonb_build_object(
    'account_email', v_row.account_email,
    'token_type',    v_row.token_type,
    'scopes',        to_jsonb(v_row.scopes),
    'metadata',      v_row.metadata,
    'is_default',    v_row.is_default
  );
END;
$$;


ALTER FUNCTION "public"."get_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_new_auth_user"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid;
  v_api_key text;
BEGIN
  -- Generate a fresh API key
  v_api_key := gen_random_uuid()::text;
  
  -- Insert or update: if row exists (via external_user_id), keep existing api_key
  -- Otherwise create with new api_key
  INSERT INTO public.clientes_blu (
    external_user_id,
    api_key,
    nome_empresa,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id::text,
    v_api_key,
    COALESCE(NEW.email, 'Empresa'),
    now(),
    now()
  )
  ON CONFLICT (external_user_id) DO NOTHING
  RETURNING client_id INTO v_client_id;

  -- If row already existed (conflict), get its client_id
  IF v_client_id IS NULL THEN
    SELECT client_id INTO v_client_id FROM public.clientes_blu
    WHERE external_user_id = NEW.id::text;
  END IF;

  -- Log the creation
  IF v_client_id IS NOT NULL THEN
    INSERT INTO public.audit_log (
      client_id,
      actor_id,
      action,
      entity_type,
      payload
    ) VALUES (
      v_client_id,
      NEW.id::text,
      'tenant_auto_created',
      'clientes_blu',
      jsonb_build_object('email', NEW.email, 'api_key_generated', true)
    );
  END IF;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_new_auth_user"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_new_auth_user_auto_confirm"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
begin
  if new.email_confirmed_at is null then
    new.email_confirmed_at := now();
  end if;
  return new;
end;
$$;


ALTER FUNCTION "public"."handle_new_auth_user_auto_confirm"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_onboarded_client"() RETURNS boolean
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_client_id     uuid := public.get_my_client_id();
  v_completed_at  timestamptz;
  v_created_at    timestamptz;
BEGIN
  IF v_client_id IS NULL THEN
    RETURN false;
  END IF;

  -- Sinal 1: onboarding explicitamente completado
  SELECT onboarding_completed_at, created_at
  INTO   v_completed_at, v_created_at
  FROM   public.clientes_blu
  WHERE  client_id = v_client_id;

  IF v_completed_at IS NOT NULL THEN
    RETURN true;
  END IF;

  -- Sinal 2: cliente possui fontes de dados conectadas
  IF EXISTS (
    SELECT 1 FROM public.client_data_sources
    WHERE  client_id = v_client_id
    LIMIT  1
  ) THEN
    RETURN true;
  END IF;

  -- Sinal 3: agentes configurados E conta existe ha mais de 1 hora
  IF v_created_at IS NOT NULL
     AND v_created_at < now() - interval '1 hour'
     AND EXISTS (
       SELECT 1 FROM public.client_enabled_agents
       WHERE  client_id = v_client_id
       LIMIT  1
     )
  THEN
    RETURN true;
  END IF;

  RETURN false;
END;
$$;


ALTER FUNCTION "public"."is_onboarded_client"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."is_onboarded_client"() IS 'Retorna true se o cliente JWT atual deve ser considerado onboarded. Usa onboarding_completed_at, data_sources, e enabled_agents como sinais. Centraliza a logica para evitar duplicacao frontend/backend.';



CREATE OR REPLACE FUNCTION "public"."list_due_report_schedules"() RETURNS TABLE("schedule_id" "uuid", "client_id" "uuid", "name" "text", "report_type" "text", "cron_expr" "text")
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.client_id,
    s.name,
    s.report_type,
    s.cron_expr
  FROM public.report_schedules s
  WHERE s.active = TRUE
    AND s.next_run_at <= NOW()
  ORDER BY s.next_run_at ASC;
END;
$$;


ALTER FUNCTION "public"."list_due_report_schedules"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_inbox_threads"("p_limit" integer DEFAULT 50) RETURNS TABLE("id" "uuid", "client_id" "uuid", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "message_count" integer, "last_message_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.client_id,
    c.created_at,
    c.updated_at,
    (SELECT COUNT(*)::INT FROM public.messages m WHERE m.session_id = c.id) as message_count,
    (SELECT MAX(m.created_at) FROM public.messages m WHERE m.session_id = c.id) as last_message_at
  FROM public.conversa c
  WHERE c.client_id = public.get_my_client_id()
  ORDER BY c.updated_at DESC
  LIMIT p_limit;
END;
$$;


ALTER FUNCTION "public"."list_inbox_threads"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_kpi_catalog"("p_dimension" "text" DEFAULT NULL::"text", "p_only_enabled" boolean DEFAULT false) RETURNS TABLE("slug" "text", "dimension" "text", "label" "text", "unit" "text", "data_status" "text", "sort_order" integer, "is_default" boolean, "default_dimension_rank" integer, "is_enabled" boolean)
    LANGUAGE "sql" STABLE
    AS $$
  SELECT
    k.slug, k.dimension, k.label, k.unit, k.data_status, k.sort_order,
    false AS is_default,
    NULL::int AS default_dimension_rank,
    (EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id()
        AND ck.slug = k.slug
    )) AS is_enabled
  FROM public.kpi_catalog k
  WHERE (p_dimension IS NULL OR k.dimension = p_dimension)
    AND (NOT p_only_enabled OR EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id() AND ck.slug = k.slug
    ))
  ORDER BY k.sort_order, k.slug;
$$;


ALTER FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."approval_requests" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "requested_by" "text",
    "action_type" "text" NOT NULL,
    "payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "decided_by" "text",
    "decided_at" timestamp with time zone,
    "expires_at" timestamp with time zone DEFAULT ("now"() + '48:00:00'::interval),
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "agent_slug" "text",
    "priority" "text" DEFAULT 'normal'::"text",
    "title" "text",
    "insight_text" "text",
    "snooze_until" timestamp with time zone,
    "snooze_count" integer DEFAULT 0,
    "scheduled_for" timestamp with time zone,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "session_id" "text",
    "tool_call_id" "text",
    "body" "text",
    "assigned_role" "text" DEFAULT 'owner'::"text",
    "metadata" "jsonb",
    CONSTRAINT "approval_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text", 'cancelled'::"text", 'expired'::"text"])))
);


ALTER TABLE "public"."approval_requests" OWNER TO "postgres";


COMMENT ON COLUMN "public"."approval_requests"."assigned_role" IS 'Role responsible for handling this approval: owner | manager | admin. Used to route routine_activation and other privileged approvals to the right user tier.';



COMMENT ON COLUMN "public"."approval_requests"."metadata" IS 'Optional artifact metadata: {artifact_type, artifact_id, artifact_url}. Written by channels.create_alert and channels.request_document_review.';



CREATE OR REPLACE FUNCTION "public"."list_pending_approvals"() RETURNS SETOF "public"."approval_requests"
    LANGUAGE "sql" STABLE
    AS $$
  SELECT * FROM public.approval_requests
  WHERE client_id = public.get_my_client_id()
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
  ORDER BY created_at DESC;
$$;


ALTER FUNCTION "public"."list_pending_approvals"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_report_runs"("p_limit" integer DEFAULT 50) RETURNS TABLE("id" "uuid", "schedule_id" "uuid", "status" "text", "output_url" "text", "error" "text", "started_at" timestamp with time zone, "completed_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.schedule_id,
    r.status,
    r.output_url,
    r.error,
    r.started_at,
    r.completed_at
  FROM public.report_runs r
  WHERE r.client_id = public.get_my_client_id()
  ORDER BY COALESCE(r.started_at, r.completed_at) DESC
  LIMIT p_limit;
END;
$$;


ALTER FUNCTION "public"."list_report_runs"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_report_schedules"() RETURNS TABLE("id" "uuid", "name" "text", "report_type" "text", "cron_expr" "text", "active" boolean, "next_run_at" timestamp with time zone, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.name,
    s.report_type,
    s.cron_expr,
    s.active,
    s.next_run_at,
    s.created_at
  FROM public.report_schedules s
  WHERE s.client_id = public.get_my_client_id()
  ORDER BY s.next_run_at ASC;
END;
$$;


ALTER FUNCTION "public"."list_report_schedules"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_result    jsonb;
BEGIN
  UPDATE public.clientes_blu
  SET onboarding_state = onboarding_state || p_patch,
      updated_at       = now()
  WHERE client_id = v_client_id
  RETURNING onboarding_state INTO v_result;
  RETURN v_result;
END;
$$;


ALTER FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id  uuid;
  v_caller_role   text;
  v_row           RECORD;
  v_secret_name   text;
  v_secret_uuid   uuid;
  v_vault_key_id  uuid;
  v_tipo_norm     text;
BEGIN
  -- AuthZ: caller is the tenant owner OR service_role.
  v_caller_role  := COALESCE(auth.jwt() ->> 'role', '');
  v_my_client_id := public.get_my_client_id();

  SELECT id, client_id, tipo, tipo_servico, credenciais, vault_key_id
    INTO v_row
    FROM public.credencial_servico_externo
   WHERE id = p_credential_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'credential not found');
  END IF;

  IF v_caller_role <> 'service_role' AND v_row.client_id <> v_my_client_id THEN
    RAISE EXCEPTION 'access denied for credential %', p_credential_id
      USING ERRCODE = '42501';
  END IF;

  -- Idempotency
  IF v_row.vault_key_id IS NOT NULL THEN
    RETURN jsonb_build_object(
      'success', true,
      'credential_id', v_row.id,
      'vault_key_id', v_row.vault_key_id,
      'migrated', false,
      'message', 'already in vault'
    );
  END IF;

  IF v_row.credenciais IS NULL OR v_row.credenciais = '{}'::jsonb THEN
    RETURN jsonb_build_object(
      'success', false,
      'credential_id', v_row.id,
      'error', 'nothing to migrate: credenciais is empty and vault_key_id is null'
    );
  END IF;

  -- Build a secret name consistent with create_bigquery_server convention.
  v_tipo_norm   := lower(COALESCE(v_row.tipo, v_row.tipo_servico, 'credential'));
  v_secret_uuid := gen_random_uuid();
  v_secret_name := v_tipo_norm || '_credential_' || v_secret_uuid::text;

  -- Push to vault
  SELECT vault.create_secret(v_row.credenciais::text, v_secret_name)
    INTO v_vault_key_id;

  IF v_vault_key_id IS NULL THEN
    RAISE EXCEPTION 'vault.create_secret returned NULL for credential %', v_row.id;
  END IF;

  -- Atomically flip the row: set vault_key_id, clear plaintext.
  UPDATE public.credencial_servico_externo
     SET vault_key_id = v_vault_key_id,
         credenciais  = '{}'::jsonb,
         updated_at   = now()
   WHERE id = v_row.id
     AND vault_key_id IS NULL;  -- defensive against race

  IF NOT FOUND THEN
    -- Lost the race: another caller migrated first. Roll back our secret.
    BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
    EXCEPTION WHEN OTHERS THEN NULL; END;
    SELECT vault_key_id INTO v_vault_key_id
      FROM public.credencial_servico_externo WHERE id = v_row.id;
    RETURN jsonb_build_object(
      'success', true,
      'credential_id', v_row.id,
      'vault_key_id', v_vault_key_id,
      'migrated', false,
      'message', 'concurrent migration won the race'
    );
  END IF;

  RETURN jsonb_build_object(
    'success', true,
    'credential_id', v_row.id,
    'vault_key_id', v_vault_key_id,
    'migrated', true
  );
END;
$$;


ALTER FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) IS 'Idempotent: moves credencial_servico_externo.credenciais (plaintext jsonb) into vault.secrets and clears the plaintext column. Re-running on an already-migrated credential is a no-op. Never returns the secret content. Authorized for the tenant owner or service_role.';



CREATE OR REPLACE FUNCTION "public"."normalize_shared_memory_link"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.link_type := lower(trim(NEW.link_type));
    NEW.source_entity_name := lower(trim(NEW.source_entity_name));
    NEW.target_entity_name := lower(trim(NEW.target_entity_name));
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."normalize_shared_memory_link"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."notify_routine_suspended"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  _routine_name text;
BEGIN
  -- Apenas transições para 'suspended' (não re-notifica se já estava)
  IF NEW.status <> 'suspended' OR OLD.status = 'suspended' THEN
    RETURN NEW;
  END IF;

  -- Nome amigável: fallback p/ routine_id se name vazio
  _routine_name := COALESCE(NULLIF(NEW.name, ''), NEW.routine_id);

  INSERT INTO public.notifications (
    client_id,
    type,
    title,
    body,
    agent_slug,
    related_entity_type,
    related_entity_id,
    urgency_level,
    channels
  ) VALUES (
    NEW.client_id,
    'routine_suspended',
    'Rotina suspensa por falhas consecutivas',
    format(
      'A rotina "%s" foi suspensa automaticamente após %s falhas consecutivas. '
      'Revise a configuração e reative manualmente.',
      _routine_name,
      NEW.consecutive_failures
    ),
    'system',
    'client_routine',
    NEW.id,
    'high',
    ARRAY['in_app','email']::text[]
  );

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."notify_routine_suspended"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."notify_routine_suspended"() IS 'Trigger fn: insere notification quando client_routines.status muda para "suspended" (circuit breaker). Lê NEW.consecutive_failures.';



CREATE OR REPLACE FUNCTION "public"."offboard_client"("p_client_id" "uuid", "p_batch_size" integer DEFAULT 5000) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $_$
DECLARE
    v_deleted_total int := 0;
    v_batch         int;
    v_report        jsonb := '{}'::jsonb;
    v_big_tables text[] := ARRAY[
        'analytics_v2.dim_inventory',
        'analytics_v2.fato_transacoes',
        'analytics_v2.fato_compras',
        'analytics_v2.dim_clientes',
        'analytics_v2.dim_fornecedores',
        'public.client_routine_executions',
        'public.messages',
        'public.frontend_events',
        'public.notifications'
    ];
    v_tbl    text;
    v_schema text;
    v_tname  text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clientes_blu WHERE client_id = p_client_id) THEN
        RETURN jsonb_build_object('error', 'client_not_found', 'client_id', p_client_id);
    END IF;

    FOREACH v_tbl IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_tbl, '.', 1);
        v_tname  := split_part(v_tbl, '.', 2);
        v_deleted_total := 0;

        LOOP
            EXECUTE format(
                'WITH rows AS (
                    SELECT ctid FROM %I.%I
                    WHERE client_id = $1
                    LIMIT $2
                )
                DELETE FROM %I.%I
                WHERE ctid IN (SELECT ctid FROM rows)',
                v_schema, v_tname, v_schema, v_tname
            ) USING p_client_id, p_batch_size;

            GET DIAGNOSTICS v_batch = ROW_COUNT;
            v_deleted_total := v_deleted_total + v_batch;
            EXIT WHEN v_batch < p_batch_size;
        END LOOP;

        v_report := v_report || jsonb_build_object(v_tbl, v_deleted_total);
    END LOOP;

    DELETE FROM clientes_blu WHERE client_id = p_client_id;
    v_report := v_report || jsonb_build_object('clientes_blu', 1);

    RETURN jsonb_build_object('status', 'ok', 'client_id', p_client_id, 'deleted', v_report);
END;
$_$;


ALTER FUNCTION "public"."offboard_client"("p_client_id" "uuid", "p_batch_size" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."offboard_client"("p_client_id" "uuid", "p_batch_size" integer) IS 'Safe client offboarding: batch-deletes large analytics tables first, then removes
the clientes_blu row (cascade handles the rest). Use instead of direct DELETE on
clientes_blu to avoid pooler connection timeouts. Default batch_size=5000.
Example: SELECT offboard_client(''<uuid>'');';



CREATE OR REPLACE FUNCTION "public"."offboard_client_batch"("p_client_id" "uuid", "p_schema" "text", "p_table" "text", "p_batch_size" integer DEFAULT 10000) RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $_$
DECLARE
    v_deleted int;
BEGIN
    EXECUTE format(
        'WITH rows AS (
            SELECT ctid FROM %I.%I
            WHERE client_id = $1
            LIMIT $2
        )
        DELETE FROM %I.%I
        WHERE ctid IN (SELECT ctid FROM rows)',
        p_schema, p_table, p_schema, p_table
    ) USING p_client_id, p_batch_size;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$_$;


ALTER FUNCTION "public"."offboard_client_batch"("p_client_id" "uuid", "p_schema" "text", "p_table" "text", "p_batch_size" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."offboard_client_batch"("p_client_id" "uuid", "p_schema" "text", "p_table" "text", "p_batch_size" integer) IS 'Delete one batch of rows for a client from a specific table.
Call repeatedly from the application until it returns 0, then DELETE FROM clientes_blu.
This releases the pooler connection between batches — safe for multi-tenant production.
Example: SELECT offboard_client_batch(''<uuid>'', ''analytics_v2'', ''dim_inventory'', 10000);';



CREATE OR REPLACE FUNCTION "public"."on_approval_completed"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_doc_type_id  text;
  v_client_id    uuid := NEW.client_id;
  v_cr_id        uuid;
BEGIN
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  IF NEW.action_type = 'routine_activation' THEN
    BEGIN
      v_cr_id := (NEW.payload->>'client_routine_id')::uuid;
      IF v_cr_id IS NOT NULL THEN
        UPDATE public.client_routines
          SET status = 'active', active = true
        WHERE id = v_cr_id
          AND client_id = v_client_id;
      END IF;
    EXCEPTION WHEN others THEN
      RAISE WARNING '[on_approval_completed] routine_activation failed for client=%: %', v_client_id, SQLERRM;
    END;
    RETURN NEW;
  END IF;

  IF NEW.payload->>'routine_id' IS NOT NULL THEN
    v_doc_type_id := NEW.payload->>'expected_output';
  ELSE
    v_doc_type_id := CASE NEW.action_type
      WHEN 'create_purchase_order'   THEN 'cotacao_rfq'
      WHEN 'approve_purchase_order'  THEN 'ordem_compra'
      WHEN 'comercial.draft_created' THEN 'proposta_comercial'
      WHEN 'reports.generate'        THEN
        CASE NEW.payload->>'report_type'
          WHEN 'dre'        THEN 'dre_mensal'
          WHEN 'cash_flow'  THEN 'fluxo_caixa_diario'
          WHEN 'margin'     THEN 'relatorio_lucratividade'
          ELSE NULL
        END
      WHEN 'pesquisa_nps'            THEN 'pesquisa_nps'
      WHEN 'send_consumer_reply'     THEN NULL
      ELSE NULL
    END;
  END IF;

  IF v_doc_type_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (v_client_id, v_doc_type_id, 'complete', 'agent_generated', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'agent_generated',
          updated_at = now()
    WHERE client_knowledge_documents.status <> 'complete';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_completed] knowledge upsert failed for action_type=%, client=%: %',
      NEW.action_type, v_client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_approval_completed"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_approval_sale_approved"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- Only fire when status transitions to 'approved'
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  -- Only for sale/order action types
  IF NEW.action_type NOT IN ('sale', 'venda', 'pedido') THEN
    RETURN NEW;
  END IF;

  BEGIN
    PERFORM public.fire_event_for_client(
      'sale_approved',
      NEW.client_id,
      jsonb_build_object('approval_id', NEW.id, 'payload', NEW.payload)
    );
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_sale_approved] fire_event failed for approval=%: %',
      NEW.id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_approval_sale_approved"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_document_review_approved"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_document_id uuid;
BEGIN
  -- Only act on document_review approvals
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'published', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_approved] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_document_review_approved"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_document_review_rejected"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_document_id uuid;
BEGIN
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'rejected' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'archived', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_rejected] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_document_review_rejected"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_knowledge_document_complete"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- Only fire when status transitions to 'complete'
  IF OLD.status = NEW.status OR NEW.status <> 'complete' THEN
    RETURN NEW;
  END IF;

  BEGIN
    -- Enqueue every routine whose trigger_document_id matches this document type
    PERFORM public.enqueue_routine(
      NEW.client_id,
      car.id,
      'document_change',
      jsonb_build_object('document_type_id', NEW.document_type_id)
    )
    FROM public.cross_agent_routines car
    WHERE car.trigger_document_id = NEW.document_type_id;
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_knowledge_document_complete] enqueue failed for doc=%, client=%: %',
      NEW.document_type_id, NEW.client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_knowledge_document_complete"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
  v_cat_trigger text;
  v_cat_config  jsonb;
BEGIN
  IF v_client_id IS NULL THEN
    INSERT INTO public.clientes_blu (external_user_id, api_key, nome_empresa, created_at, updated_at)
    VALUES (
      (auth.jwt() ->> 'sub'),
      gen_random_uuid()::text,
      COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), 'Empresa'),
      now(),
      now()
    )
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;

    IF v_client_id IS NULL THEN
      SELECT client_id INTO v_client_id
      FROM public.clientes_blu
      WHERE external_user_id = (auth.jwt() ->> 'sub');
    END IF;

    IF v_client_id IS NULL THEN
      RAISE EXCEPTION 'Failed to provision tenant for user %', (auth.jwt() ->> 'sub');
    END IF;
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), nome_empresa),
    cpf_cnpj                = COALESCE(NULLIF(trim(p_payload->>'cnpj'), ''),        cpf_cnpj),
    company_profile         = COALESCE(p_payload->'company_profile', company_profile),
    team_structure          = COALESCE(p_payload->'team_structure', team_structure),
    policies                = COALESCE(p_payload->'policies', policies),
    -- NOTE: onboarding_completed_at é setado SÓ por finalize_onboarding()
    -- após o passo 4 (Mapeamento). Não tocar aqui.
    updated_at              = now()
  WHERE client_id = v_client_id;

  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    SELECT trigger_type, trigger_config
    INTO   v_cat_trigger, v_cat_config
    FROM   public.cross_agent_routines
    WHERE  id = v_routine_id;

    v_cat_trigger := COALESCE(v_cat_trigger, 'manual');
    v_cat_config  := COALESCE(v_cat_config,  '{}'::jsonb);

    INSERT INTO public.client_routines
      (client_id, routine_id, notify_channel, active, status, trigger_type, trigger_config)
    VALUES
      (v_client_id, v_routine_id, v_notify, true, 'active', v_cat_trigger, v_cat_config)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET
      notify_channel = EXCLUDED.notify_channel,
      active         = true,
      status         = 'active',
      trigger_type   = CASE
        WHEN client_routines.trigger_type = 'manual'
        THEN EXCLUDED.trigger_type
        ELSE client_routines.trigger_type
      END,
      trigger_config = CASE
        WHEN client_routines.trigger_config = '{}'::jsonb
        THEN EXCLUDED.trigger_config
        ELSE client_routines.trigger_config
      END;

    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$$;


ALTER FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ops_list_sync_jobs"() RETURNS TABLE("job_id" "uuid", "job_type" "text", "credential_id" bigint, "resource_type" "text", "sync_mode" "text", "status" "text", "progress_pct" integer, "rows_inserted" bigint, "error_message" "text", "started_at" timestamp with time zone, "completed_at" timestamp with time zone, "duration_seconds" numeric, "retry_count" integer, "created_at" timestamp with time zone)
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  SELECT
    job_id, job_type, credential_id, resource_type, sync_mode,
    status, progress_pct, rows_inserted, error_message,
    started_at, completed_at, duration_seconds, retry_count, created_at
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
  ORDER BY created_at DESC
  LIMIT 100;
$$;


ALTER FUNCTION "public"."ops_list_sync_jobs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ops_retry_job"("p_job_id" "uuid") RETURNS "void"
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  UPDATE analytics_v2.reg_jobs
  SET
    status       = 'pending',
    error_message = NULL,
    progress_pct  = 0,
    retry_count   = retry_count + 1,
    updated_at    = now()
  WHERE job_id = p_job_id
    AND client_id = public.get_my_client_id();
$$;


ALTER FUNCTION "public"."ops_retry_job"("p_job_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."polp_set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."polp_set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."process_pending_routine_executions"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $_$
DECLARE
  v_exec         record;
  v_routine      record;
  v_cr           record;
  v_steps        jsonb;
  v_step         jsonb;
  v_done         integer := 0;
  v_step_n       integer;
  v_action       text;
  v_title        text;
  v_body         text;
  v_routine_name text;
  v_is_custom    boolean;
BEGIN
  FOR v_exec IN
    SELECT cre.*
    FROM public.client_routine_executions cre
    WHERE cre.status = 'pending'
    ORDER BY cre.created_at
    LIMIT 20
  LOOP
    v_is_custom := (v_exec.routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

    IF v_is_custom THEN
      SELECT * INTO v_cr
      FROM public.client_routines
      WHERE id = v_exec.routine_id::uuid
        AND client_id = v_exec.client_id
        AND source = 'custom';

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_cr.steps;
      v_routine_name := COALESCE(v_cr.name, 'Rotina Personalizada');
    ELSE
      SELECT * INTO v_routine
      FROM public.cross_agent_routines
      WHERE id = v_exec.routine_id;

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_routine.steps;
      v_routine_name := v_routine.name;
    END IF;

    BEGIN
      FOR v_step IN SELECT value FROM jsonb_array_elements(v_steps)
      LOOP
        v_step_n := (v_step->>'step')::integer;
        v_action := replace(v_step->>'action', '_', ' ');
        v_title  := v_routine_name || ' · Passo ' || v_step_n || ': ' || v_action;
        v_body   := 'O agente ' || (v_step->>'agent') || ' precisa da sua aprovação para: ' || v_action || '.';

        INSERT INTO public.approval_requests
          (client_id, action_type, agent_slug, title, body, payload, expires_at)
        VALUES (
          v_exec.client_id,
          v_step->>'action',
          v_step->>'agent',
          v_title,
          v_body,
          jsonb_build_object(
            'routine_id',      v_exec.routine_id,
            'execution_id',    v_exec.id,
            'step',            v_step_n,
            'expected_output', v_step->>'output',
            'routine_name',    v_routine_name,
            'is_custom',       v_is_custom
          ),
          now() + interval '7 days'
        );

        IF v_step->>'output' IS NOT NULL THEN
          INSERT INTO public.client_knowledge_documents
            (client_id, document_type_id, status, source, updated_at)
          VALUES
            (v_exec.client_id, v_step->>'output', 'partial', 'agent_generated', now())
          ON CONFLICT (client_id, document_type_id) DO UPDATE
            SET status     = 'partial',
                updated_at = now()
          WHERE client_knowledge_documents.status = 'missing';
        END IF;
      END LOOP;

      UPDATE public.client_routine_executions
        SET status = 'dispatched', dispatched_at = now()
      WHERE id = v_exec.id;

      v_done := v_done + 1;

    EXCEPTION WHEN others THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      RAISE WARNING '[process_pending_routine_executions] failed for execution %: %', v_exec.id, SQLERRM;
    END;
  END LOOP;

  RETURN v_done;
END;
$_$;


ALTER FUNCTION "public"."process_pending_routine_executions"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reap_stale_routine_executions"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
declare
  _retried        int;
  _failed         int;
  _no_heartbeat   interval := interval '10 minutes';  -- sem nenhum sinal
  _dead_heartbeat interval := interval '5 minutes';   -- heartbeat parou
  _max_reaps      int      := 2;                      -- tentativas antes de failed
begin
  -- 1) Retry: re-despacha execuções travadas com tentativas restantes
  update public.client_routine_executions
  set
    status        = 'dispatched',
    dispatched_at = now(),
    heartbeat_at  = null,
    failure_count = coalesce(failure_count, 0) + 1,
    result_text   = 'retomada automática após travamento (reaper, tentativa '
                    || (coalesce(failure_count, 0) + 1)::text || ')'
  where status in ('dispatched', 'executing')
    and (
      (heartbeat_at is null and dispatched_at < now() - _no_heartbeat)
      or
      (heartbeat_at is not null and heartbeat_at < now() - _dead_heartbeat)
    )
    and coalesce(failure_count, 0) < _max_reaps;

  get diagnostics _retried = row_count;

  -- 2) Falha definitiva: tentativas esgotadas
  update public.client_routine_executions
  set
    status       = 'failed',
    result_text  = 'timeout: execução travada (reaper) — tentativas esgotadas',
    completed_at = now()
  where status in ('dispatched', 'executing')
    and (
      (heartbeat_at is null and dispatched_at < now() - _no_heartbeat)
      or
      (heartbeat_at is not null and heartbeat_at < now() - _dead_heartbeat)
    )
    and coalesce(failure_count, 0) >= _max_reaps;

  get diagnostics _failed = row_count;

  if _retried > 0 or _failed > 0 then
    raise notice '[reap_stale] retried % execution(s), failed % execution(s)',
      _retried, _failed;
  end if;

  return _retried + _failed;
end;
$$;


ALTER FUNCTION "public"."reap_stale_routine_executions"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text" DEFAULT NULL::"text", "p_entity_id" "text" DEFAULT NULL::"text", "p_payload" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO public.audit_log (client_id, actor_id, action, entity_type, entity_id, payload)
  VALUES (public.get_my_client_id(), auth.uid()::text, p_action, p_entity_type, p_entity_id, p_payload);
END;
$$;


ALTER FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (public.get_my_client_id(), p_event_name, p_properties);
END;
$$;


ALTER FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_dimension" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text" DEFAULT 'info'::"text", "p_recommendation" "text" DEFAULT NULL::"text", "p_metric_value" numeric DEFAULT NULL::numeric, "p_baseline_value" numeric DEFAULT NULL::numeric, "p_variance_pct" numeric DEFAULT NULL::numeric, "p_payload" "jsonb" DEFAULT NULL::"jsonb", "p_run_date" "date" DEFAULT CURRENT_DATE, "p_prompt_version" "text" DEFAULT NULL::"text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id uuid;
  v_severity text;
BEGIN
  -- Normalise severity; reject anything unexpected
  v_severity := COALESCE(p_severity, 'info');
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  INSERT INTO public.client_insights (
    id, client_id, dimension, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body, generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, p_dimension, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,   -- keep body in sync for backwards compat
    now()
  )
  ON CONFLICT (client_id, run_date, dimension, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL
  DO UPDATE SET
    title           = EXCLUDED.title,
    observation     = EXCLUDED.observation,
    body            = EXCLUDED.observation,
    recommendation  = EXCLUDED.recommendation,
    severity        = EXCLUDED.severity,
    metric_value    = EXCLUDED.metric_value,
    baseline_value  = EXCLUDED.baseline_value,
    variance_pct    = EXCLUDED.variance_pct,
    prompt_version  = EXCLUDED.prompt_version,
    generated_at    = now(),
    dismissed       = false,
    dismissed_at    = NULL
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_dimension" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_room" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text" DEFAULT 'info'::"text", "p_recommendation" "text" DEFAULT NULL::"text", "p_metric_value" numeric DEFAULT NULL::numeric, "p_baseline_value" numeric DEFAULT NULL::numeric, "p_variance_pct" numeric DEFAULT NULL::numeric, "p_payload" "jsonb" DEFAULT NULL::"jsonb", "p_run_date" "date" DEFAULT CURRENT_DATE, "p_prompt_version" "text" DEFAULT NULL::"text", "p_dimension" "text" DEFAULT NULL::"text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id       uuid;
  v_severity text;
  v_room     text;
BEGIN
  -- Normalise severity
  v_severity := COALESCE(p_severity, 'info');
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  -- Support old p_dimension callers: map to room slug if p_room not given
  v_room := COALESCE(p_room, CASE p_dimension
    WHEN 'finance'    THEN 'financeiro'
    WHEN 'commercial' THEN 'clientes'
    WHEN 'inventory'  THEN 'compras'
    WHEN 'supply'     THEN 'compras'
    ELSE p_dimension
  END, 'financeiro');

  INSERT INTO public.client_insights (
    id, client_id, room, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body, generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, v_room, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,
    now()
  )
  ON CONFLICT (client_id, run_date, room, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL
  DO UPDATE SET
    title           = EXCLUDED.title,
    observation     = EXCLUDED.observation,
    body            = EXCLUDED.observation,
    recommendation  = EXCLUDED.recommendation,
    severity        = EXCLUDED.severity,
    metric_value    = EXCLUDED.metric_value,
    baseline_value  = EXCLUDED.baseline_value,
    variance_pct    = EXCLUDED.variance_pct,
    prompt_version  = EXCLUDED.prompt_version,
    generated_at    = now(),
    dismissed       = false,
    dismissed_at    = NULL
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_room" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text", "p_dimension" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_routine_failure"("p_client_id" "uuid", "p_routine_id" "text", "p_max_failures" integer DEFAULT 3) RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  _new_failures int;
  _new_status   text;
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = consecutive_failures + 1
  WHERE client_id  = p_client_id
    AND routine_id = p_routine_id
  RETURNING consecutive_failures INTO _new_failures;

  IF _new_failures IS NULL THEN
    RETURN 'not_found';
  END IF;

  IF _new_failures >= p_max_failures THEN
    UPDATE public.client_routines
    SET status = 'suspended',
        active = false
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id;
    _new_status := 'suspended';
    RAISE NOTICE '[circuit_breaker] routine % client % suspended after % failures',
      p_routine_id, p_client_id, _new_failures;
  ELSE
    _new_status := 'active';
  END IF;

  RETURN _new_status;
END;
$$;


ALTER FUNCTION "public"."record_routine_failure"("p_client_id" "uuid", "p_routine_id" "text", "p_max_failures" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."record_routine_failure"("p_client_id" "uuid", "p_routine_id" "text", "p_max_failures" integer) IS 'Circuit breaker: incrementa consecutive_failures e suspende rotina quando threshold atingido. Chamada pelo agent_api após falha em execução.';



CREATE OR REPLACE FUNCTION "public"."redispatch_routine_after_approval"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_exec_id TEXT;
BEGIN
  -- Only act when a routine_hitl approval transitions to 'approved'
  IF NEW.action_type <> 'routine_hitl'
     OR NEW.status <> 'approved'
     OR OLD.status = 'approved'
  THEN
    RETURN NEW;
  END IF;

  v_exec_id := NEW.payload ->> 'execution_id';
  IF v_exec_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Re-dispatch only if the execution is still waiting for this approval
  UPDATE public.client_routine_executions
    SET status        = 'dispatched',
        dispatched_at = NOW()
  WHERE id::TEXT     = v_exec_id
    AND status        = 'awaiting_approval';

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."redispatch_routine_after_approval"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."refresh_analytics_views"() RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_started_at  timestamptz := now();
  v_errors      text[]      := ARRAY[]::text[];
BEGIN
  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_resumo_dashboard: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_series_temporal;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_series_temporal: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_distribuicao_regional: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_ultimos_pedidos: ' || SQLERRM);
  END;

  RETURN jsonb_build_object(
    'refreshed_at',    now(),
    'duration_ms',     extract(milliseconds from (now() - v_started_at))::int,
    'views_refreshed', to_jsonb(ARRAY[
      'mv_resumo_dashboard',
      'mv_series_temporal',
      'mv_distribuicao_regional',
      'mv_ultimos_pedidos'
    ]),
    'errors', to_jsonb(v_errors)
  );
END;
$$;


ALTER FUNCTION "public"."refresh_analytics_views"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."refresh_analytics_views"() IS 'Refreshes all four analytics_v2 materialized views in dependency order. Each view is wrapped in its own exception block so a single failure does not abort the rest. Returns a JSON summary with duration and any per-view errors. Meant to be called by a cron job immediately after run_incremental_etl completes.';



CREATE OR REPLACE FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
BEGIN
  -- As MVs são globais (não filtradas por client_id na definição),
  -- então um REFRESH serve todos os clientes. O p_client_id é recebido
  -- por consistência de interface mas não filtra o refresh.
  -- Ordem importa: mv_resumo_dashboard depende de fato_transacoes (já atualizado
  -- por apply_staging_to_facts antes do enqueue do job).
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;
END;
$$;


ALTER FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") IS 'SECURITY DEFINER. Refreshes all 4 analytics_v2 dashboard MVs (CONCURRENTLY). Called by etl-refresh-dashboards edge function after apply_staging_to_facts enqueues a refresh_dashboards job. p_client_id is logged/auditable but MVs are global (not per-client partitioned).';



CREATE OR REPLACE FUNCTION "public"."request_approval"("p_action_type" "text" DEFAULT NULL::"text", "p_payload" "jsonb" DEFAULT '{}'::"jsonb", "p_expires_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "p_agent_slug" "text" DEFAULT NULL::"text", "p_action" "text" DEFAULT NULL::"text", "p_session_id" "text" DEFAULT NULL::"text", "p_tool_call_id" "text" DEFAULT NULL::"text", "p_routed_to_role" "text" DEFAULT NULL::"text", "p_sla_hours" integer DEFAULT 72) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id          uuid;
  v_action_type text := COALESCE(p_action_type, p_action);
  v_expires_at  timestamp with time zone := COALESCE(
    p_expires_at,
    CASE WHEN p_sla_hours IS NOT NULL THEN now() + (p_sla_hours || ' hours')::interval ELSE NULL END
  );
BEGIN
  IF v_action_type IS NULL THEN
    RAISE EXCEPTION 'request_approval: action_type (or p_action) is required';
  END IF;

  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, agent_slug, payload, expires_at,
     session_id, tool_call_id)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, v_action_type, p_agent_slug,
     p_payload, v_expires_at, p_session_id, p_tool_call_id)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reset_routine_failures"("p_client_id" "uuid", "p_routine_id" "text") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = 0,
      status = 'active',
      active = true
  WHERE client_id = p_client_id
    AND routine_id = p_routine_id;
END;
$$;


ALTER FUNCTION "public"."reset_routine_failures"("p_client_id" "uuid", "p_routine_id" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer DEFAULT 20) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_source    record;
  v_enqueued  integer := 0;
  v_skipped   integer := 0;
BEGIN
  FOR v_source IN
    SELECT
      cds.id              AS data_source_id,
      cds.client_id,
      cds.credential_id,
      cds.source_type,
      cds.resource_type,
      cds.watermark_column,
      cds.last_watermark_value,
      cds.last_synced_at
    FROM public.client_data_sources cds
    WHERE cds.sync_status IN ('ready', 'success', 'synced')
      AND (
        cds.last_synced_at IS NULL
        OR cds.last_synced_at < now() - (p_hours_since_last_sync || ' hours')::interval
      )
    ORDER BY cds.client_id, cds.resource_type
  LOOP
    -- Skip if a pending/running job already exists for this source
    IF EXISTS (
      SELECT 1 FROM analytics_v2.reg_jobs
      WHERE client_id     = v_source.client_id
        AND credential_id = v_source.credential_id
        AND job_type      = 'bigquery_sync'
        AND status IN ('pending', 'running')
    ) THEN
      v_skipped := v_skipped + 1;
      CONTINUE;
    END IF;

    INSERT INTO analytics_v2.reg_jobs (
      job_id, client_id, job_type, credential_id, resource_type,
      sync_mode, status, input_params, created_at, updated_at
    ) VALUES (
      gen_random_uuid(),
      v_source.client_id,
      'bigquery_sync',
      v_source.credential_id,
      v_source.resource_type,
      CASE WHEN v_source.last_watermark_value IS NOT NULL THEN 'incremental' ELSE 'full' END,
      'pending',
      jsonb_build_object(
        'credential_id',        v_source.credential_id,
        'data_source_id',       v_source.data_source_id,
        'source_type',          v_source.source_type,
        'watermark_column',     v_source.watermark_column,
        'last_watermark_value', v_source.last_watermark_value,
        'force_full_sync',      (v_source.last_watermark_value IS NULL),
        'requested_at',         now()
      ),
      now(),
      now()
    );

    v_enqueued := v_enqueued + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'enqueued', v_enqueued,
    'skipped',  v_skipped,
    'run_at',   now()
  );
END;
$$;


ALTER FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer) IS 'Enqueues analytics_etl jobs in reg_jobs for every active data source not synced within the last p_hours_since_last_sync hours. Uses watermark_column/last_watermark_value for incremental loads; falls back to full load when no watermark exists. The Python backend picks up pending jobs and executes the actual data movement.';



CREATE OR REPLACE FUNCTION "public"."schedule_monthly_context_reports"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  _client       record;
  _supabase_url text := current_setting('app.supabase_url', true);
  _service_key  text := current_setting('app.service_role_key', true);
BEGIN
  IF _supabase_url IS NULL OR _service_key IS NULL THEN
    RAISE WARNING 'schedule_monthly_context_reports: app settings not configured';
    RETURN;
  END IF;

  FOR _client IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    PERFORM net.http_post(
      url     := _supabase_url || '/functions/v1/generate-context-report',
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || _service_key
      ),
      body    := jsonb_build_object('client_id', _client.client_id)
    );
  END LOOP;
END;
$$;


ALTER FUNCTION "public"."schedule_monthly_context_reports"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."seed_client_owner"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_email text;
  v_name  text;
BEGIN
  SELECT au.email, au.raw_user_meta_data ->> 'full_name'
    INTO v_email, v_name
    FROM auth.users au
   WHERE au.id::text = NEW.external_user_id
   LIMIT 1;

  IF v_email IS NOT NULL THEN
    INSERT INTO public.client_users (client_id, auth_user_id, email, name, role, accepted_at)
    VALUES (
      NEW.client_id,
      (SELECT id FROM auth.users WHERE id::text = NEW.external_user_id LIMIT 1),
      v_email,
      v_name,
      'owner',
      now()
    )
    ON CONFLICT (client_id, email) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."seed_client_owner"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."send_email_hook"() RETURNS json
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$BEGIN
            RETURN json_build_object(
                'status', 'ok',
                'message', 'noop - email disabled via hook'
            );
        END;$$;


ALTER FUNCTION "public"."send_email_hook"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."send_email_hook"("event" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
begin
  -- The send_email hook contract expects a jsonb response.
  -- Returning {"skip": true} tells Supabase Auth to NOT invoke its
  -- built-in email provider, which is what removes the 2/h rate limit.
  return jsonb_build_object('skip', true);
end;
$$;


ALTER FUNCTION "public"."send_email_hook"("event" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_agent_lists_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_agent_lists_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
BEGIN
  DELETE FROM public.client_dimension_kpis
  WHERE client_id = v_client_id AND dimension = p_dimension;

  INSERT INTO public.client_dimension_kpis (client_id, dimension, slug)
  SELECT v_client_id, p_dimension, s
  FROM unnest(p_slugs) s
  WHERE EXISTS (SELECT 1 FROM public.kpi_catalog WHERE slug = s)
  ON CONFLICT DO NOTHING;

  RETURN jsonb_build_object('dimension', p_dimension, 'count', array_length(p_slugs, 1));
END;
$$;


ALTER FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_client_users_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_client_users_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_current_client_id"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;
$$;


ALTER FUNCTION "public"."set_current_client_id"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;
$$;


ALTER FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_current_customer_id"("p_customer_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  -- If your app uses customer_id as the client identifier in RLS,
  -- store it in the same session variable.
  PERFORM set_config('app.current_client_id', p_customer_id::text, true);
END;
$$;


ALTER FUNCTION "public"."set_current_customer_id"("p_customer_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_ui_pref"("p_key" "text", "p_value" "jsonb") RETURNS "void"
    LANGUAGE "sql"
    AS $$
  UPDATE public.clientes_blu
  SET ui_prefs = jsonb_set(COALESCE(ui_prefs, '{}'), ARRAY[p_key], p_value, true)
  WHERE external_user_id = (auth.jwt() ->> 'sub');
$$;


ALTER FUNCTION "public"."set_ui_pref"("p_key" "text", "p_value" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sincronizar_csv_cliente"("p_job_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $_$
DECLARE
  v_job              RECORD;
  v_client_id        UUID;
  v_source_id        UUID;
  v_column_mapping   JSONB;
  v_start_time       TIMESTAMPTZ := now();
  v_rows_affected    BIGINT := 0;
  v_total_rows       INTEGER;
  v_error_msg        TEXT;
  v_staging          RECORD;
  v_row              JSONB;

  v_documento            TEXT;
  v_data_competencia     TEXT;
  v_quantidade           NUMERIC;
  v_valor_unitario       NUMERIC;
  v_valor                NUMERIC;
  v_status               TEXT;
  v_tipo_lancamento      TEXT;
  v_categoria            TEXT;
  v_subcategoria         TEXT;

  v_cliente_cpf_cnpj     TEXT;
  v_cliente_nome         TEXT;
  v_cliente_telefone     TEXT;
  v_cliente_cidade       TEXT;
  v_cliente_uf           TEXT;

  v_fornecedor_cnpj      TEXT;
  v_fornecedor_nome      TEXT;
  v_fornecedor_telefone  TEXT;
  v_fornecedor_cidade    TEXT;
  v_fornecedor_uf        TEXT;

  v_produto_sku          TEXT;
  v_produto_nome         TEXT;

  v_transacao_id         TEXT;
  v_customer_id          BIGINT;
  v_fornecedor_id        BIGINT;
  v_produto_id           BIGINT;
  v_data_id              BIGINT;
  v_parsed_date          DATE;

  -- NEW: classification variables
  v_client_cpf_cnpj      TEXT;   -- CPF/CNPJ do próprio cliente (de clientes_blu)
  v_entity_context       TEXT;   -- detected_entity_context do source
  v_tipo_transacao       TEXT;   -- 'venda' | 'compra' | 'despesa' | 'banking'
  v_entry_type           TEXT;   -- 'revenue' | 'purchase' | 'expense' | 'banking'

BEGIN
  SELECT job_id, client_id, input_params, status
  INTO v_job
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id
  FOR UPDATE;

  IF v_job IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'Job not found', 'job_id', p_job_id);
  END IF;

  IF v_job.status <> 'pending' THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', format('Job is not in pending state (current: %s)', v_job.status),
      'job_id', p_job_id
    );
  END IF;

  v_client_id := v_job.client_id;
  v_source_id := (v_job.input_params->>'source_id')::UUID;

  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = now(), progress_pct = 5, updated_at = now()
  WHERE job_id = p_job_id;

  BEGIN
    SELECT column_mapping INTO v_column_mapping
    FROM public.client_data_sources
    WHERE id = v_source_id AND client_id = v_client_id;

    IF v_column_mapping IS NULL OR v_column_mapping = '{}'::jsonb THEN
      RAISE EXCEPTION 'No column_mapping found for source %', v_source_id;
    END IF;

    -- NEW: fetch client's own CPF/CNPJ and source entity context
    SELECT cpf_cnpj INTO v_client_cpf_cnpj
    FROM public.clientes_blu
    WHERE client_id = v_client_id;

    SELECT detected_entity_context INTO v_entity_context
    FROM public.client_data_sources
    WHERE id = v_source_id AND client_id = v_client_id;

    SELECT * INTO v_staging
    FROM public.csv_import_staging
    WHERE source_id = v_source_id
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_staging IS NULL THEN
      RAISE EXCEPTION 'No staged rows found for source %', v_source_id;
    END IF;

    v_total_rows := jsonb_array_length(v_staging.rows);

    UPDATE analytics_v2.reg_jobs SET progress_pct = 10, updated_at = now() WHERE job_id = p_job_id;

    FOR i IN 0 .. v_total_rows - 1 LOOP
      v_row := v_staging.rows->i;

      v_rows_affected := v_rows_affected + 1;

      v_customer_id   := NULL;
      v_fornecedor_id := NULL;
      v_produto_id    := NULL;
      v_data_id       := NULL;
      v_tipo_transacao := NULL;
      v_entry_type    := NULL;

      v_documento        := v_row ->> (v_column_mapping->>'documento');
      v_data_competencia := v_row ->> (v_column_mapping->>'data_competencia_id');
      v_quantidade       := NULLIF(v_row ->> (v_column_mapping->>'quantidade'), '')::NUMERIC;
      v_valor_unitario   := NULLIF(v_row ->> (v_column_mapping->>'valor_unitario'), '')::NUMERIC;
      v_valor            := NULLIF(v_row ->> (v_column_mapping->>'valor'), '')::NUMERIC;
      v_status           := NULLIF(v_row ->> (v_column_mapping->>'status'), '');
      -- The schema matcher emits the canonical name 'transaction_label'
      -- (INVOICES_COLUMNS in tool_pool_api match_columns); older mappings
      -- used 'tipo_lancamento'. Accept both so tier-1 classification works.
      v_tipo_lancamento  := COALESCE(
        NULLIF(v_row ->> (v_column_mapping->>'tipo_lancamento'), ''),
        NULLIF(v_row ->> (v_column_mapping->>'transaction_label'), '')
      );
      v_categoria        := NULLIF(v_row ->> (v_column_mapping->>'categoria'), '');
      v_subcategoria     := NULLIF(v_row ->> (v_column_mapping->>'subcategoria'), '');

      v_cliente_cpf_cnpj := NULLIF(v_row ->> (v_column_mapping->>'cliente_cpf_cnpj'), '');
      v_cliente_nome     := NULLIF(v_row ->> (v_column_mapping->>'cliente_nome'), '');
      v_cliente_telefone := NULLIF(v_row ->> (v_column_mapping->>'cliente_telefone'), '');
      v_cliente_cidade   := NULLIF(v_row ->> (v_column_mapping->>'cliente_cidade'), '');
      v_cliente_uf       := NULLIF(v_row ->> (v_column_mapping->>'cliente_uf'), '');

      v_fornecedor_cnpj     := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_cnpj'), '');
      v_fornecedor_nome     := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_nome'), '');
      v_fornecedor_telefone := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_telefone'), '');
      v_fornecedor_cidade   := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_cidade'), '');
      v_fornecedor_uf       := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_uf'), '');

      v_produto_sku  := NULLIF(v_row ->> (v_column_mapping->>'produto_sku'), '');
      v_produto_nome := NULLIF(v_row ->> (v_column_mapping->>'produto_nome'), '');

      v_transacao_id := md5(
        v_client_id || ':csv:' || v_source_id::TEXT || ':' ||
        COALESCE(v_documento, '') || ':' ||
        COALESCE(v_data_competencia, '') || ':' ||
        COALESCE(v_produto_sku, '') || ':' ||
        v_rows_affected::TEXT
      );

      -- Upsert dim_clientes
      IF v_cliente_cpf_cnpj IS NOT NULL OR v_cliente_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_clientes (
          client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
        ) VALUES (
          v_client_id, v_cliente_cpf_cnpj, v_cliente_nome,
          v_cliente_telefone, v_cliente_cidade, v_cliente_uf, now()
        )
        ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL
        DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_clientes.nome),
          telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_clientes.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_clientes.endereco_uf),
          atualizado_em   = now();

        SELECT customer_id INTO v_customer_id
        FROM analytics_v2.dim_clientes
        WHERE client_id = v_client_id
          AND (
            (v_cliente_cpf_cnpj IS NOT NULL AND cpf_cnpj = v_cliente_cpf_cnpj)
            OR (v_cliente_cpf_cnpj IS NULL AND nome = v_cliente_nome)
          )
        LIMIT 1;
      END IF;

      -- Upsert dim_fornecedores
      IF v_fornecedor_cnpj IS NOT NULL OR v_fornecedor_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_fornecedores (
          client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
        ) VALUES (
          v_client_id, v_fornecedor_cnpj, v_fornecedor_nome,
          v_fornecedor_telefone, v_fornecedor_cidade, v_fornecedor_uf, now()
        )
        ON CONFLICT (client_id, cnpj) WHERE cnpj IS NOT NULL
        DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_fornecedores.nome),
          telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_fornecedores.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_fornecedores.endereco_uf),
          atualizado_em   = now();

        SELECT fornecedor_id INTO v_fornecedor_id
        FROM analytics_v2.dim_fornecedores
        WHERE client_id = v_client_id
          AND (
            (v_fornecedor_cnpj IS NOT NULL AND cnpj = v_fornecedor_cnpj)
            OR (v_fornecedor_cnpj IS NULL AND nome = v_fornecedor_nome)
          )
        LIMIT 1;
      END IF;

      -- Upsert dim_inventory
      -- Com SKU: unicidade por (client_id, sku). Sem SKU: por (client_id, nome)
      -- via índice parcial dim_inventory_client_nome_uniq — antes desse índice,
      -- produtos sem SKU eram re-inseridos a cada execução do ETL.
      IF v_produto_sku IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_inventory (
          client_id, sku, nome, updated_at
        ) VALUES (
          v_client_id, v_produto_sku, v_produto_nome, now()
        )
        ON CONFLICT (client_id, sku) WHERE sku IS NOT NULL
        DO UPDATE SET
          nome       = COALESCE(EXCLUDED.nome, analytics_v2.dim_inventory.nome),
          updated_at = now();
      ELSIF v_produto_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_inventory (
          client_id, sku, nome, updated_at
        ) VALUES (
          v_client_id, NULL, v_produto_nome, now()
        )
        ON CONFLICT (client_id, nome) WHERE sku IS NULL
        DO UPDATE SET
          updated_at = now();
      END IF;

      IF v_produto_sku IS NOT NULL OR v_produto_nome IS NOT NULL THEN
        SELECT inventory_id INTO v_produto_id
        FROM analytics_v2.dim_inventory
        WHERE client_id = v_client_id
          AND (
            (v_produto_sku IS NOT NULL AND sku = v_produto_sku)
            OR (v_produto_sku IS NULL AND nome = v_produto_nome)
          )
        LIMIT 1;
      END IF;

      -- Parse date: tier 1 ISO, tier 2 DD/MM/YYYY (com ou sem hora), tier 3 serial Excel
      v_parsed_date := NULL;
      IF v_data_competencia IS NOT NULL AND v_data_competencia <> '' THEN
        BEGIN
          v_parsed_date := v_data_competencia::DATE;
        EXCEPTION WHEN OTHERS THEN NULL; END;

        IF v_parsed_date IS NULL THEN
          BEGIN
            -- strip time component before parsing (handles "12/09/2025 00:00:00")
            v_parsed_date := to_date(split_part(v_data_competencia, ' ', 1), 'DD/MM/YYYY');
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        IF v_parsed_date IS NULL AND v_data_competencia ~ '^\d+$' THEN
          BEGIN
            v_parsed_date := DATE '1899-12-30' + v_data_competencia::INTEGER;
            IF v_parsed_date < '1970-01-01' OR v_parsed_date > '2100-01-01' THEN
              v_parsed_date := NULL;
            END IF;
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        IF v_parsed_date IS NOT NULL THEN
          INSERT INTO analytics_v2.dim_datas (
            data, ano, mes, dia, numero_dia_semana, numero_semana_ano
          ) VALUES (
            v_parsed_date,
            EXTRACT(YEAR  FROM v_parsed_date)::INTEGER,
            EXTRACT(MONTH FROM v_parsed_date)::INTEGER,
            EXTRACT(DAY   FROM v_parsed_date)::INTEGER,
            EXTRACT(ISODOW FROM v_parsed_date)::INTEGER,
            EXTRACT(WEEK  FROM v_parsed_date)::INTEGER
          )
          ON CONFLICT (data) DO NOTHING;

          SELECT data_id INTO v_data_id
          FROM analytics_v2.dim_datas
          WHERE data = v_parsed_date
          LIMIT 1;
        END IF;
      END IF;

      -- ── tipo_transacao cascade (espelha apply_staging_to_facts) ─────────────
      -- Tier 1: tipo_lancamento mapeado no CSV → keyword match
      -- 'serviço' NÃO é keyword de compra: uma NF de serviço é venda para
      -- quem presta e compra para quem contrata — o label sozinho não
      -- decide. Deixa cair para os tiers 2/3, que olham a estrutura da
      -- linha (cliente presente → venda; fornecedor presente → compra).
      IF v_tipo_lancamento IS NOT NULL THEN
        v_tipo_transacao := CASE
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['venda%','receita%','faturamento%','nf%','nota fiscal%','revenue%']) THEN 'venda'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['compra%','material%','mat%','insumo%','estoque%','mdo%','mão de obra%','fornecedor%']) THEN 'compra'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['despesa%','custo%','overhead%','admin%','expense%']) THEN 'despesa'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['transfer%','banco%','banking%','saldo%']) THEN 'banking'
          ELSE NULL  -- label desconhecido → deixa cair para tier 2
        END;
      END IF;

      -- Tier 2: CPF/CNPJ do próprio cliente cruzado com dados da row
      IF v_tipo_transacao IS NULL AND v_client_cpf_cnpj IS NOT NULL THEN
        IF regexp_replace(COALESCE(v_fornecedor_cnpj, ''), '[^0-9]', '', 'g')
             = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
           AND v_fornecedor_cnpj IS NOT NULL THEN
          v_tipo_transacao := 'venda';   -- cliente é o emissor da NF (fornecedor na row == ele mesmo)
        ELSIF regexp_replace(COALESCE(v_cliente_cpf_cnpj, ''), '[^0-9]', '', 'g')
                = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
              AND v_cliente_cpf_cnpj IS NOT NULL THEN
          v_tipo_transacao := 'compra';  -- cliente é o comprador (cliente na row == ele mesmo)
        END IF;
      END IF;

      -- Tier 3: dim hit — se encontrou cliente/fornecedor nas dims
      IF v_tipo_transacao IS NULL THEN
        IF    v_customer_id   IS NOT NULL THEN v_tipo_transacao := 'venda';
        ELSIF v_fornecedor_id IS NOT NULL THEN v_tipo_transacao := 'compra';
        END IF;
      END IF;

      -- Tier 4: detected_entity_context do source
      IF v_tipo_transacao IS NULL THEN
        v_tipo_transacao := CASE
          WHEN v_entity_context ILIKE ANY(ARRAY['supplier%','cost%','expense%','purchase%','custo%','fornecedor%','compra%']) THEN 'compra'
          WHEN v_entity_context ILIKE ANY(ARRAY['customer%','revenue%','sales%','venda%','faturamento%','cliente%'])          THEN 'venda'
          WHEN v_entity_context ILIKE ANY(ARRAY['banking%','bank%','account%','conta%'])                                      THEN 'banking'
          ELSE 'despesa'  -- último fallback
        END;
      END IF;

      -- Derivar entry_type a partir de tipo_transacao
      v_entry_type := CASE v_tipo_transacao
        WHEN 'venda'   THEN 'revenue'
        WHEN 'compra'  THEN 'purchase'
        WHEN 'despesa' THEN 'expense'
        WHEN 'banking' THEN 'banking'
        ELSE 'expense'
      END;

      -- Insert/upsert fato_transacoes
      INSERT INTO analytics_v2.fato_transacoes (
        transacao_id, client_id, data_competencia_id, customer_id,
        fornecedor_id, produto_id, documento, quantidade,
        valor_unitario, valor, status,
        tipo_transacao, entry_type,
        tipo_lancamento, categoria, subcategoria
      ) VALUES (
        v_transacao_id, v_client_id, v_data_id, v_customer_id,
        v_fornecedor_id, v_produto_id,
        NULLIF(v_documento, ''), v_quantidade,
        v_valor_unitario, v_valor, v_status,
        v_tipo_transacao, v_entry_type,
        v_tipo_lancamento, v_categoria, v_subcategoria
      )
      ON CONFLICT (transacao_id, client_id) DO UPDATE SET
        data_competencia_id = EXCLUDED.data_competencia_id,
        customer_id         = EXCLUDED.customer_id,
        fornecedor_id       = EXCLUDED.fornecedor_id,
        produto_id          = EXCLUDED.produto_id,
        quantidade          = EXCLUDED.quantidade,
        valor_unitario      = EXCLUDED.valor_unitario,
        valor               = EXCLUDED.valor,
        status              = EXCLUDED.status,
        tipo_transacao      = COALESCE(EXCLUDED.tipo_transacao, analytics_v2.fato_transacoes.tipo_transacao),
        entry_type          = COALESCE(EXCLUDED.entry_type,     analytics_v2.fato_transacoes.entry_type),
        tipo_lancamento     = EXCLUDED.tipo_lancamento,
        categoria           = EXCLUDED.categoria,
        subcategoria        = EXCLUDED.subcategoria;

      IF v_rows_affected % 100 = 0 THEN
        UPDATE analytics_v2.reg_jobs
        SET
          progress_pct = LEAST(90, 10 + (v_rows_affected * 80 / GREATEST(v_total_rows, 1))::INTEGER),
          updated_at   = now()
        WHERE job_id = p_job_id;
      END IF;

    END LOOP;

    DELETE FROM public.csv_import_staging WHERE id = v_staging.id;

    UPDATE public.client_data_sources
    SET sync_status = 'completed', last_synced_at = now(), updated_at = now()
    WHERE id = v_source_id;

    UPDATE analytics_v2.reg_jobs
    SET
      status           = 'completed',
      completed_at     = now(),
      rows_inserted    = v_rows_affected,
      progress_pct     = 100,
      duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
      output           = jsonb_build_object('rows_inserted', v_rows_affected, 'completed_at', now()),
      updated_at       = now()
    WHERE job_id = p_job_id;

    RETURN jsonb_build_object(
      'success', true,
      'job_id', p_job_id,
      'rows_inserted', v_rows_affected,
      'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    UPDATE analytics_v2.reg_jobs
    SET
      status           = 'failed',
      completed_at     = now(),
      progress_pct     = 0,
      duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
      error_message    = v_error_msg,
      updated_at       = now()
    WHERE job_id = p_job_id;

    UPDATE public.client_data_sources
    SET sync_status = 'sync_failed', error_message = v_error_msg, updated_at = now()
    WHERE id = v_source_id;

    RETURN jsonb_build_object('success', false, 'job_id', p_job_id, 'error', v_error_msg);
  END;
END;
$_$;


ALTER FUNCTION "public"."sincronizar_csv_cliente"("p_job_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."soft_delete_client"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "sql" SECURITY DEFINER
    AS $$ UPDATE public.clientes_blu SET deleted_at = now() WHERE client_id = p_client_id AND deleted_at IS NULL; $$;


ALTER FUNCTION "public"."soft_delete_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_client_id UUID;
BEGIN
  SELECT client_id INTO v_client_id
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found';
  END IF;

  IF v_client_id != public.get_my_client_id() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  UPDATE public.client_data_sources
  SET sync_status = 'discovery_pending'
  WHERE credential_id = p_credential_id;

  RETURN jsonb_build_object(
    'status', 'discovery_queued',
    'credential_id', p_credential_id,
    'queued_at', to_jsonb(NOW())
  );
END;
$$;


ALTER FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_approval_stats"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO public.client_approval_stats (client_id)
    VALUES (NEW.client_id)
    ON CONFLICT (client_id) DO NOTHING;

    IF NEW.status = 'approved' THEN
      UPDATE public.client_approval_stats
        SET total_approved = total_approved + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    ELSIF NEW.status = 'rejected' THEN
      UPDATE public.client_approval_stats
        SET total_rejected = total_rejected + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    END IF;

    -- Promote trust level based on total_approved thresholds
    UPDATE public.client_approval_stats
      SET trust_level = CASE
        WHEN total_approved >= 50 THEN 'full_config'
        WHEN total_approved >= 25 THEN 'rules'
        WHEN total_approved >= 10 THEN 'similar_toggle'
        ELSE 'manual'
      END,
      updated_at = now()
      WHERE client_id = NEW.client_id;
  END IF;
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_approval_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_client_goals_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_client_goals_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_data_source_mappings_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_data_source_mappings_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_dimension_state_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_dimension_state_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_shared_business_memory_meta_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_shared_business_memory_meta_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_shared_business_memory_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_shared_business_memory_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text" DEFAULT 'complete'::"text", "p_source" "text" DEFAULT 'upload'::"text", "p_field_coverage" "jsonb" DEFAULT '{}'::"jsonb", "p_metadata" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid;
  v_result    jsonb;
BEGIN
  v_client_id := public.get_my_client_id();
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Client not authenticated';
  END IF;

  IF p_status NOT IN ('missing','partial','complete') THEN
    RAISE EXCEPTION 'Invalid status: %. Must be missing | partial | complete', p_status;
  END IF;

  INSERT INTO public.client_knowledge_documents
    (client_id, document_type_id, status, source, field_coverage, metadata, updated_at)
  VALUES
    (v_client_id, p_document_type_id, p_status, p_source, p_field_coverage, p_metadata, now())
  ON CONFLICT (client_id, document_type_id) DO UPDATE SET
    status         = EXCLUDED.status,
    source         = EXCLUDED.source,
    field_coverage = EXCLUDED.field_coverage,
    metadata       = EXCLUDED.metadata,
    updated_at     = now()
  -- Never-downgrade: only update if the new status is >= the existing status.
  -- missing (lowest) → partial → complete (highest); reverse is never allowed.
  WHERE CASE client_knowledge_documents.status
    WHEN 'missing'  THEN true                         -- any status can overwrite missing
    WHEN 'partial'  THEN EXCLUDED.status = 'complete' -- only 'complete' can overwrite partial
    WHEN 'complete' THEN false                        -- nothing overwrites complete
    ELSE true
  END
  RETURNING jsonb_build_object(
    'document_type_id', document_type_id,
    'status',           status,
    'source',           source,
    'updated_at',       updated_at
  ) INTO v_result;

  -- When the WHERE guard prevented the update, RETURNING yields nothing.
  -- Return the current row instead so callers always get a valid response.
  IF v_result IS NULL THEN
    SELECT jsonb_build_object(
      'document_type_id', document_type_id,
      'status',           status,
      'source',           source,
      'updated_at',       updated_at
    ) INTO v_result
    FROM public.client_knowledge_documents
    WHERE client_id = v_client_id AND document_type_id = p_document_type_id;
  END IF;

  RETURN v_result;
END;
$$;


ALTER FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
BEGIN
    -- Key 1: Histórico por step (nunca sobrescrito — step único por execução)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('checkpoint:run:%s:step:%s', p_exec_id, p_step_number),
         p_state_value, 'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO NOTHING;  -- step nunca deve colidir

    -- Key 2: Current state (sobrescreve a cada execução)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('current_state:%s', p_routine_id),
         p_state_value, 'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO UPDATE SET
        value      = EXCLUDED.value,
        updated_at = now();

    -- Key 3: Última execução (timestamp + exec_id + last_step — útil para dashboards)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('last_execution:%s', p_routine_id),
         jsonb_build_object(
             'exec_id',     p_exec_id,
             'last_step',   p_step_number,
             'completed_at', now()
         ),
         'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO UPDATE SET
        value      = EXCLUDED.value,
        updated_at = now();
END;
$$;


ALTER FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") IS 'Checkpoint de execução de rotina em shared_business_memory. Upserta 3 keys: checkpoint:run:{exec_id}:step:{N} (histórico), current_state:{routine_id} (estado atual), last_execution:{routine_id} (timestamp da última execução).';



CREATE OR REPLACE FUNCTION "public"."upsert_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text", "p_access_token" "text", "p_refresh_token" "text", "p_token_type" "text" DEFAULT 'Bearer'::"text", "p_expires_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "p_scopes" "text"[] DEFAULT '{}'::"text"[], "p_metadata" "jsonb" DEFAULT '{}'::"jsonb", "p_is_default" boolean DEFAULT true) RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_name    text := 'oauth_' || lower(p_provider) || '_' || p_client_id::text || '_' || lower(p_account_email);
  v_id      uuid;
  v_payload jsonb := jsonb_build_object(
    'access_token',  p_access_token,
    'refresh_token', p_refresh_token,
    'token_type',    p_token_type,
    'expires_at',    p_expires_at
  );
BEGIN
  SELECT id INTO v_id FROM vault.secrets WHERE name = v_name;
  IF v_id IS NULL THEN
    PERFORM vault.create_secret(v_payload::text, v_name,
      'OAuth tokens: ' || p_provider || ' / ' || p_account_email);
  ELSE
    PERFORM vault.update_secret(v_id, v_payload::text, v_name,
      'OAuth tokens: ' || p_provider || ' / ' || p_account_email);
  END IF;

  IF p_is_default THEN
    UPDATE public.integration_tokens SET is_default = false
    WHERE client_id = p_client_id AND provider = p_provider AND is_default = true;
  END IF;

  INSERT INTO public.integration_tokens
    (client_id, provider, account_email, token_type, scopes, metadata, is_default, vault_secret_name, updated_at)
  VALUES
    (p_client_id, p_provider, lower(p_account_email), p_token_type, p_scopes, p_metadata, p_is_default, v_name, now())
  ON CONFLICT (client_id, provider, account_email) DO UPDATE SET
    token_type        = EXCLUDED.token_type,
    scopes            = EXCLUDED.scopes,
    metadata          = EXCLUDED.metadata,
    is_default        = EXCLUDED.is_default,
    vault_secret_name = EXCLUDED.vault_secret_name,
    updated_at        = now();
END;
$$;


ALTER FUNCTION "public"."upsert_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text", "p_access_token" "text", "p_refresh_token" "text", "p_token_type" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_metadata" "jsonb", "p_is_default" boolean) OWNER TO "postgres";


CREATE FOREIGN DATA WRAPPER "bigquery_wrapper" HANDLER "extensions"."big_query_fdw_handler" VALIDATOR "extensions"."big_query_fdw_validator";




CREATE TABLE IF NOT EXISTS "_trace"."onboarding_events" (
    "id" bigint NOT NULL,
    "at" timestamp with time zone DEFAULT "clock_timestamp"() NOT NULL,
    "table_name" "text" NOT NULL,
    "op" "text" NOT NULL,
    "pk" "text",
    "client_id" "uuid",
    "changed_cols" "text"[],
    "payload" "jsonb",
    "session_user_name" "text" DEFAULT SESSION_USER,
    "app_user" "text" DEFAULT "current_setting"('request.jwt.claim.sub'::"text", true)
);


ALTER TABLE "_trace"."onboarding_events" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "_trace"."onboarding_events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "_trace"."onboarding_events_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "_trace"."onboarding_events_id_seq" OWNED BY "_trace"."onboarding_events"."id";



CREATE TABLE IF NOT EXISTS "admin"."tenant_wipe_audit" (
    "audit_id" bigint NOT NULL,
    "job_id" "uuid" NOT NULL,
    "table_name" "text" NOT NULL,
    "batch_no" integer NOT NULL,
    "rows_deleted" integer NOT NULL,
    "duration_ms" integer NOT NULL,
    "at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "admin"."tenant_wipe_audit" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "admin"."tenant_wipe_audit_audit_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "admin"."tenant_wipe_audit_audit_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "admin"."tenant_wipe_audit_audit_id_seq" OWNED BY "admin"."tenant_wipe_audit"."audit_id";



CREATE TABLE IF NOT EXISTS "admin"."tenant_wipe_jobs" (
    "job_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "reason" "text" NOT NULL,
    "requested_by" "uuid",
    "status" "text" DEFAULT 'queued'::"text" NOT NULL,
    "current_table" "text",
    "last_pk" "text",
    "rows_deleted_total" bigint DEFAULT 0 NOT NULL,
    "rows_total_estimate" bigint,
    "progress_pct" numeric(5,2) DEFAULT 0 NOT NULL,
    "error" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "started_at" timestamp with time zone,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    CONSTRAINT "tenant_wipe_jobs_status_check" CHECK (("status" = ANY (ARRAY['queued'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "admin"."tenant_wipe_jobs" OWNER TO "postgres";


CREATE OR REPLACE VIEW "admin"."v_active_wipes" AS
 SELECT "job_id",
    "client_id",
    "status",
    "current_table",
    "rows_deleted_total",
    "progress_pct",
    "started_at",
    (EXTRACT(epoch FROM ("now"() - "started_at")))::integer AS "elapsed_sec",
    "error"
   FROM "admin"."tenant_wipe_jobs" "j"
  WHERE ("status" = ANY (ARRAY['queued'::"text", 'running'::"text", 'failed'::"text"]))
  ORDER BY "created_at";


ALTER VIEW "admin"."v_active_wipes" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "admin"."wipe_table_priority" (
    "table_fqn" "text" NOT NULL,
    "priority" integer DEFAULT 100 NOT NULL
);


ALTER TABLE "admin"."wipe_table_priority" OWNER TO "postgres";


CREATE OR REPLACE VIEW "admin"."v_wipe_target_tables" AS
 SELECT ((("fk"."child_schema")::"text" || '.'::"text") || ("fk"."child_table")::"text") AS "table_fqn",
    "fk"."child_schema",
    "fk"."child_table",
    "fk"."fk_column",
    "fk"."pk_column",
    COALESCE("p"."priority", 1000) AS "priority"
   FROM (( SELECT DISTINCT "nsp"."nspname" AS "child_schema",
            "cls"."relname" AS "child_table",
            "att"."attname" AS "fk_column",
            ( SELECT "a"."attname"
                   FROM ("pg_index" "i"
                     JOIN "pg_attribute" "a" ON ((("a"."attrelid" = "i"."indrelid") AND ("a"."attnum" = ANY (("i"."indkey")::smallint[])))))
                  WHERE (("i"."indrelid" = "cls"."oid") AND "i"."indisprimary")
                  ORDER BY ("array_position"(("i"."indkey")::integer[], ("a"."attnum")::integer))
                 LIMIT 1) AS "pk_column"
           FROM ((((("pg_constraint" "con"
             JOIN "pg_class" "cls" ON (("cls"."oid" = "con"."conrelid")))
             JOIN "pg_namespace" "nsp" ON (("nsp"."oid" = "cls"."relnamespace")))
             JOIN "pg_attribute" "att" ON ((("att"."attrelid" = "con"."conrelid") AND ("att"."attnum" = ANY ("con"."conkey")))))
             JOIN "pg_class" "rcls" ON (("rcls"."oid" = "con"."confrelid")))
             JOIN "pg_namespace" "rnsp" ON (("rnsp"."oid" = "rcls"."relnamespace")))
          WHERE (("con"."contype" = 'f'::"char") AND ("rcls"."relname" = 'clientes_blu'::"name") AND ("rnsp"."nspname" = 'public'::"name") AND ("att"."attname" = 'client_id'::"name"))) "fk"
     LEFT JOIN "admin"."wipe_table_priority" "p" ON (("p"."table_fqn" = ((("fk"."child_schema")::"text" || '.'::"text") || ("fk"."child_table")::"text"))))
  WHERE ("fk"."pk_column" IS NOT NULL);


ALTER VIEW "admin"."v_wipe_target_tables" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_clientes" (
    "customer_id" bigint NOT NULL,
    "client_id" "uuid",
    "cpf_cnpj" "text",
    "nome" "text",
    "telefone" "text",
    "endereco_cidade" "text",
    "endereco_uf" "text",
    "total_pedidos" bigint DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "ticket_medio" numeric(15,2) DEFAULT 0,
    "quantidade_total" numeric DEFAULT 0,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_primeira_compra" "date",
    "data_ultima_compra" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "nps_score" numeric,
    "nps_data_coletada" "date",
    "nps_detalhes" "jsonb"
);


ALTER TABLE "analytics_v2"."dim_clientes" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_clientes" ALTER COLUMN "customer_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_clientes_cliente_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_datas" (
    "data_id" bigint NOT NULL,
    "data" "date" NOT NULL,
    "ano" integer NOT NULL,
    "mes" integer NOT NULL,
    "dia" integer NOT NULL,
    "numero_dia_semana" integer,
    "numero_semana_ano" integer,
    "numero_semestre" integer,
    "periodo_trimestral" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "analytics_v2"."dim_datas" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_datas" ALTER COLUMN "data_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_datas_data_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_fornecedores" (
    "fornecedor_id" bigint NOT NULL,
    "client_id" "uuid",
    "cnpj" "text",
    "nome" "text",
    "telefone" "text",
    "endereco_cidade" "text",
    "endereco_uf" "text",
    "total_pedidos_recebidos" bigint DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "ticket_medio" numeric(15,2) DEFAULT 0,
    "total_produtos_fornecidos" bigint DEFAULT 0,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_primeira_transacao" "date",
    "data_ultima_transacao" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "category" "text",
    "tags" "text"[],
    "rating" numeric,
    "performance_summary" "text",
    "contact_email" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    CONSTRAINT "dim_fornecedores_rating_check" CHECK ((("rating" >= (0)::numeric) AND ("rating" <= (5)::numeric)))
);


ALTER TABLE "analytics_v2"."dim_fornecedores" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_fornecedores" ALTER COLUMN "fornecedor_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_fornecedores_fornecedor_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_inventory" (
    "inventory_id" bigint NOT NULL,
    "client_id" "uuid",
    "sku" "text",
    "nome" "text",
    "quantidade_total_vendida" numeric DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "preco_medio" numeric(15,2) DEFAULT 0,
    "total_pedidos" bigint DEFAULT 0,
    "quantidade_media_por_pedido" numeric,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_ultima_venda" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "estoque_minimo" numeric
);


ALTER TABLE "analytics_v2"."dim_inventory" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_inventory" ALTER COLUMN "inventory_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_inventory_inventory_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."fato_transacoes" (
    "transacao_id" "text" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "data_competencia_id" bigint,
    "customer_id" bigint,
    "fornecedor_id" bigint,
    "produto_id" bigint,
    "documento" "text",
    "quantidade" numeric,
    "valor_unitario" numeric(15,2),
    "valor" numeric(15,2),
    "status" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "tipo_transacao" "text",
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "tipo_lancamento" "text",
    "categoria" "text",
    "subcategoria" "text",
    "entry_type" "text",
    CONSTRAINT "fato_transacoes_entry_type_check" CHECK (("entry_type" = ANY (ARRAY['revenue'::"text", 'purchase'::"text", 'expense'::"text", 'banking'::"text"])))
);


ALTER TABLE "analytics_v2"."fato_transacoes" OWNER TO "postgres";


COMMENT ON COLUMN "analytics_v2"."fato_transacoes"."tipo_transacao" IS 'venda | compra | devolucao | ajuste';



COMMENT ON COLUMN "analytics_v2"."fato_transacoes"."updated_at" IS 'Cursor for incremental ETL sync via reg_jobs';



COMMENT ON COLUMN "analytics_v2"."fato_transacoes"."entry_type" IS 'System-derived transaction direction: revenue | purchase | expense | banking. BQ NF-e: derived from CNPJ cross-reference with clientes_blu.cpf_cnpj. Polp: CREDIT=revenue, DEBIT=expense. Never user-mapped — always set by backend classification logic.';



CREATE TABLE IF NOT EXISTS "analytics_v2"."ingest_staging" (
    "id" bigint NOT NULL,
    "job_id" "uuid" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "source_id" "uuid" NOT NULL,
    "row_index" integer NOT NULL,
    "raw_data" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "analytics_v2"."ingest_staging" OWNER TO "postgres";


COMMENT ON TABLE "analytics_v2"."ingest_staging" IS 'Unified raw staging for CSV/xlsx uploads and BigQuery (and future) ingestions. Rows are consumed and deleted by analytics_v2.apply_staging_to_facts(job_id).';



CREATE SEQUENCE IF NOT EXISTS "analytics_v2"."ingest_staging_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "analytics_v2"."ingest_staging_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "analytics_v2"."ingest_staging_id_seq" OWNED BY "analytics_v2"."ingest_staging"."id";



CREATE MATERIALIZED VIEW "analytics_v2"."mv_distribuicao_regional" AS
 SELECT "dc"."client_id",
    "dc"."endereco_uf",
    "dc"."endereco_cidade",
    COALESCE("sum"("ft"."valor"), (0)::numeric) AS "receita_total",
    ("count"(DISTINCT "dc"."customer_id"))::integer AS "total_clientes",
    ("count"(DISTINCT "ft"."transacao_id"))::integer AS "total_pedidos"
   FROM ("analytics_v2"."dim_clientes" "dc"
     LEFT JOIN "analytics_v2"."fato_transacoes" "ft" ON ((("dc"."customer_id" = "ft"."customer_id") AND ("dc"."client_id" = "ft"."client_id") AND ("ft"."tipo_transacao" = 'venda'::"text"))))
  GROUP BY "dc"."client_id", "dc"."endereco_uf", "dc"."endereco_cidade"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_distribuicao_regional" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_resumo_dashboard" AS
 WITH "base" AS (
         SELECT "ft"."client_id",
            ("count"(DISTINCT "dc"."customer_id") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")))::integer AS "total_clientes",
            ("count"(DISTINCT "df"."fornecedor_id") FILTER (WHERE ("ft"."tipo_transacao" = 'compra'::"text")))::integer AS "total_fornecedores",
            ("count"(DISTINCT "di"."inventory_id") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")))::integer AS "total_produtos",
            ("count"(DISTINCT "ft"."transacao_id") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")))::integer AS "total_pedidos",
            COALESCE("sum"("ft"."valor") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")), (0)::numeric) AS "receita_total",
            COALESCE("sum"("ft"."quantidade") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")), (0)::numeric) AS "quantidade_total_vendida",
                CASE
                    WHEN ("count"(DISTINCT "ft"."transacao_id") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")) > 0) THEN (COALESCE("sum"("ft"."valor") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")), (0)::numeric) / ("count"(DISTINCT "ft"."transacao_id") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")))::numeric)
                    ELSE (0)::numeric
                END AS "ticket_medio",
            ("count"(DISTINCT "dc"."endereco_uf") FILTER (WHERE ("ft"."tipo_transacao" = 'venda'::"text")))::integer AS "total_regioes",
                CASE
                    WHEN ("count"(DISTINCT "df"."fornecedor_id") FILTER (WHERE ("ft"."tipo_transacao" = 'compra'::"text")) > 0) THEN (("count"(DISTINCT "ft"."transacao_id") FILTER (WHERE ("ft"."tipo_transacao" = 'compra'::"text")))::numeric / ("count"(DISTINCT "df"."fornecedor_id") FILTER (WHERE ("ft"."tipo_transacao" = 'compra'::"text")))::numeric)
                    ELSE (0)::numeric
                END AS "frequencia_media_fornecedores",
            ("count"(DISTINCT "dc"."customer_id") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND ("dd"."data" >= (CURRENT_DATE - 30)))))::integer AS "clientes_ativos",
            COALESCE("sum"("ft"."valor") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date"))), (0)::numeric) AS "receita_mes_atual",
            COALESCE("sum"("ft"."quantidade") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date"))), (0)::numeric) AS "quantidade_mes_atual",
            ("count"(DISTINCT "dc"."customer_id") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date"))))::integer AS "clientes_mes_atual",
            ("count"(DISTINCT "di"."inventory_id") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date"))))::integer AS "produtos_mes_atual",
            ("count"(DISTINCT "df"."fornecedor_id") FILTER (WHERE (("ft"."tipo_transacao" = 'compra'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date"))))::integer AS "fornecedores_mes_atual",
            COALESCE("sum"("ft"."valor") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date"))), (0)::numeric) AS "receita_mes_anterior",
            COALESCE("sum"("ft"."quantidade") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date"))), (0)::numeric) AS "quantidade_mes_anterior",
            ("count"(DISTINCT "dc"."customer_id") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date"))))::integer AS "clientes_mes_anterior",
            ("count"(DISTINCT "di"."inventory_id") FILTER (WHERE (("ft"."tipo_transacao" = 'venda'::"text") AND (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date"))))::integer AS "produtos_mes_anterior"
           FROM (((("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."customer_id" = "dc"."customer_id") AND ("dc"."client_id" = "ft"."client_id"))))
             LEFT JOIN "analytics_v2"."dim_fornecedores" "df" ON ((("ft"."fornecedor_id" = "df"."fornecedor_id") AND ("df"."client_id" = "ft"."client_id"))))
             LEFT JOIN "analytics_v2"."dim_inventory" "di" ON ((("ft"."produto_id" = "di"."inventory_id") AND ("di"."client_id" = "ft"."client_id"))))
          GROUP BY "ft"."client_id"
        ), "novos_agg" AS (
         SELECT "sub"."client_id",
            ("count"(*))::integer AS "clientes_novos"
           FROM ( SELECT "ft"."client_id",
                    "ft"."customer_id"
                   FROM ("analytics_v2"."fato_transacoes" "ft"
                     JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
                  WHERE (("ft"."customer_id" IS NOT NULL) AND ("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
                  GROUP BY "ft"."client_id", "ft"."customer_id"
                 HAVING ("min"("dd"."data") >= ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")) "sub"
          GROUP BY "sub"."client_id"
        )
 SELECT "b"."client_id",
    "b"."total_clientes",
    "b"."total_fornecedores",
    "b"."total_produtos",
    "b"."total_pedidos",
    "b"."receita_total",
    "b"."quantidade_total_vendida",
    "b"."ticket_medio",
    "b"."receita_mes_atual",
    "b"."quantidade_mes_atual",
    "b"."clientes_mes_atual",
    "b"."produtos_mes_atual",
    "b"."fornecedores_mes_atual",
        CASE
            WHEN ("b"."receita_mes_anterior" > (0)::numeric) THEN (("b"."receita_mes_atual" - "b"."receita_mes_anterior") / "b"."receita_mes_anterior")
            ELSE (0)::numeric
        END AS "crescimento_receita",
        CASE
            WHEN ("b"."clientes_mes_anterior" > 0) THEN ((("b"."clientes_mes_atual" - "b"."clientes_mes_anterior"))::numeric / ("b"."clientes_mes_anterior")::numeric)
            ELSE (0)::numeric
        END AS "crescimento_clientes",
        CASE
            WHEN ("b"."produtos_mes_anterior" > 0) THEN ((("b"."produtos_mes_atual" - "b"."produtos_mes_anterior"))::numeric / ("b"."produtos_mes_anterior")::numeric)
            ELSE (0)::numeric
        END AS "crescimento_produtos",
        CASE
            WHEN ("b"."quantidade_mes_anterior" > (0)::numeric) THEN (("b"."quantidade_mes_atual" - "b"."quantidade_mes_anterior") / "b"."quantidade_mes_anterior")
            ELSE (0)::numeric
        END AS "crescimento_quantidade",
    "b"."frequencia_media_fornecedores",
    "b"."total_regioes",
    "to_char"((CURRENT_DATE - '1 mon'::interval), 'Mon/YYYY'::"text") AS "ultimo_mes",
    "b"."clientes_ativos",
    COALESCE("na"."clientes_novos", 0) AS "clientes_novos",
    CURRENT_TIMESTAMP AS "gerado_em"
   FROM ("base" "b"
     LEFT JOIN "novos_agg" "na" ON (("b"."client_id" = "na"."client_id")))
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_resumo_dashboard" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_series_temporal" AS
 WITH "base" AS (
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "periodo",
            "dd"."data" AS "data_periodo",
            'receita'::"text" AS "tipo_grafico",
            'total'::"text" AS "dimensao",
            COALESCE("sum"("ft"."valor"), (0)::numeric) AS "total"
           FROM ("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
          WHERE (("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'clientes'::"text" AS "text",
            'total'::"text" AS "text",
            ("count"(DISTINCT "dc"."customer_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."customer_id" = "dc"."customer_id") AND ("dc"."client_id" = "ft"."client_id"))))
          WHERE (("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'fornecedores'::"text" AS "text",
            'total'::"text" AS "text",
            ("count"(DISTINCT "df"."fornecedor_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_fornecedores" "df" ON ((("ft"."fornecedor_id" = "df"."fornecedor_id") AND ("df"."client_id" = "ft"."client_id"))))
          WHERE (("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'compra'::"text"))
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'produtos'::"text" AS "text",
            'total'::"text" AS "text",
            ("count"(DISTINCT "di"."inventory_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_inventory" "di" ON ((("ft"."produto_id" = "di"."inventory_id") AND ("di"."client_id" = "ft"."client_id"))))
          WHERE (("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'pedidos'::"text" AS "text",
            'total'::"text" AS "text",
            ("count"(DISTINCT "ft"."transacao_id"))::numeric AS "count"
           FROM ("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
          WHERE (("dd"."data" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
          GROUP BY "ft"."client_id", "dd"."data"
        )
 SELECT "client_id",
    "periodo",
    "data_periodo",
    "tipo_grafico",
    "dimensao",
    "total",
    "sum"("total") OVER (PARTITION BY "client_id", "tipo_grafico", "dimensao" ORDER BY "data_periodo" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "total_cumulativo"
   FROM "base"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_series_temporal" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_ultimos_pedidos" AS
 SELECT "ft"."client_id",
    "ft"."transacao_id" AS "pedido_id",
    "dc"."cpf_cnpj" AS "cliente_cpf_cnpj",
    "ft"."valor" AS "valor_pedido",
    "ft"."quantidade" AS "qtd_produtos",
    "row_number"() OVER (PARTITION BY "ft"."client_id" ORDER BY "ft"."created_at" DESC) AS "ordem"
   FROM ("analytics_v2"."fato_transacoes" "ft"
     LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."customer_id" = "dc"."customer_id") AND ("dc"."client_id" = "ft"."client_id"))))
  WHERE (("ft"."created_at" IS NOT NULL) AND ("ft"."tipo_transacao" = 'venda'::"text"))
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_ultimos_pedidos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "analytics_v2"."reg_jobs" (
    "job_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "job_type" "text" DEFAULT 'bigquery_sync'::"text" NOT NULL,
    "credential_id" bigint,
    "resource_type" "text",
    "sync_mode" "text" DEFAULT 'incremental'::"text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "input_params" "jsonb" DEFAULT '{}'::"jsonb",
    "output" "jsonb",
    "rows_inserted" bigint DEFAULT 0,
    "progress_pct" integer DEFAULT 0,
    "error_message" "text",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "duration_seconds" numeric,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "retry_count" integer DEFAULT 0 NOT NULL,
    CONSTRAINT "reg_jobs_job_type_check" CHECK (("job_type" = ANY (ARRAY['bigquery_sync'::"text", 'connector_sync'::"text", 'analytics_etl'::"text", 'custom'::"text", 'csv_sync'::"text", 'refresh_dashboards'::"text"]))),
    CONSTRAINT "reg_jobs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'cancelled'::"text"]))),
    CONSTRAINT "reg_jobs_sync_mode_check" CHECK (("sync_mode" = ANY (ARRAY['incremental'::"text", 'full'::"text"])))
);


ALTER TABLE "analytics_v2"."reg_jobs" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_distribuicao_regional" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "endereco_uf",
    "endereco_cidade",
    "receita_total",
    "total_clientes",
    "total_pedidos"
   FROM "analytics_v2"."mv_distribuicao_regional"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_distribuicao_regional" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_resumo_dashboard" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "total_clientes",
    "total_fornecedores",
    "total_produtos",
    "total_pedidos",
    "receita_total",
    "quantidade_total_vendida",
    "ticket_medio",
    "receita_mes_atual",
    "quantidade_mes_atual",
    "clientes_mes_atual",
    "produtos_mes_atual",
    "fornecedores_mes_atual",
    "crescimento_receita",
    "crescimento_clientes",
    "crescimento_produtos",
    "crescimento_quantidade",
    "frequencia_media_fornecedores",
    "total_regioes",
    "ultimo_mes",
    "clientes_ativos",
    "clientes_novos",
    "gerado_em"
   FROM "analytics_v2"."mv_resumo_dashboard"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_resumo_dashboard" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_series_temporal" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "periodo",
    "data_periodo",
    "tipo_grafico",
    "dimensao",
    "total",
    "total_cumulativo"
   FROM "analytics_v2"."mv_series_temporal"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_series_temporal" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_ultimos_pedidos" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "pedido_id",
    "cliente_cpf_cnpj",
    "valor_pedido",
    "qtd_produtos",
    "ordem"
   FROM "analytics_v2"."mv_ultimos_pedidos"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_ultimos_pedidos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "fdw"."staging_transacoes" (
    "id" bigint NOT NULL,
    "job_id" "uuid" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "raw_data" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "fdw"."staging_transacoes" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "fdw"."staging_transacoes_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "fdw"."staging_transacoes_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "fdw"."staging_transacoes_id_seq" OWNED BY "fdw"."staging_transacoes"."id";



CREATE TABLE IF NOT EXISTS "public"."clientes_blu" (
    "client_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "api_key" "text",
    "nome_empresa" "text" DEFAULT 'Empresa'::"text" NOT NULL,
    "tipo_cliente" "text" DEFAULT 'standard'::"text",
    "tier" "text" DEFAULT 'free'::"text",
    "collection_rag" "text" DEFAULT 'default_collection'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "external_user_id" "text",
    "onboarding_state" "jsonb" DEFAULT '{}'::"jsonb",
    "onboarding_completed_at" timestamp with time zone,
    "company_profile" "jsonb" DEFAULT '{}'::"jsonb",
    "brand_voice" "jsonb" DEFAULT '{}'::"jsonb",
    "team_structure" "jsonb" DEFAULT '{}'::"jsonb",
    "policies" "jsonb" DEFAULT '{}'::"jsonb",
    "data_schema" "jsonb" DEFAULT '{}'::"jsonb",
    "available_tools" "jsonb" DEFAULT '{}'::"jsonb",
    "cpf_cnpj" "text",
    "deleted_at" timestamp with time zone,
    "ui_prefs" "jsonb" DEFAULT '{}'::"jsonb",
    "email" "text",
    "email_domain" "text" GENERATED ALWAYS AS (
CASE
    WHEN (("email" IS NOT NULL) AND (POSITION(('@'::"text") IN ("email")) > 0)) THEN "split_part"("email", '@'::"text", 2)
    ELSE NULL::"text"
END) STORED,
    "is_test_account" boolean DEFAULT false NOT NULL,
    "deletion_status" "text" DEFAULT 'active'::"text",
    "deletion_requested_at" timestamp with time zone,
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text" NOT NULL,
    CONSTRAINT "clientes_blu_auth_check" CHECK ((("api_key" IS NOT NULL) OR ("external_user_id" IS NOT NULL))),
    CONSTRAINT "clientes_blu_deletion_status_check" CHECK (("deletion_status" = ANY (ARRAY['active'::"text", 'deleting'::"text", 'deleted'::"text"])))
);


ALTER TABLE "public"."clientes_blu" OWNER TO "postgres";


COMMENT ON COLUMN "public"."clientes_blu"."email" IS 'Primary contact email for the client business.';



COMMENT ON COLUMN "public"."clientes_blu"."email_domain" IS 'Derived email domain — used for meeting participant matching.';



COMMENT ON COLUMN "public"."clientes_blu"."is_test_account" IS 'TRUE para contas internas de teste/QA/demo. Excluídas de production_clientes_blu, métricas agregadas, billing e alertas. Default false (clientes reais).';



COMMENT ON COLUMN "public"."clientes_blu"."timezone" IS 'IANA timezone used to evaluate cron routine schedules (P1-6). Per-subscription override: client_routines.trigger_config->>timezone.';



CREATE OR REPLACE VIEW "public"."active_clientes_blu" AS
 SELECT "client_id",
    "api_key",
    "nome_empresa",
    "tipo_cliente",
    "tier",
    "collection_rag",
    "created_at",
    "updated_at",
    "external_user_id",
    "onboarding_state",
    "onboarding_completed_at",
    "company_profile",
    "brand_voice",
    "team_structure",
    "policies",
    "data_schema",
    "available_tools",
    "cpf_cnpj",
    "deleted_at"
   FROM "public"."clientes_blu"
  WHERE ("deleted_at" IS NULL);


ALTER VIEW "public"."active_clientes_blu" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."agent_catalog" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "icon" "text",
    "agent_config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "prompt_name" "text" NOT NULL,
    "required_context" "jsonb" DEFAULT '[]'::"jsonb",
    "required_files" "jsonb" DEFAULT '{}'::"jsonb",
    "requires_google" boolean DEFAULT false,
    "tier_required" "text" DEFAULT 'BASIC'::"text",
    "landing_slug" "text",
    "workflow_graph" "jsonb",
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."agent_catalog" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."agent_lists" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "list_type" "text" NOT NULL,
    "name" "text",
    "items" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'open'::"text" NOT NULL,
    "created_by" "text",
    "session_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "agent_lists_status_check" CHECK (("status" = ANY (ARRAY['open'::"text", 'active'::"text", 'closed'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."agent_lists" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_lists" IS 'Generic persistent list store for agent operations. Keyed by list_type — each agent/operation owns its namespace. Replaces: rfq_requests. Future: buying_list, approval_queue, checklist.';



CREATE TABLE IF NOT EXISTS "public"."agent_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "agent_catalog_id" "uuid" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "collected_context" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "uploaded_document_ids" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."agent_sessions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."app_config" (
    "key" "text" NOT NULL,
    "value" "text" NOT NULL
);


ALTER TABLE "public"."app_config" OWNER TO "postgres";


COMMENT ON TABLE "public"."app_config" IS 'Runtime key/value configuration for the platform. Values that must be set for routine dispatch: agent_api_core_url (e.g. https://api.example.com/v1), agent_api_routine_dispatch_token (matches ROUTINE_DISPATCH_TOKEN env var in agent_api).';



CREATE TABLE IF NOT EXISTS "public"."artifact_log" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "execution_id" "uuid" NOT NULL,
    "step_id" "text" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "artifact_type" "text" NOT NULL,
    "function_name" "text" NOT NULL,
    "status" "text" DEFAULT 'claimed'::"text" NOT NULL,
    "outputs" "jsonb",
    "error" "text",
    "claimed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "sent_at" timestamp with time zone,
    CONSTRAINT "artifact_log_status_chk" CHECK (("status" = ANY (ARRAY['claimed'::"text", 'sent'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."artifact_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."artifact_log" IS 'Sprint 4/D2 — Dedupe de artefatos side-effectful. UNIQUE(execution_id, step_id) impede reentrega de email/whatsapp/document em retries/redispatches.';



CREATE TABLE IF NOT EXISTS "public"."audit_log" (
    "id" bigint NOT NULL,
    "client_id" "uuid",
    "actor_id" "text",
    "action" "text" NOT NULL,
    "entity_type" "text",
    "entity_id" "text",
    "payload" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."audit_log" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."audit_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."audit_log_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."audit_log_id_seq" OWNED BY "public"."audit_log"."id";



CREATE TABLE IF NOT EXISTS "public"."bigquery_foreign_tables" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "table_name" "text" NOT NULL,
    "bigquery_table" "text" NOT NULL,
    "server_name" "text" NOT NULL,
    "columns" "jsonb" NOT NULL,
    "location" "text" DEFAULT 'US'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "credential_id" bigint
);


ALTER TABLE "public"."bigquery_foreign_tables" OWNER TO "postgres";


COMMENT ON TABLE "public"."bigquery_foreign_tables" IS 'Registry of all BigQuery foreign tables';



CREATE TABLE IF NOT EXISTS "public"."bigquery_servers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "server_name" "text" NOT NULL,
    "project_id" "text" NOT NULL,
    "dataset_id" "text" NOT NULL,
    "vault_key_id" "uuid" NOT NULL,
    "location" "text" DEFAULT 'US'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."bigquery_servers" OWNER TO "postgres";


COMMENT ON TABLE "public"."bigquery_servers" IS 'Metadata for BigQuery foreign servers per client';



CREATE TABLE IF NOT EXISTS "public"."calendar_settings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "calendar_id" "text",
    "enabled" boolean DEFAULT false NOT NULL,
    "range_days" integer DEFAULT 30 NOT NULL,
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "provider" "text",
    "calendar_name" "text"
);


ALTER TABLE "public"."calendar_settings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."calendar_watch_channels" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "channel_id" "text" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "calendar_id" "text" DEFAULT 'primary'::"text" NOT NULL,
    "resource_id" "text",
    "expires_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."calendar_watch_channels" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."canonical_columns" (
    "id" integer NOT NULL,
    "table_name" "text" NOT NULL,
    "column_name" "text" NOT NULL,
    "data_type" "text" NOT NULL,
    "is_required" boolean DEFAULT false NOT NULL,
    "description" "text" NOT NULL,
    "examples" "text"[] DEFAULT '{}'::"text"[],
    "category" "text" DEFAULT 'mappable'::"text" NOT NULL,
    CONSTRAINT "canonical_columns_category_check" CHECK (("category" = ANY (ARRAY['mappable'::"text", 'aggregation'::"text", 'cluster'::"text", 'dimension'::"text", 'system'::"text"])))
);


ALTER TABLE "public"."canonical_columns" OWNER TO "postgres";


COMMENT ON TABLE "public"."canonical_columns" IS 'Descriptions for user-mappable canonical columns, injected into LLM prompts during CSV column matching.';



COMMENT ON COLUMN "public"."canonical_columns"."category" IS 'mappable=user CSV columns | aggregation=computed metrics | cluster=ML scoring | dimension=calendar attrs | system=internal PKs/FKs/timestamps';



CREATE SEQUENCE IF NOT EXISTS "public"."canonical_columns_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."canonical_columns_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."canonical_columns_id_seq" OWNED BY "public"."canonical_columns"."id";



CREATE TABLE IF NOT EXISTS "public"."client_approval_rules" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "agent_slug" "text",
    "rule_type" "text" NOT NULL,
    "condition" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "action" "text" DEFAULT 'auto_approve'::"text",
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_approval_rules_action_check" CHECK (("action" = ANY (ARRAY['auto_approve'::"text", 'skip_review'::"text"]))),
    CONSTRAINT "client_approval_rules_rule_type_check" CHECK (("rule_type" = ANY (ARRAY['amount_limit'::"text", 'category'::"text", 'supplier'::"text", 'similarity'::"text"])))
);


ALTER TABLE "public"."client_approval_rules" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_approval_stats" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "total_approved" integer DEFAULT 0,
    "total_rejected" integer DEFAULT 0,
    "total_edited" integer DEFAULT 0,
    "total_snoozed" integer DEFAULT 0,
    "trust_level" "text" DEFAULT 'manual'::"text",
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "client_approval_stats_trust_level_check" CHECK (("trust_level" = ANY (ARRAY['manual'::"text", 'similar_toggle'::"text", 'rules'::"text", 'full_config'::"text"])))
);


ALTER TABLE "public"."client_approval_stats" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_data_sources" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "credential_id" bigint,
    "source_type" "text" NOT NULL,
    "resource_type" "text" NOT NULL,
    "storage_type" "text" NOT NULL,
    "storage_location" "text" NOT NULL,
    "column_mapping" "jsonb",
    "source_columns" "jsonb",
    "source_sample_data" "jsonb",
    "sync_status" "text" DEFAULT 'pending'::"text",
    "last_synced_at" timestamp with time zone,
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "unmapped_columns" "jsonb",
    "needs_review_columns" "jsonb",
    "match_confidence" "jsonb",
    "detected_entity_context" "text",
    "auto_column_mapping" "jsonb",
    "ignored_columns" "text"[],
    "is_auto_generated" boolean DEFAULT false,
    "reviewed_at" timestamp with time zone,
    "user_column_changes" "jsonb",
    "ingestion_quality" "jsonb",
    "watermark_column" "text",
    "last_watermark_value" "text",
    "drive_file_id" "text",
    "drive_modified_time" timestamp with time zone,
    "integration_token_id" "uuid",
    "schema_type" "text"
);


ALTER TABLE "public"."client_data_sources" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_dimension_kpis" (
    "client_id" "uuid" NOT NULL,
    "dimension" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."client_dimension_kpis" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_enabled_agents" (
    "client_id" "uuid" NOT NULL,
    "agent_slug" "text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "enabled_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "current_status" "text" DEFAULT 'idle'::"text",
    "last_activity_at" timestamp with time zone,
    "pending_count" integer DEFAULT 0
);


ALTER TABLE "public"."client_enabled_agents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_goals" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "dimension" "text" NOT NULL,
    "title" "text" NOT NULL,
    "description" "text",
    "target_value" numeric,
    "current_value" numeric,
    "unit" "text",
    "deadline" "date",
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "action_plan" "jsonb",
    "source_agent" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_goals_dimension_check" CHECK (("dimension" = ANY (ARRAY['compras'::"text", 'financeiro'::"text", 'clientes'::"text", 'agenda'::"text", 'estrategia'::"text", 'documentos'::"text", 'geral'::"text"]))),
    CONSTRAINT "client_goals_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'achieved'::"text", 'cancelled'::"text", 'paused'::"text"])))
);


ALTER TABLE "public"."client_goals" OWNER TO "postgres";


COMMENT ON TABLE "public"."client_goals" IS 'Metas de negócio por dimensão. Criadas pelo usuário ou agentes; incluídas no snapshot de memória para contexto de objetivos ativos.';



CREATE TABLE IF NOT EXISTS "public"."client_insights" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "title" "text" NOT NULL,
    "body" "text",
    "severity" "text" DEFAULT 'info'::"text",
    "dismissed" boolean DEFAULT false,
    "dismissed_at" timestamp with time zone,
    "generated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone,
    "kpi" "text",
    "observation" "text",
    "recommendation" "text",
    "metric_value" numeric,
    "baseline_value" numeric,
    "variance_pct" numeric,
    "run_date" "date",
    "prompt_version" "text",
    "room" "text",
    "dimension" "text" DEFAULT 'geral'::"text",
    CONSTRAINT "client_insights_severity_check" CHECK (("severity" = ANY (ARRAY['info'::"text", 'warning'::"text", 'error'::"text"])))
);


ALTER TABLE "public"."client_insights" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_knowledge_documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "document_type_id" "text" NOT NULL,
    "status" "text" DEFAULT 'missing'::"text" NOT NULL,
    "source" "text",
    "vector_document_id" "uuid",
    "field_coverage" "jsonb" DEFAULT '{}'::"jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_knowledge_documents_status_check" CHECK (("status" = ANY (ARRAY['missing'::"text", 'partial'::"text", 'complete'::"text"])))
);


ALTER TABLE "public"."client_knowledge_documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_notification_preferences" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "notification_type" "text" NOT NULL,
    "channel" "text" NOT NULL,
    "enabled" boolean DEFAULT true,
    "quiet_hours_start" time without time zone,
    "quiet_hours_end" time without time zone,
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text",
    CONSTRAINT "client_notification_preferences_channel_check" CHECK (("channel" = ANY (ARRAY['email'::"text", 'push'::"text", 'in_app'::"text"])))
);


ALTER TABLE "public"."client_notification_preferences" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_users" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "auth_user_id" "uuid",
    "email" "text" NOT NULL,
    "name" "text",
    "role" "text" DEFAULT 'member'::"text" NOT NULL,
    "agent_permissions" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "action_permissions" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "invited_at" timestamp with time zone DEFAULT "now"(),
    "accepted_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_users_role_check" CHECK (("role" = ANY (ARRAY['owner'::"text", 'admin'::"text", 'manager'::"text", 'member'::"text"])))
);


ALTER TABLE "public"."client_users" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."cnpj_enrichments" (
    "cnpj" "text" NOT NULL,
    "brand" "text",
    "logo_url" "text",
    "colors" "jsonb",
    "social" "jsonb",
    "enriched_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."cnpj_enrichments" OWNER TO "postgres";


COMMENT ON TABLE "public"."cnpj_enrichments" IS 'Cache for Polp CNPJ enrichment API responses (brand, logo, colors, social)';



CREATE TABLE IF NOT EXISTS "public"."conversa" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."conversa" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."credencial_servico_externo" (
    "id" bigint NOT NULL,
    "client_id" "uuid" NOT NULL,
    "tipo" "text",
    "credenciais" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "nome" "text",
    "ativo" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "connection_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "nome_servico" "text",
    "tipo_servico" "text",
    "status" "text" DEFAULT 'pending'::"text",
    "vault_key_id" "uuid",
    CONSTRAINT "credencial_servico_externo_tipo_check" CHECK (("tipo" = ANY (ARRAY['bigquery'::"text", 'google_drive'::"text", 'google_sheets'::"text", 'google_docs'::"text", 'google_calendar'::"text"])))
);


ALTER TABLE "public"."credencial_servico_externo" OWNER TO "postgres";


COMMENT ON COLUMN "public"."credencial_servico_externo"."connection_metadata" IS 'Connection metadata: project_id, dataset_id, table_name, location for BigQuery; credentials for other platforms';



CREATE SEQUENCE IF NOT EXISTS "public"."credencial_servico_externo_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."credencial_servico_externo_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."credencial_servico_externo_id_seq" OWNED BY "public"."credencial_servico_externo"."id";



CREATE TABLE IF NOT EXISTS "public"."csv_import_staging" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "source_id" "uuid" NOT NULL,
    "rows" "jsonb" NOT NULL,
    "row_count" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."csv_import_staging" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."data_source_mappings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "credential_id" "uuid" NOT NULL,
    "resource_type" character varying(50) NOT NULL,
    "source_columns" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "mapping" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "unmapped_columns" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "confidence_scores" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "client_id" "uuid",
    CONSTRAINT "data_source_mappings_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['pending'::character varying, 'needs_review'::character varying, 'ready'::character varying, 'error'::character varying])::"text"[])))
);


ALTER TABLE "public"."data_source_mappings" OWNER TO "postgres";


COMMENT ON TABLE "public"."data_source_mappings" IS 'Armazena mapeamentos de colunas entre fontes externas e schema canônico Blu';



COMMENT ON COLUMN "public"."data_source_mappings"."source_columns" IS 'Lista de colunas descobertas na fonte original';



COMMENT ON COLUMN "public"."data_source_mappings"."mapping" IS 'Mapeamento coluna_origem -> coluna_blu confirmado';



COMMENT ON COLUMN "public"."data_source_mappings"."confidence_scores" IS 'Score de confiança (0-1) do match automático por coluna';



COMMENT ON COLUMN "public"."data_source_mappings"."status" IS 'pending=aguardando, needs_review=precisa revisão, ready=pronto, error=erro';



CREATE TABLE IF NOT EXISTS "public"."dimension_state" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "dimension" "text" NOT NULL,
    "summary" "text" NOT NULL,
    "structured" "jsonb",
    "valid_until" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "dimension_state_dimension_check" CHECK (("dimension" = ANY (ARRAY['compras'::"text", 'financeiro'::"text", 'clientes'::"text", 'agenda'::"text", 'estrategia'::"text", 'documentos'::"text"])))
);


ALTER TABLE "public"."dimension_state" OWNER TO "postgres";


COMMENT ON TABLE "public"."dimension_state" IS 'Estado compacto de cada dimensão de negócio. Escrito por Room Monitors, lido pelo snapshot de memória do agente principal.';



CREATE TABLE IF NOT EXISTS "public"."doc_templates" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "name" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "is_system" boolean DEFAULT false NOT NULL,
    "content" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."doc_templates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_versions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_id" "uuid" NOT NULL,
    "version_number" integer DEFAULT 1 NOT NULL,
    "editor_content" "jsonb",
    "summary" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."document_versions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "title" "text" DEFAULT 'Sem título'::"text" NOT NULL,
    "agent_slug" "text" DEFAULT 'documentos'::"text" NOT NULL,
    "editor_content" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "status" "text" DEFAULT 'published'::"text" NOT NULL,
    CONSTRAINT "documents_status_check" CHECK (("status" = ANY (ARRAY['draft'::"text", 'published'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


COMMENT ON COLUMN "public"."documents"."status" IS 'draft = gerado por agente aguardando aprovação HITL | published = aprovado/manual | archived = rejeitado';



CREATE TABLE IF NOT EXISTS "public"."frontend_events" (
    "id" bigint NOT NULL,
    "client_id" "uuid",
    "event_name" "text" NOT NULL,
    "properties" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."frontend_events" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."frontend_events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."frontend_events_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."frontend_events_id_seq" OWNED BY "public"."frontend_events"."id";



CREATE TABLE IF NOT EXISTS "public"."integration_configs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "provider" "text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."integration_configs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."integration_tokens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "provider" "text" NOT NULL,
    "account_email" "text" DEFAULT ''::"text" NOT NULL,
    "token_type" "text" DEFAULT 'Bearer'::"text",
    "scopes" "text"[],
    "is_default" boolean DEFAULT false,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "vault_secret_name" "text",
    "refresh_token_encrypted" "text",
    "access_token_encrypted" "text"
);


ALTER TABLE "public"."integration_tokens" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_agent_requirements" (
    "agent_slug" "text" NOT NULL,
    "document_type_id" "text" NOT NULL,
    "requirement_type" "text" NOT NULL,
    "coverage_threshold" numeric DEFAULT 0.8 NOT NULL,
    CONSTRAINT "knowledge_agent_requirements_requirement_type_check" CHECK (("requirement_type" = ANY (ARRAY['minimum'::"text", 'nice_to_have'::"text"])))
);


ALTER TABLE "public"."knowledge_agent_requirements" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_document_types" (
    "id" "text" NOT NULL,
    "domain_id" "text" NOT NULL,
    "subdomain_id" "text",
    "name" "text" NOT NULL,
    "type" "text" NOT NULL,
    "created_by" "text",
    "consumed_by" "text"[] DEFAULT '{}'::"text"[],
    "fields" "text"[] DEFAULT '{}'::"text"[],
    "status" "text" DEFAULT 'required'::"text" NOT NULL,
    "coverage_weight" numeric DEFAULT 1.0 NOT NULL,
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "sort_order" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "knowledge_document_types_status_check" CHECK (("status" = ANY (ARRAY['required'::"text", 'optional'::"text", 'generated'::"text"])))
);


ALTER TABLE "public"."knowledge_document_types" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_tag_definitions" (
    "tag" "text" NOT NULL,
    "description" "text",
    "consumed_by" "text"[] DEFAULT '{}'::"text"[]
);


ALTER TABLE "public"."knowledge_tag_definitions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."kpi_catalog" (
    "slug" "text" NOT NULL,
    "dimension" "text" NOT NULL,
    "label" "text" NOT NULL,
    "formula" "text" NOT NULL,
    "unit" "text" DEFAULT 'number'::"text" NOT NULL,
    "is_leading" boolean DEFAULT false NOT NULL,
    "tier_required" "text" DEFAULT 'BASIC'::"text" NOT NULL,
    "data_status" "text" DEFAULT 'live'::"text" NOT NULL,
    "rpc_column" "text",
    "description" "text",
    "references_url" "text",
    "sort_order" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "kpi_catalog_data_status_check" CHECK (("data_status" = ANY (ARRAY['live'::"text", 'proxy'::"text", 'external'::"text", 'pending_data'::"text"]))),
    CONSTRAINT "kpi_catalog_dimension_check" CHECK (("dimension" = ANY (ARRAY['finance'::"text", 'commercial'::"text", 'inventory'::"text", 'supply'::"text", 'marketing'::"text", 'admin'::"text"]))),
    CONSTRAINT "kpi_catalog_tier_required_check" CHECK (("tier_required" = ANY (ARRAY['BASIC'::"text", 'SME'::"text", 'PRO'::"text", 'PREMIUM'::"text", 'ENTERPRISE'::"text", 'ADMIN'::"text"]))),
    CONSTRAINT "kpi_catalog_unit_check" CHECK (("unit" = ANY (ARRAY['number'::"text", 'currency'::"text", 'percent'::"text", 'days'::"text", 'hours'::"text", 'ratio'::"text", 'count'::"text"])))
);


ALTER TABLE "public"."kpi_catalog" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."messages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "session_id" "uuid",
    "channel" "text" NOT NULL,
    "direction" "text",
    "role" "text",
    "body" "text",
    "media_urls" "text"[],
    "status" "text" DEFAULT 'received'::"text",
    "provider" "text",
    "sender_ref" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "messages_channel_check" CHECK (("channel" = ANY (ARRAY['chat'::"text", 'whatsapp'::"text", 'sms'::"text", 'email'::"text", 'api'::"text"]))),
    CONSTRAINT "messages_direction_check" CHECK (("direction" = ANY (ARRAY['inbound'::"text", 'outbound'::"text"]))),
    CONSTRAINT "messages_role_check" CHECK (("role" = ANY (ARRAY['user'::"text", 'assistant'::"text", 'system'::"text", 'tool'::"text"])))
);


ALTER TABLE "public"."messages" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."notifications" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "type" "text" NOT NULL,
    "title" "text" NOT NULL,
    "body" "text",
    "agent_slug" "text",
    "related_entity_type" "text",
    "related_entity_id" "uuid",
    "urgency_level" "text" DEFAULT 'normal'::"text",
    "channels" "text"[] DEFAULT ARRAY['in_app'::"text"],
    "read_at" timestamp with time zone,
    "dismissed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."notifications" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."nps_responses" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "score" integer NOT NULL,
    "comment" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "nps_responses_score_check" CHECK ((("score" >= 0) AND ("score" <= 10)))
);


ALTER TABLE "public"."nps_responses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."polp_accounts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "integration_id" "uuid" NOT NULL,
    "polp_account_id" integer NOT NULL,
    "type" "text" NOT NULL,
    "subtype" "text",
    "number" "text",
    "name" "text",
    "balance" numeric(15,2) DEFAULT 0 NOT NULL,
    "currency_code" "text" DEFAULT 'BRL'::"text" NOT NULL,
    "marketing_name" "text",
    "owner" "text",
    "bank_data" "jsonb",
    "credit_data" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."polp_accounts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."polp_bills" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "polp_account_id" integer NOT NULL,
    "polp_bill_id" integer NOT NULL,
    "due_date" "date" NOT NULL,
    "total_amount" numeric(15,2) NOT NULL,
    "minimum_payment_amount" numeric(15,2),
    "currency_code" "text" DEFAULT 'BRL'::"text" NOT NULL,
    "allows_installments" boolean,
    "finance_charges" "jsonb",
    "payments" "jsonb",
    "status" "text" DEFAULT 'open'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."polp_bills" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."polp_integrations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "polp_integration_id" integer NOT NULL,
    "institution_id" integer NOT NULL,
    "status" "text" DEFAULT 'UPDATING'::"text" NOT NULL,
    "execution_status" "text",
    "error" "text",
    "url_to_authenticate" "text",
    "url_to_authenticate_expires_at" timestamp with time zone,
    "last_updated_at" timestamp with time zone,
    "next_auto_sync_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."polp_integrations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."polp_transactions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "polp_account_id" integer NOT NULL,
    "polp_transaction_id" integer NOT NULL,
    "external_id" "text",
    "description" "text",
    "amount" numeric(15,2) NOT NULL,
    "currency_code" "text" DEFAULT 'BRL'::"text" NOT NULL,
    "date" "date" NOT NULL,
    "type" "text" NOT NULL,
    "status" "text",
    "balance_after" numeric(15,2),
    "category" "jsonb",
    "merchant" "jsonb",
    "payment_data" "jsonb",
    "credit_card_metadata" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."polp_transactions" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."production_clientes_blu" AS
 SELECT "client_id",
    "api_key",
    "nome_empresa",
    "tipo_cliente",
    "tier",
    "collection_rag",
    "created_at",
    "updated_at",
    "external_user_id",
    "onboarding_state",
    "onboarding_completed_at",
    "company_profile",
    "brand_voice",
    "team_structure",
    "policies",
    "data_schema",
    "available_tools",
    "cpf_cnpj",
    "deleted_at",
    "ui_prefs",
    "email",
    "email_domain",
    "is_test_account"
   FROM "public"."clientes_blu"
  WHERE (("deleted_at" IS NULL) AND ("is_test_account" = false));


ALTER VIEW "public"."production_clientes_blu" OWNER TO "postgres";


COMMENT ON VIEW "public"."production_clientes_blu" IS 'Subset de active_clientes_blu excluindo contas marcadas como teste. Use em dashboards, billing, métricas de retenção e alertas operacionais. Para auditoria/QA, consulte clientes_blu ou active_clientes_blu diretamente.';



CREATE TABLE IF NOT EXISTS "public"."report_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "schedule_id" "uuid",
    "client_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "output_url" "text",
    "error" "text",
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "report_runs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."report_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."report_schedules" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "name" "text" NOT NULL,
    "report_type" "text" NOT NULL,
    "cron_expr" "text",
    "recipients" "text"[],
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "active" boolean DEFAULT true,
    "last_run_at" timestamp with time zone,
    "next_run_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."report_schedules" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shared_business_memory" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "entity_type" "text" NOT NULL,
    "entity_name" "text" NOT NULL,
    "key" "text" NOT NULL,
    "value" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "source" "text" DEFAULT 'manual'::"text" NOT NULL,
    "confidence" numeric DEFAULT 1.0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "category" "text",
    "version" integer DEFAULT 1 NOT NULL,
    "curated" boolean DEFAULT false NOT NULL,
    "expires_at" timestamp with time zone,
    "content_hash" "text",
    CONSTRAINT "shared_business_memory_category_check" CHECK (("category" = ANY (ARRAY['knowledge'::"text", 'rag'::"text", 'documents'::"text", 'memory-agent'::"text", 'context'::"text", 'decision'::"text", 'preference'::"text"]))),
    CONSTRAINT "shared_business_memory_confidence_check" CHECK ((("confidence" >= 0.0) AND ("confidence" <= 1.0))),
    CONSTRAINT "shared_business_memory_entity_type_check" CHECK (("entity_type" = ANY (ARRAY['skill'::"text", 'client'::"text", 'contact'::"text", 'supplier'::"text", 'user'::"text", 'agent_result'::"text", 'agent_metadata'::"text", 'routine'::"text", 'snapshot'::"text"]))),
    CONSTRAINT "shared_business_memory_key_check" CHECK ((("length"("key") >= 1) AND ("length"("key") <= 256))),
    CONSTRAINT "shared_business_memory_source_check" CHECK (("source" = ANY (ARRAY['manual'::"text", 'memory_agent'::"text", 'specialist'::"text", 'migration'::"text", 'system'::"text"])))
);


ALTER TABLE "public"."shared_business_memory" OWNER TO "postgres";


COMMENT ON TABLE "public"."shared_business_memory" IS 'Shared Business Memory — atomic facts about business entities (skills, clients, contacts, suppliers, users, agent results, agent metadata). Agents read/write facts here instead of conversing directly. Each row is one key-value fact.';



COMMENT ON COLUMN "public"."shared_business_memory"."entity_type" IS 'Entity taxonomy: skill | client | contact | supplier | user | agent_result | agent_metadata | routine';



COMMENT ON COLUMN "public"."shared_business_memory"."key" IS 'Fact key — e.g. tom_amigavel, preferencia_horario, regra_negocio';



COMMENT ON COLUMN "public"."shared_business_memory"."source" IS 'Provenance: manual | memory_agent | specialist | migration | system';



COMMENT ON COLUMN "public"."shared_business_memory"."category" IS 'Semantic category for filtering and routing: knowledge | rag | documents | memory-agent | context | decision | preference';



COMMENT ON COLUMN "public"."shared_business_memory"."curated" IS 'Fato confirmado como conhecimento (via confirmação humana ou backfill de sistema). A síntese semanal SBM → LightRAG só lê curated=true.';



COMMENT ON COLUMN "public"."shared_business_memory"."expires_at" IS 'Expiração do fato — NULL = não expira. A síntese ignora fatos expirados.';



COMMENT ON COLUMN "public"."shared_business_memory"."content_hash" IS 'SHA-256 hash of the JSON value (canonical representation with sort_keys).
     Used for change detection and deduplication across versions.
     Computed client-side via compute_content_hash().';



CREATE TABLE IF NOT EXISTS "public"."shared_business_memory_meta" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "entity_type" "text" NOT NULL,
    "entity_name" "text" NOT NULL,
    "key" "text" NOT NULL,
    "value" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "source" "text" DEFAULT 'system'::"text" NOT NULL,
    "confidence" numeric DEFAULT 1.0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "shared_business_memory_meta_confidence_check" CHECK ((("confidence" >= 0.0) AND ("confidence" <= 1.0))),
    CONSTRAINT "shared_business_memory_meta_entity_type_check" CHECK (("entity_type" = ANY (ARRAY['synthesis_output'::"text", 'dedup_mapping'::"text", 'kg_summary'::"text"]))),
    CONSTRAINT "shared_business_memory_meta_key_check" CHECK ((("length"("key") >= 1) AND ("length"("key") <= 256))),
    CONSTRAINT "shared_business_memory_meta_source_check" CHECK (("source" = ANY (ARRAY['manual'::"text", 'memory_agent'::"text", 'specialist'::"text", 'migration'::"text", 'system'::"text"])))
);


ALTER TABLE "public"."shared_business_memory_meta" OWNER TO "postgres";


COMMENT ON TABLE "public"."shared_business_memory_meta" IS 'Shared Business Memory Meta — operational metadata generated by agents. Stores synthesis outputs, deduplication mappings, and knowledge graph summaries. Sister table to shared_business_memory.';



COMMENT ON COLUMN "public"."shared_business_memory_meta"."entity_type" IS 'Operational artifact type: synthesis_output | dedup_mapping | kg_summary';



COMMENT ON COLUMN "public"."shared_business_memory_meta"."entity_name" IS 'Business entity this metadata refers to (e.g. client name, skill name)';



COMMENT ON COLUMN "public"."shared_business_memory_meta"."key" IS 'Metadata key — e.g. resumo_semanal, mapa_skills_duplicados';



COMMENT ON COLUMN "public"."shared_business_memory_meta"."source" IS 'Provenance: manual | memory_agent | specialist | migration | system';



CREATE TABLE IF NOT EXISTS "public"."shared_business_memory_versions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "memory_id" "uuid",
    "client_id" "uuid" NOT NULL,
    "entity_type" "text" NOT NULL,
    "entity_name" "text" NOT NULL,
    "key" "text" NOT NULL,
    "value" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "source" "text" DEFAULT 'manual'::"text" NOT NULL,
    "confidence" real DEFAULT 1.0 NOT NULL,
    "version" integer NOT NULL,
    "archived_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "original_created_at" timestamp with time zone,
    "original_updated_at" timestamp with time zone,
    "content_hash" "text",
    CONSTRAINT "shared_business_memory_versions_confidence_check" CHECK ((("confidence" >= (0.0)::double precision) AND ("confidence" <= (1.0)::double precision))),
    CONSTRAINT "shared_business_memory_versions_key_check" CHECK ((("length"("key") >= 1) AND ("length"("key") <= 256))),
    CONSTRAINT "shared_business_memory_versions_source_check" CHECK (("source" = ANY (ARRAY['manual'::"text", 'memory_agent'::"text", 'specialist'::"text", 'migration'::"text", 'system'::"text"]))),
    CONSTRAINT "shared_business_memory_versions_version_check" CHECK (("version" >= 1))
);


ALTER TABLE "public"."shared_business_memory_versions" OWNER TO "postgres";


COMMENT ON TABLE "public"."shared_business_memory_versions" IS 'Versioned snapshots of shared_business_memory rows. Each row captures the full state of a memory fact at the moment it was superseded by a newer version. Supports historical audit and rollback.';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."memory_id" IS 'UUID of the current row in shared_business_memory (may be NULL if row was deleted)';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."version" IS 'Version number at the time this snapshot was taken';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."archived_at" IS 'Timestamp when this version was archived (i.e., when it was superseded)';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."original_created_at" IS 'created_at timestamp from the original shared_business_memory row';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."original_updated_at" IS 'updated_at timestamp from the original shared_business_memory row';



COMMENT ON COLUMN "public"."shared_business_memory_versions"."content_hash" IS 'SHA-256 hash of the JSON value at the time this version was archived.
     Used for diff detection between versions and dedup on archive.';



CREATE TABLE IF NOT EXISTS "public"."shared_memory_links" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "source_entity_type" "text" NOT NULL,
    "source_entity_name" "text" NOT NULL,
    "target_entity_type" "text" NOT NULL,
    "target_entity_name" "text" NOT NULL,
    "link_type" "text" NOT NULL,
    "source_memory_id" "uuid",
    "target_memory_id" "uuid",
    "source" "text" DEFAULT 'manual'::"text" NOT NULL,
    "confidence" numeric DEFAULT 1.0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "shared_memory_links_confidence_check" CHECK ((("confidence" >= 0.0) AND ("confidence" <= 1.0))),
    CONSTRAINT "shared_memory_links_link_type_check" CHECK ((("length"("link_type") >= 2) AND ("length"("link_type") <= 128))),
    CONSTRAINT "shared_memory_links_source_check" CHECK (("source" = ANY (ARRAY['manual'::"text", 'memory_agent'::"text", 'specialist'::"text", 'migration'::"text", 'system'::"text", 'agent_pending'::"text"]))),
    CONSTRAINT "shared_memory_links_source_entity_type_check" CHECK (("source_entity_type" = ANY (ARRAY['skill'::"text", 'client'::"text", 'contact'::"text", 'supplier'::"text", 'user'::"text"]))),
    CONSTRAINT "shared_memory_links_target_entity_type_check" CHECK (("target_entity_type" = ANY (ARRAY['skill'::"text", 'client'::"text", 'contact'::"text", 'supplier'::"text", 'user'::"text"])))
);


ALTER TABLE "public"."shared_memory_links" OWNER TO "postgres";


COMMENT ON TABLE "public"."shared_memory_links" IS 'Explicit semantic links between shared_business_memory entities. Enables relationship queries across entity types.';



COMMENT ON COLUMN "public"."shared_memory_links"."link_type" IS 'Relationship label: e.g. works_for, applies_to, prefers, reports_to, depends_on';



COMMENT ON COLUMN "public"."shared_memory_links"."source_memory_id" IS 'Optional: link a specific memory record (not just entity-level)';



COMMENT ON COLUMN "public"."shared_memory_links"."target_memory_id" IS 'Optional: link to a specific memory record (not just entity-level)';



COMMENT ON COLUMN "public"."shared_memory_links"."source" IS 'Provenance: manual | memory_agent | specialist | migration | system | agent_pending';



CREATE TABLE IF NOT EXISTS "public"."sql_table_config" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "table_name" "text" NOT NULL,
    "display_name" "text",
    "description" "text",
    "is_primary" boolean DEFAULT false NOT NULL,
    "column_descriptions" "jsonb" DEFAULT '{}'::"jsonb",
    "enum_values" "jsonb" DEFAULT '{}'::"jsonb",
    "example_queries" "jsonb" DEFAULT '[]'::"jsonb",
    "join_keys" "jsonb" DEFAULT '[]'::"jsonb",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."sql_table_config" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."standalone_agent_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "agent_catalog_id" "uuid" NOT NULL,
    "session_id" "text" NOT NULL,
    "config_status" "text" DEFAULT 'configuring'::"text",
    "collected_context" "jsonb" DEFAULT '{}'::"jsonb",
    "uploaded_file_ids" "uuid"[] DEFAULT ARRAY[]::"uuid"[],
    "uploaded_document_ids" "uuid"[] DEFAULT ARRAY[]::"uuid"[],
    "google_account_email" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "standalone_agent_sessions_config_status_check" CHECK (("config_status" = ANY (ARRAY['configuring'::"text", 'ready'::"text", 'active'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."standalone_agent_sessions" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."suppliers" WITH ("security_barrier"='true') AS
 SELECT ("fornecedor_id")::"text" AS "id",
    "client_id",
    "nome" AS "name",
    "cnpj",
    "category",
    "tags",
    "rating",
    "telefone" AS "contact_phone",
    "contact_email",
    "endereco_cidade" AS "city",
    "endereco_uf" AS "state",
    "performance_summary",
    "is_active",
    "receita_total",
    "ticket_medio",
    "total_pedidos_recebidos",
    "nivel_cluster",
    "dias_recencia",
    "frequencia_mensal",
    "atualizado_em" AS "updated_at"
   FROM "analytics_v2"."dim_fornecedores"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "public"."suppliers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."uploaded_files_metadata" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "file_name" "text" NOT NULL,
    "storage_path" "text" NOT NULL,
    "bucket" "text" DEFAULT 'file-uploads'::"text" NOT NULL,
    "mime_type" "text",
    "size_bytes" bigint,
    "status" "text" DEFAULT 'uploaded'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "content_hash" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."uploaded_files_metadata" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "vector_db"."document_chunks" (
    "id" integer NOT NULL,
    "document_id" "uuid" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "content" "text" NOT NULL,
    "embedding" "extensions"."halfvec"(384),
    "chunk_index" integer DEFAULT 0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "fts" "tsvector" GENERATED ALWAYS AS ("to_tsvector"('"portuguese"'::"regconfig", "content")) STORED,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "content_hash" "text",
    "scope" "text",
    "category" "text",
    "theme" "text",
    "word_cloud" "text"[],
    "usage_context" "text",
    "at_date" "date",
    "document_type_id" "text",
    "is_current" boolean DEFAULT true,
    "language" "text" DEFAULT 'pt-BR'::"text"
);


ALTER TABLE "vector_db"."document_chunks" OWNER TO "postgres";


ALTER TABLE "vector_db"."document_chunks" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "vector_db"."document_chunks_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "vector_db"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "title" "text",
    "file_name" "text" NOT NULL,
    "file_type" "text",
    "storage_path" "text",
    "source" "text" DEFAULT 'upload'::"text" NOT NULL,
    "processing_mode" "text" DEFAULT 'simple'::"text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "scope" "text",
    "category" "text",
    "content_hash" "text",
    "error_message" "text",
    "chunk_count" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "source_url" "text",
    "description" "text",
    CONSTRAINT "documents_processing_mode_check" CHECK (("processing_mode" = ANY (ARRAY['simple'::"text", 'complex'::"text"]))),
    CONSTRAINT "documents_source_check" CHECK (("source" = ANY (ARRAY['upload'::"text", 'chat'::"text", 'url'::"text", 'api'::"text", 'generated'::"text", 'archived'::"text"]))),
    CONSTRAINT "documents_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "vector_db"."documents" OWNER TO "postgres";


COMMENT ON COLUMN "vector_db"."documents"."description" IS 'Optional user-provided description of the document';



ALTER TABLE ONLY "_trace"."onboarding_events" ALTER COLUMN "id" SET DEFAULT "nextval"('"_trace"."onboarding_events_id_seq"'::"regclass");



ALTER TABLE ONLY "admin"."tenant_wipe_audit" ALTER COLUMN "audit_id" SET DEFAULT "nextval"('"admin"."tenant_wipe_audit_audit_id_seq"'::"regclass");



ALTER TABLE ONLY "analytics_v2"."ingest_staging" ALTER COLUMN "id" SET DEFAULT "nextval"('"analytics_v2"."ingest_staging_id_seq"'::"regclass");



ALTER TABLE ONLY "fdw"."staging_transacoes" ALTER COLUMN "id" SET DEFAULT "nextval"('"fdw"."staging_transacoes_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."audit_log" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."audit_log_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."canonical_columns" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."canonical_columns_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."credencial_servico_externo" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."credencial_servico_externo_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."frontend_events" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."frontend_events_id_seq"'::"regclass");



ALTER TABLE ONLY "_trace"."onboarding_events"
    ADD CONSTRAINT "onboarding_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "admin"."tenant_wipe_audit"
    ADD CONSTRAINT "tenant_wipe_audit_pkey" PRIMARY KEY ("audit_id");



ALTER TABLE ONLY "admin"."tenant_wipe_jobs"
    ADD CONSTRAINT "tenant_wipe_jobs_pkey" PRIMARY KEY ("job_id");



ALTER TABLE ONLY "admin"."wipe_table_priority"
    ADD CONSTRAINT "wipe_table_priority_pkey" PRIMARY KEY ("table_fqn");



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_client_cpf_uniq" UNIQUE ("client_id", "cpf_cnpj");



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_pkey" PRIMARY KEY ("customer_id");



ALTER TABLE ONLY "analytics_v2"."dim_datas"
    ADD CONSTRAINT "dim_datas_data_key" UNIQUE ("data");



ALTER TABLE ONLY "analytics_v2"."dim_datas"
    ADD CONSTRAINT "dim_datas_pkey" PRIMARY KEY ("data_id");



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_client_cnpj_uniq" UNIQUE ("client_id", "cnpj");



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_pkey" PRIMARY KEY ("fornecedor_id");



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_client_sku_uniq" UNIQUE ("client_id", "sku");



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_pkey" PRIMARY KEY ("inventory_id");



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_pkey" PRIMARY KEY ("transacao_id", "client_id");



ALTER TABLE ONLY "analytics_v2"."ingest_staging"
    ADD CONSTRAINT "ingest_staging_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_pkey" PRIMARY KEY ("job_id");



ALTER TABLE ONLY "fdw"."staging_transacoes"
    ADD CONSTRAINT "staging_transacoes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_catalog"
    ADD CONSTRAINT "agent_catalog_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_catalog"
    ADD CONSTRAINT "agent_catalog_slug_key" UNIQUE ("slug");



ALTER TABLE ONLY "public"."agent_lists"
    ADD CONSTRAINT "agent_lists_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_sessions"
    ADD CONSTRAINT "agent_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."app_config"
    ADD CONSTRAINT "app_config_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "public"."approval_requests"
    ADD CONSTRAINT "approval_requests_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."artifact_log"
    ADD CONSTRAINT "artifact_log_dedupe_uq" UNIQUE ("execution_id", "step_id");



ALTER TABLE ONLY "public"."artifact_log"
    ADD CONSTRAINT "artifact_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."audit_log"
    ADD CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "bigquery_foreign_tables_client_id_table_name_key" UNIQUE ("client_id", "table_name");



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "bigquery_foreign_tables_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_client_id_key" UNIQUE ("client_id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_server_name_key" UNIQUE ("server_name");



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_client_id_key" UNIQUE ("client_id");



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."calendar_watch_channels"
    ADD CONSTRAINT "calendar_watch_channels_client_id_calendar_id_key" UNIQUE ("client_id", "calendar_id");



ALTER TABLE ONLY "public"."calendar_watch_channels"
    ADD CONSTRAINT "calendar_watch_channels_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."canonical_columns"
    ADD CONSTRAINT "canonical_columns_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."canonical_columns"
    ADD CONSTRAINT "canonical_columns_table_name_column_name_key" UNIQUE ("table_name", "column_name");



ALTER TABLE ONLY "public"."client_approval_rules"
    ADD CONSTRAINT "client_approval_rules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_id_key" UNIQUE ("id");



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_pkey" PRIMARY KEY ("client_id");



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "client_data_sources_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_pkey" PRIMARY KEY ("client_id", "dimension", "slug");



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_pkey" PRIMARY KEY ("client_id", "agent_slug");



ALTER TABLE ONLY "public"."client_goals"
    ADD CONSTRAINT "client_goals_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_insights"
    ADD CONSTRAINT "client_insights_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_unique" UNIQUE ("client_id", "notification_type", "channel");



ALTER TABLE ONLY "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_pkey" PRIMARY KEY ("id");



ALTER TABLE "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'dispatched'::"text", 'executing'::"text", 'completed'::"text", 'failed'::"text", 'partial'::"text", 'awaiting_approval'::"text"]))) NOT VALID;



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_client_id_routine_id_key" UNIQUE ("client_id", "routine_id");



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_users"
    ADD CONSTRAINT "client_users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_users"
    ADD CONSTRAINT "client_users_unique_email" UNIQUE ("client_id", "email");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_api_key_key" UNIQUE ("api_key");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_external_user_id_key" UNIQUE ("external_user_id");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_pkey" PRIMARY KEY ("client_id");



ALTER TABLE ONLY "public"."cnpj_enrichments"
    ADD CONSTRAINT "cnpj_enrichments_pkey" PRIMARY KEY ("cnpj");



ALTER TABLE ONLY "public"."conversa"
    ADD CONSTRAINT "conversa_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."credencial_servico_externo"
    ADD CONSTRAINT "credencial_servico_externo_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."cross_agent_routines"
    ADD CONSTRAINT "cross_agent_routines_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."csv_import_staging"
    ADD CONSTRAINT "csv_import_staging_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."data_source_mappings"
    ADD CONSTRAINT "data_source_mappings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."dimension_state"
    ADD CONSTRAINT "dimension_state_client_dimension_key" UNIQUE ("client_id", "dimension");



ALTER TABLE ONLY "public"."dimension_state"
    ADD CONSTRAINT "dimension_state_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."doc_templates"
    ADD CONSTRAINT "doc_templates_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_version_number_key" UNIQUE ("document_id", "version_number");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_client_id_title_key" UNIQUE ("client_id", "title");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."frontend_events"
    ADD CONSTRAINT "frontend_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_client_id_provider_key" UNIQUE ("client_id", "provider");



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_client_id_provider_account_email_key" UNIQUE ("client_id", "provider", "account_email");



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_pkey" PRIMARY KEY ("agent_slug", "document_type_id");



ALTER TABLE ONLY "public"."knowledge_document_types"
    ADD CONSTRAINT "knowledge_document_types_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."knowledge_tag_definitions"
    ADD CONSTRAINT "knowledge_tag_definitions_pkey" PRIMARY KEY ("tag");



ALTER TABLE ONLY "public"."kpi_catalog"
    ADD CONSTRAINT "kpi_catalog_pkey" PRIMARY KEY ("slug");



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."nps_responses"
    ADD CONSTRAINT "nps_responses_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."polp_accounts"
    ADD CONSTRAINT "polp_accounts_client_id_polp_account_id_key" UNIQUE ("client_id", "polp_account_id");



ALTER TABLE ONLY "public"."polp_accounts"
    ADD CONSTRAINT "polp_accounts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."polp_bills"
    ADD CONSTRAINT "polp_bills_client_id_polp_bill_id_key" UNIQUE ("client_id", "polp_bill_id");



ALTER TABLE ONLY "public"."polp_bills"
    ADD CONSTRAINT "polp_bills_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."polp_integrations"
    ADD CONSTRAINT "polp_integrations_client_id_polp_integration_id_key" UNIQUE ("client_id", "polp_integration_id");



ALTER TABLE ONLY "public"."polp_integrations"
    ADD CONSTRAINT "polp_integrations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."polp_transactions"
    ADD CONSTRAINT "polp_transactions_client_id_polp_transaction_id_key" UNIQUE ("client_id", "polp_transaction_id");



ALTER TABLE ONLY "public"."polp_transactions"
    ADD CONSTRAINT "polp_transactions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_schedules"
    ADD CONSTRAINT "report_schedules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shared_business_memory_meta"
    ADD CONSTRAINT "shared_business_memory_meta_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shared_business_memory"
    ADD CONSTRAINT "shared_business_memory_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shared_business_memory_versions"
    ADD CONSTRAINT "shared_business_memory_versions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shared_memory_links"
    ADD CONSTRAINT "shared_memory_links_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."sql_table_config"
    ADD CONSTRAINT "sql_table_config_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_session_id_key" UNIQUE ("session_id");



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "unique_client_source_resource" UNIQUE ("client_id", "source_type", "resource_type");



ALTER TABLE ONLY "public"."data_source_mappings"
    ADD CONSTRAINT "unique_credential_resource" UNIQUE ("credential_id", "resource_type");



ALTER TABLE ONLY "public"."uploaded_files_metadata"
    ADD CONSTRAINT "uploaded_files_metadata_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "uq_client_document" UNIQUE ("client_id", "document_type_id");



ALTER TABLE ONLY "public"."shared_business_memory_meta"
    ADD CONSTRAINT "uq_sbm_meta_entry" UNIQUE ("client_id", "entity_type", "entity_name", "key");



ALTER TABLE ONLY "public"."shared_business_memory"
    ADD CONSTRAINT "uq_shared_memory_entry" UNIQUE ("client_id", "entity_type", "entity_name", "key");



ALTER TABLE ONLY "public"."shared_memory_links"
    ADD CONSTRAINT "uq_shared_memory_link" UNIQUE ("client_id", "source_entity_type", "source_entity_name", "link_type", "target_entity_type", "target_entity_name");



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_content_hash_key" UNIQUE ("document_id", "content_hash");



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "vector_db"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_trace_at" ON "_trace"."onboarding_events" USING "btree" ("at");



CREATE INDEX "idx_trace_table" ON "_trace"."onboarding_events" USING "btree" ("table_name", "at");



CREATE INDEX "idx_tenant_wipe_audit_job" ON "admin"."tenant_wipe_audit" USING "btree" ("job_id", "at");



CREATE INDEX "idx_tenant_wipe_jobs_client" ON "admin"."tenant_wipe_jobs" USING "btree" ("client_id");



CREATE INDEX "idx_tenant_wipe_jobs_status" ON "admin"."tenant_wipe_jobs" USING "btree" ("status", "created_at") WHERE ("status" = ANY (ARRAY['queued'::"text", 'running'::"text"]));



CREATE UNIQUE INDEX "dim_inventory_client_nome_uniq" ON "analytics_v2"."dim_inventory" USING "btree" ("client_id", "nome") WHERE ("sku" IS NULL);



CREATE INDEX "fato_transacoes_tipo_idx" ON "analytics_v2"."fato_transacoes" USING "btree" ("client_id", "tipo_transacao");



CREATE INDEX "fato_transacoes_updated_at_idx" ON "analytics_v2"."fato_transacoes" USING "btree" ("client_id", "updated_at");



CREATE INDEX "idx_dim_clientes_client" ON "analytics_v2"."dim_clientes" USING "btree" ("client_id");



CREATE UNIQUE INDEX "idx_dim_clientes_cpf_cnpj" ON "analytics_v2"."dim_clientes" USING "btree" ("client_id", "cpf_cnpj") WHERE ("cpf_cnpj" IS NOT NULL);



CREATE INDEX "idx_dim_forn_client" ON "analytics_v2"."dim_fornecedores" USING "btree" ("client_id");



CREATE INDEX "idx_dim_inv_client" ON "analytics_v2"."dim_inventory" USING "btree" ("client_id");



CREATE INDEX "idx_dim_inv_client_updated" ON "analytics_v2"."dim_inventory" USING "btree" ("client_id", "updated_at" DESC);



COMMENT ON INDEX "analytics_v2"."idx_dim_inv_client_updated" IS 'Composite index for KPI queries filtering by tenant + time range';



CREATE INDEX "idx_dim_inv_stock_alert" ON "analytics_v2"."dim_inventory" USING "btree" ("client_id", "estoque_minimo") WHERE ("estoque_minimo" IS NOT NULL);



COMMENT ON INDEX "analytics_v2"."idx_dim_inv_stock_alert" IS 'Partial composite index for stock alert queries (only non-null quantities)';



CREATE INDEX "idx_fato_client" ON "analytics_v2"."fato_transacoes" USING "btree" ("client_id");



CREATE INDEX "idx_fato_customer_dim" ON "analytics_v2"."fato_transacoes" USING "btree" ("customer_id");



CREATE INDEX "idx_fato_data" ON "analytics_v2"."fato_transacoes" USING "btree" ("data_competencia_id");



CREATE INDEX "idx_fato_fornecedor" ON "analytics_v2"."fato_transacoes" USING "btree" ("fornecedor_id");



CREATE INDEX "idx_fato_transacoes_entry_type" ON "analytics_v2"."fato_transacoes" USING "btree" ("client_id", "entry_type");



CREATE INDEX "idx_ingest_staging_job" ON "analytics_v2"."ingest_staging" USING "btree" ("job_id");



CREATE INDEX "idx_ingest_staging_job_row" ON "analytics_v2"."ingest_staging" USING "btree" ("job_id", "row_index");



CREATE INDEX "idx_ingest_staging_source" ON "analytics_v2"."ingest_staging" USING "btree" ("source_id");



CREATE INDEX "idx_reg_jobs_client_status" ON "analytics_v2"."reg_jobs" USING "btree" ("client_id", "status");



CREATE INDEX "idx_reg_jobs_created" ON "analytics_v2"."reg_jobs" USING "btree" ("created_at" DESC);



CREATE UNIQUE INDEX "uidx_mv_distribuicao_regional_pk" ON "analytics_v2"."mv_distribuicao_regional" USING "btree" ("client_id", "endereco_uf", "endereco_cidade");



CREATE UNIQUE INDEX "uidx_mv_resumo_dashboard_client" ON "analytics_v2"."mv_resumo_dashboard" USING "btree" ("client_id");



CREATE UNIQUE INDEX "uidx_mv_series_temporal_pk" ON "analytics_v2"."mv_series_temporal" USING "btree" ("client_id", "data_periodo", "tipo_grafico", "dimensao");



CREATE UNIQUE INDEX "uidx_mv_ultimos_pedidos_pk" ON "analytics_v2"."mv_ultimos_pedidos" USING "btree" ("client_id", "pedido_id");



CREATE UNIQUE INDEX "uq_reg_jobs_refresh_pending" ON "analytics_v2"."reg_jobs" USING "btree" ("client_id", "job_type") WHERE (("job_type" = 'refresh_dashboards'::"text") AND ("status" = 'pending'::"text"));



COMMENT ON INDEX "analytics_v2"."uq_reg_jobs_refresh_pending" IS 'Garante no máximo 1 job refresh_dashboards pending por cliente. Usado em ON CONFLICT (client_id, job_type) WHERE ... DO NOTHING no apply_staging_to_facts para debounce race-safe sem advisory locks.';



CREATE INDEX "idx_fdw_staging_job" ON "fdw"."staging_transacoes" USING "btree" ("job_id");



CREATE UNIQUE INDEX "client_insights_client_run_room_kpi_idx" ON "public"."client_insights" USING "btree" ("client_id", "run_date", "room", "kpi") WHERE (("run_date" IS NOT NULL) AND ("kpi" IS NOT NULL));



CREATE INDEX "doc_templates_client_id_idx" ON "public"."doc_templates" USING "btree" ("client_id") WHERE ("client_id" IS NOT NULL);



CREATE INDEX "document_versions_document_id_idx" ON "public"."document_versions" USING "btree" ("document_id", "version_number" DESC);



CREATE INDEX "documents_client_id_idx" ON "public"."documents" USING "btree" ("client_id", "updated_at" DESC);



CREATE INDEX "idx_agent_lists_client_type" ON "public"."agent_lists" USING "btree" ("client_id", "list_type");



CREATE INDEX "idx_agent_lists_session" ON "public"."agent_lists" USING "btree" ("client_id", "session_id") WHERE ("session_id" IS NOT NULL);



CREATE INDEX "idx_agent_lists_status" ON "public"."agent_lists" USING "btree" ("client_id", "list_type", "status");



CREATE INDEX "idx_agent_sessions_client_id" ON "public"."agent_sessions" USING "btree" ("client_id");



CREATE INDEX "idx_agent_sessions_status" ON "public"."agent_sessions" USING "btree" ("client_id", "status");



CREATE INDEX "idx_approval_agent_slug" ON "public"."approval_requests" USING "btree" ("client_id", "agent_slug");



CREATE INDEX "idx_approval_client_status" ON "public"."approval_requests" USING "btree" ("client_id", "status");



CREATE INDEX "idx_approval_session_id" ON "public"."approval_requests" USING "btree" ("session_id") WHERE ("session_id" IS NOT NULL);



CREATE INDEX "idx_artifact_log_client_type" ON "public"."artifact_log" USING "btree" ("client_id", "artifact_type", "claimed_at" DESC);



CREATE INDEX "idx_artifact_log_failed" ON "public"."artifact_log" USING "btree" ("claimed_at" DESC) WHERE ("status" = 'failed'::"text");



CREATE INDEX "idx_audit_client" ON "public"."audit_log" USING "btree" ("client_id");



CREATE INDEX "idx_audit_created" ON "public"."audit_log" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_bft_client_credential" ON "public"."bigquery_foreign_tables" USING "btree" ("client_id", "credential_id");



CREATE INDEX "idx_calendar_watch_channel_id" ON "public"."calendar_watch_channels" USING "btree" ("channel_id");



CREATE INDEX "idx_cds_client_id" ON "public"."client_data_sources" USING "btree" ("client_id");



CREATE INDEX "idx_cds_credential_id" ON "public"."client_data_sources" USING "btree" ("credential_id");



CREATE INDEX "idx_cds_drive_file_id" ON "public"."client_data_sources" USING "btree" ("client_id", "drive_file_id") WHERE ("drive_file_id" IS NOT NULL);



CREATE INDEX "idx_cds_integration_token" ON "public"."client_data_sources" USING "btree" ("integration_token_id") WHERE ("integration_token_id" IS NOT NULL);



CREATE INDEX "idx_ckd_client" ON "public"."client_knowledge_documents" USING "btree" ("client_id");



CREATE INDEX "idx_ckd_client_status" ON "public"."client_knowledge_documents" USING "btree" ("client_id", "status");



CREATE INDEX "idx_client_goals_active" ON "public"."client_goals" USING "btree" ("client_id", "dimension") WHERE ("status" = 'active'::"text");



CREATE INDEX "idx_client_goals_client_id" ON "public"."client_goals" USING "btree" ("client_id");



CREATE INDEX "idx_client_routines_source_status" ON "public"."client_routines" USING "btree" ("source", "status");



CREATE INDEX "idx_client_users_auth_user_id" ON "public"."client_users" USING "btree" ("auth_user_id") WHERE ("auth_user_id" IS NOT NULL);



CREATE INDEX "idx_client_users_client_id" ON "public"."client_users" USING "btree" ("client_id");



CREATE INDEX "idx_client_users_email" ON "public"."client_users" USING "btree" ("email");



CREATE INDEX "idx_clientes_blu_api_key" ON "public"."clientes_blu" USING "btree" ("api_key") WHERE ("api_key" IS NOT NULL);



CREATE INDEX "idx_clientes_blu_client_id" ON "public"."clientes_blu" USING "btree" ("client_id");



CREATE INDEX "idx_clientes_blu_deleted_at" ON "public"."clientes_blu" USING "btree" ("deleted_at") WHERE ("deleted_at" IS NOT NULL);



CREATE INDEX "idx_clientes_blu_external_user" ON "public"."clientes_blu" USING "btree" ("external_user_id");



CREATE INDEX "idx_clientes_blu_external_user_id" ON "public"."clientes_blu" USING "btree" ("external_user_id") WHERE ("external_user_id" IS NOT NULL);



CREATE INDEX "idx_clientes_blu_is_test_account" ON "public"."clientes_blu" USING "btree" ("is_test_account") WHERE ("is_test_account" = true);



CREATE INDEX "idx_clientes_blu_onboarding_incomplete" ON "public"."clientes_blu" USING "btree" ("client_id") WHERE ("onboarding_completed_at" IS NULL);



CREATE INDEX "idx_credencial_client_id" ON "public"."credencial_servico_externo" USING "btree" ("client_id");



CREATE INDEX "idx_csv_staging_client_id" ON "public"."csv_import_staging" USING "btree" ("client_id");



CREATE INDEX "idx_csv_staging_source_id" ON "public"."csv_import_staging" USING "btree" ("source_id");



CREATE INDEX "idx_dimension_state_client_id" ON "public"."dimension_state" USING "btree" ("client_id");



CREATE INDEX "idx_dimension_state_valid_until" ON "public"."dimension_state" USING "btree" ("client_id", "valid_until");



CREATE INDEX "idx_fe_client_event" ON "public"."frontend_events" USING "btree" ("client_id", "event_name");



CREATE INDEX "idx_fe_created_at" ON "public"."frontend_events" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_insights_client_active" ON "public"."client_insights" USING "btree" ("client_id", "dismissed", "generated_at" DESC);



CREATE INDEX "idx_mappings_credential" ON "public"."data_source_mappings" USING "btree" ("credential_id");



CREATE INDEX "idx_mappings_resource" ON "public"."data_source_mappings" USING "btree" ("resource_type");



CREATE INDEX "idx_mappings_status" ON "public"."data_source_mappings" USING "btree" ("status");



CREATE INDEX "idx_messages_client" ON "public"."messages" USING "btree" ("client_id", "created_at" DESC);



CREATE INDEX "idx_messages_session" ON "public"."messages" USING "btree" ("session_id") WHERE ("session_id" IS NOT NULL);



CREATE INDEX "idx_notifications_client_unread" ON "public"."notifications" USING "btree" ("client_id", "read_at", "created_at" DESC) WHERE ("dismissed_at" IS NULL);



CREATE INDEX "idx_nps_client" ON "public"."nps_responses" USING "btree" ("client_id");



CREATE INDEX "idx_report_runs_client" ON "public"."report_runs" USING "btree" ("client_id", "started_at" DESC);



CREATE INDEX "idx_routine_exec_awaiting_approval" ON "public"."client_routine_executions" USING "btree" ("client_id", "dispatched_at") WHERE ("status" = 'awaiting_approval'::"text");



CREATE INDEX "idx_routine_exec_client" ON "public"."client_routine_executions" USING "btree" ("client_id", "routine_id", "created_at" DESC);



CREATE INDEX "idx_routine_exec_dispatched" ON "public"."client_routine_executions" USING "btree" ("dispatched_at") WHERE ("status" = 'dispatched'::"text");



CREATE INDEX "idx_routine_exec_heartbeat" ON "public"."client_routine_executions" USING "btree" ("heartbeat_at") WHERE (("status" = 'dispatched'::"text") AND ("heartbeat_at" IS NOT NULL));



CREATE INDEX "idx_routine_exec_pending" ON "public"."client_routine_executions" USING "btree" ("status") WHERE ("status" = 'pending'::"text");



CREATE INDEX "idx_routine_exec_stale" ON "public"."client_routine_executions" USING "btree" ("dispatched_at") WHERE ("status" = 'dispatched'::"text");



CREATE INDEX "idx_sbm_category" ON "public"."shared_business_memory" USING "btree" ("client_id", "category") WHERE ("category" IS NOT NULL);



CREATE INDEX "idx_sbm_entity" ON "public"."shared_business_memory" USING "btree" ("client_id", "entity_type", "entity_name");



CREATE INDEX "idx_sbm_entity_temporal" ON "public"."shared_business_memory" USING "btree" ("client_id", "entity_type", "entity_name", "updated_at" DESC);



CREATE INDEX "idx_sbm_key" ON "public"."shared_business_memory" USING "btree" ("client_id", "entity_type", "entity_name", "key");



CREATE INDEX "idx_sbm_key_trgm" ON "public"."shared_business_memory" USING "gin" ("key" "extensions"."gin_trgm_ops");



CREATE INDEX "idx_sbm_meta_entity" ON "public"."shared_business_memory_meta" USING "btree" ("client_id", "entity_type", "entity_name");



CREATE INDEX "idx_sbm_meta_key" ON "public"."shared_business_memory_meta" USING "btree" ("client_id", "entity_type", "entity_name", "key");



CREATE INDEX "idx_sbm_meta_key_trgm" ON "public"."shared_business_memory_meta" USING "gin" ("key" "extensions"."gin_trgm_ops");



CREATE INDEX "idx_sbm_synthesis_weekly" ON "public"."shared_business_memory" USING "btree" ("client_id", "curated", "expires_at") WHERE (("curated" = true) AND ("expires_at" IS NULL));



CREATE INDEX "idx_sbm_versions_archived_at" ON "public"."shared_business_memory_versions" USING "btree" ("client_id", "archived_at");



CREATE INDEX "idx_sbm_versions_content_hash" ON "public"."shared_business_memory_versions" USING "btree" ("client_id", "entity_type", "entity_name", "key", "content_hash");



CREATE INDEX "idx_sbm_versions_lookup" ON "public"."shared_business_memory_versions" USING "btree" ("client_id", "entity_type", "entity_name", "key", "version" DESC);



CREATE INDEX "idx_sbm_versions_memory_id" ON "public"."shared_business_memory_versions" USING "btree" ("memory_id");



CREATE INDEX "idx_sml_source" ON "public"."shared_memory_links" USING "btree" ("client_id", "source_entity_type", "source_entity_name");



CREATE INDEX "idx_sml_source_memory" ON "public"."shared_memory_links" USING "btree" ("source_memory_id") WHERE ("source_memory_id" IS NOT NULL);



CREATE INDEX "idx_sml_target" ON "public"."shared_memory_links" USING "btree" ("client_id", "target_entity_type", "target_entity_name");



CREATE INDEX "idx_sml_target_memory" ON "public"."shared_memory_links" USING "btree" ("target_memory_id") WHERE ("target_memory_id" IS NOT NULL);



CREATE INDEX "idx_sml_type" ON "public"."shared_memory_links" USING "btree" ("client_id", "link_type");



CREATE INDEX "idx_tokens_client_provider" ON "public"."integration_tokens" USING "btree" ("client_id", "provider");



CREATE INDEX "idx_uploaded_files_client" ON "public"."uploaded_files_metadata" USING "btree" ("client_id");



CREATE INDEX "polp_accounts_client_id_idx" ON "public"."polp_accounts" USING "btree" ("client_id");



CREATE INDEX "polp_accounts_integration_id_idx" ON "public"."polp_accounts" USING "btree" ("integration_id");



CREATE INDEX "polp_bills_client_id_due_date_idx" ON "public"."polp_bills" USING "btree" ("client_id", "due_date");



CREATE INDEX "polp_integrations_client_id_idx" ON "public"."polp_integrations" USING "btree" ("client_id");



CREATE INDEX "polp_transactions_client_id_date_idx" ON "public"."polp_transactions" USING "btree" ("client_id", "date" DESC);



CREATE INDEX "polp_transactions_polp_account_id_idx" ON "public"."polp_transactions" USING "btree" ("polp_account_id");



CREATE INDEX "sql_table_config_client_id_idx" ON "public"."sql_table_config" USING "btree" ("client_id") WHERE ("is_active" = true);



CREATE UNIQUE INDEX "sql_table_config_client_table_uidx" ON "public"."sql_table_config" USING "btree" ("client_id", "table_name") WHERE ("client_id" IS NOT NULL);



CREATE UNIQUE INDEX "sql_table_config_global_table_uidx" ON "public"."sql_table_config" USING "btree" ("table_name") WHERE ("client_id" IS NULL);



CREATE INDEX "idx_chunks_at_date" ON "vector_db"."document_chunks" USING "btree" ("client_id", "at_date") WHERE ("at_date" IS NOT NULL);



CREATE INDEX "idx_chunks_client" ON "vector_db"."document_chunks" USING "btree" ("client_id");



CREATE INDEX "idx_chunks_document" ON "vector_db"."document_chunks" USING "btree" ("document_id");



CREATE INDEX "idx_chunks_document_type_id" ON "vector_db"."document_chunks" USING "btree" ("client_id", "document_type_id") WHERE ("document_type_id" IS NOT NULL);



CREATE INDEX "idx_chunks_embedding" ON "vector_db"."document_chunks" USING "hnsw" ("embedding" "extensions"."halfvec_ip_ops");



CREATE INDEX "idx_chunks_fts" ON "vector_db"."document_chunks" USING "gin" ("fts");



CREATE INDEX "idx_chunks_is_current" ON "vector_db"."document_chunks" USING "btree" ("client_id", "is_current") WHERE ("is_current" = true);



CREATE INDEX "idx_chunks_language" ON "vector_db"."document_chunks" USING "btree" ("language") WHERE ("language" IS NOT NULL);



CREATE INDEX "idx_docs_client" ON "vector_db"."documents" USING "btree" ("client_id");



CREATE INDEX "idx_docs_content_hash" ON "vector_db"."documents" USING "btree" ("content_hash") WHERE ("content_hash" IS NOT NULL);



CREATE INDEX "idx_docs_status" ON "vector_db"."documents" USING "btree" ("status");



CREATE INDEX "idx_document_chunks_category" ON "vector_db"."document_chunks" USING "btree" ("category");



CREATE INDEX "idx_document_chunks_client_scope_theme" ON "vector_db"."document_chunks" USING "btree" ("client_id", "scope", "theme");



CREATE INDEX "idx_document_chunks_scope" ON "vector_db"."document_chunks" USING "btree" ("scope");



CREATE INDEX "idx_document_chunks_theme" ON "vector_db"."document_chunks" USING "btree" ("theme");



CREATE OR REPLACE TRIGGER "trg_context_report_on_ingestion" AFTER UPDATE OF "status" ON "analytics_v2"."reg_jobs" FOR EACH ROW EXECUTE FUNCTION "public"."dispatch_context_report_on_ingestion"();



CREATE OR REPLACE TRIGGER "trg_knowledge_on_etl_completed" AFTER UPDATE OF "status" ON "analytics_v2"."reg_jobs" FOR EACH ROW EXECUTE FUNCTION "analytics_v2"."on_etl_job_completed"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."bigquery_foreign_tables" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."bigquery_servers" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."calendar_settings" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."calendar_watch_channels" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_data_sources" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_enabled_agents" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_goals" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_knowledge_documents" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_routine_executions" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_routines" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."client_users" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."conversa" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."integration_configs" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."integration_tokens" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."messages" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."notifications" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "_trace_capture" AFTER INSERT OR DELETE OR UPDATE ON "public"."uploaded_files_metadata" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "polp_accounts_updated_at" BEFORE UPDATE ON "public"."polp_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."polp_set_updated_at"();



CREATE OR REPLACE TRIGGER "polp_bills_updated_at" BEFORE UPDATE ON "public"."polp_bills" FOR EACH ROW EXECUTE FUNCTION "public"."polp_set_updated_at"();



CREATE OR REPLACE TRIGGER "polp_integrations_updated_at" BEFORE UPDATE ON "public"."polp_integrations" FOR EACH ROW EXECUTE FUNCTION "public"."polp_set_updated_at"();



CREATE OR REPLACE TRIGGER "polp_transactions_updated_at" BEFORE UPDATE ON "public"."polp_transactions" FOR EACH ROW EXECUTE FUNCTION "public"."polp_set_updated_at"();



CREATE OR REPLACE TRIGGER "trace_csv_import_staging" AFTER INSERT OR DELETE OR UPDATE ON "public"."csv_import_staging" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "trace_data_source_mappings" AFTER INSERT OR DELETE OR UPDATE ON "public"."data_source_mappings" FOR EACH ROW EXECUTE FUNCTION "_trace"."capture"();



CREATE OR REPLACE TRIGGER "trg_agent_lists_updated_at" BEFORE UPDATE ON "public"."agent_lists" FOR EACH ROW EXECUTE FUNCTION "public"."set_agent_lists_updated_at"();



CREATE OR REPLACE TRIGGER "trg_approval_requests_updated_at" BEFORE UPDATE ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_auto_enroll_catalog_routines" AFTER INSERT ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "public"."auto_enroll_catalog_routines"();



CREATE OR REPLACE TRIGGER "trg_auto_enroll_system_routines" AFTER INSERT ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "public"."auto_enroll_system_routines"();



CREATE OR REPLACE TRIGGER "trg_cleanup_auth_user_orphan" AFTER DELETE ON "public"."client_users" FOR EACH ROW EXECUTE FUNCTION "public"."cleanup_auth_user_if_orphaned"();



CREATE OR REPLACE TRIGGER "trg_cleanup_credential_vault_secret" BEFORE DELETE ON "public"."credencial_servico_externo" FOR EACH ROW EXECUTE FUNCTION "public"."cleanup_credential_vault_secret"();



CREATE OR REPLACE TRIGGER "trg_cleanup_datasource_storage" BEFORE DELETE ON "public"."client_data_sources" FOR EACH ROW EXECUTE FUNCTION "public"."cleanup_datasource_storage_object"();



CREATE OR REPLACE TRIGGER "trg_cleanup_storage_object" BEFORE DELETE ON "public"."uploaded_files_metadata" FOR EACH ROW EXECUTE FUNCTION "public"."cleanup_storage_object"();



CREATE OR REPLACE TRIGGER "trg_client_goals_updated_at" BEFORE UPDATE ON "public"."client_goals" FOR EACH ROW EXECUTE FUNCTION "public"."update_client_goals_updated_at"();



CREATE OR REPLACE TRIGGER "trg_client_routines_suspended_notify" AFTER UPDATE OF "status" ON "public"."client_routines" FOR EACH ROW WHEN ((("new"."status" = 'suspended'::"text") AND ("old"."status" IS DISTINCT FROM 'suspended'::"text"))) EXECUTE FUNCTION "public"."notify_routine_suspended"();



CREATE OR REPLACE TRIGGER "trg_client_users_updated_at" BEFORE UPDATE ON "public"."client_users" FOR EACH ROW EXECUTE FUNCTION "public"."set_client_users_updated_at"();



CREATE OR REPLACE TRIGGER "trg_dimension_state_updated_at" BEFORE UPDATE ON "public"."dimension_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_dimension_state_updated_at"();



CREATE OR REPLACE TRIGGER "trg_document_review_approved" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."on_document_review_approved"();



CREATE OR REPLACE TRIGGER "trg_document_review_rejected" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."on_document_review_rejected"();



CREATE OR REPLACE TRIGGER "trg_drop_bigquery_fdw_server" BEFORE DELETE ON "public"."bigquery_servers" FOR EACH ROW EXECUTE FUNCTION "public"."drop_bigquery_fdw_server"();



CREATE OR REPLACE TRIGGER "trg_enqueue_routine_on_doc_complete" AFTER UPDATE OF "status" ON "public"."client_knowledge_documents" FOR EACH ROW EXECUTE FUNCTION "public"."on_knowledge_document_complete"();



CREATE OR REPLACE TRIGGER "trg_ensure_approval_stats" AFTER INSERT ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "public"."ensure_client_approval_stats"();



CREATE OR REPLACE TRIGGER "trg_knowledge_on_approval_completed" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."on_approval_completed"();



CREATE OR REPLACE TRIGGER "trg_redispatch_after_approval" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."redispatch_routine_after_approval"();



CREATE OR REPLACE TRIGGER "trg_sale_approved" AFTER UPDATE ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."on_approval_sale_approved"();



CREATE OR REPLACE TRIGGER "trg_seed_client_owner" AFTER INSERT ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "public"."seed_client_owner"();



CREATE OR REPLACE TRIGGER "trg_shared_business_memory_meta_updated_at" BEFORE UPDATE ON "public"."shared_business_memory_meta" FOR EACH ROW EXECUTE FUNCTION "public"."update_shared_business_memory_meta_updated_at"();



CREATE OR REPLACE TRIGGER "trg_shared_business_memory_updated_at" BEFORE UPDATE ON "public"."shared_business_memory" FOR EACH ROW EXECUTE FUNCTION "public"."update_shared_business_memory_updated_at"();



CREATE OR REPLACE TRIGGER "trg_sml_normalize" BEFORE INSERT OR UPDATE ON "public"."shared_memory_links" FOR EACH ROW EXECUTE FUNCTION "public"."normalize_shared_memory_link"();



CREATE OR REPLACE TRIGGER "trg_update_approval_stats" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."update_approval_stats"();



CREATE OR REPLACE TRIGGER "trigger_update_data_source_mappings_updated_at" BEFORE UPDATE ON "public"."data_source_mappings" FOR EACH ROW EXECUTE FUNCTION "public"."update_data_source_mappings_updated_at"();



ALTER TABLE ONLY "admin"."tenant_wipe_audit"
    ADD CONSTRAINT "tenant_wipe_audit_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "admin"."tenant_wipe_jobs"("job_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "analytics_v2"."dim_clientes"("customer_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_data_competencia_id_fkey" FOREIGN KEY ("data_competencia_id") REFERENCES "analytics_v2"."dim_datas"("data_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_fornecedor_id_fkey" FOREIGN KEY ("fornecedor_id") REFERENCES "analytics_v2"."dim_fornecedores"("fornecedor_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_produto_id_fkey" FOREIGN KEY ("produto_id") REFERENCES "analytics_v2"."dim_inventory"("inventory_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."ingest_staging"
    ADD CONSTRAINT "ingest_staging_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."ingest_staging"
    ADD CONSTRAINT "ingest_staging_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "public"."client_data_sources"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credencial_servico_externo"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."agent_lists"
    ADD CONSTRAINT "agent_lists_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_sessions"
    ADD CONSTRAINT "agent_sessions_agent_catalog_id_fkey" FOREIGN KEY ("agent_catalog_id") REFERENCES "public"."agent_catalog"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."approval_requests"
    ADD CONSTRAINT "approval_requests_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."artifact_log"
    ADD CONSTRAINT "artifact_log_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."artifact_log"
    ADD CONSTRAINT "artifact_log_execution_id_fkey" FOREIGN KEY ("execution_id") REFERENCES "public"."client_routine_executions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."audit_log"
    ADD CONSTRAINT "audit_log_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "bigquery_foreign_tables_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credencial_servico_externo"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."calendar_watch_channels"
    ADD CONSTRAINT "calendar_watch_channels_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_approval_rules"
    ADD CONSTRAINT "client_approval_rules_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "client_data_sources_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credencial_servico_externo"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "client_data_sources_integration_token_id_fkey" FOREIGN KEY ("integration_token_id") REFERENCES "public"."integration_tokens"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_slug_fkey" FOREIGN KEY ("slug") REFERENCES "public"."kpi_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_agent_slug_fkey" FOREIGN KEY ("agent_slug") REFERENCES "public"."agent_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_goals"
    ADD CONSTRAINT "client_goals_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_insights"
    ADD CONSTRAINT "client_insights_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_document_type_id_fkey" FOREIGN KEY ("document_type_id") REFERENCES "public"."knowledge_document_types"("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_users"
    ADD CONSTRAINT "client_users_auth_user_fkey" FOREIGN KEY ("auth_user_id") REFERENCES "auth"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."client_users"
    ADD CONSTRAINT "client_users_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversa"
    ADD CONSTRAINT "conversa_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cross_agent_routines"
    ADD CONSTRAINT "cross_agent_routines_trigger_document_id_fkey" FOREIGN KEY ("trigger_document_id") REFERENCES "public"."knowledge_document_types"("id");



ALTER TABLE ONLY "public"."csv_import_staging"
    ADD CONSTRAINT "csv_import_staging_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "public"."client_data_sources"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."dimension_state"
    ADD CONSTRAINT "dimension_state_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."doc_templates"
    ADD CONSTRAINT "doc_templates_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "fk_bigquery_foreign_tables_client" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "fk_bigquery_servers_client" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "fk_client_data_sources_client" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."credencial_servico_externo"
    ADD CONSTRAINT "fk_credencial_servico_externo_client" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "fk_server" FOREIGN KEY ("server_name") REFERENCES "public"."bigquery_servers"("server_name") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."frontend_events"
    ADD CONSTRAINT "frontend_events_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_agent_slug_fkey" FOREIGN KEY ("agent_slug") REFERENCES "public"."agent_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_document_type_id_fkey" FOREIGN KEY ("document_type_id") REFERENCES "public"."knowledge_document_types"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."conversa"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."nps_responses"
    ADD CONSTRAINT "nps_responses_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."polp_accounts"
    ADD CONSTRAINT "polp_accounts_integration_id_fkey" FOREIGN KEY ("integration_id") REFERENCES "public"."polp_integrations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."polp_bills"
    ADD CONSTRAINT "polp_bills_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."polp_integrations"
    ADD CONSTRAINT "polp_integrations_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."polp_transactions"
    ADD CONSTRAINT "polp_transactions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_schedule_id_fkey" FOREIGN KEY ("schedule_id") REFERENCES "public"."report_schedules"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_schedules"
    ADD CONSTRAINT "report_schedules_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shared_business_memory"
    ADD CONSTRAINT "shared_business_memory_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shared_business_memory_meta"
    ADD CONSTRAINT "shared_business_memory_meta_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shared_business_memory_versions"
    ADD CONSTRAINT "shared_business_memory_versions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shared_memory_links"
    ADD CONSTRAINT "shared_memory_links_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shared_memory_links"
    ADD CONSTRAINT "shared_memory_links_source_memory_id_fkey" FOREIGN KEY ("source_memory_id") REFERENCES "public"."shared_business_memory"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."shared_memory_links"
    ADD CONSTRAINT "shared_memory_links_target_memory_id_fkey" FOREIGN KEY ("target_memory_id") REFERENCES "public"."shared_business_memory"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."sql_table_config"
    ADD CONSTRAINT "sql_table_config_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_agent_catalog_id_fkey" FOREIGN KEY ("agent_catalog_id") REFERENCES "public"."agent_catalog"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."uploaded_files_metadata"
    ADD CONSTRAINT "uploaded_files_metadata_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "vector_db"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "vector_db"."documents"
    ADD CONSTRAINT "documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



CREATE POLICY "authenticated read" ON "analytics_v2"."dim_datas" FOR SELECT USING (("auth"."role"() = 'authenticated'::"text"));



ALTER TABLE "analytics_v2"."dim_clientes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."dim_datas" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."dim_fornecedores" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."dim_inventory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."fato_transacoes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."ingest_staging" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "ingest_staging_own_client" ON "analytics_v2"."ingest_staging" USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ("client_id" = "public"."get_my_client_id"())));



CREATE POLICY "own client" ON "analytics_v2"."dim_clientes" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."dim_fornecedores" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."dim_inventory" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."fato_transacoes" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."reg_jobs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "analytics_v2"."reg_jobs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_catalog" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_lists" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "agent_lists_service_role" ON "public"."agent_lists" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "agent_lists_tenant_isolation" ON "public"."agent_lists" USING (("client_id" = ("current_setting"('app.current_client_id'::"text", true))::"uuid"));



ALTER TABLE "public"."agent_sessions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "agent_sessions_own_client" ON "public"."agent_sessions" USING (("client_id" = ( SELECT "clientes_blu"."client_id"
   FROM "public"."clientes_blu"
  WHERE ("agent_sessions"."id" = "auth"."uid"())
 LIMIT 1)));



ALTER TABLE "public"."app_config" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "app_config_service_only" ON "public"."app_config" USING (false);



ALTER TABLE "public"."approval_requests" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "approval_rules: client manages own" ON "public"."client_approval_rules" USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "approval_rules: client sees own" ON "public"."client_approval_rules" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "approval_stats: client sees own" ON "public"."client_approval_stats" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."artifact_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."audit_log" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "authenticated insert own" ON "public"."clientes_blu" FOR INSERT TO "authenticated" WITH CHECK (("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text")));



CREATE POLICY "authenticated read own" ON "public"."clientes_blu" FOR SELECT TO "authenticated" USING (("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text")));



CREATE POLICY "authenticated update own" ON "public"."clientes_blu" FOR UPDATE TO "authenticated" USING (("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text"))) WITH CHECK (("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text")));



ALTER TABLE "public"."bigquery_foreign_tables" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "bigquery_foreign_tables_delete" ON "public"."bigquery_foreign_tables" FOR DELETE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "bigquery_foreign_tables_insert" ON "public"."bigquery_foreign_tables" FOR INSERT TO "authenticated" WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "bigquery_foreign_tables_select" ON "public"."bigquery_foreign_tables" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "bigquery_foreign_tables_update" ON "public"."bigquery_foreign_tables" FOR UPDATE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."bigquery_servers" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "bigquery_servers_access" ON "public"."bigquery_servers" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



CREATE POLICY "bigquery_servers_update" ON "public"."bigquery_servers" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"())))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



CREATE POLICY "bigquery_servers_write" ON "public"."bigquery_servers" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



ALTER TABLE "public"."calendar_settings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."calendar_watch_channels" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "car_public_read" ON "public"."cross_agent_routines" FOR SELECT USING (true);



CREATE POLICY "ckd_client_all" ON "public"."client_knowledge_documents" USING (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."client_approval_rules" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_approval_stats" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_data_sources" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "client_data_sources_access" ON "public"."client_data_sources" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



CREATE POLICY "client_data_sources_update" ON "public"."client_data_sources" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"())))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



CREATE POLICY "client_data_sources_write" ON "public"."client_data_sources" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = "public"."get_my_client_id"()))));



ALTER TABLE "public"."client_dimension_kpis" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_enabled_agents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_goals" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_insights" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_knowledge_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_notification_preferences" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "client_own_dimension_state" ON "public"."dimension_state" USING (("client_id" = ("current_setting"('app.client_id'::"text", true))::"uuid"));



CREATE POLICY "client_own_goals" ON "public"."client_goals" USING (("client_id" = ("current_setting"('app.client_id'::"text", true))::"uuid"));



CREATE POLICY "client_own_memory_versions" ON "public"."shared_business_memory_versions" USING (("client_id" = ("current_setting"('app.client_id'::"text", true))::"uuid"));



CREATE POLICY "client_own_shared_memory" ON "public"."shared_business_memory" USING (("client_id" = ("current_setting"('app.client_id'::"text", true))::"uuid"));



CREATE POLICY "client_own_shared_memory_meta" ON "public"."shared_business_memory_meta" USING (("client_id" = ("current_setting"('app.client_id'::"text", true))::"uuid"));



CREATE POLICY "client_read_own" ON "public"."sql_table_config" FOR SELECT TO "authenticated" USING (("client_id" IN ( SELECT "clientes_blu"."client_id"
   FROM "public"."clientes_blu"
  WHERE ("clientes_blu"."external_user_id" = ("auth"."uid"())::"text"))));



ALTER TABLE "public"."client_routine_executions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_routines" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_users" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "client_users_delete" ON "public"."client_users" FOR DELETE USING ((("client_id" = "public"."get_my_client_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."client_users" "cu"
  WHERE (("cu"."client_id" = "public"."get_my_client_id"()) AND ("cu"."auth_user_id" = "auth"."uid"()) AND ("cu"."role" = ANY (ARRAY['owner'::"text", 'admin'::"text"])))))));



CREATE POLICY "client_users_insert" ON "public"."client_users" FOR INSERT WITH CHECK ((("client_id" = "public"."get_my_client_id"()) AND ((NOT (EXISTS ( SELECT 1
   FROM "public"."client_users" "client_users_1"
  WHERE ("client_users_1"."client_id" = "public"."get_my_client_id"())))) OR (EXISTS ( SELECT 1
   FROM "public"."client_users" "cu"
  WHERE (("cu"."client_id" = "public"."get_my_client_id"()) AND ("cu"."auth_user_id" = "auth"."uid"()) AND ("cu"."role" = ANY (ARRAY['owner'::"text", 'admin'::"text"]))))))));



CREATE POLICY "client_users_select" ON "public"."client_users" FOR SELECT USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "client_users_service_role" ON "public"."client_users" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text")) WITH CHECK ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "client_users_update" ON "public"."client_users" FOR UPDATE USING ((("client_id" = "public"."get_my_client_id"()) AND (("auth_user_id" = "auth"."uid"()) OR (EXISTS ( SELECT 1
   FROM "public"."client_users" "cu"
  WHERE (("cu"."client_id" = "public"."get_my_client_id"()) AND ("cu"."auth_user_id" = "auth"."uid"()) AND ("cu"."role" = ANY (ARRAY['owner'::"text", 'admin'::"text"])))))))) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."clientes_blu" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversa" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."credencial_servico_externo" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."cross_agent_routines" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."csv_import_staging" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."data_source_mappings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."dimension_state" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."doc_templates" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "doc_templates_delete" ON "public"."doc_templates" FOR DELETE USING ((("is_system" = false) AND ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



CREATE POLICY "doc_templates_insert" ON "public"."doc_templates" FOR INSERT WITH CHECK ((("is_system" = false) AND ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



CREATE POLICY "doc_templates_select" ON "public"."doc_templates" FOR SELECT USING ((("is_system" = true) OR ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



ALTER TABLE "public"."document_versions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "document_versions_select" ON "public"."document_versions" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."documents" "d"
  WHERE (("d"."id" = "document_versions"."document_id") AND ("d"."client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")))));



ALTER TABLE "public"."documents" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "documents_delete" ON "public"."documents" FOR DELETE USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_insert" ON "public"."documents" FOR INSERT WITH CHECK (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_select" ON "public"."documents" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_update" ON "public"."documents" FOR UPDATE USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."frontend_events" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "insert own client" ON "public"."calendar_settings" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"())));



ALTER TABLE "public"."integration_configs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."integration_tokens" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "kar_public_read" ON "public"."knowledge_agent_requirements" FOR SELECT USING (true);



CREATE POLICY "kdt_public_read" ON "public"."knowledge_document_types" FOR SELECT USING (true);



ALTER TABLE "public"."knowledge_agent_requirements" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."knowledge_document_types" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."knowledge_tag_definitions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."kpi_catalog" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "ktd_public_read" ON "public"."knowledge_tag_definitions" FOR SELECT USING (true);



ALTER TABLE "public"."messages" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "no_public_access" ON "public"."app_config" AS RESTRICTIVE USING (false);



CREATE POLICY "notif_prefs: client manages own" ON "public"."client_notification_preferences" USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "notif_prefs: client sees own" ON "public"."client_notification_preferences" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."notifications" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."nps_responses" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "own client" ON "public"."approval_requests" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."artifact_log" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."audit_log" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."calendar_settings" FOR SELECT USING (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"())));



CREATE POLICY "own client" ON "public"."client_dimension_kpis" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_enabled_agents" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_insights" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_routines" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."conversa" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."credencial_servico_externo" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."csv_import_staging" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."data_source_mappings" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."integration_configs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."messages" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."nps_responses" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."report_runs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."report_schedules" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."standalone_agent_sessions" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."uploaded_files_metadata" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client delete" ON "public"."integration_tokens" FOR DELETE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client delete" ON "public"."notifications" FOR DELETE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client insert" ON "public"."frontend_events" FOR INSERT TO "authenticated" WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client insert" ON "public"."integration_tokens" FOR INSERT TO "authenticated" WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client insert" ON "public"."notifications" FOR INSERT TO "authenticated" WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client read" ON "public"."client_routine_executions" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client read" ON "public"."integration_tokens" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client read" ON "public"."notifications" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client update" ON "public"."integration_tokens" FOR UPDATE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client update" ON "public"."notifications" FOR UPDATE TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."polp_accounts" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "polp_accounts: own client read" ON "public"."polp_accounts" FOR SELECT TO "authenticated" USING ((("client_id" IN ( SELECT "client_users"."client_id"
   FROM "public"."client_users"
  WHERE ("client_users"."auth_user_id" = "auth"."uid"()))) OR ("client_id" = "public"."get_my_client_id"())));



ALTER TABLE "public"."polp_bills" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "polp_bills: own client read" ON "public"."polp_bills" FOR SELECT TO "authenticated" USING ((("client_id" IN ( SELECT "client_users"."client_id"
   FROM "public"."client_users"
  WHERE ("client_users"."auth_user_id" = "auth"."uid"()))) OR ("client_id" = "public"."get_my_client_id"())));



ALTER TABLE "public"."polp_integrations" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "polp_integrations: own client read" ON "public"."polp_integrations" FOR SELECT TO "authenticated" USING ((("client_id" IN ( SELECT "client_users"."client_id"
   FROM "public"."client_users"
  WHERE ("client_users"."auth_user_id" = "auth"."uid"()))) OR ("client_id" = "public"."get_my_client_id"())));



ALTER TABLE "public"."polp_transactions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "polp_transactions: own client read" ON "public"."polp_transactions" FOR SELECT TO "authenticated" USING ((("client_id" IN ( SELECT "client_users"."client_id"
   FROM "public"."client_users"
  WHERE ("client_users"."auth_user_id" = "auth"."uid"()))) OR ("client_id" = "public"."get_my_client_id"())));



CREATE POLICY "read all" ON "public"."agent_catalog" FOR SELECT TO "authenticated" USING (("is_active" = true));



CREATE POLICY "read all" ON "public"."kpi_catalog" FOR SELECT TO "authenticated" USING (true);



ALTER TABLE "public"."report_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report_schedules" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "service role only" ON "public"."calendar_watch_channels" USING (false);



CREATE POLICY "service_role_all" ON "public"."sql_table_config" TO "service_role" USING (true) WITH CHECK (true);



ALTER TABLE "public"."shared_business_memory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shared_business_memory_meta" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shared_business_memory_versions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shared_memory_links" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "sml_client_all" ON "public"."shared_memory_links" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"())) WITH CHECK (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."sql_table_config" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."standalone_agent_sessions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "update own client" ON "public"."calendar_settings" FOR UPDATE USING (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"()))) WITH CHECK (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"())));



ALTER TABLE "public"."uploaded_files_metadata" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "vector_db"."document_chunks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "vector_db"."documents" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "own client" ON "vector_db"."document_chunks" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "vector_db"."documents" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";






GRANT USAGE ON SCHEMA "analytics_v2" TO "authenticated";
GRANT USAGE ON SCHEMA "analytics_v2" TO "service_role";
GRANT USAGE ON SCHEMA "analytics_v2" TO "anon";



GRANT USAGE ON SCHEMA "bigquery" TO "authenticated";
GRANT USAGE ON SCHEMA "bigquery" TO "service_role";






GRANT ALL ON SCHEMA "fdw" TO "service_role";






GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT USAGE ON SCHEMA "vector_db" TO "authenticated";
GRANT USAGE ON SCHEMA "vector_db" TO "service_role";

































































































































REVOKE ALL ON FUNCTION "admin"."request_client_deletion"("p_client_id" "uuid", "p_reason" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "admin"."request_client_deletion"("p_client_id" "uuid", "p_reason" "text") TO "service_role";



REVOKE ALL ON FUNCTION "admin"."tenant_wipe_tick"("p_batch_size" integer, "p_max_seconds" integer) FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."_period_range"("p_period" "text") FROM PUBLIC;



GRANT ALL ON FUNCTION "analytics_v2"."apply_staging_to_facts"("p_job_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."atualizar_agregados"("p_client_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."atualizar_dim_clientes"("p_client_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."atualizar_dim_fornecedores"("p_client_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."atualizar_dim_inventory"("p_client_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."enqueue_incremental_syncs"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."enqueue_polp_sync"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_admin_indicators"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_commercial_indicators"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_commercial_revenue_by_channel"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_commercial_top_clients"("p_period" "text", "p_limit" integer) FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid", "p_period" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid", "p_period" "text") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "analytics_v2"."get_finance_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "analytics_v2"."get_finance_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "analytics_v2"."get_finance_indicators"("p_period" "text") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text", "p_offset_days" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_indicators_for_client"("p_client_id" "uuid", "p_dimension" "text", "p_period" "text", "p_offset_days" integer) TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_inventory_indicators"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_kpi_mtd_comparison"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_kpi_mtd_comparison"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."get_kpi_mtd_comparison"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."get_marketing_indicators"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."get_supply_indicators"("p_period" "text") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."on_etl_job_completed"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."process_pending_csv_jobs"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."process_pending_etl_jobs"() FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."process_pending_jobs"() FROM PUBLIC;
GRANT ALL ON FUNCTION "analytics_v2"."process_pending_jobs"() TO "service_role";



GRANT ALL ON FUNCTION "analytics_v2"."reset_stuck_running_jobs"() TO "service_role";



REVOKE ALL ON FUNCTION "analytics_v2"."run_etl_job"("p_job_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid") FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."sync_polp_transactions"("p_client_id" "uuid", "p_batch_size" integer) FROM PUBLIC;



REVOKE ALL ON FUNCTION "analytics_v2"."trigger_context_report_on_etl"() FROM PUBLIC;



































































































































































































































































































































































































































































































































































































































































































GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."auto_enroll_catalog_routines"() TO "anon";
GRANT ALL ON FUNCTION "public"."auto_enroll_catalog_routines"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."auto_enroll_catalog_routines"() TO "service_role";



GRANT ALL ON FUNCTION "public"."auto_enroll_system_routines"() TO "anon";
GRANT ALL ON FUNCTION "public"."auto_enroll_system_routines"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."auto_enroll_system_routines"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON TABLE "public"."client_routine_executions" TO "anon";
GRANT ALL ON TABLE "public"."client_routine_executions" TO "authenticated";
GRANT ALL ON TABLE "public"."client_routine_executions" TO "service_role";



REVOKE ALL ON FUNCTION "public"."claim_routine_executions"("p_batch_size" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."claim_routine_executions"("p_batch_size" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_auth_user_if_orphaned"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_auth_user_if_orphaned"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_auth_user_if_orphaned"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_credential_vault_secret"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_credential_vault_secret"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_credential_vault_secret"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_datasource_storage_object"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_datasource_storage_object"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_datasource_storage_object"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_storage_object"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_storage_object"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_storage_object"() TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "service_role";



REVOKE ALL ON FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "service_role";



GRANT ALL ON TABLE "public"."client_routines" TO "authenticated";
GRANT ALL ON TABLE "public"."client_routines" TO "service_role";



GRANT ALL ON TABLE "public"."cross_agent_routines" TO "anon";
GRANT ALL ON TABLE "public"."cross_agent_routines" TO "authenticated";
GRANT ALL ON TABLE "public"."cross_agent_routines" TO "service_role";



GRANT ALL ON FUNCTION "public"."cross_agent_routines"("public"."client_routines") TO "anon";
GRANT ALL ON FUNCTION "public"."cross_agent_routines"("public"."client_routines") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cross_agent_routines"("public"."client_routines") TO "service_role";



GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."dispatch_context_report_on_ingestion"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."dispatch_context_report_on_ingestion"() TO "anon";
GRANT ALL ON FUNCTION "public"."dispatch_context_report_on_ingestion"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."dispatch_context_report_on_ingestion"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."dispatch_routine_event"("p_routine_id" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."dispatch_routine_event"("p_routine_id" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."dispatch_routine_executions"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."dispatch_routine_executions"() TO "service_role";



GRANT ALL ON FUNCTION "public"."drop_bigquery_fdw_server"() TO "anon";
GRANT ALL ON FUNCTION "public"."drop_bigquery_fdw_server"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."drop_bigquery_fdw_server"() TO "service_role";



GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."enqueue_custom_routine"("p_client_routine_id" "uuid", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."enqueue_custom_routine"("p_client_routine_id" "uuid", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."enqueue_monthly_close"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."enqueue_monthly_close"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."enqueue_routine_for_me"("p_routine_id" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."enqueue_routine_for_me"("p_routine_id" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."enqueue_routine_for_me"("p_routine_id" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."ensure_bigquery_fdw_table"("p_client_id" "uuid", "p_cred_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."ensure_bigquery_fdw_table"("p_client_id" "uuid", "p_cred_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."ensure_bigquery_fdw_table"("p_client_id" "uuid", "p_cred_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "anon";
GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."exec_sql"("p_query" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."exec_sql"("p_query" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."expire_pending_approvals"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."expire_pending_approvals"() TO "anon";
GRANT ALL ON FUNCTION "public"."expire_pending_approvals"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."expire_pending_approvals"() TO "service_role";



GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."finalize_onboarding"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."finalize_onboarding"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."finalize_onboarding"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."fire_event_for_client"("p_event_type" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."fire_event_for_client"("p_event_type" "text", "p_client_id" "uuid", "p_trigger_data" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_admin_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_admin_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_admin_indicators"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_churn_rate_monthly"("p_client_id" "uuid", "p_window_months" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_churn_rate_monthly"("p_client_id" "uuid", "p_window_months" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_commercial_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_commercial_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_commercial_indicators"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_credential_service_account"("p_credential_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_customer_segments"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_customer_segments"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_customer_segments"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_finance_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_finance_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_finance_indicators"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_inventory_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_inventory_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_inventory_indicators"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_marketing_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_marketing_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_marketing_indicators"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_context_metrics"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_context_metrics"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_context_metrics"("p_period" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text", "p_room" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text", "p_room" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text", "p_room" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_new_clients_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_pedidos_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_pedidos_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_platform_google_oauth_config"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_platform_google_oauth_config"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_recent_transactions"("p_client_id" "uuid", "p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_recent_transactions"("p_client_id" "uuid", "p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_recent_transactions"("p_client_id" "uuid", "p_limit" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_revenue_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_revenue_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_routine_checkpoints"("p_routine_id" "text", "p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_supply_indicators"("p_period" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_supply_indicators"("p_period" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_supply_indicators"("p_period" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_ticket_medio_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_ticket_medio_monthly_rate"("p_client_id" "uuid", "p_window_months" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_top_customers"("p_client_id" "uuid", "p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_top_customers"("p_client_id" "uuid", "p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_top_customers"("p_client_id" "uuid", "p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_unified_tasks"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_new_auth_user_auto_confirm"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user_auto_confirm"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user_auto_confirm"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."is_onboarded_client"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."is_onboarded_client"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_onboarded_client"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "service_role";



GRANT ALL ON TABLE "public"."approval_requests" TO "authenticated";
GRANT ALL ON TABLE "public"."approval_requests" TO "service_role";



GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "service_role";



GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."migrate_credential_to_vault"("p_credential_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."normalize_shared_memory_link"() TO "anon";
GRANT ALL ON FUNCTION "public"."normalize_shared_memory_link"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."normalize_shared_memory_link"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."notify_routine_suspended"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."notify_routine_suspended"() TO "anon";
GRANT ALL ON FUNCTION "public"."notify_routine_suspended"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."notify_routine_suspended"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."offboard_client"("p_client_id" "uuid", "p_batch_size" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."offboard_client"("p_client_id" "uuid", "p_batch_size" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."offboard_client_batch"("p_client_id" "uuid", "p_schema" "text", "p_table" "text", "p_batch_size" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."offboard_client_batch"("p_client_id" "uuid", "p_schema" "text", "p_table" "text", "p_batch_size" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "service_role";



GRANT ALL ON FUNCTION "public"."on_approval_sale_approved"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_approval_sale_approved"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_approval_sale_approved"() TO "service_role";



GRANT ALL ON FUNCTION "public"."on_document_review_approved"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_document_review_approved"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_document_review_approved"() TO "service_role";



GRANT ALL ON FUNCTION "public"."on_document_review_rejected"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_document_review_rejected"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_document_review_rejected"() TO "service_role";



GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "service_role";



GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."ops_list_sync_jobs"() TO "anon";
GRANT ALL ON FUNCTION "public"."ops_list_sync_jobs"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."ops_list_sync_jobs"() TO "service_role";



GRANT ALL ON FUNCTION "public"."ops_retry_job"("p_job_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."ops_retry_job"("p_job_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ops_retry_job"("p_job_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."polp_set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."polp_set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."polp_set_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "anon";
GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."reap_stale_routine_executions"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reap_stale_routine_executions"() TO "service_role";



GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_dimension" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_dimension" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_dimension" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_room" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text", "p_dimension" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_room" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text", "p_dimension" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_insight"("p_client_id" "uuid", "p_room" "text", "p_kpi" "text", "p_title" "text", "p_observation" "text", "p_severity" "text", "p_recommendation" "text", "p_metric_value" numeric, "p_baseline_value" numeric, "p_variance_pct" numeric, "p_payload" "jsonb", "p_run_date" "date", "p_prompt_version" "text", "p_dimension" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."record_routine_failure"("p_client_id" "uuid", "p_routine_id" "text", "p_max_failures" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."record_routine_failure"("p_client_id" "uuid", "p_routine_id" "text", "p_max_failures" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."redispatch_routine_after_approval"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."redispatch_routine_after_approval"() TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_analytics_views"() TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_analytics_views"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_analytics_views"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_client_dashboards"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."reset_routine_failures"("p_client_id" "uuid", "p_routine_id" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reset_routine_failures"("p_client_id" "uuid", "p_routine_id" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."run_incremental_etl"("p_hours_since_last_sync" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."schedule_monthly_context_reports"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."schedule_monthly_context_reports"() TO "service_role";



GRANT ALL ON FUNCTION "public"."seed_client_owner"() TO "anon";
GRANT ALL ON FUNCTION "public"."seed_client_owner"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."seed_client_owner"() TO "service_role";



GRANT ALL ON FUNCTION "public"."send_email_hook"() TO "anon";
GRANT ALL ON FUNCTION "public"."send_email_hook"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."send_email_hook"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."send_email_hook"("event" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."send_email_hook"("event" "jsonb") TO "service_role";
GRANT ALL ON FUNCTION "public"."send_email_hook"("event" "jsonb") TO "supabase_auth_admin";



GRANT ALL ON FUNCTION "public"."set_agent_lists_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_agent_lists_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_agent_lists_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."set_client_users_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_client_users_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_client_users_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."set_current_client_id"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."set_current_client_id"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."set_current_customer_id"("p_customer_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."set_current_customer_id"("p_customer_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_ui_pref"("p_key" "text", "p_value" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."set_ui_pref"("p_key" "text", "p_value" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_ui_pref"("p_key" "text", "p_value" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sincronizar_csv_cliente"("p_job_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."sincronizar_csv_cliente"("p_job_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sincronizar_csv_cliente"("p_job_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."soft_delete_client"("p_client_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."soft_delete_client"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_client_goals_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_client_goals_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_client_goals_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_dimension_state_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_dimension_state_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_dimension_state_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_shared_business_memory_meta_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_shared_business_memory_meta_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_shared_business_memory_meta_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_shared_business_memory_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_shared_business_memory_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_shared_business_memory_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."upsert_routine_checkpoint"("p_client_id" "uuid", "p_routine_id" "text", "p_exec_id" "uuid", "p_step_number" integer, "p_state_value" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."upsert_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text", "p_access_token" "text", "p_refresh_token" "text", "p_token_type" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_metadata" "jsonb", "p_is_default" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."upsert_user_oauth_tokens"("p_client_id" "uuid", "p_provider" "text", "p_account_email" "text", "p_access_token" "text", "p_refresh_token" "text", "p_token_type" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_metadata" "jsonb", "p_is_default" boolean) TO "service_role";
























GRANT SELECT ON TABLE "admin"."v_active_wipes" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_clientes" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_clientes" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_clientes_cliente_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_datas" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_datas" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_datas_data_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_fornecedores" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_fornecedores" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_fornecedores_fornecedor_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_inventory" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_inventory" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_inventory_inventory_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."fato_transacoes" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."fato_transacoes" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."ingest_staging" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."ingest_staging" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."ingest_staging_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_distribuicao_regional" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."mv_distribuicao_regional" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_resumo_dashboard" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."mv_resumo_dashboard" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_series_temporal" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."mv_series_temporal" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_ultimos_pedidos" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."mv_ultimos_pedidos" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."reg_jobs" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."reg_jobs" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_distribuicao_regional" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."v_distribuicao_regional" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_resumo_dashboard" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."v_resumo_dashboard" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_series_temporal" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."v_series_temporal" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_ultimos_pedidos" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "analytics_v2"."v_ultimos_pedidos" TO "service_role";
























GRANT ALL ON TABLE "public"."clientes_blu" TO "anon";
GRANT ALL ON TABLE "public"."clientes_blu" TO "authenticated";
GRANT ALL ON TABLE "public"."clientes_blu" TO "service_role";



GRANT ALL ON TABLE "public"."active_clientes_blu" TO "anon";
GRANT ALL ON TABLE "public"."active_clientes_blu" TO "authenticated";
GRANT ALL ON TABLE "public"."active_clientes_blu" TO "service_role";



GRANT ALL ON TABLE "public"."agent_catalog" TO "anon";
GRANT ALL ON TABLE "public"."agent_catalog" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_catalog" TO "service_role";



GRANT ALL ON TABLE "public"."agent_lists" TO "anon";
GRANT ALL ON TABLE "public"."agent_lists" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_lists" TO "service_role";



GRANT ALL ON TABLE "public"."agent_sessions" TO "anon";
GRANT ALL ON TABLE "public"."agent_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."app_config" TO "service_role";



GRANT ALL ON TABLE "public"."artifact_log" TO "anon";
GRANT ALL ON TABLE "public"."artifact_log" TO "authenticated";
GRANT ALL ON TABLE "public"."artifact_log" TO "service_role";



GRANT ALL ON TABLE "public"."audit_log" TO "anon";
GRANT ALL ON TABLE "public"."audit_log" TO "authenticated";
GRANT ALL ON TABLE "public"."audit_log" TO "service_role";



GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "anon";
GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "authenticated";
GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "service_role";



GRANT ALL ON TABLE "public"."bigquery_servers" TO "anon";
GRANT ALL ON TABLE "public"."bigquery_servers" TO "authenticated";
GRANT ALL ON TABLE "public"."bigquery_servers" TO "service_role";



GRANT ALL ON TABLE "public"."calendar_settings" TO "anon";
GRANT ALL ON TABLE "public"."calendar_settings" TO "authenticated";
GRANT ALL ON TABLE "public"."calendar_settings" TO "service_role";



GRANT ALL ON TABLE "public"."calendar_watch_channels" TO "anon";
GRANT ALL ON TABLE "public"."calendar_watch_channels" TO "authenticated";
GRANT ALL ON TABLE "public"."calendar_watch_channels" TO "service_role";



GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."canonical_columns" TO "anon";
GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."canonical_columns" TO "authenticated";
GRANT ALL ON TABLE "public"."canonical_columns" TO "service_role";



GRANT ALL ON SEQUENCE "public"."canonical_columns_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."canonical_columns_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."canonical_columns_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."client_approval_rules" TO "anon";
GRANT ALL ON TABLE "public"."client_approval_rules" TO "authenticated";
GRANT ALL ON TABLE "public"."client_approval_rules" TO "service_role";



GRANT ALL ON TABLE "public"."client_approval_stats" TO "anon";
GRANT ALL ON TABLE "public"."client_approval_stats" TO "authenticated";
GRANT ALL ON TABLE "public"."client_approval_stats" TO "service_role";



GRANT ALL ON TABLE "public"."client_data_sources" TO "anon";
GRANT ALL ON TABLE "public"."client_data_sources" TO "authenticated";
GRANT ALL ON TABLE "public"."client_data_sources" TO "service_role";



GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "anon";
GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "authenticated";
GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "service_role";



GRANT ALL ON TABLE "public"."client_enabled_agents" TO "anon";
GRANT ALL ON TABLE "public"."client_enabled_agents" TO "authenticated";
GRANT ALL ON TABLE "public"."client_enabled_agents" TO "service_role";



GRANT ALL ON TABLE "public"."client_goals" TO "anon";
GRANT ALL ON TABLE "public"."client_goals" TO "authenticated";
GRANT ALL ON TABLE "public"."client_goals" TO "service_role";



GRANT ALL ON TABLE "public"."client_insights" TO "authenticated";
GRANT ALL ON TABLE "public"."client_insights" TO "service_role";



GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "anon";
GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "service_role";



GRANT ALL ON TABLE "public"."client_notification_preferences" TO "anon";
GRANT ALL ON TABLE "public"."client_notification_preferences" TO "authenticated";
GRANT ALL ON TABLE "public"."client_notification_preferences" TO "service_role";



GRANT ALL ON TABLE "public"."client_users" TO "anon";
GRANT ALL ON TABLE "public"."client_users" TO "authenticated";
GRANT ALL ON TABLE "public"."client_users" TO "service_role";



GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."cnpj_enrichments" TO "anon";
GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."cnpj_enrichments" TO "authenticated";
GRANT ALL ON TABLE "public"."cnpj_enrichments" TO "service_role";



GRANT ALL ON TABLE "public"."conversa" TO "anon";
GRANT ALL ON TABLE "public"."conversa" TO "authenticated";
GRANT ALL ON TABLE "public"."conversa" TO "service_role";



GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "anon";
GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "authenticated";
GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "service_role";



GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."csv_import_staging" TO "anon";
GRANT ALL ON TABLE "public"."csv_import_staging" TO "authenticated";
GRANT ALL ON TABLE "public"."csv_import_staging" TO "service_role";



GRANT ALL ON TABLE "public"."data_source_mappings" TO "anon";
GRANT ALL ON TABLE "public"."data_source_mappings" TO "authenticated";
GRANT ALL ON TABLE "public"."data_source_mappings" TO "service_role";



GRANT ALL ON TABLE "public"."dimension_state" TO "anon";
GRANT ALL ON TABLE "public"."dimension_state" TO "authenticated";
GRANT ALL ON TABLE "public"."dimension_state" TO "service_role";



GRANT ALL ON TABLE "public"."doc_templates" TO "anon";
GRANT ALL ON TABLE "public"."doc_templates" TO "authenticated";
GRANT ALL ON TABLE "public"."doc_templates" TO "service_role";



GRANT ALL ON TABLE "public"."document_versions" TO "anon";
GRANT ALL ON TABLE "public"."document_versions" TO "authenticated";
GRANT ALL ON TABLE "public"."document_versions" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."frontend_events" TO "authenticated";
GRANT ALL ON TABLE "public"."frontend_events" TO "service_role";



GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."integration_configs" TO "anon";
GRANT ALL ON TABLE "public"."integration_configs" TO "authenticated";
GRANT ALL ON TABLE "public"."integration_configs" TO "service_role";



GRANT ALL ON TABLE "public"."integration_tokens" TO "anon";
GRANT ALL ON TABLE "public"."integration_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."integration_tokens" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_document_types" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_document_types" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_document_types" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "service_role";



GRANT ALL ON TABLE "public"."kpi_catalog" TO "anon";
GRANT ALL ON TABLE "public"."kpi_catalog" TO "authenticated";
GRANT ALL ON TABLE "public"."kpi_catalog" TO "service_role";



GRANT ALL ON TABLE "public"."messages" TO "authenticated";
GRANT ALL ON TABLE "public"."messages" TO "service_role";



GRANT ALL ON TABLE "public"."notifications" TO "anon";
GRANT ALL ON TABLE "public"."notifications" TO "authenticated";
GRANT ALL ON TABLE "public"."notifications" TO "service_role";



GRANT ALL ON TABLE "public"."nps_responses" TO "anon";
GRANT ALL ON TABLE "public"."nps_responses" TO "authenticated";
GRANT ALL ON TABLE "public"."nps_responses" TO "service_role";



GRANT ALL ON TABLE "public"."polp_accounts" TO "authenticated";
GRANT ALL ON TABLE "public"."polp_accounts" TO "service_role";



GRANT ALL ON TABLE "public"."polp_bills" TO "authenticated";
GRANT ALL ON TABLE "public"."polp_bills" TO "service_role";



GRANT ALL ON TABLE "public"."polp_integrations" TO "authenticated";
GRANT ALL ON TABLE "public"."polp_integrations" TO "service_role";



GRANT ALL ON TABLE "public"."polp_transactions" TO "authenticated";
GRANT ALL ON TABLE "public"."polp_transactions" TO "service_role";



GRANT ALL ON TABLE "public"."production_clientes_blu" TO "anon";
GRANT ALL ON TABLE "public"."production_clientes_blu" TO "authenticated";
GRANT ALL ON TABLE "public"."production_clientes_blu" TO "service_role";



GRANT ALL ON TABLE "public"."report_runs" TO "anon";
GRANT ALL ON TABLE "public"."report_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."report_runs" TO "service_role";



GRANT ALL ON TABLE "public"."report_schedules" TO "anon";
GRANT ALL ON TABLE "public"."report_schedules" TO "authenticated";
GRANT ALL ON TABLE "public"."report_schedules" TO "service_role";



GRANT ALL ON TABLE "public"."shared_business_memory" TO "anon";
GRANT ALL ON TABLE "public"."shared_business_memory" TO "authenticated";
GRANT ALL ON TABLE "public"."shared_business_memory" TO "service_role";



GRANT ALL ON TABLE "public"."shared_business_memory_meta" TO "anon";
GRANT ALL ON TABLE "public"."shared_business_memory_meta" TO "authenticated";
GRANT ALL ON TABLE "public"."shared_business_memory_meta" TO "service_role";



GRANT ALL ON TABLE "public"."shared_business_memory_versions" TO "anon";
GRANT ALL ON TABLE "public"."shared_business_memory_versions" TO "authenticated";
GRANT ALL ON TABLE "public"."shared_business_memory_versions" TO "service_role";



GRANT ALL ON TABLE "public"."shared_memory_links" TO "anon";
GRANT ALL ON TABLE "public"."shared_memory_links" TO "authenticated";
GRANT ALL ON TABLE "public"."shared_memory_links" TO "service_role";



GRANT ALL ON TABLE "public"."sql_table_config" TO "anon";
GRANT ALL ON TABLE "public"."sql_table_config" TO "authenticated";
GRANT ALL ON TABLE "public"."sql_table_config" TO "service_role";



GRANT ALL ON TABLE "public"."standalone_agent_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."standalone_agent_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."suppliers" TO "anon";
GRANT ALL ON TABLE "public"."suppliers" TO "authenticated";
GRANT ALL ON TABLE "public"."suppliers" TO "service_role";



GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "anon";
GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "authenticated";
GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "service_role";









GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "vector_db"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "vector_db"."document_chunks" TO "service_role";



GRANT ALL ON SEQUENCE "vector_db"."document_chunks_id_seq" TO "service_role";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "vector_db"."documents" TO "authenticated";
GRANT ALL ON TABLE "vector_db"."documents" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "analytics_v2" GRANT ALL ON SEQUENCES TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "analytics_v2" GRANT SELECT ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "analytics_v2" GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "vector_db" GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO "authenticated";






























-- =====================================================================
-- CRON JOBS (pg_cron) — reconstruídos de cron.job em 2026-07-20
-- =====================================================================
select cron.schedule('process-pending-etl-jobs', '* * * * *', 'SELECT analytics_v2.process_pending_etl_jobs()');
update cron.job set active=false where jobname='process-pending-etl-jobs';
select cron.schedule('enqueue_monthly_close', '0 23 28-31 * *', ' SELECT public.enqueue_monthly_close(); ');
select cron.schedule('process-pending-csv-jobs', '* * * * *', 'SELECT analytics_v2.process_pending_csv_jobs()');
select cron.schedule('enqueue_incremental_syncs_12h', '0 2,14 * * *', ' SELECT analytics_v2.enqueue_incremental_syncs(); ');
select cron.schedule('polp_sync_to_fato_6h', '0 */6 * * *', 'SELECT analytics_v2.enqueue_polp_sync();');
select cron.schedule('offboard_cleanup_nightly', '0 3 * * *', '
  DO $cleanup$
  DECLARE
    v_id       uuid;
    v_deleted  int;
    v_big_tables text[] := ARRAY[
      ''analytics_v2|dim_inventory'',
      ''analytics_v2|fato_transacoes'',
      ''analytics_v2|fato_compras'',
      ''analytics_v2|dim_clientes'',
      ''analytics_v2|dim_fornecedores''
    ];
    v_entry    text;
    v_schema   text;
    v_tbl      text;
  BEGIN
    FOR v_id IN
      SELECT client_id FROM public.clientes_blu
      WHERE deleted_at IS NOT NULL
        AND deleted_at < now() - interval ''7 days''
    LOOP
      -- Delete big tables in batches of 5000
      FOREACH v_entry IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_entry, ''|'', 1);
        v_tbl    := split_part(v_entry, ''|'', 2);
        LOOP
          EXECUTE format(
            ''WITH batch AS (SELECT ctid FROM %I.%I WHERE client_id = $1 LIMIT 5000) ''
            ''DELETE FROM %I.%I WHERE ctid IN (SELECT ctid FROM batch)'',
            v_schema, v_tbl, v_schema, v_tbl
          ) USING v_id;
          GET DIAGNOSTICS v_deleted = ROW_COUNT;
          EXIT WHEN v_deleted = 0;
        END LOOP;
      END LOOP;

      -- Hard delete the tenant row (cascade handles remaining FK children)
      DELETE FROM public.clientes_blu WHERE client_id = v_id;
    END LOOP;
  END
  $cleanup$;
  ');
select cron.schedule('reap_stale_routine_executions', '*/5 * * * *', ' SELECT public.reap_stale_routine_executions(); ');
select cron.schedule('dispatch_routine_executions', '* * * * *', ' SELECT public.dispatch_routine_executions(); ');
select cron.schedule('expire_pending_approvals_10min', '*/10 * * * *', ' SELECT public.expire_pending_approvals(); ');
select cron.schedule('tenant_wipe_worker', '* * * * *', ' SELECT count(*) FROM admin.tenant_wipe_tick(5000, 25) ');
select cron.schedule('process-pending-bigquery-jobs', '* * * * *', 'SELECT analytics_v2.process_pending_jobs();');
select cron.schedule('reg_jobs_running_watchdog', '* * * * *', ' SELECT analytics_v2.reset_stuck_running_jobs(); ');
select cron.schedule('process-pending-jobs-b', '* * * * *', 'SELECT pg_sleep(30); SELECT analytics_v2.process_pending_jobs();');
select cron.schedule('process-pending-jobs', '* * * * *', 'select analytics_v2.process_pending_jobs()');

