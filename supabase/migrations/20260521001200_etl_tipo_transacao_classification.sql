-- ─────────────────────────────────────────────────────────────────────────────
-- FASE 1 · ETL: populate tipo_transacao + classificação por cpf_cnpj
--
-- Changes to run_etl_job():
--   1. Read client's cpf_cnpj from clientes_blu (v_client_cpf_cnpj).
--   2. Fato_transacoes upsert now includes tipo_transacao, tipo_lancamento,
--      categoria, subcategoria.
--   3. Classification logic (applied when tipo_transacao is NULL in source):
--        fornecedor_cnpj = client cpf_cnpj → 'venda'   (we are the supplier → revenue)
--        cliente_cpf_cnpj = client cpf_cnpj → 'compra'  (we are the buyer   → expense)
--      Comparison strips non-digits to handle formatting differences (00.000.000/0001-00 vs 00000000000100).
--   4. ON CONFLICT DO UPDATE includes the four new columns; uses COALESCE to
--      preserve an existing non-null value if the new row has null.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.run_etl_job(p_job_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2', 'fdw'
AS $function$
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

  -- 12. Upsert fato_transacoes (inclui tipo_transacao + classificação por cpf_cnpj)
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
    -- tipo_transacao: use mapped source value; if absent, classify via cpf_cnpj
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
    -- COALESCE preserves existing non-null value when incremental row has null
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
$function$;
