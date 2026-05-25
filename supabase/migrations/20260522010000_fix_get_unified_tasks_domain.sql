CREATE OR REPLACE FUNCTION public.get_unified_tasks(p_client_id uuid)
RETURNS TABLE(task_id text, title text, domain text, start_date date, due_date date, status text, source text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $$
BEGIN
  RETURN QUERY
  SELECT * FROM (
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
      'approval'::text                 AS source
    FROM public.approval_requests ar
    WHERE ar.client_id = p_client_id AND ar.status = 'pending'

    UNION ALL

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
      COALESCE(cr.last_run_at::date, CURRENT_DATE),
      COALESCE(cr.last_run_at::date, CURRENT_DATE) + 7,
      CASE WHEN cr.active THEN 'active' ELSE 'paused' END,
      'routine'::text
    FROM public.client_routines cr
    LEFT JOIN public.cross_agent_routines car ON car.id = cr.routine_id
    WHERE cr.client_id = p_client_id AND cr.active = true
  ) t
  ORDER BY t.start_date ASC NULLS LAST;
END;
$$;

COMMENT ON FUNCTION public.get_unified_tasks(uuid) IS
  'Returns unified tasks for Gantt. Domain mapped via cross_agent_routines.room (home→Estratégia). Fixed 2026-05-22.';
