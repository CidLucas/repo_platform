-- =============================================================================
-- Migration: populate entry_type in both ETL pipelines
-- =============================================================================
-- 1. BQ ETL function (process_etl_job): add entry_type to INSERT + ON CONFLICT
-- 2. Polp batch sync function: add entry_type to INSERT + ON CONFLICT
-- =============================================================================

-- 1. BQ ETL — recreate function with entry_type classification
CREATE OR REPLACE FUNCTION analytics_v2.process_etl_job(p_job_id text)
RETURNS void
LANGUAGE plpgsql
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

-- 2. Polp batch sync — recreate function with entry_type
CREATE OR REPLACE FUNCTION analytics_v2.batch_sync_polp(
    p_client_id  uuid,
    p_batch_size int DEFAULT 500
)
RETURNS int
LANGUAGE plpgsql
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

COMMENT ON FUNCTION analytics_v2.batch_sync_polp IS
  'Syncs polp_transactions -> fato_transacoes in batches. '
  'entry_type: CREDIT→revenue, DEBIT→expense, else banking. '
  'tipo_lancamento always bancario for Polp rows.';

-- 3. Backfill entry_type for existing Polp rows (CREDIT/DEBIT já sincronizados)
-- Polp rows têm transacao_id='polp_*' e tipo_lancamento='bancario'
UPDATE analytics_v2.fato_transacoes ft
SET entry_type = CASE
    WHEN pt.type = 'CREDIT' THEN 'revenue'
    WHEN pt.type = 'DEBIT'  THEN 'expense'
    ELSE 'banking'
  END
FROM public.polp_transactions pt
WHERE ft.transacao_id = 'polp_' || pt.polp_transaction_id::text
  AND ft.client_id = pt.client_id
  AND (ft.entry_type IS NULL OR ft.entry_type = 'revenue');
-- note: rows that were 'revenue' from the generic backfill may now be corrected to 'expense'

COMMENT ON COLUMN analytics_v2.fato_transacoes.entry_type IS
  'System-derived transaction direction: revenue | purchase | expense | banking. '
  'BQ NF-e: derived from CNPJ cross-reference with clientes_blu.cpf_cnpj. '
  'Polp: CREDIT=revenue, DEBIT=expense. '
  'Never user-mapped — always set by backend classification logic.';
