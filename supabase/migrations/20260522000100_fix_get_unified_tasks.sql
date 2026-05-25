-- Fix get_unified_tasks v2:
-- 1. title ambiguity fixed (ar.title alias)
-- 2. is_active → active, next_run_at removed
-- 3. context_section removed (doesn't exist)
-- 4. client_routines.name is empty → JOIN cross_agent_routines for catalog name
-- 5. Domain inference uses catalog name (car.name) as fallback

DROP FUNCTION IF EXISTS public.get_unified_tasks(uuid);

CREATE FUNCTION public.get_unified_tasks(p_client_id uuid)
RETURNS TABLE(task_id text, title text, domain text, start_date date, due_date date, status text, source text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
BEGIN
  RETURN QUERY
  SELECT
    'apr_' || ar.id::text AS task_id,
    ar.title AS title,
    CASE ar.agent_slug
      WHEN 'compras'     THEN 'Compras'
      WHEN 'financeiro'  THEN 'Financeiro'
      WHEN 'agenda'      THEN 'Agenda'
      WHEN 'documentos'  THEN 'Documentos'
      WHEN 'estrategia'  THEN 'Estratégia'
      WHEN 'clientes'    THEN 'Clientes'
      ELSE COALESCE(ar.agent_slug, 'Geral')
    END AS domain,
    ar.created_at::date AS start_date,
    COALESCE(ar.scheduled_for::date, (ar.created_at + interval '7 days')::date) AS due_date,
    ar.status AS status,
    'approval' AS source
  FROM public.approval_requests ar
  WHERE ar.client_id = p_client_id
    AND ar.status = 'pending'

  UNION ALL

  SELECT
    'rtn_' || cr.id::text AS task_id,
    COALESCE(NULLIF(cr.name, ''), car.name, cr.routine_id) AS title,
    CASE
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%compra%'  THEN 'Compras'
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%financ%'  THEN 'Financeiro'
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%agenda%'  THEN 'Agenda'
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%doc%'     THEN 'Documentos'
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%estrat%'  THEN 'Estratégia'
      WHEN COALESCE(NULLIF(cr.name,''), car.name,'') ILIKE '%client%'  THEN 'Clientes'
      ELSE 'Geral'
    END AS domain,
    COALESCE(cr.last_run_at::date, CURRENT_DATE) AS start_date,
    COALESCE(cr.last_run_at::date, CURRENT_DATE) + 7 AS due_date,
    CASE WHEN cr.active THEN 'active' ELSE 'paused' END AS status,
    'routine' AS source
  FROM public.client_routines cr
  LEFT JOIN public.cross_agent_routines car ON car.id = cr.routine_id
  WHERE cr.client_id = p_client_id
    AND cr.active = true

  ORDER BY start_date ASC NULLS LAST;
END;
$$;
