-- Fix dim_inventory RLS policy still using deprecated app.current_client_id
-- and recreate missing regional dashboard view.

BEGIN;

ALTER TABLE analytics_v2.dim_inventory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dim_inventory_policy ON analytics_v2.dim_inventory;
DROP POLICY IF EXISTS produtos_client_isolation ON analytics_v2.dim_inventory;

CREATE POLICY dim_inventory_client_isolation ON analytics_v2.dim_inventory
FOR SELECT
USING (client_id = public.get_my_client_id());

CREATE POLICY dim_inventory_service_role_all ON analytics_v2.dim_inventory
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE OR REPLACE VIEW analytics_v2.v_distribuicao_regional AS
WITH estado_para_regiao AS (
    SELECT mapping.sigla_estado, mapping.nome_regiao
    FROM (VALUES
        ('AC','Norte'), ('AM','Norte'), ('AP','Norte'), ('PA','Norte'),
        ('RO','Norte'), ('RR','Norte'), ('TO','Norte'),
        ('AL','Nordeste'), ('BA','Nordeste'), ('CE','Nordeste'), ('MA','Nordeste'),
        ('PB','Nordeste'), ('PE','Nordeste'), ('PI','Nordeste'), ('RN','Nordeste'), ('SE','Nordeste'),
        ('DF','Centro-Oeste'), ('GO','Centro-Oeste'), ('MT','Centro-Oeste'), ('MS','Centro-Oeste'),
        ('ES','Sudeste'), ('MG','Sudeste'), ('RJ','Sudeste'), ('SP','Sudeste'),
        ('PR','Sul'), ('RS','Sul'), ('SC','Sul')
    ) AS mapping(sigla_estado, nome_regiao)
),
totais_regionais AS (
    SELECT ft.client_id,
        COALESCE(dc.endereco_uf, 'Não informado') AS estado,
        COALESCE(sr.nome_regiao, 'Não informado') AS regiao,
        COUNT(DISTINCT ft.documento) AS total
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    LEFT JOIN estado_para_regiao sr ON dc.endereco_uf = sr.sigla_estado
    GROUP BY ft.client_id, dc.endereco_uf, sr.nome_regiao
),
totais_cliente AS (
    SELECT client_id, SUM(total) AS total_geral
    FROM totais_regionais
    GROUP BY client_id
)
SELECT tr.client_id,
    'pedidos_por_regiao'::text AS tipo_grafico,
    'pedidos'::text AS dimensao,
    tr.estado,
    tr.regiao,
    tr.total,
    CASE WHEN tc.total_geral > 0
        THEN (tr.total::numeric / tc.total_geral) * 100
        ELSE 0
    END AS percentual
FROM totais_regionais tr
JOIN totais_cliente tc ON tr.client_id = tc.client_id;

GRANT SELECT ON analytics_v2.v_distribuicao_regional TO authenticated, service_role;
GRANT SELECT ON analytics_v2.dim_inventory TO authenticated;
GRANT ALL ON analytics_v2.dim_inventory TO service_role;

COMMIT;
