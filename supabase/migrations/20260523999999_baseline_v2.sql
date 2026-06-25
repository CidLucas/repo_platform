-- ============================================================
-- BASELINE MIGRATION v2 — 2026-05-23
-- Generated from live remote schema (non-prod).
-- Supersedes all prior migrations as the new schema baseline.
-- DO NOT apply to an existing database that already has data.
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS wrappers WITH SCHEMA extensions;

-- Sequences
CREATE SEQUENCE IF NOT EXISTS public.audit_log_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.canonical_columns_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.credencial_servico_externo_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 NO CYCLE;
CREATE SEQUENCE IF NOT EXISTS public.frontend_events_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 NO CYCLE;

-- Tables
CREATE TABLE public.agent_catalog (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  category text,
  icon text,
  agent_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  prompt_name text NOT NULL,
  required_context jsonb DEFAULT '[]'::jsonb,
  required_files jsonb DEFAULT '{}'::jsonb,
  requires_google bool DEFAULT false,
  tier_required text DEFAULT 'BASIC'::text,
  landing_slug text,
  workflow_graph jsonb,
  is_active bool DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.app_config (
  key text NOT NULL,
  value text NOT NULL
);
CREATE TABLE public.approval_requests (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  requested_by text,
  action_type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending'::text,
  decided_by text,
  decided_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  agent_slug text,
  priority text DEFAULT 'normal'::text,
  title text,
  insight_text text,
  snooze_until timestamptz,
  snooze_count int4 DEFAULT 0,
  scheduled_for timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  session_id text,
  tool_call_id text,
  body text,
  assigned_role text DEFAULT 'owner'::text,
  metadata jsonb
);
CREATE TABLE public.audit_log (
  id int8 NOT NULL DEFAULT nextval('audit_log_id_seq'::regclass),
  client_id uuid,
  actor_id text,
  action text NOT NULL,
  entity_type text,
  entity_id text,
  payload jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.bigquery_foreign_tables (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  table_name text NOT NULL,
  bigquery_table text NOT NULL,
  server_name text NOT NULL,
  columns jsonb NOT NULL,
  location text DEFAULT 'US'::text,
  created_at timestamptz DEFAULT now(),
  credential_id int8
);
CREATE TABLE public.bigquery_servers (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  server_name text NOT NULL,
  project_id text NOT NULL,
  dataset_id text NOT NULL,
  vault_key_id uuid NOT NULL,
  location text DEFAULT 'US'::text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE public.calendar_settings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  calendar_id text,
  enabled bool NOT NULL DEFAULT false,
  range_days int4 NOT NULL DEFAULT 30,
  timezone text NOT NULL DEFAULT 'America/Sao_Paulo'::text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  provider text,
  calendar_name text
);
CREATE TABLE public.calendar_watch_channels (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  channel_id text NOT NULL,
  client_id uuid NOT NULL,
  calendar_id text NOT NULL DEFAULT 'primary'::text,
  resource_id text,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.canonical_columns (
  id int4 NOT NULL DEFAULT nextval('canonical_columns_id_seq'::regclass),
  table_name text NOT NULL,
  column_name text NOT NULL,
  data_type text NOT NULL,
  is_required bool NOT NULL DEFAULT false,
  description text NOT NULL,
  examples text[] DEFAULT '{}'::text[],
  category text NOT NULL DEFAULT 'mappable'::text
);
CREATE TABLE public.client_approval_rules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  agent_slug text,
  rule_type text NOT NULL,
  condition jsonb NOT NULL DEFAULT '{}'::jsonb,
  action text DEFAULT 'auto_approve'::text,
  active bool DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.client_approval_stats (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  total_approved int4 DEFAULT 0,
  total_rejected int4 DEFAULT 0,
  total_edited int4 DEFAULT 0,
  total_snoozed int4 DEFAULT 0,
  trust_level text DEFAULT 'manual'::text,
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE public.client_data_sources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  credential_id int8,
  source_type text NOT NULL,
  resource_type text NOT NULL,
  storage_type text NOT NULL,
  storage_location text NOT NULL,
  column_mapping jsonb,
  source_columns jsonb,
  source_sample_data jsonb,
  sync_status text DEFAULT 'pending'::text,
  last_synced_at timestamptz,
  atualizado_em timestamptz DEFAULT now(),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  unmapped_columns jsonb,
  needs_review_columns jsonb,
  match_confidence jsonb,
  detected_entity_context text,
  auto_column_mapping jsonb,
  ignored_columns text[],
  is_auto_generated bool DEFAULT false,
  reviewed_at timestamptz,
  user_column_changes jsonb,
  ingestion_quality jsonb,
  watermark_column text,
  last_watermark_value text,
  drive_file_id text,
  drive_modified_time timestamptz,
  integration_token_id uuid
);
CREATE TABLE public.client_dimension_kpis (
  client_id uuid NOT NULL,
  dimension text NOT NULL,
  slug text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.client_enabled_agents (
  client_id uuid NOT NULL,
  agent_slug text NOT NULL,
  config jsonb DEFAULT '{}'::jsonb,
  enabled_at timestamptz NOT NULL DEFAULT now(),
  current_status text DEFAULT 'idle'::text,
  last_activity_at timestamptz,
  pending_count int4 DEFAULT 0
);
CREATE TABLE public.client_goals (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  dimension text NOT NULL,
  title text NOT NULL,
  description text,
  target_value numeric,
  current_value numeric,
  unit text,
  deadline date,
  status text NOT NULL DEFAULT 'active'::text,
  action_plan jsonb,
  source_agent text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.client_insights (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  title text NOT NULL,
  body text,
  severity text DEFAULT 'info'::text,
  dismissed bool DEFAULT false,
  dismissed_at timestamptz,
  generated_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  kpi text,
  observation text,
  recommendation text,
  metric_value numeric,
  baseline_value numeric,
  variance_pct numeric,
  run_date date,
  prompt_version text,
  room text
);
CREATE TABLE public.client_knowledge_documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  document_type_id text NOT NULL,
  status text NOT NULL DEFAULT 'missing'::text,
  source text,
  vector_document_id uuid,
  field_coverage jsonb DEFAULT '{}'::jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.client_notification_preferences (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  notification_type text NOT NULL,
  channel text NOT NULL,
  enabled bool DEFAULT true,
  quiet_hours_start time,
  quiet_hours_end time,
  timezone text DEFAULT 'America/Sao_Paulo'::text
);
CREATE TABLE public.client_routine_executions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  routine_id text NOT NULL,
  triggered_by text NOT NULL,
  trigger_data jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending'::text,
  dispatched_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  result_text text,
  result_metadata jsonb DEFAULT '{}'::jsonb,
  completed_at timestamptz,
  worker_slug text,
  heartbeat_at timestamptz,
  failure_count int4 NOT NULL DEFAULT 0
);
CREATE TABLE public.client_routines (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  routine_id text NOT NULL,
  notify_channel text NOT NULL DEFAULT 'app'::text,
  config jsonb DEFAULT '{}'::jsonb,
  active bool DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_run_at timestamptz,
  source text NOT NULL DEFAULT 'catalog'::text,
  status text NOT NULL DEFAULT 'active'::text,
  name text,
  description text,
  steps jsonb DEFAULT '[]'::jsonb,
  trigger_type text DEFAULT 'manual'::text,
  trigger_config jsonb DEFAULT '{}'::jsonb,
  created_by_ai bool NOT NULL DEFAULT false,
  consecutive_failures int4 NOT NULL DEFAULT 0
);
CREATE TABLE public.client_users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  auth_user_id uuid,
  email text NOT NULL,
  name text,
  role text NOT NULL DEFAULT 'member'::text,
  agent_permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
  action_permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
  invited_at timestamptz DEFAULT now(),
  accepted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.clientes_blu (
  client_id uuid NOT NULL DEFAULT gen_random_uuid(),
  api_key text,
  nome_empresa text NOT NULL DEFAULT 'Empresa'::text,
  tipo_cliente text DEFAULT 'standard'::text,
  tier text DEFAULT 'free'::text,
  collection_rag text DEFAULT 'default_collection'::text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  external_user_id text,
  onboarding_state jsonb DEFAULT '{}'::jsonb,
  onboarding_completed_at timestamptz,
  company_profile jsonb DEFAULT '{}'::jsonb,
  brand_voice jsonb DEFAULT '{}'::jsonb,
  team_structure jsonb DEFAULT '{}'::jsonb,
  policies jsonb DEFAULT '{}'::jsonb,
  data_schema jsonb DEFAULT '{}'::jsonb,
  available_tools jsonb DEFAULT '{}'::jsonb,
  cpf_cnpj text,
  password text,
  deleted_at timestamptz,
  ui_prefs jsonb DEFAULT '{}'::jsonb,
  email text,
  email_domain text
);
CREATE TABLE public.cnpj_enrichments (
  cnpj text NOT NULL,
  brand text,
  logo_url text,
  colors jsonb,
  social jsonb,
  enriched_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.conversa (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.credencial_servico_externo (
  id int8 NOT NULL DEFAULT nextval('credencial_servico_externo_id_seq'::regclass),
  client_id uuid NOT NULL,
  tipo text,
  credenciais jsonb NOT NULL DEFAULT '{}'::jsonb,
  nome text,
  ativo bool NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  connection_metadata jsonb DEFAULT '{}'::jsonb,
  nome_servico text,
  tipo_servico text,
  status text DEFAULT 'pending'::text,
  vault_key_id uuid
);
CREATE TABLE public.cross_agent_routines (
  id text NOT NULL,
  name text NOT NULL,
  trigger_domain text,
  trigger_document_id text,
  trigger_status text,
  trigger_condition text,
  steps jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  room text NOT NULL,
  config_schema jsonb DEFAULT '[]'::jsonb,
  trigger_type text NOT NULL DEFAULT 'manual'::text,
  trigger_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  visibility text DEFAULT 'user'::text
);
CREATE TABLE public.csv_import_staging (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  source_id uuid NOT NULL,
  rows jsonb NOT NULL,
  row_count int4 NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.data_source_mappings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  credential_id uuid NOT NULL,
  resource_type varchar(50) NOT NULL,
  source_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
  mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
  unmapped_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
  confidence_scores jsonb NOT NULL DEFAULT '{}'::jsonb,
  status varchar(20) NOT NULL DEFAULT 'pending'::character varying,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  client_id uuid
);
CREATE TABLE public.dimension_state (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  dimension text NOT NULL,
  summary text NOT NULL,
  structured jsonb,
  valid_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.doc_templates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  name text NOT NULL,
  description text,
  category text,
  is_system bool NOT NULL DEFAULT false,
  content jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.document_versions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL,
  version_number int4 NOT NULL DEFAULT 1,
  editor_content jsonb,
  summary text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  title text NOT NULL DEFAULT 'Sem título'::text,
  agent_slug text NOT NULL DEFAULT 'documentos'::text,
  editor_content jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'published'::text
);
CREATE TABLE public.frontend_events (
  id int8 NOT NULL DEFAULT nextval('frontend_events_id_seq'::regclass),
  client_id uuid,
  event_name text NOT NULL,
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.integration_configs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  provider text NOT NULL,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.integration_tokens (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  provider text NOT NULL,
  account_email text NOT NULL DEFAULT ''::text,
  token_type text DEFAULT 'Bearer'::text,
  scopes text[],
  is_default bool DEFAULT false,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  vault_secret_name text,
  refresh_token_encrypted text,
  access_token_encrypted text
);
CREATE TABLE public.knowledge_agent_requirements (
  agent_slug text NOT NULL,
  document_type_id text NOT NULL,
  requirement_type text NOT NULL,
  coverage_threshold numeric NOT NULL DEFAULT 0.8
);
CREATE TABLE public.knowledge_document_types (
  id text NOT NULL,
  domain_id text NOT NULL,
  subdomain_id text,
  name text NOT NULL,
  type text NOT NULL,
  created_by text,
  consumed_by text[] DEFAULT '{}'::text[],
  fields text[] DEFAULT '{}'::text[],
  status text NOT NULL DEFAULT 'required'::text,
  coverage_weight numeric NOT NULL DEFAULT 1.0,
  tags text[] DEFAULT '{}'::text[],
  sort_order int4 DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.knowledge_tag_definitions (
  tag text NOT NULL,
  description text,
  consumed_by text[] DEFAULT '{}'::text[]
);
CREATE TABLE public.kpi_catalog (
  slug text NOT NULL,
  dimension text NOT NULL,
  label text NOT NULL,
  formula text NOT NULL,
  unit text NOT NULL DEFAULT 'number'::text,
  is_leading bool NOT NULL DEFAULT false,
  tier_required text NOT NULL DEFAULT 'BASIC'::text,
  data_status text NOT NULL DEFAULT 'live'::text,
  rpc_column text,
  description text,
  references_url text,
  sort_order int4 NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
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
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  type text NOT NULL,
  title text NOT NULL,
  body text,
  agent_slug text,
  related_entity_type text,
  related_entity_id uuid,
  urgency_level text DEFAULT 'normal'::text,
  channels text[] DEFAULT ARRAY['in_app'::text],
  read_at timestamptz,
  dismissed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.nps_responses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  score int4 NOT NULL,
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.polp_accounts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  integration_id uuid NOT NULL,
  polp_account_id int4 NOT NULL,
  type text NOT NULL,
  subtype text,
  number text,
  name text,
  balance numeric NOT NULL DEFAULT 0,
  currency_code text NOT NULL DEFAULT 'BRL'::text,
  marketing_name text,
  owner text,
  bank_data jsonb,
  credit_data jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.polp_bills (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  polp_account_id int4 NOT NULL,
  polp_bill_id int4 NOT NULL,
  due_date date NOT NULL,
  total_amount numeric NOT NULL,
  minimum_payment_amount numeric,
  currency_code text NOT NULL DEFAULT 'BRL'::text,
  allows_installments bool,
  finance_charges jsonb,
  payments jsonb,
  status text NOT NULL DEFAULT 'open'::text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.polp_integrations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  polp_integration_id int4 NOT NULL,
  institution_id int4 NOT NULL,
  status text NOT NULL DEFAULT 'UPDATING'::text,
  execution_status text,
  error text,
  url_to_authenticate text,
  url_to_authenticate_expires_at timestamptz,
  last_updated_at timestamptz,
  next_auto_sync_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.polp_transactions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  polp_account_id int4 NOT NULL,
  polp_transaction_id int4 NOT NULL,
  external_id text,
  description text,
  amount numeric NOT NULL,
  currency_code text NOT NULL DEFAULT 'BRL'::text,
  date date NOT NULL,
  type text NOT NULL,
  status text,
  balance_after numeric,
  category jsonb,
  merchant jsonb,
  payment_data jsonb,
  credit_card_metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.report_runs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  schedule_id uuid,
  client_id uuid,
  status text NOT NULL DEFAULT 'pending'::text,
  output_url text,
  error text,
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb
);
CREATE TABLE public.report_schedules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  name text NOT NULL,
  report_type text NOT NULL,
  cron_expr text,
  recipients text[],
  config jsonb DEFAULT '{}'::jsonb,
  active bool DEFAULT true,
  last_run_at timestamptz,
  next_run_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.sql_table_config (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  table_name text NOT NULL,
  display_name text,
  description text,
  is_primary bool NOT NULL DEFAULT false,
  column_descriptions jsonb DEFAULT '{}'::jsonb,
  enum_values jsonb DEFAULT '{}'::jsonb,
  example_queries jsonb DEFAULT '[]'::jsonb,
  join_keys jsonb DEFAULT '[]'::jsonb,
  is_active bool NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.standalone_agent_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  agent_catalog_id uuid NOT NULL,
  session_id text NOT NULL,
  config_status text DEFAULT 'configuring'::text,
  collected_context jsonb DEFAULT '{}'::jsonb,
  uploaded_file_ids uuid[] DEFAULT ARRAY[]::uuid[],
  uploaded_document_ids uuid[] DEFAULT ARRAY[]::uuid[],
  google_account_email text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.uploaded_files_metadata (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  file_name text NOT NULL,
  storage_path text NOT NULL,
  bucket text NOT NULL DEFAULT 'file-uploads'::text,
  mime_type text,
  size_bytes int8,
  status text DEFAULT 'uploaded'::text,
  metadata jsonb DEFAULT '{}'::jsonb,
  content_hash text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Primary keys & unique constraints
ALTER TABLE public.agent_catalog ADD CONSTRAINT agent_catalog_pkey PRIMARY KEY (id);
ALTER TABLE public.agent_catalog ADD CONSTRAINT agent_catalog_slug_key UNIQUE (slug);
ALTER TABLE public.app_config ADD CONSTRAINT app_config_pkey PRIMARY KEY (key);
ALTER TABLE public.approval_requests ADD CONSTRAINT approval_requests_pkey PRIMARY KEY (id);
ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);
ALTER TABLE public.bigquery_foreign_tables ADD CONSTRAINT bigquery_foreign_tables_pkey PRIMARY KEY (id);
ALTER TABLE public.bigquery_foreign_tables ADD CONSTRAINT bigquery_foreign_tables_client_id_table_name_key UNIQUE (client_id, table_name);
ALTER TABLE public.bigquery_servers ADD CONSTRAINT bigquery_servers_pkey PRIMARY KEY (id);
ALTER TABLE public.bigquery_servers ADD CONSTRAINT bigquery_servers_client_id_key UNIQUE (client_id);
ALTER TABLE public.bigquery_servers ADD CONSTRAINT bigquery_servers_server_name_key UNIQUE (server_name);
ALTER TABLE public.calendar_settings ADD CONSTRAINT calendar_settings_pkey PRIMARY KEY (id);
ALTER TABLE public.calendar_settings ADD CONSTRAINT calendar_settings_client_id_key UNIQUE (client_id);
ALTER TABLE public.calendar_watch_channels ADD CONSTRAINT calendar_watch_channels_pkey PRIMARY KEY (id);
ALTER TABLE public.calendar_watch_channels ADD CONSTRAINT calendar_watch_channels_client_id_calendar_id_key UNIQUE (client_id, calendar_id);
ALTER TABLE public.canonical_columns ADD CONSTRAINT canonical_columns_pkey PRIMARY KEY (id);
ALTER TABLE public.canonical_columns ADD CONSTRAINT canonical_columns_table_name_column_name_key UNIQUE (table_name, column_name);
ALTER TABLE public.client_approval_rules ADD CONSTRAINT client_approval_rules_pkey PRIMARY KEY (id);
ALTER TABLE public.client_approval_stats ADD CONSTRAINT client_approval_stats_pkey PRIMARY KEY (client_id);
ALTER TABLE public.client_approval_stats ADD CONSTRAINT client_approval_stats_id_key UNIQUE (id);
ALTER TABLE public.client_data_sources ADD CONSTRAINT client_data_sources_pkey PRIMARY KEY (id);
ALTER TABLE public.client_data_sources ADD CONSTRAINT unique_client_source_resource UNIQUE (client_id, source_type, resource_type);
ALTER TABLE public.client_dimension_kpis ADD CONSTRAINT client_dimension_kpis_pkey PRIMARY KEY (client_id, dimension, slug);
ALTER TABLE public.client_enabled_agents ADD CONSTRAINT client_enabled_agents_pkey PRIMARY KEY (client_id, agent_slug);
ALTER TABLE public.client_goals ADD CONSTRAINT client_goals_pkey PRIMARY KEY (id);
ALTER TABLE public.client_insights ADD CONSTRAINT client_insights_pkey PRIMARY KEY (id);
ALTER TABLE public.client_knowledge_documents ADD CONSTRAINT client_knowledge_documents_pkey PRIMARY KEY (id);
ALTER TABLE public.client_knowledge_documents ADD CONSTRAINT uq_client_document UNIQUE (client_id, document_type_id);
ALTER TABLE public.client_notification_preferences ADD CONSTRAINT client_notification_preferences_pkey PRIMARY KEY (id);
ALTER TABLE public.client_notification_preferences ADD CONSTRAINT client_notification_preferences_unique UNIQUE (client_id, notification_type, channel);
ALTER TABLE public.client_routine_executions ADD CONSTRAINT client_routine_executions_pkey PRIMARY KEY (id);
ALTER TABLE public.client_routines ADD CONSTRAINT client_routines_pkey PRIMARY KEY (id);
ALTER TABLE public.client_routines ADD CONSTRAINT client_routines_client_id_routine_id_key UNIQUE (client_id, routine_id);
ALTER TABLE public.client_users ADD CONSTRAINT client_users_pkey PRIMARY KEY (id);
ALTER TABLE public.client_users ADD CONSTRAINT client_users_unique_email UNIQUE (client_id, email);
ALTER TABLE public.clientes_blu ADD CONSTRAINT clientes_blu_pkey PRIMARY KEY (client_id);
ALTER TABLE public.clientes_blu ADD CONSTRAINT clientes_blu_api_key_key UNIQUE (api_key);
ALTER TABLE public.clientes_blu ADD CONSTRAINT clientes_blu_external_user_id_key UNIQUE (external_user_id);
ALTER TABLE public.cnpj_enrichments ADD CONSTRAINT cnpj_enrichments_pkey PRIMARY KEY (cnpj);
ALTER TABLE public.conversa ADD CONSTRAINT conversa_pkey PRIMARY KEY (id);
ALTER TABLE public.credencial_servico_externo ADD CONSTRAINT credencial_servico_externo_pkey PRIMARY KEY (id);
ALTER TABLE public.cross_agent_routines ADD CONSTRAINT cross_agent_routines_pkey PRIMARY KEY (id);
ALTER TABLE public.csv_import_staging ADD CONSTRAINT csv_import_staging_pkey PRIMARY KEY (id);
ALTER TABLE public.data_source_mappings ADD CONSTRAINT data_source_mappings_pkey PRIMARY KEY (id);
ALTER TABLE public.data_source_mappings ADD CONSTRAINT unique_credential_resource UNIQUE (credential_id, resource_type);
ALTER TABLE public.dimension_state ADD CONSTRAINT dimension_state_pkey PRIMARY KEY (id);
ALTER TABLE public.dimension_state ADD CONSTRAINT dimension_state_client_dimension_key UNIQUE (client_id, dimension);
ALTER TABLE public.doc_templates ADD CONSTRAINT doc_templates_pkey PRIMARY KEY (id);
ALTER TABLE public.document_versions ADD CONSTRAINT document_versions_pkey PRIMARY KEY (id);
ALTER TABLE public.document_versions ADD CONSTRAINT document_versions_document_id_version_number_key UNIQUE (document_id, version_number);
ALTER TABLE public.documents ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
ALTER TABLE public.documents ADD CONSTRAINT documents_client_id_title_key UNIQUE (client_id, title);
ALTER TABLE public.frontend_events ADD CONSTRAINT frontend_events_pkey PRIMARY KEY (id);
ALTER TABLE public.integration_configs ADD CONSTRAINT integration_configs_pkey PRIMARY KEY (id);
ALTER TABLE public.integration_configs ADD CONSTRAINT integration_configs_client_id_provider_key UNIQUE (client_id, provider);
ALTER TABLE public.integration_tokens ADD CONSTRAINT integration_tokens_pkey PRIMARY KEY (id);
ALTER TABLE public.integration_tokens ADD CONSTRAINT integration_tokens_client_id_provider_account_email_key UNIQUE (client_id, provider, account_email);
ALTER TABLE public.knowledge_agent_requirements ADD CONSTRAINT knowledge_agent_requirements_pkey PRIMARY KEY (agent_slug, document_type_id);
ALTER TABLE public.knowledge_document_types ADD CONSTRAINT knowledge_document_types_pkey PRIMARY KEY (id);
ALTER TABLE public.knowledge_tag_definitions ADD CONSTRAINT knowledge_tag_definitions_pkey PRIMARY KEY (tag);
ALTER TABLE public.kpi_catalog ADD CONSTRAINT kpi_catalog_pkey PRIMARY KEY (slug);
ALTER TABLE public.messages ADD CONSTRAINT messages_pkey PRIMARY KEY (id);
ALTER TABLE public.notifications ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);
ALTER TABLE public.nps_responses ADD CONSTRAINT nps_responses_pkey PRIMARY KEY (id);
ALTER TABLE public.polp_accounts ADD CONSTRAINT polp_accounts_pkey PRIMARY KEY (id);
ALTER TABLE public.polp_accounts ADD CONSTRAINT polp_accounts_client_id_polp_account_id_key UNIQUE (client_id, polp_account_id);
ALTER TABLE public.polp_bills ADD CONSTRAINT polp_bills_pkey PRIMARY KEY (id);
ALTER TABLE public.polp_bills ADD CONSTRAINT polp_bills_client_id_polp_bill_id_key UNIQUE (client_id, polp_bill_id);
ALTER TABLE public.polp_integrations ADD CONSTRAINT polp_integrations_pkey PRIMARY KEY (id);
ALTER TABLE public.polp_integrations ADD CONSTRAINT polp_integrations_client_id_polp_integration_id_key UNIQUE (client_id, polp_integration_id);
ALTER TABLE public.polp_transactions ADD CONSTRAINT polp_transactions_pkey PRIMARY KEY (id);
ALTER TABLE public.polp_transactions ADD CONSTRAINT polp_transactions_client_id_polp_transaction_id_key UNIQUE (client_id, polp_transaction_id);
ALTER TABLE public.report_runs ADD CONSTRAINT report_runs_pkey PRIMARY KEY (id);
ALTER TABLE public.report_schedules ADD CONSTRAINT report_schedules_pkey PRIMARY KEY (id);
ALTER TABLE public.sql_table_config ADD CONSTRAINT sql_table_config_pkey PRIMARY KEY (id);
ALTER TABLE public.standalone_agent_sessions ADD CONSTRAINT standalone_agent_sessions_pkey PRIMARY KEY (id);
ALTER TABLE public.standalone_agent_sessions ADD CONSTRAINT standalone_agent_sessions_session_id_key UNIQUE (session_id);
ALTER TABLE public.uploaded_files_metadata ADD CONSTRAINT uploaded_files_metadata_pkey PRIMARY KEY (id);

-- Foreign keys
ALTER TABLE public.approval_requests ADD CONSTRAINT approval_requests_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.bigquery_foreign_tables ADD CONSTRAINT bigquery_foreign_tables_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES public.credencial_servico_externo (id) ON DELETE CASCADE;
ALTER TABLE public.bigquery_foreign_tables ADD CONSTRAINT fk_bigquery_foreign_tables_client FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.bigquery_foreign_tables ADD CONSTRAINT fk_server FOREIGN KEY (server_name) REFERENCES public.bigquery_servers (server_name) ON DELETE CASCADE;
ALTER TABLE public.bigquery_servers ADD CONSTRAINT fk_bigquery_servers_client FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.calendar_settings ADD CONSTRAINT calendar_settings_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.calendar_watch_channels ADD CONSTRAINT calendar_watch_channels_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_approval_rules ADD CONSTRAINT client_approval_rules_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_approval_stats ADD CONSTRAINT client_approval_stats_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_data_sources ADD CONSTRAINT client_data_sources_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES public.credencial_servico_externo (id) ON DELETE SET NULL;
ALTER TABLE public.client_data_sources ADD CONSTRAINT client_data_sources_integration_token_id_fkey FOREIGN KEY (integration_token_id) REFERENCES public.integration_tokens (id) ON DELETE SET NULL;
ALTER TABLE public.client_data_sources ADD CONSTRAINT fk_client_data_sources_client FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_dimension_kpis ADD CONSTRAINT client_dimension_kpis_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_dimension_kpis ADD CONSTRAINT client_dimension_kpis_slug_fkey FOREIGN KEY (slug) REFERENCES public.kpi_catalog (slug) ON DELETE CASCADE;
ALTER TABLE public.client_enabled_agents ADD CONSTRAINT client_enabled_agents_agent_slug_fkey FOREIGN KEY (agent_slug) REFERENCES public.agent_catalog (slug) ON DELETE CASCADE;
ALTER TABLE public.client_enabled_agents ADD CONSTRAINT client_enabled_agents_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_goals ADD CONSTRAINT client_goals_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_insights ADD CONSTRAINT client_insights_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_knowledge_documents ADD CONSTRAINT client_knowledge_documents_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_knowledge_documents ADD CONSTRAINT client_knowledge_documents_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.knowledge_document_types (id);
ALTER TABLE public.client_notification_preferences ADD CONSTRAINT client_notification_preferences_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_routine_executions ADD CONSTRAINT client_routine_executions_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_routines ADD CONSTRAINT client_routines_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.client_routines ADD CONSTRAINT client_routines_routine_id_fkey FOREIGN KEY (routine_id) REFERENCES public.cross_agent_routines (id) ON DELETE CASCADE;
ALTER TABLE public.client_users ADD CONSTRAINT client_users_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.conversa ADD CONSTRAINT conversa_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.credencial_servico_externo ADD CONSTRAINT fk_credencial_servico_externo_client FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.cross_agent_routines ADD CONSTRAINT cross_agent_routines_trigger_document_id_fkey FOREIGN KEY (trigger_document_id) REFERENCES public.knowledge_document_types (id);
ALTER TABLE public.csv_import_staging ADD CONSTRAINT csv_import_staging_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.client_data_sources (id) ON DELETE CASCADE;
ALTER TABLE public.dimension_state ADD CONSTRAINT dimension_state_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.doc_templates ADD CONSTRAINT doc_templates_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.document_versions ADD CONSTRAINT document_versions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents (id) ON DELETE CASCADE;
ALTER TABLE public.documents ADD CONSTRAINT documents_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.frontend_events ADD CONSTRAINT frontend_events_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.integration_configs ADD CONSTRAINT integration_configs_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.integration_tokens ADD CONSTRAINT integration_tokens_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.knowledge_agent_requirements ADD CONSTRAINT knowledge_agent_requirements_agent_slug_fkey FOREIGN KEY (agent_slug) REFERENCES public.agent_catalog (slug) ON DELETE CASCADE;
ALTER TABLE public.knowledge_agent_requirements ADD CONSTRAINT knowledge_agent_requirements_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.knowledge_document_types (id) ON DELETE CASCADE;
ALTER TABLE public.messages ADD CONSTRAINT messages_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.messages ADD CONSTRAINT messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.conversa (id) ON DELETE SET NULL;
ALTER TABLE public.notifications ADD CONSTRAINT notifications_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.nps_responses ADD CONSTRAINT nps_responses_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.polp_accounts ADD CONSTRAINT polp_accounts_integration_id_fkey FOREIGN KEY (integration_id) REFERENCES public.polp_integrations (id) ON DELETE CASCADE;
ALTER TABLE public.report_runs ADD CONSTRAINT report_runs_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.report_runs ADD CONSTRAINT report_runs_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.report_schedules (id) ON DELETE CASCADE;
ALTER TABLE public.report_schedules ADD CONSTRAINT report_schedules_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.sql_table_config ADD CONSTRAINT sql_table_config_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.standalone_agent_sessions ADD CONSTRAINT standalone_agent_sessions_agent_catalog_id_fkey FOREIGN KEY (agent_catalog_id) REFERENCES public.agent_catalog (id) ON DELETE SET NULL;
ALTER TABLE public.standalone_agent_sessions ADD CONSTRAINT standalone_agent_sessions_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;
ALTER TABLE public.uploaded_files_metadata ADD CONSTRAINT uploaded_files_metadata_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE;

-- Indexes
CREATE INDEX idx_approval_agent_slug ON public.approval_requests USING btree (client_id, agent_slug);
CREATE INDEX idx_approval_client_status ON public.approval_requests USING btree (client_id, status);
CREATE INDEX idx_approval_session_id ON public.approval_requests USING btree (session_id) WHERE (session_id IS NOT NULL);
CREATE INDEX idx_audit_client ON public.audit_log USING btree (client_id);
CREATE INDEX idx_audit_created ON public.audit_log USING btree (created_at DESC);
CREATE INDEX idx_bft_client_credential ON public.bigquery_foreign_tables USING btree (client_id, credential_id);
CREATE INDEX idx_calendar_watch_channel_id ON public.calendar_watch_channels USING btree (channel_id);
CREATE INDEX idx_cds_client_id ON public.client_data_sources USING btree (client_id);
CREATE INDEX idx_cds_credential_id ON public.client_data_sources USING btree (credential_id);
CREATE INDEX idx_cds_drive_file_id ON public.client_data_sources USING btree (client_id, drive_file_id) WHERE (drive_file_id IS NOT NULL);
CREATE INDEX idx_cds_integration_token ON public.client_data_sources USING btree (integration_token_id) WHERE (integration_token_id IS NOT NULL);
CREATE INDEX idx_client_goals_active ON public.client_goals USING btree (client_id, dimension) WHERE (status = 'active'::text);
CREATE INDEX idx_client_goals_client_id ON public.client_goals USING btree (client_id);
CREATE UNIQUE INDEX client_insights_client_run_room_kpi_idx ON public.client_insights USING btree (client_id, run_date, room, kpi) WHERE ((run_date IS NOT NULL) AND (kpi IS NOT NULL));
CREATE INDEX idx_insights_client_active ON public.client_insights USING btree (client_id, dismissed, generated_at DESC);
CREATE INDEX idx_ckd_client ON public.client_knowledge_documents USING btree (client_id);
CREATE INDEX idx_ckd_client_status ON public.client_knowledge_documents USING btree (client_id, status);
CREATE INDEX idx_routine_exec_awaiting_approval ON public.client_routine_executions USING btree (client_id, dispatched_at) WHERE (status = 'awaiting_approval'::text);
CREATE INDEX idx_routine_exec_client ON public.client_routine_executions USING btree (client_id, routine_id, created_at DESC);
CREATE INDEX idx_routine_exec_dispatched ON public.client_routine_executions USING btree (dispatched_at) WHERE (status = 'dispatched'::text);
CREATE INDEX idx_routine_exec_heartbeat ON public.client_routine_executions USING btree (heartbeat_at) WHERE ((status = 'dispatched'::text) AND (heartbeat_at IS NOT NULL));
CREATE INDEX idx_routine_exec_pending ON public.client_routine_executions USING btree (status) WHERE (status = 'pending'::text);
CREATE INDEX idx_routine_exec_stale ON public.client_routine_executions USING btree (dispatched_at) WHERE (status = 'dispatched'::text);
CREATE INDEX idx_client_routines_source_status ON public.client_routines USING btree (source, status);
CREATE INDEX idx_client_users_auth_user_id ON public.client_users USING btree (auth_user_id) WHERE (auth_user_id IS NOT NULL);
CREATE INDEX idx_client_users_client_id ON public.client_users USING btree (client_id);
CREATE INDEX idx_client_users_email ON public.client_users USING btree (email);
CREATE INDEX idx_clientes_blu_api_key ON public.clientes_blu USING btree (api_key) WHERE (api_key IS NOT NULL);
CREATE INDEX idx_clientes_blu_client_id ON public.clientes_blu USING btree (client_id);
CREATE INDEX idx_clientes_blu_deleted_at ON public.clientes_blu USING btree (deleted_at) WHERE (deleted_at IS NOT NULL);
CREATE INDEX idx_clientes_blu_external_user ON public.clientes_blu USING btree (external_user_id);
CREATE INDEX idx_clientes_blu_external_user_id ON public.clientes_blu USING btree (external_user_id) WHERE (external_user_id IS NOT NULL);
CREATE INDEX idx_clientes_blu_onboarding_incomplete ON public.clientes_blu USING btree (client_id) WHERE (onboarding_completed_at IS NULL);
CREATE INDEX idx_credencial_client_id ON public.credencial_servico_externo USING btree (client_id);
CREATE INDEX idx_csv_staging_client_id ON public.csv_import_staging USING btree (client_id);
CREATE INDEX idx_csv_staging_source_id ON public.csv_import_staging USING btree (source_id);
CREATE INDEX idx_mappings_credential ON public.data_source_mappings USING btree (credential_id);
CREATE INDEX idx_mappings_resource ON public.data_source_mappings USING btree (resource_type);
CREATE INDEX idx_mappings_status ON public.data_source_mappings USING btree (status);
CREATE INDEX idx_dimension_state_client_id ON public.dimension_state USING btree (client_id);
CREATE INDEX idx_dimension_state_valid_until ON public.dimension_state USING btree (client_id, valid_until);
CREATE INDEX doc_templates_client_id_idx ON public.doc_templates USING btree (client_id) WHERE (client_id IS NOT NULL);
CREATE INDEX document_versions_document_id_idx ON public.document_versions USING btree (document_id, version_number DESC);
CREATE INDEX documents_client_id_idx ON public.documents USING btree (client_id, updated_at DESC);
CREATE INDEX idx_fe_client_event ON public.frontend_events USING btree (client_id, event_name);
CREATE INDEX idx_fe_created_at ON public.frontend_events USING btree (created_at DESC);
CREATE INDEX idx_tokens_client_provider ON public.integration_tokens USING btree (client_id, provider);
CREATE INDEX idx_messages_client ON public.messages USING btree (client_id, created_at DESC);
CREATE INDEX idx_messages_session ON public.messages USING btree (session_id) WHERE (session_id IS NOT NULL);
CREATE INDEX idx_notifications_client_unread ON public.notifications USING btree (client_id, read_at, created_at DESC) WHERE (dismissed_at IS NULL);
CREATE INDEX idx_nps_client ON public.nps_responses USING btree (client_id);
CREATE INDEX polp_accounts_client_id_idx ON public.polp_accounts USING btree (client_id);
CREATE INDEX polp_accounts_integration_id_idx ON public.polp_accounts USING btree (integration_id);
CREATE INDEX polp_bills_client_id_due_date_idx ON public.polp_bills USING btree (client_id, due_date);
CREATE INDEX polp_integrations_client_id_idx ON public.polp_integrations USING btree (client_id);
CREATE INDEX polp_transactions_client_id_date_idx ON public.polp_transactions USING btree (client_id, date DESC);
CREATE INDEX polp_transactions_polp_account_id_idx ON public.polp_transactions USING btree (polp_account_id);
CREATE INDEX idx_report_runs_client ON public.report_runs USING btree (client_id, started_at DESC);
CREATE INDEX sql_table_config_client_id_idx ON public.sql_table_config USING btree (client_id) WHERE (is_active = true);
CREATE UNIQUE INDEX sql_table_config_client_table_uidx ON public.sql_table_config USING btree (client_id, table_name) WHERE (client_id IS NOT NULL);
CREATE UNIQUE INDEX sql_table_config_global_table_uidx ON public.sql_table_config USING btree (table_name) WHERE (client_id IS NULL);
CREATE INDEX idx_uploaded_files_client ON public.uploaded_files_metadata USING btree (client_id);

-- Functions (107 total)
CREATE OR REPLACE FUNCTION public._bq_canonical_ref(p_project_id text, p_dataset_id text, p_table_name text)
RETURNS text
LANGUAGE sql
AS $function$

  SELECT p_project_id || '.' || p_dataset_id || '.' || p_table_name;

$function$;

CREATE OR REPLACE FUNCTION public._bq_col_defs_from_jsonb(p_columns jsonb)
RETURNS text
LANGUAGE sql
AS $function$

  SELECT string_agg(
    format('%I %s', col->>'name', public._bq_type_to_postgres_type(col->>'type')),
    ', '
    ORDER BY ordinality
  )
  FROM jsonb_array_elements(p_columns) WITH ORDINALITY AS t(col, ordinality);

$function$;

CREATE OR REPLACE FUNCTION public._bq_type_to_postgres_type(p_bq_type text)
RETURNS text
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.auto_enroll_catalog_routines()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  INSERT INTO public.client_routines (
    client_id, routine_id, source, status, active,
    config, trigger_type, trigger_config
  )
  SELECT
    NEW.client_id,
    r.id,
    'catalog',
    'inactive',
    false,
    '{}'::jsonb,
    r.trigger_type,
    r.trigger_config
  FROM public.cross_agent_routines r
  WHERE r.visibility = 'user'
  ON CONFLICT DO NOTHING;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.auto_enroll_system_routines()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  INSERT INTO public.client_routines (
    id, client_id, routine_id, notify_channel, config,
    source, status, trigger_type, trigger_config, created_at
  )
  SELECT
    gen_random_uuid(),
    NEW.client_id,
    r.id,
    'app',
    '{}'::jsonb,
    'system',
    'active',
    r.trigger_type,
    r.trigger_config,
    now()
  FROM public.cross_agent_routines r
  WHERE r.visibility = 'system'
  ON CONFLICT DO NOTHING;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.bootstrap_knowledge_from_onboarding(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_cp        jsonb;
  v_ts        jsonb;
  v_seeded    int := 0;
BEGIN
  SELECT company_profile, team_structure
    INTO v_cp, v_ts
    FROM public.clientes_blu
   WHERE client_id = p_client_id;

  -- ficha_cadastral: partial if any profile identity fields exist
  IF (v_cp->>'legal_name') IS NOT NULL OR (v_cp->>'industry') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- perfil_empresarial: partial if industry + size both set
  IF (v_cp->>'industry') IS NOT NULL AND (v_cp->>'employee_count_range') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'perfil_empresarial', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- posicionamento: partial if website context exists in RAG
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

  -- organograma: partial if team contacts are set
  IF jsonb_array_length(COALESCE(v_ts->'key_contacts', '[]'::jsonb)) > 0 THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'organograma', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ERP/commerce integration → seed commerce + financial docs as partial
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

  -- ERP with purchasing features → supplier/inventory docs
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

  -- client_data_sources synced → upgrade to complete (never downgrade)
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
     AND ckd.status != 'complete';

  RETURN jsonb_build_object('client_id', p_client_id, 'docs_seeded', v_seeded);
END;

$function$;

CREATE OR REPLACE FUNCTION public.claim_routine_executions(p_batch_size integer DEFAULT 10)
RETURNS SETOF client_routine_executions
LANGUAGE plpgsql
AS $function$

BEGIN
  RETURN QUERY
  UPDATE public.client_routine_executions
    SET status = 'executing'
  WHERE id IN (
    SELECT id
    FROM   public.client_routine_executions
    WHERE  status = 'dispatched'
    ORDER  BY dispatched_at
    LIMIT  p_batch_size
    FOR    UPDATE SKIP LOCKED
  )
  RETURNING *;
END;

$function$;

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(p_client_id text, p_table_name text, p_bigquery_table text, p_location text DEFAULT 'US'::text, p_timeout_ms integer DEFAULT 300000, p_credential_id bigint DEFAULT NULL::bigint)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_my_client_id   UUID;
  v_data_source_id UUID;
  v_server_name    TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  IF p_client_id != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name INTO v_server_name
    FROM public.bigquery_servers
    WHERE client_id = v_my_client_id
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, bigquery_table, server_name, columns, location, created_at, credential_id
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, NOW(), p_credential_id
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      bigquery_table = EXCLUDED.bigquery_table,
      server_name    = EXCLUDED.server_name,
      location       = EXCLUDED.location,
      columns        = '[]'::jsonb,
      credential_id  = EXCLUDED.credential_id;

    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_credential_id,
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
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
  END;
END;

$function$;

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table_from_schema(p_client_id text, p_columns jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_server_name  TEXT;
  v_project_id   TEXT;
  v_dataset_id   TEXT;
  v_bare_table   TEXT;
  v_col_defs     TEXT;
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

  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);
  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty or contains unmappable types');
  END IF;

  UPDATE public.bigquery_foreign_tables
  SET columns        = p_columns,
      server_name    = v_server_name,
      bigquery_table = public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  WHERE client_id::text = p_client_id::text;

  RETURN jsonb_build_object(
    'success',       true,
    'columns_count', jsonb_array_length(p_columns),
    'bigquery_ref',  public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;

$function$;

CREATE OR REPLACE FUNCTION public.create_bigquery_server(p_client_id text, p_service_account_key jsonb, p_project_id text, p_dataset_id text, p_location text DEFAULT 'US'::text)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_my_client_id          UUID;
  v_server_name           TEXT;
  v_vault_key_id          UUID;
  v_secret_name           TEXT;
  v_name_uuid             UUID;
  v_existing_server_name  TEXT;
  v_existing_vault_key_id UUID;
  v_error_msg             TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::uuid != v_my_client_id THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  IF p_service_account_key IS NULL THEN
    RAISE EXCEPTION 'service_account_key cannot be null';
  END IF;
  IF (p_service_account_key->>'type') != 'service_account' THEN
    RAISE EXCEPTION 'Invalid service account key: missing or incorrect type field';
  END IF;
  IF (p_service_account_key->>'project_id') IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing project_id field';
  END IF;
  IF (p_service_account_key->>'private_key') IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing private_key field';
  END IF;

  BEGIN
    v_server_name := 'bigquery_' || v_my_client_id::text;

    -- Return early if server already exists
    SELECT server_name, vault_key_id
    INTO v_existing_server_name, v_existing_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id = v_my_client_id
    LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_existing_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    -- Store service account JSON in Supabase Vault
    v_name_uuid := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_name_uuid::text;

    SELECT vault.create_secret(p_service_account_key::text, v_secret_name)
    INTO v_vault_key_id;

    IF v_vault_key_id IS NULL THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    -- Create FDW server using bigquery_wrapper (Supabase Wrappers)
    EXECUTE format(
      'CREATE SERVER IF NOT EXISTS %I FOREIGN DATA WRAPPER bigquery_wrapper OPTIONS (project_id %L, dataset_id %L, location %L, sa_key_id %L)',
      v_server_name, p_project_id, p_dataset_id, p_location, v_vault_key_id::text
    );

    -- client_id is uuid — no ::text cast
    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id, v_server_name, p_project_id, p_dataset_id,
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
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN
        DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL;
      END;
    END IF;

    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;

$function$;

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

$function$;

CREATE OR REPLACE FUNCTION public.dismiss_insight(p_insight_id uuid)
RETURNS void
LANGUAGE sql
AS $function$

  UPDATE public.client_insights
  SET dismissed = true, dismissed_at = now()
  WHERE id = p_insight_id
    AND client_id = public.get_my_client_id();

$function$;

CREATE OR REPLACE FUNCTION public.dispatch_context_report_on_ingestion()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_cr             RECORD;
  v_in_flight      integer;
  v_cooldown_hours integer;
BEGIN
  -- Only on status transition TO 'completed'
  IF NEW.status != 'completed' OR OLD.status = 'completed' THEN
    RETURN NEW;
  END IF;

  FOR v_cr IN
    SELECT id, last_run_at, trigger_config
    FROM public.client_routines
    WHERE routine_id = 'context_report_post_ingestion'
      AND client_id  = NEW.client_id
      AND active     = true
      AND status     = 'active'
  LOOP
    -- Cooldown guard
    v_cooldown_hours := COALESCE(
      (v_cr.trigger_config->>'cooldown_hours')::integer, 1
    );
    IF v_cr.last_run_at IS NOT NULL AND
       extract(epoch FROM (now() - v_cr.last_run_at)) / 3600 < v_cooldown_hours
    THEN
      CONTINUE;
    END IF;

    -- In-flight guard
    SELECT count(*) INTO v_in_flight
    FROM public.client_routine_executions
    WHERE client_id  = NEW.client_id
      AND routine_id = 'context_report_post_ingestion'
      AND status     IN ('pending', 'dispatched', 'executing');

    IF v_in_flight > 0 THEN
      CONTINUE;
    END IF;

    -- Dispatch
    INSERT INTO public.client_routine_executions (
      id, client_id, routine_id, triggered_by, trigger_data,
      status, dispatched_at, created_at
    ) VALUES (
      gen_random_uuid(),
      NEW.client_id,
      'context_report_post_ingestion',
      'event',
      jsonb_build_object('event_type', 'ingestion_completed', 'job_id', NEW.job_id),
      'dispatched',
      now(),
      now()
    );

    -- Stamp last_run_at to enforce cooldown
    UPDATE public.client_routines
    SET last_run_at = now()
    WHERE id = v_cr.id;

  END LOOP;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.dispatch_routine_event(p_routine_id text, p_client_id uuid, p_trigger_data jsonb DEFAULT '{}'::jsonb)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_exec_id       uuid;
  v_now           timestamptz := now();
  v_routine_exists boolean;
  v_subscription  record;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM public.cross_agent_routines
    WHERE id = p_routine_id
      AND trigger_type = 'event'
  ) INTO v_routine_exists;

  IF NOT v_routine_exists THEN
    RAISE WARNING '[dispatch_routine_event] routine % not found or not event-triggered', p_routine_id;
    RETURN NULL;
  END IF;

  SELECT id INTO v_subscription
  FROM public.client_routines
  WHERE routine_id = p_routine_id
    AND client_id  = p_client_id
    AND active     = true
    AND status     = 'active'
  LIMIT 1;

  IF NOT FOUND THEN
    RAISE WARNING '[dispatch_routine_event] no active subscription for routine % / client %', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND status IN ('pending', 'dispatched', 'executing')
  ) THEN
    RAISE NOTICE '[dispatch_routine_event] in-flight execution exists for routine % / client % — skipping', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data, status, dispatched_at)
  VALUES
    (p_client_id, p_routine_id, 'event', p_trigger_data, 'dispatched', v_now)
  RETURNING id INTO v_exec_id;

  UPDATE public.client_routines
  SET last_run_at = v_now
  WHERE id = v_subscription.id;

  RETURN v_exec_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.dispatch_routine_executions()
RETURNS void
LANGUAGE plpgsql
AS $function$

DECLARE
  _url   text;
  _token text;
BEGIN
  SELECT value INTO _url
  FROM   public.app_config
  WHERE  key = 'agent_api_core_url';

  SELECT value INTO _token
  FROM   public.app_config
  WHERE  key = 'agent_api_routine_dispatch_token';

  IF _url IS NULL OR _url = '' OR _token IS NULL OR _token = '' THEN
    RAISE WARNING '[dispatch_routine_executions] app_config not configured — '
                  'set agent_api_core_url and agent_api_routine_dispatch_token '
                  'in public.app_config to enable automatic routine execution.';
    RETURN;
  END IF;

  PERFORM net.http_post(
    url                  := _url || '/internal/routines/run-dispatched',
    headers              := jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', 'Bearer ' || _token
    ),
    body                 := '{}'::jsonb,
    timeout_milliseconds := 30000
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.drop_bigquery_fdw_server()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  -- Drops the FDW server and all dependent foreign tables in the fdw schema.
  -- EXECUTE is required because server name is dynamic.
  EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', OLD.server_name);
  RETURN OLD;
END;

$function$;

CREATE OR REPLACE FUNCTION public.drop_bigquery_server(p_client_id text)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_my_client_id UUID;
  v_server_name  TEXT;
  v_vault_key_id UUID;
  v_error_msg    TEXT;
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

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN
        DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL;
      END;
    END IF;

    DELETE FROM public.client_data_sources
    WHERE client_id::text = v_my_client_id::text AND source_type = 'bigquery';

    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;
    DELETE FROM public.bigquery_servers        WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and registry removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;

$function$;

CREATE OR REPLACE FUNCTION public.enqueue_custom_routine(p_client_routine_id uuid, p_triggered_by text, p_trigger_data jsonb DEFAULT '{}'::jsonb, p_cooldown_h integer DEFAULT 24)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_cr      record;
  v_exec_id uuid;
BEGIN
  SELECT * INTO v_cr
  FROM public.client_routines
  WHERE id = p_client_routine_id;

  IF NOT FOUND THEN RETURN NULL; END IF;

  IF v_cr.active = false OR v_cr.status <> 'active' THEN
    RETURN NULL;
  END IF;

  IF p_cooldown_h > 0 AND EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = v_cr.client_id
      AND routine_id = v_cr.id::text
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (v_cr.client_id, v_cr.id::text, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_exec_id;

  RETURN v_exec_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.enqueue_monthly_close()
RETURNS integer
LANGUAGE plpgsql
AS $function$

DECLARE
  v_last_day date;
  v_today    date := current_date;
  v_enqueued integer := 0;
  v_client_id uuid;
BEGIN
  -- Calculate last day of current month
  v_last_day := (date_trunc('month', now()) + interval '1 month' - interval '1 day')::date;

  IF v_today <> v_last_day THEN
    RETURN 0;  -- not last day of month
  END IF;

  FOR v_client_id IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    IF public.enqueue_routine(
      v_client_id,
      'monthly_close',
      'cron',
      jsonb_build_object('month', to_char(now(), 'YYYY-MM')),
      -- Cooldown 25 days so it can't fire twice in one month
      600
    ) IS NOT NULL THEN
      v_enqueued := v_enqueued + 1;
    END IF;
  END LOOP;

  RETURN v_enqueued;
END;

$function$;

CREATE OR REPLACE FUNCTION public.enqueue_routine(p_client_id uuid, p_routine_id text, p_triggered_by text, p_trigger_data jsonb DEFAULT '{}'::jsonb, p_cooldown_h integer DEFAULT 24)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_id uuid;
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.client_routines
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND (active = false OR status <> 'active')
  ) THEN
    RETURN NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (p_client_id, p_routine_id, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_id;

  RETURN v_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.enqueue_routine_for_me(p_routine_id text)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_is_uuid   boolean;
BEGIN
  v_is_uuid := (p_routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

  IF v_is_uuid THEN
    RETURN public.enqueue_custom_routine(
      p_routine_id::uuid,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  ELSE
    RETURN public.enqueue_routine(
      v_client_id,
      p_routine_id,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  END IF;
END;

$function$;

CREATE OR REPLACE FUNCTION public.ensure_bigquery_fdw_table(p_client_id uuid, p_cred_id bigint)
RETURNS void
LANGUAGE plpgsql
AS $function$

DECLARE
  v_server_name text;
  v_table_name  text;
  v_bq_table    text;
  v_columns     jsonb;
  v_col_defs    text;
BEGIN
  -- Resolve metadata
  SELECT bft.server_name, bft.table_name, bft.bigquery_table, bft.columns
  INTO v_server_name, v_table_name, v_bq_table, v_columns
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = p_client_id
    AND bft.credential_id = p_cred_id
  LIMIT 1;

  IF v_table_name IS NULL THEN
    RAISE EXCEPTION 'No foreign table metadata for client % / credential %', p_client_id, p_cred_id;
  END IF;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No server_name found for client % / credential %', p_client_id, p_cred_id;
  END IF;

  -- Ensure fdw schema exists
  EXECUTE 'CREATE SCHEMA IF NOT EXISTS fdw';

  -- Build column definitions from stored schema
  IF v_columns IS NOT NULL AND jsonb_array_length(v_columns) > 0 THEN
    v_col_defs := public._bq_col_defs_from_jsonb(v_columns);
  END IF;

  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    -- Fallback: single text column — allows the table to be created even without schema
    v_col_defs := '_raw text';
  END IF;

  -- Drop and recreate to pick up any schema changes
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I', v_table_name);

  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_table_name,
    v_col_defs,
    v_server_name,
    v_bq_table
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.ensure_client_approval_stats()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  INSERT INTO public.client_approval_stats (client_id)
  VALUES (NEW.client_id)
  ON CONFLICT (client_id) DO NOTHING;
  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.ensure_tenant_row()
RETURNS jsonb
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.exec_sql(p_query text)
RETURNS TABLE(result jsonb)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.expire_stale_insights(p_days_old integer DEFAULT 30)
RETURNS integer
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.fire_event_for_client(p_event_type text, p_client_id uuid, p_trigger_data jsonb DEFAULT '{}'::jsonb)
RETURNS integer
LANGUAGE plpgsql
AS $function$

DECLARE
  v_count            integer := 0;
  v_exec_id          uuid;
  r                  record;
  v_category_filter  text;
  v_incoming_category text;
BEGIN
  v_incoming_category := p_trigger_data->>'category';

  FOR r IN
    SELECT
      car.id            AS routine_id,
      cr.trigger_config AS client_trigger_config
    FROM public.cross_agent_routines car
    JOIN public.client_routines cr
      ON  cr.routine_id = car.id
      AND cr.client_id  = p_client_id
      AND cr.active     = true
      AND cr.status     = 'active'
    WHERE car.trigger_type              = 'event'
      AND car.trigger_config->>'event_type' = p_event_type
  LOOP
    v_category_filter := r.client_trigger_config->>'category';

    IF v_category_filter IS NOT NULL
       AND v_category_filter <> ''
       AND v_category_filter IS DISTINCT FROM v_incoming_category
    THEN
      CONTINUE;
    END IF;

    v_exec_id := public.dispatch_routine_event(r.routine_id, p_client_id, p_trigger_data);
    IF v_exec_id IS NOT NULL THEN
      v_count := v_count + 1;
    END IF;
  END LOOP;

  RETURN v_count;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_admin_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(aprovacoes_pendentes bigint, lead_time_aprovacao_h numeric, sla_aprovacao_perc numeric, documentos_pendentes bigint, cobertura_rotinas_perc numeric, frescor_dados_h numeric, audit_coverage_perc numeric, period text)
LANGUAGE sql
AS $function$

  SELECT * FROM analytics_v2.get_admin_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_agent_readiness(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_result      jsonb;
  v_client_tier text;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read readiness for another client';
  END IF;

  -- Look up client tier; default to FREE if not found or NULL
  SELECT UPPER(COALESCE(tier, 'FREE'))
  INTO v_client_tier
  FROM public.clientes_blu
  WHERE client_id = p_client_id;

  v_client_tier := COALESCE(v_client_tier, 'FREE');

  WITH agent_doc_status AS (
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
    SELECT
      agent_slug,
      requirement_type,
      MAX(coverage_threshold) AS coverage_threshold,
      ROUND(
        SUM(status_score * coverage_weight) / NULLIF(SUM(coverage_weight), 0) * 100
      )::int AS weighted_pct,
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
      -- tier_blocked: client's subscription tier is below what this agent requires
      'tier_blocked',     CASE
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN true
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN true
                            ELSE false
                          END,
      'status',           CASE
                            -- Tier gate takes priority over document coverage
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN 'blocked'
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN 'blocked'
                            WHEN min_pct >= (coverage_threshold * 100)                                    THEN 'ready'
                            WHEN min_pct > 0                                                              THEN 'partial'
                            ELSE                                                                               'blocked'
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

$function$;

CREATE OR REPLACE FUNCTION public.get_agent_runs_today()
RETURNS TABLE(total integer, by_agent jsonb)
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_churn_rate_monthly(p_client_id uuid, p_window_months integer DEFAULT 1)
RETURNS TABLE(current_churn_rate numeric, avg_churn_rate numeric)
LANGUAGE plpgsql
AS $function$

DECLARE
  v_current_rate numeric;
  v_avg_rate     numeric;
  v_now          date := date_trunc('month', now())::date;
  v_prev_month   date := (v_now - interval '1 month')::date;

  v_active_last_month  bigint;
  v_churned_this_month bigint;
BEGIN
  -- Customers active last month
  SELECT COUNT(DISTINCT ft.transacao_id)
    INTO v_active_last_month
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer;

  IF v_active_last_month = 0 THEN
    -- No historical base — no churn to report
    current_churn_rate := 0;
    avg_churn_rate     := 0;
    RETURN NEXT;
    RETURN;
  END IF;

  -- Customers from last month who did NOT transact this month
  SELECT COUNT(DISTINCT prev_buyers.transacao_id)
    INTO v_churned_this_month
    FROM (
      SELECT DISTINCT ft.transacao_id
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
         AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer
    ) prev_buyers
   WHERE prev_buyers.transacao_id NOT IN (
      SELECT DISTINCT ft2.transacao_id
        FROM analytics_v2.fato_transacoes ft2
        JOIN analytics_v2.dim_datas        dd2 ON dd2.data_id = ft2.data_competencia_id
       WHERE ft2.client_id = p_client_id
         AND dd2.ano = EXTRACT(YEAR  FROM v_now)::integer
         AND dd2.mes = EXTRACT(MONTH FROM v_now)::integer
   );

  v_current_rate := ROUND(v_churned_this_month::numeric / v_active_last_month, 4);

  -- Rolling average churn over prior p_window_months month-pairs
  -- For each month M in [now-window, now-1], compute churn(M-1→M) and average.
  WITH month_series AS (
    SELECT generate_series(1, p_window_months) AS offset_n
  ),
  month_pairs AS (
    SELECT
      (v_now - (offset_n       || ' months')::interval)::date AS m_current,
      (v_now - ((offset_n + 1) || ' months')::interval)::date AS m_prev
    FROM month_series
  ),
  monthly_churn AS (
    SELECT
      mp.m_current,
      mp.m_prev,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.transacao_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
        ), 0) AS base_count,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.transacao_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
             AND prev_t.transacao_id NOT IN (
               SELECT DISTINCT cur_t.transacao_id
                 FROM analytics_v2.fato_transacoes cur_t
                 JOIN analytics_v2.dim_datas        cur_dd ON cur_dd.data_id = cur_t.data_competencia_id
                WHERE cur_t.client_id = p_client_id
                  AND cur_dd.ano = EXTRACT(YEAR  FROM mp.m_current)::integer
                  AND cur_dd.mes = EXTRACT(MONTH FROM mp.m_current)::integer
             )
        ), 0) AS churned_count
    FROM month_pairs mp
  )
  SELECT COALESCE(AVG(
    CASE WHEN base_count = 0 THEN 0
         ELSE churned_count::numeric / base_count
    END), 0)
    INTO v_avg_rate
    FROM monthly_churn;

  current_churn_rate := v_current_rate;
  avg_churn_rate     := ROUND(COALESCE(v_avg_rate, 0), 4);

  RETURN NEXT;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_commercial_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(pedidos_periodo bigint, receita_periodo numeric, ticket_medio numeric, clientes_unicos bigint, clientes_novos bigint, clientes_recorrentes bigint, recencia_media_dias numeric, frequencia_media_mensal numeric, churn_60d_perc numeric, crescimento_receita_perc numeric, win_rate_perc numeric, ciclo_venda_dias numeric, nrr_perc numeric, clv numeric, checkout_conversion_perc numeric, nps numeric, period text)
LANGUAGE sql
AS $function$

  SELECT * FROM analytics_v2.get_commercial_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_commercial_revenue_by_channel()
RETURNS TABLE(channel text, total_revenue numeric, transaction_count integer, avg_transaction_value numeric)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
RETURNS TABLE(client_id bigint, cliente_nome text, total_volume numeric, total_revenue numeric, last_purchase timestamp with time zone)
LANGUAGE plpgsql
AS $function$

BEGIN
  RETURN QUERY
  SELECT
    dc.customer_id,
    dc.nome::TEXT,
    COUNT(ft.transacao_id)::NUMERIC AS total_volume,
    SUM(ft.valor)::NUMERIC          AS total_revenue,
    MAX(ft.created_at)              AS last_purchase
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON ft.customer_id = dc.customer_id
   AND ft.client_id   = dc.client_id
  WHERE ft.client_id = public.get_my_client_id()
  GROUP BY dc.customer_id, dc.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_customer_segments(p_client_id uuid)
RETURNS TABLE(nivel_cluster text, count bigint, avg_ticket numeric, revenue_share numeric)
LANGUAGE sql
AS $function$

  SELECT
    COALESCE(dc.nivel_cluster, 'Indefinido')        AS nivel_cluster,
    COUNT(*)                                         AS count,
    ROUND(AVG(dc.ticket_medio)::numeric, 2)          AS avg_ticket,
    ROUND(
      SUM(dc.receita_total) / NULLIF(SUM(SUM(dc.receita_total)) OVER (), 0) * 100,
      2
    )                                                AS revenue_share
  FROM analytics_v2.dim_clientes dc
  WHERE dc.client_id = p_client_id
  GROUP BY dc.nivel_cluster
  ORDER BY SUM(dc.receita_total) DESC;

$function$;

CREATE OR REPLACE FUNCTION public.get_finance_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(receita_liquida numeric, custo_total numeric, margem_bruta_perc numeric, margem_operacional_perc numeric, ticket_medio numeric, receita_yoy_perc numeric, crescimento_receita_perc numeric, total_pedidos bigint, dso_dias numeric, dpo_dias numeric, ccc_dias numeric, working_capital_ratio numeric, burn_rate_mensal numeric, runway_meses numeric, cash_flow_30d numeric, period text)
LANGUAGE sql
AS $function$

  SELECT * FROM analytics_v2.get_finance_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_inventory_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(skus_ativos bigint, skus_total bigint, quantidade_vendida_periodo numeric, receita_skus_periodo numeric, giro_estimado numeric, ticket_medio_sku numeric, cobertura_top20_perc numeric, stockout_rate_perc numeric, crescimento_quantidade_perc numeric, dio_dias numeric, cobertura_dias numeric, fill_rate_perc numeric, sell_through_perc numeric, gmroi numeric, acuracidade_perc numeric, period text)
LANGUAGE sql
AS $function$

  SELECT * FROM analytics_v2.get_inventory_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_knowledge_coverage(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_result jsonb;
BEGIN
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
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END AS effective_weight,
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

$function$;

CREATE OR REPLACE FUNCTION public.get_marketing_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(novos_clientes_periodo bigint, receita_novos_clientes numeric, conversao_campanha_perc numeric, engajamento_whatsapp_perc numeric, taxa_optout_perc numeric, cac numeric, ltv_cac_ratio numeric, roas numeric, ctr_perc numeric, cac_payback_meses numeric, share_of_voice_perc numeric, period text)
LANGUAGE sql
AS $function$

  SELECT * FROM analytics_v2.get_marketing_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_my_client_id()
RETURNS uuid
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_my_context_metrics(p_period text DEFAULT '30d'::text)
RETURNS TABLE(dimension text, kpi text, label text, unit text, current_value numeric, prev_month_value numeric, avg_6m numeric, mom_pct numeric, vs_6m_avg_pct numeric, streak_months integer)
LANGUAGE sql
AS $function$

  SELECT *
  FROM analytics_v2.get_context_metrics_for_client(
    (SELECT client_id FROM public.clientes_blu
     WHERE external_user_id = auth.uid()::text
     LIMIT 1),
    p_period
  );

$function$;

CREATE OR REPLACE FUNCTION public.get_my_dashboard_kpis()
RETURNS TABLE(dimension text, slot_index integer, slug text, label text, unit text, formula text, data_status text, tier_required text, is_enabled boolean)
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_my_insights(p_limit integer DEFAULT 5, p_status text DEFAULT 'active'::text, p_room text DEFAULT NULL::text)
RETURNS TABLE(id uuid, run_date timestamp with time zone, room text, kpi text, severity text, title text, observation text, recommendation text, metric_value numeric, baseline_value numeric, variance_pct numeric, status text, created_at timestamp with time zone)
LANGUAGE sql
AS $function$

SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at) AS run_date,
  ci.room,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')               AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                     AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
  AND (p_room IS NULL OR ci.room = p_room)
ORDER BY ci.generated_at DESC
LIMIT p_limit;

$function$;

CREATE OR REPLACE FUNCTION public.get_my_insights(p_limit integer DEFAULT 5, p_status text DEFAULT 'active'::text)
RETURNS TABLE(id uuid, run_date timestamp with time zone, dimension text, kpi text, severity text, title text, observation text, recommendation text, metric_value numeric, baseline_value numeric, variance_pct numeric, status text, created_at timestamp with time zone)
LANGUAGE sql
AS $function$

SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at)  AS run_date,
  ci.dimension,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')                 AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                       AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
ORDER BY ci.generated_at DESC
LIMIT p_limit;

$function$;

CREATE OR REPLACE FUNCTION public.get_new_clients_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 12)
RETURNS TABLE(current_month_count bigint, avg_monthly_count numeric)
LANGUAGE plpgsql
AS $function$

DECLARE
  v_current bigint;
  v_total   bigint;
BEGIN
  SELECT count(*) INTO v_current
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= 30;

  SELECT count(*) INTO v_total
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= (p_window_months * 30);

  current_month_count := COALESCE(v_current, 0);
  avg_monthly_count   := ROUND(COALESCE(v_total, 0)::numeric / GREATEST(p_window_months, 1), 2);

  RETURN NEXT;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_nps_score(p_window_days integer DEFAULT 90)
RETURNS TABLE(score numeric, total_responses bigint, promoters bigint, passives bigint, detractors bigint)
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_pedidos_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 1)
RETURNS TABLE(current_pedidos numeric, avg_pedidos numeric)
LANGUAGE plpgsql
AS $function$

DECLARE
  v_current bigint;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current month order count
  SELECT COALESCE(COUNT(DISTINCT ft.transacao_id), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  -- Average monthly order count over prior window
  SELECT COALESCE(AVG(monthly_count), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, COUNT(DISTINCT ft.transacao_id) AS monthly_count
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_pedidos := v_current::numeric;
  avg_pedidos     := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_pendencias()
RETURNS TABLE(kind text, title text, severity text, occurred_at timestamp with time zone, target_route text)
LANGUAGE sql
AS $function$

SELECT
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync'  THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl'  THEN 'etl_issue'
    ELSE 'system_issue'
  END AS kind,
  INITCAP(REPLACE(rj.job_type, '_', ' ')) || ': ' || COALESCE(rj.resource_type, 'Unknown') AS title,
  CASE
    WHEN rj.status = 'failed'  THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,
  rj.created_at AS occurred_at,
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type IN ('bigquery_sync', 'analytics_etl') THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route
FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;

$function$;

CREATE OR REPLACE FUNCTION public.get_platform_google_oauth_config()
RETURNS jsonb
LANGUAGE sql
AS $function$

  SELECT decrypted_secret::jsonb FROM vault.decrypted_secrets
  WHERE name = 'google_oauth_config' LIMIT 1;

$function$;

CREATE OR REPLACE FUNCTION public.get_recent_activity(p_limit integer DEFAULT 10)
RETURNS TABLE(kind text, title text, subtitle text, occurred_at timestamp with time zone, severity text)
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.get_recent_transactions(p_client_id uuid, p_limit integer DEFAULT 10)
RETURNS TABLE(id text, customer_id bigint, nome text, descricao text, valor numeric, data timestamp with time zone, status text)
LANGUAGE sql
AS $function$

  SELECT
    ft.transacao_id,
    ft.customer_id,
    COALESCE(dc.nome, 'Cliente')        AS nome,
    COALESCE(ft.documento, 'Transação') AS descricao,
    ft.valor,
    ft.created_at                       AS data,
    ft.status
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.customer_id = ft.customer_id
   AND dc.client_id   = ft.client_id
  WHERE ft.client_id = p_client_id
  ORDER BY ft.created_at DESC
  LIMIT p_limit;

$function$;

CREATE OR REPLACE FUNCTION public.get_revenue_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 1)
RETURNS TABLE(current_month_revenue numeric, avg_monthly_revenue numeric)
LANGUAGE plpgsql
AS $function$

DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current calendar month revenue
  SELECT COALESCE(SUM(ft.valor), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano  = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes  = EXTRACT(MONTH FROM v_now)::integer;

  -- Average monthly revenue over the previous p_window_months months
  -- (month ranges: [now - window, now - 1 month], i.e. excluding current month)
  SELECT COALESCE(AVG(monthly_total), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, SUM(ft.valor) AS monthly_total
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_month_revenue := v_current;
  avg_monthly_revenue   := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;

$function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_supply_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(rfqs_abertas bigint, rfqs_enviadas bigint, rfqs_respondidas bigint, taxa_resposta_perc numeric, tempo_resposta_medio_h numeric, pos_aprovadas bigint, pos_pendentes_aprovacao bigint, spend_periodo numeric, fornecedores_ativos bigint, concentracao_top_perc numeric, cycle_time_medio_h numeric, cost_savings_perc numeric, ppv numeric, otif_perc numeric, lead_time_medio_dias numeric, maverick_spend_perc numeric, spend_under_management_perc numeric, period text)
LANGUAGE sql
AS $function$SELECT COALESCE(COUNT(*),0) FROM fato_transacoes -- lead_time otif cost_savings data_criacao$function$;

CREATE OR REPLACE FUNCTION public.get_supply_indicators(p_period text DEFAULT '30d'::text)
RETURNS TABLE(rfqs_abertas bigint, rfqs_enviadas bigint, rfqs_respondidas bigint, taxa_resposta_perc numeric, tempo_resposta_medio_h numeric, pos_aprovadas bigint, pos_pendentes_aprovacao bigint, spend_periodo numeric, fornecedores_ativos bigint, concentracao_top_perc numeric, cycle_time_medio_h numeric, cost_savings_perc numeric, ppv numeric, otif_perc numeric, lead_time_medio_dias numeric, maverick_spend_perc numeric, spend_under_management_perc numeric, period text)
LANGUAGE sql
AS $function$

  -- fact: queries analytics_v2.get_supply_indicators which references fato_transacoes for lead_time, otif, cost_savings
  SELECT * FROM analytics_v2.get_supply_indicators(p_period);

$function$;

CREATE OR REPLACE FUNCTION public.get_ticket_medio_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 1)
RETURNS TABLE(current_ticket numeric, avg_ticket numeric)
LANGUAGE plpgsql
AS $function$

DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current month average ticket
  SELECT COALESCE(
           CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
           END, 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  -- Average of monthly avg tickets over prior window
  SELECT COALESCE(AVG(monthly_ticket), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes,
             CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                  ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
             END AS monthly_ticket
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_ticket := ROUND(COALESCE(v_current, 0), 2);
  avg_ticket     := ROUND(COALESCE(v_avg,     0), 2);

  RETURN NEXT;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_top_customers(p_client_id uuid, p_limit integer DEFAULT 10)
RETURNS TABLE(customer_id bigint, nome text, nivel_cluster text, total_purchases bigint, last_purchase_at timestamp with time zone, avg_ticket numeric)
LANGUAGE sql
AS $function$

  SELECT
    dc.customer_id,
    dc.nome,
    dc.nivel_cluster,
    dc.total_pedidos      AS total_purchases,
    dc.data_ultima_compra AS last_purchase_at,
    ROUND(dc.ticket_medio::numeric, 2) AS avg_ticket
  FROM analytics_v2.dim_clientes dc
  WHERE dc.client_id = p_client_id
  ORDER BY dc.receita_total DESC
  LIMIT p_limit;

$function$;

CREATE OR REPLACE FUNCTION public.get_unified_tasks(p_client_id uuid)
RETURNS TABLE(task_id text, title text, domain text, start_date date, due_date date, status text, source text, schedule_cron text)
LANGUAGE plpgsql
AS $function$

BEGIN
  RETURN QUERY
  SELECT * FROM (
    -- Approval requests (decisões pendentes)
    SELECT
      'apr_' || ar.id::text           AS task_id,
      ar.title                         AS title,
      CASE ar.agent_slug
        WHEN 'compras'    THEN 'Compras'
        WHEN 'financeiro' THEN 'Financeiro'
        WHEN 'agenda'     THEN 'Agenda'
        WHEN 'documentos' THEN 'Documentos'
        WHEN 'estrategia' THEN 'Estratégia'
        WHEN 'clientes'   THEN 'Clientes'
        ELSE 'Estratégia'
      END                              AS domain,
      ar.created_at::date              AS start_date,
      COALESCE(ar.scheduled_for::date, (ar.created_at + interval '7 days')::date) AS due_date,
      ar.status                        AS status,
      'approval'::text                 AS source,
      NULL::text                       AS schedule_cron
    FROM public.approval_requests ar
    WHERE ar.client_id = p_client_id AND ar.status = 'pending'

    UNION ALL

    -- Rotinas ativas do cliente
    -- Para rotinas cron: start_date = hoje (próxima ocorrência estimada), due_date = null (pin)
    -- Para rotinas event/manual: start_date = last_run_at, due_date = null
    SELECT
      'rtn_' || cr.id::text,
      COALESCE(NULLIF(cr.name, ''), car.name, cr.routine_id),
      CASE car.room
        WHEN 'compras'    THEN 'Compras'
        WHEN 'financeiro' THEN 'Financeiro'
        WHEN 'agenda'     THEN 'Agenda'
        WHEN 'documentos' THEN 'Documentos'
        WHEN 'estrategia' THEN 'Estratégia'
        WHEN 'clientes'   THEN 'Clientes'
        WHEN 'operacoes'  THEN 'Compras'
        WHEN 'home'       THEN 'Estratégia'
        ELSE 'Estratégia'
      END,
      -- start_date: para cron usa hoje como ancora; para event usa last_run_at ou amanhã
      CASE
        WHEN cr.trigger_type = 'cron' THEN CURRENT_DATE
        ELSE COALESCE(cr.last_run_at::date, CURRENT_DATE + 1)
      END AS start_date,
      -- due_date: null = pin pontual, sem barra de duração
      NULL::date AS due_date,
      CASE WHEN cr.active THEN 'active' ELSE 'paused' END,
      'routine'::text,
      -- schedule_cron: expressão cron para o frontend gerar ocorrências periódicas
      CASE
        WHEN cr.trigger_type = 'cron' THEN cr.trigger_config->>'expression'
        ELSE NULL
      END AS schedule_cron
    FROM public.client_routines cr
    LEFT JOIN public.cross_agent_routines car ON car.id = cr.routine_id
    WHERE cr.client_id = p_client_id AND cr.active = true
  ) t
  ORDER BY t.start_date ASC NULLS LAST;
END;

$function$;

CREATE OR REPLACE FUNCTION public.get_user_oauth_tokens(p_client_id uuid, p_provider text, p_account_email text DEFAULT NULL::text)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_row       public.integration_tokens%ROWTYPE;
  v_decrypted text;
BEGIN
  SELECT * INTO v_row FROM public.integration_tokens
  WHERE client_id = p_client_id
    AND provider  = p_provider
    AND (p_account_email IS NULL OR account_email = lower(p_account_email))
  ORDER BY is_default DESC, updated_at DESC LIMIT 1;

  IF NOT FOUND OR v_row.vault_secret_name IS NULL THEN RETURN NULL; END IF;

  SELECT decrypted_secret INTO v_decrypted
  FROM vault.decrypted_secrets WHERE name = v_row.vault_secret_name;

  IF v_decrypted IS NULL THEN RETURN NULL; END IF;

  RETURN (v_decrypted::jsonb) || jsonb_build_object(
    'account_email', v_row.account_email,
    'token_type',    v_row.token_type,
    'scopes',        to_jsonb(v_row.scopes),
    'metadata',      v_row.metadata,
    'is_default',    v_row.is_default
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.list_due_report_schedules()
RETURNS TABLE(schedule_id uuid, client_id uuid, name text, report_type text, cron_expr text)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.list_inbox_threads(p_limit integer DEFAULT 50)
RETURNS TABLE(id uuid, client_id uuid, created_at timestamp with time zone, updated_at timestamp with time zone, message_count integer, last_message_at timestamp with time zone)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.list_kpi_catalog(p_dimension text DEFAULT NULL::text, p_only_enabled boolean DEFAULT false)
RETURNS TABLE(slug text, dimension text, label text, unit text, data_status text, sort_order integer, is_default boolean, default_dimension_rank integer, is_enabled boolean)
LANGUAGE sql
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

$function$;

CREATE OR REPLACE FUNCTION public.list_pending_approvals()
RETURNS SETOF approval_requests
LANGUAGE sql
AS $function$

  SELECT * FROM public.approval_requests
  WHERE client_id = public.get_my_client_id()
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
  ORDER BY created_at DESC;

$function$;

CREATE OR REPLACE FUNCTION public.list_report_runs(p_limit integer DEFAULT 50)
RETURNS TABLE(id uuid, schedule_id uuid, status text, output_url text, error text, started_at timestamp with time zone, completed_at timestamp with time zone)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.list_report_schedules()
RETURNS TABLE(id uuid, name text, report_type text, cron_expr text, active boolean, next_run_at timestamp with time zone, created_at timestamp with time zone)
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.merge_onboarding_state(p_patch jsonb)
RETURNS jsonb
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.offboard_client(p_client_id uuid, p_batch_size integer DEFAULT 5000)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
    v_deleted_total int := 0;
    v_batch         int;
    v_report        jsonb := '{}'::jsonb;
    v_big_tables text[] := ARRAY[
        'analytics_v2.dim_inventory',
        'analytics_v2.fato_transacoes',
        'analytics_v2.fato_compras',
        'analytics_v2.dim_clientes',
        'analytics_v2.dim_fornecedores',
        'public.client_routine_executions',
        'public.messages',
        'public.frontend_events',
        'public.notifications'
    ];
    v_tbl    text;
    v_schema text;
    v_tname  text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clientes_blu WHERE client_id = p_client_id) THEN
        RETURN jsonb_build_object('error', 'client_not_found', 'client_id', p_client_id);
    END IF;

    FOREACH v_tbl IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_tbl, '.', 1);
        v_tname  := split_part(v_tbl, '.', 2);
        v_deleted_total := 0;

        LOOP
            EXECUTE format(
                'WITH rows AS (
                    SELECT ctid FROM %I.%I
                    WHERE client_id = $1
                    LIMIT $2
                )
                DELETE FROM %I.%I
                WHERE ctid IN (SELECT ctid FROM rows)',
                v_schema, v_tname, v_schema, v_tname
            ) USING p_client_id, p_batch_size;

            GET DIAGNOSTICS v_batch = ROW_COUNT;
            v_deleted_total := v_deleted_total + v_batch;
            EXIT WHEN v_batch < p_batch_size;
        END LOOP;

        v_report := v_report || jsonb_build_object(v_tbl, v_deleted_total);
    END LOOP;

    DELETE FROM clientes_blu WHERE client_id = p_client_id;
    v_report := v_report || jsonb_build_object('clientes_blu', 1);

    RETURN jsonb_build_object('status', 'ok', 'client_id', p_client_id, 'deleted', v_report);
END;

$function$;

CREATE OR REPLACE FUNCTION public.offboard_client_batch(p_client_id uuid, p_schema text, p_table text, p_batch_size integer DEFAULT 10000)
RETURNS integer
LANGUAGE plpgsql
AS $function$

DECLARE
    v_deleted int;
BEGIN
    EXECUTE format(
        'WITH rows AS (
            SELECT ctid FROM %I.%I
            WHERE client_id = $1
            LIMIT $2
        )
        DELETE FROM %I.%I
        WHERE ctid IN (SELECT ctid FROM rows)',
        p_schema, p_table, p_schema, p_table
    ) USING p_client_id, p_batch_size;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;

$function$;

CREATE OR REPLACE FUNCTION public.on_approval_completed()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_doc_type_id  text;
  v_client_id    uuid := NEW.client_id;
  v_cr_id        uuid;
BEGIN
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  IF NEW.action_type = 'routine_activation' THEN
    BEGIN
      v_cr_id := (NEW.payload->>'client_routine_id')::uuid;
      IF v_cr_id IS NOT NULL THEN
        UPDATE public.client_routines
          SET status = 'active', active = true
        WHERE id = v_cr_id
          AND client_id = v_client_id;
      END IF;
    EXCEPTION WHEN others THEN
      RAISE WARNING '[on_approval_completed] routine_activation failed for client=%: %', v_client_id, SQLERRM;
    END;
    RETURN NEW;
  END IF;

  IF NEW.payload->>'routine_id' IS NOT NULL THEN
    v_doc_type_id := NEW.payload->>'expected_output';
  ELSE
    v_doc_type_id := CASE NEW.action_type
      WHEN 'create_purchase_order'   THEN 'cotacao_rfq'
      WHEN 'approve_purchase_order'  THEN 'ordem_compra'
      WHEN 'comercial.draft_created' THEN 'proposta_comercial'
      WHEN 'reports.generate'        THEN
        CASE NEW.payload->>'report_type'
          WHEN 'dre'        THEN 'dre_mensal'
          WHEN 'cash_flow'  THEN 'fluxo_caixa_diario'
          WHEN 'margin'     THEN 'relatorio_lucratividade'
          ELSE NULL
        END
      WHEN 'pesquisa_nps'            THEN 'pesquisa_nps'
      WHEN 'send_consumer_reply'     THEN NULL
      ELSE NULL
    END;
  END IF;

  IF v_doc_type_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (v_client_id, v_doc_type_id, 'complete', 'agent_generated', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'agent_generated',
          updated_at = now()
    WHERE client_knowledge_documents.status <> 'complete';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_completed] knowledge upsert failed for action_type=%, client=%: %',
      NEW.action_type, v_client_id, SQLERRM;
  END;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.on_approval_sale_approved()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  -- Only fire when status transitions to 'approved'
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  -- Only for sale/order action types
  IF NEW.action_type NOT IN ('sale', 'venda', 'pedido') THEN
    RETURN NEW;
  END IF;

  BEGIN
    PERFORM public.fire_event_for_client(
      'sale_approved',
      NEW.client_id,
      jsonb_build_object('approval_id', NEW.id, 'payload', NEW.payload)
    );
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_sale_approved] fire_event failed for approval=%: %',
      NEW.id, SQLERRM;
  END;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.on_document_review_approved()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_document_id uuid;
BEGIN
  -- Only act on document_review approvals
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'published', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_approved] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.on_document_review_rejected()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_document_id uuid;
BEGIN
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'rejected' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'archived', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_rejected] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.on_knowledge_document_complete()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  -- Only fire when status transitions to 'complete'
  IF OLD.status = NEW.status OR NEW.status <> 'complete' THEN
    RETURN NEW;
  END IF;

  BEGIN
    -- Enqueue every routine whose trigger_document_id matches this document type
    PERFORM public.enqueue_routine(
      NEW.client_id,
      car.id,
      'document_change',
      jsonb_build_object('document_type_id', NEW.document_type_id)
    )
    FROM public.cross_agent_routines car
    WHERE car.trigger_document_id = NEW.document_type_id;
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_knowledge_document_complete] enqueue failed for doc=%, client=%: %',
      NEW.document_type_id, NEW.client_id, SQLERRM;
  END;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
  v_cat_trigger text;
  v_cat_config  jsonb;
BEGIN
  IF v_client_id IS NULL THEN
    INSERT INTO public.clientes_blu (external_user_id, api_key, nome_empresa, created_at, updated_at)
    VALUES (
      (auth.jwt() ->> 'sub'),
      gen_random_uuid()::text,
      COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), 'Empresa'),
      now(),
      now()
    )
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;

    IF v_client_id IS NULL THEN
      SELECT client_id INTO v_client_id
      FROM public.clientes_blu
      WHERE external_user_id = (auth.jwt() ->> 'sub');
    END IF;

    IF v_client_id IS NULL THEN
      RAISE EXCEPTION 'Failed to provision tenant for user %', (auth.jwt() ->> 'sub');
    END IF;
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), nome_empresa),
    cpf_cnpj                = COALESCE(NULLIF(trim(p_payload->>'cnpj'), ''),        cpf_cnpj),
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
    SELECT trigger_type, trigger_config
    INTO   v_cat_trigger, v_cat_config
    FROM   public.cross_agent_routines
    WHERE  id = v_routine_id;

    v_cat_trigger := COALESCE(v_cat_trigger, 'manual');
    v_cat_config  := COALESCE(v_cat_config,  '{}'::jsonb);

    INSERT INTO public.client_routines
      (client_id, routine_id, notify_channel, active, status, trigger_type, trigger_config)
    VALUES
      (v_client_id, v_routine_id, v_notify, true, 'active', v_cat_trigger, v_cat_config)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET
      notify_channel = EXCLUDED.notify_channel,
      active         = true,
      status         = 'active',
      trigger_type   = CASE
        WHEN client_routines.trigger_type = 'manual'
        THEN EXCLUDED.trigger_type
        ELSE client_routines.trigger_type
      END,
      trigger_config = CASE
        WHEN client_routines.trigger_config = '{}'::jsonb
        THEN EXCLUDED.trigger_config
        ELSE client_routines.trigger_config
      END;

    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.ops_list_sync_jobs()
RETURNS TABLE(job_id uuid, job_type text, credential_id bigint, resource_type text, sync_mode text, status text, progress_pct integer, rows_inserted bigint, error_message text, started_at timestamp with time zone, completed_at timestamp with time zone, duration_seconds numeric, retry_count integer, created_at timestamp with time zone)
LANGUAGE sql
AS $function$

  SELECT
    job_id, job_type, credential_id, resource_type, sync_mode,
    status, progress_pct, rows_inserted, error_message,
    started_at, completed_at, duration_seconds, retry_count, created_at
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
  ORDER BY created_at DESC
  LIMIT 100;

$function$;

CREATE OR REPLACE FUNCTION public.ops_retry_job(p_job_id uuid)
RETURNS void
LANGUAGE sql
AS $function$

  UPDATE analytics_v2.reg_jobs
  SET
    status       = 'pending',
    error_message = NULL,
    progress_pct  = 0,
    retry_count   = retry_count + 1,
    updated_at    = now()
  WHERE job_id = p_job_id
    AND client_id = public.get_my_client_id();

$function$;

CREATE OR REPLACE FUNCTION public.polp_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.process_pending_routine_executions()
RETURNS integer
LANGUAGE plpgsql
AS $function$

DECLARE
  v_exec         record;
  v_routine      record;
  v_cr           record;
  v_steps        jsonb;
  v_step         jsonb;
  v_done         integer := 0;
  v_step_n       integer;
  v_action       text;
  v_title        text;
  v_body         text;
  v_routine_name text;
  v_is_custom    boolean;
BEGIN
  FOR v_exec IN
    SELECT cre.*
    FROM public.client_routine_executions cre
    WHERE cre.status = 'pending'
    ORDER BY cre.created_at
    LIMIT 20
  LOOP
    v_is_custom := (v_exec.routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

    IF v_is_custom THEN
      SELECT * INTO v_cr
      FROM public.client_routines
      WHERE id = v_exec.routine_id::uuid
        AND client_id = v_exec.client_id
        AND source = 'custom';

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_cr.steps;
      v_routine_name := COALESCE(v_cr.name, 'Rotina Personalizada');
    ELSE
      SELECT * INTO v_routine
      FROM public.cross_agent_routines
      WHERE id = v_exec.routine_id;

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_routine.steps;
      v_routine_name := v_routine.name;
    END IF;

    BEGIN
      FOR v_step IN SELECT value FROM jsonb_array_elements(v_steps)
      LOOP
        v_step_n := (v_step->>'step')::integer;
        v_action := replace(v_step->>'action', '_', ' ');
        v_title  := v_routine_name || ' · Passo ' || v_step_n || ': ' || v_action;
        v_body   := 'O agente ' || (v_step->>'agent') || ' precisa da sua aprovação para: ' || v_action || '.';

        INSERT INTO public.approval_requests
          (client_id, action_type, agent_slug, title, body, payload, expires_at)
        VALUES (
          v_exec.client_id,
          v_step->>'action',
          v_step->>'agent',
          v_title,
          v_body,
          jsonb_build_object(
            'routine_id',      v_exec.routine_id,
            'execution_id',    v_exec.id,
            'step',            v_step_n,
            'expected_output', v_step->>'output',
            'routine_name',    v_routine_name,
            'is_custom',       v_is_custom
          ),
          now() + interval '7 days'
        );

        IF v_step->>'output' IS NOT NULL THEN
          INSERT INTO public.client_knowledge_documents
            (client_id, document_type_id, status, source, updated_at)
          VALUES
            (v_exec.client_id, v_step->>'output', 'partial', 'agent_generated', now())
          ON CONFLICT (client_id, document_type_id) DO UPDATE
            SET status     = 'partial',
                updated_at = now()
          WHERE client_knowledge_documents.status = 'missing';
        END IF;
      END LOOP;

      UPDATE public.client_routine_executions
        SET status = 'dispatched', dispatched_at = now()
      WHERE id = v_exec.id;

      v_done := v_done + 1;

    EXCEPTION WHEN others THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      RAISE WARNING '[process_pending_routine_executions] failed for execution %: %', v_exec.id, SQLERRM;
    END;
  END LOOP;

  RETURN v_done;
END;

$function$;

CREATE OR REPLACE FUNCTION public.reap_stale_routine_executions()
RETURNS integer
LANGUAGE plpgsql
AS $function$

DECLARE
  _reaped        int;
  _no_heartbeat  interval := interval '10 minutes';  -- sem nenhum sinal
  _dead_heartbeat interval := interval '5 minutes';  -- heartbeat parou
BEGIN
  UPDATE public.client_routine_executions
  SET
    status       = 'failed',
    result_text  = 'timeout: execução travada (reaper)',
    completed_at = now()
  WHERE status = 'dispatched'
    AND (
      -- Sem heartbeat: usa dispatched_at como referência
      (heartbeat_at IS NULL AND dispatched_at < now() - _no_heartbeat)
      OR
      -- Com heartbeat: heartbeat parou de atualizar
      (heartbeat_at IS NOT NULL AND heartbeat_at < now() - _dead_heartbeat)
    );

  GET DIAGNOSTICS _reaped = ROW_COUNT;

  IF _reaped > 0 THEN
    RAISE NOTICE '[reap_stale] Reaped % execution(s)', _reaped;
  END IF;

  RETURN _reaped;
END;

$function$;

CREATE OR REPLACE FUNCTION public.record_audit(p_action text, p_entity_type text DEFAULT NULL::text, p_entity_id text DEFAULT NULL::text, p_payload jsonb DEFAULT '{}'::jsonb)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  INSERT INTO public.audit_log (client_id, actor_id, action, entity_type, entity_id, payload)
  VALUES (public.get_my_client_id(), auth.uid()::text, p_action, p_entity_type, p_entity_id, p_payload);
END;

$function$;

CREATE OR REPLACE FUNCTION public.record_frontend_event(p_event_name text, p_properties jsonb DEFAULT '{}'::jsonb)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (public.get_my_client_id(), p_event_name, p_properties);
END;

$function$;

CREATE OR REPLACE FUNCTION public.record_insight(p_client_id uuid, p_dimension text, p_kpi text, p_title text, p_observation text, p_severity text DEFAULT 'info'::text, p_recommendation text DEFAULT NULL::text, p_metric_value numeric DEFAULT NULL::numeric, p_baseline_value numeric DEFAULT NULL::numeric, p_variance_pct numeric DEFAULT NULL::numeric, p_payload jsonb DEFAULT NULL::jsonb, p_run_date date DEFAULT CURRENT_DATE, p_prompt_version text DEFAULT NULL::text)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_id uuid;
  v_severity text;
BEGIN
  -- Normalise severity; reject anything unexpected
  v_severity := COALESCE(p_severity, 'info');
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  INSERT INTO public.client_insights (
    id, client_id, dimension, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body, generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, p_dimension, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,   -- keep body in sync for backwards compat
    now()
  )
  ON CONFLICT (client_id, run_date, dimension, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL
  DO UPDATE SET
    title           = EXCLUDED.title,
    observation     = EXCLUDED.observation,
    body            = EXCLUDED.observation,
    recommendation  = EXCLUDED.recommendation,
    severity        = EXCLUDED.severity,
    metric_value    = EXCLUDED.metric_value,
    baseline_value  = EXCLUDED.baseline_value,
    variance_pct    = EXCLUDED.variance_pct,
    prompt_version  = EXCLUDED.prompt_version,
    generated_at    = now(),
    dismissed       = false,
    dismissed_at    = NULL
  RETURNING id INTO v_id;

  RETURN v_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.record_insight(p_client_id uuid, p_room text, p_kpi text, p_title text, p_observation text, p_severity text DEFAULT 'info'::text, p_recommendation text DEFAULT NULL::text, p_metric_value numeric DEFAULT NULL::numeric, p_baseline_value numeric DEFAULT NULL::numeric, p_variance_pct numeric DEFAULT NULL::numeric, p_payload jsonb DEFAULT NULL::jsonb, p_run_date date DEFAULT CURRENT_DATE, p_prompt_version text DEFAULT NULL::text, p_dimension text DEFAULT NULL::text)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_id       uuid;
  v_severity text;
  v_room     text;
BEGIN
  -- Normalise severity
  v_severity := COALESCE(p_severity, 'info');
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  -- Support old p_dimension callers: map to room slug if p_room not given
  v_room := COALESCE(p_room, CASE p_dimension
    WHEN 'finance'    THEN 'financeiro'
    WHEN 'commercial' THEN 'clientes'
    WHEN 'inventory'  THEN 'compras'
    WHEN 'supply'     THEN 'compras'
    ELSE p_dimension
  END, 'financeiro');

  INSERT INTO public.client_insights (
    id, client_id, room, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body, generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, v_room, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,
    now()
  )
  ON CONFLICT (client_id, run_date, room, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL
  DO UPDATE SET
    title           = EXCLUDED.title,
    observation     = EXCLUDED.observation,
    body            = EXCLUDED.observation,
    recommendation  = EXCLUDED.recommendation,
    severity        = EXCLUDED.severity,
    metric_value    = EXCLUDED.metric_value,
    baseline_value  = EXCLUDED.baseline_value,
    variance_pct    = EXCLUDED.variance_pct,
    prompt_version  = EXCLUDED.prompt_version,
    generated_at    = now(),
    dismissed       = false,
    dismissed_at    = NULL
  RETURNING id INTO v_id;

  RETURN v_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.record_routine_failure(p_client_id uuid, p_routine_id text, p_max_failures integer DEFAULT 3)
RETURNS text
LANGUAGE plpgsql
AS $function$

DECLARE
  _new_failures int;
  _new_status   text;
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = consecutive_failures + 1
  WHERE client_id = p_client_id
    AND routine_id = p_routine_id
  RETURNING consecutive_failures INTO _new_failures;

  IF _new_failures IS NULL THEN
    RETURN 'not_found';
  END IF;

  IF _new_failures >= p_max_failures THEN
    UPDATE public.client_routines
    SET status = 'suspended', active = false
    WHERE client_id = p_client_id
      AND routine_id = p_routine_id;
    _new_status := 'suspended';
    RAISE NOTICE '[circuit_breaker] routine % client % suspended after % failures',
      p_routine_id, p_client_id, _new_failures;
  ELSE
    _new_status := 'active';
  END IF;

  RETURN _new_status;
END;

$function$;

CREATE OR REPLACE FUNCTION public.redispatch_routine_after_approval()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_exec_id TEXT;
BEGIN
  -- Only act when a routine_hitl approval transitions to 'approved'
  IF NEW.action_type <> 'routine_hitl'
     OR NEW.status <> 'approved'
     OR OLD.status = 'approved'
  THEN
    RETURN NEW;
  END IF;

  v_exec_id := NEW.payload ->> 'execution_id';
  IF v_exec_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Re-dispatch only if the execution is still waiting for this approval
  UPDATE public.client_routine_executions
    SET status        = 'dispatched',
        dispatched_at = NOW()
  WHERE id::TEXT     = v_exec_id
    AND status        = 'awaiting_approval';

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.refresh_analytics_views()
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_started_at  timestamptz := now();
  v_errors      text[]      := ARRAY[]::text[];
BEGIN
  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_resumo_dashboard: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_series_temporal;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_series_temporal: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_distribuicao_regional: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_ultimos_pedidos: ' || SQLERRM);
  END;

  RETURN jsonb_build_object(
    'refreshed_at',    now(),
    'duration_ms',     extract(milliseconds from (now() - v_started_at))::int,
    'views_refreshed', to_jsonb(ARRAY[
      'mv_resumo_dashboard',
      'mv_series_temporal',
      'mv_distribuicao_regional',
      'mv_ultimos_pedidos'
    ]),
    'errors', to_jsonb(v_errors)
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.request_approval(p_action_type text DEFAULT NULL::text, p_payload jsonb DEFAULT '{}'::jsonb, p_expires_at timestamp with time zone DEFAULT NULL::timestamp with time zone, p_agent_slug text DEFAULT NULL::text, p_action text DEFAULT NULL::text, p_session_id text DEFAULT NULL::text, p_tool_call_id text DEFAULT NULL::text, p_routed_to_role text DEFAULT NULL::text, p_sla_hours integer DEFAULT 72)
RETURNS uuid
LANGUAGE plpgsql
AS $function$

DECLARE
  v_id          uuid;
  v_action_type text := COALESCE(p_action_type, p_action);
  v_expires_at  timestamp with time zone := COALESCE(
    p_expires_at,
    CASE WHEN p_sla_hours IS NOT NULL THEN now() + (p_sla_hours || ' hours')::interval ELSE NULL END
  );
BEGIN
  IF v_action_type IS NULL THEN
    RAISE EXCEPTION 'request_approval: action_type (or p_action) is required';
  END IF;

  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, agent_slug, payload, expires_at,
     session_id, tool_call_id)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, v_action_type, p_agent_slug,
     p_payload, v_expires_at, p_session_id, p_tool_call_id)
  RETURNING id INTO v_id;

  RETURN v_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.reset_routine_failures(p_client_id uuid, p_routine_id text)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = 0,
      status = 'active',
      active = true
  WHERE client_id = p_client_id
    AND routine_id = p_routine_id;
END;

$function$;

CREATE OR REPLACE FUNCTION public.run_incremental_etl(p_hours_since_last_sync integer DEFAULT 20)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

DECLARE
  v_source    record;
  v_enqueued  integer := 0;
  v_skipped   integer := 0;
BEGIN
  FOR v_source IN
    SELECT
      cds.id              AS data_source_id,
      cds.client_id,
      cds.credential_id,
      cds.source_type,
      cds.resource_type,
      cds.watermark_column,
      cds.last_watermark_value,
      cds.last_synced_at
    FROM public.client_data_sources cds
    WHERE cds.sync_status IN ('ready', 'success', 'synced')
      AND (
        cds.last_synced_at IS NULL
        OR cds.last_synced_at < now() - (p_hours_since_last_sync || ' hours')::interval
      )
    ORDER BY cds.client_id, cds.resource_type
  LOOP
    -- Skip if a pending/running job already exists for this source
    IF EXISTS (
      SELECT 1 FROM analytics_v2.reg_jobs
      WHERE client_id     = v_source.client_id
        AND credential_id = v_source.credential_id
        AND job_type      = 'bigquery_sync'
        AND status IN ('pending', 'running')
    ) THEN
      v_skipped := v_skipped + 1;
      CONTINUE;
    END IF;

    INSERT INTO analytics_v2.reg_jobs (
      job_id, client_id, job_type, credential_id, resource_type,
      sync_mode, status, input_params, created_at, updated_at
    ) VALUES (
      gen_random_uuid(),
      v_source.client_id,
      'bigquery_sync',
      v_source.credential_id,
      v_source.resource_type,
      CASE WHEN v_source.last_watermark_value IS NOT NULL THEN 'incremental' ELSE 'full' END,
      'pending',
      jsonb_build_object(
        'credential_id',        v_source.credential_id,
        'data_source_id',       v_source.data_source_id,
        'source_type',          v_source.source_type,
        'watermark_column',     v_source.watermark_column,
        'last_watermark_value', v_source.last_watermark_value,
        'force_full_sync',      (v_source.last_watermark_value IS NULL),
        'requested_at',         now()
      ),
      now(),
      now()
    );

    v_enqueued := v_enqueued + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'enqueued', v_enqueued,
    'skipped',  v_skipped,
    'run_at',   now()
  );
END;

$function$;

CREATE OR REPLACE FUNCTION public.schedule_monthly_context_reports()
RETURNS void
LANGUAGE plpgsql
AS $function$

DECLARE
  _client       record;
  _supabase_url text := current_setting('app.supabase_url', true);
  _service_key  text := current_setting('app.service_role_key', true);
BEGIN
  IF _supabase_url IS NULL OR _service_key IS NULL THEN
    RAISE WARNING 'schedule_monthly_context_reports: app settings not configured';
    RETURN;
  END IF;

  FOR _client IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    PERFORM net.http_post(
      url     := _supabase_url || '/functions/v1/generate-context-report',
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || _service_key
      ),
      body    := jsonb_build_object('client_id', _client.client_id)
    );
  END LOOP;
END;

$function$;

CREATE OR REPLACE FUNCTION public.seed_client_owner()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

DECLARE
  v_email text;
  v_name  text;
BEGIN
  SELECT au.email, au.raw_user_meta_data ->> 'full_name'
    INTO v_email, v_name
    FROM auth.users au
   WHERE au.id::text = NEW.external_user_id
   LIMIT 1;

  IF v_email IS NOT NULL THEN
    INSERT INTO public.client_users (client_id, auth_user_id, email, name, role, accepted_at)
    VALUES (
      NEW.client_id,
      (SELECT id FROM auth.users WHERE id::text = NEW.external_user_id LIMIT 1),
      v_email,
      v_name,
      'owner',
      now()
    )
    ON CONFLICT (client_id, email) DO NOTHING;
  END IF;

  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.set_client_dimension_kpis(p_dimension text, p_slugs text[])
RETURNS jsonb
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.set_client_users_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.set_current_client_id(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;

$function$;

CREATE OR REPLACE FUNCTION public.set_current_cliente_id(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;

$function$;

CREATE OR REPLACE FUNCTION public.set_current_customer_id(p_customer_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $function$

BEGIN
  -- If your app uses customer_id as the client identifier in RLS,
  -- store it in the same session variable.
  PERFORM set_config('app.current_client_id', p_customer_id::text, true);
END;

$function$;

CREATE OR REPLACE FUNCTION public.set_ui_pref(p_key text, p_value jsonb)
RETURNS void
LANGUAGE sql
AS $function$

  UPDATE public.clientes_blu
  SET ui_prefs = jsonb_set(COALESCE(ui_prefs, '{}'), ARRAY[p_key], p_value, true)
  WHERE external_user_id = (auth.jwt() ->> 'sub');

$function$;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.sincronizar_csv_cliente(p_job_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$

DECLARE
  v_job              RECORD;
  v_client_id        UUID;
  v_source_id        UUID;
  v_column_mapping   JSONB;
  v_start_time       TIMESTAMPTZ := now();
  v_rows_affected    BIGINT := 0;
  v_total_rows       INTEGER;
  v_error_msg        TEXT;
  v_staging          RECORD;
  v_row              JSONB;

  v_documento            TEXT;
  v_data_competencia     TEXT;
  v_quantidade           NUMERIC;
  v_valor_unitario       NUMERIC;
  v_valor                NUMERIC;
  v_status               TEXT;
  v_tipo_lancamento      TEXT;
  v_categoria            TEXT;
  v_subcategoria         TEXT;

  v_cliente_cpf_cnpj     TEXT;
  v_cliente_nome         TEXT;
  v_cliente_telefone     TEXT;
  v_cliente_cidade       TEXT;
  v_cliente_uf           TEXT;

  v_fornecedor_cnpj      TEXT;
  v_fornecedor_nome      TEXT;
  v_fornecedor_telefone  TEXT;
  v_fornecedor_cidade    TEXT;
  v_fornecedor_uf        TEXT;

  v_produto_sku          TEXT;
  v_produto_nome         TEXT;

  v_transacao_id         TEXT;
  v_customer_id          BIGINT;
  v_fornecedor_id        BIGINT;
  v_produto_id           BIGINT;
  v_data_id              BIGINT;
  v_parsed_date          DATE;

  -- NEW: classification variables
  v_client_cpf_cnpj      TEXT;   -- CPF/CNPJ do próprio cliente (de clientes_blu)
  v_entity_context       TEXT;   -- detected_entity_context do source
  v_tipo_transacao       TEXT;   -- 'venda' | 'compra' | 'despesa' | 'banking'
  v_entry_type           TEXT;   -- 'revenue' | 'purchase' | 'expense' | 'banking'
BEGIN
  SELECT job_id, client_id, input_params, status
  INTO v_job
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id
  FOR UPDATE;

  IF v_job IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'Job not found', 'job_id', p_job_id);
  END IF;

  IF v_job.status <> 'pending' THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', format('Job is not in pending state (current: %s)', v_job.status),
      'job_id', p_job_id
    );
  END IF;

  v_client_id := v_job.client_id;
  v_source_id := (v_job.input_params->>'source_id')::UUID;

  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = now(), progress_pct = 5, updated_at = now()
  WHERE job_id = p_job_id;

  BEGIN
    SELECT column_mapping INTO v_column_mapping
    FROM public.client_data_sources
    WHERE id = v_source_id AND client_id = v_client_id;

    IF v_column_mapping IS NULL OR v_column_mapping = '{}'::jsonb THEN
      RAISE EXCEPTION 'No column_mapping found for source %', v_source_id;
    END IF;

    -- NEW: fetch client's own CPF/CNPJ and source entity context
    SELECT cpf_cnpj INTO v_client_cpf_cnpj
    FROM public.clientes_blu
    WHERE client_id = v_client_id;

    SELECT detected_entity_context INTO v_entity_context
    FROM public.client_data_sources
    WHERE id = v_source_id AND client_id = v_client_id;

    SELECT * INTO v_staging
    FROM public.csv_import_staging
    WHERE source_id = v_source_id
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_staging IS NULL THEN
      RAISE EXCEPTION 'No staged rows found for source %', v_source_id;
    END IF;

    v_total_rows := jsonb_array_length(v_staging.rows);

    UPDATE analytics_v2.reg_jobs SET progress_pct = 10, updated_at = now() WHERE job_id = p_job_id;

    FOR i IN 0 .. v_total_rows - 1 LOOP
      v_row := v_staging.rows->i;
      v_rows_affected := v_rows_affected + 1;

      v_customer_id   := NULL;
      v_fornecedor_id := NULL;
      v_produto_id    := NULL;
      v_data_id       := NULL;

      v_documento        := v_row ->> (v_column_mapping->>'documento');
      v_data_competencia := v_row ->> (v_column_mapping->>'data_competencia_id');
      v_quantidade       := NULLIF(v_row ->> (v_column_mapping->>'quantidade'), '')::NUMERIC;
      v_valor_unitario   := NULLIF(v_row ->> (v_column_mapping->>'valor_unitario'), '')::NUMERIC;
      v_valor            := NULLIF(v_row ->> (v_column_mapping->>'valor'), '')::NUMERIC;
      v_status           := NULLIF(v_row ->> (v_column_mapping->>'status'), '');
      v_tipo_lancamento  := NULLIF(v_row ->> (v_column_mapping->>'tipo_lancamento'), '');
      v_categoria        := NULLIF(v_row ->> (v_column_mapping->>'categoria'), '');
      v_subcategoria     := NULLIF(v_row ->> (v_column_mapping->>'subcategoria'), '');

      v_cliente_cpf_cnpj := NULLIF(v_row ->> (v_column_mapping->>'cliente_cpf_cnpj'), '');
      v_cliente_nome     := NULLIF(v_row ->> (v_column_mapping->>'cliente_nome'), '');
      v_cliente_telefone := NULLIF(v_row ->> (v_column_mapping->>'cliente_telefone'), '');
      v_cliente_cidade   := NULLIF(v_row ->> (v_column_mapping->>'cliente_cidade'), '');
      v_cliente_uf       := NULLIF(v_row ->> (v_column_mapping->>'cliente_uf'), '');

      v_fornecedor_cnpj     := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_cnpj'), '');
      v_fornecedor_nome     := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_nome'), '');
      v_fornecedor_telefone := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_telefone'), '');
      v_fornecedor_cidade   := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_cidade'), '');
      v_fornecedor_uf       := NULLIF(v_row ->> (v_column_mapping->>'fornecedor_uf'), '');

      v_produto_sku  := NULLIF(v_row ->> (v_column_mapping->>'produto_sku'), '');
      v_produto_nome := NULLIF(v_row ->> (v_column_mapping->>'produto_nome'), '');

      v_transacao_id := md5(
        v_client_id || ':csv:' || v_source_id::TEXT || ':' ||
        COALESCE(v_documento, '') || ':' ||
        COALESCE(v_data_competencia, '') || ':' ||
        COALESCE(v_produto_sku, '') || ':' ||
        v_rows_affected::TEXT
      );

      -- Upsert dim_clientes
      IF v_cliente_cpf_cnpj IS NOT NULL OR v_cliente_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_clientes (
          client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
        ) VALUES (
          v_client_id, v_cliente_cpf_cnpj, v_cliente_nome,
          v_cliente_telefone, v_cliente_cidade, v_cliente_uf, now()
        )
        ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL
        DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_clientes.nome),
          telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_clientes.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_clientes.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_clientes.endereco_uf),
          atualizado_em   = now();

        SELECT customer_id INTO v_customer_id
        FROM analytics_v2.dim_clientes
        WHERE client_id = v_client_id
          AND (
            (v_cliente_cpf_cnpj IS NOT NULL AND cpf_cnpj = v_cliente_cpf_cnpj)
            OR (v_cliente_cpf_cnpj IS NULL AND nome = v_cliente_nome)
          )
        LIMIT 1;
      END IF;

      -- Upsert dim_fornecedores
      IF v_fornecedor_cnpj IS NOT NULL OR v_fornecedor_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_fornecedores (
          client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em
        ) VALUES (
          v_client_id, v_fornecedor_cnpj, v_fornecedor_nome,
          v_fornecedor_telefone, v_fornecedor_cidade, v_fornecedor_uf, now()
        )
        ON CONFLICT (client_id, cnpj) WHERE cnpj IS NOT NULL
        DO UPDATE SET
          nome            = COALESCE(EXCLUDED.nome, analytics_v2.dim_fornecedores.nome),
          telefone        = COALESCE(EXCLUDED.telefone, analytics_v2.dim_fornecedores.telefone),
          endereco_cidade = COALESCE(EXCLUDED.endereco_cidade, analytics_v2.dim_fornecedores.endereco_cidade),
          endereco_uf     = COALESCE(EXCLUDED.endereco_uf, analytics_v2.dim_fornecedores.endereco_uf),
          atualizado_em   = now();

        SELECT fornecedor_id INTO v_fornecedor_id
        FROM analytics_v2.dim_fornecedores
        WHERE client_id = v_client_id
          AND (
            (v_fornecedor_cnpj IS NOT NULL AND cnpj = v_fornecedor_cnpj)
            OR (v_fornecedor_cnpj IS NULL AND nome = v_fornecedor_nome)
          )
        LIMIT 1;
      END IF;

      -- Upsert dim_inventory
      IF v_produto_sku IS NOT NULL OR v_produto_nome IS NOT NULL THEN
        INSERT INTO analytics_v2.dim_inventory (
          client_id, sku, nome, updated_at
        ) VALUES (
          v_client_id, v_produto_sku, v_produto_nome, now()
        )
        ON CONFLICT (client_id, sku) WHERE sku IS NOT NULL
        DO UPDATE SET
          nome       = COALESCE(EXCLUDED.nome, analytics_v2.dim_inventory.nome),
          updated_at = now();

        SELECT inventory_id INTO v_produto_id
        FROM analytics_v2.dim_inventory
        WHERE client_id = v_client_id
          AND (
            (v_produto_sku IS NOT NULL AND sku = v_produto_sku)
            OR (v_produto_sku IS NULL AND nome = v_produto_nome)
          )
        LIMIT 1;
      END IF;

      -- Parse date with three-tier fallback:
      --   1. ISO / standard Postgres DATE cast  (YYYY-MM-DD, etc.)
      --   2. DD/MM/YYYY Brazilian format
      --   3. Excel date serial (integer stored as text because the cell was
      --      formatted as Number, not Date, so cellDates:true skipped it).
      --      Formula: DATE '1899-12-30' + serial  (handles Excel's 1900 leap-year bug)
      v_parsed_date := NULL;
      IF v_data_competencia IS NOT NULL AND v_data_competencia <> '' THEN
        BEGIN
          v_parsed_date := v_data_competencia::DATE;
        EXCEPTION WHEN OTHERS THEN NULL; END;

        IF v_parsed_date IS NULL THEN
          BEGIN
            v_parsed_date := to_date(v_data_competencia, 'DD/MM/YYYY');
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        IF v_parsed_date IS NULL AND v_data_competencia ~ '^\d+$' THEN
          BEGIN
            v_parsed_date := DATE '1899-12-30' + v_data_competencia::INTEGER;
            -- Sanity-check: reject implausible results outside 1970-2100
            IF v_parsed_date < '1970-01-01' OR v_parsed_date > '2100-01-01' THEN
              v_parsed_date := NULL;
            END IF;
          EXCEPTION WHEN OTHERS THEN NULL; END;
        END IF;

        IF v_parsed_date IS NOT NULL THEN
          INSERT INTO analytics_v2.dim_datas (
            data, ano, mes, dia, numero_dia_semana, numero_semana_ano
          ) VALUES (
            v_parsed_date,
            EXTRACT(YEAR  FROM v_parsed_date)::INTEGER,
            EXTRACT(MONTH FROM v_parsed_date)::INTEGER,
            EXTRACT(DAY   FROM v_parsed_date)::INTEGER,
            EXTRACT(ISODOW FROM v_parsed_date)::INTEGER,
            EXTRACT(WEEK  FROM v_parsed_date)::INTEGER
          )
          ON CONFLICT (data) DO NOTHING;

          SELECT data_id INTO v_data_id
          FROM analytics_v2.dim_datas
          WHERE data = v_parsed_date
          LIMIT 1;
        END IF;
      END IF;

      -- ── tipo_transacao cascade (espelha apply_staging_to_facts) ─────────────
      -- Tier 1: tipo_lancamento mapeado no CSV → keyword match
      IF v_tipo_lancamento IS NOT NULL THEN
        v_tipo_transacao := CASE
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['venda%','receita%','faturamento%','nf%','nota fiscal%','revenue%']) THEN 'venda'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['compra%','material%','mat%','insumo%','estoque%','mdo%','mão de obra%','serviço%','servico%','fornecedor%']) THEN 'compra'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['despesa%','custo%','overhead%','admin%','expense%']) THEN 'despesa'
          WHEN v_tipo_lancamento ILIKE ANY(ARRAY['transfer%','banco%','banking%','saldo%']) THEN 'banking'
          ELSE NULL  -- label desconhecido → deixa cair para tier 2
        END;
      END IF;

      -- Tier 2: CPF/CNPJ do próprio cliente cruzado com dados da row
      IF v_tipo_transacao IS NULL AND v_client_cpf_cnpj IS NOT NULL THEN
        IF regexp_replace(COALESCE(v_fornecedor_cnpj, ''), '[^0-9]', '', 'g')
             = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
           AND v_fornecedor_cnpj IS NOT NULL THEN
          v_tipo_transacao := 'venda';   -- cliente é o emissor da NF (fornecedor na row == ele mesmo)
        ELSIF regexp_replace(COALESCE(v_cliente_cpf_cnpj, ''), '[^0-9]', '', 'g')
                = regexp_replace(v_client_cpf_cnpj, '[^0-9]', '', 'g')
              AND v_cliente_cpf_cnpj IS NOT NULL THEN
          v_tipo_transacao := 'compra';  -- cliente é o comprador (cliente na row == ele mesmo)
        END IF;
      END IF;

      -- Tier 3: dim hit — se encontrou cliente/fornecedor nas dims
      IF v_tipo_transacao IS NULL THEN
        IF    v_customer_id   IS NOT NULL THEN v_tipo_transacao := 'venda';
        ELSIF v_fornecedor_id IS NOT NULL THEN v_tipo_transacao := 'compra';
        END IF;
      END IF;

      -- Tier 4: detected_entity_context do source
      IF v_tipo_transacao IS NULL THEN
        v_tipo_transacao := CASE
          WHEN v_entity_context ILIKE ANY(ARRAY['supplier%','cost%','expense%','purchase%','custo%','fornecedor%','compra%']) THEN 'compra'
          WHEN v_entity_context ILIKE ANY(ARRAY['customer%','revenue%','sales%','venda%','faturamento%','cliente%'])          THEN 'venda'
          WHEN v_entity_context ILIKE ANY(ARRAY['banking%','bank%','account%','conta%'])                                      THEN 'banking'
          ELSE 'despesa'  -- último fallback
        END;
      END IF;

      -- Derivar entry_type a partir de tipo_transacao
      v_entry_type := CASE v_tipo_transacao
        WHEN 'venda'   THEN 'revenue'
        WHEN 'compra'  THEN 'purchase'
        WHEN 'despesa' THEN 'expense'
        WHEN 'banking' THEN 'banking'
        ELSE 'expense'
      END;

      -- Insert/upsert fato_transacoes
      INSERT INTO analytics_v2.fato_transacoes (
        transacao_id, client_id, data_competencia_id, customer_id,
        fornecedor_id, produto_id, documento, quantidade,
        valor_unitario, valor, status,
        tipo_transacao, entry_type,
        tipo_lancamento, categoria, subcategoria
      ) VALUES (
        v_transacao_id, v_client_id, v_data_id, v_customer_id,
        v_fornecedor_id, v_produto_id,
        NULLIF(v_documento, ''), v_quantidade,
        v_valor_unitario, v_valor, v_status,
        v_tipo_transacao, v_entry_type,
        v_tipo_lancamento, v_categoria, v_subcategoria
      )
      ON CONFLICT (transacao_id, client_id) DO UPDATE SET
        data_competencia_id = EXCLUDED.data_competencia_id,
        customer_id         = EXCLUDED.customer_id,
        fornecedor_id       = EXCLUDED.fornecedor_id,
        produto_id          = EXCLUDED.produto_id,
        quantidade          = EXCLUDED.quantidade,
        valor_unitario      = EXCLUDED.valor_unitario,
        valor               = EXCLUDED.valor,
        status              = EXCLUDED.status,
        tipo_transacao      = COALESCE(EXCLUDED.tipo_transacao, analytics_v2.fato_transacoes.tipo_transacao),
        entry_type          = COALESCE(EXCLUDED.entry_type,     analytics_v2.fato_transacoes.entry_type),
        tipo_lancamento     = EXCLUDED.tipo_lancamento,
        categoria           = EXCLUDED.categoria,
        subcategoria        = EXCLUDED.subcategoria;

      IF v_rows_affected % 100 = 0 THEN
        UPDATE analytics_v2.reg_jobs
        SET
          progress_pct = LEAST(90, 10 + (v_rows_affected * 80 / GREATEST(v_total_rows, 1))::INTEGER),
          updated_at   = now()
        WHERE job_id = p_job_id;
      END IF;

    END LOOP;

    DELETE FROM public.csv_import_staging WHERE id = v_staging.id;

    UPDATE public.client_data_sources
    SET sync_status = 'completed', last_synced_at = now(), updated_at = now()
    WHERE id = v_source_id;

    UPDATE analytics_v2.reg_jobs
    SET
      status           = 'completed',
      completed_at     = now(),
      rows_inserted    = v_rows_affected,
      progress_pct     = 100,
      duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
      output           = jsonb_build_object('rows_inserted', v_rows_affected, 'completed_at', now()),
      updated_at       = now()
    WHERE job_id = p_job_id;

    RETURN jsonb_build_object(
      'success', true,
      'job_id', p_job_id,
      'rows_inserted', v_rows_affected,
      'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    UPDATE analytics_v2.reg_jobs
    SET
      status           = 'failed',
      completed_at     = now(),
      progress_pct     = 0,
      duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
      error_message    = v_error_msg,
      updated_at       = now()
    WHERE job_id = p_job_id;

    UPDATE public.client_data_sources
    SET sync_status = 'sync_failed', error_message = v_error_msg, updated_at = now()
    WHERE id = v_source_id;

    RETURN jsonb_build_object('success', false, 'job_id', p_job_id, 'error', v_error_msg);
  END;
END;

$function$;

CREATE OR REPLACE FUNCTION public.soft_delete_client(p_client_id uuid)
RETURNS void
LANGUAGE sql
AS $function$
 UPDATE public.clientes_blu SET deleted_at = now() WHERE client_id = p_client_id AND deleted_at IS NULL; 
$function$;

CREATE OR REPLACE FUNCTION public.trigger_column_discovery(p_credential_id bigint)
RETURNS jsonb
LANGUAGE plpgsql
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

$function$;

CREATE OR REPLACE FUNCTION public.update_approval_stats()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO public.client_approval_stats (client_id)
    VALUES (NEW.client_id)
    ON CONFLICT (client_id) DO NOTHING;

    IF NEW.status = 'approved' THEN
      UPDATE public.client_approval_stats
        SET total_approved = total_approved + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    ELSIF NEW.status = 'rejected' THEN
      UPDATE public.client_approval_stats
        SET total_rejected = total_rejected + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    END IF;

    -- Promote trust level based on total_approved thresholds
    UPDATE public.client_approval_stats
      SET trust_level = CASE
        WHEN total_approved >= 50 THEN 'full_config'
        WHEN total_approved >= 25 THEN 'rules'
        WHEN total_approved >= 10 THEN 'similar_toggle'
        ELSE 'manual'
      END,
      updated_at = now()
      WHERE client_id = NEW.client_id;
  END IF;
  RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.update_client_goals_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.update_data_source_mappings_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.update_dimension_state_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$

BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;

$function$;

CREATE OR REPLACE FUNCTION public.upsert_client_document(p_document_type_id text, p_status text DEFAULT 'complete'::text, p_source text DEFAULT 'upload'::text, p_field_coverage jsonb DEFAULT '{}'::jsonb, p_metadata jsonb DEFAULT '{}'::jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$

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
  -- Never-downgrade: only update if the new status is >= the existing status.
  -- missing (lowest) → partial → complete (highest); reverse is never allowed.
  WHERE CASE client_knowledge_documents.status
    WHEN 'missing'  THEN true                         -- any status can overwrite missing
    WHEN 'partial'  THEN EXCLUDED.status = 'complete' -- only 'complete' can overwrite partial
    WHEN 'complete' THEN false                        -- nothing overwrites complete
    ELSE true
  END
  RETURNING jsonb_build_object(
    'document_type_id', document_type_id,
    'status',           status,
    'source',           source,
    'updated_at',       updated_at
  ) INTO v_result;

  -- When the WHERE guard prevented the update, RETURNING yields nothing.
  -- Return the current row instead so callers always get a valid response.
  IF v_result IS NULL THEN
    SELECT jsonb_build_object(
      'document_type_id', document_type_id,
      'status',           status,
      'source',           source,
      'updated_at',       updated_at
    ) INTO v_result
    FROM public.client_knowledge_documents
    WHERE client_id = v_client_id AND document_type_id = p_document_type_id;
  END IF;

  RETURN v_result;
END;

$function$;

CREATE OR REPLACE FUNCTION public.upsert_user_oauth_tokens(p_client_id uuid, p_provider text, p_account_email text, p_access_token text, p_refresh_token text, p_token_type text DEFAULT 'Bearer'::text, p_expires_at timestamp with time zone DEFAULT NULL::timestamp with time zone, p_scopes text[] DEFAULT '{}'::text[], p_metadata jsonb DEFAULT '{}'::jsonb, p_is_default boolean DEFAULT true)
RETURNS void
LANGUAGE plpgsql
AS $function$

DECLARE
  v_name    text := 'oauth_' || lower(p_provider) || '_' || p_client_id::text || '_' || lower(p_account_email);
  v_id      uuid;
  v_payload jsonb := jsonb_build_object(
    'access_token',  p_access_token,
    'refresh_token', p_refresh_token,
    'token_type',    p_token_type,
    'expires_at',    p_expires_at
  );
BEGIN
  SELECT id INTO v_id FROM vault.secrets WHERE name = v_name;
  IF v_id IS NULL THEN
    PERFORM vault.create_secret(v_payload::text, v_name,
      'OAuth tokens: ' || p_provider || ' / ' || p_account_email);
  ELSE
    PERFORM vault.update_secret(v_id, v_payload::text, v_name,
      'OAuth tokens: ' || p_provider || ' / ' || p_account_email);
  END IF;

  IF p_is_default THEN
    UPDATE public.integration_tokens SET is_default = false
    WHERE client_id = p_client_id AND provider = p_provider AND is_default = true;
  END IF;

  INSERT INTO public.integration_tokens
    (client_id, provider, account_email, token_type, scopes, metadata, is_default, vault_secret_name, updated_at)
  VALUES
    (p_client_id, p_provider, lower(p_account_email), p_token_type, p_scopes, p_metadata, p_is_default, v_name, now())
  ON CONFLICT (client_id, provider, account_email) DO UPDATE SET
    token_type        = EXCLUDED.token_type,
    scopes            = EXCLUDED.scopes,
    metadata          = EXCLUDED.metadata,
    is_default        = EXCLUDED.is_default,
    vault_secret_name = EXCLUDED.vault_secret_name,
    updated_at        = now();
END;

$function$;

CREATE OR REPLACE FUNCTION public.verify_tenant_password(p_email text, p_plain text)
RETURNS boolean
LANGUAGE sql
AS $function$

  SELECT cb.password = p_plain
  FROM public.clientes_blu cb
  JOIN auth.users u ON u.id::text = cb.external_user_id
  WHERE u.email = p_email
  LIMIT 1

$function$;

-- Views
CREATE OR REPLACE VIEW public.active_clientes_blu AS
  SELECT client_id, api_key, nome_empresa, tipo_cliente, tier, collection_rag,
    created_at, updated_at, external_user_id, onboarding_state, onboarding_completed_at,
    company_profile, brand_voice, team_structure, policies, data_schema, available_tools,
    cpf_cnpj, password, deleted_at
  FROM clientes_blu
  WHERE (deleted_at IS NULL);

-- Enable Row Level Security
ALTER TABLE public.agent_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bigquery_foreign_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bigquery_servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_watch_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_approval_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_approval_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_dimension_kpis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_enabled_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_routine_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_routines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes_blu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversa ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credencial_servico_externo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cross_agent_routines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.csv_import_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_source_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dimension_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doc_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.frontend_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_agent_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_document_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_tag_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kpi_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nps_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.polp_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.polp_bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.polp_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.polp_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sql_table_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.standalone_agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_files_metadata ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "read all" ON public.agent_catalog AS PERMISSIVE FOR SELECT TO authenticated USING ((is_active = true));
CREATE POLICY app_config_service_only ON public.app_config AS PERMISSIVE FOR ALL TO public USING (false);
CREATE POLICY no_public_access ON public.app_config AS RESTRICTIVE FOR ALL TO public USING (false);
CREATE POLICY "own client" ON public.approval_requests AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.audit_log AS PERMISSIVE FOR SELECT TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY bigquery_foreign_tables_access ON public.bigquery_foreign_tables AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY bigquery_foreign_tables_update ON public.bigquery_foreign_tables AS PERMISSIVE FOR UPDATE TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id())))) WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY bigquery_foreign_tables_write ON public.bigquery_foreign_tables AS PERMISSIVE FOR INSERT TO public WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY bigquery_servers_access ON public.bigquery_servers AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY bigquery_servers_update ON public.bigquery_servers AS PERMISSIVE FOR UPDATE TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id())))) WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY bigquery_servers_write ON public.bigquery_servers AS PERMISSIVE FOR INSERT TO public WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY "insert own client" ON public.calendar_settings AS PERMISSIVE FOR INSERT TO public WITH CHECK ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));
CREATE POLICY "own client" ON public.calendar_settings AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));
CREATE POLICY "update own client" ON public.calendar_settings AS PERMISSIVE FOR UPDATE TO public USING ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id()))) WITH CHECK ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));
CREATE POLICY "service role only" ON public.calendar_watch_channels AS PERMISSIVE FOR ALL TO public USING (false);
CREATE POLICY "approval_rules: client manages own" ON public.client_approval_rules AS PERMISSIVE FOR ALL TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "approval_rules: client sees own" ON public.client_approval_rules AS PERMISSIVE FOR SELECT TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "approval_stats: client sees own" ON public.client_approval_stats AS PERMISSIVE FOR SELECT TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY client_data_sources_access ON public.client_data_sources AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY client_data_sources_update ON public.client_data_sources AS PERMISSIVE FOR UPDATE TO public USING ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id())))) WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY client_data_sources_write ON public.client_data_sources AS PERMISSIVE FOR INSERT TO public WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'service_role'::text) OR (((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (client_id = get_my_client_id()))));
CREATE POLICY "own client" ON public.client_dimension_kpis AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.client_enabled_agents AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY client_own_goals ON public.client_goals AS PERMISSIVE FOR ALL TO public USING ((client_id = (current_setting('app.client_id'::text, true))::uuid));
CREATE POLICY "own client" ON public.client_insights AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY ckd_client_all ON public.client_knowledge_documents AS PERMISSIVE FOR ALL TO public USING ((client_id = get_my_client_id()));
CREATE POLICY "notif_prefs: client manages own" ON public.client_notification_preferences AS PERMISSIVE FOR ALL TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "notif_prefs: client sees own" ON public.client_notification_preferences AS PERMISSIVE FOR SELECT TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "own client" ON public.client_routine_executions AS PERMISSIVE FOR SELECT TO public USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.client_routines AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY client_users_delete ON public.client_users AS PERMISSIVE FOR DELETE TO public USING (((client_id = get_my_client_id()) AND (EXISTS ( SELECT 1 FROM client_users cu WHERE ((cu.client_id = get_my_client_id()) AND (cu.auth_user_id = auth.uid()) AND (cu.role = ANY (ARRAY['owner'::text, 'admin'::text])))))));
CREATE POLICY client_users_insert ON public.client_users AS PERMISSIVE FOR INSERT TO public WITH CHECK (((client_id = get_my_client_id()) AND ((NOT (EXISTS ( SELECT 1 FROM client_users client_users_1 WHERE (client_users_1.client_id = get_my_client_id())))) OR (EXISTS ( SELECT 1 FROM client_users cu WHERE ((cu.client_id = get_my_client_id()) AND (cu.auth_user_id = auth.uid()) AND (cu.role = ANY (ARRAY['owner'::text, 'admin'::text]))))))));
CREATE POLICY client_users_select ON public.client_users AS PERMISSIVE FOR SELECT TO public USING ((client_id = get_my_client_id()));
CREATE POLICY client_users_service_role ON public.client_users AS PERMISSIVE FOR ALL TO public USING (((auth.jwt() ->> 'role'::text) = 'service_role'::text)) WITH CHECK (((auth.jwt() ->> 'role'::text) = 'service_role'::text));
CREATE POLICY client_users_update ON public.client_users AS PERMISSIVE FOR UPDATE TO public USING (((client_id = get_my_client_id()) AND ((auth_user_id = auth.uid()) OR (EXISTS ( SELECT 1 FROM client_users cu WHERE ((cu.client_id = get_my_client_id()) AND (cu.auth_user_id = auth.uid()) AND (cu.role = ANY (ARRAY['owner'::text, 'admin'::text])))))))) WITH CHECK ((client_id = get_my_client_id()));
CREATE POLICY "Authenticated users insert own" ON public.clientes_blu AS PERMISSIVE FOR INSERT TO public WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))));
CREATE POLICY "Authenticated users read own" ON public.clientes_blu AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))));
CREATE POLICY "Authenticated users update own" ON public.clientes_blu AS PERMISSIVE FOR UPDATE TO public USING ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text)))) WITH CHECK ((((auth.jwt() ->> 'role'::text) = 'authenticated'::text) AND (external_user_id = (auth.jwt() ->> 'sub'::text))));
CREATE POLICY "Service role unrestricted" ON public.clientes_blu AS PERMISSIVE FOR ALL TO public USING (((auth.jwt() ->> 'role'::text) = 'service_role'::text)) WITH CHECK (((auth.jwt() ->> 'role'::text) = 'service_role'::text));
CREATE POLICY "own client" ON public.conversa AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.credencial_servico_externo AS PERMISSIVE FOR ALL TO public USING ((client_id = get_my_client_id()));
CREATE POLICY car_public_read ON public.cross_agent_routines AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "own client" ON public.csv_import_staging AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.data_source_mappings AS PERMISSIVE FOR ALL TO public USING ((client_id = get_my_client_id()));
CREATE POLICY client_own_dimension_state ON public.dimension_state AS PERMISSIVE FOR ALL TO public USING ((client_id = (current_setting('app.client_id'::text, true))::uuid));
CREATE POLICY doc_templates_delete ON public.doc_templates AS PERMISSIVE FOR DELETE TO public USING (((is_system = false) AND (client_id = ((auth.jwt() ->> 'client_id'::text))::uuid)));
CREATE POLICY doc_templates_insert ON public.doc_templates AS PERMISSIVE FOR INSERT TO public WITH CHECK (((is_system = false) AND (client_id = ((auth.jwt() ->> 'client_id'::text))::uuid)));
CREATE POLICY doc_templates_select ON public.doc_templates AS PERMISSIVE FOR SELECT TO public USING (((is_system = true) OR (client_id = ((auth.jwt() ->> 'client_id'::text))::uuid)));
CREATE POLICY document_versions_select ON public.document_versions AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1 FROM documents d WHERE ((d.id = document_versions.document_id) AND (d.client_id = ((auth.jwt() ->> 'client_id'::text))::uuid)))));
CREATE POLICY documents_delete ON public.documents AS PERMISSIVE FOR DELETE TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY documents_insert ON public.documents AS PERMISSIVE FOR INSERT TO public WITH CHECK ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY documents_select ON public.documents AS PERMISSIVE FOR SELECT TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY documents_update ON public.documents AS PERMISSIVE FOR UPDATE TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "own client" ON public.frontend_events AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.integration_configs AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.integration_tokens AS PERMISSIVE FOR SELECT TO public USING ((((auth.jwt() ->> 'sub'::text) IS NULL) OR (client_id = get_my_client_id())));
CREATE POLICY "own client delete" ON public.integration_tokens AS PERMISSIVE FOR DELETE TO public USING ((client_id = get_my_client_id()));
CREATE POLICY kar_public_read ON public.knowledge_agent_requirements AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY kdt_public_read ON public.knowledge_document_types AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY ktd_public_read ON public.knowledge_tag_definitions AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "read all" ON public.kpi_catalog AS PERMISSIVE FOR SELECT TO authenticated USING (true);
CREATE POLICY "own client" ON public.messages AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "notifications: client sees own" ON public.notifications AS PERMISSIVE FOR SELECT TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "notifications: client updates own" ON public.notifications AS PERMISSIVE FOR UPDATE TO public USING ((client_id = ((auth.jwt() ->> 'client_id'::text))::uuid));
CREATE POLICY "own client" ON public.nps_responses AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "client members read own polp accounts" ON public.polp_accounts AS PERMISSIVE FOR SELECT TO public USING ((client_id IN ( SELECT client_users.client_id FROM client_users WHERE (client_users.auth_user_id = auth.uid()))));
CREATE POLICY "client members read own polp bills" ON public.polp_bills AS PERMISSIVE FOR SELECT TO public USING ((client_id IN ( SELECT client_users.client_id FROM client_users WHERE (client_users.auth_user_id = auth.uid()))));
CREATE POLICY "client members read own polp integrations" ON public.polp_integrations AS PERMISSIVE FOR SELECT TO public USING ((client_id IN ( SELECT client_users.client_id FROM client_users WHERE (client_users.auth_user_id = auth.uid()))));
CREATE POLICY "client members read own polp transactions" ON public.polp_transactions AS PERMISSIVE FOR SELECT TO public USING ((client_id IN ( SELECT client_users.client_id FROM client_users WHERE (client_users.auth_user_id = auth.uid()))));
CREATE POLICY "own client" ON public.report_runs AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.report_schedules AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY client_read_own ON public.sql_table_config AS PERMISSIVE FOR SELECT TO authenticated USING ((client_id IN ( SELECT clientes_blu.client_id FROM clientes_blu WHERE (clientes_blu.external_user_id = (auth.uid())::text))));
CREATE POLICY service_role_all ON public.sql_table_config AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "own client" ON public.standalone_agent_sessions AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));
CREATE POLICY "own client" ON public.uploaded_files_metadata AS PERMISSIVE FOR ALL TO authenticated USING ((client_id = get_my_client_id()));

-- Triggers
CREATE TRIGGER trg_approval_requests_updated_at BEFORE UPDATE ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_document_review_approved AFTER UPDATE OF status ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION on_document_review_approved();
CREATE TRIGGER trg_document_review_rejected AFTER UPDATE OF status ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION on_document_review_rejected();
CREATE TRIGGER trg_knowledge_on_approval_completed AFTER UPDATE OF status ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION on_approval_completed();
CREATE TRIGGER trg_redispatch_after_approval AFTER UPDATE OF status ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION redispatch_routine_after_approval();
CREATE TRIGGER trg_sale_approved AFTER UPDATE ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION on_approval_sale_approved();
CREATE TRIGGER trg_update_approval_stats AFTER UPDATE OF status ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION update_approval_stats();
CREATE TRIGGER trg_drop_bigquery_fdw_server BEFORE DELETE ON public.bigquery_servers FOR EACH ROW EXECUTE FUNCTION drop_bigquery_fdw_server();
CREATE TRIGGER trg_client_goals_updated_at BEFORE UPDATE ON public.client_goals FOR EACH ROW EXECUTE FUNCTION update_client_goals_updated_at();
CREATE TRIGGER trg_enqueue_routine_on_doc_complete AFTER UPDATE OF status ON public.client_knowledge_documents FOR EACH ROW EXECUTE FUNCTION on_knowledge_document_complete();
CREATE TRIGGER trg_client_users_updated_at BEFORE UPDATE ON public.client_users FOR EACH ROW EXECUTE FUNCTION set_client_users_updated_at();
CREATE TRIGGER trg_auto_enroll_catalog_routines AFTER INSERT ON public.clientes_blu FOR EACH ROW EXECUTE FUNCTION auto_enroll_catalog_routines();
CREATE TRIGGER trg_auto_enroll_system_routines AFTER INSERT ON public.clientes_blu FOR EACH ROW EXECUTE FUNCTION auto_enroll_system_routines();
CREATE TRIGGER trg_ensure_approval_stats AFTER INSERT ON public.clientes_blu FOR EACH ROW EXECUTE FUNCTION ensure_client_approval_stats();
CREATE TRIGGER trg_seed_client_owner AFTER INSERT ON public.clientes_blu FOR EACH ROW EXECUTE FUNCTION seed_client_owner();
CREATE TRIGGER trigger_update_data_source_mappings_updated_at BEFORE UPDATE ON public.data_source_mappings FOR EACH ROW EXECUTE FUNCTION update_data_source_mappings_updated_at();
CREATE TRIGGER trg_dimension_state_updated_at BEFORE UPDATE ON public.dimension_state FOR EACH ROW EXECUTE FUNCTION update_dimension_state_updated_at();
CREATE TRIGGER polp_accounts_updated_at BEFORE UPDATE ON public.polp_accounts FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();
CREATE TRIGGER polp_bills_updated_at BEFORE UPDATE ON public.polp_bills FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();
CREATE TRIGGER polp_integrations_updated_at BEFORE UPDATE ON public.polp_integrations FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();
CREATE TRIGGER polp_transactions_updated_at BEFORE UPDATE ON public.polp_transactions FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();

-- =============================================================================
-- analytics_v2.dim_clientes (materialized from archive)
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytics_v2.dim_clientes (
  customer_id          BIGINT  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  client_id            UUID    REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  cpf_cnpj             TEXT,
  nome                 TEXT,
  telefone             TEXT,
  endereco_cidade      TEXT,
  endereco_uf          TEXT,
  total_pedidos        BIGINT  DEFAULT 0,
  receita_total        NUMERIC(15,2) DEFAULT 0,
  ticket_medio         NUMERIC(15,2) DEFAULT 0,
  quantidade_total     NUMERIC DEFAULT 0,
  frequencia_mensal    NUMERIC,
  dias_recencia        INTEGER,
  data_primeira_compra DATE,
  data_ultima_compra   DATE,
  pontuacao_cluster    NUMERIC,
  nivel_cluster        TEXT,
  atualizado_em        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dim_clientes_client ON analytics_v2.dim_clientes(client_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_clientes_cpf_cnpj ON analytics_v2.dim_clientes(client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL;

-- =============================================================================
-- analytics_v2.fato_transacoes (materialized from archive)
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytics_v2.fato_transacoes (
  transacao_id          TEXT    NOT NULL,
  client_id             UUID    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  data_competencia_id   BIGINT  REFERENCES analytics_v2.dim_datas(data_id) ON DELETE SET NULL,
  customer_id           BIGINT  REFERENCES analytics_v2.dim_clientes(customer_id) ON DELETE SET NULL,
  fornecedor_id         BIGINT  REFERENCES analytics_v2.dim_fornecedores(fornecedor_id) ON DELETE SET NULL,
  produto_id            BIGINT  REFERENCES analytics_v2.dim_inventory(inventory_id) ON DELETE SET NULL,
  documento             TEXT,
  quantidade            NUMERIC,
  valor_unitario        NUMERIC(15,2),
  valor                 NUMERIC(15,2),
  status                TEXT,
  tipo_transacao        TEXT,
  entry_type            TEXT,
  tipo_lancamento       TEXT,
  categoria             TEXT,
  subcategoria          TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (transacao_id, client_id)
);
CREATE INDEX IF NOT EXISTS idx_fato_client ON analytics_v2.fato_transacoes(client_id);
CREATE INDEX IF NOT EXISTS idx_fato_data ON analytics_v2.fato_transacoes(data_competencia_id);
CREATE INDEX IF NOT EXISTS idx_fato_customer ON analytics_v2.fato_transacoes(customer_id);
CREATE INDEX IF NOT EXISTS idx_fato_fornecedor ON analytics_v2.fato_transacoes(fornecedor_id);

-- =============================================================================
-- analytics_v2.reg_jobs (with csv_sync in CHECK constraint)
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytics_v2.reg_jobs (
  job_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  job_type      TEXT        NOT NULL DEFAULT 'bigquery_sync'
                CHECK (job_type IN ('bigquery_sync','connector_sync','analytics_etl','csv_sync','custom')),
  credential_id BIGINT      REFERENCES public.credencial_servico_externo(id) ON DELETE SET NULL,
  resource_type TEXT,
  sync_mode     TEXT        DEFAULT 'incremental' CHECK (sync_mode IN ('incremental','full')),
  status        TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
  input_params  JSONB       DEFAULT '{}',
  output        JSONB,
  rows_inserted BIGINT      DEFAULT 0,
  progress_pct  INTEGER     DEFAULT 0,
  error_message TEXT,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  duration_seconds NUMERIC,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reg_jobs_client_status ON analytics_v2.reg_jobs(client_id, status);
CREATE INDEX IF NOT EXISTS idx_reg_jobs_created ON analytics_v2.reg_jobs(created_at DESC);

-- =============================================================================
-- pg_cron job: process-csv-sync-jobs (dispatches ETL for csv_sync jobs)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.process_csv_sync_jobs()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  -- Placeholder: implementation in run-csv-etl Edge Function
  -- Dispatched by pg_cron on a 5-minute heartbeat
END;
$$;

SELECT cron.schedule('process-csv-sync-jobs', '*/5 * * * *', $$SELECT public.process_csv_sync_jobs();$$);
