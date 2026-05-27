-- ============================================================================
-- Commit 1 / 3 — Unified ingestion pipeline (CSV + xlsx + BigQuery)
--
-- Goal: collapse 2 duplicate pipelines (sincronizar_csv_cliente + run_etl_job)
-- into ONE canonical UPSERT path. This commit only ADDS the new table and
-- function — old pipelines are untouched and continue to work. Cutover and
-- drops happen in commits 2 and 3.
--
-- Design decisions (locked with user 2026-05-26):
--   • Staging lives in analytics_v2 (fdw schema is being retired).
--   • CSV/xlsx keep a single jsonb row per upload (rows[] array) — apply
--     function unnest()s internally. Same shape works for BQ bulk insert.
--   • transacao_id = md5(client_id || source_id || documento || data || sku
--                        || row_index) — robust to duplicate documento across
--     files, idempotent on re-runs.
--   • Date parsing: 3-tier (ISO → DD/MM/YYYY → Excel serial). Same for all
--     sources (BQ DATE columns come as ISO, so tier 1 catches them).
--   • tipo_transacao cascade: explicit mapping → cpf_cnpj match against
--     client cpf_cnpj → dimensional join. Same for all sources.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Unified staging table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.ingest_staging (
  id          bigserial PRIMARY KEY,
  job_id      uuid        NOT NULL,
  client_id   uuid        NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  source_id   uuid        NOT NULL REFERENCES public.client_data_sources(id) ON DELETE CASCADE,
  row_index   integer     NOT NULL,
  raw_data    jsonb       NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingest_staging_job    ON analytics_v2.ingest_staging (job_id);
CREATE INDEX IF NOT EXISTS idx_ingest_staging_source ON analytics_v2.ingest_staging (source_id);
CREATE INDEX IF NOT EXISTS idx_ingest_staging_job_row ON analytics_v2.ingest_staging (job_id, row_index);

ALTER TABLE analytics_v2.ingest_staging ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname='analytics_v2' AND tablename='ingest_staging' AND policyname='ingest_staging_own_client'
  ) THEN
    CREATE POLICY ingest_staging_own_client ON analytics_v2.ingest_staging
      USING (
        ((auth.jwt() ->> 'role') = 'service_role')
        OR (client_id = public.get_my_client_id())
      );
  END IF;
END $$;

COMMENT ON TABLE analytics_v2.ingest_staging IS
  'Unified raw staging for CSV/xlsx uploads and BigQuery (and future) ingestions. '
  'Rows are consumed and deleted by analytics_v2.apply_staging_to_facts(job_id).';

-- ---------------------------------------------------------------------------
-- 2. Shared date parser (3-tier fallback)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.parse_ingest_date(p_value text)
RETURNS date
LANGUAGE plpgsql
IMMUTABLE
AS $function$
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
$function$;

COMMENT ON FUNCTION analytics_v2.parse_ingest_date(text) IS
  '3-tier date parser: ISO → DD/MM/YYYY → Excel serial. Used by apply_staging_to_facts.';

-- ---------------------------------------------------------------------------
-- 3. Canonical UPSERT: stage rows → dimensions → fato_transacoes
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.apply_staging_to_facts(p_job_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$
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
$function$;

COMMENT ON FUNCTION analytics_v2.apply_staging_to_facts(uuid) IS
  'Canonical UPSERT for ingested raw rows. Reads analytics_v2.ingest_staging '
  'rows for the given job, renames source columns to canonical names via '
  'client_data_sources.column_mapping, upserts dim_*, then fato_transacoes '
  'with cascading tipo_transacao classification. Used by both CSV/xlsx and '
  'BigQuery pipelines.';

COMMIT;
