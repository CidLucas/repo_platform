-- sql_table_config: SQL table schema annotations for agent context enrichment.
-- Used by blu_context_service._enrich_data_schema_with_table_schemas() to give agents
-- human-readable column descriptions, enum values, example queries, and join keys.
--
-- client_id = NULL  → global/shared entry (analytics_v2 standard schema, applies to all clients)
-- client_id = <uuid> → per-client override (e.g. BigQuery FDW tables with custom column names)

CREATE TABLE IF NOT EXISTS public.sql_table_config (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       uuid REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
    table_name      text NOT NULL,
    display_name    text,
    description     text,
    is_primary      boolean NOT NULL DEFAULT false,
    column_descriptions jsonb DEFAULT '{}',   -- {"col": "description"}
    enum_values         jsonb DEFAULT '{}',   -- {"col": ["val1", "val2"]}
    example_queries     jsonb DEFAULT '[]',   -- ["SELECT ...", ...]
    join_keys           jsonb DEFAULT '[]',   -- [{"from": "col", "to": "table.col"}]
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- One global entry per table_name (client_id IS NULL)
CREATE UNIQUE INDEX IF NOT EXISTS sql_table_config_global_table_uidx
    ON public.sql_table_config (table_name)
    WHERE client_id IS NULL;

-- One client-specific entry per (client_id, table_name)
CREATE UNIQUE INDEX IF NOT EXISTS sql_table_config_client_table_uidx
    ON public.sql_table_config (client_id, table_name)
    WHERE client_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS sql_table_config_client_id_idx
    ON public.sql_table_config (client_id) WHERE is_active = true;

-- RLS
ALTER TABLE public.sql_table_config ENABLE ROW LEVEL SECURITY;

-- Service role has full access (used by context_service via service key)
CREATE POLICY "service_role_all" ON public.sql_table_config
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated users can read global rows + their own client's rows
CREATE POLICY "client_read_own" ON public.sql_table_config
    FOR SELECT TO authenticated
    USING (
        client_id IS NULL
        OR client_id IN (
            SELECT client_id FROM public.clientes_blu
            WHERE external_user_id = auth.uid()::text
        )
    );

-- Seed: shared analytics_v2 schema annotations (client_id = NULL)
INSERT INTO public.sql_table_config
    (client_id, table_name, display_name, description, is_primary, column_descriptions, join_keys)
VALUES
(NULL, 'analytics_v2.fato_transacoes', 'Transações', 'Tabela de fatos: pedidos de compra e linhas de item. Uma linha por item de pedido.', true,
 '{"transacao_id":"Identificador único da linha","customer_id":"FK para dim_clientes (o cliente que realizou a transação)","fornecedor_id":"FK para dim_fornecedores","data_competencia_id":"FK para dim_datas","documento":"Número do documento/NF","quantidade":"Quantidade pedida","valor_unitario":"Preço unitário","valor":"Valor total da linha","status":"Status: pending, confirmed, delivered, cancelled","created_at":"Data de criação"}',
 '[{"from":"fornecedor_id","to":"analytics_v2.dim_fornecedores.fornecedor_id"},{"from":"data_competencia_id","to":"analytics_v2.dim_datas.data_id"},{"from":"customer_id","to":"analytics_v2.dim_clientes.customer_id"}]'
),
(NULL, 'analytics_v2.dim_clientes', 'Clientes', 'Dimensão de clientes. Cada tenant vê apenas seus próprios clientes via RLS.', false,
 '{"customer_id":"Identificador único do cliente final (BIGINT)","nome":"Razão social ou nome","cpf_cnpj":"CPF ou CNPJ","endereco_cidade":"Cidade","endereco_uf":"Estado","receita_total":"Receita total acumulada","total_pedidos":"Total de pedidos","ticket_medio":"Ticket médio","dias_recencia":"Dias desde a última compra","frequencia_mensal":"Frequência mensal de compras","nivel_cluster":"Nível de cluster (ex: alto, médio, baixo)"}',
 '[]'
),
(NULL, 'analytics_v2.dim_fornecedores', 'Fornecedores', 'Dimensão de fornecedores cadastrados pelo tenant.', false,
 '{"id":"Identificador único","nome":"Nome ou razão social","cnpj":"CNPJ","categoria":"Categoria de produtos","ativo":"Se o fornecedor está ativo"}',
 '[]'
),
(NULL, 'analytics_v2.dim_datas', 'Calendário', 'Dimensão de datas para agrupamentos temporais.', false,
 '{"id":"Data no formato YYYYMMDD","data":"Data completa","ano":"Ano","mes":"Mês (1-12)","trimestre":"Trimestre (1-4)","dia_semana":"Dia da semana (0=domingo)"}',
 '[]'
)
ON CONFLICT DO NOTHING;
