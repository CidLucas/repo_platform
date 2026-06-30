-- Migration: fix date parse to handle DD/MM/YYYY HH24:MI:SS (Brazilian datetime with time)
-- Root cause: sincronizar_csv_cliente tier-2 uses to_date(v, 'DD/MM/YYYY') which fails
-- when the value contains a time component like "12/09/2025 00:00:00"
-- Fix: extract date part before trying DD/MM/YYYY, and add explicit datetime format tier

CREATE OR REPLACE FUNCTION public.sincronizar_csv_cliente(p_job_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
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
  v_date_str             TEXT;  -- trimmed date string (no time component)
BEGIN
  SELECT job_id, client_id, input_params, status
  INTO v_job
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('skipped', true, 'reason', 'job not found or locked');
  END IF;

  IF v_job.status NOT IN ('pending', 'running') THEN
    RETURN jsonb_build_object('skipped', true, 'reason', 'job status ' || v_job.status);
  END IF;

  v_client_id := v_job.client_id;
  v_source_id := (v_job.input_params->>'source_id')::UUID;

  -- Mark running
  UPDATE analytics_v2.reg_jobs
  SET status = 'running', updated_at = now()
  WHERE job_id = p_job_id;

  -- Load column_mapping { canonical → source_col }
  SELECT column_mapping INTO v_column_mapping
  FROM public.client_data_sources
  WHERE id = v_source_id;

  IF v_column_mapping IS NULL THEN
    UPDATE analytics_v2.reg_jobs
    SET status = 'failed', error_message = 'column_mapping not found for source_id ' || v_source_id, updated_at = now()
    WHERE job_id = p_job_id;
    RETURN jsonb_build_object('error', 'column_mapping not found');
  END IF;

  -- Get latest staging batch
  SELECT id, rows, row_count INTO v_staging
  FROM public.csv_import_staging
  WHERE client_id = v_client_id AND source_id = v_source_id
  ORDER BY created_at DESC
  LIMIT 1;

  IF NOT FOUND THEN
    UPDATE analytics_v2.reg_jobs
    SET status = 'failed', error_message = 'no staging data found', updated_at = now()
    WHERE job_id = p_job_id;
    RETURN jsonb_build_object('error', 'no staging data');
  END IF;

  v_total_rows := v_staging.row_count;

  -- Process each row
  FOR v_row IN SELECT jsonb_array_elements(v_staging.rows)
  LOOP
    BEGIN
      -- Reset per-row vars
      v_data_id       := NULL;
      v_customer_id   := NULL;
      v_fornecedor_id := NULL;
      v_produto_id    := NULL;

      -- Extract fields using { canonical → source_col } mapping
      v_documento        := v_row ->> (v_column_mapping->>'documento');
      v_data_competencia := v_row ->> (v_column_mapping->>'data_competencia_id');
      v_quantidade       := NULLIF(v_row ->> (v_column_mapping->>'quantidade'), '')::NUMERIC;
      v_valor_unitario   := NULLIF(v_row ->> (v_column_mapping->>'valor_unitario'), '')::NUMERIC;
      v_valor            := NULLIF(v_row ->> (v_column_mapping->>'valor'), '')::NUMERIC;
      v_status           := NULLIF(v_row ->> (v_column_mapping->>'status'), '');
      v_tipo_lancamento  := NULLIF(v_row ->> (v_column_mapping->>'tipo_lancamento'), '');
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

      -- ── Unique transaction ID (idempotent) ──────────────────────────────────
      v_transacao_id := md5(
        v_client_id::text || ':' || v_source_id::text || ':' ||
        COALESCE(v_documento, '') || ':' ||
        COALESCE(v_data_competencia, '') || ':' ||
        COALESCE(v_produto_sku, '') || ':' ||
        v_rows_affected::text
      );

      -- ── Date parse — 4-tier fallback ────────────────────────────────────────
      -- Tier 0: strip time component — handle "DD/MM/YYYY HH24:MI:SS" and
      --         "YYYY-MM-DD HH24:MI:SS" by taking only the date portion.
      -- Tier 1: ISO cast (YYYY-MM-DD, etc.)
      -- Tier 2: DD/MM/YYYY Brazilian format
      -- Tier 3: Excel date serial (integer text, e.g. cellDates:false export)
      v_parsed_date := NULL;
      IF v_data_competencia IS NOT NULL AND v_data_competencia <> '' THEN
        -- Strip time: take chars before the first space
        v_date_str := TRIM(split_part(v_data_competencia, ' ', 1));

        -- Tier 1: ISO cast
        BEGIN
          v_parsed_date := v_date_str::DATE;
        EXCEPTION WHEN OTHERS THEN NULL; END;

        -- Tier 2: DD/MM/YYYY
        IF v_parsed_date IS NULL THEN
          BEGIN
            v_parsed_date := to_date(v_date_str, 'DD/MM/YYYY');
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        -- Tier 2b: DD/MM/YY (two-digit year)
        IF v_parsed_date IS NULL THEN
          BEGIN
            v_parsed_date := to_date(v_date_str, 'DD/MM/YY');
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        -- Tier 3: Excel serial (pure integer)
        IF v_parsed_date IS NULL AND v_date_str ~ '^\d+$' THEN
          BEGIN
            v_parsed_date := DATE '1899-12-30' + v_date_str::INTEGER;
            IF v_parsed_date < '1970-01-01' OR v_parsed_date > '2100-01-01' THEN
              v_parsed_date := NULL;
            END IF;
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        -- Lookup or insert dim_datas
        IF v_parsed_date IS NOT NULL THEN
          INSERT INTO analytics_v2.dim_datas (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
          VALUES (
            v_parsed_date,
            EXTRACT(YEAR  FROM v_parsed_date)::INTEGER,
            EXTRACT(MONTH FROM v_parsed_date)::INTEGER,
            EXTRACT(DAY   FROM v_parsed_date)::INTEGER,
            EXTRACT(ISODOW FROM v_parsed_date)::INTEGER,
            EXTRACT(WEEK  FROM v_parsed_date)::INTEGER,
            CASE WHEN EXTRACT(MONTH FROM v_parsed_date) <= 6 THEN 1 ELSE 2 END,
            'T' || EXTRACT(QUARTER FROM v_parsed_date)::TEXT
          )
          ON CONFLICT (data) DO NOTHING;

          SELECT data_id INTO v_data_id
          FROM analytics_v2.dim_datas
          WHERE data = v_parsed_date;
        END IF;
      END IF;

      -- ── dim_clientes upsert ─────────────────────────────────────────────────
      IF v_cliente_cpf_cnpj IS NOT NULL OR v_cliente_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_clientes
          (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
        VALUES
          (v_client_id, v_cliente_cpf_cnpj, v_cliente_nome,
           v_cliente_telefone, v_cliente_cidade, v_cliente_uf, now())
        ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, dim_clientes.nome),
          telefone        = COALESCE(EXCLUDED.telefone, dim_clientes.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, dim_clientes.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, dim_clientes.endereco_uf),
          atualizado_em   = now();

        SELECT customer_id INTO v_customer_id
        FROM analytics_v2.dim_clientes
        WHERE client_id = v_client_id AND cpf_cnpj = v_cliente_cpf_cnpj;
      END IF;

      -- ── dim_fornecedores upsert ─────────────────────────────────────────────
      IF v_fornecedor_cnpj IS NOT NULL OR v_fornecedor_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_fornecedores
          (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
        VALUES
          (v_client_id, v_fornecedor_cnpj, v_fornecedor_nome,
           v_fornecedor_telefone, v_fornecedor_cidade, v_fornecedor_uf, now())
        ON CONFLICT (client_id, cnpj) DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, dim_fornecedores.nome),
          telefone        = COALESCE(EXCLUDED.telefone, dim_fornecedores.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, dim_fornecedores.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, dim_fornecedores.endereco_uf),
          atualizado_em   = now();

        SELECT fornecedor_id INTO v_fornecedor_id
        FROM analytics_v2.dim_fornecedores
        WHERE client_id = v_client_id AND cnpj = v_fornecedor_cnpj;
      END IF;

      -- ── dim_inventory upsert ────────────────────────────────────────────────
      IF v_produto_sku IS NOT NULL OR v_produto_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_inventory
          (client_id, sku, nome, atualizado_em)
        VALUES
          (v_client_id, COALESCE(v_produto_sku, v_produto_nome), v_produto_nome, now())
        ON CONFLICT (client_id, sku) DO UPDATE SET
          nome          = COALESCE(EXCLUDED.nome, dim_inventory.nome),
          atualizado_em = now();

        SELECT inventory_id INTO v_produto_id
        FROM analytics_v2.dim_inventory
        WHERE client_id = v_client_id AND sku = COALESCE(v_produto_sku, v_produto_nome);
      END IF;

      -- ── fato_transacoes upsert ──────────────────────────────────────────────
      -- Inferir tipo_transacao e entry_type
      -- Prioridade: campo mapeado → heurística por valor → default 'despesa'
      DECLARE
        v_tipo_raw TEXT := NULLIF(TRIM(COALESCE(v_tipo_lancamento, '')), '');
        v_tipo     TEXT;
        v_entry    TEXT;
      BEGIN
        v_tipo := CASE
          WHEN v_tipo_raw ILIKE ANY(ARRAY['venda%','receita%','faturamento%','nf%','nota fiscal%']) THEN 'venda'
          WHEN v_tipo_raw ILIKE ANY(ARRAY['compra%','material%','mat%','insumo%','estoque%','mdo%','mão de obra%','servico%','serviço%']) THEN 'compra'
          WHEN v_tipo_raw ILIKE ANY(ARRAY['despesa%','custo%','overhead%','admin%']) THEN 'despesa'
          WHEN v_tipo_raw ILIKE ANY(ARRAY['transfer%','banco%','banc%','banking%']) THEN 'banking'
          WHEN v_tipo_raw IS NOT NULL THEN 'despesa'  -- unknown label → default despesa
          ELSE 'despesa'  -- sem mapeamento → default despesa
        END;
        v_entry := CASE v_tipo
          WHEN 'venda'   THEN 'revenue'
          WHEN 'compra'  THEN 'purchase'
          WHEN 'despesa' THEN 'expense'
          WHEN 'banking' THEN 'banking'
          ELSE 'expense'
        END;

      INSERT INTO analytics_v2.fato_transacoes (
        transacao_id, client_id, data_competencia_id, customer_id,
        fornecedor_id, produto_id, documento, quantidade,
        valor_unitario, valor, status,
        tipo_lancamento, categoria, subcategoria
      ) VALUES (
        v_transacao_id, v_client_id, v_data_id, v_customer_id,
        v_fornecedor_id, v_produto_id,
        NULLIF(v_documento, ''), v_quantidade,
        v_valor_unitario, v_valor, v_status,
        v_tipo_lancamento, v_categoria, v_subcategoria
      )
      ON CONFLICT (transacao_id, client_id) DO UPDATE SET
        data_competencia_id = EXCLUDED.data_competencia_id,
        customer_id         = EXCLUDED.customer_id,
        fornecedor_id       = EXCLUDED.fornecedor_id,
        produto_id          = EXCLUDED.produto_id,
        documento           = COALESCE(EXCLUDED.documento, fato_transacoes.documento),
        quantidade          = COALESCE(EXCLUDED.quantidade, fato_transacoes.quantidade),
        valor_unitario      = COALESCE(EXCLUDED.valor_unitario, fato_transacoes.valor_unitario),
        valor               = COALESCE(EXCLUDED.valor, fato_transacoes.valor),
        status              = COALESCE(EXCLUDED.status, fato_transacoes.status),
        tipo_lancamento     = COALESCE(EXCLUDED.tipo_lancamento, fato_transacoes.tipo_lancamento),
        categoria           = COALESCE(EXCLUDED.categoria, fato_transacoes.categoria),
        subcategoria        = COALESCE(EXCLUDED.subcategoria, fato_transacoes.subcategoria);

      v_rows_affected := v_rows_affected + 1;

      -- Progress update every 50 rows
      IF v_rows_affected % 50 = 0 THEN
        UPDATE analytics_v2.reg_jobs SET
          progress_pct = LEAST(90, 10 + (v_rows_affected * 80 / GREATEST(v_total_rows, 1))::INTEGER),
          rows_inserted = v_rows_affected,
          updated_at = now()
        WHERE job_id = p_job_id;
      END IF;

    EXCEPTION WHEN OTHERS THEN
      -- Log but continue — bad rows should not abort the entire batch
      RAISE WARNING '[sincronizar_csv_cliente] row error job=% : %', p_job_id, SQLERRM;
    END;
  END LOOP;

  -- Final update
  UPDATE analytics_v2.reg_jobs SET
    status       = 'completed',
    progress_pct = 100,
    rows_inserted = v_rows_affected,
    updated_at   = now()
  WHERE job_id = p_job_id;

  -- Enqueue dashboard refresh job (dispatcher process_pending_jobs does the refresh)
  INSERT INTO analytics_v2.reg_jobs (client_id, job_type, status, input_params, progress_pct, created_at, updated_at)
  VALUES (v_client_id, 'refresh_dashboards', 'pending', '{}'::jsonb, 0, now(), now())
  ON CONFLICT DO NOTHING;

  RETURN jsonb_build_object(
    'rows_inserted', v_rows_affected,
    'total_rows',    v_total_rows,
    'duration_ms',   EXTRACT(EPOCH FROM (now() - v_start_time)) * 1000
  );

EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_error_msg = MESSAGE_TEXT;
  UPDATE analytics_v2.reg_jobs SET
    status = 'failed', error_message = v_error_msg, updated_at = now()
  WHERE job_id = p_job_id;
  RETURN jsonb_build_object('error', v_error_msg);
END;
$$;
