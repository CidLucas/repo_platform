-- =============================================================================
-- Migration: Optimize sincronizar_dados_cliente for full async processing
-- Date: 2026-04-28
-- Purpose: Ensure processor handles full dataset without batching limits
-- =============================================================================

BEGIN;

-- Drop and recreate with full-batch optimization
DROP FUNCTION IF EXISTS public.sincronizar_dados_cliente(UUID);

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
    p_job_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_job RECORD;
    v_client_id UUID;
    v_credential_id BIGINT;
    v_start_time TIMESTAMPTZ;
    v_rows_affected BIGINT := 0;
    v_error_msg TEXT;
    v_ft_name TEXT;
    v_ft_record RECORD;
    v_column_mapping JSONB;
    v_data_source_id UUID;
    v_cliente_id BIGINT;
    v_fornecedor_id BIGINT;
    v_produto_id BIGINT;
    v_data_id BIGINT;
    v_documento TEXT;
    v_data_competencia TEXT;
    v_quantidade NUMERIC;
    v_valor_unitario NUMERIC;
    v_valor NUMERIC;
    v_status TEXT;
    v_cliente_cpf_cnpj TEXT;
    v_cliente_nome TEXT;
    v_cliente_telefone TEXT;
    v_cliente_cidade TEXT;
    v_cliente_uf TEXT;
    v_fornecedor_cnpj TEXT;
    v_fornecedor_nome TEXT;
    v_fornecedor_telefone TEXT;
    v_fornecedor_cidade TEXT;
    v_fornecedor_uf TEXT;
    v_produto_sku TEXT;
    v_produto_nome TEXT;
    v_transacao_id TEXT;
    v_query TEXT;
    v_cursor REFCURSOR;
BEGIN
    v_start_time := now();

    -- Get the job details with row lock
    SELECT
        j.job_id, j.client_id, j.credential_id, j.input_params, j.status
    INTO v_job
    FROM analytics_v2.reg_jobs j
    WHERE j.job_id = p_job_id
    FOR UPDATE;

    IF v_job IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Job not found',
            'job_id', p_job_id
        );
    END IF;

    IF v_job.status NOT IN ('pending', 'running') THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', format('Job is not in processable state (current: %s)', v_job.status),
            'job_id', p_job_id
        );
    END IF;

    v_client_id := v_job.client_id;
    v_credential_id := (v_job.input_params->>'credential_id')::BIGINT;

    -- Update job status to running
    UPDATE analytics_v2.reg_jobs
    SET
        status = 'running',
        started_at = COALESCE(started_at, now()),
        progress_pct = 10,
        updated_at = now()
    WHERE job_id = p_job_id;

    BEGIN
        -- Get the data source metadata and foreign table
        SELECT
            ds.id,
            ds.column_mapping,
            bft.foreign_table_name
        INTO
            v_data_source_id,
            v_column_mapping,
            v_ft_name
        FROM public.client_data_sources ds
        LEFT JOIN public.bigquery_foreign_tables bft
            ON bft.client_id::TEXT = ds.client_id
        WHERE ds.client_id = v_client_id::TEXT
        AND ds.credential_id = v_credential_id
        ORDER BY ds.atualizado_em DESC
        LIMIT 1;

        IF v_data_source_id IS NULL THEN
            RAISE EXCEPTION 'No data source found for this credential';
        END IF;

        IF v_ft_name IS NULL THEN
            RAISE EXCEPTION 'No foreign table found for this data source';
        END IF;

        IF v_column_mapping IS NULL OR v_column_mapping = '{}'::jsonb THEN
            RAISE EXCEPTION 'No column mapping found for this data source';
        END IF;

        -- Build dynamic query to read ALL rows from foreign table (no LIMIT)
        v_query := format('SELECT * FROM public.%I', v_ft_name);

        -- Process each row from the foreign table in one continuous loop
        OPEN v_cursor FOR EXECUTE v_query;

        LOOP
            FETCH v_cursor INTO v_ft_record;
            EXIT WHEN NOT FOUND;

            v_rows_affected := v_rows_affected + 1;

            -- Extract mapped values from the record using column mapping
            v_documento := (v_ft_record).* ->> (v_column_mapping->>'id_operatorinvoice');
            v_data_competencia := (v_ft_record).* ->> (v_column_mapping->>'createdat_operatorinvoice');
            v_quantidade := ((v_ft_record).* ->> (v_column_mapping->>'quantitytraded_product'))::NUMERIC;
            v_valor_unitario := ((v_ft_record).* ->> (v_column_mapping->>'unitprice_product'))::NUMERIC;
            v_valor := ((v_ft_record).* ->> (v_column_mapping->>'totalprice_product'))::NUMERIC;
            v_status := (v_ft_record).* ->> (v_column_mapping->>'status_operatorinvoice');

            -- Extract cliente fields
            v_cliente_cpf_cnpj := (v_ft_record).* ->> (v_column_mapping->>'receiverlegaldoc');
            v_cliente_nome := (v_ft_record).* ->> (v_column_mapping->>'receiverlegalname');
            v_cliente_telefone := (v_ft_record).* ->> (v_column_mapping->>'receiverphone');
            v_cliente_cidade := (v_ft_record).* ->> (v_column_mapping->>'receivercity');
            v_cliente_uf := (v_ft_record).* ->> (v_column_mapping->>'receiverstateuf');

            -- Extract fornecedor fields
            v_fornecedor_cnpj := (v_ft_record).* ->> (v_column_mapping->>'emitterlegaldoc');
            v_fornecedor_nome := (v_ft_record).* ->> (v_column_mapping->>'emitterlegalname');
            v_fornecedor_telefone := (v_ft_record).* ->> (v_column_mapping->>'emitterphone');
            v_fornecedor_cidade := (v_ft_record).* ->> (v_column_mapping->>'emittercity');
            v_fornecedor_uf := (v_ft_record).* ->> (v_column_mapping->>'emitterstateuf');

            -- Extract produto fields
            v_produto_sku := (v_ft_record).* ->> (v_column_mapping->>'id_product');
            v_produto_nome := (v_ft_record).* ->> (v_column_mapping->>'description_product');

            -- Generate unique transaction ID using COALESCE for null-safe MD5
            v_transacao_id := md5(
                COALESCE(v_client_id::TEXT, '') || ':' ||
                COALESCE(v_documento, '') || ':' ||
                COALESCE(v_data_competencia, '') || ':' ||
                COALESCE(v_produto_sku, '')
            );

            -- Upsert into dim_clientes
            IF v_cliente_cpf_cnpj IS NOT NULL OR v_cliente_nome IS NOT NULL THEN
                INSERT INTO analytics_v2.dim_clientes (
                    client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
                ) VALUES (
                    v_client_id, v_cliente_cpf_cnpj, v_cliente_nome, v_cliente_telefone, v_cliente_cidade, v_cliente_uf, now()
                )
                ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL
                DO UPDATE SET
                    nome = COALESCE(EXCLUDED.nome, analytics_v2.dim_clientes.nome),
                    telefone = COALESCE(EXCLUDED.telefone, analytics_v2.dim_clientes.telefone),
                    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
                    endereco_uf = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_clientes.endereco_uf),
                    atualizado_em = now();

                SELECT cliente_id INTO v_cliente_id FROM analytics_v2.dim_clientes
                WHERE client_id = v_client_id AND cpf_cnpj = v_cliente_cpf_cnpj
                LIMIT 1;
            END IF;

            -- Upsert into dim_fornecedores
            IF v_fornecedor_cnpj IS NOT NULL OR v_fornecedor_nome IS NOT NULL THEN
                INSERT INTO analytics_v2.dim_fornecedores (
                    client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
                ) VALUES (
                    v_client_id, v_fornecedor_cnpj, v_fornecedor_nome, v_fornecedor_telefone, v_fornecedor_cidade, v_fornecedor_uf, now()
                )
                ON CONFLICT (client_id, cnpj) WHERE cnpj IS NOT NULL
                DO UPDATE SET
                    nome = COALESCE(EXCLUDED.nome, analytics_v2.dim_fornecedores.nome),
                    telefone = COALESCE(EXCLUDED.telefone, analytics_v2.dim_fornecedores.telefone),
                    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
                    endereco_uf = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_fornecedores.endereco_uf),
                    atualizado_em = now();

                SELECT fornecedor_id INTO v_fornecedor_id FROM analytics_v2.dim_fornecedores
                WHERE client_id = v_client_id AND cnpj = v_fornecedor_cnpj
                LIMIT 1;
            END IF;

            -- Upsert into dim_inventory
            IF v_produto_sku IS NOT NULL OR v_produto_nome IS NOT NULL THEN
                INSERT INTO analytics_v2.dim_inventory (
                    client_id, sku, nome, updated_at
                ) VALUES (
                    v_client_id, v_produto_sku, v_produto_nome, now()
                )
                ON CONFLICT (client_id, sku) WHERE sku IS NOT NULL
                DO UPDATE SET
                    nome = COALESCE(EXCLUDED.nome, analytics_v2.dim_inventory.nome),
                    updated_at = now();

                SELECT inventory_id INTO v_produto_id FROM analytics_v2.dim_inventory
                WHERE client_id = v_client_id AND sku = v_produto_sku
                LIMIT 1;
            END IF;

            -- Get or create data dimension
            IF v_data_competencia IS NOT NULL THEN
                BEGIN
                    v_data_id := (v_data_competencia::DATE);
                    INSERT INTO analytics_v2.dim_datas (
                        data, ano, mes, dia, numero_dia_semana, numero_semana_ano
                    ) VALUES (
                        v_data_id,
                        EXTRACT(YEAR FROM v_data_id)::INTEGER,
                        EXTRACT(MONTH FROM v_data_id)::INTEGER,
                        EXTRACT(DAY FROM v_data_id)::INTEGER,
                        EXTRACT(ISODOW FROM v_data_id)::INTEGER,
                        EXTRACT(WEEK FROM v_data_id)::INTEGER
                    )
                    ON CONFLICT (data) DO NOTHING;

                    SELECT data_id INTO v_data_id FROM analytics_v2.dim_datas
                    WHERE data = v_data_id::DATE
                    LIMIT 1;
                EXCEPTION WHEN OTHERS THEN
                    v_data_id := NULL;
                END;
            END IF;

            -- Insert into fato_transacoes
            INSERT INTO analytics_v2.fato_transacoes (
                transacao_id, client_id, data_competencia_id, cliente_id, fornecedor_id, produto_id,
                documento, quantidade, valor_unitario, valor, status
            ) VALUES (
                v_transacao_id, v_client_id, v_data_id, v_cliente_id, v_fornecedor_id, v_produto_id,
                v_documento, v_quantidade, v_valor_unitario, v_valor, v_status
            )
            ON CONFLICT (transacao_id, client_id) DO UPDATE SET
                cliente_id = EXCLUDED.cliente_id,
                fornecedor_id = EXCLUDED.fornecedor_id,
                produto_id = EXCLUDED.produto_id,
                quantidade = EXCLUDED.quantidade,
                valor_unitario = EXCLUDED.valor_unitario,
                valor = EXCLUDED.valor,
                status = EXCLUDED.status;

            -- Update progress frequently for frontend polling
            IF v_rows_affected % 500 = 0 THEN
                UPDATE analytics_v2.reg_jobs
                SET
                    progress_pct = LEAST(99, 10 + (v_rows_affected::NUMERIC / 1000 * 10)::INTEGER),
                    rows_inserted = v_rows_affected,
                    updated_at = now()
                WHERE job_id = p_job_id;
            END IF;

        END LOOP;

        CLOSE v_cursor;

        -- Update job to completed
        UPDATE analytics_v2.reg_jobs
        SET
            status = 'completed',
            completed_at = now(),
            rows_inserted = v_rows_affected,
            progress_pct = 100,
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
            output = jsonb_build_object(
                'rows_inserted', v_rows_affected,
                'completed_at', now()
            ),
            updated_at = now()
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
            status = 'failed',
            completed_at = now(),
            progress_pct = 0,
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
            error_message = v_error_msg,
            updated_at = now()
        WHERE job_id = p_job_id;

        RETURN jsonb_build_object(
            'success', false,
            'job_id', p_job_id,
            'error', v_error_msg
        );
    END;

END;
$$;

COMMENT ON FUNCTION public.sincronizar_dados_cliente(UUID) IS
'Process a queued BigQuery sync job. Processes ALL rows in one continuous execution without batching limits. Called directly by async edge function.';

COMMIT;
