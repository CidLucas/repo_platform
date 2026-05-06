-- ═══════════════════════════════════════════════════════════════════════
-- BASELINE MIGRATION — reverse-engineered from live DB on 2026-04-30
-- Replaces all previous migration files.
-- ═══════════════════════════════════════════════════════════════════════


-- ────────────────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ────────────────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS wrappers WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;


-- ────────────────────────────────────────────────────────────────────────────
-- SCHEMAS
-- ────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS analytics_v2;
CREATE SCHEMA IF NOT EXISTS vector_db;
CREATE SCHEMA IF NOT EXISTS fdw;

GRANT USAGE ON SCHEMA fdw TO service_role;
GRANT ALL   ON SCHEMA fdw TO service_role;


-- ────────────────────────────────────────────────────────────────────────────
-- TABLES
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.kpi_catalog (
  slug text NOT NULL,
  dimension text NOT NULL,
  label text NOT NULL,
  formula text NOT NULL,
  unit text DEFAULT 'number'::text NOT NULL,
  is_leading boolean DEFAULT false NOT NULL,
  tier_required text DEFAULT 'BASIC'::text NOT NULL,
  data_status text DEFAULT 'live'::text NOT NULL,
  rpc_column text,
  description text,
  references_url text,
  sort_order integer DEFAULT 0 NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT kpi_catalog_pkey PRIMARY KEY (slug)
);

CREATE TABLE IF NOT EXISTS public.agent_catalog (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  category text,
  icon text,
  agent_config jsonb DEFAULT '{}'::jsonb NOT NULL,
  prompt_name text NOT NULL,
  required_context jsonb DEFAULT '[]'::jsonb,
  required_files jsonb DEFAULT '{}'::jsonb,
  requires_google boolean DEFAULT false,
  tier_required text DEFAULT 'BASIC'::text,
  landing_slug text,
  workflow_graph jsonb,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT agent_catalog_pkey PRIMARY KEY (id)
  , CONSTRAINT agent_catalog_slug_key UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS public.clientes_blu (
  client_id uuid DEFAULT gen_random_uuid() NOT NULL,
  api_key text,
  nome_empresa text DEFAULT 'Empresa'::text NOT NULL,
  tipo_cliente text DEFAULT 'standard'::text,
  tier text DEFAULT 'free'::text,
  collection_rag text DEFAULT 'default_collection'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  external_user_id text,
  onboarding_state jsonb DEFAULT '{}'::jsonb,
  onboarding_completed_at timestamp with time zone,
  company_profile jsonb DEFAULT '{}'::jsonb,
  brand_voice jsonb DEFAULT '{}'::jsonb,
  team_structure jsonb DEFAULT '{}'::jsonb,
  policies jsonb DEFAULT '{}'::jsonb,
  data_schema jsonb DEFAULT '{}'::jsonb,
  available_tools jsonb DEFAULT '{}'::jsonb,
  cpf_cnpj text
  , CONSTRAINT clientes_blu_pkey PRIMARY KEY (client_id)
  , CONSTRAINT clientes_blu_api_key_key UNIQUE (api_key)
  , CONSTRAINT clientes_blu_external_user_id_key UNIQUE (external_user_id)
);

CREATE TABLE IF NOT EXISTS public.credencial_servico_externo (
  id bigint DEFAULT nextval('credencial_servico_externo_id_seq'::regclass) NOT NULL,
  client_id text NOT NULL,
  tipo text,
  credenciais jsonb DEFAULT '{}'::jsonb NOT NULL,
  nome text,
  ativo boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  connection_metadata jsonb DEFAULT '{}'::jsonb,
  nome_servico text,
  tipo_servico text,
  status text DEFAULT 'pending'::text,
  vault_key_id uuid
  , CONSTRAINT credencial_servico_externo_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.bigquery_servers (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id text NOT NULL,
  server_name text NOT NULL,
  project_id text NOT NULL,
  dataset_id text NOT NULL,
  vault_key_id uuid NOT NULL,
  location text DEFAULT 'US'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
  , CONSTRAINT bigquery_servers_pkey PRIMARY KEY (id)
  , CONSTRAINT bigquery_servers_client_id_key UNIQUE (client_id)
  , CONSTRAINT bigquery_servers_server_name_key UNIQUE (server_name)
);

CREATE TABLE IF NOT EXISTS public.conversa (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT conversa_pkey PRIMARY KEY (id)
  , CONSTRAINT conversa_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.audit_log (
  id bigint DEFAULT nextval('audit_log_id_seq'::regclass) NOT NULL,
  client_id uuid,
  actor_id text,
  action text NOT NULL,
  entity_type text,
  entity_id text,
  payload jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT audit_log_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.approval_requests (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  requested_by text,
  action_type text NOT NULL,
  payload jsonb DEFAULT '{}'::jsonb NOT NULL,
  status text DEFAULT 'pending'::text NOT NULL,
  decided_by text,
  decided_at timestamp with time zone,
  expires_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT approval_requests_pkey PRIMARY KEY (id)
  , CONSTRAINT approval_requests_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.calendar_settings (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid NOT NULL,
  calendar_id text,
  enabled boolean DEFAULT false NOT NULL,
  range_days integer DEFAULT 30 NOT NULL,
  timezone text DEFAULT 'America/Sao_Paulo'::text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT calendar_settings_pkey PRIMARY KEY (id)
  , CONSTRAINT calendar_settings_client_id_key UNIQUE (client_id)
  , CONSTRAINT calendar_settings_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.client_dimension_kpis (
  client_id uuid NOT NULL,
  dimension text NOT NULL,
  slug text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT client_dimension_kpis_pkey PRIMARY KEY (client_id, dimension, slug)
  , CONSTRAINT client_dimension_kpis_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
  , CONSTRAINT client_dimension_kpis_slug_fkey FOREIGN KEY (slug) REFERENCES public.kpi_catalog(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.client_enabled_agents (
  client_id uuid NOT NULL,
  agent_slug text NOT NULL,
  config jsonb DEFAULT '{}'::jsonb,
  enabled_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT client_enabled_agents_pkey PRIMARY KEY (client_id, agent_slug)
  , CONSTRAINT client_enabled_agents_agent_slug_fkey FOREIGN KEY (agent_slug) REFERENCES public.agent_catalog(slug) ON DELETE CASCADE
  , CONSTRAINT client_enabled_agents_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.client_insights (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  dimension text NOT NULL,
  title text NOT NULL,
  body text,
  severity text DEFAULT 'info'::text,
  dismissed boolean DEFAULT false,
  dismissed_at timestamp with time zone,
  generated_at timestamp with time zone DEFAULT now() NOT NULL,
  expires_at timestamp with time zone
  , CONSTRAINT client_insights_pkey PRIMARY KEY (id)
  , CONSTRAINT client_insights_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.client_routines (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid NOT NULL,
  routine_id text NOT NULL,
  notify_channel text DEFAULT 'app'::text NOT NULL,
  config jsonb DEFAULT '{}'::jsonb,
  active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT client_routines_pkey PRIMARY KEY (id)
  , CONSTRAINT client_routines_client_id_routine_id_key UNIQUE (client_id, routine_id)
  , CONSTRAINT client_routines_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.data_source_mappings (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  credential_id uuid NOT NULL,
  resource_type character varying(50) NOT NULL,
  source_columns jsonb DEFAULT '[]'::jsonb NOT NULL,
  mapping jsonb DEFAULT '{}'::jsonb NOT NULL,
  unmapped_columns jsonb DEFAULT '[]'::jsonb NOT NULL,
  confidence_scores jsonb DEFAULT '{}'::jsonb NOT NULL,
  status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT data_source_mappings_pkey PRIMARY KEY (id)
  , CONSTRAINT unique_credential_resource UNIQUE (credential_id, resource_type)
);

CREATE TABLE IF NOT EXISTS public.frontend_events (
  id bigint DEFAULT nextval('frontend_events_id_seq'::regclass) NOT NULL,
  client_id uuid,
  event_name text NOT NULL,
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT frontend_events_pkey PRIMARY KEY (id)
  , CONSTRAINT frontend_events_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.integration_configs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  provider text NOT NULL,
  config jsonb DEFAULT '{}'::jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT integration_configs_pkey PRIMARY KEY (id)
  , CONSTRAINT integration_configs_client_id_provider_key UNIQUE (client_id, provider)
  , CONSTRAINT integration_configs_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.integration_tokens (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  provider text NOT NULL,
  account_email text DEFAULT ''::text NOT NULL,
  access_token_encrypted text,
  refresh_token_encrypted text,
  token_type text DEFAULT 'Bearer'::text,
  scopes text[],
  is_default boolean DEFAULT false,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT integration_tokens_pkey PRIMARY KEY (id)
  , CONSTRAINT integration_tokens_client_id_provider_account_email_key UNIQUE (client_id, provider, account_email)
  , CONSTRAINT integration_tokens_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.messages (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid NOT NULL,
  session_id uuid,
  channel text NOT NULL,
  direction text,
  role text,
  body text,
  media_urls text[],
  status text DEFAULT 'received'::text,
  provider text,
  sender_ref text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT messages_pkey PRIMARY KEY (id)
  , CONSTRAINT messages_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
  , CONSTRAINT messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.conversa(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS public.nps_responses (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  score integer NOT NULL,
  comment text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT nps_responses_pkey PRIMARY KEY (id)
  , CONSTRAINT nps_responses_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.report_schedules (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  name text NOT NULL,
  report_type text NOT NULL,
  cron_expr text,
  recipients text[],
  config jsonb DEFAULT '{}'::jsonb,
  active boolean DEFAULT true,
  last_run_at timestamp with time zone,
  next_run_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT report_schedules_pkey PRIMARY KEY (id)
  , CONSTRAINT report_schedules_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.report_runs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  schedule_id uuid,
  client_id uuid,
  status text DEFAULT 'pending'::text NOT NULL,
  output_url text,
  error text,
  started_at timestamp with time zone DEFAULT now(),
  completed_at timestamp with time zone,
  metadata jsonb DEFAULT '{}'::jsonb
  , CONSTRAINT report_runs_pkey PRIMARY KEY (id)
  , CONSTRAINT report_runs_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
  , CONSTRAINT report_runs_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.report_schedules(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.standalone_agent_sessions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid NOT NULL,
  agent_catalog_id uuid NOT NULL,
  session_id text NOT NULL,
  config_status text DEFAULT 'configuring'::text,
  collected_context jsonb DEFAULT '{}'::jsonb,
  uploaded_file_ids uuid[] DEFAULT ARRAY[]::uuid[],
  uploaded_document_ids uuid[] DEFAULT ARRAY[]::uuid[],
  google_account_email text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT standalone_agent_sessions_pkey PRIMARY KEY (id)
  , CONSTRAINT standalone_agent_sessions_session_id_key UNIQUE (session_id)
  , CONSTRAINT standalone_agent_sessions_agent_catalog_id_fkey FOREIGN KEY (agent_catalog_id) REFERENCES public.agent_catalog(id) ON DELETE RESTRICT
  , CONSTRAINT standalone_agent_sessions_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.uploaded_files_metadata (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  file_name text NOT NULL,
  storage_path text NOT NULL,
  bucket text DEFAULT 'file-uploads'::text NOT NULL,
  mime_type text,
  size_bytes bigint,
  status text DEFAULT 'uploaded'::text,
  metadata jsonb DEFAULT '{}'::jsonb,
  content_hash text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
  , CONSTRAINT uploaded_files_metadata_pkey PRIMARY KEY (id)
  , CONSTRAINT uploaded_files_metadata_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.bigquery_foreign_tables (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id text NOT NULL,
  table_name text NOT NULL,
  bigquery_table text NOT NULL,
  server_name text NOT NULL,
  columns jsonb NOT NULL,
  location text DEFAULT 'US'::text,
  created_at timestamp with time zone DEFAULT now()
  , CONSTRAINT bigquery_foreign_tables_pkey PRIMARY KEY (id)
  , CONSTRAINT bigquery_foreign_tables_client_id_table_name_key UNIQUE (client_id, table_name)
  , CONSTRAINT fk_server FOREIGN KEY (server_name) REFERENCES public.bigquery_servers(server_name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.client_data_sources (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id text NOT NULL,
  credential_id bigint,
  source_type text NOT NULL,
  resource_type text NOT NULL,
  storage_type text NOT NULL,
  storage_location text NOT NULL,
  column_mapping jsonb,
  source_columns jsonb,
  source_sample_data jsonb,
  sync_status text DEFAULT 'pending'::text,
  last_synced_at timestamp with time zone,
  atualizado_em timestamp with time zone DEFAULT now(),
  error_message text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  unmapped_columns jsonb,
  needs_review_columns jsonb,
  match_confidence jsonb,
  detected_entity_context text,
  auto_column_mapping jsonb,
  ignored_columns text[],
  is_auto_generated boolean DEFAULT false,
  reviewed_at timestamp with time zone,
  user_column_changes jsonb,
  ingestion_quality jsonb
  , CONSTRAINT client_data_sources_pkey PRIMARY KEY (id)
  , CONSTRAINT unique_client_source_resource UNIQUE (client_id, source_type, resource_type)
  , CONSTRAINT client_data_sources_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES public.credencial_servico_externo(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS analytics_v2.dim_datas (
  data_id bigint NOT NULL,
  data date NOT NULL,
  ano integer NOT NULL,
  mes integer NOT NULL,
  dia integer NOT NULL,
  numero_dia_semana integer,
  numero_semana_ano integer,
  numero_semestre integer,
  periodo_trimestral text,
  created_at timestamp with time zone DEFAULT now()
  , CONSTRAINT dim_datas_pkey PRIMARY KEY (data_id)
  , CONSTRAINT dim_datas_data_key UNIQUE (data)
);

CREATE TABLE IF NOT EXISTS analytics_v2.dim_clientes (
  cliente_id bigint NOT NULL,
  client_id uuid,
  cpf_cnpj text,
  nome text,
  telefone text,
  endereco_cidade text,
  endereco_uf text,
  total_pedidos bigint DEFAULT 0,
  receita_total numeric DEFAULT 0,
  ticket_medio numeric DEFAULT 0,
  quantidade_total numeric DEFAULT 0,
  frequencia_mensal numeric,
  dias_recencia integer,
  data_primeira_compra date,
  data_ultima_compra date,
  pontuacao_cluster numeric,
  nivel_cluster text,
  atualizado_em timestamp with time zone DEFAULT now()
  , CONSTRAINT dim_clientes_pkey PRIMARY KEY (cliente_id)
  , CONSTRAINT dim_clientes_client_cpf_uniq UNIQUE (client_id, cpf_cnpj)
  , CONSTRAINT dim_clientes_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analytics_v2.dim_fornecedores (
  fornecedor_id bigint NOT NULL,
  client_id uuid,
  cnpj text,
  nome text,
  telefone text,
  endereco_cidade text,
  endereco_uf text,
  total_pedidos_recebidos bigint DEFAULT 0,
  receita_total numeric DEFAULT 0,
  ticket_medio numeric DEFAULT 0,
  total_produtos_fornecidos bigint DEFAULT 0,
  frequencia_mensal numeric,
  dias_recencia integer,
  data_primeira_transacao date,
  data_ultima_transacao date,
  pontuacao_cluster numeric,
  nivel_cluster text,
  atualizado_em timestamp with time zone DEFAULT now()
  , CONSTRAINT dim_fornecedores_pkey PRIMARY KEY (fornecedor_id)
  , CONSTRAINT dim_fornecedores_client_cnpj_uniq UNIQUE (client_id, cnpj)
  , CONSTRAINT dim_fornecedores_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analytics_v2.dim_inventory (
  inventory_id bigint NOT NULL,
  client_id uuid,
  sku text,
  nome text,
  quantidade_total_vendida numeric DEFAULT 0,
  receita_total numeric DEFAULT 0,
  preco_medio numeric DEFAULT 0,
  total_pedidos bigint DEFAULT 0,
  quantidade_media_por_pedido numeric,
  frequencia_mensal numeric,
  dias_recencia integer,
  data_ultima_venda date,
  pontuacao_cluster numeric,
  nivel_cluster text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
  , CONSTRAINT dim_inventory_pkey PRIMARY KEY (inventory_id)
  , CONSTRAINT dim_inventory_client_sku_uniq UNIQUE (client_id, sku)
  , CONSTRAINT dim_inventory_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analytics_v2.fato_transacoes (
  transacao_id text NOT NULL,
  client_id uuid NOT NULL,
  data_competencia_id bigint,
  cliente_id bigint,
  fornecedor_id bigint,
  produto_id bigint,
  documento text,
  quantidade numeric,
  valor_unitario numeric,
  valor numeric,
  status text,
  created_at timestamp with time zone DEFAULT now()
  , CONSTRAINT fato_transacoes_pkey PRIMARY KEY (transacao_id, client_id)
  , CONSTRAINT fato_transacoes_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
  , CONSTRAINT fato_transacoes_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES analytics_v2.dim_clientes(cliente_id) ON DELETE SET NULL
  , CONSTRAINT fato_transacoes_data_competencia_id_fkey FOREIGN KEY (data_competencia_id) REFERENCES analytics_v2.dim_datas(data_id) ON DELETE SET NULL
  , CONSTRAINT fato_transacoes_fornecedor_id_fkey FOREIGN KEY (fornecedor_id) REFERENCES analytics_v2.dim_fornecedores(fornecedor_id) ON DELETE SET NULL
  , CONSTRAINT fato_transacoes_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES analytics_v2.dim_inventory(inventory_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS analytics_v2.etl_staging (
  job_id uuid NOT NULL,
  documento text,
  data_competencia_raw text,
  quantidade_raw text,
  valor_unitario_raw text,
  valor_raw text,
  status text,
  cliente_cpf_cnpj text,
  cliente_nome text,
  cliente_telefone text,
  cliente_cidade text,
  cliente_uf text,
  fornecedor_cnpj text,
  fornecedor_nome text,
  fornecedor_telefone text,
  fornecedor_cidade text,
  fornecedor_uf text,
  produto_sku text,
  produto_nome text
);

CREATE TABLE IF NOT EXISTS analytics_v2.reg_jobs (
  job_id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid,
  job_type text DEFAULT 'bigquery_sync'::text NOT NULL,
  credential_id bigint,
  resource_type text,
  sync_mode text DEFAULT 'incremental'::text,
  status text DEFAULT 'pending'::text NOT NULL,
  input_params jsonb DEFAULT '{}'::jsonb,
  output jsonb,
  rows_inserted bigint DEFAULT 0,
  progress_pct integer DEFAULT 0,
  error_message text,
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  duration_seconds numeric,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  retry_count integer DEFAULT 0 NOT NULL
  , CONSTRAINT reg_jobs_pkey PRIMARY KEY (job_id)
  , CONSTRAINT reg_jobs_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
  , CONSTRAINT reg_jobs_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES public.credencial_servico_externo(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS vector_db.documents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  client_id uuid NOT NULL,
  title text,
  file_name text NOT NULL,
  file_type text,
  storage_path text,
  source text DEFAULT 'upload'::text NOT NULL,
  processing_mode text DEFAULT 'simple'::text NOT NULL,
  status text DEFAULT 'pending'::text NOT NULL,
  scope text,
  category text,
  content_hash text,
  error_message text,
  chunk_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
  , CONSTRAINT documents_pkey PRIMARY KEY (id)
  , CONSTRAINT documents_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vector_db.document_chunks (
  id integer NOT NULL,
  document_id uuid NOT NULL,
  client_id uuid NOT NULL,
  content text NOT NULL,
  embedding extensions.halfvec,
  chunk_index integer DEFAULT 0 NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  fts tsvector,
  created_at timestamp with time zone DEFAULT now()
  , CONSTRAINT document_chunks_pkey PRIMARY KEY (id)
  , CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES vector_db.documents(id) ON DELETE CASCADE
);


-- ────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ────────────────────────────────────────────────────────────────────────────

CREATE INDEX idx_dim_clientes_client ON analytics_v2.dim_clientes USING btree (client_id);
CREATE UNIQUE INDEX idx_dim_clientes_cpf_cnpj ON analytics_v2.dim_clientes USING btree (client_id, cpf_cnpj) WHERE (cpf_cnpj IS NOT NULL);
CREATE UNIQUE INDEX dim_datas_data_key ON analytics_v2.dim_datas USING btree (data);
CREATE INDEX idx_dim_forn_client ON analytics_v2.dim_fornecedores USING btree (client_id);
CREATE INDEX idx_dim_inv_client ON analytics_v2.dim_inventory USING btree (client_id);
CREATE INDEX idx_etl_staging_job_id ON analytics_v2.etl_staging USING btree (job_id);
CREATE INDEX idx_fato_client ON analytics_v2.fato_transacoes USING btree (client_id);
CREATE INDEX idx_fato_cliente_dim ON analytics_v2.fato_transacoes USING btree (cliente_id);
CREATE INDEX idx_fato_data ON analytics_v2.fato_transacoes USING btree (data_competencia_id);
CREATE INDEX idx_fato_fornecedor ON analytics_v2.fato_transacoes USING btree (fornecedor_id);
CREATE INDEX idx_reg_jobs_client_status ON analytics_v2.reg_jobs USING btree (client_id, status);
CREATE INDEX idx_reg_jobs_created ON analytics_v2.reg_jobs USING btree (created_at DESC);
CREATE UNIQUE INDEX agent_catalog_slug_key ON public.agent_catalog USING btree (slug);
CREATE INDEX idx_approval_client_status ON public.approval_requests USING btree (client_id, status);
CREATE INDEX idx_audit_client ON public.audit_log USING btree (client_id);
CREATE INDEX idx_audit_created ON public.audit_log USING btree (created_at DESC);
CREATE UNIQUE INDEX bigquery_foreign_tables_client_id_table_name_key ON public.bigquery_foreign_tables USING btree (client_id, table_name);
CREATE UNIQUE INDEX bigquery_servers_client_id_key ON public.bigquery_servers USING btree (client_id);
CREATE UNIQUE INDEX bigquery_servers_server_name_key ON public.bigquery_servers USING btree (server_name);
CREATE UNIQUE INDEX calendar_settings_client_id_key ON public.calendar_settings USING btree (client_id);
CREATE INDEX idx_cds_client_id ON public.client_data_sources USING btree (client_id);
CREATE INDEX idx_cds_credential_id ON public.client_data_sources USING btree (credential_id);
CREATE UNIQUE INDEX unique_client_source_resource ON public.client_data_sources USING btree (client_id, source_type, resource_type);
CREATE INDEX idx_insights_client_active ON public.client_insights USING btree (client_id, dismissed, generated_at DESC);
CREATE UNIQUE INDEX client_routines_client_id_routine_id_key ON public.client_routines USING btree (client_id, routine_id);
CREATE UNIQUE INDEX clientes_blu_api_key_key ON public.clientes_blu USING btree (api_key);
CREATE UNIQUE INDEX clientes_blu_external_user_id_key ON public.clientes_blu USING btree (external_user_id);
CREATE INDEX idx_clientes_blu_api_key ON public.clientes_blu USING btree (api_key) WHERE (api_key IS NOT NULL);
CREATE INDEX idx_clientes_blu_client_id ON public.clientes_blu USING btree (client_id);
CREATE INDEX idx_clientes_blu_external_user ON public.clientes_blu USING btree (external_user_id);
CREATE INDEX idx_clientes_blu_external_user_id ON public.clientes_blu USING btree (external_user_id) WHERE (external_user_id IS NOT NULL);
CREATE INDEX idx_clientes_blu_onboarding_incomplete ON public.clientes_blu USING btree (client_id) WHERE (onboarding_completed_at IS NULL);
CREATE INDEX idx_credencial_client_id ON public.credencial_servico_externo USING btree (client_id);
CREATE INDEX idx_mappings_credential ON public.data_source_mappings USING btree (credential_id);
CREATE INDEX idx_mappings_resource ON public.data_source_mappings USING btree (resource_type);
CREATE INDEX idx_mappings_status ON public.data_source_mappings USING btree (status);
CREATE UNIQUE INDEX unique_credential_resource ON public.data_source_mappings USING btree (credential_id, resource_type);
CREATE INDEX idx_fe_client_event ON public.frontend_events USING btree (client_id, event_name);
CREATE INDEX idx_fe_created_at ON public.frontend_events USING btree (created_at DESC);
CREATE UNIQUE INDEX integration_configs_client_id_provider_key ON public.integration_configs USING btree (client_id, provider);
CREATE INDEX idx_tokens_client_provider ON public.integration_tokens USING btree (client_id, provider);
CREATE UNIQUE INDEX integration_tokens_client_id_provider_account_email_key ON public.integration_tokens USING btree (client_id, provider, account_email);
CREATE INDEX idx_messages_client ON public.messages USING btree (client_id, created_at DESC);
CREATE INDEX idx_messages_session ON public.messages USING btree (session_id) WHERE (session_id IS NOT NULL);
CREATE INDEX idx_nps_client ON public.nps_responses USING btree (client_id);
CREATE INDEX idx_report_runs_client ON public.report_runs USING btree (client_id, started_at DESC);
CREATE UNIQUE INDEX standalone_agent_sessions_session_id_key ON public.standalone_agent_sessions USING btree (session_id);
CREATE INDEX idx_uploaded_files_client ON public.uploaded_files_metadata USING btree (client_id);
CREATE INDEX idx_chunks_client ON vector_db.document_chunks USING btree (client_id);
CREATE INDEX idx_chunks_document ON vector_db.document_chunks USING btree (document_id);
CREATE INDEX idx_chunks_embedding ON vector_db.document_chunks USING hnsw (embedding halfvec_ip_ops);
CREATE INDEX idx_chunks_fts ON vector_db.document_chunks USING gin (fts);
CREATE INDEX idx_docs_client ON vector_db.documents USING btree (client_id);
CREATE INDEX idx_docs_content_hash ON vector_db.documents USING btree (content_hash) WHERE (content_hash IS NOT NULL);
CREATE INDEX idx_docs_status ON vector_db.documents USING btree (status);


-- ────────────────────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE analytics_v2.dim_clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_fornecedores ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.fato_transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.reg_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bigquery_foreign_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bigquery_servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_dimension_kpis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_enabled_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_routines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes_blu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversa ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.frontend_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kpi_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nps_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.standalone_agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_files_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_db.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_db.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own client" ON analytics_v2.dim_clientes
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON analytics_v2.dim_fornecedores
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON analytics_v2.dim_inventory
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON analytics_v2.fato_transacoes
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON analytics_v2.reg_jobs
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "read all" ON public.agent_catalog
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((is_active = true));

CREATE POLICY "own client" ON public.approval_requests
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.audit_log
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "bigquery_foreign_tables_access" ON public.bigquery_foreign_tables
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "bigquery_foreign_tables_update" ON public.bigquery_foreign_tables
  AS PERMISSIVE FOR UPDATE TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))))
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "bigquery_foreign_tables_write" ON public.bigquery_foreign_tables
  AS PERMISSIVE FOR INSERT TO public
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "bigquery_servers_access" ON public.bigquery_servers
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "bigquery_servers_update" ON public.bigquery_servers
  AS PERMISSIVE FOR UPDATE TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))))
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "bigquery_servers_write" ON public.bigquery_servers
  AS PERMISSIVE FOR INSERT TO public
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "own client" ON public.calendar_settings
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));

CREATE POLICY "client_data_sources_access" ON public.client_data_sources
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "client_data_sources_update" ON public.client_data_sources
  AS PERMISSIVE FOR UPDATE TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))))
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "client_data_sources_write" ON public.client_data_sources
  AS PERMISSIVE FOR INSERT TO public
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = (get_my_client_id())::text))));

CREATE POLICY "own client" ON public.client_dimension_kpis
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.client_enabled_agents
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.client_insights
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.client_routines
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "Authenticated users read own" ON public.clientes_blu
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))));

CREATE POLICY "Authenticated users update own" ON public.clientes_blu
  AS PERMISSIVE FOR UPDATE TO public
  USING ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))))
  WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))));

CREATE POLICY "Service role unrestricted" ON public.clientes_blu
  AS PERMISSIVE FOR ALL TO public
  USING (((auth.jwt() ->> 'role'::text) = 'service_role'::text))
  WITH CHECK (((auth.jwt() ->> 'role'::text) = 'service_role'::text));

CREATE POLICY "own client" ON public.conversa
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.frontend_events
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.integration_configs
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.integration_tokens
  AS PERMISSIVE FOR SELECT TO public
  USING ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));

CREATE POLICY "read all" ON public.kpi_catalog
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "own client" ON public.messages
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.nps_responses
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.report_runs
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.report_schedules
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.standalone_agent_sessions
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON public.uploaded_files_metadata
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "client file access" ON storage.objects
  AS PERMISSIVE FOR ALL TO authenticated
  USING (((bucket_id = 'file-uploads'::text) AND ((storage.foldername(name))[1] = (get_my_client_id())::text)))
  WITH CHECK (((bucket_id = 'file-uploads'::text) AND ((storage.foldername(name))[1] = (get_my_client_id())::text)));

CREATE POLICY "client kb access" ON storage.objects
  AS PERMISSIVE FOR ALL TO authenticated
  USING (((bucket_id = 'knowledge-base'::text) AND ((storage.foldername(name))[1] = (get_my_client_id())::text)))
  WITH CHECK (((bucket_id = 'knowledge-base'::text) AND ((storage.foldername(name))[1] = (get_my_client_id())::text)));

CREATE POLICY "own client" ON vector_db.document_chunks
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((client_id = get_my_client_id()));

CREATE POLICY "own client" ON vector_db.documents
  AS PERMISSIVE FOR ALL TO authenticated
  USING ((client_id = get_my_client_id()));


-- ────────────────────────────────────────────────────────────────────────────
-- FUNCTIONS
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(p_client_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET statement_timeout TO '0'
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_start timestamptz := clock_timestamp();
BEGIN
  RAISE NOTICE '[atualizar_agregados] client=%: updating dim aggregates', p_client_id;

  PERFORM analytics_v2.atualizar_dim_clientes(p_client_id);
  PERFORM analytics_v2.atualizar_dim_fornecedores(p_client_id);
  PERFORM analytics_v2.atualizar_dim_inventory(p_client_id);

  RAISE NOTICE '[atualizar_agregados] client=%: dims done in %.1fs, refreshing MVs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);

  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;

  RAISE NOTICE '[atualizar_agregados] client=%: all done in %.1fs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_clientes(p_client_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT
      ft.cliente_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS ticket_medio,
      COALESCE(SUM(ft.quantidade), 0)                                     AS quantidade_total,
      MIN(dd.data)                                                        AS data_primeira_compra,
      MAX(dd.data)                                                        AS data_ultima_compra,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.cliente_id IS NOT NULL
    GROUP BY ft.cliente_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia    DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal ASC  NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total     ASC  NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_clientes dc
  SET
    total_pedidos        = s.total_pedidos,
    receita_total        = s.receita_total,
    ticket_medio         = s.ticket_medio,
    quantidade_total     = s.quantidade_total,
    data_primeira_compra = s.data_primeira_compra,
    data_ultima_compra   = s.data_ultima_compra,
    dias_recencia        = s.dias_recencia,
    frequencia_mensal    = s.frequencia_mensal,
    pontuacao_cluster    = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster        = CASE
                             WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                             WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                             ELSE 'Baixo'
                           END,
    atualizado_em        = clock_timestamp()
  FROM scored s
  WHERE dc.client_id  = p_client_id
    AND dc.cliente_id = s.cliente_id;

  RAISE NOTICE '[atualizar_dim_clientes] client=%: done', p_client_id;
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_fornecedores(p_client_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT
      ft.fornecedor_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos_recebidos,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS ticket_medio,
      COUNT(DISTINCT ft.produto_id)                                       AS total_produtos_fornecidos,
      MIN(dd.data)                                                        AS data_primeira_transacao,
      MAX(dd.data)                                                        AS data_ultima_transacao,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id     = p_client_id
      AND ft.fornecedor_id IS NOT NULL
    GROUP BY ft.fornecedor_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_fornecedores df
  SET
    total_pedidos_recebidos   = s.total_pedidos_recebidos,
    receita_total             = s.receita_total,
    ticket_medio              = s.ticket_medio,
    total_produtos_fornecidos = s.total_produtos_fornecidos,
    data_primeira_transacao   = s.data_primeira_transacao,
    data_ultima_transacao     = s.data_ultima_transacao,
    dias_recencia             = s.dias_recencia,
    frequencia_mensal         = s.frequencia_mensal,
    pontuacao_cluster         = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster             = CASE
                                  WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                  WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                  ELSE 'Baixo'
                                END,
    atualizado_em             = clock_timestamp()
  FROM scored s
  WHERE df.client_id     = p_client_id
    AND df.fornecedor_id = s.fornecedor_id;

  RAISE NOTICE '[atualizar_dim_fornecedores] client=%: done', p_client_id;
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_inventory(p_client_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT
      ft.produto_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos,
      COALESCE(SUM(ft.quantidade), 0)                                     AS quantidade_total_vendida,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COALESCE(SUM(ft.quantidade), 0) > 0
           THEN COALESCE(SUM(ft.valor), 0) / SUM(ft.quantidade)
           ELSE 0 END                                                     AS preco_medio,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.quantidade), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS quantidade_media_por_pedido,
      MAX(dd.data)                                                        AS data_ultima_venda,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.produto_id IS NOT NULL
    GROUP BY ft.produto_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_inventory di
  SET
    quantidade_total_vendida    = s.quantidade_total_vendida,
    receita_total               = s.receita_total,
    preco_medio                 = s.preco_medio,
    total_pedidos               = s.total_pedidos,
    quantidade_media_por_pedido = s.quantidade_media_por_pedido,
    data_ultima_venda           = s.data_ultima_venda,
    dias_recencia               = s.dias_recencia,
    frequencia_mensal           = s.frequencia_mensal,
    pontuacao_cluster           = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster               = CASE
                                    WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                    WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                    ELSE 'Baixo'
                                  END,
    updated_at                  = clock_timestamp()
  FROM scored s
  WHERE di.client_id   = p_client_id
    AND di.inventory_id = s.produto_id;

  RAISE NOTICE '[atualizar_dim_inventory] client=%: done', p_client_id;
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.process_pending_etl_jobs()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET statement_timeout TO '0'
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_job_id uuid;
BEGIN
  -- Pick one job: pending jobs first, then failed jobs eligible for retry
  -- (failed < 3 times, last attempt > 5 minutes ago)
  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE job_type = 'bigquery_sync'
    AND (
      status = 'pending'
      OR (
        status = 'failed'
        AND retry_count < 3
        AND completed_at < now() - interval '5 minutes'
      )
    )
  ORDER BY
    CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
    created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_job_id IS NOT NULL THEN
    -- If this is a retry, reset back to pending and increment counter
    UPDATE analytics_v2.reg_jobs
    SET
      status        = 'pending',
      retry_count   = retry_count + 1,
      error_message = NULL,
      updated_at    = clock_timestamp()
    WHERE job_id = v_job_id AND status = 'failed';

    RAISE NOTICE '[process_pending_etl_jobs] dispatching job %', v_job_id;
    PERFORM analytics_v2.run_etl_job(v_job_id);
  END IF;
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.run_etl_job(p_job_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET statement_timeout TO '0'
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_client_id           uuid;
  v_cred_id             bigint;
  v_mapping             jsonb;
  v_server_name         text;
  v_bq_columns          jsonb;
  v_bare_table          text;
  v_ft_bare             text;
  v_col_defs            text;

  c_documento           text;
  c_data_competencia    text;
  c_quantidade          text;
  c_valor_unitario      text;
  c_valor               text;
  c_status              text;
  c_cliente_cpf_cnpj    text;
  c_cliente_nome        text;
  c_cliente_telefone    text;
  c_cliente_cidade      text;
  c_cliente_uf          text;
  c_fornecedor_cnpj     text;
  c_fornecedor_nome     text;
  c_fornecedor_telefone text;
  c_fornecedor_cidade   text;
  c_fornecedor_uf       text;
  c_produto_sku         text;
  c_produto_nome        text;

  v_select              text;
  v_start               timestamptz := clock_timestamp();
  v_rows                bigint  := 0;
  v_staged              bigint  := 0;
  v_duration            numeric;
BEGIN
  SET LOCAL statement_timeout = 0;

  -- ── Fetch job ────────────────────────────────────────────────────────────────
  SELECT client_id, (input_params->>'credential_id')::bigint
  INTO v_client_id, v_cred_id
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id AND status = 'pending';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job % not found or not in pending state', p_job_id;
  END IF;

  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = clock_timestamp(), progress_pct = 5, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Fetch column mapping ──────────────────────────────────────────────────────
  SELECT column_mapping INTO v_mapping
  FROM public.client_data_sources
  WHERE client_id = v_client_id::text AND credential_id = v_cred_id
  ORDER BY atualizado_em DESC NULLS LAST
  LIMIT 1;

  IF v_mapping IS NULL OR v_mapping = '{}'::jsonb THEN
    RAISE EXCEPTION 'No column mapping found for client_id=% credential_id=%', v_client_id, v_cred_id;
  END IF;

  -- ── Fetch FDW metadata from registry ─────────────────────────────────────────
  SELECT bft.server_name, bft.columns, bft.table_name
  INTO v_server_name, v_bq_columns, v_bare_table
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = v_client_id::text
  ORDER BY bft.created_at DESC LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery registry entry found for client_id=%', v_client_id;
  END IF;

  -- ── Create ephemeral foreign table in fdw schema ──────────────────────────────
  -- Deterministic name: one slot per client, no random suffix
  v_ft_bare  := 'bq_ft_' || SUBSTRING(REPLACE(v_client_id::text, '-', ''), 1, 12);
  v_col_defs := public._bq_col_defs_from_jsonb(v_bq_columns);

  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_ft_bare, v_col_defs, v_server_name, v_bare_table
  );

  -- ── Invert column mapping ─────────────────────────────────────────────────────
  SELECT key INTO c_documento           FROM jsonb_each_text(v_mapping) WHERE value = 'documento'           LIMIT 1;
  SELECT key INTO c_data_competencia    FROM jsonb_each_text(v_mapping) WHERE value = 'data_competencia_id' LIMIT 1;
  SELECT key INTO c_quantidade          FROM jsonb_each_text(v_mapping) WHERE value = 'quantidade'          LIMIT 1;
  SELECT key INTO c_valor_unitario      FROM jsonb_each_text(v_mapping) WHERE value = 'valor_unitario'      LIMIT 1;
  SELECT key INTO c_valor               FROM jsonb_each_text(v_mapping) WHERE value = 'valor'               LIMIT 1;
  SELECT key INTO c_status              FROM jsonb_each_text(v_mapping) WHERE value = 'status'              LIMIT 1;
  SELECT key INTO c_cliente_cpf_cnpj    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cpf_cnpj'   LIMIT 1;
  SELECT key INTO c_cliente_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_nome'        LIMIT 1;
  SELECT key INTO c_cliente_telefone    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_telefone'    LIMIT 1;
  SELECT key INTO c_cliente_cidade      FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cidade'      LIMIT 1;
  SELECT key INTO c_cliente_uf          FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_uf'          LIMIT 1;
  SELECT key INTO c_fornecedor_cnpj     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cnpj'     LIMIT 1;
  SELECT key INTO c_fornecedor_nome     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_nome'     LIMIT 1;
  SELECT key INTO c_fornecedor_telefone FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_telefone' LIMIT 1;
  SELECT key INTO c_fornecedor_cidade   FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cidade'   LIMIT 1;
  SELECT key INTO c_fornecedor_uf       FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_uf'       LIMIT 1;
  SELECT key INTO c_produto_sku         FROM jsonb_each_text(v_mapping) WHERE value = 'produto_sku'         LIMIT 1;
  SELECT key INTO c_produto_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'produto_nome'        LIMIT 1;

  IF c_documento IS NULL THEN
    RAISE EXCEPTION 'Column mapping missing required field "documento". Got mapping: %', v_mapping;
  END IF;

  RAISE NOTICE '[run_etl_job] job=%: mapping resolved — documento=%, valor=%, data=%',
    p_job_id, c_documento, c_valor, c_data_competencia;

  -- ── Build SELECT clause ───────────────────────────────────────────────────────
  v_select := format(
    $sel$
      %s::text AS documento,
      %s::text AS data_competencia_raw,
      %s::text AS quantidade_raw,
      %s::text AS valor_unitario_raw,
      %s::text AS valor_raw,
      %s::text AS status,
      %s::text AS cliente_cpf_cnpj,
      %s::text AS cliente_nome,
      %s::text AS cliente_telefone,
      %s::text AS cliente_cidade,
      %s::text AS cliente_uf,
      %s::text AS fornecedor_cnpj,
      %s::text AS fornecedor_nome,
      %s::text AS fornecedor_telefone,
      %s::text AS fornecedor_cidade,
      %s::text AS fornecedor_uf,
      %s::text AS produto_sku,
      %s::text AS produto_nome
    $sel$,
    CASE WHEN c_documento           IS NOT NULL THEN format('%I', c_documento)           ELSE 'NULL' END,
    CASE WHEN c_data_competencia    IS NOT NULL THEN format('%I', c_data_competencia)    ELSE 'NULL' END,
    CASE WHEN c_quantidade          IS NOT NULL THEN format('%I', c_quantidade)          ELSE 'NULL' END,
    CASE WHEN c_valor_unitario      IS NOT NULL THEN format('%I', c_valor_unitario)      ELSE 'NULL' END,
    CASE WHEN c_valor               IS NOT NULL THEN format('%I', c_valor)               ELSE 'NULL' END,
    CASE WHEN c_status              IS NOT NULL THEN format('%I', c_status)              ELSE 'NULL' END,
    CASE WHEN c_cliente_cpf_cnpj    IS NOT NULL THEN format('%I', c_cliente_cpf_cnpj)    ELSE 'NULL' END,
    CASE WHEN c_cliente_nome        IS NOT NULL THEN format('%I', c_cliente_nome)        ELSE 'NULL' END,
    CASE WHEN c_cliente_telefone    IS NOT NULL THEN format('%I', c_cliente_telefone)    ELSE 'NULL' END,
    CASE WHEN c_cliente_cidade      IS NOT NULL THEN format('%I', c_cliente_cidade)      ELSE 'NULL' END,
    CASE WHEN c_cliente_uf          IS NOT NULL THEN format('%I', c_cliente_uf)          ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cnpj     IS NOT NULL THEN format('%I', c_fornecedor_cnpj)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_nome     IS NOT NULL THEN format('%I', c_fornecedor_nome)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_telefone IS NOT NULL THEN format('%I', c_fornecedor_telefone) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cidade   IS NOT NULL THEN format('%I', c_fornecedor_cidade)   ELSE 'NULL' END,
    CASE WHEN c_fornecedor_uf       IS NOT NULL THEN format('%I', c_fornecedor_uf)       ELSE 'NULL' END,
    CASE WHEN c_produto_sku         IS NOT NULL THEN format('%I', c_produto_sku)         ELSE 'NULL' END,
    CASE WHEN c_produto_nome        IS NOT NULL THEN format('%I', c_produto_nome)        ELSE 'NULL' END
  );

  -- ── Clear leftover staging rows ────────────────────────────────────────────────
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 10, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Single FDW scan → staging ─────────────────────────────────────────────────
  EXECUTE format(
    'INSERT INTO analytics_v2.etl_staging
       (job_id, documento, data_competencia_raw, quantidade_raw, valor_unitario_raw, valor_raw,
        status, cliente_cpf_cnpj, cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
        fornecedor_cnpj, fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
        produto_sku, produto_nome)
     SELECT %L, %s FROM %I.%I',
    p_job_id, v_select, 'fdw', v_ft_bare
  );
  GET DIAGNOSTICS v_staged = ROW_COUNT;

  -- Drop ephemeral FT immediately after scan
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);

  RAISE NOTICE '[run_etl_job] job=%: staged % rows from fdw.%', p_job_id, v_staged, v_ft_bare;

  UPDATE analytics_v2.reg_jobs
  SET progress_pct = 55, rows_inserted = v_staged, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Upsert dim_clientes ───────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(cliente_cpf_cnpj, cliente_nome))
    v_client_id,
    COALESCE(cliente_cpf_cnpj, cliente_nome),
    cliente_nome,
    cliente_telefone,
    cliente_cidade,
    cliente_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(cliente_cpf_cnpj, cliente_nome) IS NOT NULL
  ORDER BY COALESCE(cliente_cpf_cnpj, cliente_nome)
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 65, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_fornecedores ───────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(fornecedor_cnpj, fornecedor_nome))
    v_client_id,
    COALESCE(fornecedor_cnpj, fornecedor_nome),
    fornecedor_nome,
    fornecedor_telefone,
    fornecedor_cidade,
    fornecedor_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(fornecedor_cnpj, fornecedor_nome) IS NOT NULL
  ORDER BY COALESCE(fornecedor_cnpj, fornecedor_nome)
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 75, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_inventory ──────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (COALESCE(produto_sku, produto_nome))
    v_client_id, COALESCE(produto_sku, produto_nome), produto_nome, clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(produto_sku, produto_nome) IS NOT NULL
  ORDER BY COALESCE(produto_sku, produto_nome)
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome = EXCLUDED.nome, updated_at = EXCLUDED.updated_at;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 82, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_datas ──────────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    d::date,
    EXTRACT(year FROM d)::int, EXTRACT(month FROM d)::int, EXTRACT(day FROM d)::int,
    CASE WHEN EXTRACT(dow FROM d) = 0 THEN 7 ELSE EXTRACT(dow FROM d)::int END,
    EXTRACT(week FROM d)::int,
    CASE WHEN EXTRACT(month FROM d) <= 6 THEN 1 ELSE 2 END,
    'Q' || EXTRACT(quarter FROM d)::text
  FROM (
    SELECT data_competencia_raw::timestamptz AS d
    FROM analytics_v2.etl_staging
    WHERE job_id = p_job_id
      AND data_competencia_raw IS NOT NULL
      AND data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
  ) t
  ON CONFLICT (data) DO NOTHING;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 88, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert fato_transacoes ────────────────────────────────────────────────────
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, cliente_id, fornecedor_id, produto_id,
     documento, quantidade, valor_unitario, valor, status)
  SELECT
    md5(v_client_id::text || ':' ||
        COALESCE(s.documento, '')            || ':' ||
        COALESCE(s.data_competencia_raw, '') || ':' ||
        COALESCE(s.produto_sku, ''))         AS transacao_id,
    v_client_id,
    dd.data_id,
    dc.cliente_id,
    df.fornecedor_id,
    di.inventory_id,
    s.documento,
    analytics_v2.safe_to_numeric(s.quantidade_raw),
    analytics_v2.safe_to_numeric(s.valor_unitario_raw),
    analytics_v2.safe_to_numeric(s.valor_raw),
    s.status
  FROM analytics_v2.etl_staging s
  LEFT JOIN analytics_v2.dim_datas dd
    ON dd.data = (
      CASE WHEN s.data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
           THEN (s.data_competencia_raw::timestamptz)::date ELSE NULL END
    )
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.client_id = v_client_id AND dc.cpf_cnpj = COALESCE(s.cliente_cpf_cnpj, s.cliente_nome)
  LEFT JOIN analytics_v2.dim_fornecedores df
    ON df.client_id = v_client_id AND df.cnpj = COALESCE(s.fornecedor_cnpj, s.fornecedor_nome)
  LEFT JOIN analytics_v2.dim_inventory di
    ON di.client_id = v_client_id AND di.sku = COALESCE(s.produto_sku, s.produto_nome)
  WHERE s.job_id = p_job_id
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    cliente_id          = EXCLUDED.cliente_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    documento           = EXCLUDED.documento,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status;

  GET DIAGNOSTICS v_rows = ROW_COUNT;

  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'completed',
    completed_at     = clock_timestamp(),
    rows_inserted    = v_rows,
    progress_pct     = 100,
    duration_seconds = v_duration,
    output           = jsonb_build_object(
                         'rows_inserted', v_rows,
                         'rows_staged',   v_staged,
                         'completed_at',  now()::text
                       ),
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;

  RAISE NOTICE '[run_etl_job] job=%: DONE — % fato rows from % staged rows in %.1fs',
    p_job_id, v_rows, v_staged, v_duration;

  -- ── Refresh aggregates (non-fatal if it fails) ────────────────────────────────
  BEGIN
    PERFORM analytics_v2.atualizar_agregados(v_client_id);
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[run_etl_job] job=%: aggregate refresh failed (non-fatal): %', p_job_id, SQLERRM;
  END;

EXCEPTION WHEN OTHERS THEN
  -- Clean up ephemeral FT if it was created before the error
  IF v_ft_bare IS NOT NULL THEN
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  END IF;
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;
  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET status = 'failed', completed_at = clock_timestamp(), progress_pct = 0,
      duration_seconds = v_duration, error_message = SQLERRM, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;
  RAISE;
END;
$function$

CREATE OR REPLACE FUNCTION analytics_v2.safe_to_numeric(p_text text)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
  v_text text;
BEGIN
  IF p_text IS NULL OR trim(p_text) = '' THEN
    RETURN NULL;
  END IF;
  v_text := trim(p_text);

  -- Direct cast: plain integers and standard decimals (1234, 1234.56, -1234.56)
  BEGIN
    RETURN v_text::numeric;
  EXCEPTION WHEN OTHERS THEN NULL;
  END;

  -- Brazilian format: period = thousands sep, comma = decimal ("1.234,56")
  IF v_text ~ '^-?[\d.]+,\d+$' THEN
    BEGIN
      RETURN replace(replace(v_text, '.', ''), ',', '.')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  -- US format: comma = thousands sep, period = decimal ("1,234.56")
  IF v_text ~ '^-?[\d,]+\.\d+$' THEN
    BEGIN
      RETURN replace(v_text, ',', '')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  RETURN NULL;
END;
$function$

CREATE OR REPLACE FUNCTION public._bq_canonical_ref(p_project_id text, p_dataset_id text, p_table_name text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
  SELECT p_project_id || '.' || p_dataset_id || '.' || p_table_name;
$function$

CREATE OR REPLACE FUNCTION public._bq_type_to_postgres_type(p_bq_type text)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
  v_bq_type_lower TEXT := LOWER(p_bq_type);
BEGIN
  CASE v_bq_type_lower
    -- Numeric types
    WHEN 'int64', 'integer' THEN RETURN 'bigint';
    WHEN 'int32' THEN RETURN 'integer';
    WHEN 'float64', 'float' THEN RETURN 'double precision';
    WHEN 'float32' THEN RETURN 'real';
    WHEN 'numeric', 'decimal' THEN RETURN 'numeric';

    -- String types
    WHEN 'string' THEN RETURN 'text';
    WHEN 'bytes' THEN RETURN 'bytea';

    -- Boolean
    WHEN 'bool', 'boolean' THEN RETURN 'boolean';

    -- Temporal types
    WHEN 'date' THEN RETURN 'date';
    WHEN 'time', 'time64' THEN RETURN 'time';
    WHEN 'datetime', 'timestamp' THEN RETURN 'timestamp with time zone';

    -- Complex types (stored as JSON)
    WHEN 'record', 'struct' THEN RETURN 'jsonb';
    WHEN 'array' THEN RETURN 'jsonb';
    WHEN 'geography', 'bignumeric' THEN RETURN 'jsonb';

    -- Default fallback
    ELSE RETURN 'text';
  END CASE;
END;
$function$

CREATE OR REPLACE FUNCTION public._bq_col_defs_from_jsonb(p_columns jsonb)
 RETURNS text
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  SELECT string_agg(
    format('%I %s', col->>'name', public._bq_type_to_postgres_type(col->>'type')),
    ', ' ORDER BY ordinality
  )
  FROM jsonb_array_elements(p_columns) WITH ORDINALITY AS t(col, ordinality);
$function$

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(p_client_id text, p_table_name text, p_bigquery_table text, p_location text DEFAULT 'US'::text, p_timeout_ms integer DEFAULT 300000, p_credential_id bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_my_client_id    UUID;
  v_data_source_id  UUID;
  v_error_msg       TEXT;
  v_server_name     TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    -- Verify server exists and fetch its name
    SELECT server_name INTO v_server_name
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    -- Drop any existing registry entry for this (client, table)
    DELETE FROM public.bigquery_foreign_tables
    WHERE client_id::text = v_my_client_id::text
      AND table_name = p_table_name;

    -- Register metadata; columns will be populated by the schema-discovery step
    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name,
      bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, NOW()
    )
    RETURNING id INTO v_data_source_id;

    -- Register data source (columns will be populated by discovery)
    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_credential_id,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', NOW(), NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      credential_id  = EXCLUDED.credential_id,
      updated_at     = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending',
      'message',        'Metadata registered. Calling discover-bigquery-columns to create FT with real schema.'
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table_from_schema(p_client_id text, p_columns jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_server_name    TEXT;
  v_project_id     TEXT;
  v_dataset_id     TEXT;
  v_bare_table     TEXT;
  v_col_defs       TEXT;
  v_error_msg      TEXT;
BEGIN
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  SELECT table_name INTO v_bare_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bare_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  -- Verify columns are mappable (also validates the array is non-empty)
  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);

  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty');
  END IF;

  BEGIN
    UPDATE public.bigquery_foreign_tables
    SET columns        = p_columns,
        server_name    = v_server_name,
        bigquery_table = public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
    WHERE client_id::text = p_client_id::text;

    RETURN jsonb_build_object(
      'success',       true,
      'bigquery_ref',  public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table),
      'columns_count', jsonb_array_length(p_columns)
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$

CREATE OR REPLACE FUNCTION public.create_bigquery_server(p_client_id text, p_service_account_key jsonb, p_project_id text, p_dataset_id text, p_location text DEFAULT 'US'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_vault_key_id UUID;
  v_secret_name TEXT;
  v_existing_server_name TEXT;
  v_error_msg TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  IF p_service_account_key IS NULL THEN
    RAISE EXCEPTION 'service_account_key cannot be null';
  END IF;

  IF (p_service_account_key->>'type')::text != 'service_account' THEN
    RAISE EXCEPTION 'Invalid service account key: missing or incorrect type field';
  END IF;

  IF (p_service_account_key->>'project_id')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing project_id field';
  END IF;

  IF (p_service_account_key->>'private_key')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing private_key field';
  END IF;

  BEGIN
    v_server_name := 'bq_server_' || (v_my_client_id::text) || '_' || EXTRACT(EPOCH FROM NOW())::bigint::text;

    SELECT server_name INTO v_existing_server_name
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      SELECT vault_key_id INTO v_vault_key_id
      FROM public.bigquery_servers
      WHERE client_id::text = v_my_client_id::text;

      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    v_vault_key_id := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;

    INSERT INTO vault.decrypted_secrets (name, decrypted_secret)
    VALUES (v_secret_name, p_service_account_key::text)
    ON CONFLICT (name) DO NOTHING;

    PERFORM 1 FROM vault.decrypted_secrets WHERE name = v_secret_name;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    EXECUTE format('CREATE SERVER IF NOT EXISTS %I FOREIGN DATA WRAPPER bigquery_fdw OPTIONS (project_id %L, dataset_id %L, location %L)',
                   v_server_name, p_project_id, p_dataset_id, p_location);

    EXECUTE format('CREATE USER MAPPING IF NOT EXISTS FOR current_user SERVER %I OPTIONS (service_account_json %L)',
                   v_server_name, p_service_account_key::text);

    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id::text, v_server_name, p_project_id, p_dataset_id,
      v_vault_key_id, p_location, NOW(), NOW()
    )
    ON CONFLICT (client_id) DO NOTHING;

    RETURN jsonb_build_object(
      'success', true,
      'server_name', v_server_name,
      'vault_key_id', v_vault_key_id
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN
        DELETE FROM vault.decrypted_secrets WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN
        NULL;
      END;
    END IF;

    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$

CREATE OR REPLACE FUNCTION public.decide_approval(p_request_id uuid, p_decision text, p_reason text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
BEGIN
  UPDATE public.approval_requests
  SET status     = p_decision,
      decided_by = auth.uid()::text,
      decided_at = now(),
      payload    = payload || jsonb_build_object('reason', p_reason)
  WHERE id = p_request_id
    AND client_id = public.get_my_client_id()
    AND status = 'pending';

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'Not found or already decided');
  END IF;
  RETURN jsonb_build_object('success', true, 'status', p_decision);
END;
$function$

CREATE OR REPLACE FUNCTION public.dismiss_insight(p_insight_id uuid)
 RETURNS void
 LANGUAGE sql
AS $function$
  UPDATE public.client_insights
  SET dismissed = true, dismissed_at = now()
  WHERE id = p_insight_id
    AND client_id = public.get_my_client_id();
$function$

CREATE OR REPLACE FUNCTION public.drop_bigquery_server(p_client_id text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_vault_key_id UUID;
  v_secret_name TEXT;
  v_error_msg TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name, vault_key_id
    INTO v_server_name, v_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object('success', true, 'message', 'No BigQuery server found for this tenant');
    END IF;

    -- Foreign tables are ephemeral (created/dropped inside run_etl_job), nothing to clean up here.

    BEGIN
      EXECUTE format('DROP USER MAPPING IF EXISTS FOR current_user SERVER %I', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;
      BEGIN
        DELETE FROM vault.decrypted_secrets WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN
        NULL;
      END;
    END IF;

    DELETE FROM public.client_data_sources
    WHERE client_id::text = v_my_client_id::text AND source_type = 'bigquery';

    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;

    DELETE FROM public.bigquery_servers WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and all related objects removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$

CREATE OR REPLACE FUNCTION public.ensure_tenant_row()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_user_id text := auth.uid()::text;
  v_email   text;
  v_client_id uuid;
  v_api_key text;
BEGIN
  SELECT client_id INTO v_client_id FROM public.clientes_blu
  WHERE external_user_id = v_user_id;
  
  IF v_client_id IS NULL THEN
    SELECT email INTO v_email FROM auth.users WHERE id = auth.uid();
    v_api_key := gen_random_uuid()::text;
    
    INSERT INTO public.clientes_blu (external_user_id, nome_empresa, api_key)
    VALUES (v_user_id, COALESCE(v_email, 'Empresa'), v_api_key)
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;
  END IF;
  
  -- Ensure api_key exists (fill in for existing rows without one)
  IF v_client_id IS NOT NULL THEN
    UPDATE public.clientes_blu
    SET api_key = COALESCE(api_key, gen_random_uuid()::text)
    WHERE client_id = v_client_id AND api_key IS NULL;
  END IF;
  
  RETURN jsonb_build_object('client_id', v_client_id);
END;
$function$

CREATE OR REPLACE FUNCTION public.exec_sql(p_query text)
 RETURNS TABLE(result jsonb)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
  -- session_user is the actual calling role, not the definer
  IF session_user NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION 'exec_sql: permission denied for role %', session_user;
  END IF;

  RETURN QUERY EXECUTE format(
    'SELECT to_jsonb(t) FROM (%s) t', p_query
  );
EXCEPTION WHEN OTHERS THEN
  RETURN QUERY SELECT jsonb_build_object('error', SQLERRM, 'detail', SQLSTATE)::JSONB;
END;
$function$

CREATE OR REPLACE FUNCTION public.expire_stale_insights(p_days_old integer DEFAULT 30)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_count INT;
BEGIN
  UPDATE public.client_insights
  SET dismissed_at = NOW()
  WHERE dismissed_at IS NULL
    AND created_at < NOW() - (p_days_old || ' days')::INTERVAL
    AND severity != 'critical';

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$function$

CREATE OR REPLACE FUNCTION public.get_agent_runs_today()
 RETURNS TABLE(total integer, by_agent jsonb)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2'
AS $function$
SELECT
  COUNT(*)::INT AS total,
  JSONB_OBJECT_AGG(
    COALESCE(resource_type, 'unknown'),
    run_count
  ) AS by_agent
FROM (
  SELECT
    resource_type,
    COUNT(*)::INT AS run_count
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
    AND job_type LIKE '%agent%'
    AND DATE(created_at) = CURRENT_DATE
  GROUP BY resource_type
) subquery;
$function$

CREATE OR REPLACE FUNCTION public.get_commercial_revenue_by_channel()
 RETURNS TABLE(channel text, total_revenue numeric, transaction_count integer, avg_transaction_value numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    f.channel::TEXT,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    COUNT(*)::INT as transaction_count,
    AVG(f.valor_total)::NUMERIC as avg_transaction_value
  FROM analytics_v2.fato_transacoes f
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY f.channel
  ORDER BY total_revenue DESC;
END;
$function$

CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
 RETURNS TABLE(cliente_id bigint, cliente_nome text, total_volume numeric, total_revenue numeric, last_purchase timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.nome::TEXT,
    COUNT(f.pedido_id)::NUMERIC as total_volume,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    MAX(f.data_transacao) as last_purchase
  FROM analytics_v2.fato_transacoes f
  LEFT JOIN analytics_v2.dim_clientes d ON f.cliente_id = d.id
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY d.id, d.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$function$

CREATE OR REPLACE FUNCTION public.get_my_client_id()
 RETURNS uuid
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  SELECT COALESCE(
    -- 1. app_metadata (backend-authoritative)
    (auth.jwt() -> 'app_metadata' ->> 'client_id')::uuid,
    -- 2. user_metadata (social/onboarding path)
    (auth.jwt() -> 'user_metadata' ->> 'client_id')::uuid,
    -- 3. DB lookup (legacy accounts without JWT claim)
    (SELECT client_id
     FROM public.clientes_blu
     WHERE external_user_id = (auth.jwt() ->> 'sub')
     LIMIT 1)
  );
$function$

CREATE OR REPLACE FUNCTION public.get_my_dashboard_kpis()
 RETURNS TABLE(dimension text, slot_index integer, slug text, label text, unit text, formula text, data_status text, tier_required text, is_enabled boolean)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
SELECT
  kc.dimension,
  ROW_NUMBER() OVER (PARTITION BY kc.dimension ORDER BY COALESCE(kc.sort_order, 999)) AS slot_index,
  kc.slug,
  kc.label,
  kc.unit,
  kc.formula,
  kc.data_status,
  kc.tier_required,
  COALESCE(ck.slug IS NOT NULL, FALSE) AS is_enabled
FROM public.kpi_catalog kc
LEFT JOIN public.client_dimension_kpis ck
  ON ck.slug = kc.slug
  AND ck.client_id = public.get_my_client_id()
  AND ck.dimension = kc.dimension
ORDER BY kc.dimension, COALESCE(kc.sort_order, 999);
$function$

CREATE OR REPLACE FUNCTION public.get_my_insights(p_limit integer DEFAULT 5, p_status text DEFAULT 'active'::text)
 RETURNS TABLE(id uuid, run_date timestamp with time zone, dimension text, kpi text, severity text, title text, observation text, recommendation text, metric_value numeric, baseline_value numeric, variance_pct numeric, status text, created_at timestamp with time zone)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
SELECT
  ci.id,
  ci.generated_at::TIMESTAMPTZ AS run_date,
  ci.dimension,
  ''::TEXT AS kpi,
  ci.severity,
  ci.title,
  ci.body::TEXT AS observation,
  ''::TEXT AS recommendation,
  NULL::NUMERIC AS metric_value,
  NULL::NUMERIC AS baseline_value,
  NULL::NUMERIC AS variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at::TIMESTAMPTZ AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
    p_status = 'active'    AND NOT ci.dismissed
    OR p_status = 'dismissed' AND ci.dismissed
    OR p_status NOT IN ('active', 'dismissed')
  )
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$function$

CREATE OR REPLACE FUNCTION public.get_nps_score(p_window_days integer DEFAULT 90)
 RETURNS TABLE(score numeric, total_responses bigint, promoters bigint, passives bigint, detractors bigint)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
SELECT
  CASE
    WHEN COUNT(*) > 0
    THEN ROUND(
      ((COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::NUMERIC -
        COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::NUMERIC) /
       COUNT(*)::NUMERIC * 100), 1)
    ELSE NULL::NUMERIC
  END AS score,
  COUNT(*)::BIGINT AS total_responses,
  COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::BIGINT AS promoters,
  COALESCE(SUM(CASE WHEN score >= 7 AND score <= 8 THEN 1 ELSE 0 END), 0)::BIGINT AS passives,
  COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::BIGINT AS detractors
FROM public.nps_responses
WHERE client_id = public.get_my_client_id()
  AND created_at >= CURRENT_TIMESTAMP - (p_window_days || ' days')::INTERVAL;
$function$

CREATE OR REPLACE FUNCTION public.get_pendencias()
 RETURNS TABLE(kind text, title text, severity text, occurred_at timestamp with time zone, target_route text)
 LANGUAGE sql
 STABLE
 SET search_path TO 'analytics_v2', 'public'
AS $function$
SELECT
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync'  THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl'  THEN 'rfq_pending'
    ELSE 'rfq_pending'
  END AS kind,
  'Job: ' || rj.job_type || ' - ' || COALESCE(rj.resource_type, 'Unknown') AS title,
  CASE
    WHEN rj.status = 'failed'  THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,
  rj.created_at AS occurred_at,
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type = 'bigquery_sync'  THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route
FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;
$function$

CREATE OR REPLACE FUNCTION public.get_platform_google_oauth_config()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $function$
  SELECT decrypted_secret::jsonb FROM vault.decrypted_secrets
  WHERE name = 'google_oauth_config' LIMIT 1;
$function$

CREATE OR REPLACE FUNCTION public.get_recent_activity(p_limit integer DEFAULT 10)
 RETURNS TABLE(kind text, title text, subtitle text, occurred_at timestamp with time zone, severity text)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
SELECT
  CASE
    WHEN action = 'CREATE' THEN 'ingestion'
    WHEN action = 'UPDATE' THEN 'agent_session'
    WHEN action = 'DELETE' THEN 'error'
    ELSE 'info'
  END AS kind,
  UPPER(entity_type) || ' ' || action AS title,
  (payload->>'description')::TEXT AS subtitle,
  created_at AS occurred_at,
  CASE
    WHEN action = 'DELETE' THEN 'error'
    WHEN action = 'UPDATE' THEN 'warning'
    ELSE 'info'
  END AS severity
FROM public.audit_log
WHERE client_id = public.get_my_client_id()
ORDER BY created_at DESC
LIMIT p_limit;
$function$

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_client_id uuid;
  v_api_key text;
BEGIN
  -- Generate a fresh API key
  v_api_key := gen_random_uuid()::text;
  
  -- Insert or update: if row exists (via external_user_id), keep existing api_key
  -- Otherwise create with new api_key
  INSERT INTO public.clientes_blu (
    external_user_id,
    api_key,
    nome_empresa,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id::text,
    v_api_key,
    COALESCE(NEW.email, 'Empresa'),
    now(),
    now()
  )
  ON CONFLICT (external_user_id) DO NOTHING
  RETURNING client_id INTO v_client_id;

  -- If row already existed (conflict), get its client_id
  IF v_client_id IS NULL THEN
    SELECT client_id INTO v_client_id FROM public.clientes_blu
    WHERE external_user_id = NEW.id::text;
  END IF;

  -- Log the creation
  IF v_client_id IS NOT NULL THEN
    INSERT INTO public.audit_log (
      client_id,
      actor_id,
      action,
      entity_type,
      payload
    ) VALUES (
      v_client_id,
      NEW.id::text,
      'tenant_auto_created',
      'clientes_blu',
      jsonb_build_object('email', NEW.email, 'api_key_generated', true)
    );
  END IF;

  RETURN NEW;
END;
$function$

CREATE OR REPLACE FUNCTION public.list_due_report_schedules()
 RETURNS TABLE(schedule_id uuid, client_id uuid, name text, report_type text, cron_expr text)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.client_id,
    s.name,
    s.report_type,
    s.cron_expr
  FROM public.report_schedules s
  WHERE s.active = TRUE
    AND s.next_run_at <= NOW()
  ORDER BY s.next_run_at ASC;
END;
$function$

CREATE OR REPLACE FUNCTION public.list_inbox_threads(p_limit integer DEFAULT 50)
 RETURNS TABLE(id uuid, client_id uuid, created_at timestamp with time zone, updated_at timestamp with time zone, message_count integer, last_message_at timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.client_id,
    c.created_at,
    c.updated_at,
    (SELECT COUNT(*)::INT FROM public.messages m WHERE m.session_id = c.id) as message_count,
    (SELECT MAX(m.created_at) FROM public.messages m WHERE m.session_id = c.id) as last_message_at
  FROM public.conversa c
  WHERE c.client_id = public.get_my_client_id()
  ORDER BY c.updated_at DESC
  LIMIT p_limit;
END;
$function$

CREATE OR REPLACE FUNCTION public.list_kpi_catalog(p_dimension text DEFAULT NULL::text, p_only_enabled boolean DEFAULT false)
 RETURNS TABLE(slug text, dimension text, label text, unit text, data_status text, sort_order integer, is_default boolean, default_dimension_rank integer, is_enabled boolean)
 LANGUAGE sql
 STABLE
AS $function$
  SELECT
    k.slug, k.dimension, k.label, k.unit, k.data_status, k.sort_order,
    false AS is_default,
    NULL::int AS default_dimension_rank,
    (EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id()
        AND ck.slug = k.slug
    )) AS is_enabled
  FROM public.kpi_catalog k
  WHERE (p_dimension IS NULL OR k.dimension = p_dimension)
    AND (NOT p_only_enabled OR EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id() AND ck.slug = k.slug
    ))
  ORDER BY k.sort_order, k.slug;
$function$

CREATE OR REPLACE FUNCTION public.list_pending_approvals()
 RETURNS SETOF approval_requests
 LANGUAGE sql
 STABLE
AS $function$
  SELECT * FROM public.approval_requests
  WHERE client_id = public.get_my_client_id()
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
  ORDER BY created_at DESC;
$function$

CREATE OR REPLACE FUNCTION public.list_report_runs(p_limit integer DEFAULT 50)
 RETURNS TABLE(id uuid, schedule_id uuid, status text, output_url text, error text, started_at timestamp with time zone, completed_at timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.schedule_id,
    r.status,
    r.output_url,
    r.error,
    r.started_at,
    r.completed_at
  FROM public.report_runs r
  WHERE r.client_id = public.get_my_client_id()
  ORDER BY COALESCE(r.started_at, r.completed_at) DESC
  LIMIT p_limit;
END;
$function$

CREATE OR REPLACE FUNCTION public.list_report_schedules()
 RETURNS TABLE(id uuid, name text, report_type text, cron_expr text, active boolean, next_run_at timestamp with time zone, created_at timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.name,
    s.report_type,
    s.cron_expr,
    s.active,
    s.next_run_at,
    s.created_at
  FROM public.report_schedules s
  WHERE s.client_id = public.get_my_client_id()
  ORDER BY s.next_run_at ASC;
END;
$function$

CREATE OR REPLACE FUNCTION public.merge_onboarding_state(p_patch jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_result    jsonb;
BEGIN
  UPDATE public.clientes_blu
  SET onboarding_state = onboarding_state || p_patch,
      updated_at       = now()
  WHERE client_id = v_client_id
  RETURNING onboarding_state INTO v_result;
  RETURN v_result;
END;
$function$

CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
BEGIN
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant row found for current user';
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(p_payload->>'nome_empresa', nome_empresa),
    company_profile         = COALESCE(p_payload->'company_profile', company_profile),
    team_structure          = COALESCE(p_payload->'team_structure', team_structure),
    policies                = COALESCE(p_payload->'policies', policies),
    onboarding_completed_at = COALESCE(onboarding_completed_at, now()),
    updated_at              = now()
  WHERE client_id = v_client_id;

  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    INSERT INTO public.client_routines (client_id, routine_id, notify_channel)
    VALUES (v_client_id, v_routine_id, v_notify)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET notify_channel = EXCLUDED.notify_channel;
    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$function$

CREATE OR REPLACE FUNCTION public.record_audit(p_action text, p_entity_type text DEFAULT NULL::text, p_entity_id text DEFAULT NULL::text, p_payload jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  INSERT INTO public.audit_log (client_id, actor_id, action, entity_type, entity_id, payload)
  VALUES (public.get_my_client_id(), auth.uid()::text, p_action, p_entity_type, p_entity_id, p_payload);
END;
$function$

CREATE OR REPLACE FUNCTION public.record_frontend_event(p_event_name text, p_properties jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (public.get_my_client_id(), p_event_name, p_properties);
END;
$function$

CREATE OR REPLACE FUNCTION public.record_insight(p_title text, p_content text, p_severity text DEFAULT 'info'::text, p_data jsonb DEFAULT NULL::jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_insight_id UUID;
BEGIN
  INSERT INTO public.client_insights (
    id,
    client_id,
    title,
    content,
    severity,
    metadata,
    created_at,
    dismissed_at
  )
  VALUES (
    gen_random_uuid(),
    public.get_my_client_id(),
    p_title,
    p_content,
    p_severity,
    p_data,
    NOW(),
    NULL
  )
  RETURNING id INTO v_insight_id;

  RETURN v_insight_id;
END;
$function$

CREATE OR REPLACE FUNCTION public.request_approval(p_action_type text, p_payload jsonb DEFAULT '{}'::jsonb, p_expires_at timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE v_id uuid;
BEGIN
  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, payload, expires_at)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, p_action_type, p_payload, p_expires_at)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$function$

CREATE OR REPLACE FUNCTION public.set_client_dimension_kpis(p_dimension text, p_slugs text[])
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
BEGIN
  DELETE FROM public.client_dimension_kpis
  WHERE client_id = v_client_id AND dimension = p_dimension;

  INSERT INTO public.client_dimension_kpis (client_id, dimension, slug)
  SELECT v_client_id, p_dimension, s
  FROM unnest(p_slugs) s
  WHERE EXISTS (SELECT 1 FROM public.kpi_catalog WHERE slug = s)
  ON CONFLICT DO NOTHING;

  RETURN jsonb_build_object('dimension', p_dimension, 'count', array_length(p_slugs, 1));
END;
$function$

CREATE OR REPLACE FUNCTION public.set_current_cliente_id(p_client_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;
$function$

CREATE OR REPLACE FUNCTION public.trigger_column_discovery(p_credential_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_client_id UUID;
BEGIN
  SELECT client_id INTO v_client_id
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found';
  END IF;

  IF v_client_id != public.get_my_client_id() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  UPDATE public.client_data_sources
  SET sync_status = 'discovery_pending'
  WHERE credential_id = p_credential_id;

  RETURN jsonb_build_object(
    'status', 'discovery_queued',
    'credential_id', p_credential_id,
    'queued_at', to_jsonb(NOW())
  );
END;
$function$

CREATE OR REPLACE FUNCTION public.update_bigquery_foreign_table_columns(p_client_id text, p_columns jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_col_defs  TEXT;
  v_error_msg TEXT;
BEGIN
  IF p_columns IS NULL OR jsonb_array_length(p_columns) = 0 THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty');
  END IF;

  -- Verify columns are mappable before persisting
  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);

  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty');
  END IF;

  BEGIN
    UPDATE public.bigquery_foreign_tables
    SET columns = p_columns
    WHERE client_id::text = p_client_id::text;

    RETURN jsonb_build_object('success', true, 'columns_count', jsonb_array_length(p_columns));

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$

CREATE OR REPLACE FUNCTION public.update_data_source_mappings_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$

CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(p_client_id uuid, p_query_embed halfvec, p_query_text text, p_match_count integer DEFAULT 10, p_theme_filter text DEFAULT NULL::text)
 RETURNS TABLE(id integer, document_id uuid, content text, metadata jsonb, similarity double precision)
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $function$
  WITH semantic AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      1 - (c.embedding <#> p_query_embed) AS sim
    FROM vector_db.document_chunks c
    WHERE c.client_id = p_client_id
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    ORDER BY c.embedding <#> p_query_embed
    LIMIT p_match_count * 3
  ),
  fts AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      ts_rank(c.fts, plainto_tsquery('portuguese', p_query_text)) AS rank
    FROM vector_db.document_chunks c
    WHERE c.client_id = p_client_id
      AND c.fts @@ plainto_tsquery('portuguese', p_query_text)
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    LIMIT p_match_count * 3
  )
  SELECT DISTINCT ON (COALESCE(s.id, f.id))
    COALESCE(s.id, f.id),
    COALESCE(s.document_id, f.document_id),
    COALESCE(s.content, f.content),
    COALESCE(s.metadata, f.metadata),
    COALESCE(s.sim, 0) * 0.7 + COALESCE(f.rank, 0) * 0.3 AS similarity
  FROM semantic s
  FULL OUTER JOIN fts f USING (id)
  ORDER BY COALESCE(s.id, f.id), similarity DESC
  LIMIT p_match_count;
$function$


-- ────────────────────────────────────────────────────────────────────────────
-- TRIGGERS
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE TRIGGER trigger_update_data_source_mappings_updated_at
  BEFORE UPDATE ON public.data_source_mappings
  FOR EACH ROW EXECUTE FUNCTION update_data_source_mappings_updated_at();


-- ────────────────────────────────────────────────────────────────────────────
-- MATERIALIZED VIEWS
-- ────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_distribuicao_regional AS SELECT dc.client_id,
    dc.endereco_uf,
    dc.endereco_cidade,
    COALESCE(sum(ft.valor), 0::numeric) AS receita_total,
    count(DISTINCT dc.cliente_id)::integer AS total_clientes,
    count(DISTINCT ft.transacao_id)::integer AS total_pedidos
   FROM analytics_v2.dim_clientes dc
     LEFT JOIN analytics_v2.fato_transacoes ft ON dc.cliente_id = ft.cliente_id AND dc.client_id = ft.client_id
  GROUP BY dc.client_id, dc.endereco_uf, dc.endereco_cidade;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_resumo_dashboard AS WITH base AS (
         SELECT ft.client_id,
            count(DISTINCT dc.cliente_id)::integer AS total_clientes,
            count(DISTINCT df.fornecedor_id)::integer AS total_fornecedores,
            count(DISTINCT di.inventory_id)::integer AS total_produtos,
            count(DISTINCT ft.transacao_id)::integer AS total_pedidos,
            COALESCE(sum(ft.valor), 0::numeric) AS receita_total,
            COALESCE(sum(ft.quantidade), 0::numeric) AS quantidade_total_vendida,
                CASE
                    WHEN count(DISTINCT ft.transacao_id) > 0 THEN COALESCE(sum(ft.valor), 0::numeric) / count(DISTINCT ft.transacao_id)::numeric
                    ELSE 0::numeric
                END AS ticket_medio,
            count(DISTINCT dc.endereco_uf)::integer AS total_regioes,
                CASE
                    WHEN count(DISTINCT df.fornecedor_id) > 0 THEN count(DISTINCT ft.transacao_id)::numeric / count(DISTINCT df.fornecedor_id)::numeric
                    ELSE 0::numeric
                END AS frequencia_media_fornecedores,
            count(DISTINCT dc.cliente_id) FILTER (WHERE dd.data >= (CURRENT_DATE - 30))::integer AS clientes_ativos,
            COALESCE(sum(ft.valor) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date), 0::numeric) AS receita_mes_atual,
            COALESCE(sum(ft.quantidade) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date), 0::numeric) AS quantidade_mes_atual,
            count(DISTINCT dc.cliente_id) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date)::integer AS clientes_mes_atual,
            count(DISTINCT di.inventory_id) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date)::integer AS produtos_mes_atual,
            count(DISTINCT df.fornecedor_id) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date)::integer AS fornecedores_mes_atual,
            COALESCE(sum(ft.valor) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '1 mon'::interval)::date), 0::numeric) AS receita_mes_anterior,
            COALESCE(sum(ft.quantidade) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '1 mon'::interval)::date), 0::numeric) AS quantidade_mes_anterior,
            count(DISTINCT dc.cliente_id) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '1 mon'::interval)::date)::integer AS clientes_mes_anterior,
            count(DISTINCT di.inventory_id) FILTER (WHERE date_trunc('month'::text, dd.data::timestamp with time zone)::date = (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '1 mon'::interval)::date)::integer AS produtos_mes_anterior
           FROM analytics_v2.fato_transacoes ft
             LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
             LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id AND dc.client_id = ft.client_id
             LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id
             LEFT JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id AND di.client_id = ft.client_id
          GROUP BY ft.client_id
        ), novos_agg AS (
         SELECT sub.client_id,
            count(*)::integer AS clientes_novos
           FROM ( SELECT ft.client_id,
                    ft.cliente_id
                   FROM analytics_v2.fato_transacoes ft
                     JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
                  WHERE ft.cliente_id IS NOT NULL AND dd.data IS NOT NULL
                  GROUP BY ft.client_id, ft.cliente_id
                 HAVING min(dd.data) >= date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date) sub
          GROUP BY sub.client_id
        )
 SELECT b.client_id, b.total_clientes, b.total_fornecedores, b.total_produtos,
    b.total_pedidos, b.receita_total, b.quantidade_total_vendida, b.ticket_medio,
    b.receita_mes_atual, b.quantidade_mes_atual, b.clientes_mes_atual, b.produtos_mes_atual,
    b.fornecedores_mes_atual,
    CASE WHEN b.receita_mes_anterior > 0::numeric THEN (b.receita_mes_atual - b.receita_mes_anterior) / b.receita_mes_anterior ELSE 0::numeric END AS crescimento_receita,
    CASE WHEN b.clientes_mes_anterior > 0 THEN (b.clientes_mes_atual - b.clientes_mes_anterior)::numeric / b.clientes_mes_anterior::numeric ELSE 0::numeric END AS crescimento_clientes,
    CASE WHEN b.produtos_mes_anterior > 0 THEN (b.produtos_mes_atual - b.produtos_mes_anterior)::numeric / b.produtos_mes_anterior::numeric ELSE 0::numeric END AS crescimento_produtos,
    CASE WHEN b.quantidade_mes_anterior > 0::numeric THEN (b.quantidade_mes_atual - b.quantidade_mes_anterior) / b.quantidade_mes_anterior ELSE 0::numeric END AS crescimento_quantidade,
    b.frequencia_media_fornecedores, b.total_regioes,
    to_char(CURRENT_DATE - '1 mon'::interval, 'Mon/YYYY'::text) AS ultimo_mes,
    b.clientes_ativos, COALESCE(na.clientes_novos, 0) AS clientes_novos,
    CURRENT_TIMESTAMP AS gerado_em
   FROM base b LEFT JOIN novos_agg na ON b.client_id = na.client_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_series_temporal AS WITH base AS (
         SELECT ft.client_id, to_char(dd.data::timestamp with time zone, 'YYYY-MM'::text) AS periodo, dd.data AS data_periodo, 'receita'::text AS tipo_grafico, 'total'::text AS dimensao, COALESCE(sum(ft.valor), 0::numeric) AS total
           FROM analytics_v2.fato_transacoes ft LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id WHERE dd.data IS NOT NULL GROUP BY ft.client_id, dd.data
        UNION ALL
         SELECT ft.client_id, to_char(dd.data::timestamp with time zone, 'YYYY-MM'::text), dd.data, 'clientes'::text, 'total'::text, count(DISTINCT dc.cliente_id)::numeric
           FROM analytics_v2.fato_transacoes ft LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id AND dc.client_id = ft.client_id WHERE dd.data IS NOT NULL GROUP BY ft.client_id, dd.data
        UNION ALL
         SELECT ft.client_id, to_char(dd.data::timestamp with time zone, 'YYYY-MM'::text), dd.data, 'fornecedores'::text, 'total'::text, count(DISTINCT df.fornecedor_id)::numeric
           FROM analytics_v2.fato_transacoes ft LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id WHERE dd.data IS NOT NULL GROUP BY ft.client_id, dd.data
        UNION ALL
         SELECT ft.client_id, to_char(dd.data::timestamp with time zone, 'YYYY-MM'::text), dd.data, 'produtos'::text, 'total'::text, count(DISTINCT di.inventory_id)::numeric
           FROM analytics_v2.fato_transacoes ft LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id LEFT JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id AND di.client_id = ft.client_id WHERE dd.data IS NOT NULL GROUP BY ft.client_id, dd.data
        UNION ALL
         SELECT ft.client_id, to_char(dd.data::timestamp with time zone, 'YYYY-MM'::text), dd.data, 'pedidos'::text, 'total'::text, count(DISTINCT ft.transacao_id)::numeric
           FROM analytics_v2.fato_transacoes ft LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id WHERE dd.data IS NOT NULL GROUP BY ft.client_id, dd.data
        )
 SELECT client_id, periodo, data_periodo, tipo_grafico, dimensao, total,
    sum(total) OVER (PARTITION BY client_id, tipo_grafico, dimensao ORDER BY data_periodo ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS total_cumulativo
   FROM base;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_ultimos_pedidos AS SELECT ft.client_id, ft.transacao_id AS pedido_id, dc.cpf_cnpj AS cliente_cpf_cnpj,
    ft.valor AS valor_pedido, ft.quantidade AS qtd_produtos,
    row_number() OVER (PARTITION BY ft.client_id ORDER BY ft.created_at DESC) AS ordem
   FROM analytics_v2.fato_transacoes ft
     LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id AND dc.client_id = ft.client_id
  WHERE ft.created_at IS NOT NULL;


-- ────────────────────────────────────────────────────────────────────────────
-- MATERIALIZED VIEW INDEXES
-- ────────────────────────────────────────────────────────────────────────────

CREATE INDEX idx_mv_distribuicao_regional_client_id ON analytics_v2.mv_distribuicao_regional USING btree (client_id);
CREATE INDEX idx_mv_distribuicao_regional_uf ON analytics_v2.mv_distribuicao_regional USING btree (endereco_uf);
CREATE UNIQUE INDEX mv_distribuicao_regional_unique_idx ON analytics_v2.mv_distribuicao_regional USING btree (client_id, endereco_uf, endereco_cidade);
CREATE UNIQUE INDEX mv_resumo_dashboard_client_id_idx ON analytics_v2.mv_resumo_dashboard USING btree (client_id);
CREATE UNIQUE INDEX mv_series_temporal_unique_idx ON analytics_v2.mv_series_temporal USING btree (client_id, data_periodo, tipo_grafico, dimensao);
CREATE INDEX idx_mv_ultimos_pedidos_client_id ON analytics_v2.mv_ultimos_pedidos USING btree (client_id);
CREATE UNIQUE INDEX mv_ultimos_pedidos_unique_idx ON analytics_v2.mv_ultimos_pedidos USING btree (client_id, pedido_id);


-- ────────────────────────────────────────────────────────────────────────────
-- VIEWS
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW analytics_v2.v_distribuicao_regional AS
SELECT client_id, endereco_uf, endereco_cidade, receita_total, total_clientes, total_pedidos
   FROM analytics_v2.mv_distribuicao_regional
  WHERE (client_id = get_my_client_id());

CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard AS
SELECT client_id, total_clientes, total_fornecedores, total_produtos, total_pedidos, receita_total, quantidade_total_vendida, ticket_medio, receita_mes_atual, quantidade_mes_atual, clientes_mes_atual, produtos_mes_atual, fornecedores_mes_atual, crescimento_receita, crescimento_clientes, crescimento_produtos, crescimento_quantidade, frequencia_media_fornecedores, total_regioes, ultimo_mes, clientes_ativos, clientes_novos, gerado_em
   FROM analytics_v2.mv_resumo_dashboard
  WHERE (client_id = get_my_client_id());

CREATE OR REPLACE VIEW analytics_v2.v_series_temporal AS
SELECT client_id, periodo, data_periodo, tipo_grafico, dimensao, total, total_cumulativo
   FROM analytics_v2.mv_series_temporal
  WHERE (client_id = get_my_client_id());

CREATE OR REPLACE VIEW analytics_v2.v_ultimos_pedidos AS
SELECT client_id, pedido_id, cliente_cpf_cnpj, valor_pedido, qtd_produtos, ordem
   FROM analytics_v2.mv_ultimos_pedidos
  WHERE (client_id = get_my_client_id());


-- ────────────────────────────────────────────────────────────────────────────
-- STORAGE BUCKETS
-- ────────────────────────────────────────────────────────────────────────────

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  ('file-uploads', 'file-uploads', false, 104857600, ARRAY['application/pdf','text/plain','text/csv','application/json','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/vnd.ms-excel','image/png','image/jpeg','image/gif']),
  ('knowledge-base', 'knowledge-base', false, null, null),
  ('Vizu-dev', 'Vizu-dev', false, 5242880, null),
  ('vizu-uploads', 'vizu-uploads', false, null, null)
ON CONFLICT (id) DO NOTHING;


-- ────────────────────────────────────────────────────────────────────────────
-- GRANTS
-- ────────────────────────────────────────────────────────────────────────────

GRANT USAGE ON SCHEMA analytics_v2 TO authenticated;
GRANT USAGE ON SCHEMA analytics_v2 TO service_role;
GRANT USAGE ON SCHEMA vector_db TO authenticated;
GRANT USAGE ON SCHEMA vector_db TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics_v2 TO authenticated;
GRANT SELECT ON analytics_v2.mv_resumo_dashboard TO authenticated;
GRANT SELECT ON analytics_v2.mv_series_temporal TO authenticated;
GRANT SELECT ON analytics_v2.mv_distribuicao_regional TO authenticated;
GRANT SELECT ON analytics_v2.mv_ultimos_pedidos TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA analytics_v2 TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA analytics_v2 TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA vector_db TO service_role;


-- ────────────────────────────────────────────────────────────────────────────
-- CRON JOBS
-- ────────────────────────────────────────────────────────────────────────────

SELECT cron.schedule(
  'process_pending_etl_jobs',
  '* * * * *',
  $$SELECT analytics_v2.process_pending_etl_jobs()$$
);
