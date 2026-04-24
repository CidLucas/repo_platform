-- =============================================================================
-- Migration: Production-grade invoice ingestion
-- Date: 2026-04-22
--
-- Root causes fixed:
--
-- (1) data_competencia_id was always today's date
--     BigQuery source `emittedat_operatorinvoice` holds Unix epoch seconds
--     serialised as text (e.g. '1.77635604E9'). The previous cast produced
--     a 10-digit int which the `ensure_dim_data` trigger rejected (regex
--     requires 8 digits) and silently replaced with current_date.
--
--     Fix: detect int4/int8 target columns whose name matches `data_*_id`
--     and convert source values – whether Unix epoch or ISO timestamp –
--     to YYYYMMDD integer.
--
-- (2) dim_clientes / dim_fornecedores / dim_categoria / dim_inventory were
--     never populated from BigQuery.
--     Mapping targets for dim attributes (`cliente_nome`, `fornecedor_cnpj`,
--     `categoria_material`, `produto_ncm`, …) do not exist on
--     fato_transacoes, so `extract_bigquery_data` silently dropped them.
--
--     Fix: new `analytics_v2.ingest_invoices_from_bq` that populates the
--     four dim tables from the same foreign table before loading the fact
--     table, then resolves FK columns on the inserted fact rows.
--
-- (3) Removed the misleading `data_competencia_id = current_date` fallback
--     that was masking (1). `valor` and `tipo_id` fallbacks remain because
--     both are NOT NULL and there are valid cases where the source has no
--     value (e.g. fiscal-only documents with zero amount).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) extract_bigquery_data: smart date-id casting, cleaner control flow
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.extract_bigquery_data(
  p_foreign_table     text,
  p_destination_table text,
  p_column_mapping    jsonb   DEFAULT NULL,
  p_client_id         text    DEFAULT NULL,
  p_where_clause      text    DEFAULT NULL,
  p_limit             integer DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
  v_rows_inserted BIGINT;
  v_select_parts  TEXT[] := ARRAY[]::text[];
  v_insert_cols   TEXT[] := ARRAY[]::text[];
  v_query         TEXT;
  v_key           TEXT;
  v_val           TEXT;
  v_dest_schema   TEXT;
  v_dest_table    TEXT;
  v_source_exists BOOLEAN;
  v_target_exists BOOLEAN;
  v_has_client_id BOOLEAN := FALSE;
  v_udt_schema    TEXT;
  v_udt_name      TEXT;
  v_cast_type     TEXT;
  v_nullable      TEXT;
  v_is_date_id    BOOLEAN;
  v_cli_udt_schema TEXT;
  v_cli_udt_name   TEXT;
  v_cli_cast_type  TEXT;
  v_expr          TEXT;
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
    FOR v_key, v_val IN SELECT * FROM jsonb_each_text(p_column_mapping) LOOP
      SELECT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = to_regclass(p_foreign_table)
          AND attnum > 0 AND NOT attisdropped AND attname = v_key
      ) INTO v_source_exists;

      SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = v_dest_schema
          AND table_name   = v_dest_table
          AND column_name  = v_val
      ) INTO v_target_exists;

      IF NOT (v_source_exists AND v_target_exists) THEN
        RAISE LOG '[extract_bq] Skip %→% (src=% tgt=%)',
          v_key, v_val, v_source_exists, v_target_exists;
        CONTINUE;
      END IF;

      SELECT udt_schema, udt_name, is_nullable
        INTO v_udt_schema, v_udt_name, v_nullable
      FROM information_schema.columns
      WHERE table_schema = v_dest_schema
        AND table_name   = v_dest_table
        AND column_name  = v_val
      LIMIT 1;

      v_cast_type := CASE
        WHEN v_udt_schema = 'pg_catalog' THEN quote_ident(v_udt_name)
        ELSE format('%I.%I', v_udt_schema, v_udt_name)
      END;

      v_is_date_id := v_udt_name IN ('int2','int4','int8') AND v_val ~ '^data_.*_id$';

      IF v_is_date_id THEN
        -- Accept Unix epoch (possibly scientific notation) OR an ISO/text
        -- timestamp. Convert to YYYYMMDD integer.
        v_expr := format(
          'CASE
             WHEN NULLIF(%1$I::text, '''') IS NULL THEN NULL
             WHEN %1$I::text ~ ''^-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?$''
               THEN to_char(to_timestamp(%1$I::text::numeric), ''YYYYMMDD'')::%2$s
             ELSE to_char(%1$I::text::timestamptz, ''YYYYMMDD'')::%2$s
           END',
          v_key, v_cast_type
        );
      ELSIF v_udt_name IN ('text','varchar','bpchar') THEN
        v_expr := format('%I::text', v_key);
      ELSIF v_udt_name IN ('int2','int4','int8') THEN
        -- cast via numeric first to tolerate scientific notation
        v_expr := format('NULLIF(%I::text, '''')::numeric::%s', v_key, v_cast_type);
      ELSE
        v_expr := format('NULLIF(%I::text, '''')::%s', v_key, v_cast_type);
      END IF;

      -- NOT NULL coercion for ordinary columns. Date-id columns pass through
      -- the ensure_dim_data trigger and must keep NULL semantics.
      IF v_nullable = 'NO' AND NOT v_is_date_id THEN
        IF v_udt_name IN ('int2','int4','int8','numeric','float4','float8') THEN
          v_expr := format('COALESCE(%s, 0::%s)', v_expr, v_cast_type);
        ELSIF v_udt_name = 'bool' THEN
          v_expr := format('COALESCE(%s, false)', v_expr);
        END IF;
      END IF;

      v_insert_cols  := array_append(v_insert_cols,  quote_ident(v_val));
      v_select_parts := array_append(v_select_parts, v_expr);

      IF v_val = 'client_id' THEN
        v_has_client_id := TRUE;
      END IF;
    END LOOP;

    IF array_length(v_insert_cols, 1) IS NULL THEN
      RETURN jsonb_build_object(
        'success', false,
        'error',   'No valid mapped columns found for destination table',
        'destination_table', p_destination_table
      );
    END IF;

    IF p_client_id IS NOT NULL AND NOT v_has_client_id THEN
      SELECT udt_schema, udt_name INTO v_cli_udt_schema, v_cli_udt_name
      FROM information_schema.columns
      WHERE table_schema = v_dest_schema
        AND table_name   = v_dest_table
        AND column_name  = 'client_id'
      LIMIT 1;

      IF FOUND THEN
        v_cli_cast_type := CASE
          WHEN v_cli_udt_schema = 'pg_catalog' THEN quote_ident(v_cli_udt_name)
          ELSE format('%I.%I', v_cli_udt_schema, v_cli_udt_name)
        END;
        v_insert_cols  := array_append(v_insert_cols,  'client_id');
        v_select_parts := array_append(v_select_parts,
          format('%L::%s', p_client_id, v_cli_cast_type));
      END IF;
    END IF;

    -- Guarantee NOT NULL required columns on fato_transacoes.
    -- NOTE: data_competencia_id is NOT included here on purpose —
    -- a missing competencia date is a real defect that must surface.
    IF v_dest_schema = 'analytics_v2' AND v_dest_table = 'fato_transacoes' THEN
      IF NOT ('tipo_id' = ANY(v_insert_cols)) THEN
        v_insert_cols  := array_append(v_insert_cols,  'tipo_id');
        v_select_parts := array_append(v_select_parts, '0::int4');
      END IF;
      IF NOT ('valor' = ANY(v_insert_cols)) THEN
        v_insert_cols  := array_append(v_insert_cols,  'valor');
        v_select_parts := array_append(v_select_parts, '0::numeric');
      END IF;
    END IF;

    v_query := format(
      'INSERT INTO %s (%s) SELECT %s FROM %s',
      p_destination_table,
      array_to_string(v_insert_cols, ', '),
      array_to_string(v_select_parts, ', '),
      p_foreign_table
    );
  END IF;

  IF p_where_clause IS NOT NULL THEN
    v_query := v_query || ' WHERE ' || p_where_clause;
  END IF;
  IF p_limit IS NOT NULL THEN
    v_query := v_query || ' LIMIT ' || p_limit;
  END IF;

  RAISE LOG '[extract_bq] %', v_query;
  EXECUTE v_query;
  GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

  RETURN jsonb_build_object(
    'success',       true,
    'rows_inserted', v_rows_inserted,
    'query',         v_query
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'query', v_query);
END;
$function$;

GRANT EXECUTE ON FUNCTION public.extract_bigquery_data(text, text, jsonb, text, text, integer)
  TO authenticated, service_role, postgres;


-- ---------------------------------------------------------------------------
-- 2) ingest_invoices_from_bq: populates dims first, then calls
--    extract_bigquery_data for fato_transacoes, then resolves FK columns.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION analytics_v2.ingest_invoices_from_bq(
  p_foreign_table  text,
  p_client_id      text,
  p_column_mapping jsonb,
  p_where_clause   text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
  v_rev            jsonb;
  v_where_suffix   text := CASE WHEN p_where_clause IS NULL THEN '' ELSE ' AND (' || p_where_clause || ')' END;
  v_where_only     text := CASE WHEN p_where_clause IS NULL THEN '' ELSE ' WHERE ' || p_where_clause END;

  -- Source column names (may be NULL if mapping does not include target)
  s_cli_cnpj  text; s_cli_nome  text; s_cli_fant  text; s_cli_phone text;
  s_cli_cnae  text; s_cli_rua   text; s_cli_num   text; s_cli_bairro text;
  s_cli_cidade text; s_cli_uf   text; s_cli_cep   text;

  s_frn_cnpj  text; s_frn_nome  text; s_frn_fant  text; s_frn_phone text;
  s_frn_cnae  text; s_frn_rua   text; s_frn_num   text; s_frn_bairro text;
  s_frn_cidade text; s_frn_uf   text; s_frn_cep   text; s_frn_comp  text;

  s_cat_nome  text;
  s_prd_ext   text; s_prd_desc  text; s_prd_ncm   text; s_prd_un    text;
  s_documento text;

  v_sql    text;
  v_cli    int := 0;
  v_frn    int := 0;
  v_cat    int := 0;
  v_inv    int := 0;
  v_res    jsonb;
  v_rows   int := 0;
BEGIN
  -- Reverse mapping: canonical_target -> source_column
  SELECT jsonb_object_agg(value, key) INTO v_rev FROM jsonb_each_text(p_column_mapping);

  s_cli_cnpj  := v_rev->>'cliente_cpf_cnpj';
  s_cli_nome  := v_rev->>'cliente_nome';
  s_cli_fant  := v_rev->>'cliente_nome_fantasia';
  s_cli_phone := v_rev->>'cliente_telefone';
  s_cli_cnae  := v_rev->>'cliente_cnae';
  s_cli_rua   := v_rev->>'cliente_rua';
  s_cli_num   := v_rev->>'cliente_numero';
  s_cli_bairro:= v_rev->>'cliente_bairro';
  s_cli_cidade:= v_rev->>'cliente_cidade';
  s_cli_uf    := v_rev->>'cliente_uf';
  s_cli_cep   := v_rev->>'cliente_cep';

  s_frn_cnpj  := v_rev->>'fornecedor_cnpj';
  s_frn_nome  := v_rev->>'fornecedor_nome';
  s_frn_fant  := v_rev->>'fornecedor_nome_fantasia';
  s_frn_phone := v_rev->>'fornecedor_telefone';
  s_frn_cnae  := v_rev->>'fornecedor_cnae';
  s_frn_rua   := v_rev->>'fornecedor_rua';
  s_frn_num   := v_rev->>'fornecedor_numero';
  s_frn_bairro:= v_rev->>'fornecedor_bairro';
  s_frn_cidade:= v_rev->>'fornecedor_cidade';
  s_frn_uf    := v_rev->>'fornecedor_uf';
  s_frn_cep   := v_rev->>'fornecedor_cep';
  s_frn_comp  := v_rev->>'fornecedor_company_id';

  s_cat_nome  := v_rev->>'categoria_material';

  s_prd_ext   := v_rev->>'produto_id_externo';
  s_prd_desc  := v_rev->>'produto_descricao';
  s_prd_ncm   := v_rev->>'produto_ncm';
  s_prd_un    := v_rev->>'produto_unidade';

  s_documento := v_rev->>'documento';

  -- -------------------------------------------------------------------------
  -- 2a) dim_clientes
  -- -------------------------------------------------------------------------
  IF s_cli_cnpj IS NOT NULL THEN
    v_sql := format(
      $f$
      INSERT INTO analytics_v2.dim_clientes
        (client_id, cpf_cnpj, nome, nome_fantasia, telefone, cnae,
         endereco_rua, endereco_numero, endereco_bairro, endereco_cidade,
         endereco_uf, endereco_cep)
      SELECT %1$L,
             NULLIF(%2$I::text, '') AS cpf_cnpj,
             COALESCE(MAX(NULLIF(%3$s::text, '')), 'SEM_NOME'),
             MAX(NULLIF(%4$s::text, '')),
             MAX(NULLIF(%5$s::text, '')),
             MAX(NULLIF(%6$s::text, '')),
             MAX(NULLIF(%7$s::text, '')),
             MAX(NULLIF(%8$s::text, '')),
             MAX(NULLIF(%9$s::text, '')),
             MAX(NULLIF(%10$s::text, '')),
             MAX(NULLIF(%11$s::text, '')),
             MAX(NULLIF(%12$s::text, ''))
      FROM %13$s
      WHERE NULLIF(%2$I::text, '') IS NOT NULL %14$s
      GROUP BY NULLIF(%2$I::text, '')
      ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
        nome            = COALESCE(NULLIF(EXCLUDED.nome,'SEM_NOME'), analytics_v2.dim_clientes.nome),
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
      $f$,
      p_client_id,                                   -- %1
      s_cli_cnpj,                                    -- %2
      COALESCE(quote_ident(s_cli_nome),   'NULL'),   -- %3
      COALESCE(quote_ident(s_cli_fant),   'NULL'),   -- %4
      COALESCE(quote_ident(s_cli_phone),  'NULL'),   -- %5
      COALESCE(quote_ident(s_cli_cnae),   'NULL'),   -- %6
      COALESCE(quote_ident(s_cli_rua),    'NULL'),   -- %7
      COALESCE(quote_ident(s_cli_num),    'NULL'),   -- %8
      COALESCE(quote_ident(s_cli_bairro), 'NULL'),   -- %9
      COALESCE(quote_ident(s_cli_cidade), 'NULL'),   -- %10
      COALESCE(quote_ident(s_cli_uf),     'NULL'),   -- %11
      COALESCE(quote_ident(s_cli_cep),    'NULL'),   -- %12
      p_foreign_table,                               -- %13
      v_where_suffix                                 -- %14
    );
    EXECUTE v_sql;
    GET DIAGNOSTICS v_cli = ROW_COUNT;
  END IF;

  -- -------------------------------------------------------------------------
  -- 2b) dim_fornecedores
  -- -------------------------------------------------------------------------
  IF s_frn_cnpj IS NOT NULL THEN
    v_sql := format(
      $f$
      INSERT INTO analytics_v2.dim_fornecedores
        (client_id, cnpj, nome, nome_fantasia, telefone, cnae,
         endereco_rua, endereco_numero, endereco_bairro, endereco_cidade,
         endereco_uf, endereco_cep, company_id)
      SELECT %1$L,
             NULLIF(%2$I::text, '') AS cnpj,
             COALESCE(MAX(NULLIF(%3$s::text, '')), 'SEM_NOME'),
             MAX(NULLIF(%4$s::text, '')),
             MAX(NULLIF(%5$s::text, '')),
             MAX(NULLIF(%6$s::text, '')),
             MAX(NULLIF(%7$s::text, '')),
             MAX(NULLIF(%8$s::text, '')),
             MAX(NULLIF(%9$s::text, '')),
             MAX(NULLIF(%10$s::text, '')),
             MAX(NULLIF(%11$s::text, '')),
             MAX(NULLIF(%12$s::text, '')),
             MAX(NULLIF(%13$s::text, ''))
      FROM %14$s
      WHERE NULLIF(%2$I::text, '') IS NOT NULL %15$s
      GROUP BY NULLIF(%2$I::text, '')
      ON CONFLICT (client_id, cnpj) DO UPDATE SET
        nome            = COALESCE(NULLIF(EXCLUDED.nome,'SEM_NOME'), analytics_v2.dim_fornecedores.nome),
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
      $f$,
      p_client_id,
      s_frn_cnpj,
      COALESCE(quote_ident(s_frn_nome),   'NULL'),
      COALESCE(quote_ident(s_frn_fant),   'NULL'),
      COALESCE(quote_ident(s_frn_phone),  'NULL'),
      COALESCE(quote_ident(s_frn_cnae),   'NULL'),
      COALESCE(quote_ident(s_frn_rua),    'NULL'),
      COALESCE(quote_ident(s_frn_num),    'NULL'),
      COALESCE(quote_ident(s_frn_bairro), 'NULL'),
      COALESCE(quote_ident(s_frn_cidade), 'NULL'),
      COALESCE(quote_ident(s_frn_uf),     'NULL'),
      COALESCE(quote_ident(s_frn_cep),    'NULL'),
      COALESCE(quote_ident(s_frn_comp),   'NULL'),
      p_foreign_table,
      v_where_suffix
    );
    EXECUTE v_sql;
    GET DIAGNOSTICS v_frn = ROW_COUNT;
  END IF;

  -- -------------------------------------------------------------------------
  -- 2c) dim_categoria
  -- -------------------------------------------------------------------------
  IF s_cat_nome IS NOT NULL THEN
    v_sql := format(
      $f$
      INSERT INTO analytics_v2.dim_categoria (client_id, nome)
      SELECT DISTINCT %1$L, NULLIF(%2$I::text, '')
      FROM %3$s
      WHERE NULLIF(%2$I::text, '') IS NOT NULL %4$s
      ON CONFLICT (client_id, nome) DO NOTHING
      $f$,
      p_client_id,
      s_cat_nome,
      p_foreign_table,
      v_where_suffix
    );
    EXECUTE v_sql;
    GET DIAGNOSTICS v_cat = ROW_COUNT;
  END IF;

  -- -------------------------------------------------------------------------
  -- 2d) dim_inventory
  --     Business key is (client_id, nome). Nome preference:
  --     description_product  >  id_product  >  'Sem descrição'.
  -- -------------------------------------------------------------------------
  IF s_prd_ext IS NOT NULL OR s_prd_desc IS NOT NULL THEN
    v_sql := format(
      $f$
      INSERT INTO analytics_v2.dim_inventory
        (client_id, nome, sku, external_id, ncm, unidade_comercial, category_id)
      SELECT %1$L,
             nome_key,
             MAX(sku_val),
             MAX(external_val),
             MAX(ncm_val),
             MAX(un_val),
             (array_agg(cat_id) FILTER (WHERE cat_id IS NOT NULL))[1]
      FROM (
        SELECT
          COALESCE(NULLIF(%2$s::text, ''), NULLIF(%3$s::text, ''), 'Sem descrição') AS nome_key,
          NULLIF(%3$s::text, '') AS sku_val,
          NULLIF(%3$s::text, '') AS external_val,
          NULLIF(%4$s::text, '') AS ncm_val,
          NULLIF(%5$s::text, '') AS un_val,
          dc.categoria_id        AS cat_id
        FROM %6$s src
        LEFT JOIN analytics_v2.dim_categoria dc
          ON dc.client_id = %1$L
         AND dc.nome      = NULLIF(%7$s::text, '')
        %8$s
      ) t
      GROUP BY nome_key
      ON CONFLICT (client_id, nome) DO UPDATE SET
        sku               = COALESCE(EXCLUDED.sku,               analytics_v2.dim_inventory.sku),
        external_id       = COALESCE(EXCLUDED.external_id,       analytics_v2.dim_inventory.external_id),
        ncm               = COALESCE(EXCLUDED.ncm,               analytics_v2.dim_inventory.ncm),
        unidade_comercial = COALESCE(EXCLUDED.unidade_comercial, analytics_v2.dim_inventory.unidade_comercial),
        category_id       = COALESCE(EXCLUDED.category_id,       analytics_v2.dim_inventory.category_id),
        updated_at        = now()
      $f$,
      p_client_id,                                         -- %1
      COALESCE(quote_ident(s_prd_desc),     'NULL'),       -- %2
      COALESCE(quote_ident(s_prd_ext),      'NULL'),       -- %3
      COALESCE(quote_ident(s_prd_ncm),      'NULL'),       -- %4
      COALESCE(quote_ident(s_prd_un),       'NULL'),       -- %5
      p_foreign_table,                                     -- %6
      COALESCE('src.' || quote_ident(s_cat_nome), 'NULL'), -- %7
      v_where_only                                          -- %8
    );
    EXECUTE v_sql;
    GET DIAGNOSTICS v_inv = ROW_COUNT;
  END IF;

  -- -------------------------------------------------------------------------
  -- 2e) fato_transacoes via generic extract (with date-id casting fix)
  -- -------------------------------------------------------------------------
  v_res := public.extract_bigquery_data(
    p_foreign_table     := p_foreign_table,
    p_destination_table := 'analytics_v2.fato_transacoes',
    p_column_mapping    := p_column_mapping,
    p_client_id         := p_client_id,
    p_where_clause      := p_where_clause,
    p_limit             := NULL
  );

  IF NOT COALESCE((v_res->>'success')::boolean, false) THEN
    RETURN jsonb_build_object(
      'success',    false,
      'stage',      'fato_transacoes',
      'error',      v_res->>'error',
      'details',    v_res,
      'dim_counts', jsonb_build_object(
        'clientes', v_cli, 'fornecedores', v_frn, 'categorias', v_cat, 'inventory', v_inv
      )
    );
  END IF;

  v_rows := COALESCE((v_res->>'rows_inserted')::int, 0);

  -- -------------------------------------------------------------------------
  -- 2f) Resolve FK columns on the rows we just inserted.
  --     We match using client_id + documento (the invoice operation id)
  --     which is stable across product rows of the same invoice.
  -- -------------------------------------------------------------------------

  IF s_documento IS NOT NULL AND s_cli_cnpj IS NOT NULL THEN
    EXECUTE format(
      $f$
      UPDATE analytics_v2.fato_transacoes ft
      SET cliente_id = dc.cliente_id
      FROM %1$s src
      JOIN analytics_v2.dim_clientes dc
        ON dc.client_id = %2$L
       AND dc.cpf_cnpj  = NULLIF(src.%3$I::text, '')
      WHERE ft.client_id   = %2$L
        AND ft.cliente_id  IS NULL
        AND ft.documento   = NULLIF(src.%4$I::text, '')
      $f$,
      p_foreign_table, p_client_id, s_cli_cnpj, s_documento
    );
  END IF;

  IF s_documento IS NOT NULL AND s_frn_cnpj IS NOT NULL THEN
    EXECUTE format(
      $f$
      UPDATE analytics_v2.fato_transacoes ft
      SET fornecedor_id = df.fornecedor_id
      FROM %1$s src
      JOIN analytics_v2.dim_fornecedores df
        ON df.client_id = %2$L
       AND df.cnpj      = NULLIF(src.%3$I::text, '')
      WHERE ft.client_id     = %2$L
        AND ft.fornecedor_id IS NULL
        AND ft.documento     = NULLIF(src.%4$I::text, '')
      $f$,
      p_foreign_table, p_client_id, s_frn_cnpj, s_documento
    );
  END IF;

  IF s_documento IS NOT NULL AND s_cat_nome IS NOT NULL THEN
    EXECUTE format(
      $f$
      UPDATE analytics_v2.fato_transacoes ft
      SET categoria_id = dc.categoria_id
      FROM %1$s src
      JOIN analytics_v2.dim_categoria dc
        ON dc.client_id = %2$L
       AND dc.nome      = NULLIF(src.%3$I::text, '')
      WHERE ft.client_id    = %2$L
        AND ft.categoria_id IS NULL
        AND ft.documento    = NULLIF(src.%4$I::text, '')
      $f$,
      p_foreign_table, p_client_id, s_cat_nome, s_documento
    );
  END IF;

  IF s_documento IS NOT NULL AND (s_prd_ext IS NOT NULL OR s_prd_desc IS NOT NULL) THEN
    EXECUTE format(
      $f$
      UPDATE analytics_v2.fato_transacoes ft
      SET inventory_id = di.inventory_id
      FROM %1$s src
      JOIN analytics_v2.dim_inventory di
        ON di.client_id = %2$L
       AND di.nome      = COALESCE(NULLIF(src.%3$s::text, ''), NULLIF(src.%4$s::text, ''), 'Sem descrição')
      WHERE ft.client_id    = %2$L
        AND ft.inventory_id IS NULL
        AND ft.documento    = NULLIF(src.%5$I::text, '')
      $f$,
      p_foreign_table,
      p_client_id,
      COALESCE(quote_ident(s_prd_desc), 'NULL'),
      COALESCE(quote_ident(s_prd_ext),  'NULL'),
      s_documento
    );
  END IF;

  RETURN jsonb_build_object(
    'success',       true,
    'rows_inserted', v_rows,
    'dim_counts',    jsonb_build_object(
      'clientes',     v_cli,
      'fornecedores', v_frn,
      'categorias',   v_cat,
      'inventory',    v_inv
    )
  );
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.ingest_invoices_from_bq(text, text, jsonb, text)
  TO authenticated, service_role, postgres;


-- ---------------------------------------------------------------------------
-- 3) sincronizar_dados_cliente: route invoices through ingest_invoices_from_bq
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
  p_client_id       UUID,
  p_credential_id   INTEGER,
  p_force_full_sync BOOLEAN DEFAULT FALSE
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
  v_rows           INTEGER := 0;
  v_start_time     TIMESTAMPTZ := now();
  v_sync_mode      TEXT;
  v_last_watermark TIMESTAMPTZ;
  v_watermark_col  TEXT;
  v_where_clause   TEXT;
  v_res            JSONB;
BEGIN
  SET LOCAL statement_timeout = '1500000';  -- 25 min safety net

  RAISE LOG '[sincronizar_dados_cliente] START client=%, credential=%, force=%',
    p_client_id, p_credential_id, p_force_full_sync;

  SELECT cds.id, cds.storage_location, cds.column_mapping, cds.resource_type
    INTO v_data_source
  FROM public.client_data_sources cds
  WHERE cds.client_id     = p_client_id::text
    AND cds.credential_id = p_credential_id
  ORDER BY cds.atualizado_em DESC
  LIMIT 1;

  IF v_data_source IS NULL THEN
    RETURN jsonb_build_object('success', false,
      'error', 'Data source not found. Run column discovery first.');
  END IF;

  v_foreign_table  := v_data_source.storage_location;
  v_column_mapping := v_data_source.column_mapping;
  v_resource_type  := COALESCE(v_data_source.resource_type, 'invoices');

  IF v_foreign_table IS NULL THEN
    RETURN jsonb_build_object('success', false,
      'error', 'storage_location is NULL — foreign table not yet created');
  END IF;

  v_target_table := CASE v_resource_type
    WHEN 'invoices'  THEN 'analytics_v2.fato_transacoes'
    WHEN 'sales'     THEN 'analytics_v2.fato_transacoes'
    WHEN 'customers' THEN 'analytics_v2.dim_clientes'
    WHEN 'suppliers' THEN 'analytics_v2.dim_fornecedores'
    WHEN 'products'  THEN 'analytics_v2.dim_categoria'
    WHEN 'inventory' THEN 'analytics_v2.dim_inventory'
    ELSE 'analytics_v2.fato_transacoes'
  END;

  SELECT last_watermark_value, COALESCE(watermark_column, 'updated_at')
    INTO v_last_watermark, v_watermark_col
  FROM public.connector_sync_history
  WHERE cliente_vizu_id = p_client_id
    AND credential_id   = p_credential_id
    AND status          = 'completed'
  ORDER BY sync_completed_at DESC
  LIMIT 1;

  IF p_force_full_sync OR v_last_watermark IS NULL THEN
    v_sync_mode    := 'full';
    v_where_clause := NULL;
  ELSE
    v_sync_mode    := 'incremental';
    v_where_clause := format('%I > %L', v_watermark_col, v_last_watermark);
  END IF;

  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE client_id = p_client_id::text
    AND job_type  = 'bigquery_sync'
    AND status    = 'running'
    AND (input_params->>'credential_id')::integer = p_credential_id
  ORDER BY created_at DESC
  LIMIT 1;

  INSERT INTO public.connector_sync_history (
    client_id, cliente_vizu_id, credential_id, status,
    sync_started_at, sync_mode, watermark_column,
    target_table, mapping_id
  ) VALUES (
    p_client_id, p_client_id, p_credential_id, 'running',
    v_start_time, v_sync_mode, v_watermark_col,
    v_target_table, v_data_source.id
  )
  RETURNING id INTO v_sync_id;

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 20, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  IF v_sync_mode = 'full' THEN
    EXECUTE format('DELETE FROM %s WHERE client_id = %L', v_target_table, p_client_id::text);
    IF v_resource_type IN ('invoices','sales') THEN
      DELETE FROM analytics_v2.dim_inventory    WHERE client_id = p_client_id::text;
      DELETE FROM analytics_v2.dim_categoria    WHERE client_id = p_client_id::text;
      DELETE FROM analytics_v2.dim_clientes     WHERE client_id = p_client_id::text;
      DELETE FROM analytics_v2.dim_fornecedores WHERE client_id = p_client_id::text;
    END IF;
  END IF;

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 30, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  IF v_resource_type IN ('invoices','sales') THEN
    v_res := analytics_v2.ingest_invoices_from_bq(
      p_foreign_table  := v_foreign_table,
      p_client_id      := p_client_id::text,
      p_column_mapping := v_column_mapping,
      p_where_clause   := v_where_clause
    );
  ELSE
    v_res := public.extract_bigquery_data(
      p_foreign_table     := v_foreign_table,
      p_destination_table := v_target_table,
      p_column_mapping    := v_column_mapping,
      p_client_id         := p_client_id::text,
      p_where_clause      := v_where_clause,
      p_limit             := NULL
    );
  END IF;

  IF NOT COALESCE((v_res->>'success')::boolean, false) THEN
    UPDATE public.connector_sync_history
       SET status            = 'failed',
           sync_completed_at = now(),
           error_message     = v_res->>'error',
           error_details     = v_res
     WHERE id = v_sync_id;

    RETURN jsonb_build_object(
      'success', false,
      'error',   v_res->>'error',
      'details', v_res,
      'sync_id', v_sync_id
    );
  END IF;

  v_rows := COALESCE((v_res->>'rows_inserted')::int, 0);

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 80, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  BEGIN
    PERFORM public.atualizar_agregados(p_client_id::text);
  EXCEPTION WHEN OTHERS THEN
    RAISE LOG '[sincronizar_dados_cliente] aggregate refresh failed: % — continuing', SQLERRM;
  END;

  UPDATE public.connector_sync_history
     SET status            = 'completed',
         sync_completed_at = now(),
         records_inserted  = v_rows,
         records_processed = v_rows,
         progress_percent  = 100
   WHERE id = v_sync_id;

  UPDATE public.client_data_sources
     SET last_synced_at = now(), sync_status = 'completed'
   WHERE id = v_data_source.id;

  RETURN jsonb_build_object(
    'success',          true,
    'sync_id',          v_sync_id,
    'sync_mode',        v_sync_mode,
    'target_table',     v_target_table,
    'rows_inserted',    v_rows,
    'dim_counts',       v_res->'dim_counts',
    'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
  );

EXCEPTION WHEN OTHERS THEN
  RAISE LOG '[sincronizar_dados_cliente] EXCEPTION: % (%)', SQLERRM, SQLSTATE;
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

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean)
  TO authenticated, service_role, postgres;

COMMIT;
