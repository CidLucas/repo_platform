-- BKL-024: Implement analytics_v2.get_finance_indicators RPC body
--
-- The public wrapper `public.get_finance_indicators(p_period)` exists in the
-- baseline and delegates to `analytics_v2.get_finance_indicators(p_period)`,
-- but that function was never defined — every call returned null, causing the
-- frontend to display `—` for the 5 finance indicators below.
--
-- This migration implements the missing function with:
--   AC1: dso_dias                  = (contas_receber / receita_liquida) * dias_periodo
--   AC2: dpo_dias                  = (contas_pagar / custo_total) * dias_periodo
--   AC3: ccc_dias                  = dso_dias - dpo_dias
--   AC4: working_capital_ratio     = ativo_circulante / passivo_circulante
--   AC5: margem_operacional_perc   = ((receita - custo - despesas) / receita) * 100
--   AC6: Never raises — uses NULLIF, COALESCE and exception swallowing so the
--       RPC always returns a row with `period` populated.

CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(
    receita_liquida numeric, custo_total numeric, margem_bruta_perc numeric,
    margem_operacional_perc numeric, ticket_medio numeric, receita_yoy_perc numeric,
    crescimento_receita_perc numeric, total_pedidos bigint,
    dso_dias numeric, dpo_dias numeric, ccc_dias numeric, working_capital_ratio numeric,
    burn_rate_mensal numeric, runway_meses numeric, cash_flow_30d numeric, period text
)
LANGUAGE plpgsql
AS $function$
DECLARE
    v_receita_liquida numeric;
    v_custo_total numeric;
    v_despesas_operacionais numeric;
    v_contas_receber numeric;
    v_contas_pagar numeric;
    v_ativo_circulante numeric;
    v_passivo_circulante numeric;
    v_dias_periodo integer;
    v_dso_dias numeric;
    v_dpo_dias numeric;
    v_ccc_dias numeric;
    v_working_capital_ratio numeric;
    v_margem_operacional_perc numeric;
BEGIN
    v_dias_periodo := COALESCE(NULLIF(REGEXP_REPLACE(p_period, '[^0-9]', '', 'g'), '')::integer, 30);
    v_receita_liquida := NULL;
    v_custo_total := NULL;
    v_despesas_operacionais := NULL;
    v_contas_receber := NULL;
    v_contas_pagar := NULL;
    v_ativo_circulante := NULL;
    v_passivo_circulante := NULL;

    BEGIN
        SELECT COALESCE(SUM(ft.receita_liquida), 0), COALESCE(SUM(ft.custo_total), 0), COALESCE(SUM(ft.despesas_operacionais), 0)
        INTO v_receita_liquida, v_custo_total, v_despesas_operacionais
        FROM fato_transacoes ft;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    BEGIN
        SELECT COALESCE(SUM(dcr.valor), 0) INTO v_contas_receber
        FROM dim_contas_receber dcr WHERE dcr.status = 'pendente';
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    BEGIN
        SELECT COALESCE(SUM(dcp.valor), 0) INTO v_contas_pagar
        FROM dim_contas_pagar dcp WHERE dcp.status = 'pendente';
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    BEGIN
        SELECT COALESCE(SUM(db.ativo_circulante), 0), COALESCE(SUM(db.passivo_circulante), 0)
        INTO v_ativo_circulante, v_passivo_circulante
        FROM dim_balanco db;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    v_dso_dias := (v_contas_receber / NULLIF(v_receita_liquida, 0)) * v_dias_periodo;
    v_dpo_dias := (v_contas_pagar / NULLIF(v_custo_total, 0)) * v_dias_periodo;
    -- CCC (Cash Conversion Cycle): dso_dias - dpo_dias
    v_ccc_dias := v_dso_dias - v_dpo_dias;
    v_working_capital_ratio := v_ativo_circulante / NULLIF(v_passivo_circulante, 0);
    v_margem_operacional_perc := ((v_receita_liquida - v_custo_total - v_despesas_operacionais) / NULLIF(v_receita_liquida, 0)) * 100;

    RETURN QUERY
    SELECT
        v_receita_liquida, v_custo_total,
        (v_receita_liquida - v_custo_total) / NULLIF(v_receita_liquida, 0) * 100,
        v_margem_operacional_perc,
        NULL::numeric, NULL::numeric, NULL::numeric, NULL::bigint,
        v_dso_dias, v_dpo_dias, v_ccc_dias, v_working_capital_ratio,
        NULL::numeric, NULL::numeric, NULL::numeric,
        p_period::text AS period;
END;
$function$;
