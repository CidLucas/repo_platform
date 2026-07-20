-- ══════════════════════════════════════════════════════════════════════════════
-- Knowledge Domain Mind Map
-- Ontology: Documents as atoms, domains as molecules, agents as reactions
-- Schema version: 2.0  (mirrors blu_knowledge_ontology.json)
-- ══════════════════════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. ONTOLOGY CATALOG TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Catalog of all ~51 typed document definitions across all domains.
-- Documents are immutable definitions; client state lives in client_knowledge_documents.
CREATE TABLE IF NOT EXISTS public.knowledge_document_types (
  id              text PRIMARY KEY,                -- 'ficha_cadastral', 'fluxo_caixa_diario'
  domain_id       text NOT NULL,                   -- 'identidade' | 'operacoes' | 'pessoas' | 'externo' | 'estrategia'
  subdomain_id    text,                            -- 'comercial' | 'financeiro' | 'compras' | 'producao' | 'logistica' | NULL for root docs
  name            text NOT NULL,
  type            text NOT NULL,                   -- 'registry' | 'analysis' | 'transaction' | 'legal' | 'report' | ...
  created_by      text,                            -- 'onboarding' | 'erp' | 'documentos_agent' | ...
  consumed_by     text[]   DEFAULT '{}',           -- agent slugs or 'all'
  fields          text[]   DEFAULT '{}',           -- field names within this document
  status          text     NOT NULL DEFAULT 'required'
                           CHECK (status IN ('required', 'optional', 'generated')),
  coverage_weight numeric  NOT NULL DEFAULT 1.0,   -- 0.0–1.0; required=1.0, optional=0.6, generated=0.8
  tags            text[]   DEFAULT '{}',           -- from tag_system: 'estratégico' | 'financeiro' | ...
  sort_order      int      DEFAULT 0,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- 8 tags that control cross-agent document visibility.
CREATE TABLE IF NOT EXISTS public.knowledge_tag_definitions (
  tag         text PRIMARY KEY,
  description text,
  consumed_by text[] DEFAULT '{}'
);

-- Per-agent document requirements: minimum (blocks activation) vs nice_to_have (enables full capability).
CREATE TABLE IF NOT EXISTS public.knowledge_agent_requirements (
  agent_slug          text    NOT NULL REFERENCES public.agent_catalog(slug) ON DELETE CASCADE,
  document_type_id    text    NOT NULL REFERENCES public.knowledge_document_types(id) ON DELETE CASCADE,
  requirement_type    text    NOT NULL CHECK (requirement_type IN ('minimum', 'nice_to_have')),
  coverage_threshold  numeric NOT NULL DEFAULT 0.8,  -- agent-level threshold (same value per agent_slug)
  PRIMARY KEY (agent_slug, document_type_id)
);

-- 5 multi-step workflows triggered by document state changes.
CREATE TABLE IF NOT EXISTS public.cross_agent_routines (
  id                  text PRIMARY KEY,
  name                text NOT NULL,
  trigger_domain      text,
  trigger_document_id text REFERENCES public.knowledge_document_types(id),
  trigger_status      text,                         -- 'signed' | '100%' | NULL
  trigger_condition   text,                         -- 'last_day_of_month' | 'price_increase_>15%' | NULL
  steps               jsonb NOT NULL DEFAULT '[]',  -- [{step, agent, action, output}]
  created_at          timestamptz NOT NULL DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. CLIENT DOCUMENT INVENTORY
-- ─────────────────────────────────────────────────────────────────────────────

-- Tracks which documents each client has, and their coverage status.
-- One row per (client, document_type). Missing = not yet inserted.
CREATE TABLE IF NOT EXISTS public.client_knowledge_documents (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id        uuid        NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  document_type_id text        NOT NULL REFERENCES public.knowledge_document_types(id),
  status           text        NOT NULL DEFAULT 'missing'
                               CHECK (status IN ('missing', 'partial', 'complete')),
  source           text,                    -- 'onboarding' | 'erp' | 'erp_synced' | 'upload' | 'agent_generated'
  vector_document_id uuid,                 -- optional FK to vector_db.documents
  field_coverage   jsonb       DEFAULT '{}', -- {field_name: bool} — which document fields are populated
  metadata         jsonb       DEFAULT '{}',
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_client_document UNIQUE (client_id, document_type_id)
);

CREATE INDEX IF NOT EXISTS idx_ckd_client
  ON public.client_knowledge_documents (client_id);

CREATE INDEX IF NOT EXISTS idx_ckd_client_status
  ON public.client_knowledge_documents (client_id, status);


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. ROW-LEVEL SECURITY
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.knowledge_document_types     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_tag_definitions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_agent_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cross_agent_routines         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_knowledge_documents   ENABLE ROW LEVEL SECURITY;

-- Catalog tables: public read (catalog is not per-client)
CREATE POLICY "kdt_public_read"  ON public.knowledge_document_types     FOR SELECT USING (true);
CREATE POLICY "ktd_public_read"  ON public.knowledge_tag_definitions    FOR SELECT USING (true);
CREATE POLICY "kar_public_read"  ON public.knowledge_agent_requirements FOR SELECT USING (true);
CREATE POLICY "car_public_read"  ON public.cross_agent_routines         FOR SELECT USING (true);

-- Client documents: clients see and mutate only their own rows
CREATE POLICY "ckd_client_all"   ON public.client_knowledge_documents
  FOR ALL USING (client_id = public.get_my_client_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. SEED: TAG DEFINITIONS (8 tags from tag_system)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.knowledge_tag_definitions (tag, description, consumed_by) VALUES
  ('cadastro',     'Foundation data — used by all agents',               ARRAY['compras','financeiro','documentos','estrategia','clientes','agenda']),
  ('estratégico',  'Strategic documents — executive/strategy visibility', ARRAY['estrategia','admin']),
  ('financeiro',   'Financial documents',                                 ARRAY['financeiro','estrategia']),
  ('operacional',  'Operational documents',                               ARRAY['compras','agenda']),
  ('cliente',      'Client-related documents',                            ARRAY['clientes','estrategia']),
  ('legal',        'Legal documents',                                     ARRAY['documentos','admin']),
  ('fiscal',       'Tax documents',                                       ARRAY['financeiro','admin']),
  ('conhecimento', 'Knowledge base — broadly accessible',                ARRAY['documentos','compras','financeiro','estrategia','clientes','agenda'])
ON CONFLICT (tag) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. SEED: DOCUMENT TYPES  (51 docs from JSON ontology v2.0)
-- ─────────────────────────────────────────────────────────────────────────────

-- ── IDENTIDADE ───────────────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('ficha_cadastral',      'identidade', NULL, 'Ficha Cadastral',        'registry',  'onboarding',       ARRAY['all'],                           ARRAY['cnpj','razao_social','nome_fantasia','endereco','cnae','regime_tributario'],                 'required', 1.0, '{}',                    10),
  ('perfil_empresarial',   'identidade', NULL, 'Perfil Empresarial',     'analysis',  'interview_chat',   ARRAY['estrategia','documentos'],        ARRAY['segmento','porte','maturidade_digital','diferencial','tempo_mercado'],                      'required', 0.9, '{}',                    20),
  ('posicionamento',       'identidade', NULL, 'Posicionamento',         'strategy',  'user_scraping',    ARRAY['estrategia','clientes'],          ARRAY['concorrentes_diretos','territorio','preco_vs_mercado','proposta_valor'],                    'required', 0.8, '{}',                    30),
  ('missao_visao_valores', 'identidade', NULL, 'Missão, Visão e Valores','cultural',  'documentos_agent', ARRAY['estrategia','documentos'],        ARRAY['missao','visao','valores','metas_proprietario'],                                           'optional', 0.6, ARRAY['estratégico'],    40),
  ('termos_lgpd',          'identidade', NULL, 'Termos de Uso / LGPD',  'legal',     'documentos_agent', ARRAY['admin'],                          ARRAY['consentimentos','politica_dados','retencao','dpo_contato'],                                 'required', 0.7, '{}',                    50)
ON CONFLICT (id) DO NOTHING;

-- ── OPERAÇÕES > COMERCIAL ────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('catalogo_produtos',  'operacoes','comercial','Catálogo de Produtos/Serviços','master_data','erp_user',         ARRAY['compras','financeiro','documentos','estrategia'],ARRAY['sku','nome','categoria','preco','margem','status'],                           'required', 1.0, '{}',                              110),
  ('pipeline_vendas',    'operacoes','comercial','Pipeline de Vendas',           'crm',        'crm_planilhas',    ARRAY['financeiro','estrategia'],                       ARRAY['etapa','probabilidade','valor','cliente','previsao_fechamento'],              'required', 0.9, '{}',                              120),
  ('historico_pedidos',  'operacoes','comercial','Histórico de Pedidos',         'transaction','erp',              ARRAY['compras','financeiro','estrategia','clientes'],  ARRAY['pedido_id','cliente','itens','valor','data','status'],                        'required', 1.0, '{}',                              130),
  ('proposta_comercial', 'operacoes','comercial','Proposta Comercial',           'sales',      'documentos_agent', ARRAY['clientes','financeiro'],                         ARRAY['escopo','prazos','valores','condicoes_pagamento','cliente'],                  'generated',0.8, ARRAY['operacional','cliente'],    140),
  ('contrato_venda',     'operacoes','comercial','Contrato de Venda',            'legal',      'documentos_agent', ARRAY['agenda','compras'],                              ARRAY['partes','escopo','vigencia','valores','clausulas'],                           'generated',0.8, ARRAY['legal','operacional'],      150)
ON CONFLICT (id) DO NOTHING;

-- ── OPERAÇÕES > FINANCEIRO ───────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('fluxo_caixa_diario',     'operacoes','financeiro','Fluxo de Caixa Diário',      'report',    'banking_erp',          ARRAY['agenda','estrategia'],              ARRAY['data','entradas','saidas','saldo','projetado_7d','projetado_30d'],                                   'required', 1.0, '{}',                              210),
  ('dre_mensal',             'operacoes','financeiro','DRE Mensal',                 'accounting','erp_contador',          ARRAY['estrategia','admin'],               ARRAY['receita','cmv','despesas_fixas','despesas_variaveis','ebitda','lucro_liquido'],                      'required', 1.0, '{}',                              220),
  ('balanco_patrimonial',    'operacoes','financeiro','Balanço Patrimonial',        'accounting','contador',               ARRAY['estrategia','bancos'],             ARRAY['ativo','passivo','patrimonio_liquido','data_base'],                                                 'optional', 0.7, '{}',                              230),
  ('darf_gfip_gps',          'operacoes','financeiro','DARF / GFIP / GPS',          'tax',       'financeiro_agent',      ARRAY['admin','documentos'],              ARRAY['tipo','valor','vencimento','periodo_apuracao','status_pagamento'],                                   'generated',0.9, ARRAY['fiscal'],                    240),
  ('projecao_caixa',         'operacoes','financeiro','Projeção de Caixa',          'forecast',  'financeiro_agent',      ARRAY['agenda','estrategia'],             ARRAY['horizonte','cenario_otimista','cenario_realista','cenario_pessimista','riscos'],                     'generated',0.8, ARRAY['financeiro'],                250),
  ('fatura_nota_fiscal',     'operacoes','financeiro','Fatura / Nota Fiscal',       'invoice',   'documentos_financeiro', ARRAY['clientes','financeiro'],           ARRAY['numero','cliente','valor','vencimento','status','itens'],                                            'generated',1.0, ARRAY['financeiro','cliente'],      260),
  ('relatorio_inadimplencia','operacoes','financeiro','Relatório de Inadimplência', 'risk',      'financeiro_agent',      ARRAY['clientes','estrategia'],           ARRAY['cliente','valor_atrasado','dias_atraso','acao_sugerida','provisao'],                                  'generated',0.8, ARRAY['financeiro','cliente'],      270)
ON CONFLICT (id) DO NOTHING;

-- ── OPERAÇÕES > COMPRAS ──────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('cadastro_fornecedores', 'operacoes','compras','Cadastro de Fornecedores', 'master_data','erp_user',         ARRAY['compras','financeiro'],   ARRAY['nome','cnpj','contato','categoria','avaliacao','lead_time'],                                       'required', 1.0, '{}',                          310),
  ('cotacao_rfq',           'operacoes','compras','Cotação / RFQ',            'procurement','compras_agent',    ARRAY['estrategia'],             ARRAY['item','fornecedores','precos','prazos','condicoes','recomendacao'],                                 'generated',0.8, ARRAY['operacional'],           320),
  ('ordem_compra',          'operacoes','compras','Ordem de Compra',          'transaction','compras_agent',    ARRAY['financeiro','agenda'],    ARRAY['numero','fornecedor','itens','valor','prazo_entrega','status'],                                     'generated',0.9, ARRAY['operacional'],           330),
  ('controle_inventario',   'operacoes','compras','Controle de Inventário',   'stock',      'erp_wms',          ARRAY['compras','financeiro'],   ARRAY['sku','quantidade','localizacao','custo_medio','validade','curva_abc'],                             'required', 1.0, '{}',                          340),
  ('avaliacao_fornecedor',  'operacoes','compras','Avaliação de Fornecedor',  'scorecard',  'compras_agent',    ARRAY['estrategia'],             ARRAY['fornecedor','score_preco','score_prazo','score_qualidade','score_total','recomendacao'],            'generated',0.7, ARRAY['operacional'],           350),
  ('contrato_fornecimento', 'operacoes','compras','Contrato de Fornecimento', 'legal',      'documentos_agent', ARRAY['compras','financeiro'],   ARRAY['fornecedor','vigencia','valores','clausulas','reajuste','penalidades'],                            'generated',0.7, ARRAY['legal','operacional'],   360)
ON CONFLICT (id) DO NOTHING;

-- ── OPERAÇÕES > PRODUÇÃO ─────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('ficha_tecnica',        'operacoes','producao','Ficha Técnica / Receita',       'technical','documentos_agent',ARRAY['compras','agenda'],         ARRAY['produto','ingredientes','quantidades','tempo','rendimento','custo_unitario'],    'generated',0.9, ARRAY['conhecimento','operacional'], 410),
  ('plano_producao',       'operacoes','producao','Plano de Produção',             'schedule', 'agenda_agent',   ARRAY['compras','financeiro'],      ARRAY['data','produtos','quantidades','staff','equipamentos','prioridade'],             'generated',0.8, ARRAY['operacional'],                420),
  ('controle_qualidade',   'operacoes','producao','Controle de Qualidade',         'qc',       'producao',       ARRAY['estrategia','documentos'],   ARRAY['lote','parametros','resultados','conformidade','acoes_corretivas'],              'required', 0.7, '{}',                               430),
  ('relatorio_capacidade', 'operacoes','producao','Relatório de Capacidade',       'capacity', 'erp_iot',        ARRAY['estrategia','agenda'],       ARRAY['equipamento','utilizacao','oee','gargalos','sugestao_expansao'],                'optional', 0.6, '{}',                               440),
  ('nao_conformidade',     'operacoes','producao','Registro de Não Conformidade',  'issue',    'producao',       ARRAY['estrategia','compras'],      ARRAY['data','descricao','causa_raiz','acao_corretiva','responsavel','prazo'],          'required', 0.6, '{}',                               450)
ON CONFLICT (id) DO NOTHING;

-- ── OPERAÇÕES > LOGÍSTICA ────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('rota_entrega',    'operacoes','logistica','Rota de Entrega',              'route', 'agenda_agent',    ARRAY['clientes','financeiro'],   ARRAY['data','clientes','sequencia','distancia_km','tempo_estimado','motorista'], 'generated',0.8, ARRAY['operacional'],         510),
  ('estoque_fisico',  'operacoes','logistica','Controle de Estoque Físico',  'wms',   'wms_erp',         ARRAY['compras','financeiro'],    ARRAY['local','sku','quantidade_fisica','divergencia','ultima_contagem'],         'required', 0.8, '{}',                        520),
  ('termo_entrega',   'operacoes','logistica','Termo de Entrega / O.S.',     'proof', 'agenda_logistica', ARRAY['documentos','clientes'],  ARRAY['numero','cliente','itens','data_entrega','recebido_por','assinatura'],     'generated',0.7, ARRAY['operacional','cliente'],530),
  ('relatorio_frete', 'operacoes','logistica','Relatório de Frete',          'cost',  'logistica',        ARRAY['financeiro','estrategia'],ARRAY['periodo','total_frete','frete_medio','transportadoras','rotas_mais_caros'],'optional', 0.6, '{}',                        540)
ON CONFLICT (id) DO NOTHING;

-- ── PESSOAS ──────────────────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('organograma',     'pessoas',NULL,'Organograma',         'structure','rh_user',           ARRAY['estrategia','agenda'],  ARRAY['cargo','funcao','reporta_a','headcount','area'],                           'required',0.8,'{}', 610),
  ('folha_pagamento', 'pessoas',NULL,'Folha de Pagamento',  'payroll',  'erp_folha',          ARRAY['financeiro','admin'],   ARRAY['funcionario','salario','beneficios','encargos','total','competencia'],    'required',0.9,'{}', 620),
  ('skills_matrix',   'pessoas',NULL,'Skills Matrix',       'competency','rh_avaliacao',      ARRAY['estrategia','agenda'],  ARRAY['funcionario','habilidades','nivel','gaps','plano_desenvolvimento'],        'optional',0.6,'{}', 630),
  ('registro_ponto',  'pessoas',NULL,'Registro de Ponto',   'time',     'ponto_eletronico',   ARRAY['agenda','financeiro'],  ARRAY['funcionario','data','entrada','saida','horas_extras','banco_horas'],      'required',0.8,'{}', 640),
  ('pesquisa_clima',  'pessoas',NULL,'Pesquisa de Clima',   'culture',  'rh',                 ARRAY['estrategia','admin'],   ARRAY['data','nps_interno','turnover_motivado','satisfacao','acoes'],            'optional',0.5,'{}', 650),
  ('ferias_licencas', 'pessoas',NULL,'Férias / Licenças',   'absence',  'rh',                 ARRAY['agenda','financeiro'],  ARRAY['funcionario','tipo','inicio','fim','dias','status'],                       'required',0.7,'{}', 660)
ON CONFLICT (id) DO NOTHING;

-- ── EXTERNO ──────────────────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('ficha_cliente',                'externo',NULL,'Ficha do Cliente',                   'crm',      'crm_user',         ARRAY['clientes','estrategia'],  ARRAY['nome','segmento','ticket_medio','ltv','nps','ultima_compra','ciclo_compra'],          'required',1.0,'{}', 710),
  ('pesquisa_nps',                 'externo',NULL,'Pesquisa NPS',                       'survey',   'clientes_agent',   ARRAY['estrategia','clientes'],  ARRAY['cliente','nota','feedback','categoria','data','acao_sugerida'],                      'generated',0.8,ARRAY['cliente'], 720),
  ('analise_concorrencia',         'externo',NULL,'Análise de Concorrência',            'intel',    'scraping_news',    ARRAY['estrategia','documentos'],ARRAY['concorrente','precos','movimentos','market_share','diferenciais','data_coleta'],    'optional', 0.6,'{}', 730),
  ('monitoramento_precos_mercado', 'externo',NULL,'Monitoramento de Preços de Mercado', 'market',   'apis_news',        ARRAY['compras','estrategia'],   ARRAY['insumo','preco_atual','variacao','fonte','data','tendencia'],                        'optional', 0.6,'{}', 740),
  ('alerta_regulatorio',           'externo',NULL,'Alerta Regulatório',                 'compliance','gov_consultor',   ARRAY['documentos','admin'],     ARRAY['norma','descricao','vigencia','impacto','setor','acao_necessaria'],                   'optional', 0.5,'{}', 750),
  ('relatorio_economico',          'externo',NULL,'Relatório Econômico',                'macro',    'bcb_ibge',         ARRAY['estrategia','financeiro'],ARRAY['indicador','valor','variacao','impacto_setor','previsao'],                          'optional', 0.5,'{}', 760)
ON CONFLICT (id) DO NOTHING;

-- ── ESTRATÉGIA ───────────────────────────────────────────────────────────────
INSERT INTO public.knowledge_document_types
  (id, domain_id, subdomain_id, name, type, created_by, consumed_by, fields, status, coverage_weight, tags, sort_order)
VALUES
  ('plano_estrategico',    'estrategia',NULL,'Plano Estratégico',        'strategy', 'documentos_agent', ARRAY['estrategia','admin'],       ARRAY['horizonte','objetivos','iniciativas','kpis','responsaveis','revisao'],              'generated',0.9,ARRAY['estratégico'], 810),
  ('okrs_metas',           'estrategia',NULL,'OKRs / Metas Trimestrais', 'goals',    'estrategia_agent', ARRAY['all'],                      ARRAY['objetivo','key_results','baseline','target','atual','status'],                     'generated',0.9,ARRAY['estratégico'], 820),
  ('analise_cenarios',     'estrategia',NULL,'Análise de Cenários',      'scenario', 'estrategia_agent', ARRAY['estrategia','financeiro'],  ARRAY['cenario','premissas','projecao_receita','projecao_custo','probabilidade','recomendacao'],'generated',0.7,ARRAY['estratégico'],830),
  ('relatorio_lucratividade','estrategia',NULL,'Relatório de Lucratividade','profit', 'estrategia_agent', ARRAY['estrategia','compras'],     ARRAY['produto','receita','custo_total','margem','lucro_hora','ranking'],                  'generated',0.8,ARRAY['estratégico'], 840),
  ('benchmark_mercado',    'estrategia',NULL,'Benchmark de Mercado',     'intel',    'documentos_agent', ARRAY['estrategia','clientes'],    ARRAY['metrica','meu_valor','media_mercado','top_quartil','gap','acao'],                  'generated',0.7,ARRAY['estratégico'], 850),
  ('analise_investimento', 'estrategia',NULL,'Análise de Investimento',  'capex',    'estrategia_agent', ARRAY['financeiro','admin'],       ARRAY['investimento','custo','beneficios','payback','roi','riscos','recomendacao'],       'generated',0.6,ARRAY['estratégico'], 860),
  ('mapa_riscos',          'estrategia',NULL,'Mapa de Riscos',           'risk',     'estrategia_agent', ARRAY['all'],                      ARRAY['risco','probabilidade','impacto','mitigacao','responsavel','status'],               'generated',0.6,ARRAY['estratégico'], 870)
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. SEED: AGENT CATALOG (6 agents; idempotent upsert)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.agent_catalog
  (slug, name, description, prompt_name, landing_slug, required_context, tier_required, is_active)
VALUES
  ('compras',    'Agente de Compras',    'Gestão de fornecedores, pedidos de compra, inventário e cotações',    'agents/compras',    'landing/compras',    '["cadastro_fornecedores","controle_inventario","ordem_compra"]',          'BASIC', true),
  ('financeiro', 'Agente Financeiro',   'Fluxo de caixa, DRE, análise de lucratividade e cenários financeiros', 'agents/financeiro', 'landing/financeiro', '["fluxo_caixa_diario","dre_mensal","fatura_nota_fiscal"]',               'BASIC', true),
  ('agenda',     'Agente de Agenda',    'Agendamento, roteirização, planejamento de produção e equipe',          'agents/agenda',     'landing/agenda',     '["organograma","plano_producao","registro_ponto","ferias_licencas"]',    'BASIC', true),
  ('documentos', 'Agente de Documentos','Geração e gestão de contratos, propostas, NFs e documentos legais',    'agents/documentos', 'landing/documentos', '["ficha_cadastral","perfil_empresarial","termos_lgpd"]',                 'BASIC', true),
  ('estrategia', 'Agente de Estratégia','Análise estratégica, OKRs, cenários e benchmarking de mercado',        'agents/estrategia', 'landing/estrategia', '["plano_estrategico","okrs_metas","dre_mensal","pipeline_vendas"]',      'PRO',   true),
  ('clientes',   'Agente de Clientes',  'CRM, análise de churn, NPS e inteligência de clientes',               'agents/clientes',   'landing/clientes',   '["ficha_cliente","historico_pedidos","pesquisa_nps"]',                  'BASIC', true)
ON CONFLICT (slug) DO UPDATE SET
  name             = EXCLUDED.name,
  description      = EXCLUDED.description,
  prompt_name      = EXCLUDED.prompt_name,
  landing_slug     = EXCLUDED.landing_slug,
  required_context = EXCLUDED.required_context,
  tier_required    = EXCLUDED.tier_required,
  is_active        = EXCLUDED.is_active,
  updated_at       = now();


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. SEED: AGENT REQUIREMENTS (from agent_readiness in JSON ontology)
-- ─────────────────────────────────────────────────────────────────────────────

-- compras  (coverage_threshold: 0.85)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('compras','cadastro_fornecedores',         'minimum',      0.85),
  ('compras','controle_inventario',           'minimum',      0.85),
  ('compras','ordem_compra',                  'minimum',      0.85),
  ('compras','cotacao_rfq',                   'nice_to_have', 0.85),
  ('compras','contrato_fornecimento',         'nice_to_have', 0.85),
  ('compras','avaliacao_fornecedor',          'nice_to_have', 0.85),
  ('compras','monitoramento_precos_mercado',  'nice_to_have', 0.85)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;

-- financeiro  (coverage_threshold: 0.90)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('financeiro','fluxo_caixa_diario',  'minimum',      0.90),
  ('financeiro','dre_mensal',          'minimum',      0.90),
  ('financeiro','fatura_nota_fiscal',  'minimum',      0.90),
  ('financeiro','folha_pagamento',     'nice_to_have', 0.90),
  ('financeiro','projecao_caixa',      'nice_to_have', 0.90),
  ('financeiro','balanco_patrimonial', 'nice_to_have', 0.90)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;

-- documentos  (coverage_threshold: 0.80)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('documentos','ficha_cadastral',    'minimum', 0.80),
  ('documentos','perfil_empresarial', 'minimum', 0.80),
  ('documentos','termos_lgpd',        'minimum', 0.80)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;

-- estrategia  (coverage_threshold: 0.70)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('estrategia','plano_estrategico',    'minimum',      0.70),
  ('estrategia','okrs_metas',           'minimum',      0.70),
  ('estrategia','dre_mensal',           'minimum',      0.70),
  ('estrategia','pipeline_vendas',      'minimum',      0.70),
  ('estrategia','benchmark_mercado',    'nice_to_have', 0.70),
  ('estrategia','pesquisa_nps',         'nice_to_have', 0.70),
  ('estrategia','analise_investimento', 'nice_to_have', 0.70),
  ('estrategia','analise_concorrencia', 'nice_to_have', 0.70)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;

-- clientes  (coverage_threshold: 0.80)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('clientes','ficha_cliente',     'minimum',      0.80),
  ('clientes','historico_pedidos', 'minimum',      0.80),
  ('clientes','pesquisa_nps',      'minimum',      0.80),
  ('clientes','skills_matrix',     'nice_to_have', 0.80),
  ('clientes','pesquisa_clima',    'nice_to_have', 0.80)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;

-- agenda  (coverage_threshold: 0.75)
INSERT INTO public.knowledge_agent_requirements (agent_slug, document_type_id, requirement_type, coverage_threshold) VALUES
  ('agenda','organograma',          'minimum',      0.75),
  ('agenda','plano_producao',       'minimum',      0.75),
  ('agenda','registro_ponto',       'minimum',      0.75),
  ('agenda','ferias_licencas',      'minimum',      0.75),
  ('agenda','relatorio_capacidade', 'nice_to_have', 0.75),
  ('agenda','skills_matrix',        'nice_to_have', 0.75)
ON CONFLICT (agent_slug, document_type_id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 8. SEED: CROSS-AGENT ROUTINES (5 workflows from JSON ontology)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, trigger_domain, trigger_document_id, trigger_status, trigger_condition, steps) VALUES
  (
    'project_wrap', 'Project Wrap',
    'agenda', NULL, '100%', NULL,
    '[
      {"step":1,"agent":"documentos","action":"generate_invoice","output":"fatura_nota_fiscal"},
      {"step":2,"agent":"compras",   "action":"schedule_equipment_return","output":"ordem_compra"},
      {"step":3,"agent":"documentos","action":"update_portfolio","output":"portfolio_update"},
      {"step":4,"agent":"documentos","action":"draft_testimonial_request","output":"testimonial_request"}
    ]'
  ),
  (
    'new_event_confirmed', 'New Event Confirmed',
    'operacoes', 'contrato_venda', 'signed', NULL,
    '[
      {"step":1,"agent":"agenda",    "action":"create_event_timeline","output":"cronograma_evento"},
      {"step":2,"agent":"compras",   "action":"preorder_ingredients","output":"ordem_compra"},
      {"step":3,"agent":"financeiro","action":"generate_deposit_invoice","output":"fatura_nota_fiscal"},
      {"step":4,"agent":"agenda",    "action":"schedule_staff","output":"plano_producao"}
    ]'
  ),
  (
    'churn_prevention', 'Churn Prevention',
    'operacoes', 'relatorio_inadimplencia', NULL, '45_days_no_purchase',
    '[
      {"step":1,"agent":"agenda",    "action":"schedule_checkin_call","output":"evento"},
      {"step":2,"agent":"documentos","action":"draft_we_miss_you_offer","output":"proposta_comercial"},
      {"step":3,"agent":"financeiro","action":"calculate_discount_breakeven","output":"analise_cenarios"},
      {"step":4,"agent":"compras",   "action":"verify_equipment_status","output":"controle_inventario"}
    ]'
  ),
  (
    'price_spike_response', 'Price Spike Response',
    'operacoes', 'cotacao_rfq', NULL, 'price_increase_>15%',
    '[
      {"step":1,"agent":"financeiro","action":"recalculate_costs","output":"relatorio_lucratividade"},
      {"step":2,"agent":"estrategia","action":"suggest_price_adjustment","output":"analise_cenarios"},
      {"step":3,"agent":"documentos","action":"update_menus_quotes","output":"proposta_comercial"}
    ]'
  ),
  (
    'monthly_close', 'Monthly Close',
    'system', NULL, NULL, 'last_day_of_month',
    '[
      {"step":1,"agent":"financeiro","action":"generate_reports","output":"dre_mensal"},
      {"step":2,"agent":"compras",   "action":"reconcile_inventory","output":"controle_inventario"},
      {"step":3,"agent":"documentos","action":"update_knowledge_base","output":"ficha_tecnica"},
      {"step":4,"agent":"estrategia","action":"run_trend_analysis","output":"relatorio_lucratividade"}
    ]'
  )
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 9. RPC: get_knowledge_coverage(p_client_id)
-- Returns weighted coverage % per domain and sub-domain, plus per-document status.
-- Coverage scoring formula (from JSON schema):
--   effective_weight = coverage_weight × status_multiplier
--     where status_multiplier: required=1.0, optional=0.6, generated=0.8
--   score = Σ(effective_weight × status_score) / Σ(effective_weight)
--     where status_score: complete=1.0, partial=0.5, missing=0.0
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_knowledge_coverage(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, vector_db
AS $$
DECLARE
  v_result jsonb;
BEGIN
  -- Only authenticated clients may read their own coverage; service role bypasses
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read coverage for another client';
  END IF;

  WITH doc_status AS (
    SELECT
      kdt.id              AS document_type_id,
      kdt.domain_id,
      kdt.subdomain_id,
      kdt.name,
      kdt.type,
      kdt.status          AS doc_status,
      kdt.coverage_weight,
      kdt.tags,
      kdt.consumed_by,
      COALESCE(ckd.status, 'missing') AS client_status
    FROM public.knowledge_document_types kdt
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kdt.id
      AND ckd.client_id        = p_client_id
  ),
  weighted AS (
    SELECT
      domain_id,
      subdomain_id,
      document_type_id,
      name,
      doc_status,
      client_status,
      tags,
      consumed_by,
      -- effective weight = coverage_weight × status multiplier
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END AS effective_weight,
      -- earned weight = effective_weight × completion score
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END * CASE client_status
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS earned_weight
    FROM doc_status
  ),
  group_scores AS (
    SELECT
      domain_id,
      subdomain_id,
      ROUND(
        CASE WHEN SUM(effective_weight) = 0 THEN 0
             ELSE SUM(earned_weight) / SUM(effective_weight)
        END * 100
      )::int AS coverage_pct,
      jsonb_agg(
        jsonb_build_object(
          'id',            document_type_id,
          'name',          name,
          'type',          doc_status,
          'client_status', client_status,
          'tags',          tags,
          'consumed_by',   consumed_by
        ) ORDER BY document_type_id
      ) AS documents
    FROM weighted
    GROUP BY domain_id, subdomain_id
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'domain_id',    domain_id,
      'subdomain_id', subdomain_id,
      'coverage_pct', coverage_pct,
      'is_covered',   (coverage_pct >= 60),
      'documents',    documents
    ) ORDER BY domain_id, COALESCE(subdomain_id, '')
  )
  INTO v_result
  FROM group_scores;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 10. RPC: get_agent_readiness(p_client_id)
-- Returns status (ready | partial | blocked) and capability (full | partial)
-- per agent, based on minimum vs nice_to_have document coverage.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_agent_readiness(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_result jsonb;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read readiness for another client';
  END IF;

  WITH agent_doc_status AS (
    -- Join requirements with client document inventory
    SELECT
      kar.agent_slug,
      kar.document_type_id,
      kar.requirement_type,
      kar.coverage_threshold,
      kdt.name            AS doc_name,
      kdt.coverage_weight,
      COALESCE(ckd.status, 'missing') AS client_doc_status,
      CASE COALESCE(ckd.status, 'missing')
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS status_score
    FROM public.knowledge_agent_requirements kar
    JOIN public.knowledge_document_types kdt
      ON  kdt.id = kar.document_type_id
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kar.document_type_id
      AND ckd.client_id        = p_client_id
  ),
  agent_scores AS (
    -- Weighted coverage per agent per requirement_type
    SELECT
      agent_slug,
      requirement_type,
      MAX(coverage_threshold) AS coverage_threshold,
      ROUND(
        SUM(status_score * coverage_weight) / NULLIF(SUM(coverage_weight), 0) * 100
      )::int AS weighted_pct,
      -- Collect names of missing minimum docs for the gap message
      array_agg(doc_name ORDER BY doc_name)
        FILTER (WHERE requirement_type = 'minimum' AND client_doc_status = 'missing')
        AS missing_doc_names
    FROM agent_doc_status
    GROUP BY agent_slug, requirement_type
  ),
  agent_summary AS (
    SELECT
      s.agent_slug,
      cat.name          AS agent_name,
      cat.tier_required,
      (cea.enabled_at IS NOT NULL) AS is_enabled,
      MAX(CASE WHEN s.requirement_type = 'minimum'      THEN s.weighted_pct   ELSE 0   END) AS min_pct,
      MAX(CASE WHEN s.requirement_type = 'nice_to_have' THEN s.weighted_pct   ELSE 0   END) AS nice_pct,
      MAX(s.coverage_threshold) AS coverage_threshold,
      -- Flatten missing_doc_names arrays (one entry per requirement_type row)
      array_remove(
        array_agg(DISTINCT elem)
          FILTER (WHERE s.requirement_type = 'minimum'),
        NULL
      ) AS missing_names
    FROM agent_scores s
    CROSS JOIN LATERAL unnest(COALESCE(s.missing_doc_names, ARRAY[]::text[])) AS elem
    JOIN public.agent_catalog cat ON cat.slug = s.agent_slug
    LEFT JOIN public.client_enabled_agents cea
      ON cea.agent_slug = s.agent_slug AND cea.client_id = p_client_id
    GROUP BY s.agent_slug, cat.name, cat.tier_required, cea.enabled_at
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'agent_slug',       agent_slug,
      'agent_name',       agent_name,
      'tier_required',    tier_required,
      'is_enabled',       is_enabled,
      'status',           CASE
                            WHEN min_pct >= (coverage_threshold * 100) THEN 'ready'
                            WHEN min_pct > 0                            THEN 'partial'
                            ELSE                                             'blocked'
                          END,
      'capability',       CASE WHEN nice_pct >= 70 THEN 'full' ELSE 'partial' END,
      'min_coverage_pct', min_pct,
      'nice_coverage_pct',nice_pct,
      'missing_docs',     COALESCE(to_jsonb(missing_names), '[]'::jsonb)
    ) ORDER BY agent_slug
  )
  INTO v_result
  FROM agent_summary;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 11. RPC: upsert_client_document(...)
-- Called by integrations, upload handlers, and agents to mark a document
-- as present (partial or complete) for the calling client.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.upsert_client_document(
  p_document_type_id  text,
  p_status            text    DEFAULT 'complete',
  p_source            text    DEFAULT 'upload',
  p_field_coverage    jsonb   DEFAULT '{}',
  p_metadata          jsonb   DEFAULT '{}'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_client_id uuid;
  v_result    jsonb;
BEGIN
  v_client_id := public.get_my_client_id();
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Client not authenticated';
  END IF;

  IF p_status NOT IN ('missing','partial','complete') THEN
    RAISE EXCEPTION 'Invalid status: %. Must be missing | partial | complete', p_status;
  END IF;

  INSERT INTO public.client_knowledge_documents
    (client_id, document_type_id, status, source, field_coverage, metadata, updated_at)
  VALUES
    (v_client_id, p_document_type_id, p_status, p_source, p_field_coverage, p_metadata, now())
  ON CONFLICT (client_id, document_type_id) DO UPDATE SET
    status         = EXCLUDED.status,
    source         = EXCLUDED.source,
    field_coverage = EXCLUDED.field_coverage,
    metadata       = EXCLUDED.metadata,
    updated_at     = now()
  RETURNING jsonb_build_object(
    'document_type_id', document_type_id,
    'status',           status,
    'source',           source,
    'updated_at',       updated_at
  ) INTO v_result;

  RETURN v_result;
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 12. RPC: bootstrap_knowledge_from_onboarding(p_client_id)
-- Seeds initial client_knowledge_documents from data already collected:
--   • clientes_blu.company_profile  → ficha_cadastral, perfil_empresarial
--   • vector_db.documents (website) → posicionamento
--   • team_structure.key_contacts   → organograma
--   • integration_configs presence  → ERP-backed documents (partial)
--   • client_data_sources synced    → upgrades matching docs to complete
-- Idempotent (ON CONFLICT DO NOTHING / UPDATE only if better status).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.bootstrap_knowledge_from_onboarding(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, vector_db
AS $$
DECLARE
  v_cp        jsonb;
  v_ts        jsonb;
  v_seeded    int := 0;
BEGIN
  SELECT company_profile, team_structure
    INTO v_cp, v_ts
    FROM public.clientes_blu
   WHERE client_id = p_client_id;

  -- ── Identidade: ficha_cadastral ─────────────────────────────────
  IF (v_cp->>'legal_name') IS NOT NULL OR (v_cp->>'industry') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ── Identidade: perfil_empresarial ──────────────────────────────
  IF (v_cp->>'industry') IS NOT NULL AND (v_cp->>'employee_count_range') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'perfil_empresarial', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ── Identidade: posicionamento (from website context in RAG) ────
  IF EXISTS (
    SELECT 1 FROM vector_db.documents
     WHERE client_id = p_client_id AND source = 'onboarding.website_context'
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'posicionamento', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ── Pessoas: organograma (from team_structure.key_contacts) ─────
  IF jsonb_array_length(COALESCE(v_ts->'key_contacts', '[]'::jsonb)) > 0 THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'organograma', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ── ERP/commerce integration present → seed ERP-backed docs as partial
  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny','shopify','vtex','nuvemshop')
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'historico_pedidos',  'partial', 'erp'),
      (p_client_id, 'catalogo_produtos',  'partial', 'erp'),
      (p_client_id, 'fluxo_caixa_diario', 'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 3;
  END IF;

  -- ── ERP with purchasing features → supplier/inventory docs ──────
  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny')
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'cadastro_fornecedores', 'partial', 'erp'),
      (p_client_id, 'controle_inventario',   'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 2;
  END IF;

  -- ── client_data_sources synced → upgrade status to 'complete' ───
  UPDATE public.client_knowledge_documents ckd
     SET status     = 'complete',
         source     = 'erp_synced',
         updated_at = now()
    FROM public.client_data_sources cds
   WHERE cds.client_id = p_client_id::text
     AND cds.sync_status IN ('ready','success')
     AND ckd.client_id = p_client_id
     AND ckd.document_type_id = CASE cds.resource_type
           WHEN 'orders'       THEN 'historico_pedidos'
           WHEN 'pedidos'      THEN 'historico_pedidos'
           WHEN 'products'     THEN 'catalogo_produtos'
           WHEN 'inventory'    THEN 'controle_inventario'
           WHEN 'estoque'      THEN 'controle_inventario'
           WHEN 'customers'    THEN 'ficha_cliente'
           WHEN 'clientes'     THEN 'ficha_cliente'
           WHEN 'fornecedores' THEN 'cadastro_fornecedores'
           ELSE NULL
         END
     AND ckd.status != 'complete';  -- only upgrade, never downgrade

  RETURN jsonb_build_object('client_id', p_client_id, 'docs_seeded', v_seeded);
END;
$$;
