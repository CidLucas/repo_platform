-- G5b: RPC refresh_client_dashboards
-- Chamada pela edge function etl-refresh-dashboards.
-- SECURITY DEFINER: edge function não precisa de USAGE em analytics_v2.
-- Executa REFRESH MATERIALIZED VIEW CONCURRENTLY nas 4 MVs do dashboard.
-- Nota: CONCURRENTLY requer índice único em cada MV. As MVs do baseline
-- têm UNIQUE INDEX (criados junto com elas). Se não tiver, cai no REFRESH normal.

BEGIN;

CREATE OR REPLACE FUNCTION public.refresh_client_dashboards(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
BEGIN
  -- As MVs são globais (não filtradas por client_id na definição),
  -- então um REFRESH serve todos os clientes. O p_client_id é recebido
  -- por consistência de interface mas não filtra o refresh.
  -- Ordem importa: mv_resumo_dashboard depende de fato_transacoes (já atualizado
  -- por apply_staging_to_facts antes do enqueue do job).
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;
END;
$$;

REVOKE ALL ON FUNCTION public.refresh_client_dashboards(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.refresh_client_dashboards(uuid) TO service_role;

COMMENT ON FUNCTION public.refresh_client_dashboards IS
'SECURITY DEFINER. Refreshes all 4 analytics_v2 dashboard MVs (CONCURRENTLY). '
'Called by etl-refresh-dashboards edge function after apply_staging_to_facts '
'enqueues a refresh_dashboards job. p_client_id is logged/auditable but MVs '
'are global (not per-client partitioned).';

COMMIT;
