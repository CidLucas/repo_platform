-- Migration: Phase 6 — §6 KPI Catalog (Blu MVP roadmap)
-- Date: 2026-04-27
--
-- Implements §6 of `docs/plans/2026-04-26-blu-mvp-roadmap.md`:
-- the canonical KPI catalog plus the per-dimension RPCs that surface every
-- KPI defined in the roadmap. The Per-KPI implementation rule from the
-- roadmap requires:
--   • each KPI is exposed by a stable analytics_v2 contract (one RPC per
--     dimension, one column per KPI), AND
--   • each KPI is described in a tenant-readable catalog so the frontend
--     can render labels/tier-gates/data-availability from a single source
--     of truth (no hard-coded KPI lists in React).
--
-- Outputs of this migration:
--   1. `public.kpi_catalog` — seeded with every §6.1..§6.6 KPI.
--   2. `public.list_kpi_catalog(p_dimension, p_only_enabled)` — tier-aware
--      RPC the dashboard consumes to enumerate KPIs.
--   3. Replaced dimension RPCs returning the full §6 KPI surface (KPIs
--      flagged `data_status='external'` or `'pending_data'` return NULL
--      until the corresponding ingestion lands).
--   4. New `analytics_v2.get_admin_indicators(p_period)` — §6.6.
--   5. New `analytics_v2.get_commercial_revenue_by_channel(p_period)` and
--      `analytics_v2.get_commercial_top_clients(p_period, p_limit)` for
--      the KPIs that are inherently list/groupby (§6.2 "Receita por
--      canal", "Top 10 clientes").
--
-- Tier vocabulary: BASIC | SME | PRO | PREMIUM | ENTERPRISE | ADMIN
-- (canonical list from libs/vizu_agent_framework/src/vizu_agent_framework/approval.py).

BEGIN;

SET LOCAL statement_timeout = '5min';
SET LOCAL lock_timeout       = '1min';

-- ────────────────────────────────────────────────────────────────────────
-- 1. Catalog table + tier rank helper
-- ────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.kpi_catalog (
  slug              text        PRIMARY KEY,
  dimension         text        NOT NULL CHECK (dimension IN
    ('finance','commercial','inventory','supply','marketing','admin')),
  label             text        NOT NULL,
  formula           text        NOT NULL,
  unit              text        NOT NULL DEFAULT 'number'
    CHECK (unit IN ('number','currency','percent','days','hours','ratio','count')),
  is_leading        boolean     NOT NULL DEFAULT false,  -- false → lagging
  tier_required     text        NOT NULL DEFAULT 'BASIC'
    CHECK (tier_required IN ('BASIC','SME','PRO','PREMIUM','ENTERPRISE','ADMIN')),
  data_status       text        NOT NULL DEFAULT 'live'
    CHECK (data_status IN ('live','proxy','external','pending_data')),
  rpc_column        text,        -- column name returned by the dimension RPC
  description       text,
  references_url    text,
  sort_order        integer     NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.kpi_catalog IS
  'Canonical KPI catalog (§6 of Blu MVP roadmap). Every KPI shipped on the dashboard is described here exactly once. data_status: live=ready, proxy=approximation, external=needs ingest connector, pending_data=awaiting upstream EPIC.';

CREATE INDEX IF NOT EXISTS idx_kpi_catalog_dimension
  ON public.kpi_catalog(dimension, sort_order);

ALTER TABLE public.kpi_catalog ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kpi_catalog_read_all ON public.kpi_catalog;
CREATE POLICY kpi_catalog_read_all ON public.kpi_catalog
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS kpi_catalog_service_role ON public.kpi_catalog;
CREATE POLICY kpi_catalog_service_role ON public.kpi_catalog
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Helper: numeric rank for tier comparison so list_kpi_catalog can filter
-- "what does the current tenant have access to?".
CREATE OR REPLACE FUNCTION public.kpi_tier_rank(p_tier text)
RETURNS integer
LANGUAGE sql IMMUTABLE
AS $$
  SELECT CASE upper(coalesce(p_tier, 'BASIC'))
    WHEN 'BASIC'      THEN 10
    WHEN 'SME'        THEN 20
    WHEN 'PRO'        THEN 20
    WHEN 'PREMIUM'    THEN 30
    WHEN 'ENTERPRISE' THEN 40
    WHEN 'ADMIN'      THEN 99
    ELSE 10
  END;
$$;

GRANT EXECUTE ON FUNCTION public.kpi_tier_rank(text) TO authenticated;

-- ────────────────────────────────────────────────────────────────────────
-- 2. Tier-aware lookup RPC
-- ────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.list_kpi_catalog(
  p_dimension     text DEFAULT NULL,
  p_only_enabled  boolean DEFAULT true
)
RETURNS TABLE (
  slug           text,
  dimension      text,
  label          text,
  formula        text,
  unit           text,
  is_leading     boolean,
  tier_required  text,
  data_status    text,
  rpc_column     text,
  description    text,
  references_url text,
  sort_order     integer,
  is_enabled     boolean
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
  WITH me AS (
    SELECT public.kpi_tier_rank(coalesce(c.tier, 'BASIC')) AS rank
    FROM public.clientes_vizu c
    WHERE c.client_id::text = public.get_my_client_id()
    LIMIT 1
  ),
  fallback AS (SELECT public.kpi_tier_rank('BASIC') AS rank)
  SELECT
    k.slug,
    k.dimension,
    k.label,
    k.formula,
    k.unit,
    k.is_leading,
    k.tier_required,
    k.data_status,
    k.rpc_column,
    k.description,
    k.references_url,
    k.sort_order,
    (public.kpi_tier_rank(k.tier_required)
       <= COALESCE((SELECT rank FROM me), (SELECT rank FROM fallback)))
       AND k.data_status IN ('live','proxy')
       AS is_enabled
  FROM public.kpi_catalog k
  WHERE (p_dimension IS NULL OR k.dimension = p_dimension)
    AND (
      NOT p_only_enabled
      OR (
        public.kpi_tier_rank(k.tier_required)
          <= COALESCE((SELECT rank FROM me), (SELECT rank FROM fallback))
        AND k.data_status IN ('live','proxy')
      )
    )
  ORDER BY k.dimension, k.sort_order, k.slug;
$$;

COMMENT ON FUNCTION public.list_kpi_catalog(text, boolean) IS
  'Lists KPIs from §6 catalog filtered by current tenant tier. is_enabled=true when the KPI is both reachable by the tenant tier and has a live/proxy data source. p_only_enabled=false returns the full catalog (useful for upgrade-prompt UX).';

GRANT EXECUTE ON FUNCTION public.list_kpi_catalog(text, boolean) TO authenticated;

-- ────────────────────────────────────────────────────────────────────────
-- 3. Seed §6.1 .. §6.6 catalog rows
-- ────────────────────────────────────────────────────────────────────────

INSERT INTO public.kpi_catalog
  (slug, dimension, label, formula, unit, is_leading, tier_required, data_status, rpc_column, description, sort_order)
VALUES
  -- §6.1 Finance
  ('fin.receita_liquida',          'finance', 'Receita líquida',                'Σ valor onde tipo=receita e status<>cancelled',          'currency', false, 'BASIC',      'live',         'receita_liquida',          'Receita líquida acumulada no período.', 100),
  ('fin.custo_total',              'finance', 'Custo total',                    'Σ valor onde categoria IN (despesa,custo)',              'currency', false, 'BASIC',      'live',         'custo_total',              'COGS + OPEX consolidados.', 110),
  ('fin.margem_bruta_perc',        'finance', 'Margem bruta',                   '(Receita − COGS) / Receita',                              'percent',  false, 'BASIC',      'proxy',        'margem_bruta_perc',        'Aproximada quando COGS não é segregado de OPEX.', 120),
  ('fin.margem_operacional_perc',  'finance', 'Margem operacional',             '(Receita − COGS − OPEX) / Receita',                       'percent',  false, 'BASIC',      'proxy',        'margem_operacional_perc',  'Aproximada quando OPEX não está categorizado.', 130),
  ('fin.ticket_medio',             'finance', 'Ticket médio (AOV)',             'Receita / nº pedidos',                                    'currency', false, 'BASIC',      'live',         'ticket_medio',             'Average order value no período.', 140),
  ('fin.dso',                      'finance', 'DSO — Days Sales Outstanding',   '(AR médio / Receita) × dias',                             'days',     false, 'PRO',        'pending_data', 'dso_dias',                 'Requer ingestão de contas a receber.', 150),
  ('fin.dpo',                      'finance', 'DPO — Days Payable Outstanding', '(AP médio / COGS) × dias',                                'days',     false, 'PRO',        'pending_data', 'dpo_dias',                 'Requer ingestão de contas a pagar.', 160),
  ('fin.ccc',                      'finance', 'Cash Conversion Cycle',          'DIO + DSO − DPO',                                          'days',     false, 'PRO',        'pending_data', 'ccc_dias',                 'Composição (DIO+DSO−DPO).', 170),
  ('fin.working_capital_ratio',    'finance', 'Working Capital Ratio',          'Ativo circulante / Passivo circulante',                   'ratio',    true,  'PRO',        'pending_data', 'working_capital_ratio',    'Liquidez corrente.', 180),
  ('fin.burn_rate_mensal',         'finance', 'Burn rate mensal',               'Σ saídas operacionais / mês',                             'currency', true,  'PRO',        'proxy',        'burn_rate_mensal',         'Aproximado pela média mensal de despesas no período.', 190),
  ('fin.runway_meses',             'finance', 'Runway (meses)',                 'Caixa atual / Burn rate',                                  'number',   true,  'PRO',        'pending_data', 'runway_meses',             'Requer caixa atual ingerido.', 200),
  ('fin.cash_flow_30d',            'finance', 'Fluxo de caixa projetado 30d',   'Σ recebíveis 30d − Σ pagáveis 30d',                       'currency', true,  'PRO',        'pending_data', 'cash_flow_30d',            'Requer transações futuras (data > today).', 210),
  ('fin.receita_yoy_perc',         'finance', 'Receita YoY',                    '(Receita período − Receita período-1A) / período-1A',     'percent',  false, 'BASIC',      'live',         'receita_yoy_perc',         'Crescimento ano contra ano.', 220),
  ('fin.crescimento_receita_perc', 'finance', 'Crescimento de receita (período anterior)', '(Receita atual − Receita anterior) / Receita anterior', 'percent', false, 'BASIC', 'live', 'crescimento_receita_perc', 'Crescimento vs período imediatamente anterior.', 230),
  ('fin.total_pedidos',            'finance', 'Total de pedidos',               'COUNT(DISTINCT documento)',                                'count',    false, 'BASIC',      'live',         'total_pedidos',            'Volume de pedidos no período.', 240),

  -- §6.2 Commercial
  ('com.pedidos_periodo',          'commercial', 'Pedidos no período',          'COUNT(*) WHERE tipo=venda',                                'count',    false, 'BASIC', 'live',  'pedidos_periodo',         'Vendas registradas.', 100),
  ('com.receita_periodo',          'commercial', 'Receita do período',          'Σ valor (vendas)',                                          'currency', false, 'BASIC', 'live',  'receita_periodo',         'Receita bruta de vendas.', 110),
  ('com.ticket_medio',             'commercial', 'Ticket médio',                'Receita / pedidos',                                         'currency', false, 'BASIC', 'live',  'ticket_medio',            'AOV.', 120),
  ('com.clientes_unicos',          'commercial', 'Clientes únicos',             'COUNT DISTINCT cliente_id',                                 'count',    false, 'BASIC', 'live',  'clientes_unicos',         'Compradores ativos.', 130),
  ('com.clientes_novos',           'commercial', 'Clientes novos',              'COUNT(*) WHERE total_pedidos = 1',                          'count',    false, 'BASIC', 'live',  'clientes_novos',          'First-time buyers.', 140),
  ('com.clientes_recorrentes',     'commercial', 'Clientes recorrentes',        'COUNT(*) WHERE total_pedidos > 1',                          'count',    false, 'BASIC', 'live',  'clientes_recorrentes',    'Buyers com 2+ pedidos.', 150),
  ('com.recencia_media_dias',      'commercial', 'Recência média (dias)',       'avg(dias_recencia)',                                        'days',     true,  'PRO',   'live',  'recencia_media_dias',     'RFM-R.', 160),
  ('com.frequencia_media_mensal',  'commercial', 'Frequência média mensal',     'dim_clientes.frequencia_mensal',                            'number',   false, 'PRO',   'live',  'frequencia_media_mensal', 'Pedidos/mês por cliente.', 170),
  ('com.churn_60d_perc',           'commercial', 'Churn 60d',                   'inativos_60d / total_clientes',                             'percent',  false, 'PRO',   'live',  'churn_60d_perc',          'Clientes sem compra > 60d.', 180),
  ('com.crescimento_receita_perc', 'commercial', 'Crescimento de receita',      '(atual − anterior) / anterior',                             'percent',  false, 'BASIC', 'live',  'crescimento_receita_perc','Vs período anterior.', 190),
  ('com.win_rate_perc',            'commercial', 'Win-rate (lead→pedido)',      'pedidos / leads_qualificados',                              'percent',  false, 'PRO',   'pending_data', 'win_rate_perc',           'Requer eventos CRM.', 200),
  ('com.ciclo_venda_dias',         'commercial', 'Ciclo de venda médio',        'avg(data_pedido − data_primeiro_contato)',                  'days',     false, 'PRO',   'pending_data', 'ciclo_venda_dias',        'Sales Cycle Length.', 210),
  ('com.nrr_perc',                 'commercial', 'Net Revenue Retention',       'Σ receita coorte t / Σ receita coorte t-1',                 'percent',  false, 'PRO',   'proxy',        'nrr_perc',                'Aproximada via receita de clientes recorrentes vs período anterior.', 220),
  ('com.clv',                      'commercial', 'Customer Lifetime Value',     'Ticket × Frequência × Tempo retenção',                      'currency', true,  'PRO',   'proxy',        'clv',                     'CLV proxy = ticket × frequência × 12 meses.', 230),
  ('com.checkout_conversion_perc', 'commercial', 'Conversão de checkout',       'pedidos / sessões',                                         'percent',  false, 'PRO',   'pending_data', 'checkout_conversion_perc','Requer conector e-commerce.', 240),
  ('com.nps',                      'commercial', 'NPS',                         '% promotores − % detratores',                                'number',   true,  'PRO',   'pending_data', 'nps',                     'Requer survey log.', 250),

  -- §6.3 Inventory
  ('inv.skus_ativos',              'inventory', 'SKUs ativos',                  'COUNT WHERE quantidade_vendida > 0',                        'count',    false, 'BASIC',      'live',         'skus_ativos',                'SKUs com movimentação histórica.', 100),
  ('inv.skus_total',               'inventory', 'SKUs totais',                  'COUNT FROM dim_inventory',                                  'count',    false, 'BASIC',      'live',         'skus_total',                 'Catálogo de produtos.', 110),
  ('inv.qtd_vendida_periodo',      'inventory', 'Quantidade vendida (período)', 'Σ quantidade no período',                                   'count',    false, 'BASIC',      'live',         'quantidade_vendida_periodo', 'Volume movimentado.', 120),
  ('inv.receita_periodo',          'inventory', 'Receita SKUs (período)',       'Σ valor no período',                                        'currency', false, 'BASIC',      'live',         'receita_skus_periodo',       'Receita atribuível a SKUs.', 130),
  ('inv.giro_estimado',            'inventory', 'Giro estimado',                'qtd vendida / SKUs ativos',                                 'ratio',    false, 'PRO',        'proxy',        'giro_estimado',              'Inventory turnover proxy (sem estoque on-hand).', 140),
  ('inv.dio_dias',                 'inventory', 'DIO — Days Inventory Outstanding', '(Estoque médio / COGS) × dias',                          'days',     false, 'PRO',        'pending_data', 'dio_dias',                   'Requer estoque on-hand histórico.', 150),
  ('inv.cobertura_dias',           'inventory', 'Cobertura de estoque (dias)',  'Estoque atual / consumo médio diário',                      'days',     true,  'PRO',        'pending_data', 'cobertura_dias',             'Requer estoque atual.', 160),
  ('inv.stockout_rate_perc',       'inventory', 'Stockout rate',                'SKUs sem giro / total SKUs (proxy)',                        'percent',  false, 'PRO',        'proxy',        'stockout_rate_perc',         'Proxy: SKUs sem movimentação no período.', 170),
  ('inv.fill_rate_perc',           'inventory', 'Fill rate',                    'Itens entregues / itens pedidos',                           'percent',  false, 'PRO',        'pending_data', 'fill_rate_perc',             'Requer dados de entrega.', 180),
  ('inv.sell_through_perc',        'inventory', 'Sell-through rate',            'Vendido / recebido no período',                              'percent',  false, 'PRO',        'pending_data', 'sell_through_perc',          'Requer recebimentos do estoque.', 190),
  ('inv.gmroi',                    'inventory', 'GMROI',                        'Margem bruta / Estoque médio',                              'ratio',    false, 'PRO',        'pending_data', 'gmroi',                      'Requer estoque médio em valor.', 200),
  ('inv.acuracidade_perc',         'inventory', 'Acuracidade de inventário',    '1 − |sistema−físico| / sistema',                            'percent',  true,  'ENTERPRISE', 'pending_data', 'acuracidade_perc',           'Requer contagens periódicas.', 210),
  ('inv.cobertura_top20_perc',     'inventory', 'Cobertura SKU classe A (Pareto)','% receita coberto pelos top 20% SKUs',                    'percent',  false, 'PRO',        'live',         'cobertura_top20_perc',       'Pareto coverage.', 220),
  ('inv.ticket_medio_sku',         'inventory', 'Ticket médio por SKU',          'Receita / SKUs movimentados',                              'currency', false, 'BASIC',      'live',         'ticket_medio_sku',           'Receita média por SKU ativo no período.', 230),
  ('inv.crescimento_quantidade_perc','inventory','Crescimento de quantidade',    '(qtd atual − anterior) / anterior',                         'percent',  false, 'BASIC',      'live',         'crescimento_quantidade_perc','Vs período anterior.', 240),

  -- §6.4 Supply
  ('sup.rfqs_abertas',             'supply', 'RFQs abertas',                    'status IN (sent,responded)',                                'count',    false, 'BASIC',      'live',         'rfqs_abertas',               'RFQs em fluxo.', 100),
  ('sup.rfqs_enviadas',            'supply', 'RFQs enviadas',                   'status = sent',                                              'count',    false, 'BASIC',      'live',         'rfqs_enviadas',              'Aguardando resposta.', 110),
  ('sup.rfqs_respondidas',         'supply', 'RFQs respondidas',                'status = responded',                                         'count',    false, 'BASIC',      'live',         'rfqs_respondidas',           'Respondidas no período.', 120),
  ('sup.taxa_resposta_perc',       'supply', 'Taxa de resposta de RFQ',         'respondidas / enviadas',                                     'percent',  false, 'BASIC',      'live',         'taxa_resposta_perc',         'Conversão da fase de RFQ.', 130),
  ('sup.tempo_resposta_medio_h',   'supply', 'Tempo médio de resposta',         'avg(responded_at − sent_at) (horas)',                       'hours',    false, 'BASIC',      'live',         'tempo_resposta_medio_h',     'Latência de fornecedores.', 140),
  ('sup.pos_aprovadas',            'supply', 'POs aprovadas',                   'status = approved',                                          'count',    false, 'BASIC',      'live',         'pos_aprovadas',              'POs no período.', 150),
  ('sup.pos_pendentes_aprovacao',  'supply', 'POs pendentes de aprovação',      'status = pending_approval',                                  'count',    true,  'BASIC',      'live',         'pos_pendentes_aprovacao',    'Backlog de aprovação.', 160),
  ('sup.spend_periodo',            'supply', 'Spend do período',                'Σ total_amount (approved+sent)',                             'currency', false, 'BASIC',      'live',         'spend_periodo',              'Volume de compras.', 170),
  ('sup.fornecedores_ativos',      'supply', 'Fornecedores ativos',             'fornecedores com frequência > 0',                            'count',    false, 'BASIC',      'live',         'fornecedores_ativos',        'Fornecedores em uso.', 180),
  ('sup.concentracao_top_perc',    'supply', 'Concentração por fornecedor',     'share% maior fornecedor (rolling 90d)',                      'percent',  true,  'PRO',        'live',         'concentracao_top_perc',      'Risco de concentração.', 190),
  ('sup.cycle_time_medio_h',       'supply', 'Cycle time PR→PO',                'avg(approved_at − created_at) (horas)',                     'hours',    false, 'PRO',        'live',         'cycle_time_medio_h',         'Tempo até aprovação da PO.', 200),
  ('sup.cost_savings_perc',        'supply', 'Cost savings %',                  '(baseline − ganhador) / baseline',                          'percent',  false, 'PRO',        'pending_data', 'cost_savings_perc',          'Requer baseline por SKU.', 210),
  ('sup.ppv',                      'supply', 'Price variance (PPV)',            '(preço atual − preço padrão) × quantidade',                  'currency', false, 'PRO',        'pending_data', 'ppv',                        'Requer preço padrão.', 220),
  ('sup.otif_perc',                'supply', 'OTIF — On-Time In-Full',          'pedidos no prazo+completos / total',                         'percent',  false, 'PRO',        'pending_data', 'otif_perc',                  'Requer recebimentos.', 230),
  ('sup.lead_time_medio_dias',     'supply', 'Lead time médio',                 'avg(data_entrega − data_po)',                                'days',     false, 'PRO',        'pending_data', 'lead_time_medio_dias',       'Requer data de entrega.', 240),
  ('sup.maverick_spend_perc',      'supply', 'Maverick spend %',                'compras fora-do-processo / total',                          'percent',  false, 'ENTERPRISE', 'pending_data', 'maverick_spend_perc',        'Requer audit das compras manuais.', 250),
  ('sup.spend_under_management_perc','supply','Spend under management',         'spend categorizado / total',                                 'percent',  false, 'PRO',        'proxy',        'spend_under_management_perc','Aproximado: % do spend ligado a fornecedor cadastrado.', 260),

  -- §6.5 Marketing (PRO-first)
  ('mkt.novos_clientes_periodo',   'marketing', 'Novos clientes (período)',     'COUNT cliente_id WHERE total_pedidos = 1',                  'count',    false, 'PRO',        'live',         'novos_clientes_periodo',     'Aquisições no período.', 100),
  ('mkt.receita_novos_clientes',   'marketing', 'Receita de novos clientes',    'Σ valor de clientes novos',                                 'currency', false, 'PRO',        'live',         'receita_novos_clientes',     'Receita atribuível à aquisição.', 110),
  ('mkt.cac',                      'marketing', 'CAC',                          '(Mkt + Sales spend) / novos clientes',                       'currency', false, 'PRO',        'pending_data', 'cac',                        'Requer ad spend ingerido.', 120),
  ('mkt.ltv_cac_ratio',            'marketing', 'LTV / CAC',                    'CLV / CAC',                                                  'ratio',    true,  'PRO',        'pending_data', 'ltv_cac_ratio',              'Saúde alvo ≥ 3.', 130),
  ('mkt.cac_payback_meses',        'marketing', 'CAC payback (meses)',          'CAC / Margem bruta mensal por cliente',                      'number',   true,  'PRO',        'pending_data', 'cac_payback_meses',          'Requer CAC.', 140),
  ('mkt.roas',                     'marketing', 'ROAS',                         'Receita atribuída / Investimento em mídia',                  'ratio',    false, 'PRO',        'pending_data', 'roas',                       'Requer ad spend.', 150),
  ('mkt.conversao_campanha_perc',  'marketing', 'Conversão de campanha',        'respostas / mensagens enviadas',                             'percent',  false, 'PRO',        'pending_data', 'conversao_campanha_perc',    'Aguarda EPIC-F outbound.', 160),
  ('mkt.ctr_perc',                 'marketing', 'CTR',                          'cliques / impressões',                                       'percent',  false, 'PRO',        'pending_data', 'ctr_perc',                   'Requer ingestão de mídia paga.', 170),
  ('mkt.engajamento_whatsapp_perc','marketing', 'Engajamento WhatsApp',         'lidas / enviadas',                                           'percent',  true,  'PRO',        'pending_data', 'engajamento_whatsapp_perc',  'Requer Twilio webhook.', 180),
  ('mkt.taxa_optout_perc',         'marketing', 'Taxa de opt-out',              'opt-outs / mensagens enviadas',                              'percent',  true,  'PRO',        'pending_data', 'taxa_optout_perc',           'Requer Twilio webhook.', 190),
  ('mkt.share_of_voice_perc',      'marketing', 'Share of voice',               'menções marca / menções setor',                              'percent',  false, 'ENTERPRISE', 'pending_data', 'share_of_voice_perc',        'Requer monitor externo.', 200),

  -- §6.6 Administrativo & Operacional
  ('adm.aprovacoes_pendentes',     'admin', 'Aprovações pendentes',             'COUNT approval_requests WHERE status=pending',                'count',    true,  'BASIC', 'live',  'aprovacoes_pendentes',          'Backlog do owner.', 100),
  ('adm.lead_time_aprovacao_h',    'admin', 'Lead-time médio de aprovação',     'avg(decided_at − created_at) horas',                          'hours',    false, 'PRO',   'live',  'lead_time_aprovacao_h',         'Latência de aprovação.', 110),
  ('adm.sla_aprovacao_perc',       'admin', 'SLA de aprovação (% no prazo)',    'aprovações no SLA / total',                                   'percent',  false, 'PRO',   'live',  'sla_aprovacao_perc',            'SLA padrão = 72h (BASIC).', 120),
  ('adm.documentos_pendentes',     'admin', 'Documentos pendentes',             'COUNT uploaded_files_metadata WHERE status IN (uploaded,failed)','count', true,  'BASIC', 'proxy', 'documentos_pendentes',          'Backlog de processamento de uploads (proxy enquanto fonte_de_dados.categoria não existir).', 130),
  ('adm.cobertura_rotinas_perc',   'admin', 'Cobertura de rotinas ativas',      'rotinas ativas / disponíveis no tier',                        'percent',  true,  'BASIC', 'live',  'cobertura_rotinas_perc',        'Adoção de automações.', 140),
  ('adm.frescor_dados_h',          'admin', 'Frescor dos dados (h)',            'now() − max(updated_at) por fato',                            'hours',    true,  'BASIC', 'live',  'frescor_dados_h',               'Idade dos dados ingestados.', 150),
  ('adm.audit_coverage_perc',      'admin', 'Auditabilidade (% ações com audit_log)', 'audit_log entries / mutating tool calls (proxy)',     'percent',  true,  'BASIC', 'proxy', 'audit_coverage_perc',           'Aproximada por contagem de logs vs aprovações.', 160)
ON CONFLICT (slug) DO UPDATE SET
  dimension      = EXCLUDED.dimension,
  label          = EXCLUDED.label,
  formula        = EXCLUDED.formula,
  unit           = EXCLUDED.unit,
  is_leading     = EXCLUDED.is_leading,
  tier_required  = EXCLUDED.tier_required,
  data_status    = EXCLUDED.data_status,
  rpc_column     = EXCLUDED.rpc_column,
  description    = EXCLUDED.description,
  sort_order     = EXCLUDED.sort_order;

-- ────────────────────────────────────────────────────────────────────────
-- 4. Replace dimension RPCs with §6 full surface
--    (DROP + CREATE because RETURNS TABLE shape changes.)
-- ────────────────────────────────────────────────────────────────────────

-- ── 4.1 Finance ────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS analytics_v2.get_finance_indicators(text);
CREATE FUNCTION analytics_v2.get_finance_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  receita_liquida          numeric,
  custo_total              numeric,
  margem_bruta_perc        numeric,
  margem_operacional_perc  numeric,
  ticket_medio             numeric,
  receita_yoy_perc         numeric,
  crescimento_receita_perc numeric,
  total_pedidos            bigint,
  -- §6.1 PRO extensions (proxy or pending_data — return NULL until ingest lands)
  dso_dias                 numeric,
  dpo_dias                 numeric,
  ccc_dias                 numeric,
  working_capital_ratio    numeric,
  burn_rate_mensal         numeric,
  runway_meses             numeric,
  cash_flow_30d            numeric,
  period                   text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
          AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
      ), 0)::numeric AS receita,
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') IN ('despesa','custo')
      ), 0)::numeric AS custos,
      COUNT(DISTINCT ft.documento) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
      )::bigint AS pedidos
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT COALESCE(SUM(ft.valor) FILTER (
      WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
        AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
    ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  yoy AS (
    SELECT COALESCE(SUM(ft.valor) FILTER (
      WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
        AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
    ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (p.window_start - interval '1 year')::date
      AND dd.data <  (p.window_end   - interval '1 year')::date
  ),
  -- Burn rate proxy: monthly average of operational outflows in the window
  burn AS (
    SELECT
      CASE WHEN (SELECT (window_end - window_start) FROM p) > 0
           THEN (cur.custos / GREATEST((SELECT (window_end - window_start) FROM p), 1) * 30)::numeric
           ELSE 0::numeric END AS burn_mensal
    FROM cur
  )
  SELECT
    cur.receita                                               AS receita_liquida,
    cur.custos                                                AS custo_total,
    CASE WHEN cur.receita > 0
         THEN round(((cur.receita - cur.custos) / cur.receita) * 100, 2)
         ELSE NULL END                                        AS margem_bruta_perc,
    CASE WHEN cur.receita > 0
         THEN round(((cur.receita - cur.custos) / cur.receita) * 100, 2)
         ELSE NULL END                                        AS margem_operacional_perc,
    CASE WHEN cur.pedidos > 0
         THEN round(cur.receita / cur.pedidos, 2)
         ELSE 0::numeric END                                  AS ticket_medio,
    CASE WHEN yoy.receita > 0
         THEN round(((cur.receita - yoy.receita) / yoy.receita) * 100, 2)
         ELSE NULL END                                        AS receita_yoy_perc,
    CASE WHEN prev.receita > 0
         THEN round(((cur.receita - prev.receita) / prev.receita) * 100, 2)
         ELSE NULL END                                        AS crescimento_receita_perc,
    cur.pedidos                                               AS total_pedidos,
    NULL::numeric                                             AS dso_dias,
    NULL::numeric                                             AS dpo_dias,
    NULL::numeric                                             AS ccc_dias,
    NULL::numeric                                             AS working_capital_ratio,
    round(burn.burn_mensal, 2)                                AS burn_rate_mensal,
    NULL::numeric                                             AS runway_meses,
    NULL::numeric                                             AS cash_flow_30d,
    (SELECT period_code FROM p)                               AS period
  FROM cur, prev, yoy, burn;
$$;

COMMENT ON FUNCTION analytics_v2.get_finance_indicators(text) IS
  'Finance dimension KPIs (§6.1, full surface). NULL columns map to data_status=pending_data in public.kpi_catalog.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_finance_indicators(text) TO authenticated;

-- ── 4.2 Commercial ─────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS analytics_v2.get_commercial_indicators(text);
CREATE FUNCTION analytics_v2.get_commercial_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  pedidos_periodo            bigint,
  receita_periodo            numeric,
  ticket_medio               numeric,
  clientes_unicos            bigint,
  clientes_novos             bigint,
  clientes_recorrentes       bigint,
  recencia_media_dias        numeric,
  frequencia_media_mensal    numeric,
  churn_60d_perc             numeric,
  crescimento_receita_perc   numeric,
  -- §6.2 PRO extensions
  win_rate_perc              numeric,
  ciclo_venda_dias           numeric,
  nrr_perc                   numeric,
  clv                        numeric,
  checkout_conversion_perc   numeric,
  nps                        numeric,
  period                     text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COUNT(DISTINCT ft.documento)::bigint                  AS pedidos,
      COALESCE(SUM(ft.valor), 0)::numeric                   AS receita,
      COUNT(DISTINCT ft.cliente_id)::bigint                 AS clientes_unicos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT
      COALESCE(SUM(ft.valor), 0)::numeric                   AS receita,
      COALESCE(SUM(ft.valor) FILTER (
        WHERE c.total_pedidos > 1
      ), 0)::numeric                                        AS receita_recorrentes
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd     ON dd.data_id   = ft.data_competencia_id
    LEFT JOIN analytics_v2.dim_clientes c ON c.cliente_id = ft.cliente_id
                                         AND c.client_id  = ft.client_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  cur_recor AS (
    SELECT COALESCE(SUM(ft.valor) FILTER (
      WHERE c.total_pedidos > 1
    ), 0)::numeric AS receita_recorrentes
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd     ON dd.data_id   = ft.data_competencia_id
    LEFT JOIN analytics_v2.dim_clientes c ON c.cliente_id = ft.cliente_id
                                         AND c.client_id  = ft.client_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  cli_agg AS (
    SELECT
      COUNT(*) FILTER (WHERE c.total_pedidos = 1)::bigint                   AS novos,
      COUNT(*) FILTER (WHERE c.total_pedidos > 1)::bigint                   AS recorrentes,
      COALESCE(AVG(c.dias_recencia)::numeric, 0)                             AS recencia,
      COALESCE(AVG(c.frequencia_mensal)::numeric, 0)                         AS frequencia,
      COUNT(*) FILTER (WHERE c.dias_recencia > 60)::numeric                  AS inativos_60d,
      NULLIF(COUNT(*)::numeric, 0)                                           AS total_clientes,
      COALESCE(AVG(c.ticket_medio)::numeric, 0)                              AS ticket_cli
    FROM analytics_v2.dim_clientes c
    WHERE c.client_id = public.get_my_client_id()
  )
  SELECT
    cur.pedidos,
    cur.receita,
    CASE WHEN cur.pedidos > 0
         THEN round(cur.receita / cur.pedidos, 2)
         ELSE 0::numeric END                                AS ticket_medio,
    cur.clientes_unicos,
    cli_agg.novos                                           AS clientes_novos,
    cli_agg.recorrentes                                     AS clientes_recorrentes,
    round(cli_agg.recencia, 1)                              AS recencia_media_dias,
    round(cli_agg.frequencia, 2)                            AS frequencia_media_mensal,
    CASE WHEN cli_agg.total_clientes IS NOT NULL
         THEN round((cli_agg.inativos_60d / cli_agg.total_clientes) * 100, 2)
         ELSE NULL END                                      AS churn_60d_perc,
    CASE WHEN prev.receita > 0
         THEN round(((cur.receita - prev.receita) / prev.receita) * 100, 2)
         ELSE NULL END                                      AS crescimento_receita_perc,
    NULL::numeric                                           AS win_rate_perc,
    NULL::numeric                                           AS ciclo_venda_dias,
    -- NRR proxy: receita de clientes recorrentes no período / mesma coorte no período anterior
    CASE WHEN prev.receita_recorrentes > 0
         THEN round((cur_recor.receita_recorrentes / prev.receita_recorrentes) * 100, 2)
         ELSE NULL END                                      AS nrr_perc,
    -- CLV proxy: ticket × frequência mensal × 12 meses
    CASE WHEN cli_agg.ticket_cli > 0 AND cli_agg.frequencia > 0
         THEN round(cli_agg.ticket_cli * cli_agg.frequencia * 12, 2)
         ELSE NULL END                                      AS clv,
    NULL::numeric                                           AS checkout_conversion_perc,
    NULL::numeric                                           AS nps,
    (SELECT period_code FROM p)                             AS period
  FROM cur, prev, cur_recor, cli_agg;
$$;

COMMENT ON FUNCTION analytics_v2.get_commercial_indicators(text) IS
  'Commercial dimension KPIs (§6.2, full surface). NRR + CLV são proxies — ver public.kpi_catalog.data_status.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_commercial_indicators(text) TO authenticated;

-- ── 4.3 Inventory ──────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS analytics_v2.get_inventory_indicators(text);
CREATE FUNCTION analytics_v2.get_inventory_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  skus_ativos                  bigint,
  skus_total                   bigint,
  quantidade_vendida_periodo   numeric,
  receita_skus_periodo         numeric,
  giro_estimado                numeric,
  ticket_medio_sku             numeric,
  cobertura_top20_perc         numeric,
  stockout_rate_perc           numeric,
  crescimento_quantidade_perc  numeric,
  -- §6.3 PRO extensions
  dio_dias                     numeric,
  cobertura_dias               numeric,
  fill_rate_perc               numeric,
  sell_through_perc            numeric,
  gmroi                        numeric,
  acuracidade_perc             numeric,
  period                       text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COUNT(DISTINCT ft.produto_id)::bigint                   AS skus_movimentados,
      COALESCE(SUM(ft.quantidade), 0)::numeric                AS qtd,
      COALESCE(SUM(ft.valor), 0)::numeric                     AS receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT COALESCE(SUM(ft.quantidade), 0)::numeric AS qtd
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  inv AS (
    SELECT
      COUNT(*)::bigint                                                                          AS total_skus,
      COUNT(*) FILTER (WHERE COALESCE(i.quantidade_total_vendida, 0) > 0)::bigint               AS ativos,
      COUNT(*) FILTER (WHERE COALESCE(i.quantidade_total_vendida, 0) = 0)::bigint               AS sem_giro,
      COALESCE(SUM(i.receita_total), 0)::numeric                                                AS receita_total
    FROM analytics_v2.dim_inventory i
    WHERE i.client_id = public.get_my_client_id()
  ),
  pareto AS (
    SELECT
      COALESCE(SUM(i.receita_total) FILTER (
        WHERE i.rn <= GREATEST(1, ceil(i.cnt * 0.20))
      ), 0)::numeric AS top_receita,
      COALESCE(SUM(i.receita_total), 0)::numeric AS total_receita
    FROM (
      SELECT
        i.receita_total,
        ROW_NUMBER() OVER (ORDER BY i.receita_total DESC NULLS LAST) AS rn,
        COUNT(*) OVER ()                                              AS cnt
      FROM analytics_v2.dim_inventory i
      WHERE i.client_id = public.get_my_client_id()
    ) i
  )
  SELECT
    inv.ativos                                                  AS skus_ativos,
    inv.total_skus                                              AS skus_total,
    cur.qtd                                                     AS quantidade_vendida_periodo,
    cur.receita                                                 AS receita_skus_periodo,
    CASE WHEN inv.ativos > 0
         THEN round(cur.qtd / inv.ativos, 2)
         ELSE NULL END                                          AS giro_estimado,
    CASE WHEN cur.skus_movimentados > 0
         THEN round(cur.receita / cur.skus_movimentados, 2)
         ELSE 0::numeric END                                    AS ticket_medio_sku,
    CASE WHEN pareto.total_receita > 0
         THEN round((pareto.top_receita / pareto.total_receita) * 100, 2)
         ELSE NULL END                                          AS cobertura_top20_perc,
    CASE WHEN inv.total_skus > 0
         THEN round((inv.sem_giro::numeric / inv.total_skus) * 100, 2)
         ELSE NULL END                                          AS stockout_rate_perc,
    CASE WHEN prev.qtd > 0
         THEN round(((cur.qtd - prev.qtd) / prev.qtd) * 100, 2)
         ELSE NULL END                                          AS crescimento_quantidade_perc,
    NULL::numeric                                               AS dio_dias,
    NULL::numeric                                               AS cobertura_dias,
    NULL::numeric                                               AS fill_rate_perc,
    NULL::numeric                                               AS sell_through_perc,
    NULL::numeric                                               AS gmroi,
    NULL::numeric                                               AS acuracidade_perc,
    (SELECT period_code FROM p)                                 AS period
  FROM cur, prev, inv, pareto;
$$;

COMMENT ON FUNCTION analytics_v2.get_inventory_indicators(text) IS
  'Inventory KPIs (§6.3, full surface).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_inventory_indicators(text) TO authenticated;

-- ── 4.4 Supply ─────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS analytics_v2.get_supply_indicators(text);
CREATE FUNCTION analytics_v2.get_supply_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  rfqs_abertas              bigint,
  rfqs_enviadas             bigint,
  rfqs_respondidas          bigint,
  taxa_resposta_perc        numeric,
  tempo_resposta_medio_h    numeric,
  pos_aprovadas             bigint,
  pos_pendentes_aprovacao   bigint,
  spend_periodo             numeric,
  fornecedores_ativos       bigint,
  concentracao_top_perc     numeric,
  cycle_time_medio_h        numeric,
  -- §6.4 PRO extensions
  cost_savings_perc         numeric,
  ppv                       numeric,
  otif_perc                 numeric,
  lead_time_medio_dias      numeric,
  maverick_spend_perc       numeric,
  spend_under_management_perc numeric,
  period                    text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  rfq_cur AS (
    SELECT
      COUNT(*) FILTER (WHERE r.status IN ('sent','responded'))::bigint                AS abertas,
      COUNT(*) FILTER (WHERE r.status = 'sent')::bigint                               AS enviadas,
      COUNT(*) FILTER (WHERE r.status = 'responded')::bigint                          AS respondidas,
      AVG(EXTRACT(EPOCH FROM (r.updated_at - r.sent_at)) / 3600.0) FILTER (
        WHERE r.status = 'responded' AND r.sent_at IS NOT NULL
      )::numeric                                                                       AS resp_h
    FROM public.rfq_requests r
    CROSS JOIN p
    WHERE r.client_id = public.get_my_client_id()::uuid
      AND r.created_at::date >= p.window_start
      AND r.created_at::date <  p.window_end
  ),
  po_cur AS (
    SELECT
      COUNT(*) FILTER (WHERE po.status = 'approved')::bigint                          AS aprovadas,
      COUNT(*) FILTER (WHERE po.status = 'pending_approval')::bigint                  AS pendentes,
      COALESCE(SUM(po.total_amount) FILTER (WHERE po.status IN ('approved','sent')), 0)::numeric AS spend,
      COALESCE(SUM(po.total_amount) FILTER (
        WHERE po.status IN ('approved','sent') AND po.supplier_id IS NOT NULL
      ), 0)::numeric                                                                  AS spend_categorizado,
      AVG(EXTRACT(EPOCH FROM (po.approved_at - po.created_at)) / 3600.0) FILTER (
        WHERE po.approved_at IS NOT NULL
      )::numeric                                                                       AS cycle_h
    FROM public.purchase_orders po
    CROSS JOIN p
    WHERE po.client_id = public.get_my_client_id()::uuid
      AND po.created_at::date >= p.window_start
      AND po.created_at::date <  p.window_end
  ),
  forn AS (
    SELECT
      COUNT(*) FILTER (WHERE f.frequencia_mensal IS NOT NULL AND f.frequencia_mensal > 0)::bigint AS ativos,
      COALESCE(SUM(f.receita_total), 0)::numeric                                                  AS spend_total,
      MAX(f.receita_total)                                                                        AS top_receita
    FROM analytics_v2.dim_fornecedores f
    WHERE f.client_id = public.get_my_client_id()
  )
  SELECT
    rfq_cur.abertas,
    rfq_cur.enviadas,
    rfq_cur.respondidas,
    CASE WHEN (rfq_cur.enviadas + rfq_cur.respondidas) > 0
         THEN round((rfq_cur.respondidas::numeric / (rfq_cur.enviadas + rfq_cur.respondidas)) * 100, 2)
         ELSE NULL END                                                                AS taxa_resposta_perc,
    CASE WHEN rfq_cur.resp_h IS NOT NULL THEN round(rfq_cur.resp_h, 2) ELSE NULL END  AS tempo_resposta_medio_h,
    po_cur.aprovadas                                                                  AS pos_aprovadas,
    po_cur.pendentes                                                                  AS pos_pendentes_aprovacao,
    po_cur.spend                                                                      AS spend_periodo,
    forn.ativos                                                                       AS fornecedores_ativos,
    CASE WHEN forn.spend_total > 0 AND forn.top_receita IS NOT NULL
         THEN round((forn.top_receita / forn.spend_total) * 100, 2)
         ELSE NULL END                                                                AS concentracao_top_perc,
    CASE WHEN po_cur.cycle_h IS NOT NULL THEN round(po_cur.cycle_h, 2) ELSE NULL END  AS cycle_time_medio_h,
    NULL::numeric                                                                     AS cost_savings_perc,
    NULL::numeric                                                                     AS ppv,
    NULL::numeric                                                                     AS otif_perc,
    NULL::numeric                                                                     AS lead_time_medio_dias,
    NULL::numeric                                                                     AS maverick_spend_perc,
    -- Spend under management proxy: % of spend tied to a supplier in dim_fornecedores
    CASE WHEN po_cur.spend > 0
         THEN round((po_cur.spend_categorizado / po_cur.spend) * 100, 2)
         ELSE NULL END                                                                AS spend_under_management_perc,
    (SELECT period_code FROM p)                                                       AS period
  FROM rfq_cur, po_cur, forn;
$$;

COMMENT ON FUNCTION analytics_v2.get_supply_indicators(text) IS
  'Supply/Procurement KPIs (§6.4, full surface).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_supply_indicators(text) TO authenticated;

-- ── 4.5 Marketing (mostly pending_data; still a single contract) ───────
DROP FUNCTION IF EXISTS analytics_v2.get_marketing_indicators(text);
CREATE FUNCTION analytics_v2.get_marketing_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  novos_clientes_periodo    bigint,
  receita_novos_clientes    numeric,
  conversao_campanha_perc   numeric,
  engajamento_whatsapp_perc numeric,
  taxa_optout_perc          numeric,
  cac                       numeric,
  ltv_cac_ratio             numeric,
  cac_payback_meses         numeric,
  roas                      numeric,
  ctr_perc                  numeric,
  share_of_voice_perc       numeric,
  period                    text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  novos AS (
    SELECT
      COUNT(DISTINCT ft.cliente_id) FILTER (
        WHERE c.total_pedidos = 1
      )::bigint AS qtd,
      COALESCE(SUM(ft.valor) FILTER (
        WHERE c.total_pedidos = 1
      ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd     ON dd.data_id   = ft.data_competencia_id
    LEFT JOIN analytics_v2.dim_clientes c ON c.cliente_id = ft.cliente_id
                                         AND c.client_id  = ft.client_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  )
  SELECT
    novos.qtd                       AS novos_clientes_periodo,
    novos.receita                   AS receita_novos_clientes,
    NULL::numeric                   AS conversao_campanha_perc,
    NULL::numeric                   AS engajamento_whatsapp_perc,
    NULL::numeric                   AS taxa_optout_perc,
    NULL::numeric                   AS cac,
    NULL::numeric                   AS ltv_cac_ratio,
    NULL::numeric                   AS cac_payback_meses,
    NULL::numeric                   AS roas,
    NULL::numeric                   AS ctr_perc,
    NULL::numeric                   AS share_of_voice_perc,
    (SELECT period_code FROM p)     AS period
  FROM novos;
$$;

COMMENT ON FUNCTION analytics_v2.get_marketing_indicators(text) IS
  'Marketing KPIs (§6.5, PRO). Live: novos clientes do período. Restante = pending_data até EPIC-F + ad ingest.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_marketing_indicators(text) TO authenticated;

-- ── 4.6 Admin (NEW — §6.6) ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.get_admin_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  aprovacoes_pendentes      bigint,
  lead_time_aprovacao_h     numeric,
  sla_aprovacao_perc        numeric,
  documentos_pendentes      bigint,
  cobertura_rotinas_perc    numeric,
  frescor_dados_h           numeric,
  audit_coverage_perc       numeric,
  period                    text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  appr AS (
    SELECT
      COUNT(*) FILTER (WHERE ar.status = 'pending')::bigint                    AS pendentes,
      AVG(EXTRACT(EPOCH FROM (ar.decided_at - ar.created_at)) / 3600.0) FILTER (
        WHERE ar.decided_at IS NOT NULL
          AND ar.created_at::date >= (SELECT window_start FROM p)
          AND ar.created_at::date <  (SELECT window_end   FROM p)
      )::numeric                                                                AS lead_h,
      COUNT(*) FILTER (
        WHERE ar.decided_at IS NOT NULL
          AND ar.created_at::date >= (SELECT window_start FROM p)
          AND ar.created_at::date <  (SELECT window_end   FROM p)
      )::numeric                                                                AS decided_n,
      COUNT(*) FILTER (
        WHERE ar.decided_at IS NOT NULL
          AND ar.created_at::date >= (SELECT window_start FROM p)
          AND ar.created_at::date <  (SELECT window_end   FROM p)
          AND EXTRACT(EPOCH FROM (ar.decided_at - ar.created_at)) <= COALESCE(ar.sla_hours, 72) * 3600
      )::numeric                                                                AS in_sla_n
    FROM public.approval_requests ar
    WHERE ar.client_id::text = public.get_my_client_id()
  ),
  docs AS (
    SELECT
      COUNT(*) FILTER (
        WHERE COALESCE(uf.status, 'uploaded') IN ('uploaded','failed')
      )::bigint AS pendentes
    FROM public.uploaded_files_metadata uf
    WHERE uf.cliente_vizu_id::text = public.get_my_client_id()
  ),
  rotinas AS (
    SELECT
      COUNT(*) FILTER (WHERE cr.enabled)::numeric AS ativas,
      NULLIF(COUNT(*)::numeric, 0)                AS total
    FROM public.client_routines cr
    WHERE cr.client_id::text = public.get_my_client_id()
  ),
  frescor AS (
    -- Hours since the latest fato_transacoes row; proxy for ingestion freshness.
    SELECT
      EXTRACT(EPOCH FROM (now() - MAX(ft.created_at))) / 3600.0 AS horas
    FROM analytics_v2.fato_transacoes ft
    WHERE ft.client_id = public.get_my_client_id()
  ),
  audit AS (
    -- Audit coverage proxy: audit_log entries in window / mutating events
    -- (approved+rejected approvals + sent consumer messages, when present).
    SELECT
      (SELECT COUNT(*)::numeric FROM public.audit_log al
        WHERE al.client_id::text = public.get_my_client_id()
          AND al.created_at::date >= (SELECT window_start FROM p)
          AND al.created_at::date <  (SELECT window_end   FROM p)
      )                                                                          AS audited,
      GREATEST(
        (SELECT COUNT(*)::numeric FROM public.approval_requests ar
          WHERE ar.client_id::text = public.get_my_client_id()
            AND ar.decided_at IS NOT NULL
            AND ar.decided_at::date >= (SELECT window_start FROM p)
            AND ar.decided_at::date <  (SELECT window_end   FROM p)
        ),
        1
      )                                                                          AS expected
  )
  SELECT
    appr.pendentes                                                              AS aprovacoes_pendentes,
    CASE WHEN appr.lead_h IS NOT NULL THEN round(appr.lead_h, 2) ELSE NULL END  AS lead_time_aprovacao_h,
    CASE WHEN appr.decided_n > 0
         THEN round((appr.in_sla_n / appr.decided_n) * 100, 2)
         ELSE NULL END                                                          AS sla_aprovacao_perc,
    docs.pendentes                                                              AS documentos_pendentes,
    CASE WHEN rotinas.total IS NOT NULL
         THEN round((rotinas.ativas / rotinas.total) * 100, 2)
         ELSE NULL END                                                          AS cobertura_rotinas_perc,
    CASE WHEN frescor.horas IS NOT NULL THEN round(frescor.horas::numeric, 2) ELSE NULL END
                                                                                AS frescor_dados_h,
    CASE WHEN audit.expected > 0
         THEN round(LEAST(audit.audited / audit.expected, 1) * 100, 2)
         ELSE NULL END                                                          AS audit_coverage_perc,
    (SELECT period_code FROM p)                                                 AS period
  FROM appr, docs, rotinas, frescor, audit;
$$;

COMMENT ON FUNCTION analytics_v2.get_admin_indicators(text) IS
  'Administrative & operational KPIs (§6.6): approval queue, lead-time, SLA, documentos sem categoria, cobertura de rotinas, frescor dos dados, audit coverage.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_admin_indicators(text) TO authenticated;

-- ────────────────────────────────────────────────────────────────────────
-- 5. Auxiliary Commercial RPCs for groupby / list KPIs (§6.2)
-- ────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_revenue_by_channel(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  channel       text,
  receita       numeric,
  pedidos       bigint,
  share_perc    numeric,
  period        text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  -- We do not yet ingest a "canal" column on fato_transacoes. As a temporary
  -- proxy we group by the transaction status (a stand-in for source/channel).
  -- When a real `canal` field lands the GROUP BY can be swapped in place
  -- without changing the RPC signature.
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  agg AS (
    SELECT
      COALESCE(NULLIF(ft.status, ''), 'sem_canal')::text AS channel,
      COALESCE(SUM(ft.valor), 0)::numeric                AS receita,
      COUNT(DISTINCT ft.documento)::bigint               AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
    GROUP BY 1
  ),
  total AS (SELECT NULLIF(SUM(receita), 0)::numeric AS grand FROM agg)
  SELECT
    agg.channel,
    agg.receita,
    agg.pedidos,
    CASE WHEN total.grand IS NOT NULL
         THEN round((agg.receita / total.grand) * 100, 2)
         ELSE NULL END                                AS share_perc,
    (SELECT period_code FROM p)                      AS period
  FROM agg, total
  ORDER BY agg.receita DESC NULLS LAST;
$$;

COMMENT ON FUNCTION analytics_v2.get_commercial_revenue_by_channel(text) IS
  'Receita por canal (§6.2). Hoje agrupa por fato_transacoes.status como proxy até existir um campo canal nativo.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_commercial_revenue_by_channel(text) TO authenticated;

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_top_clients(
  p_period text  DEFAULT '30d',
  p_limit  integer DEFAULT 10
)
RETURNS TABLE (
  cliente_id   bigint,
  nome         text,
  receita      numeric,
  pedidos      bigint,
  share_perc   numeric,
  period       text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  agg AS (
    SELECT
      ft.cliente_id,
      MAX(c.nome)                          AS nome,
      COALESCE(SUM(ft.valor), 0)::numeric  AS receita,
      COUNT(DISTINCT ft.documento)::bigint AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas    dd ON dd.data_id = ft.data_competencia_id
    LEFT JOIN analytics_v2.dim_clientes c
      ON c.cliente_id = ft.cliente_id AND c.client_id = ft.client_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
      AND ft.cliente_id IS NOT NULL
    GROUP BY ft.cliente_id
  ),
  total AS (SELECT NULLIF(SUM(receita), 0)::numeric AS grand FROM agg)
  SELECT
    agg.cliente_id,
    agg.nome,
    agg.receita,
    agg.pedidos,
    CASE WHEN total.grand IS NOT NULL
         THEN round((agg.receita / total.grand) * 100, 2)
         ELSE NULL END                              AS share_perc,
    (SELECT period_code FROM p)                    AS period
  FROM agg, total
  ORDER BY agg.receita DESC NULLS LAST
  LIMIT GREATEST(coalesce(p_limit, 10), 1);
$$;

COMMENT ON FUNCTION analytics_v2.get_commercial_top_clients(text, integer) IS
  'Top N clientes por receita no período (§6.2 Pareto / 80–20).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_commercial_top_clients(text, integer) TO authenticated;

COMMIT;
