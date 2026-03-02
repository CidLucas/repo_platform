Pipeline Migration: Deprecate APIs, Move to Supabase-Only
Context
The data ingestion and analytics APIs are being deprecated. The dashboard currently can't access data because:

The database has been migrated to a new normalized schema (fato_transacoes + new dim tables) but all code still references the old vendas/fcx_vendas table with old column names
The views (v_series_temporal, v_ultimos_pedidos, etc.) still query the old tables
The analyticsService.ts queries fcx_vendas which no longer exists
The connectorService.ts calls the Data Ingestion API which is being deprecated
Target architecture: Frontend -> Supabase (FDW + RPCs + Edge Functions + PostgREST) -> Dashboard

Pipeline Flow (Revised - No Staging Table)
User enters database info on "Fonte de Dados" page
Frontend calls Supabase RPCs to create FDW server + foreign table (user chooses which table holds their data)
Frontend discovers source column names from the foreign table
match-columns edge function maps source columns -> canonical column names
User reviews/confirms mapping on AdminConnectorMappingPage
Frontend calls sincronizar_dados_cliente RPC which:
Reads from the foreign table using the column_mapping
Upserts dimensions first (dim_clientes, dim_fornecedores, dim_produtos, dim_datas)
Then inserts into fato_transacoes with FK resolution via JOINs to dimensions
Runs atualizar_agregados to refresh dimension metrics
Dashboard reads from PostgREST (views + dimension tables)
Why no staging table: The FDW foreign table IS the staging. We read from it and write directly to final tables in a single SQL function. The column_mapping JSONB (from match-columns) drives dynamic SQL. Dimensions are populated first so FK resolution works.

Implementation Plan
Phase 1: SQL Migrations (Foundation)
1.1 Sync + Transform function (direct FDW → dimensions → fato)
New file: supabase/migrations/20260226_pipeline_v2.sql

Prerequisites - ensure these exist:

Unique constraints: dim_clientes(client_id, cpf_cnpj), dim_fornecedores(client_id, cnpj), dim_produtos(client_id, nome)
Seed dim_tipo_transacao with default entry (tipo_id=1, codigo='venda', categoria='entrada')
Rewrite sincronizar_dados_cliente(p_client_id, p_credential_id, p_force_full_sync):
The function receives column_mapping JSONB from client_data_sources table. This mapping has the form { "source_col": "canonical_col" } (e.g. {"emitterlegalname": "fornecedor_nome", "receiverlegaldoc": "cliente_cpf_cnpj", ...}).

The function builds dynamic SQL to:

Upsert dim_clientes: Extract columns mapped to cliente_* canonical names from the foreign table → INSERT INTO dim_clientes ON CONFLICT DO UPDATE
Upsert dim_fornecedores: Extract columns mapped to fornecedor_* canonical names → INSERT INTO dim_fornecedores ON CONFLICT DO UPDATE
Upsert dim_produtos: Extract columns mapped to produto_descricao → INSERT INTO dim_produtos ON CONFLICT DO NOTHING
Populate dim_datas: Extract mapped data_transacao column → INSERT INTO dim_datas ON CONFLICT DO NOTHING
Insert fato_transacoes: Read from foreign table, JOIN dim tables for FK resolution:
data_transacao::date → JOIN dim_datas → data_competencia_id
cliente_cpf_cnpj → JOIN dim_clientes → cliente_id
fornecedor_cnpj → JOIN dim_fornecedores → fornecedor_id
produto_descricao → JOIN dim_produtos → produto_id
pedido_id → documento
valor_total → valor
quantidade, valor_unitario pass through
Log to connector_sync_history
Canonical → Destination mapping (hardcoded in function, the dynamic part is source → canonical):


cliente_cpf_cnpj    → dim_clientes.cpf_cnpj
cliente_nome        → dim_clientes.nome
cliente_telefone    → dim_clientes.telefone
cliente_rua         → dim_clientes.endereco_rua
cliente_numero      → dim_clientes.endereco_numero
cliente_bairro      → dim_clientes.endereco_bairro
cliente_cidade      → dim_clientes.endereco_cidade
cliente_uf          → dim_clientes.endereco_uf
cliente_cep         → dim_clientes.endereco_cep
fornecedor_cnpj     → dim_fornecedores.cnpj
fornecedor_nome     → dim_fornecedores.nome
fornecedor_telefone → dim_fornecedores.telefone
fornecedor_cidade   → dim_fornecedores.endereco_cidade
fornecedor_uf       → dim_fornecedores.endereco_uf
produto_descricao   → dim_produtos.nome
data_transacao      → dim_datas lookup → fato_transacoes.data_competencia_id
pedido_id           → fato_transacoes.documento
quantidade          → fato_transacoes.quantidade
valor_unitario      → fato_transacoes.valor_unitario
valor_total         → fato_transacoes.valor
status              → fato_transacoes.status
Rewrite atualizar_agregados(p_client_id):

All CTEs read from fato_transacoes instead of vendas
Join dim_datas for date calculations (instead of data_transacao column)
Join dim_clientes via ft.cliente_id = dc.cliente_id (instead of cliente_cpf_cnpj)
Join dim_fornecedores via ft.fornecedor_id = df.fornecedor_id (instead of fornecedor_cnpj)
Replace valor_total → valor, pedido_id → documento
1.2 Update views for fato_transacoes
New file: supabase/migrations/20260226_update_views_fato_transacoes.sql

Replace all 4 views to query fato_transacoes with JOINs:

v_series_temporal: JOIN dim_datas dd ON ft.data_competencia_id = dd.data_id, use dd.data for date grouping, ft.valor for revenue, JOIN dim_clientes/fornecedores/produtos via UUID FKs for distinct counts
v_ultimos_pedidos: JOIN fato_transacoes with dim_datas + dim_clientes, alias ft.documento AS pedido_id, dd.data AS data_transacao, dc.cpf_cnpj AS cliente_cpf_cnpj (keep view output columns compatible with frontend)
v_distribuicao_regional: JOIN fato_transacoes with dim_clientes via ft.cliente_id = dc.cliente_id for endereco_uf
v_resumo_dashboard: Count from fato_transacoes using get_my_client_id() for RLS, count(DISTINCT documento) for pedidos, sum(valor) for receita
Important: View output columns stay compatible with the existing analyticsService.ts view-based queries (same column names, same types).

Phase 2: Edge Function Update
File: supabase/functions/match-columns/index.ts

Add fato_transacoes to SchemaType union and CANONICAL_SCHEMAS with normalized column names (documento, valor, tipo_id, etc.)
Add SCHEMA_CONTEXT_DEFAULTS for fato_transacoes
The existing invoices schema type already maps source columns to canonical names that work perfectly as intermediate mapping. No changes needed to invoices schema - it maps to canonical names like cliente_cpf_cnpj, fornecedor_nome, valor_total etc. which the sync function knows how to route to the right dimension/fact tables.
The user selects their source table; the frontend sends the column names to match-columns with schema_type: "invoices" (or whichever preset best matches their data shape)
Phase 3: Frontend Updates
3.1 analyticsService.ts
File: apps/vizu_dashboard/src/services/analyticsService.ts

View-based queries (getPedidosOverview, getFornecedores, getClientes, getProdutosOverview, getHomeMetrics, all indicators) - minimal changes needed since views keep compatible output columns.

Cross-analysis queries need rewriting (8 functions) - replace fcx_vendas with fato_transacoes and use PostgREST FK disambiguation:


// Example: getPedidoDetails
const { data } = await supabase
  .schema(ANALYTICS_SCHEMA)
  .from('fato_transacoes')
  .select(`
    documento,
    valor,
    quantidade,
    valor_unitario,
    dim_clientes(nome, cpf_cnpj, telefone, endereco_uf, endereco_cidade),
    dim_produtos(nome),
    dim_datas!data_competencia_id(data)
  `)
  .eq('documento', order_id);

// For getCustomersByProduct - multiple FK disambiguation
.from('fato_transacoes')
.select(`
  valor, quantidade,
  dim_clientes!inner(cpf_cnpj, nome, receita_total),
  dim_produtos!inner(nome)
`)
.eq('dim_produtos.nome', productName)

// For queries filtering by customer cpf_cnpj - resolve FK first:
const { data: customer } = await supabase.schema(ANALYTICS_SCHEMA)
  .from('dim_clientes').select('cliente_id').eq('cpf_cnpj', cpfCnpj).single();
const { data } = await supabase.schema(ANALYTICS_SCHEMA)
  .from('fato_transacoes').select('...').eq('cliente_id', customer.cliente_id);
Functions to rewrite:

getPedidoDetails: fcx_vendas -> fato_transacoes + dim JOINs + dim_datas!data_competencia_id disambiguation
getCustomersByProduct: fato_transacoes with dim_produtos!inner and dim_clientes!inner
getProductsByCustomer: resolve cpf_cnpj -> cliente_id, then query fato_transacoes
getCustomerMonthlyOrders: fato_transacoes with dim_datas!data_competencia_id for dates
getCustomersBySupplier: resolve cnpj -> fornecedor_id, then query fato_transacoes
getProductsBySupplier: same resolve pattern
getSuppliersByProduct: fato_transacoes with dim_fornecedores!inner and dim_produtos!inner
Column mapping: pedido_id -> documento, valor_total -> valor, data_transacao -> dim_datas!data_competencia_id.data, cliente_cpf_cnpj -> dim_clientes.cpf_cnpj, fornecedor_cnpj -> dim_fornecedores.cnpj

3.2 connectorService.ts
File: apps/vizu_dashboard/src/services/connectorService.ts

Remove all fetch() calls to Data Ingestion API. Replace with Supabase RPCs:

testConnection -> supabase.rpc('validate_bigquery_connection', ...) (FDW function already exists)
createCredential -> supabase.rpc('create_bigquery_server', ...) + insert into credencial_servico_externo (FDW + Vault already set up)
startSync -> supabase.rpc('sincronizar_dados_cliente', ...)
getSyncStatus -> supabase.from('connector_sync_history').select('*').eq('id', jobId)
listConnections -> supabase.from('credencial_servico_externo').select('*').eq('client_id', id)
deleteConnection -> supabase.rpc('drop_bigquery_server', ...) + delete from credencial
Remove API_BASE_URL constant and VITE_DATA_INGESTION_API_URL dependency
3.3 connectorStatusService.ts
File: apps/vizu_dashboard/src/services/connectorStatusService.ts

Replace all external API calls with Supabase PostgREST queries:

getConnectorStatus -> query credencial_servico_externo with nested connector_sync_history via FK join
getSyncHistory -> query connector_sync_history ordered by date
getDashboardStats -> aggregate from credencial_servico_externo
startSyncJob -> supabase.rpc('sincronizar_dados_cliente', ...)
3.4 AdminConnectorMappingPage.tsx
File: apps/vizu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx

Update CANONICAL_COLUMNS dictionary to show all mappable canonical columns (the ones the sync function knows how to route):

pedido_id, data_transacao, quantidade, valor_unitario, valor_total, status,
cliente_cpf_cnpj, cliente_nome, cliente_telefone, cliente_rua, cliente_numero,
cliente_bairro, cliente_cidade, cliente_uf, cliente_cep,
fornecedor_cnpj, fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
produto_descricao
Remove old FK UUID columns (venda_id, cliente_id, fornecedor_id, produto_id) from the UI - these are resolved automatically
handleConfirmAndSync already calls sincronizar_dados_cliente via supabase.rpc() - no change needed
3.5 useColumnMatching hook
Update SchemaType to include fato_transacoes
Phase 4: Cleanup
Remove/deprecate VITE_DATA_INGESTION_API_URL and VITE_API_URL_ANALYTICS env vars
Add deprecation notices to services/analytics_api/ and services/data_ingestion_api/
Key Files to Modify
File	Change Type
supabase/migrations/20260226_pipeline_v2.sql	NEW - rewrite sync + transform + aggregation RPCs
supabase/migrations/20260226_update_views_fato_transacoes.sql	NEW - recreate 4 views for fato_transacoes
supabase/functions/match-columns/index.ts	EDIT - add fato_transacoes schema type
apps/vizu_dashboard/src/services/analyticsService.ts	EDIT - rewrite 8 cross-analysis queries
apps/vizu_dashboard/src/services/connectorService.ts	REWRITE - Supabase RPCs instead of API calls
apps/vizu_dashboard/src/services/connectorStatusService.ts	REWRITE - Supabase queries instead of API calls
apps/vizu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx	EDIT - update CANONICAL_COLUMNS
apps/vizu_dashboard/src/hooks/useColumnMatching.ts	EDIT - update SchemaType
Key Supabase Patterns (from docs)
FDW Security: Foreign tables in private schema, accessed via SECURITY DEFINER RPCs only. Never expose foreign tables via PostgREST.
PostgREST FK Disambiguation: fato_transacoes has 3 FKs to dim_datas - must use dim_datas!data_competencia_id(data) syntax in PostgREST select.
RPC for complex logic: sincronizar_dados_cliente encapsulates multi-step ETL as a single RPC call from frontend.
PostgREST for reads: Dashboard queries use PostgREST auto-generated API (views + tables with RLS). No custom API needed.
Vault for credentials: FDW credentials stored in Supabase Vault (already set up for BigQuery).
Verification Plan
SQL: Call sincronizar_dados_cliente with test credential -> verify dim tables populated -> verify fato_transacoes has rows with correct FK references -> query each view -> verify atualizar_agregados updates dimension metrics
Edge function: POST to match-columns with various schema_types -> verify correct mappings
Dashboard: Load each page (home, clientes, fornecedores, produtos, pedidos) -> verify data displays correctly from views
Cross-analysis: Test each rewritten function (getCustomersByProduct, etc.) -> verify PostgREST FK joins work with disambiguation
Full connector flow: Create BigQuery connection -> discover columns -> map columns -> sync -> verify data flows to dashboard
RLS: Verify different users see only their client's data via get_my_client_id()