-- =============================================================================
-- Migration: fix sincronizar_csv_cliente to write tipo_lancamento/categoria/subcategoria
-- Date: 2026-05-18
-- Purpose: Columns already exist (added by add_custo_fields_to_fato_transacoes).
--          The ETL function was never updated to declare, extract, or write them.
--          This migration adds the three missing pieces to sincronizar_csv_cliente.
-- Applied directly via MCP as: fix_sincronizar_csv_write_cost_fields
-- =============================================================================

-- ── Update ETL function ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.sincronizar_csv_cliente(p_job_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
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

  -- Extracted field variables (canonical names from match-columns schema)
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
BEGIN
  -- Fetch and lock job
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

  -- Mark running
  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = now(), progress_pct = 5, updated_at = now()
  WHERE job_id = p_job_id;

  BEGIN
    -- Fetch column_mapping from data source
    -- Format: { "canonical_field": "source_column_name" }
    -- e.g. { "documento": "invoice_id", "valor": "amount", "tipo_lancamento": "MAT ou MDO" }
    SELECT column_mapping INTO v_column_mapping
    FROM public.client_data_sources
    WHERE id = v_source_id AND client_id = v_client_id;

    IF v_column_mapping IS NULL OR v_column_mapping = '{}'::jsonb THEN
      RAISE EXCEPTION 'No column_mapping found for source %', v_source_id;
    END IF;

    -- Fetch most recent staging batch for this source
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

    -- Iterate rows
    FOR i IN 0 .. v_total_rows - 1 LOOP
      v_row := v_staging.rows->i;
      v_rows_affected := v_rows_affected + 1;

      -- Reset dim FKs per row
      v_customer_id   := NULL;
      v_fornecedor_id := NULL;
      v_produto_id    := NULL;
      v_data_id       := NULL;

      -- Extract values: v_row ->> (v_column_mapping->>'canonical') resolves
      -- the source column name from the mapping, then reads that key from the row.
      v_documento        := v_row ->> (v_column_mapping->>'documento');
      v_data_competencia := v_row ->> (v_column_mapping->>'data_competencia_id');
      v_quantidade       := NULLIF(v_row ->> (v_column_mapping->>'quantidade'), '')::NUMERIC;
      v_valor_unitario   := NULLIF(v_row ->> (v_column_mapping->>'valor_unitario'), '')::NUMERIC;
      v_valor            := NULLIF(v_row ->> (v_column_mapping->>'valor'), '')::NUMERIC;
      v_status           := v_row ->> (v_column_mapping->>'status');
      v_tipo_lancamento  := v_row ->> (v_column_mapping->>'tipo_lancamento');
      v_categoria        := v_row ->> (v_column_mapping->>'categoria');
      v_subcategoria     := v_row ->> (v_column_mapping->>'subcategoria');

      v_cliente_cpf_cnpj := v_row ->> (v_column_mapping->>'cliente_cpf_cnpj');
      v_cliente_nome     := v_row ->> (v_column_mapping->>'cliente_nome');
      v_cliente_telefone := v_row ->> (v_column_mapping->>'cliente_telefone');
      v_cliente_cidade   := v_row ->> (v_column_mapping->>'cliente_cidade');
      v_cliente_uf       := v_row ->> (v_column_mapping->>'cliente_uf');

      v_fornecedor_cnpj    := v_row ->> (v_column_mapping->>'fornecedor_cnpj');
      v_fornecedor_nome    := v_row ->> (v_column_mapping->>'fornecedor_nome');
      v_fornecedor_telefone := v_row ->> (v_column_mapping->>'fornecedor_telefone');
      v_fornecedor_cidade  := v_row ->> (v_column_mapping->>'fornecedor_cidade');
      v_fornecedor_uf      := v_row ->> (v_column_mapping->>'fornecedor_uf');

      v_produto_sku  := v_row ->> (v_column_mapping->>'produto_sku');
      v_produto_nome := v_row ->> (v_column_mapping->>'produto_nome');

      -- Stable transaction ID: same row re-uploaded won't create duplicates
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
        WHERE client_id = v_client_id AND cpf_cnpj = v_cliente_cpf_cnpj
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
        WHERE client_id = v_client_id AND cnpj = v_fornecedor_cnpj
        LIMIT 1;

        -- Fall back to name-based lookup when cnpj is absent
        IF v_fornecedor_id IS NULL AND v_fornecedor_nome IS NOT NULL THEN
          SELECT fornecedor_id INTO v_fornecedor_id
          FROM analytics_v2.dim_fornecedores
          WHERE client_id = v_client_id AND nome = v_fornecedor_nome
          LIMIT 1;
        END IF;
      END IF;

      -- Upsert dim_inventory
      IF v_produto_sku IS NOT NULL OR v_produto_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_inventory (
          client_id, sku, nome, updated_at
        ) VALUES (
          v_client_id, v_produto_sku, v_produto_nome, now()
        )
        ON CONFLICT (client_id, sku) WHERE sku IS NOT NULL
        DO UPDATE SET
          nome       = COALESCE(EXCLUDED.nome, analytics_v2.dim_inventory.nome),
          updated_at = now();

        SELECT inventory_id INTO v_produto_id
        FROM analytics_v2.dim_inventory
        WHERE client_id = v_client_id AND sku = v_produto_sku
        LIMIT 1;
      END IF;

      -- Upsert dim_datas
      IF v_data_competencia IS NOT NULL AND v_data_competencia <> '' THEN
        BEGIN
          INSERT INTO analytics_v2.dim_datas (
            data, ano, mes, dia, numero_dia_semana, numero_semana_ano
          ) VALUES (
            v_data_competencia::DATE,
            EXTRACT(YEAR  FROM v_data_competencia::DATE)::INTEGER,
            EXTRACT(MONTH FROM v_data_competencia::DATE)::INTEGER,
            EXTRACT(DAY   FROM v_data_competencia::DATE)::INTEGER,
            EXTRACT(ISODOW FROM v_data_competencia::DATE)::INTEGER,
            EXTRACT(WEEK  FROM v_data_competencia::DATE)::INTEGER
          )
          ON CONFLICT (data) DO NOTHING;

          SELECT data_id INTO v_data_id
          FROM analytics_v2.dim_datas
          WHERE data = v_data_competencia::DATE
          LIMIT 1;
        EXCEPTION WHEN OTHERS THEN
          v_data_id := NULL; -- unparseable date: skip dim_datas, still write fato
        END;
      END IF;

      -- Insert/upsert fato_transacoes
      INSERT INTO analytics_v2.fato_transacoes (
        transacao_id, client_id, data_competencia_id, customer_id,
        fornecedor_id, produto_id, documento, quantidade,
        valor_unitario, valor, status,
        tipo_lancamento, categoria, subcategoria
      ) VALUES (
        v_transacao_id, v_client_id, v_data_id, v_customer_id,
        v_fornecedor_id, v_produto_id, v_documento, v_quantidade,
        v_valor_unitario, v_valor, v_status,
        v_tipo_lancamento, v_categoria, v_subcategoria
      )
      ON CONFLICT (transacao_id, client_id) DO UPDATE SET
        customer_id      = EXCLUDED.customer_id,
        fornecedor_id    = EXCLUDED.fornecedor_id,
        produto_id       = EXCLUDED.produto_id,
        quantidade       = EXCLUDED.quantidade,
        valor_unitario   = EXCLUDED.valor_unitario,
        valor            = EXCLUDED.valor,
        status           = EXCLUDED.status,
        tipo_lancamento  = EXCLUDED.tipo_lancamento,
        categoria        = EXCLUDED.categoria,
        subcategoria     = EXCLUDED.subcategoria;

      -- Progress every 100 rows
      IF v_rows_affected % 100 = 0 THEN
        UPDATE analytics_v2.reg_jobs
        SET
          progress_pct = LEAST(90, 10 + (v_rows_affected * 80 / GREATEST(v_total_rows, 1))::INTEGER),
          updated_at   = now()
        WHERE job_id = p_job_id;
      END IF;

    END LOOP;

    -- Cleanup staging rows
    DELETE FROM public.csv_import_staging WHERE id = v_staging.id;

    -- Mark data source as synced
    UPDATE public.client_data_sources
    SET sync_status = 'completed', last_synced_at = now(), updated_at = now()
    WHERE id = v_source_id;

    -- Complete job
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
$$;

