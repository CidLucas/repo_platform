-- =============================================================================
-- Fix: add `room` column to cross_agent_routines (was referenced in INSERT
-- seeds and get_unified_tasks RPC but never defined via ALTER TABLE).
-- Also adds `visibility` idempotently in case 20260520000300 was skipped.
-- =============================================================================

-- ── 1. room column ────────────────────────────────────────────────────────────
ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS room text NOT NULL DEFAULT 'estrategia';

-- ── 2. visibility column (idempotent; safe if already added) ─────────────────
ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'builtin'
    CHECK (visibility IN ('builtin', 'optional', 'hidden'));

-- ── 3. Backfill known room values from all seed migrations ───────────────────
-- Routines not listed here keep the DEFAULT 'estrategia'.

UPDATE public.cross_agent_routines SET room = 'estrategia' WHERE id IN (
  'daily_briefing',
  'morning_sync',
  'pending_decisions_review',
  'end_of_day_digest',
  'weekly_summary',
  'hidden_patterns',
  'competitor_analysis'
);

UPDATE public.cross_agent_routines SET room = 'agenda' WHERE id IN (
  'deadline_radar',
  'meeting_prep',
  'agenda_monitor'
);

UPDATE public.cross_agent_routines SET room = 'clientes' WHERE id IN (
  'weekly_reengagement',
  'onboarding_complete',
  'low_new_client_alert',
  'collection_overdue',
  'sales_followup',
  'client_reactivation',
  'satisfaction_survey',
  'clientes_monitor'
);

UPDATE public.cross_agent_routines SET room = 'financeiro' WHERE id IN (
  'cash_flow_alert',
  'monthly_reconciliation',
  'monthly_close',
  'financeiro_monitor'
);

UPDATE public.cross_agent_routines SET room = 'operacoes' WHERE id IN (
  'inventory_alert',
  'supplier_management'
);

UPDATE public.cross_agent_routines SET room = 'compras' WHERE id IN (
  'compras_monitor'
);

UPDATE public.cross_agent_routines SET room = 'home' WHERE id IN (
  'daily_insights'
);

UPDATE public.cross_agent_routines SET room = 'biblioteca' WHERE id IN (
  'biblioteca_monitor'
);

COMMENT ON COLUMN public.cross_agent_routines.room IS
  'Room/domain this routine belongs to (matches rooms in the app: '
  'estrategia, agenda, clientes, financeiro, operacoes, compras, home, biblioteca). '
  'Used by get_unified_tasks() to map routines to Gantt domains.';
