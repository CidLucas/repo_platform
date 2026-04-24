-- Migration: NPS responses table + score RPC
-- Date: 2026-04-23
-- Phase: Dashboard mocks → live data, Phase 1
--
-- Adds public.nps_responses (RLS-scoped) and public.get_nps_score(window_days)
-- powering the NPS tile on the HomePage KPI rail.

-- ── 1. Table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.nps_responses (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   text NOT NULL,
  user_id     text,
  score       smallint NOT NULL CHECK (score BETWEEN 0 AND 10),
  comment     text,
  source      text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_nps_responses_client_created
  ON public.nps_responses(client_id, created_at DESC);

ALTER TABLE public.nps_responses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS nps_responses_select ON public.nps_responses;
CREATE POLICY nps_responses_select ON public.nps_responses
  FOR SELECT TO authenticated
  USING (client_id = public.get_my_client_id());

DROP POLICY IF EXISTS nps_responses_insert ON public.nps_responses;
CREATE POLICY nps_responses_insert ON public.nps_responses
  FOR INSERT TO authenticated
  WITH CHECK (client_id = public.get_my_client_id());

DROP POLICY IF EXISTS nps_responses_service ON public.nps_responses;
CREATE POLICY nps_responses_service ON public.nps_responses
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- ── 2. RPC ───────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_nps_score(
  p_window_days int DEFAULT 90
)
RETURNS TABLE (
  score            numeric,
  total_responses  int,
  promoters        int,
  passives         int,
  detractors       int
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
  WITH window_responses AS (
    SELECT score
    FROM public.nps_responses
    WHERE client_id = public.get_my_client_id()
      AND created_at >= now() - make_interval(days => GREATEST(p_window_days, 1))
  ),
  buckets AS (
    SELECT
      COUNT(*) FILTER (WHERE score >= 9)              AS promoters,
      COUNT(*) FILTER (WHERE score BETWEEN 7 AND 8)   AS passives,
      COUNT(*) FILTER (WHERE score <= 6)              AS detractors,
      COUNT(*)                                        AS total
    FROM window_responses
  )
  SELECT
    CASE WHEN total > 0
         THEN ROUND(((promoters - detractors)::numeric / total) * 100, 0)
         ELSE 0
    END                AS score,
    total::int         AS total_responses,
    promoters::int     AS promoters,
    passives::int      AS passives,
    detractors::int    AS detractors
  FROM buckets;
$$;

GRANT EXECUTE ON FUNCTION public.get_nps_score(int) TO authenticated;

COMMENT ON TABLE public.nps_responses IS
  'NPS survey responses. client_id-scoped via RLS using public.get_my_client_id().';
COMMENT ON FUNCTION public.get_nps_score(int) IS
  'Standard NPS score over the last N days. RLS-scoped via public.get_my_client_id().';
