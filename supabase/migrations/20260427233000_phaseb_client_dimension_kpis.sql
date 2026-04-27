-- Migration: Phase B — Onboarding core KPI selection
-- Date: 2026-04-27
--
-- Adds per-tenant KPI slot selection (max 5 per dimension), plus RPCs used by
-- onboarding/package proposal and Mission Control.

BEGIN;

SET LOCAL statement_timeout = '5min';
SET LOCAL lock_timeout = '1min';

-- 1) Extend catalog with deterministic defaults used when website intel fails.
ALTER TABLE public.kpi_catalog
  ADD COLUMN IF NOT EXISTS is_default boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS default_dimension_rank integer;

CREATE INDEX IF NOT EXISTS idx_kpi_catalog_defaults
  ON public.kpi_catalog (dimension, is_default, default_dimension_rank);

-- Fill rank only when missing to keep manual curation stable.
WITH ranked AS (
  SELECT
    slug,
    row_number() OVER (PARTITION BY dimension ORDER BY sort_order, slug) AS rn
  FROM public.kpi_catalog
)
UPDATE public.kpi_catalog k
SET
  default_dimension_rank = COALESCE(k.default_dimension_rank, r.rn),
  is_default = CASE
    WHEN k.is_default THEN true
    WHEN COALESCE(k.default_dimension_rank, r.rn) <= 5 THEN true
    ELSE false
  END
FROM ranked r
WHERE r.slug = k.slug;

-- 2) Per-tenant selected KPI slots by dimension (0..4).
CREATE TABLE IF NOT EXISTS public.client_dimension_kpis (
  client_id uuid NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  dimension text NOT NULL CHECK (dimension IN ('finance','commercial','inventory','supply','marketing','admin')),
  slot_index integer NOT NULL CHECK (slot_index BETWEEN 0 AND 4),
  kpi_slug text NOT NULL REFERENCES public.kpi_catalog(slug),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (client_id, dimension, slot_index)
);

CREATE INDEX IF NOT EXISTS idx_client_dimension_kpis_client
  ON public.client_dimension_kpis (client_id, dimension);

CREATE INDEX IF NOT EXISTS idx_client_dimension_kpis_slug
  ON public.client_dimension_kpis (kpi_slug);

CREATE OR REPLACE FUNCTION public._set_updated_at_client_dimension_kpis()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_client_dimension_kpis_updated_at ON public.client_dimension_kpis;
CREATE TRIGGER trg_client_dimension_kpis_updated_at
BEFORE UPDATE ON public.client_dimension_kpis
FOR EACH ROW EXECUTE FUNCTION public._set_updated_at_client_dimension_kpis();

ALTER TABLE public.client_dimension_kpis ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS client_dimension_kpis_select ON public.client_dimension_kpis;
CREATE POLICY client_dimension_kpis_select ON public.client_dimension_kpis
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_dimension_kpis_insert ON public.client_dimension_kpis;
CREATE POLICY client_dimension_kpis_insert ON public.client_dimension_kpis
  FOR INSERT TO authenticated
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_dimension_kpis_update ON public.client_dimension_kpis;
CREATE POLICY client_dimension_kpis_update ON public.client_dimension_kpis
  FOR UPDATE TO authenticated
  USING (client_id::text = public.get_my_client_id())
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_dimension_kpis_delete ON public.client_dimension_kpis;
CREATE POLICY client_dimension_kpis_delete ON public.client_dimension_kpis
  FOR DELETE TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_dimension_kpis_service_role ON public.client_dimension_kpis;
CREATE POLICY client_dimension_kpis_service_role ON public.client_dimension_kpis
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- 3) Atomic replace for one dimension.
CREATE OR REPLACE FUNCTION public.set_client_dimension_kpis(
  p_dimension text,
  p_slugs text[]
)
RETURNS TABLE (
  dimension text,
  slot_index integer,
  kpi_slug text
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_client_id uuid;
  v_len integer;
  v_slug text;
  v_slot integer;
  v_kpi_dimension text;
BEGIN
  v_client_id := public.get_my_client_id()::uuid;
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant bound to this session';
  END IF;

  IF p_dimension IS NULL OR p_dimension NOT IN ('finance','commercial','inventory','supply','marketing','admin') THEN
    RAISE EXCEPTION 'Invalid dimension: %', p_dimension;
  END IF;

  v_len := COALESCE(array_length(p_slugs, 1), 0);
  IF v_len > 5 THEN
    RAISE EXCEPTION 'At most 5 slugs are allowed per dimension';
  END IF;

  DELETE FROM public.client_dimension_kpis
  WHERE client_id = v_client_id
    AND dimension = p_dimension;

  IF v_len = 0 THEN
    RETURN;
  END IF;

  FOR v_slot IN 1..v_len LOOP
    v_slug := p_slugs[v_slot];
    IF v_slug IS NULL OR btrim(v_slug) = '' THEN
      RAISE EXCEPTION 'KPI slug at slot % is empty', v_slot - 1;
    END IF;

    SELECT k.dimension
    INTO v_kpi_dimension
    FROM public.kpi_catalog k
    WHERE k.slug = v_slug;

    IF v_kpi_dimension IS NULL THEN
      RAISE EXCEPTION 'Unknown KPI slug: %', v_slug;
    END IF;

    IF v_kpi_dimension <> p_dimension THEN
      RAISE EXCEPTION 'KPI slug % belongs to %, expected %', v_slug, v_kpi_dimension, p_dimension;
    END IF;

    INSERT INTO public.client_dimension_kpis (client_id, dimension, slot_index, kpi_slug)
    VALUES (v_client_id, p_dimension, v_slot - 1, v_slug);
  END LOOP;

  RETURN QUERY
  SELECT c.dimension, c.slot_index, c.kpi_slug
  FROM public.client_dimension_kpis c
  WHERE c.client_id = v_client_id
    AND c.dimension = p_dimension
  ORDER BY c.slot_index;
END;
$$;

COMMENT ON FUNCTION public.set_client_dimension_kpis(text, text[]) IS
  'Replaces the current tenant KPI slots (0..4) for one dimension atomically. Validates slug existence and dimension ownership.';

GRANT EXECUTE ON FUNCTION public.set_client_dimension_kpis(text, text[]) TO authenticated;

-- 4) Read current dashboard KPI set. If a dimension has no selection,
-- returns up to 5 defaults from kpi_catalog.is_default ordered by default rank.
CREATE OR REPLACE FUNCTION public.get_my_dashboard_kpis()
RETURNS TABLE (
  dimension text,
  slot_index integer,
  slug text,
  label text,
  unit text,
  formula text,
  data_status text,
  tier_required text,
  is_enabled boolean
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  WITH me AS (
    SELECT public.get_my_client_id()::uuid AS client_id
  ),
  dims AS (
    SELECT unnest(ARRAY['finance','commercial','inventory','supply','marketing']::text[]) AS dimension
  ),
  selected AS (
    SELECT c.dimension, c.slot_index, c.kpi_slug AS slug
    FROM public.client_dimension_kpis c
    JOIN me ON c.client_id = me.client_id
  ),
  defaults AS (
    SELECT
      k.dimension,
      (row_number() OVER (PARTITION BY k.dimension ORDER BY COALESCE(k.default_dimension_rank, 9999), k.sort_order, k.slug) - 1)::integer AS slot_index,
      k.slug
    FROM public.kpi_catalog k
    WHERE k.is_default = true
      AND k.dimension IN (SELECT dimension FROM dims)
  ),
  fallback AS (
    SELECT d.dimension, d.slot_index, d.slug
    FROM defaults d
    WHERE d.slot_index BETWEEN 0 AND 4
      AND NOT EXISTS (
        SELECT 1 FROM selected s WHERE s.dimension = d.dimension
      )
  ),
  unioned AS (
    SELECT * FROM selected
    UNION ALL
    SELECT * FROM fallback
  )
  SELECT
    u.dimension,
    u.slot_index,
    k.slug,
    k.label,
    k.unit,
    k.formula,
    k.data_status,
    k.tier_required,
    (
      public.kpi_tier_rank(k.tier_required)
      <= COALESCE(
        (SELECT public.kpi_tier_rank(cv.tier)
         FROM public.clientes_vizu cv
         JOIN me ON cv.client_id = me.client_id
         LIMIT 1),
        public.kpi_tier_rank('BASIC')
      )
      AND k.data_status IN ('live', 'proxy')
    ) AS is_enabled
  FROM unioned u
  JOIN public.kpi_catalog k ON k.slug = u.slug
  ORDER BY u.dimension, u.slot_index;
$$;

COMMENT ON FUNCTION public.get_my_dashboard_kpis() IS
  'Returns current tenant dashboard KPI slots by dimension, with fallback to kpi_catalog defaults when no explicit selection exists.';

GRANT EXECUTE ON FUNCTION public.get_my_dashboard_kpis() TO authenticated;

COMMIT;
