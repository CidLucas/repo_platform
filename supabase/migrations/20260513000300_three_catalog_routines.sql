-- ─────────────────────────────────────────────────────────────────────────────
-- Three Catalog Routines + Trigger Schema
--
-- 1. Add trigger_type / trigger_config to cross_agent_routines
-- 2. Extend client_routines.trigger_type check to include 'numeric'
-- 3. Add get_new_clients_monthly_rate() RPC for numeric trigger evaluation
-- 4. Seed three catalog routines: weekly_reengagement, onboarding_complete,
--    low_new_client_alert
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. cross_agent_routines: trigger columns ─────────────────────────────────

ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS trigger_type   text NOT NULL DEFAULT 'manual'
    CHECK (trigger_type IN ('manual', 'cron', 'event', 'numeric')),
  ADD COLUMN IF NOT EXISTS trigger_config jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.cross_agent_routines.trigger_type IS
  'How this routine fires: manual (admin/user), cron (scheduled), event (hook), numeric (metric threshold).';
COMMENT ON COLUMN public.cross_agent_routines.trigger_config IS
  'Trigger-specific config: {expression} for cron, {event_type} for event, {metric, threshold, window_months} for numeric.';


-- ── 2. client_routines: extend trigger_type to include 'numeric' ─────────────

ALTER TABLE public.client_routines
  DROP CONSTRAINT IF EXISTS client_routines_trigger_type_check;

ALTER TABLE public.client_routines
  ADD CONSTRAINT client_routines_trigger_type_check
  CHECK (trigger_type IN ('manual', 'document', 'schedule', 'event', 'numeric'));


-- ── 3. get_new_clients_monthly_rate() — metric for numeric trigger ────────────
--
-- Returns the count of new end-customers in the current calendar month and
-- the rolling average over the last N months.
-- "New" is approximated by dias_recencia <= 30 (first-time buyers appear with
-- low recency; adjust if you have an acquisition_date column).

CREATE OR REPLACE FUNCTION public.get_new_clients_monthly_rate(
  p_client_id    uuid,
  p_window_months integer DEFAULT 12
)
RETURNS TABLE(current_month_count bigint, avg_monthly_count numeric)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_current bigint;
  v_total   bigint;
BEGIN
  -- Current month new customers (recency proxy: ≤30 days)
  SELECT count(*) INTO v_current
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= 30;

  -- Total new customers over window (rough monthly average)
  SELECT count(*) INTO v_total
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia <= (p_window_months * 30);

  current_month_count := COALESCE(v_current, 0);
  avg_monthly_count   := ROUND(COALESCE(v_total, 0)::numeric / GREATEST(p_window_months, 1), 2);

  RETURN NEXT;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.get_new_clients_monthly_rate(uuid, integer) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.get_new_clients_monthly_rate(uuid, integer) TO service_role;


-- ── 4. Seed three catalog routines ───────────────────────────────────────────

-- 4a. weekly_reengagement
-- Fires every Monday at 09:00. Queries inactive clients, enriches context,
-- writes personalised re-engagement emails, and sends them.

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'weekly_reengagement',
  'Reengajamento Semanal',
  'clientes',
  'crm',
  'cron',
  '{"expression": "0 9 * * 1"}'::jsonb,
  '[
    {
      "id":       "query_inactive",
      "step":     1,
      "type":     "function",
      "function": "analytics.query_inactive_clients",
      "inputs":   {"days_inactive": 14, "lookback_months": 3},
      "outputs":  ["client_list"],
      "on_failure": "halt"
    },
    {
      "id":       "gather_context",
      "step":     2,
      "type":     "function",
      "function": "analytics.gather_client_context",
      "inputs":   {"client_list": "{{client_list}}"},
      "outputs":  ["client_context"],
      "on_failure": "halt"
    },
    {
      "id":            "write_emails",
      "step":          3,
      "type":          "skill",
      "skill_slug":    "crm",
      "task_template": "Escreva emails de reengajamento personalizados para os seguintes clientes inativos da empresa {{nome_empresa}}. Use o histórico de compras e o cluster de cada cliente para personalizar a abordagem.\n\nClientes: {{client_context}}",
      "outputs":       {"emails": "array de objetos {to_email, subject, body_html}"},
      "on_failure":    "halt"
    },
    {
      "id":            "send_emails",
      "step":          4,
      "type":          "artifact",
      "artifact_type": "email",
      "function":      "channels.send_email_batch",
      "inputs":        {"emails": "{{emails}}"},
      "on_failure":    "continue"
    }
  ]'::jsonb,
  '[
    {"key": "days_inactive",   "label": "Dias inativo mínimo",  "type": "number",  "default": 14},
    {"key": "lookback_months", "label": "Janela de atividade",  "type": "number",  "default": 3}
  ]'::jsonb
)
ON CONFLICT (id) DO UPDATE
  SET name          = EXCLUDED.name,
      trigger_type  = EXCLUDED.trigger_type,
      trigger_config= EXCLUDED.trigger_config,
      steps         = EXCLUDED.steps,
      config_schema = EXCLUDED.config_schema;


-- 4b. onboarding_complete
-- Fires when a client completes onboarding (event trigger).
-- Generates a context report, crawls the company website, fetches the
-- masterprompt template, asks the estrategia agent to fill it, then saves
-- the document and creates an in-app alert.

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'onboarding_complete',
  'Mapa de Contexto (Onboarding)',
  'clientes',
  'estrategia',
  'event',
  '{"event_type": "onboarding_completed"}'::jsonb,
  '[
    {
      "id":       "generate_report",
      "step":     1,
      "type":     "function",
      "function": "analytics.generate_context_report",
      "inputs":   {},
      "outputs":  ["context_report_summary"],
      "on_failure": "continue"
    },
    {
      "id":       "crawl_website",
      "step":     2,
      "type":     "function",
      "function": "web.extract_company_context",
      "inputs":   {"url": "{{website_url}}"},
      "outputs":  ["website_content"],
      "on_failure": "continue"
    },
    {
      "id":       "get_masterprompt",
      "step":     3,
      "type":     "function",
      "function": "knowledge.get_masterprompt",
      "inputs":   {},
      "outputs":  ["masterprompt", "masterprompt_exists"],
      "on_failure": "halt"
    },
    {
      "id":            "fill_masterprompt",
      "step":          4,
      "type":          "skill",
      "skill_slug":    "estrategia",
      "task_template": "Preencha o Business Context Map abaixo com informações da empresa {{nome_empresa}}. Use os dados disponíveis: contexto do site ({{website_content}}), relatório de contexto ({{context_report_summary}}). Mantenha a estrutura de seções do documento e escreva em PT-BR.\n\nTemplate atual:\n{{masterprompt}}",
      "outputs":       {"filled_masterprompt": "markdown string com o Business Context Map preenchido"},
      "on_failure":    "halt"
    },
    {
      "id":            "save_document",
      "step":          5,
      "type":          "artifact",
      "artifact_type": "document",
      "function":      "storage.save_context_document",
      "inputs":        {"content": "{{filled_masterprompt}}", "title": "Business Context Map"},
      "on_failure":    "continue"
    },
    {
      "id":            "notify_alert",
      "step":          6,
      "type":          "artifact",
      "artifact_type": "alert",
      "inputs":        {"title": "Mapa de Contexto gerado", "body": "O Business Context Map de {{nome_empresa}} foi criado e indexado na base de conhecimento.", "priority": "normal", "artifact_type": "document", "artifact_id": "{{document_id}}"},
      "on_failure":    "continue"
    }
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (id) DO UPDATE
  SET name          = EXCLUDED.name,
      trigger_type  = EXCLUDED.trigger_type,
      trigger_config= EXCLUDED.trigger_config,
      steps         = EXCLUDED.steps,
      config_schema = EXCLUDED.config_schema;


-- 4c. low_new_client_alert
-- Fires when new client acquisition drops below 50% of the 12-month average.
-- Asks the estrategia agent for recommendations, then emails them to the client.

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'low_new_client_alert',
  'Alerta: Baixa Captação de Clientes',
  'clientes',
  'crm',
  'numeric',
  '{"metric": "new_clients_monthly_rate", "threshold": 0.5, "window_months": 12}'::jsonb,
  '[
    {
      "id":            "strategy_recommendations",
      "step":          1,
      "type":          "skill",
      "skill_slug":    "estrategia",
      "task_template": "A captação de novos clientes da empresa {{nome_empresa}} este mês está abaixo de 50% da média dos últimos 12 meses. Analise essa situação e forneça 3-5 recomendações práticas e específicas para reverter essa tendência. Considere canais de aquisição, ofertas, sazonalidade e contexto do negócio.",
      "outputs":       {"email_content": "texto em HTML com as recomendações formatadas para email"},
      "on_failure":    "halt"
    },
    {
      "id":            "send_alert_email",
      "step":          2,
      "type":          "artifact",
      "artifact_type": "email",
      "function":      "channels.send_email_batch",
      "inputs":        {"emails": [{"to_email": "{{notify_email}}", "subject": "Alerta Blu: Captação de clientes abaixo da média", "body_html": "{{email_content}}"}]},
      "on_failure":    "continue"
    }
  ]'::jsonb,
  '[
    {"key": "threshold",      "label": "Limite (% da média)",   "type": "number",  "default": 0.5},
    {"key": "window_months",  "label": "Janela histórica (meses)", "type": "number", "default": 12}
  ]'::jsonb
)
ON CONFLICT (id) DO UPDATE
  SET name          = EXCLUDED.name,
      trigger_type  = EXCLUDED.trigger_type,
      trigger_config= EXCLUDED.trigger_config,
      steps         = EXCLUDED.steps,
      config_schema = EXCLUDED.config_schema;
