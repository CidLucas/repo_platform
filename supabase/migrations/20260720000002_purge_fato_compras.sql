-- =====================================================================
-- 20260720000002_purge_fato_compras.sql
-- Remove todas as referências à tabela inexistente analytics_v2.fato_compras.
-- Decisão (2026-07-20): toda transação vive em analytics_v2.fato_transacoes,
-- discriminada por tipo_transacao. fato_compras nunca existiu em produção e
-- quebrava: (a) get_indicators_for_client dimensão 'supply', (b) offboard_client
-- e o cron offboard_cleanup_nightly (array de tabelas a limpar).
--
--  - supply: redirecionado para fato_transacoes com tipo_transacao='compra',
--    preservando a semântica original (COUNT DISTINCT documento / status='aprovado').
--  - offboard: entrada fato_compras removida dos arrays (fato_transacoes já cobre compras).
-- =====================================================================

BEGIN;

-- 1a) get_indicators_for_client (3 args) — supply via fato_transacoes/compra
CREATE OR REPLACE FUNCTION analytics_v2.get_indicators_for_client(p_client_id uuid, p_dimension text, p_period text DEFAULT '30d'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_days int; v_start date; v_prev_start date; v_result jsonb := '{}'::jsonb;
  v_receita numeric; v_prev_receita numeric; v_pedidos bigint; v_ticket numeric;
  v_clientes_ativos bigint; v_novos_clientes bigint; v_recorrentes bigint;
  v_skus_ativos bigint; v_giro numeric; v_rfqs bigint; v_pos_aprovadas bigint;
BEGIN
  v_days := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_start := CURRENT_DATE - (v_days * INTERVAL '1 day')::interval;
  v_prev_start := v_start - (v_days * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;
    v_result := jsonb_build_object('receita_liquida', v_receita, 'custo_total', NULL,
      'margem_bruta_perc', NULL, 'ticket_medio', v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2) ELSE NULL END);

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start
      GROUP BY ft.customer_id HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;
    v_result := jsonb_build_object('total_pedidos', v_pedidos, 'ticket_medio', v_ticket,
      'novos_clientes', v_novos_clientes, 'clientes_ativos', v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END);

  ELSIF p_dimension = 'inventory' THEN
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2) INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory WHERE client_id = p_client_id AND dias_recencia <= 90;
    v_result := jsonb_build_object('skus_ativos', v_skus_ativos, 'skus_sem_estoque', NULL,
      'stockout_rate_perc', NULL, 'giro_estoque', v_giro, 'dias_cobertura', NULL);

  ELSIF p_dimension = 'supply' THEN
    SELECT COUNT(DISTINCT fc.documento), COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas FROM analytics_v2.fato_transacoes fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id AND fc.tipo_transacao = 'compra' AND dd.data >= v_start;
    v_result := jsonb_build_object('rfqs_abertas', v_rfqs, 'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL, 'pos_aprovadas', v_pos_aprovadas);

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;
  RETURN v_result;
END; $function$

;

-- 1b) get_indicators_for_client (4 args, com p_offset_days)
CREATE OR REPLACE FUNCTION analytics_v2.get_indicators_for_client(p_client_id uuid, p_dimension text, p_period text DEFAULT '30d'::text, p_offset_days integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_days      int;
  v_end       date;
  v_start     date;
  v_prev_start date;
  v_result    jsonb := '{}'::jsonb;

  v_receita       numeric;
  v_prev_receita  numeric;
  v_pedidos       bigint;
  v_ticket        numeric;
  v_clientes_ativos bigint;
  v_novos_clientes  bigint;
  v_recorrentes     bigint;
  v_skus_ativos   bigint;
  v_giro          numeric;
  v_rfqs          bigint;
  v_pos_aprovadas bigint;
BEGIN
  v_days       := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_end        := CURRENT_DATE - (p_offset_days * INTERVAL '1 day')::interval;
  v_start      := v_end      - (v_days        * INTERVAL '1 day')::interval;
  v_prev_start := v_start    - (v_days        * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;

    v_result := jsonb_build_object(
      'receita_liquida',         v_receita,
      'custo_total',             NULL,
      'margem_bruta_perc',       NULL,
      'ticket_medio',            v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2)
        ELSE NULL END
    );

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
        AND dd.data >= v_start AND dd.data <= v_end
      GROUP BY ft.customer_id
      HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;

    v_result := jsonb_build_object(
      'total_pedidos',        v_pedidos,
      'ticket_medio',         v_ticket,
      'novos_clientes',       v_novos_clientes,
      'clientes_ativos',      v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END
    );

  ELSIF p_dimension = 'inventory' THEN
    -- dim_inventory is a current-state snapshot (no time-series), offset has no effect
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2)
    INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory
    WHERE client_id = p_client_id AND dias_recencia <= 90;

    v_result := jsonb_build_object(
      'skus_ativos',       v_skus_ativos,
      'skus_sem_estoque',  NULL,
      'stockout_rate_perc', NULL,
      'giro_estoque',      v_giro,
      'dias_cobertura',    NULL
    );

  ELSIF p_dimension = 'supply' THEN
    SELECT
      COUNT(DISTINCT fc.documento),
      COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas
    FROM analytics_v2.fato_transacoes fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id AND fc.tipo_transacao = 'compra'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_result := jsonb_build_object(
      'rfqs_abertas',           v_rfqs,
      'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL,
      'pos_aprovadas',          v_pos_aprovadas
    );

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;

  RETURN v_result;
END;
$function$

;

-- 2) offboard_client — sem fato_compras no array
CREATE OR REPLACE FUNCTION public.offboard_client(p_client_id uuid, p_batch_size integer DEFAULT 5000)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_deleted_total int := 0;
    v_batch         int;
    v_report        jsonb := '{}'::jsonb;
    v_big_tables text[] := ARRAY[
        'analytics_v2.dim_inventory',
        'analytics_v2.fato_transacoes',
        'analytics_v2.dim_clientes',
        'analytics_v2.dim_fornecedores',
        'public.client_routine_executions',
        'public.messages',
        'public.frontend_events',
        'public.notifications'
    ];
    v_tbl    text;
    v_schema text;
    v_tname  text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clientes_blu WHERE client_id = p_client_id) THEN
        RETURN jsonb_build_object('error', 'client_not_found', 'client_id', p_client_id);
    END IF;

    FOREACH v_tbl IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_tbl, '.', 1);
        v_tname  := split_part(v_tbl, '.', 2);
        v_deleted_total := 0;

        LOOP
            EXECUTE format(
                'WITH rows AS (
                    SELECT ctid FROM %I.%I
                    WHERE client_id = $1
                    LIMIT $2
                )
                DELETE FROM %I.%I
                WHERE ctid IN (SELECT ctid FROM rows)',
                v_schema, v_tname, v_schema, v_tname
            ) USING p_client_id, p_batch_size;

            GET DIAGNOSTICS v_batch = ROW_COUNT;
            v_deleted_total := v_deleted_total + v_batch;
            EXIT WHEN v_batch < p_batch_size;
        END LOOP;

        v_report := v_report || jsonb_build_object(v_tbl, v_deleted_total);
    END LOOP;

    DELETE FROM clientes_blu WHERE client_id = p_client_id;
    v_report := v_report || jsonb_build_object('clientes_blu', 1);

    RETURN jsonb_build_object('status', 'ok', 'client_id', p_client_id, 'deleted', v_report);
END;
$function$

;

-- 3) cron offboard_cleanup_nightly — re-agendado sem fato_compras
select cron.schedule('offboard_cleanup_nightly', '0 3 * * *', $job$
  DO $cleanup$
  DECLARE
    v_id       uuid;
    v_deleted  int;
    v_big_tables text[] := ARRAY[
      'analytics_v2|dim_inventory',
      'analytics_v2|fato_transacoes',
      'analytics_v2|dim_clientes',
      'analytics_v2|dim_fornecedores'
    ];
    v_entry    text;
    v_schema   text;
    v_tbl      text;
  BEGIN
    FOR v_id IN
      SELECT client_id FROM public.clientes_blu
      WHERE deleted_at IS NOT NULL
        AND deleted_at < now() - interval '7 days'
    LOOP
      -- Delete big tables in batches of 5000
      FOREACH v_entry IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_entry, '|', 1);
        v_tbl    := split_part(v_entry, '|', 2);
        LOOP
          EXECUTE format(
            'WITH batch AS (SELECT ctid FROM %I.%I WHERE client_id = $1 LIMIT 5000) '
            'DELETE FROM %I.%I WHERE ctid IN (SELECT ctid FROM batch)',
            v_schema, v_tbl, v_schema, v_tbl
          ) USING v_id;
          GET DIAGNOSTICS v_deleted = ROW_COUNT;
          EXIT WHEN v_deleted = 0;
        END LOOP;
      END LOOP;

      -- Hard delete the tenant row (cascade handles remaining FK children)
      DELETE FROM public.clientes_blu WHERE client_id = v_id;
    END LOOP;
  END
  $cleanup$;
  
\$job$);

COMMIT;
