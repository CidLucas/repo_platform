-- Analytics V2 Cleanup — Phase D
-- Rewrite analytics_v2.sync_invoices_client() against the slim schema:
--   fato_transacoes: 13 cols
--   dim_clientes / dim_fornecedores / dim_inventory: no drop-listed cols
--   dim_datas: 9 cols
--   dim_categoria: REMOVED (table dropped in Phase A)
-- Also patches public.sincronizar_dados_cliente to drop the 'products' route
-- (dim_categoria no longer exists) and the deprecated public.extract_bigquery_data
-- fallback column list.

BEGIN;

SET LOCAL statement_timeout = '5min';

-- ── 1. Replace sync_invoices_client ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.sync_invoices_client(
    p_client_id       uuid,
    p_credential_id   integer,
    p_force_full_sync boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
    v_cid            text := p_client_id::text;
    v_data_source    RECORD;
    v_foreign_table  text;
    v_mapping        jsonb;
    v_sync_id        bigint;
    v_job_id         uuid;
    v_start          timestamptz := now();
    v_rows_staged    bigint := 0;
    v_rows_fato      bigint := 0;
    v_staging_sql    text;
    v_select_parts   text[] := ARRAY[]::text[];
    v_canonical      text;
    v_source_col     text;
    -- Slim canonical list: only columns that remain in the minimal schema
    v_canonicals     text[] := ARRAY[
        -- fato_transacoes (13 cols minus FKs + raw emission date)
        'documento', 'quantidade', 'valor_unitario', 'valor', 'status',
        'data_competencia_id',
        -- dim_fornecedores
        'fornecedor_cnpj', 'fornecedor_nome', 'fornecedor_telefone',
        'fornecedor_cidade', 'fornecedor_uf',
        -- dim_clientes
        'cliente_cpf_cnpj', 'cliente_nome', 'cliente_telefone',
        'cliente_cidade', 'cliente_uf',
        -- dim_inventory
        'produto_id_externo', 'produto_descricao',
        -- dim_tipo_transacao
        'tipo_cfop'
    ];
BEGIN
    SET LOCAL statement_timeout = '1500000';

    RAISE LOG '[sync_invoices_client] START client=%, credential=%, force=%',
        p_client_id, p_credential_id, p_force_full_sync;

    SELECT id, storage_location, column_mapping
    INTO v_data_source
    FROM public.client_data_sources
    WHERE client_id     = p_client_id
      AND credential_id = p_credential_id
    ORDER BY atualizado_em DESC
    LIMIT 1;

    IF v_data_source IS NULL THEN
        RETURN jsonb_build_object('success', false,
            'error', 'Data source not found. Run column discovery first.');
    END IF;

    v_foreign_table := v_data_source.storage_location;
    v_mapping       := v_data_source.column_mapping;

    IF v_foreign_table IS NULL THEN
        RETURN jsonb_build_object('success', false,
            'error', 'storage_location is NULL — foreign table not created');
    END IF;
    IF v_mapping IS NULL OR v_mapping = '{}'::jsonb THEN
        RETURN jsonb_build_object('success', false,
            'error', 'column_mapping is empty — run match-columns first');
    END IF;

    SELECT job_id INTO v_job_id
    FROM analytics_v2.reg_jobs
    WHERE client_id = v_cid
      AND job_type  = 'bigquery_sync'
      AND status    = 'running'
      AND (input_params->>'credential_id')::int = p_credential_id
    ORDER BY created_at DESC
    LIMIT 1;

    INSERT INTO public.connector_sync_history (
        client_id, cliente_vizu_id, credential_id, status,
        sync_started_at, sync_mode, target_table, mapping_id
    ) VALUES (
        p_client_id, p_client_id, p_credential_id, 'running',
        v_start, 'full', 'analytics_v2.fato_transacoes', v_data_source.id
    )
    RETURNING id INTO v_sync_id;

    -- Build staging projection
    FOREACH v_canonical IN ARRAY v_canonicals LOOP
        v_source_col := analytics_v2.canonical_source_column(v_mapping, v_canonical);
        IF v_source_col IS NOT NULL THEN
            v_select_parts := array_append(v_select_parts,
                format('%I::text AS %I', v_source_col, v_canonical));
        ELSE
            v_select_parts := array_append(v_select_parts,
                format('NULL::text AS %I', v_canonical));
        END IF;
    END LOOP;

    EXECUTE 'DROP TABLE IF EXISTS tmp_invoice_staging';
    v_staging_sql := format(
        'CREATE TEMP TABLE tmp_invoice_staging ON COMMIT DROP AS SELECT %s FROM %s',
        array_to_string(v_select_parts, ', '), v_foreign_table);
    RAISE LOG '[sync_invoices_client] staging sql: %', v_staging_sql;
    EXECUTE v_staging_sql;

    GET DIAGNOSTICS v_rows_staged = ROW_COUNT;
    RAISE LOG '[sync_invoices_client] staged % rows', v_rows_staged;

    IF v_job_id IS NOT NULL THEN
        UPDATE analytics_v2.reg_jobs
        SET progress_pct = 30, updated_at = now()
        WHERE job_id = v_job_id;
    END IF;

    -- Clear existing fato rows for this client (full resync)
    DELETE FROM analytics_v2.fato_transacoes WHERE client_id = v_cid;

    -- ── dim_fornecedores ────────────────────────────────────────────────
    INSERT INTO analytics_v2.dim_fornecedores AS f (
        client_id, cnpj, nome, telefone,
        endereco_cidade, endereco_uf, atualizado_em
    )
    SELECT DISTINCT ON (fornecedor_cnpj)
        v_cid,
        fornecedor_cnpj,
        COALESCE(NULLIF(fornecedor_nome, ''), 'SEM_NOME'),
        NULLIF(fornecedor_telefone, ''),
        NULLIF(fornecedor_cidade, ''),
        NULLIF(fornecedor_uf, ''),
        now()
    FROM tmp_invoice_staging
    WHERE NULLIF(fornecedor_cnpj, '') IS NOT NULL
    ON CONFLICT (client_id, cnpj) DO UPDATE SET
        nome            = COALESCE(NULLIF(EXCLUDED.nome, 'SEM_NOME'), f.nome),
        telefone        = COALESCE(EXCLUDED.telefone, f.telefone),
        endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, f.endereco_cidade),
        endereco_uf     = COALESCE(EXCLUDED.endereco_uf, f.endereco_uf),
        atualizado_em   = now();

    -- ── dim_clientes ────────────────────────────────────────────────────
    INSERT INTO analytics_v2.dim_clientes AS c (
        client_id, cpf_cnpj, nome, telefone,
        endereco_cidade, endereco_uf, atualizado_em
    )
    SELECT DISTINCT ON (cliente_cpf_cnpj)
        v_cid,
        cliente_cpf_cnpj,
        COALESCE(NULLIF(cliente_nome, ''), 'SEM_NOME'),
        NULLIF(cliente_telefone, ''),
        NULLIF(cliente_cidade, ''),
        NULLIF(cliente_uf, ''),
        now()
    FROM tmp_invoice_staging
    WHERE NULLIF(cliente_cpf_cnpj, '') IS NOT NULL
    ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
        nome            = COALESCE(NULLIF(EXCLUDED.nome, 'SEM_NOME'), c.nome),
        telefone        = COALESCE(EXCLUDED.telefone, c.telefone),
        endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, c.endereco_cidade),
        endereco_uf     = COALESCE(EXCLUDED.endereco_uf, c.endereco_uf),
        atualizado_em   = now();

    -- ── dim_inventory ───────────────────────────────────────────────────
    INSERT INTO analytics_v2.dim_inventory AS inv (
        client_id, nome, sku, created_at, updated_at
    )
    SELECT DISTINCT ON (COALESCE(NULLIF(produto_descricao, ''), produto_id_externo))
        v_cid,
        COALESCE(NULLIF(produto_descricao, ''), produto_id_externo),
        produto_id_externo,
        now(), now()
    FROM tmp_invoice_staging
    WHERE COALESCE(NULLIF(produto_descricao, ''), NULLIF(produto_id_externo, '')) IS NOT NULL
    ON CONFLICT (client_id, nome) DO UPDATE SET
        sku        = COALESCE(EXCLUDED.sku, inv.sku),
        updated_at = now();

    -- ── dim_tipo_transacao ──────────────────────────────────────────────
    INSERT INTO analytics_v2.dim_tipo_transacao (codigo, descricao, categoria)
    SELECT DISTINCT NULLIF(tipo_cfop, ''), 'CFOP ' || tipo_cfop, 'fiscal'
    FROM tmp_invoice_staging
    WHERE NULLIF(tipo_cfop, '') IS NOT NULL
    ON CONFLICT (codigo) DO NOTHING;

    -- ── dim_datas (9-col slim schema) ───────────────────────────────────
    INSERT INTO analytics_v2.dim_datas (
        data_id, data, ano, trimestre, mes, nome_mes,
        dia, semana_do_ano, dia_da_semana
    )
    SELECT
        to_char(d, 'YYYYMMDD')::int,
        d,
        EXTRACT(YEAR    FROM d)::int,
        EXTRACT(QUARTER FROM d)::int,
        EXTRACT(MONTH   FROM d)::int,
        TO_CHAR(d, 'TMMonth'),
        EXTRACT(DAY     FROM d)::int,
        EXTRACT(WEEK    FROM d)::int,
        EXTRACT(DOW     FROM d)::int
    FROM (
        SELECT DISTINCT (NULLIF(data_competencia_id, '')::timestamptz)::date AS d
        FROM tmp_invoice_staging
        WHERE NULLIF(data_competencia_id, '') IS NOT NULL
    ) s
    WHERE d IS NOT NULL
    ON CONFLICT (data_id) DO NOTHING;

    IF v_job_id IS NOT NULL THEN
        UPDATE analytics_v2.reg_jobs
        SET progress_pct = 60, updated_at = now()
        WHERE job_id = v_job_id;
    END IF;

    -- ── fato_transacoes (13-col slim schema) ────────────────────────────
    INSERT INTO analytics_v2.fato_transacoes (
        client_id, tipo_id, data_competencia_id,
        cliente_id, fornecedor_id, produto_id,
        documento, quantidade, valor_unitario, valor, status
    )
    SELECT
        v_cid,
        COALESCE(tt.tipo_id, 0),
        to_char(
            COALESCE(NULLIF(s.data_competencia_id, '')::timestamptz, now()),
            'YYYYMMDD'
        )::int,
        cli.cliente_id,
        forn.fornecedor_id,
        inv.inventory_id,
        s.documento,
        NULLIF(s.quantidade, '')::numeric,
        NULLIF(s.valor_unitario, '')::numeric,
        COALESCE(NULLIF(s.valor, '')::numeric, 0),
        s.status
    FROM tmp_invoice_staging s
    LEFT JOIN analytics_v2.dim_fornecedores forn
        ON forn.client_id = v_cid
        AND forn.cnpj = NULLIF(s.fornecedor_cnpj, '')
    LEFT JOIN analytics_v2.dim_clientes cli
        ON cli.client_id = v_cid
        AND cli.cpf_cnpj = NULLIF(s.cliente_cpf_cnpj, '')
    LEFT JOIN analytics_v2.dim_inventory inv
        ON inv.client_id = v_cid
        AND inv.nome = COALESCE(NULLIF(s.produto_descricao, ''), NULLIF(s.produto_id_externo, ''))
    LEFT JOIN analytics_v2.dim_tipo_transacao tt
        ON tt.codigo = NULLIF(s.tipo_cfop, '');

    GET DIAGNOSTICS v_rows_fato = ROW_COUNT;

    IF v_job_id IS NOT NULL THEN
        UPDATE analytics_v2.reg_jobs
        SET progress_pct = 85, updated_at = now()
        WHERE job_id = v_job_id;
    END IF;

    BEGIN
        PERFORM analytics_v2.atualizar_agregados(v_cid);
    EXCEPTION WHEN OTHERS THEN
        RAISE LOG '[sync_invoices_client] aggregate refresh failed: %', SQLERRM;
    END;

    UPDATE public.connector_sync_history
    SET status            = 'completed',
        sync_completed_at = now(),
        records_inserted  = v_rows_fato,
        records_processed = v_rows_staged,
        progress_percent  = 100
    WHERE id = v_sync_id;

    UPDATE public.client_data_sources
    SET last_synced_at = now(), sync_status = 'completed'
    WHERE id = v_data_source.id;

    RAISE LOG '[sync_invoices_client] DONE rows_staged=%, rows_fato=%, duration=%s',
        v_rows_staged, v_rows_fato,
        EXTRACT(EPOCH FROM (now() - v_start))::int;

    RETURN jsonb_build_object(
        'success',          true,
        'sync_id',          v_sync_id,
        'rows_staged',      v_rows_staged,
        'rows_inserted',    v_rows_fato,
        'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start))::int
    );

EXCEPTION WHEN OTHERS THEN
    RAISE LOG '[sync_invoices_client] EXCEPTION: % (SQLSTATE=%)', SQLERRM, SQLSTATE;

    IF v_sync_id IS NOT NULL AND v_sync_id > 0 THEN
        UPDATE public.connector_sync_history
        SET status            = 'failed',
            sync_completed_at = now(),
            error_message     = SQLERRM,
            error_details     = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
        WHERE id = v_sync_id;
    END IF;

    RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'sync_id', v_sync_id);
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.sync_invoices_client(uuid, integer, boolean)
    TO authenticated, service_role, postgres;

-- ── 2. Patch dispatcher: drop 'products' route (dim_categoria gone) ─────────
CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
    p_client_id       uuid,
    p_credential_id   integer,
    p_force_full_sync boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
    v_resource_type text;
    v_data_source_id uuid;
BEGIN
    SET LOCAL statement_timeout = '1500000';

    SELECT id, resource_type
    INTO v_data_source_id, v_resource_type
    FROM public.client_data_sources
    WHERE client_id     = p_client_id
      AND credential_id = p_credential_id
    ORDER BY atualizado_em DESC
    LIMIT 1;

    IF v_data_source_id IS NULL THEN
        RETURN jsonb_build_object('success', false,
            'error', 'Data source not found. Run column discovery first.');
    END IF;

    -- Only 'invoices' is supported end-to-end. Other resource types are
    -- currently unused after the Apr 2026 slim (dim_categoria was dropped,
    -- single-table customer/supplier/inventory sync not in production).
    IF COALESCE(v_resource_type, 'invoices') = 'invoices' THEN
        RETURN analytics_v2.sync_invoices_client(
            p_client_id, p_credential_id, p_force_full_sync
        );
    END IF;

    RETURN jsonb_build_object('success', false,
        'error', format('resource_type %L is no longer supported by the slim pipeline', v_resource_type));
END;
$$;

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean)
    TO authenticated, service_role, postgres;

-- ── 3. Drop the obsolete generic extractor ──────────────────────────────────
DROP FUNCTION IF EXISTS public.extract_bigquery_data(text, text, jsonb, text, text, integer);

COMMIT;
