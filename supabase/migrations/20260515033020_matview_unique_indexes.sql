-- Unique indexes required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_resumo_dashboard_client
  ON analytics_v2.mv_resumo_dashboard (client_id);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_distribuicao_regional_pk
  ON analytics_v2.mv_distribuicao_regional (client_id, endereco_uf, endereco_cidade);
