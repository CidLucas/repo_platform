-- Migration: cross_agent_routines.steps[].skill_slug
-- Substitui agent slugs por skill slugs diretos do SKILL_REGISTRY
-- Identificador: coluna "id" (não "name" que é display label)

UPDATE cross_agent_routines
SET steps = (
  SELECT jsonb_agg(
    CASE
      WHEN id = 'agenda_monitor'        AND step->>'skill_slug' = 'agenda'     THEN jsonb_set(step, '{skill_slug}', '"agenda_monitor_report"')
      WHEN id = 'clientes_monitor'      AND step->>'skill_slug' = 'crm'        THEN jsonb_set(step, '{skill_slug}', '"clients_monitor_report"')
      WHEN id = 'compras_monitor'       AND step->>'skill_slug' = 'compras'    THEN jsonb_set(step, '{skill_slug}', '"inventory_digest"')
      WHEN id = 'financeiro_monitor'    AND step->>'skill_slug' = 'financeiro' THEN jsonb_set(step, '{skill_slug}', '"finance_monitor_report"')
      WHEN id = 'daily_insights'        AND step->>'skill_slug' = 'synthesis'  THEN jsonb_set(step, '{skill_slug}', '"insights_synthesis"')
      WHEN id = 'collection_overdue'    AND step->>'skill_slug' = 'crm'        THEN jsonb_set(step, '{skill_slug}', '"collection_messages"')
      WHEN id = 'client_reactivation'   AND step->>'skill_slug' = 'crm'        THEN jsonb_set(step, '{skill_slug}', '"reactivation_proposal"')
      WHEN id = 'sales_followup'        AND step->>'skill_slug' = 'crm'        THEN jsonb_set(step, '{skill_slug}', '"followup_draft"')
      WHEN id = 'satisfaction_survey'   AND step->>'skill_slug' = 'crm'        THEN jsonb_set(step, '{skill_slug}', '"satisfaction_survey"')
      WHEN id = 'meeting_prep'          AND step->>'skill_slug' = 'agenda'     THEN jsonb_set(step, '{skill_slug}', '"meeting_brief"')
      WHEN id = 'monthly_reconciliation' AND step->>'skill_slug' = 'financeiro' THEN jsonb_set(step, '{skill_slug}', '"reconciliation_report"')
      WHEN id = 'competitor_analysis'   AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"competitor_analysis"')
      WHEN id = 'daily_briefing'        AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"morning_plan"')
      WHEN id = 'end_of_day_digest'     AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"end_of_day_digest"')
      WHEN id = 'weekly_summary'        AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"weekly_summary"')
      WHEN id = 'hidden_patterns'       AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"hidden_patterns"')
      WHEN id = 'onboarding_complete'   AND step->>'skill_slug' = 'estrategia' THEN jsonb_set(step, '{skill_slug}', '"insights_synthesis"')
      ELSE step
    END
  )
  FROM jsonb_array_elements(steps) AS step
);
