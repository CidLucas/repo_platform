-- Migration: add tipo_transacao + entry_type inference to sincronizar_csv_cliente
-- Mirrors the cascade logic already in apply_staging_to_facts (BigQuery pipeline):
--   1. tipo_lancamento mapeado no CSV → keyword match
--   2. fornecedor_cnpj da row == CPF/CNPJ do próprio cliente → 'venda' (ele é o emissor da NF)
--   3. cliente_cpf_cnpj da row == CPF/CNPJ do próprio cliente → 'compra' (ele é o comprador)
--   4. dim_clientes hit (v_customer_id preenchido) → 'venda'
--   5. dim_fornecedores hit (v_fornecedor_id preenchido) → 'compra'
--   6. detected_entity_context do source → fallback contextual
--   7. NULL → 'despesa' (último recurso)

CREATE OR REPLACE FUNCTION public.sincronizar_csv_cliente(p_job_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$
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
      IF v_tipo_lancamento IS NOT NULL THEN
        v_tipo_transacao := CASE
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['venda%','receita%','faturamento%','nf%','nota fiscal%','revenue%']) THEN 'venda'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['compra%','material%','mat%','insumo%','estoque%','mdo%','mão de obra%','serviço%','servico%','fornecedor%']) THEN 'compra'
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

    -- Enqueue dashboard refresh job (dispatcher process_pending_jobs does the refresh)
    INSERT INTO analytics_v2.reg_jobs (client_id, job_type, status, input_params, progress_pct, created_at, updated_at)
    VALUES (v_client_id, 'refresh_dashboards', 'pending', '{}'::jsonb, 0, now(), now())
    ON CONFLICT DO NOTHING;

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
$function$;
