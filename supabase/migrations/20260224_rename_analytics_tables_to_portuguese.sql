-- Migration: Rename analytics_v2 tables to Portuguese
-- This migration consolidates the schema by:
-- 1. Renaming dim_* tables and fact_sales to Portuguese names
-- 2. Renaming columns to Portuguese
-- 3. Creating compras table from erp_purchase_orders
-- 4. Dropping redundant erp_* views
-- 5. Updating RLS policies and indexes

BEGIN;

-- =============================================================================
-- PHASE 1: Drop Redundant Views (They're just Portuguese aliases)
-- =============================================================================

DROP VIEW IF EXISTS analytics_v2.erp_clientes CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_fornecedores CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_produtos CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_pedidos CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_pedidos_recentes CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_transacoes CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_itens_pedido CASCADE;
DROP VIEW IF EXISTS analytics_v2.erp_resumo_dashboard CASCADE;

-- Drop analytics views that will be recreated with new table names
DROP VIEW IF EXISTS analytics_v2.v_time_series CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_last_orders CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_customer_products CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_regional CASCADE;

-- =============================================================================
-- PHASE 2: Drop existing RLS policies before renaming
-- =============================================================================

DROP POLICY IF EXISTS dim_customer_client_isolation ON analytics_v2.dim_customer;
DROP POLICY IF EXISTS dim_supplier_client_isolation ON analytics_v2.dim_supplier;
DROP POLICY IF EXISTS dim_product_client_isolation ON analytics_v2.dim_product;
DROP POLICY IF EXISTS fact_sales_client_isolation ON analytics_v2.fact_sales;

-- =============================================================================
-- PHASE 3: Rename Tables
-- =============================================================================

-- dim_customer → clientes
ALTER TABLE analytics_v2.dim_customer RENAME TO clientes;

-- dim_supplier → fornecedores  
ALTER TABLE analytics_v2.dim_supplier RENAME TO fornecedores;

-- dim_product → produtos
ALTER TABLE analytics_v2.dim_product RENAME TO produtos;

-- dim_date → datas
ALTER TABLE analytics_v2.dim_date RENAME TO datas;

-- fact_sales → vendas
ALTER TABLE analytics_v2.fact_sales RENAME TO vendas;

-- =============================================================================
-- PHASE 4: Rename Columns to Portuguese
-- =============================================================================

-- clientes (formerly dim_customer)
ALTER TABLE analytics_v2.clientes RENAME COLUMN customer_id TO cliente_id;
ALTER TABLE analytics_v2.clientes RENAME COLUMN name TO nome;
ALTER TABLE analytics_v2.clientes RENAME COLUMN total_orders TO total_pedidos;
ALTER TABLE analytics_v2.clientes RENAME COLUMN total_revenue TO receita_total;
ALTER TABLE analytics_v2.clientes RENAME COLUMN avg_order_value TO ticket_medio;
ALTER TABLE analytics_v2.clientes RENAME COLUMN total_quantity TO quantidade_total;
ALTER TABLE analytics_v2.clientes RENAME COLUMN orders_last_30_days TO pedidos_ultimos_30_dias;
ALTER TABLE analytics_v2.clientes RENAME COLUMN frequency_per_month TO frequencia_mensal;
ALTER TABLE analytics_v2.clientes RENAME COLUMN recency_days TO dias_recencia;
ALTER TABLE analytics_v2.clientes RENAME COLUMN lifetime_start_date TO data_primeira_compra;
ALTER TABLE analytics_v2.clientes RENAME COLUMN lifetime_end_date TO data_ultima_compra;
ALTER TABLE analytics_v2.clientes RENAME COLUMN created_at TO criado_em;
ALTER TABLE analytics_v2.clientes RENAME COLUMN updated_at TO atualizado_em;
ALTER TABLE analytics_v2.clientes RENAME COLUMN cluster_score TO pontuacao_cluster;
ALTER TABLE analytics_v2.clientes RENAME COLUMN cluster_tier TO nivel_cluster;

-- fornecedores (formerly dim_supplier)
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN supplier_id TO fornecedor_id;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN name TO nome;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN total_orders_received TO total_pedidos_recebidos;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN total_revenue TO receita_total;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN avg_order_value TO ticket_medio;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN total_products_supplied TO total_produtos_fornecidos;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN frequency_per_month TO frequencia_mensal;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN recency_days TO dias_recencia;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN first_transaction_date TO data_primeira_transacao;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN last_transaction_date TO data_ultima_transacao;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN created_at TO criado_em;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN updated_at TO atualizado_em;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN cluster_score TO pontuacao_cluster;
ALTER TABLE analytics_v2.fornecedores RENAME COLUMN cluster_tier TO nivel_cluster;

-- produtos (formerly dim_product)
ALTER TABLE analytics_v2.produtos RENAME COLUMN product_id TO produto_id;
ALTER TABLE analytics_v2.produtos RENAME COLUMN product_name TO nome;
ALTER TABLE analytics_v2.produtos RENAME COLUMN total_quantity_sold TO quantidade_total_vendida;
ALTER TABLE analytics_v2.produtos RENAME COLUMN total_revenue TO receita_total;
ALTER TABLE analytics_v2.produtos RENAME COLUMN avg_price TO preco_medio;
ALTER TABLE analytics_v2.produtos RENAME COLUMN number_of_orders TO total_pedidos;
ALTER TABLE analytics_v2.produtos RENAME COLUMN avg_quantity_per_order TO quantidade_media_por_pedido;
ALTER TABLE analytics_v2.produtos RENAME COLUMN frequency_per_month TO frequencia_mensal;
ALTER TABLE analytics_v2.produtos RENAME COLUMN recency_days TO dias_recencia;
ALTER TABLE analytics_v2.produtos RENAME COLUMN last_sale_date TO data_ultima_venda;
ALTER TABLE analytics_v2.produtos RENAME COLUMN created_at TO criado_em;
ALTER TABLE analytics_v2.produtos RENAME COLUMN updated_at TO atualizado_em;
ALTER TABLE analytics_v2.produtos RENAME COLUMN cluster_score TO pontuacao_cluster;
ALTER TABLE analytics_v2.produtos RENAME COLUMN cluster_tier TO nivel_cluster;

-- datas (formerly dim_date)
ALTER TABLE analytics_v2.datas RENAME COLUMN date_id TO data_id;
ALTER TABLE analytics_v2.datas RENAME COLUMN date TO data;
ALTER TABLE analytics_v2.datas RENAME COLUMN year TO ano;
ALTER TABLE analytics_v2.datas RENAME COLUMN iso_year TO ano_iso;
ALTER TABLE analytics_v2.datas RENAME COLUMN quarter TO trimestre;
ALTER TABLE analytics_v2.datas RENAME COLUMN quarter_name TO nome_trimestre;
ALTER TABLE analytics_v2.datas RENAME COLUMN month TO mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN month_name TO nome_mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN day TO dia;
ALTER TABLE analytics_v2.datas RENAME COLUMN day_of_year TO dia_do_ano;
ALTER TABLE analytics_v2.datas RENAME COLUMN week_of_year_iso TO semana_do_ano;
ALTER TABLE analytics_v2.datas RENAME COLUMN day_of_week TO dia_da_semana;
ALTER TABLE analytics_v2.datas RENAME COLUMN day_name TO nome_dia;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_weekend TO e_fim_de_semana;
ALTER TABLE analytics_v2.datas RENAME COLUMN first_day_of_month TO primeiro_dia_mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN last_day_of_month TO ultimo_dia_mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_month_start TO e_inicio_mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_month_end TO e_fim_mes;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_quarter_start TO e_inicio_trimestre;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_quarter_end TO e_fim_trimestre;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_year_start TO e_inicio_ano;
ALTER TABLE analytics_v2.datas RENAME COLUMN is_year_end TO e_fim_ano;

-- vendas (formerly fact_sales)
ALTER TABLE analytics_v2.vendas RENAME COLUMN sale_id TO venda_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN customer_id TO cliente_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN supplier_id TO fornecedor_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN product_id TO produto_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN order_id TO pedido_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN customer_cpf_cnpj TO cliente_cpf_cnpj;
ALTER TABLE analytics_v2.vendas RENAME COLUMN supplier_cnpj TO fornecedor_cnpj;
ALTER TABLE analytics_v2.vendas RENAME COLUMN created_at TO criado_em;
ALTER TABLE analytics_v2.vendas RENAME COLUMN updated_at TO atualizado_em;
ALTER TABLE analytics_v2.vendas RENAME COLUMN date_id TO data_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN time_id TO hora_id;
ALTER TABLE analytics_v2.vendas RENAME COLUMN line_item_sequence TO sequencia_item;

-- =============================================================================
-- PHASE 5: Create compras table (purchases FROM suppliers)
-- =============================================================================

CREATE TABLE analytics_v2.compras (
    compra_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    pedido_compra_id UUID REFERENCES analytics_v2.erp_purchase_orders(purchase_order_id),
    fornecedor_id UUID NOT NULL,
    produto_id UUID NOT NULL,
    numero_pedido TEXT,
    data_pedido DATE NOT NULL,
    data_entrega_prevista DATE,
    quantidade_pedida NUMERIC NOT NULL,
    quantidade_recebida NUMERIC DEFAULT 0,
    valor_unitario NUMERIC NOT NULL,
    valor_total NUMERIC NOT NULL,
    status TEXT DEFAULT 'pendente',
    sequencia_item INTEGER DEFAULT 1,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

-- Migrate data from erp_purchase_order_items + erp_purchase_orders
INSERT INTO analytics_v2.compras (
    client_id,
    pedido_compra_id,
    fornecedor_id,
    produto_id,
    numero_pedido,
    data_pedido,
    data_entrega_prevista,
    quantidade_pedida,
    quantidade_recebida,
    valor_unitario,
    valor_total,
    status,
    sequencia_item,
    criado_em,
    atualizado_em
)
SELECT 
    poi.client_id,
    poi.purchase_order_id,
    po.supplier_id,
    poi.product_id,
    po.order_number,
    po.order_date,
    po.expected_delivery_date,
    poi.quantity_ordered,
    poi.quantity_received,
    poi.unit_price,
    poi.total_price,
    po.status,
    poi.line_number,
    poi.created_at,
    poi.updated_at
FROM analytics_v2.erp_purchase_order_items poi
JOIN analytics_v2.erp_purchase_orders po ON poi.purchase_order_id = po.purchase_order_id;

-- Create indexes for compras
CREATE INDEX idx_compras_client_id ON analytics_v2.compras(client_id);
CREATE INDEX idx_compras_fornecedor_id ON analytics_v2.compras(fornecedor_id);
CREATE INDEX idx_compras_produto_id ON analytics_v2.compras(produto_id);
CREATE INDEX idx_compras_data_pedido ON analytics_v2.compras(data_pedido);

-- Enable RLS on compras
ALTER TABLE analytics_v2.compras ENABLE ROW LEVEL SECURITY;

CREATE POLICY compras_client_isolation ON analytics_v2.compras
    FOR ALL
    USING (client_id = COALESCE(current_setting('app.current_cliente_id', true), '00000000-0000-0000-0000-000000000000'));

-- =============================================================================
-- PHASE 6: Re-create RLS policies with new table names
-- =============================================================================

CREATE POLICY clientes_client_isolation ON analytics_v2.clientes
    FOR ALL
    USING (client_id = COALESCE(current_setting('app.current_cliente_id', true), '00000000-0000-0000-0000-000000000000'));

CREATE POLICY fornecedores_client_isolation ON analytics_v2.fornecedores
    FOR ALL
    USING (client_id = COALESCE(current_setting('app.current_cliente_id', true), '00000000-0000-0000-0000-000000000000'));

CREATE POLICY produtos_client_isolation ON analytics_v2.produtos
    FOR ALL
    USING (client_id = COALESCE(current_setting('app.current_cliente_id', true), '00000000-0000-0000-0000-000000000000'));

CREATE POLICY vendas_client_isolation ON analytics_v2.vendas
    FOR ALL
    USING (client_id = COALESCE(current_setting('app.current_cliente_id', true), '00000000-0000-0000-0000-000000000000'));

-- =============================================================================
-- PHASE 7: Recreate Analytics Views with new table/column names
-- =============================================================================

-- Time series view for dashboard charts
CREATE OR REPLACE VIEW analytics_v2.v_series_temporal AS
SELECT v.client_id,
    'fornecedores_no_tempo'::text AS tipo_grafico,
    'fornecedores'::text AS dimensao,
    to_char(v.data_transacao, 'YYYY-MM') AS periodo,
    (date_trunc('month', v.data_transacao))::date AS data_periodo,
    count(DISTINCT v.fornecedor_cnpj) AS total
FROM analytics_v2.vendas v
WHERE v.data_transacao IS NOT NULL
GROUP BY v.client_id, to_char(v.data_transacao, 'YYYY-MM'), (date_trunc('month', v.data_transacao))::date
UNION ALL
SELECT v.client_id,
    'clientes_no_tempo'::text AS tipo_grafico,
    'clientes'::text AS dimensao,
    to_char(v.data_transacao, 'YYYY-MM') AS periodo,
    (date_trunc('month', v.data_transacao))::date AS data_periodo,
    count(DISTINCT v.cliente_cpf_cnpj) AS total
FROM analytics_v2.vendas v
WHERE v.data_transacao IS NOT NULL
GROUP BY v.client_id, to_char(v.data_transacao, 'YYYY-MM'), (date_trunc('month', v.data_transacao))::date
UNION ALL
SELECT v.client_id,
    'produtos_no_tempo'::text AS tipo_grafico,
    'produtos'::text AS dimensao,
    to_char(v.data_transacao, 'YYYY-MM') AS periodo,
    (date_trunc('month', v.data_transacao))::date AS data_periodo,
    count(DISTINCT v.produto_id) AS total
FROM analytics_v2.vendas v
WHERE v.data_transacao IS NOT NULL
GROUP BY v.client_id, to_char(v.data_transacao, 'YYYY-MM'), (date_trunc('month', v.data_transacao))::date
UNION ALL
SELECT v.client_id,
    'pedidos_no_tempo'::text AS tipo_grafico,
    'pedidos'::text AS dimensao,
    to_char(v.data_transacao, 'YYYY-MM') AS periodo,
    (date_trunc('month', v.data_transacao))::date AS data_periodo,
    count(DISTINCT v.pedido_id) AS total
FROM analytics_v2.vendas v
WHERE v.data_transacao IS NOT NULL
GROUP BY v.client_id, to_char(v.data_transacao, 'YYYY-MM'), (date_trunc('month', v.data_transacao))::date
UNION ALL
SELECT v.client_id,
    'receita_no_tempo'::text AS tipo_grafico,
    'receita'::text AS dimensao,
    to_char(v.data_transacao, 'YYYY-MM') AS periodo,
    (date_trunc('month', v.data_transacao))::date AS data_periodo,
    COALESCE(sum(v.valor_total), 0)::bigint AS total
FROM analytics_v2.vendas v
WHERE v.data_transacao IS NOT NULL
GROUP BY v.client_id, to_char(v.data_transacao, 'YYYY-MM'), (date_trunc('month', v.data_transacao))::date;

-- Last orders view
CREATE OR REPLACE VIEW analytics_v2.v_ultimos_pedidos AS
WITH resumo_pedido AS (
    SELECT v.client_id,
        v.pedido_id,
        v.data_transacao,
        v.cliente_cpf_cnpj,
        max(c.nome) AS nome_cliente,
        sum(v.valor_total) AS valor_pedido,
        count(*) AS qtd_produtos,
        row_number() OVER (PARTITION BY v.client_id ORDER BY v.data_transacao DESC, v.pedido_id DESC) AS ordem
    FROM analytics_v2.vendas v
    LEFT JOIN analytics_v2.clientes c ON v.cliente_cpf_cnpj = c.cpf_cnpj AND v.client_id = c.client_id
    WHERE v.data_transacao IS NOT NULL
    GROUP BY v.client_id, v.pedido_id, v.data_transacao, v.cliente_cpf_cnpj
)
SELECT client_id,
    pedido_id,
    data_transacao,
    cliente_cpf_cnpj,
    nome_cliente,
    valor_pedido,
    qtd_produtos,
    ordem
FROM resumo_pedido
WHERE ordem <= 100;

-- Customer products view
CREATE OR REPLACE VIEW analytics_v2.v_produtos_por_cliente AS
SELECT v.client_id,
    v.cliente_cpf_cnpj,
    c.nome AS nome_cliente,
    p.nome AS nome_produto,
    sum(v.quantidade) AS quantidade_total,
    sum(v.valor_total) AS valor_total,
    count(DISTINCT v.pedido_id) AS num_compras,
    max(v.data_transacao) AS ultima_compra
FROM analytics_v2.vendas v
LEFT JOIN analytics_v2.clientes c ON v.cliente_cpf_cnpj = c.cpf_cnpj AND v.client_id = c.client_id
LEFT JOIN analytics_v2.produtos p ON v.produto_id = p.produto_id AND v.client_id = p.client_id
WHERE v.cliente_cpf_cnpj IS NOT NULL AND v.produto_id IS NOT NULL
GROUP BY v.client_id, v.cliente_cpf_cnpj, c.nome, p.nome;

-- Regional distribution view
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
    SELECT v.client_id,
        COALESCE(c.endereco_uf, 'Não informado') AS estado,
        COALESCE(sr.nome_regiao, 'Não informado') AS regiao,
        count(DISTINCT v.pedido_id) AS total
    FROM analytics_v2.vendas v
    LEFT JOIN analytics_v2.clientes c ON v.cliente_cpf_cnpj = c.cpf_cnpj AND v.client_id = c.client_id
    LEFT JOIN estado_para_regiao sr ON c.endereco_uf = sr.sigla_estado
    GROUP BY v.client_id, c.endereco_uf, sr.nome_regiao
),
totais_cliente AS (
    SELECT client_id, sum(total) AS total_geral
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

-- Dashboard summary view
CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard AS
SELECT 
    current_setting('app.current_cliente_id', true) AS client_id,
    (SELECT count(*) FROM analytics_v2.clientes 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS total_clientes,
    (SELECT count(*) FROM analytics_v2.fornecedores 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS total_fornecedores,
    (SELECT count(*) FROM analytics_v2.produtos 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS total_produtos,
    (SELECT count(DISTINCT pedido_id) FROM analytics_v2.vendas 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS total_pedidos,
    (SELECT COALESCE(sum(valor_total), 0) FROM analytics_v2.vendas 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS receita_total,
    (SELECT COALESCE(avg(valor_total), 0) FROM analytics_v2.vendas 
     WHERE client_id = current_setting('app.current_cliente_id', true)) AS ticket_medio,
    now() AS gerado_em;

-- =============================================================================
-- PHASE 8: Update indexes to match new column names
-- =============================================================================

-- Note: PostgreSQL automatically renames indexes when columns are renamed,
-- but we should ensure proper naming for clarity

-- Drop old indexes if they exist with old naming
DROP INDEX IF EXISTS analytics_v2.idx_dim_customer_client_id;
DROP INDEX IF EXISTS analytics_v2.idx_dim_supplier_client_id;
DROP INDEX IF EXISTS analytics_v2.idx_dim_product_client_id;
DROP INDEX IF EXISTS analytics_v2.idx_fact_sales_client_id;

-- Create indexes with Portuguese names (if not auto-renamed)
CREATE INDEX IF NOT EXISTS idx_clientes_client_id ON analytics_v2.clientes(client_id);
CREATE INDEX IF NOT EXISTS idx_clientes_cpf_cnpj ON analytics_v2.clientes(cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_fornecedores_client_id ON analytics_v2.fornecedores(client_id);
CREATE INDEX IF NOT EXISTS idx_fornecedores_cnpj ON analytics_v2.fornecedores(cnpj);
CREATE INDEX IF NOT EXISTS idx_produtos_client_id ON analytics_v2.produtos(client_id);
CREATE INDEX IF NOT EXISTS idx_vendas_client_id ON analytics_v2.vendas(client_id);
CREATE INDEX IF NOT EXISTS idx_vendas_cliente_id ON analytics_v2.vendas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_vendas_fornecedor_id ON analytics_v2.vendas(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_vendas_produto_id ON analytics_v2.vendas(produto_id);
CREATE INDEX IF NOT EXISTS idx_vendas_pedido_id ON analytics_v2.vendas(pedido_id);
CREATE INDEX IF NOT EXISTS idx_vendas_data_transacao ON analytics_v2.vendas(data_transacao);

-- =============================================================================
-- PHASE 9: Add comments for documentation
-- =============================================================================

COMMENT ON TABLE analytics_v2.clientes IS 'Dimensão de clientes - compradores finais dos produtos';
COMMENT ON TABLE analytics_v2.fornecedores IS 'Dimensão de fornecedores - quem fornece produtos';
COMMENT ON TABLE analytics_v2.produtos IS 'Dimensão de produtos - itens vendidos';
COMMENT ON TABLE analytics_v2.datas IS 'Dimensão de datas - calendário para análises temporais';
COMMENT ON TABLE analytics_v2.vendas IS 'Fato de vendas - transações de venda para clientes';
COMMENT ON TABLE analytics_v2.compras IS 'Fato de compras - transações de compra de fornecedores';

COMMIT;
