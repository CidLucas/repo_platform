-- =============================================================================
-- Migration: Fix NULL columns in fato_transacoes after ingestion
-- Date: 2026-04-22
--
-- Root causes addressed:
--   1. emittedat_operatorinvoice (timestamp text) was cast as numeric → int4,
--      which fails and leaves data_competencia_id NULL. The NOT NULL fallback
--      then wrote today's YYYYMMDD. This migration teaches extract_bigquery_data
--      to cast timestamp → YYYYMMDD int for integer target columns named
--      data_*_id (convention for dim_datas FKs).
--
--   2. Business-key mappings (receiverlegaldoc → cliente_cpf_cnpj, etc.) were
--      silently skipped because those columns don't exist on fato_transacoes.
--      As a result cliente_id, fornecedor_id, categoria_id, produto_id stayed
--      NULL. This migration adds an enrichment pass that:
--        a. UPSERTs analytics_v2.dim_{fornecedores,clientes,categoria} from the
--           foreign table using canonical targets present in column_mapping.
--        b. UPDATEs fato_transacoes FKs by JOINing dim tables and the foreign
--           table on `documento = <source documento column>`.
--        c. Populates origem_tabela and origem_id (source row provenance).
--
--   3. sincronizar_dados_cliente now calls the enrichment function for
--      resource_type='invoices'.
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. extract_bigquery_data: cast timestamp text → YYYYMMDD integer for
--    target columns whose name ends with _id (dim_datas FK convention).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.extract_bigquery_data(
	p_foreign_table text,
	p_destination_table text,
	p_column_mapping jsonb DEFAULT NULL::jsonb,
	p_client_id text DEFAULT NULL::text,
	p_where_clause text DEFAULT NULL::text,
	p_limit integer DEFAULT NULL::integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
	v_rows_inserted BIGINT;
	v_select_parts  TEXT[];
	v_insert_cols   TEXT[];
	v_select_clause TEXT;
	v_cols_clause   TEXT;
	v_query         TEXT;
	v_key           TEXT;
	v_val           TEXT;
	v_dest_schema   TEXT;
	v_dest_table    TEXT;
	v_source_exists BOOLEAN;
	v_target_exists BOOLEAN;
	v_has_client_id BOOLEAN := FALSE;

	v_target_udt_schema TEXT;
	v_target_udt_name   TEXT;
	v_target_cast_type  TEXT;
	v_target_nullable   TEXT;

	v_client_udt_schema TEXT;
	v_client_udt_name   TEXT;
	v_client_cast_type  TEXT;

	v_expr              TEXT;
	v_is_date_key       BOOLEAN;
BEGIN
	IF strpos(p_destination_table, '.') > 0 THEN
		v_dest_schema := replace(split_part(p_destination_table, '.', 1), '"', '');
		v_dest_table  := replace(split_part(p_destination_table, '.', 2), '"', '');
	ELSE
		v_dest_schema := 'public';
		v_dest_table  := replace(p_destination_table, '"', '');
	END IF;

	IF p_column_mapping IS NULL OR p_column_mapping = '{}'::jsonb THEN
		v_query := format('INSERT INTO %s SELECT * FROM %s', p_destination_table, p_foreign_table);
	ELSE
		FOR v_key, v_val IN SELECT * FROM jsonb_each_text(p_column_mapping)
		LOOP
			SELECT EXISTS (
				SELECT 1
				FROM pg_attribute
				WHERE attrelid = to_regclass(p_foreign_table)
					AND attnum > 0
					AND NOT attisdropped
					AND attname = v_key
			) INTO v_source_exists;

			SELECT EXISTS (
				SELECT 1
				FROM information_schema.columns
				WHERE table_schema = v_dest_schema
					AND table_name = v_dest_table
					AND column_name = v_val
			) INTO v_target_exists;

			IF v_source_exists AND v_target_exists THEN
				SELECT c.udt_schema, c.udt_name, c.is_nullable
				INTO v_target_udt_schema, v_target_udt_name, v_target_nullable
				FROM information_schema.columns c
				WHERE c.table_schema = v_dest_schema
					AND c.table_name = v_dest_table
					AND c.column_name = v_val
				LIMIT 1;

				IF v_target_udt_schema = 'pg_catalog' THEN
					v_target_cast_type := quote_ident(v_target_udt_name);
				ELSE
					v_target_cast_type := format('%I.%I', v_target_udt_schema, v_target_udt_name);
				END IF;

				v_insert_cols := array_append(v_insert_cols, quote_ident(v_val));

				-- Detect dim_datas FK convention: target is int and column name
				-- matches data_*_id. For these, accept timestamp/date text and
				-- convert to YYYYMMDD integer.
				v_is_date_key := (
					v_target_udt_name IN ('int2', 'int4', 'int8')
					AND v_val ~ '^data_.*_id$'
				);

				IF v_is_date_key THEN
					v_expr := format(
						$$NULLIF(to_char(NULLIF(%s::text, '')::timestamptz, 'YYYYMMDD'), '')::%s$$,
						quote_ident(v_key),
						v_target_cast_type
					);
				ELSIF v_target_udt_name IN ('text', 'varchar', 'bpchar') THEN
					v_expr := format('%s::text', quote_ident(v_key));
				ELSIF v_target_udt_name IN ('int2', 'int4', 'int8') THEN
					v_expr := format(
						'NULLIF(%s::text, '''')::numeric::%s',
						quote_ident(v_key), v_target_cast_type
					);
				ELSIF v_target_udt_name IN ('timestamp', 'timestamptz', 'date') THEN
					v_expr := format(
						'NULLIF(%s::text, '''')::%s',
						quote_ident(v_key), v_target_cast_type
					);
				ELSE
					v_expr := format(
						'NULLIF(%s::text, '''')::%s',
						quote_ident(v_key), v_target_cast_type
					);
				END IF;

				IF v_target_nullable = 'NO' THEN
					IF v_is_date_key THEN
						v_expr := format(
							'COALESCE(%s, to_char(current_date, ''YYYYMMDD'')::%s)',
							v_expr, v_target_cast_type
						);
					ELSIF v_target_udt_name IN ('int2', 'int4', 'int8') THEN
						v_expr := format('COALESCE(%s, 0::%s)', v_expr, v_target_cast_type);
					ELSIF v_target_udt_name IN ('numeric', 'float4', 'float8') THEN
						v_expr := format('COALESCE(%s, 0::%s)', v_expr, v_target_cast_type);
					ELSIF v_target_udt_name = 'bool' THEN
						v_expr := format('COALESCE(%s, false)', v_expr);
					END IF;
				END IF;

				v_select_parts := array_append(v_select_parts, v_expr);

				IF v_val = 'client_id' THEN
					v_has_client_id := TRUE;
				END IF;
			ELSE
				RAISE LOG '[extract_bq] Skipping invalid mapping source=% target=% source_exists=% target_exists=%',
					v_key, v_val, v_source_exists, v_target_exists;
			END IF;
		END LOOP;

		IF coalesce(array_length(v_insert_cols, 1), 0) = 0 THEN
			RETURN jsonb_build_object(
				'success', false,
				'error', 'No valid mapped columns found for destination table',
				'destination_table', p_destination_table
			);
		END IF;

		IF p_client_id IS NOT NULL AND NOT v_has_client_id THEN
			SELECT c.udt_schema, c.udt_name
			INTO v_client_udt_schema, v_client_udt_name
			FROM information_schema.columns c
			WHERE c.table_schema = v_dest_schema
				AND c.table_name = v_dest_table
				AND c.column_name = 'client_id'
			LIMIT 1;

			IF FOUND THEN
				IF v_client_udt_schema = 'pg_catalog' THEN
					v_client_cast_type := quote_ident(v_client_udt_name);
				ELSE
					v_client_cast_type := format('%I.%I', v_client_udt_schema, v_client_udt_name);
				END IF;

				v_select_parts := array_append(v_select_parts, format('%L::%s', p_client_id, v_client_cast_type));
				v_insert_cols  := array_append(v_insert_cols, 'client_id');
			END IF;
		END IF;

		-- Hard fallback for mandatory columns in analytics_v2.fato_transacoes.
		IF v_dest_schema = 'analytics_v2' AND v_dest_table = 'fato_transacoes' THEN
			IF NOT ('tipo_id' = ANY(v_insert_cols)) THEN
				v_insert_cols := array_append(v_insert_cols, 'tipo_id');
				v_select_parts := array_append(v_select_parts, '0::int4');
			END IF;

			IF NOT ('data_competencia_id' = ANY(v_insert_cols)) THEN
				v_insert_cols := array_append(v_insert_cols, 'data_competencia_id');
				v_select_parts := array_append(v_select_parts, 'to_char(current_date, ''YYYYMMDD'')::int4');
			END IF;

			IF NOT ('valor' = ANY(v_insert_cols)) THEN
				v_insert_cols := array_append(v_insert_cols, 'valor');
				v_select_parts := array_append(v_select_parts, '0::numeric');
			END IF;
		END IF;

		v_select_clause := array_to_string(v_select_parts, ', ');
		v_cols_clause   := array_to_string(v_insert_cols, ', ');

		v_query := format(
			'INSERT INTO %s (%s) SELECT %s FROM %s',
			p_destination_table,
			v_cols_clause,
			v_select_clause,
			p_foreign_table
		);
	END IF;

	IF p_where_clause IS NOT NULL THEN
		v_query := v_query || ' WHERE ' || p_where_clause;
	END IF;

	IF p_limit IS NOT NULL THEN
		v_query := v_query || ' LIMIT ' || p_limit;
	END IF;

	RAISE LOG '[extract_bq] Executing: %', v_query;
	EXECUTE v_query;
	GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

	RETURN jsonb_build_object('success', true, 'rows_inserted', v_rows_inserted, 'query', v_query);

EXCEPTION WHEN OTHERS THEN
	RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'query', v_query);
END;
$function$;

GRANT EXECUTE ON FUNCTION public.extract_bigquery_data(text, text, jsonb, text, text, integer)
TO authenticated, service_role, postgres;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. analytics_v2.enrich_fato_transacoes_from_source
--
--    After extract_bigquery_data() has inserted the base fato_transacoes rows,
--    use the saved column_mapping to:
--      • UPSERT dim_fornecedores from emitter_* columns
--      • UPSERT dim_clientes   from receiver_* columns
--      • UPSERT dim_categoria  from material column
--      • UPDATE fato_transacoes FKs + origem_tabela + origem_id by joining
--        the foreign table on documento = <source documento column>
--
--    The function is driven by the inverted column_mapping (canonical → source)
--    so it adapts to any ERP schema that exposes the canonical target names.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.enrich_fato_transacoes_from_source(
	p_client_id      uuid,
	p_foreign_table  text,
	p_column_mapping jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $function$
DECLARE
	v_inv        jsonb;
	v_src_doc    text;
	v_src_for_cnpj     text;
	v_src_for_nome     text;
	v_src_for_fantasia text;
	v_src_for_fone     text;
	v_src_for_cnae     text;
	v_src_for_rua      text;
	v_src_for_num      text;
	v_src_for_bairro   text;
	v_src_for_cid      text;
	v_src_for_uf       text;
	v_src_for_cep      text;
	v_src_for_company  text;

	v_src_cli_cpf_cnpj text;
	v_src_cli_nome     text;
	v_src_cli_fantasia text;
	v_src_cli_fone     text;
	v_src_cli_cnae     text;
	v_src_cli_rua      text;
	v_src_cli_num      text;
	v_src_cli_bairro   text;
	v_src_cli_cid      text;
	v_src_cli_uf       text;
	v_src_cli_cep      text;

	v_src_cat_nome  text;

	v_sql        text;
	v_updated    bigint;
	v_for_upserted bigint := 0;
	v_cli_upserted bigint := 0;
	v_cat_upserted bigint := 0;
	v_result_origem text := 'bigquery_products_invoices';
BEGIN
	-- Invert mapping: canonical_target → source_column.
	SELECT jsonb_object_agg(value, key)
	INTO v_inv
	FROM jsonb_each_text(p_column_mapping);

	v_src_doc := v_inv->>'documento';
	IF v_src_doc IS NULL THEN
		RETURN jsonb_build_object(
			'success', false,
			'error',   'column_mapping does not route any source column to canonical "documento"; cannot enrich FKs'
		);
	END IF;

	-- Fornecedor sources
	v_src_for_cnpj     := v_inv->>'fornecedor_cnpj';
	v_src_for_nome     := v_inv->>'fornecedor_nome';
	v_src_for_fantasia := v_inv->>'fornecedor_nome_fantasia';
	v_src_for_fone     := v_inv->>'fornecedor_telefone';
	v_src_for_cnae     := v_inv->>'fornecedor_cnae';
	v_src_for_rua      := v_inv->>'fornecedor_rua';
	v_src_for_num      := v_inv->>'fornecedor_numero';
	v_src_for_bairro   := v_inv->>'fornecedor_bairro';
	v_src_for_cid      := v_inv->>'fornecedor_cidade';
	v_src_for_uf       := v_inv->>'fornecedor_uf';
	v_src_for_cep      := v_inv->>'fornecedor_cep';
	v_src_for_company  := v_inv->>'fornecedor_company_id';

	-- Cliente sources
	v_src_cli_cpf_cnpj := v_inv->>'cliente_cpf_cnpj';
	v_src_cli_nome     := v_inv->>'cliente_nome';
	v_src_cli_fantasia := v_inv->>'cliente_nome_fantasia';
	v_src_cli_fone     := v_inv->>'cliente_telefone';
	v_src_cli_cnae     := v_inv->>'cliente_cnae';
	v_src_cli_rua      := v_inv->>'cliente_rua';
	v_src_cli_num      := v_inv->>'cliente_numero';
	v_src_cli_bairro   := v_inv->>'cliente_bairro';
	v_src_cli_cid      := v_inv->>'cliente_cidade';
	v_src_cli_uf       := v_inv->>'cliente_uf';
	v_src_cli_cep      := v_inv->>'cliente_cep';

	-- Categoria source
	v_src_cat_nome := v_inv->>'categoria_material';

	-- ── dim_fornecedores UPSERT ──
	IF v_src_for_cnpj IS NOT NULL THEN
		v_sql := format($upsert$
			INSERT INTO analytics_v2.dim_fornecedores (
				client_id, cnpj, nome, nome_fantasia, telefone, cnae,
				endereco_rua, endereco_numero, endereco_bairro,
				endereco_cidade, endereco_uf, endereco_cep, company_id
			)
			SELECT DISTINCT ON (%1$I::text)
				%2$L::text,
				%1$I::text,
				COALESCE(NULLIF(%3$s::text, ''), 'SEM_NOME'),
				%4$s::text, %5$s::text, %6$s::text,
				%7$s::text, %8$s::text, %9$s::text,
				%10$s::text, %11$s::text, %12$s::text, %13$s::text
			FROM %14$s
			WHERE %1$I IS NOT NULL AND %1$I::text <> ''
			ON CONFLICT (client_id, cnpj) DO UPDATE
			SET nome            = COALESCE(NULLIF(EXCLUDED.nome, ''), analytics_v2.dim_fornecedores.nome),
			    nome_fantasia   = COALESCE(EXCLUDED.nome_fantasia,   analytics_v2.dim_fornecedores.nome_fantasia),
			    telefone        = COALESCE(EXCLUDED.telefone,        analytics_v2.dim_fornecedores.telefone),
			    cnae            = COALESCE(EXCLUDED.cnae,            analytics_v2.dim_fornecedores.cnae),
			    endereco_rua    = COALESCE(EXCLUDED.endereco_rua,    analytics_v2.dim_fornecedores.endereco_rua),
			    endereco_numero = COALESCE(EXCLUDED.endereco_numero, analytics_v2.dim_fornecedores.endereco_numero),
			    endereco_bairro = COALESCE(EXCLUDED.endereco_bairro, analytics_v2.dim_fornecedores.endereco_bairro),
			    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
			    endereco_uf     = COALESCE(EXCLUDED.endereco_uf,     analytics_v2.dim_fornecedores.endereco_uf),
			    endereco_cep    = COALESCE(EXCLUDED.endereco_cep,    analytics_v2.dim_fornecedores.endereco_cep),
			    company_id      = COALESCE(EXCLUDED.company_id,      analytics_v2.dim_fornecedores.company_id),
			    atualizado_em   = now()
		$upsert$,
			v_src_for_cnpj, p_client_id::text,
			COALESCE(quote_ident(v_src_for_nome), 'NULL'),
			COALESCE(quote_ident(v_src_for_fantasia), 'NULL'),
			COALESCE(quote_ident(v_src_for_fone),     'NULL'),
			COALESCE(quote_ident(v_src_for_cnae),     'NULL'),
			COALESCE(quote_ident(v_src_for_rua),      'NULL'),
			COALESCE(quote_ident(v_src_for_num),      'NULL'),
			COALESCE(quote_ident(v_src_for_bairro),   'NULL'),
			COALESCE(quote_ident(v_src_for_cid),      'NULL'),
			COALESCE(quote_ident(v_src_for_uf),       'NULL'),
			COALESCE(quote_ident(v_src_for_cep),      'NULL'),
			COALESCE(quote_ident(v_src_for_company),  'NULL'),
			p_foreign_table
		);
		EXECUTE v_sql;
		GET DIAGNOSTICS v_for_upserted = ROW_COUNT;
		RAISE LOG '[enrich_fato] dim_fornecedores upserted: %', v_for_upserted;
	END IF;

	-- ── dim_clientes UPSERT ──
	IF v_src_cli_cpf_cnpj IS NOT NULL THEN
		v_sql := format($upsert$
			INSERT INTO analytics_v2.dim_clientes (
				client_id, cpf_cnpj, nome, nome_fantasia, telefone, cnae,
				endereco_rua, endereco_numero, endereco_bairro,
				endereco_cidade, endereco_uf, endereco_cep
			)
			SELECT DISTINCT ON (%1$I::text)
				%2$L::text,
				%1$I::text,
				COALESCE(NULLIF(%3$s::text, ''), 'SEM_NOME'),
				%4$s::text, %5$s::text, %6$s::text,
				%7$s::text, %8$s::text, %9$s::text,
				%10$s::text, %11$s::text, %12$s::text
			FROM %13$s
			WHERE %1$I IS NOT NULL AND %1$I::text <> ''
			ON CONFLICT (client_id, cpf_cnpj) DO UPDATE
			SET nome            = COALESCE(NULLIF(EXCLUDED.nome, ''), analytics_v2.dim_clientes.nome),
			    nome_fantasia   = COALESCE(EXCLUDED.nome_fantasia,   analytics_v2.dim_clientes.nome_fantasia),
			    telefone        = COALESCE(EXCLUDED.telefone,        analytics_v2.dim_clientes.telefone),
			    cnae            = COALESCE(EXCLUDED.cnae,            analytics_v2.dim_clientes.cnae),
			    endereco_rua    = COALESCE(EXCLUDED.endereco_rua,    analytics_v2.dim_clientes.endereco_rua),
			    endereco_numero = COALESCE(EXCLUDED.endereco_numero, analytics_v2.dim_clientes.endereco_numero),
			    endereco_bairro = COALESCE(EXCLUDED.endereco_bairro, analytics_v2.dim_clientes.endereco_bairro),
			    endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
			    endereco_uf     = COALESCE(EXCLUDED.endereco_uf,     analytics_v2.dim_clientes.endereco_uf),
			    endereco_cep    = COALESCE(EXCLUDED.endereco_cep,    analytics_v2.dim_clientes.endereco_cep),
			    atualizado_em   = now()
		$upsert$,
			v_src_cli_cpf_cnpj, p_client_id::text,
			COALESCE(quote_ident(v_src_cli_nome),     'NULL'),
			COALESCE(quote_ident(v_src_cli_fantasia), 'NULL'),
			COALESCE(quote_ident(v_src_cli_fone),     'NULL'),
			COALESCE(quote_ident(v_src_cli_cnae),     'NULL'),
			COALESCE(quote_ident(v_src_cli_rua),      'NULL'),
			COALESCE(quote_ident(v_src_cli_num),      'NULL'),
			COALESCE(quote_ident(v_src_cli_bairro),   'NULL'),
			COALESCE(quote_ident(v_src_cli_cid),      'NULL'),
			COALESCE(quote_ident(v_src_cli_uf),       'NULL'),
			COALESCE(quote_ident(v_src_cli_cep),      'NULL'),
			p_foreign_table
		);
		EXECUTE v_sql;
		GET DIAGNOSTICS v_cli_upserted = ROW_COUNT;
		RAISE LOG '[enrich_fato] dim_clientes upserted: %', v_cli_upserted;
	END IF;

	-- ── dim_categoria UPSERT ──
	IF v_src_cat_nome IS NOT NULL THEN
		v_sql := format($upsert$
			INSERT INTO analytics_v2.dim_categoria (client_id, nome)
			SELECT DISTINCT %2$L::text, %1$I::text
			FROM %3$s
			WHERE %1$I IS NOT NULL AND %1$I::text <> ''
			ON CONFLICT (client_id, nome) DO NOTHING
		$upsert$,
			v_src_cat_nome, p_client_id::text, p_foreign_table
		);
		EXECUTE v_sql;
		GET DIAGNOSTICS v_cat_upserted = ROW_COUNT;
		RAISE LOG '[enrich_fato] dim_categoria upserted: %', v_cat_upserted;
	END IF;

	-- ── fato_transacoes FK resolution via JOIN on documento = source doc ──
	v_sql := format($fkupd$
		UPDATE analytics_v2.fato_transacoes f
		SET
			fornecedor_id   = fo.fornecedor_id,
			cliente_id      = cl.cliente_id,
			categoria_id    = ca.categoria_id,
			origem_tabela   = %3$L,
			origem_id       = CASE
				WHEN bq.%4$I::text ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
				THEN bq.%4$I::uuid
				ELSE NULL
			END
		FROM %5$s bq
		LEFT JOIN analytics_v2.dim_fornecedores fo
			ON fo.client_id = %1$L::text
			AND fo.cnpj = %6$s
		LEFT JOIN analytics_v2.dim_clientes cl
			ON cl.client_id = %1$L::text
			AND cl.cpf_cnpj = %7$s
		LEFT JOIN analytics_v2.dim_categoria ca
			ON ca.client_id = %1$L::text
			AND ca.nome = %8$s
		WHERE f.client_id = %1$L::text
			AND f.documento = bq.%4$I::text
	$fkupd$,
		p_client_id::text,
		'',  -- placeholder for %2$ (not used); kept to avoid re-numbering surprises
		v_result_origem,
		v_src_doc,
		p_foreign_table,
		CASE WHEN v_src_for_cnpj     IS NULL THEN 'NULL' ELSE format('bq.%I::text', v_src_for_cnpj)     END,
		CASE WHEN v_src_cli_cpf_cnpj IS NULL THEN 'NULL' ELSE format('bq.%I::text', v_src_cli_cpf_cnpj) END,
		CASE WHEN v_src_cat_nome     IS NULL THEN 'NULL' ELSE format('bq.%I::text', v_src_cat_nome)     END
	);
	EXECUTE v_sql;
	GET DIAGNOSTICS v_updated = ROW_COUNT;
	RAISE LOG '[enrich_fato] fato_transacoes rows enriched: %', v_updated;

	RETURN jsonb_build_object(
		'success',                  true,
		'fornecedores_upserted',    v_for_upserted,
		'clientes_upserted',        v_cli_upserted,
		'categorias_upserted',      v_cat_upserted,
		'fato_rows_enriched',       v_updated
	);

EXCEPTION WHEN OTHERS THEN
	RAISE LOG '[enrich_fato] EXCEPTION: % (SQLSTATE: %)', SQLERRM, SQLSTATE;
	RETURN jsonb_build_object(
		'success', false,
		'error',   SQLERRM,
		'sqlstate', SQLSTATE
	);
END;
$function$;

GRANT EXECUTE ON FUNCTION analytics_v2.enrich_fato_transacoes_from_source(uuid, text, jsonb)
TO authenticated, service_role, postgres;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. sincronizar_dados_cliente: call enrichment for invoices resource
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
	p_client_id        UUID,
	p_credential_id    INTEGER,
	p_force_full_sync  BOOLEAN DEFAULT FALSE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
	v_data_source    RECORD;
	v_foreign_table  TEXT;
	v_column_mapping JSONB;
	v_resource_type  TEXT;
	v_target_table   TEXT;
	v_sync_id        BIGINT;
	v_job_id         UUID;
	v_rows_inserted  INTEGER := 0;
	v_start_time     TIMESTAMPTZ := now();
	v_sync_mode      TEXT;
	v_last_watermark TIMESTAMPTZ;
	v_watermark_col  TEXT;
	v_where_clause   TEXT;
	v_extract_result JSONB;
	v_enrich_result  JSONB;
BEGIN
	SET LOCAL statement_timeout = '1500000'; -- 25 min

	RAISE LOG '[sincronizar_dados_cliente] START client=%, credential=%, force=%',
		p_client_id, p_credential_id, p_force_full_sync;

	SELECT cds.id, cds.storage_location, cds.column_mapping, cds.resource_type, cds.source_type
	INTO v_data_source
	FROM public.client_data_sources cds
	WHERE cds.client_id = p_client_id
		AND cds.credential_id = p_credential_id
	ORDER BY cds.atualizado_em DESC
	LIMIT 1;

	IF v_data_source IS NULL THEN
		RETURN jsonb_build_object(
			'success', false,
			'error',   'Data source not found. Run column discovery first.'
		);
	END IF;

	v_foreign_table  := v_data_source.storage_location;
	v_column_mapping := v_data_source.column_mapping;
	v_resource_type  := COALESCE(v_data_source.resource_type, 'invoices');

	IF v_foreign_table IS NULL THEN
		RETURN jsonb_build_object(
			'success', false,
			'error',   'storage_location is NULL — foreign table not yet created'
		);
	END IF;

	v_target_table := CASE v_resource_type
		WHEN 'invoices'   THEN 'analytics_v2.fato_transacoes'
		WHEN 'sales'      THEN 'analytics_v2.fato_transacoes'
		WHEN 'customers'  THEN 'analytics_v2.dim_clientes'
		WHEN 'suppliers'  THEN 'analytics_v2.dim_fornecedores'
		WHEN 'products'   THEN 'analytics_v2.dim_categoria'
		WHEN 'inventory'  THEN 'analytics_v2.dim_inventory'
		ELSE 'analytics_v2.fato_transacoes'
	END;

	-- Watermark
	SELECT last_watermark_value, COALESCE(watermark_column, 'updated_at')
	INTO v_last_watermark, v_watermark_col
	FROM public.connector_sync_history
	WHERE cliente_vizu_id = p_client_id
		AND credential_id  = p_credential_id
		AND status         = 'completed'
	ORDER BY sync_completed_at DESC
	LIMIT 1;

	IF p_force_full_sync OR v_last_watermark IS NULL THEN
		v_sync_mode    := 'full';
		v_where_clause := NULL;
	ELSE
		v_sync_mode    := 'incremental';
		v_where_clause := format('%I > %L', v_watermark_col, v_last_watermark);
	END IF;

	-- Find the associated reg_jobs row (reg_jobs.client_id is TEXT)
	SELECT job_id INTO v_job_id
	FROM analytics_v2.reg_jobs
	WHERE client_id  = p_client_id::text
		AND job_type = 'bigquery_sync'
		AND status   = 'running'
		AND (input_params->>'credential_id')::integer = p_credential_id
	ORDER BY created_at DESC
	LIMIT 1;

	INSERT INTO public.connector_sync_history (
		client_id, cliente_vizu_id, credential_id, status,
		sync_started_at, sync_mode, watermark_column, target_table, mapping_id
	) VALUES (
		p_client_id, p_client_id, p_credential_id, 'running',
		v_start_time, v_sync_mode, v_watermark_col, v_target_table, v_data_source.id
	)
	RETURNING id INTO v_sync_id;

	IF v_job_id IS NOT NULL THEN
		UPDATE analytics_v2.reg_jobs SET progress_pct = 20, updated_at = now() WHERE job_id = v_job_id;
	END IF;

	IF v_sync_mode = 'full' THEN
		EXECUTE format('DELETE FROM %s WHERE client_id = %L', v_target_table, p_client_id::text);
	END IF;

	IF v_job_id IS NOT NULL THEN
		UPDATE analytics_v2.reg_jobs SET progress_pct = 30, updated_at = now() WHERE job_id = v_job_id;
	END IF;

	v_extract_result := public.extract_bigquery_data(
		p_foreign_table     := v_foreign_table,
		p_destination_table := v_target_table,
		p_column_mapping    := v_column_mapping,
		p_client_id         := p_client_id::text,
		p_where_clause      := v_where_clause,
		p_limit             := NULL
	);

	IF NOT COALESCE((v_extract_result->>'success')::boolean, false) THEN
		UPDATE public.connector_sync_history
		SET status = 'failed', sync_completed_at = now(),
		    error_message = v_extract_result->>'error',
		    error_details = v_extract_result
		WHERE id = v_sync_id;

		RETURN jsonb_build_object(
			'success', false,
			'error',   COALESCE(v_extract_result->>'error', 'extract_bigquery_data failure'),
			'details', v_extract_result,
			'sync_id', v_sync_id
		);
	END IF;

	v_rows_inserted := COALESCE((v_extract_result->>'rows_inserted')::integer, 0);

	-- ── ENRICHMENT: resolve dim FKs for invoices ──
	IF v_resource_type IN ('invoices', 'sales')
		AND v_target_table = 'analytics_v2.fato_transacoes'
		AND v_rows_inserted > 0
	THEN
		IF v_job_id IS NOT NULL THEN
			UPDATE analytics_v2.reg_jobs SET progress_pct = 60, updated_at = now() WHERE job_id = v_job_id;
		END IF;

		v_enrich_result := analytics_v2.enrich_fato_transacoes_from_source(
			p_client_id, v_foreign_table, v_column_mapping
		);
		RAISE LOG '[sincronizar_dados_cliente] Enrichment result: %', v_enrich_result;
	END IF;

	-- Aggregates
	IF v_job_id IS NOT NULL THEN
		UPDATE analytics_v2.reg_jobs SET progress_pct = 80, updated_at = now() WHERE job_id = v_job_id;
	END IF;

	BEGIN
		PERFORM public.atualizar_agregados(p_client_id::text);
	EXCEPTION WHEN OTHERS THEN
		RAISE LOG '[sincronizar_dados_cliente] aggregate refresh failed: % — continuing', SQLERRM;
	END;

	UPDATE public.connector_sync_history
	SET status = 'completed', sync_completed_at = now(),
	    records_inserted = v_rows_inserted,
	    records_processed = v_rows_inserted,
	    progress_percent = 100
	WHERE id = v_sync_id;

	UPDATE public.client_data_sources
	SET last_synced_at = now(), sync_status = 'completed'
	WHERE id = v_data_source.id;

	RETURN jsonb_build_object(
		'success',          true,
		'sync_id',          v_sync_id,
		'sync_mode',        v_sync_mode,
		'target_table',     v_target_table,
		'rows_inserted',    v_rows_inserted,
		'enrichment',       v_enrich_result,
		'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
	);

EXCEPTION WHEN OTHERS THEN
	RAISE LOG '[sincronizar_dados_cliente] EXCEPTION: % (SQLSTATE: %)', SQLERRM, SQLSTATE;

	IF v_sync_id IS NOT NULL AND v_sync_id > 0 THEN
		UPDATE public.connector_sync_history
		SET status = 'failed', sync_completed_at = now(),
		    error_message = SQLERRM,
		    error_details = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
		WHERE id = v_sync_id;
	END IF;

	RETURN jsonb_build_object(
		'success', false,
		'error',   SQLERRM,
		'sync_id', v_sync_id
	);
END;
$$;

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean)
TO authenticated, service_role, postgres;

COMMIT;
