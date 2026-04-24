-- =============================================================================
-- Migration: Multi-table ETL for `invoices` resource type
-- Date: 2026-04-22
--
-- Problem:
--   sincronizar_dados_cliente() + extract_bigquery_data() only INSERT into
--   fato_transacoes. Canonical targets belonging to dim_* tables
--   (fornecedor_nome, cliente_cpf_cnpj, produto_descricao, ...) were silently
--   dropped because v_target_exists=false. As a result fato rows were saved
--   with every dimension FK (cliente_id/fornecedor_id/produto_id/categoria_id)
--   as NULL and dim_* tables stayed empty.
--
--   Additionally, data_competencia_id (INT YYYYMMDD) was mapped from the
--   emittedat_operatorinvoice timestamp text, which cannot be cast directly
--   to int4/numeric. The safety-net fallback kicked in and every row got
--   data_competencia_id = CURRENT_DATE.
--
-- Fix:
--   Introduce analytics_v2.sync_invoices_client(): a deterministic multi-table
--   ETL that consumes the flat column_mapping and:
--     1. Materialises a TEMP staging table from the foreign table, projecting
--        every known canonical column (absent ones materialise as NULL).
--     2. Upserts dim_fornecedores, dim_clientes, dim_categoria, dim_inventory,
--        dim_tipo_transacao from DISTINCT rows in staging using business keys.
--     3. Pre-creates missing dim_datas rows for every emission timestamp.
--     4. INSERTs fato_transacoes joining staging to dims to resolve every FK
--        and converts the timestamp text to a YYYYMMDD integer.
--
--   The legacy generic extract_bigquery_data() is kept for non-invoice
--   resource types (it already handles simple single-table inserts).
--
-- Scope:
--   Only the `invoices` resource_type is routed to the new pipeline. Other
--   resource types (customers/suppliers/products/inventory/sales) continue to
--   use the existing single-table extract path — they are each a single dim
--   sync and the generic code is sufficient.
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- Helper: find the source column for a canonical target inside column_mapping.
-- column_mapping is { "<source_column>": "<canonical_target>" } so we need an
-- inverse lookup. Returns NULL when the canonical is not mapped.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.canonical_source_column(
	p_mapping  jsonb,
	p_canonical text
) RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
	SELECT key
	FROM jsonb_each_text(coalesce(p_mapping, '{}'::jsonb))
	WHERE value = p_canonical
	LIMIT 1;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.canonical_source_column(jsonb, text)
	TO authenticated, service_role, postgres;


-- ─────────────────────────────────────────────────────────────────────────────
-- Main entry point: sync_invoices_client()
-- ─────────────────────────────────────────────────────────────────────────────
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
	v_canonicals     text[] := ARRAY[
		-- ── fato_transacoes fields ──
		'documento',               'nf_numero',             'quantidade',
		'quantidade_kg',           'valor_unitario',        'valor_unitario_kg',
		'valor',                   'valor_nf',              'status',
		'movement_type',           'danfe',                 'data_criacao_origem',
		'is_blocked',              'volume',                'volume_validado',
		'valor_validado',          'id_credito',            'data_credito',
		'status_produto',          'data_criacao_produto',  'was_purchased',
		'was_compensation',        'compensations_ids',     'purchase_order_ids',
		'purchase_order_codes',    'in_offer',              'has_credit',
		'product_invalidations',   'cpl_adicional',         'fisco_adicional',
		'danfe_materials',         'filial_id',             'filial_cnpj',
		-- Raw emission timestamp (text) converted to data_competencia_id downstream
		'data_competencia_id',
		-- ── dim_fornecedores fields ──
		'fornecedor_cnpj',         'fornecedor_nome',       'fornecedor_nome_fantasia',
		'fornecedor_telefone',     'fornecedor_cnae',       'fornecedor_rua',
		'fornecedor_numero',       'fornecedor_bairro',     'fornecedor_cidade',
		'fornecedor_uf',           'fornecedor_cep',        'fornecedor_company_id',
		-- ── dim_clientes fields ──
		'cliente_cpf_cnpj',        'cliente_nome',          'cliente_nome_fantasia',
		'cliente_telefone',        'cliente_cnae',          'cliente_rua',
		'cliente_numero',          'cliente_bairro',        'cliente_cidade',
		'cliente_uf',              'cliente_cep',
		-- ── dim_inventory fields ──
		'produto_id_externo',      'produto_descricao',     'produto_ncm',
		'produto_unidade',
		-- ── dim_categoria field ──
		'categoria_material',
		-- ── dim_tipo_transacao field ──
		'tipo_cfop'
	];
BEGIN
	-- Safety net: 25 minutes. pg_cron has no wall-clock limit so we still
	-- cap individual statements.
	SET LOCAL statement_timeout = '1500000';

	RAISE LOG '[sync_invoices_client] START client=%, credential=%, force=%',
		p_client_id, p_credential_id, p_force_full_sync;

	-- ── Locate data source ────────────────────────────────────────────────
	SELECT id, storage_location, column_mapping
	INTO v_data_source
	FROM public.client_data_sources
	WHERE client_id     = p_client_id
	  AND credential_id = p_credential_id
	ORDER BY atualizado_em DESC
	LIMIT 1;

	IF v_data_source IS NULL THEN
		RETURN jsonb_build_object(
			'success', false,
			'error',   'Data source not found. Run column discovery first.'
		);
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

	-- ── Locate the running reg_jobs row for progress reporting ───────────
	SELECT job_id INTO v_job_id
	FROM analytics_v2.reg_jobs
	WHERE client_id = v_cid
	  AND job_type  = 'bigquery_sync'
	  AND status    = 'running'
	  AND (input_params->>'credential_id')::int = p_credential_id
	ORDER BY created_at DESC
	LIMIT 1;

	-- ── connector_sync_history header row ────────────────────────────────
	INSERT INTO public.connector_sync_history (
		client_id, cliente_vizu_id, credential_id, status,
		sync_started_at, sync_mode, target_table, mapping_id
	) VALUES (
		p_client_id, p_client_id, p_credential_id, 'running',
		v_start, 'full',
		'analytics_v2.fato_transacoes',
		v_data_source.id
	)
	RETURNING id INTO v_sync_id;

	-- ── Build the staging projection: one column per known canonical ─────
	-- Mapped canonicals → `<source>::text AS <canonical>`
	-- Unmapped canonicals → `NULL::text AS <canonical>`
	FOREACH v_canonical IN ARRAY v_canonicals LOOP
		v_source_col := analytics_v2.canonical_source_column(v_mapping, v_canonical);
		IF v_source_col IS NOT NULL THEN
			v_select_parts := array_append(
				v_select_parts,
				format('%I::text AS %I', v_source_col, v_canonical)
			);
		ELSE
			v_select_parts := array_append(
				v_select_parts,
				format('NULL::text AS %I', v_canonical)
			);
		END IF;
	END LOOP;

	-- ── Materialise staging ──────────────────────────────────────────────
	-- We use a TEMP TABLE so every downstream dim insert sees the same shape.
	EXECUTE 'DROP TABLE IF EXISTS tmp_invoice_staging';
	v_staging_sql := format(
		'CREATE TEMP TABLE tmp_invoice_staging ON COMMIT DROP AS SELECT %s FROM %s',
		array_to_string(v_select_parts, ', '),
		v_foreign_table
	);
	RAISE LOG '[sync_invoices_client] staging sql: %', v_staging_sql;
	EXECUTE v_staging_sql;

	GET DIAGNOSTICS v_rows_staged = ROW_COUNT;
	RAISE LOG '[sync_invoices_client] staged % rows', v_rows_staged;

	IF v_job_id IS NOT NULL THEN
		UPDATE analytics_v2.reg_jobs
		SET progress_pct = 30, updated_at = now()
		WHERE job_id = v_job_id;
	END IF;

	-- ── Full-sync: clear existing fato rows for this client ─────────────
	-- dim rows are upserted so they do not need clearing.
	DELETE FROM analytics_v2.fato_transacoes WHERE client_id = v_cid;

	-- ── dim_fornecedores ─────────────────────────────────────────────────
	INSERT INTO analytics_v2.dim_fornecedores AS f (
		client_id, cnpj, nome, nome_fantasia, telefone, cnae,
		endereco_rua, endereco_numero, endereco_bairro,
		endereco_cidade, endereco_uf, endereco_cep, company_id,
		criado_em, atualizado_em
	)
	SELECT DISTINCT ON (fornecedor_cnpj)
		v_cid,
		fornecedor_cnpj,
		COALESCE(NULLIF(fornecedor_nome, ''), 'SEM_NOME'),
		NULLIF(fornecedor_nome_fantasia, ''),
		NULLIF(fornecedor_telefone, ''),
		NULLIF(fornecedor_cnae, ''),
		NULLIF(fornecedor_rua, ''),
		NULLIF(fornecedor_numero, ''),
		NULLIF(fornecedor_bairro, ''),
		NULLIF(fornecedor_cidade, ''),
		NULLIF(fornecedor_uf, ''),
		NULLIF(fornecedor_cep, ''),
		NULLIF(fornecedor_company_id, ''),
		now(), now()
	FROM tmp_invoice_staging
	WHERE NULLIF(fornecedor_cnpj, '') IS NOT NULL
	ON CONFLICT (client_id, cnpj) DO UPDATE SET
		nome                = COALESCE(NULLIF(EXCLUDED.nome, 'SEM_NOME'), f.nome),
		nome_fantasia       = COALESCE(EXCLUDED.nome_fantasia, f.nome_fantasia),
		telefone            = COALESCE(EXCLUDED.telefone, f.telefone),
		cnae                = COALESCE(EXCLUDED.cnae, f.cnae),
		endereco_rua        = COALESCE(EXCLUDED.endereco_rua, f.endereco_rua),
		endereco_numero     = COALESCE(EXCLUDED.endereco_numero, f.endereco_numero),
		endereco_bairro     = COALESCE(EXCLUDED.endereco_bairro, f.endereco_bairro),
		endereco_cidade     = COALESCE(EXCLUDED.endereco_cidade, f.endereco_cidade),
		endereco_uf         = COALESCE(EXCLUDED.endereco_uf, f.endereco_uf),
		endereco_cep        = COALESCE(EXCLUDED.endereco_cep, f.endereco_cep),
		company_id          = COALESCE(EXCLUDED.company_id, f.company_id),
		atualizado_em       = now();

	-- ── dim_clientes ─────────────────────────────────────────────────────
	INSERT INTO analytics_v2.dim_clientes AS c (
		client_id, cpf_cnpj, nome, nome_fantasia, telefone, cnae,
		endereco_rua, endereco_numero, endereco_bairro,
		endereco_cidade, endereco_uf, endereco_cep,
		criado_em, atualizado_em
	)
	SELECT DISTINCT ON (cliente_cpf_cnpj)
		v_cid,
		cliente_cpf_cnpj,
		COALESCE(NULLIF(cliente_nome, ''), 'SEM_NOME'),
		NULLIF(cliente_nome_fantasia, ''),
		NULLIF(cliente_telefone, ''),
		NULLIF(cliente_cnae, ''),
		NULLIF(cliente_rua, ''),
		NULLIF(cliente_numero, ''),
		NULLIF(cliente_bairro, ''),
		NULLIF(cliente_cidade, ''),
		NULLIF(cliente_uf, ''),
		NULLIF(cliente_cep, ''),
		now(), now()
	FROM tmp_invoice_staging
	WHERE NULLIF(cliente_cpf_cnpj, '') IS NOT NULL
	ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
		nome               = COALESCE(NULLIF(EXCLUDED.nome, 'SEM_NOME'), c.nome),
		nome_fantasia      = COALESCE(EXCLUDED.nome_fantasia, c.nome_fantasia),
		telefone           = COALESCE(EXCLUDED.telefone, c.telefone),
		cnae               = COALESCE(EXCLUDED.cnae, c.cnae),
		endereco_rua       = COALESCE(EXCLUDED.endereco_rua, c.endereco_rua),
		endereco_numero    = COALESCE(EXCLUDED.endereco_numero, c.endereco_numero),
		endereco_bairro    = COALESCE(EXCLUDED.endereco_bairro, c.endereco_bairro),
		endereco_cidade    = COALESCE(EXCLUDED.endereco_cidade, c.endereco_cidade),
		endereco_uf        = COALESCE(EXCLUDED.endereco_uf, c.endereco_uf),
		endereco_cep       = COALESCE(EXCLUDED.endereco_cep, c.endereco_cep),
		atualizado_em      = now();

	-- ── dim_categoria ────────────────────────────────────────────────────
	-- Unique key: (client_id, nome). Default tipo='material' so tests can filter.
	INSERT INTO analytics_v2.dim_categoria (client_id, nome, tipo, created_at)
	SELECT DISTINCT v_cid, NULLIF(categoria_material, ''), 'material', now()
	FROM tmp_invoice_staging
	WHERE NULLIF(categoria_material, '') IS NOT NULL
	ON CONFLICT (client_id, nome) DO NOTHING;

	-- ── dim_inventory ────────────────────────────────────────────────────
	-- Unique key: (client_id, nome). Use produto_descricao as nome and fall
	-- back to produto_id_externo when description is missing.
	INSERT INTO analytics_v2.dim_inventory AS inv (
		client_id, nome, sku, external_id, ncm, unidade_comercial,
		inventory_type, created_at, updated_at
	)
	SELECT DISTINCT ON (COALESCE(NULLIF(produto_descricao, ''), produto_id_externo))
		v_cid,
		COALESCE(NULLIF(produto_descricao, ''), produto_id_externo),
		produto_id_externo,
		produto_id_externo,
		NULLIF(produto_ncm, ''),
		NULLIF(produto_unidade, ''),
		'product',
		now(), now()
	FROM tmp_invoice_staging
	WHERE COALESCE(NULLIF(produto_descricao, ''), NULLIF(produto_id_externo, '')) IS NOT NULL
	ON CONFLICT (client_id, nome) DO UPDATE SET
		sku               = COALESCE(EXCLUDED.sku, inv.sku),
		external_id       = COALESCE(EXCLUDED.external_id, inv.external_id),
		ncm               = COALESCE(EXCLUDED.ncm, inv.ncm),
		unidade_comercial = COALESCE(EXCLUDED.unidade_comercial, inv.unidade_comercial),
		updated_at        = now();

	-- ── dim_tipo_transacao ───────────────────────────────────────────────
	-- Unique key: codigo (global).
	INSERT INTO analytics_v2.dim_tipo_transacao (codigo, descricao, categoria)
	SELECT DISTINCT NULLIF(tipo_cfop, ''), 'CFOP ' || tipo_cfop, 'fiscal'
	FROM tmp_invoice_staging
	WHERE NULLIF(tipo_cfop, '') IS NOT NULL
	ON CONFLICT (codigo) DO NOTHING;

	-- ── dim_datas: ensure every emission date has a row ──────────────────
	INSERT INTO analytics_v2.dim_datas (
		data_id, data, ano, ano_iso, trimestre, nome_trimestre,
		mes, nome_mes, dia, dia_do_ano, semana_do_ano,
		dia_da_semana, nome_dia, e_fim_de_semana,
		primeiro_dia_mes, ultimo_dia_mes,
		e_inicio_mes, e_fim_mes,
		e_inicio_trimestre, e_fim_trimestre,
		e_inicio_ano, e_fim_ano
	)
	SELECT
		to_char(d, 'YYYYMMDD')::int,
		d,
		EXTRACT(YEAR    FROM d)::int,
		EXTRACT(ISOYEAR FROM d)::int,
		EXTRACT(QUARTER FROM d)::int,
		'Q' || EXTRACT(QUARTER FROM d)::text,
		EXTRACT(MONTH FROM d)::int,
		TO_CHAR(d, 'TMMonth'),
		EXTRACT(DAY   FROM d)::int,
		EXTRACT(DOY   FROM d)::int,
		EXTRACT(WEEK  FROM d)::int,
		EXTRACT(DOW   FROM d)::int,
		TO_CHAR(d, 'TMDay'),
		EXTRACT(DOW FROM d) IN (0, 6),
		date_trunc('month', d)::date,
		(date_trunc('month', d) + interval '1 month - 1 day')::date,
		d = date_trunc('month', d)::date,
		d = (date_trunc('month', d) + interval '1 month - 1 day')::date,
		d = date_trunc('quarter', d)::date,
		d = (date_trunc('quarter', d) + interval '3 month - 1 day')::date,
		d = date_trunc('year', d)::date,
		d = (date_trunc('year', d) + interval '1 year - 1 day')::date
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

	-- ── fato_transacoes: insert with FK resolution ───────────────────────
	INSERT INTO analytics_v2.fato_transacoes (
		client_id,
		tipo_id,
		data_competencia_id,
		categoria_id,
		cliente_id,
		fornecedor_id,
		produto_id,
		inventory_id,
		documento,
		nf_numero,
		quantidade,
		quantidade_kg,
		valor_unitario,
		valor_unitario_kg,
		valor,
		valor_nf,
		status,
		movement_type,
		danfe,
		data_criacao_origem,
		is_blocked,
		volume,
		volume_validado,
		valor_validado,
		id_credito,
		data_credito,
		status_produto,
		data_criacao_produto,
		was_purchased,
		was_compensation,
		compensations_ids,
		purchase_order_ids,
		purchase_order_codes,
		in_offer,
		has_credit,
		product_invalidations,
		cpl_adicional,
		fisco_adicional,
		danfe_materials,
		filial_id,
		filial_cnpj
	)
	SELECT
		v_cid,
		COALESCE(tt.tipo_id, 0),
		to_char(
			COALESCE(NULLIF(s.data_competencia_id, '')::timestamptz, now()),
			'YYYYMMDD'
		)::int,
		cat.categoria_id,
		cli.cliente_id,
		forn.fornecedor_id,
		inv.inventory_id,   -- produto_id reuses inventory for this schema
		inv.inventory_id,
		s.documento,
		s.nf_numero,
		NULLIF(s.quantidade, '')::numeric,
		NULLIF(s.quantidade_kg, '')::numeric,
		NULLIF(s.valor_unitario, '')::numeric,
		NULLIF(s.valor_unitario_kg, '')::numeric,
		COALESCE(NULLIF(s.valor, '')::numeric, 0),
		NULLIF(s.valor_nf, '')::numeric,
		s.status,
		s.movement_type,
		s.danfe,
		NULLIF(s.data_criacao_origem, '')::timestamptz,
		CASE lower(COALESCE(s.is_blocked, ''))
			WHEN 'true' THEN true
			WHEN 'false' THEN false
			WHEN 'sim' THEN true
			WHEN 'não' THEN false
			WHEN 'nao' THEN false
			ELSE NULL
		END,
		NULLIF(s.volume, '')::numeric,
		NULLIF(s.volume_validado, '')::numeric,
		NULLIF(s.valor_validado, '')::numeric,
		s.id_credito,
		NULLIF(s.data_credito, '')::timestamptz,
		s.status_produto,
		NULLIF(s.data_criacao_produto, '')::timestamptz,
		s.was_purchased,
		s.was_compensation,
		s.compensations_ids,
		s.purchase_order_ids,
		s.purchase_order_codes,
		s.in_offer,
		s.has_credit,
		s.product_invalidations,
		s.cpl_adicional,
		s.fisco_adicional,
		s.danfe_materials,
		s.filial_id,
		s.filial_cnpj
	FROM tmp_invoice_staging s
	LEFT JOIN analytics_v2.dim_fornecedores forn
		ON forn.client_id = v_cid
		AND forn.cnpj = NULLIF(s.fornecedor_cnpj, '')
	LEFT JOIN analytics_v2.dim_clientes cli
		ON cli.client_id = v_cid
		AND cli.cpf_cnpj = NULLIF(s.cliente_cpf_cnpj, '')
	LEFT JOIN analytics_v2.dim_categoria cat
		ON cat.client_id = v_cid
		AND cat.nome = NULLIF(s.categoria_material, '')
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

	-- ── Aggregates ───────────────────────────────────────────────────────
	BEGIN
		PERFORM analytics_v2.atualizar_agregados(p_client_id);
	EXCEPTION WHEN OTHERS THEN
		RAISE LOG '[sync_invoices_client] aggregate refresh failed: %', SQLERRM;
	END;

	-- ── Finalise ─────────────────────────────────────────────────────────
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

	RETURN jsonb_build_object(
		'success', false,
		'error',   SQLERRM,
		'sync_id', v_sync_id
	);
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.sync_invoices_client(uuid, integer, boolean)
	TO authenticated, service_role, postgres;


-- ─────────────────────────────────────────────────────────────────────────────
-- Dispatcher: public.sincronizar_dados_cliente()
-- Routes `invoices` resource_type to the multi-table ETL and keeps the legacy
-- single-table extract path for every other resource type.
-- ─────────────────────────────────────────────────────────────────────────────
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
	v_target_table  text;
	v_foreign_table text;
	v_column_mapping jsonb;
	v_data_source_id uuid;
	v_sync_id       bigint;
	v_start         timestamptz := now();
	v_extract_res   jsonb;
	v_rows          integer := 0;
BEGIN
	SET LOCAL statement_timeout = '1500000';

	SELECT id, resource_type, storage_location, column_mapping
	INTO v_data_source_id, v_resource_type, v_foreign_table, v_column_mapping
	FROM public.client_data_sources
	WHERE client_id     = p_client_id
	  AND credential_id = p_credential_id
	ORDER BY atualizado_em DESC
	LIMIT 1;

	IF v_data_source_id IS NULL THEN
		RETURN jsonb_build_object('success', false,
			'error', 'Data source not found. Run column discovery first.');
	END IF;

	-- Invoices → multi-table ETL (dim_* + fato_transacoes + FK resolution)
	IF COALESCE(v_resource_type, 'invoices') = 'invoices' THEN
		RETURN analytics_v2.sync_invoices_client(
			p_client_id, p_credential_id, p_force_full_sync
		);
	END IF;

	-- Other resource types: single-table extract.
	v_target_table := CASE v_resource_type
		WHEN 'customers' THEN 'analytics_v2.dim_clientes'
		WHEN 'suppliers' THEN 'analytics_v2.dim_fornecedores'
		WHEN 'products'  THEN 'analytics_v2.dim_categoria'
		WHEN 'inventory' THEN 'analytics_v2.dim_inventory'
		WHEN 'sales'     THEN 'analytics_v2.fato_transacoes'
		ELSE NULL
	END;

	IF v_target_table IS NULL THEN
		RETURN jsonb_build_object('success', false,
			'error', format('Unsupported resource_type: %s', v_resource_type));
	END IF;

	INSERT INTO public.connector_sync_history (
		client_id, cliente_vizu_id, credential_id, status,
		sync_started_at, sync_mode, target_table, mapping_id
	) VALUES (
		p_client_id, p_client_id, p_credential_id, 'running',
		v_start, 'full', v_target_table, v_data_source_id
	)
	RETURNING id INTO v_sync_id;

	EXECUTE format('DELETE FROM %s WHERE client_id = %L', v_target_table, p_client_id::text);

	v_extract_res := public.extract_bigquery_data(
		p_foreign_table     := v_foreign_table,
		p_destination_table := v_target_table,
		p_column_mapping    := v_column_mapping,
		p_client_id         := p_client_id::text,
		p_where_clause      := NULL,
		p_limit             := NULL
	);

	IF NOT COALESCE((v_extract_res->>'success')::boolean, false) THEN
		UPDATE public.connector_sync_history
		SET status            = 'failed',
		    sync_completed_at = now(),
		    error_message     = v_extract_res->>'error',
		    error_details     = v_extract_res
		WHERE id = v_sync_id;

		RETURN jsonb_build_object(
			'success', false,
			'error',   COALESCE(v_extract_res->>'error', 'extract_bigquery_data failed'),
			'details', v_extract_res
		);
	END IF;

	v_rows := COALESCE((v_extract_res->>'rows_inserted')::int, 0);

	UPDATE public.connector_sync_history
	SET status            = 'completed',
	    sync_completed_at = now(),
	    records_inserted  = v_rows,
	    records_processed = v_rows,
	    progress_percent  = 100
	WHERE id = v_sync_id;

	UPDATE public.client_data_sources
	SET last_synced_at = now(), sync_status = 'completed'
	WHERE id = v_data_source_id;

	RETURN jsonb_build_object(
		'success',       true,
		'sync_id',       v_sync_id,
		'rows_inserted', v_rows,
		'target_table',  v_target_table
	);

EXCEPTION WHEN OTHERS THEN
	IF v_sync_id IS NOT NULL AND v_sync_id > 0 THEN
		UPDATE public.connector_sync_history
		SET status            = 'failed',
		    sync_completed_at = now(),
		    error_message     = SQLERRM,
		    error_details     = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
		WHERE id = v_sync_id;
	END IF;

	RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean)
	TO authenticated, service_role, postgres;

COMMIT;
