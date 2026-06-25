TWO MINIMAL CHANGES ONLY. DO NOT ADD ANYTHING ELSE.

CHANGE 1: Edit supabase/migrations/20260523999999_baseline_v2.sql
Replace the entire get_commercial_top_clients function (lines 2271-2294) with:
```sql
CREATE OR REPLACE FUNCTION public.get_commercial_top_clients(
  p_period text DEFAULT '30d',
  p_limit integer DEFAULT 10
)
RETURNS TABLE(client_id bigint, nome text, receita numeric, pedidos bigint, share_perc numeric, period text)
LANGUAGE plpgsql
AS $function$

BEGIN
  RETURN QUERY
  SELECT
    dc.customer_id,
    dc.nome::TEXT,
    SUM(ft.valor)::NUMERIC AS receita,
    COUNT(ft.transacao_id)::BIGINT AS pedidos,
    ROUND(
      SUM(ft.valor) / NULLIF(SUM(SUM(ft.valor)) OVER (), 0) * 100,
      2
    ) AS share_perc,
    p_period AS period
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON ft.customer_id = dc.customer_id
   AND ft.client_id   = dc.client_id
  WHERE ft.client_id = public.get_my_client_id()
    AND ft.created_at >= now() - p_period::interval
  GROUP BY dc.customer_id, dc.nome
  ORDER BY receita DESC
  LIMIT p_limit;
END;

$function$;
```

CHANGE 2: Edit apps/blu_v3/src/api/analytics.ts
In function getCommercialIndicators, replace line 457:
  const r = await callDimensionRpc<Record<string, unknown>>('get_commercial_indicators', period)
with:
  let r: Record<string, unknown>
  try {
    r = await callDimensionRpc<Record<string, unknown>>('get_commercial_indicators', period)
  } catch (_) {
    r = { period }
  }

IMPORTANT: The catch MUST use catch (_) or catch (e) with parentheses — NOT catch { without parentheses. The test regex requires catch\s*\(.

Then run: pytest tests/behaviors/test_b3_dim_clientes_commercial_indicators.py -v
All 5 tests must pass. Then git add, commit with message "GREEN: dim_clientes commercial indicators - AC2 RPC params + AC4 try/catch fallback", push to origin pr-217.
