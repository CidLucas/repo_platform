CREATE OR REPLACE FUNCTION public.get_unified_tasks(p_client_id uuid)
RETURNS TABLE(
  task_id text,
  title text,
  domain text,
  start_date date,
  due_date date,
  status text,
  source text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    'apr_' || id::text AS task_id,
    title,
    CASE agent_slug
      WHEN 'compras' THEN 'Compras'
      WHEN 'financeiro' THEN 'Financeiro'
      WHEN 'agenda' THEN 'Agenda'
      WHEN 'documentos' THEN 'Documentos'
      WHEN 'estrategia' THEN 'Estratégia'
      WHEN 'clientes' THEN 'Clientes'
      ELSE COALESCE(agent_slug, 'Geral')
    END AS domain,
    created_at::date AS start_date,
    COALESCE(scheduled_for::date, (created_at + interval '7 days')::date) AS due_date,
    status,
    'approval' AS source
  FROM public.approval_requests
  WHERE client_id = p_client_id
    AND status = 'pending'

  UNION ALL

  SELECT
    'rtn_' || id::text AS task_id,
    name AS title,
    CASE
      WHEN name ILIKE '%compra%' OR context_section ILIKE '%compra%' THEN 'Compras'
      WHEN name ILIKE '%financ%' OR context_section ILIKE '%financ%' THEN 'Financeiro'
      WHEN name ILIKE '%agenda%' OR context_section ILIKE '%agenda%' THEN 'Agenda'
      WHEN name ILIKE '%doc%' OR context_section ILIKE '%doc%' THEN 'Documentos'
      WHEN name ILIKE '%estrat%' OR context_section ILIKE '%estrat%' THEN 'Estratégia'
      WHEN name ILIKE '%client%' OR context_section ILIKE '%client%' THEN 'Clientes'
      ELSE 'Geral'
    END AS domain,
    COALESCE(last_run_at::date, CURRENT_DATE) AS start_date,
    next_run_at::date AS due_date,
    CASE WHEN is_active THEN 'active' ELSE 'paused' END AS status,
    'routine' AS source
  FROM public.client_routines
  WHERE client_id = p_client_id
    AND is_active = true
    AND next_run_at IS NOT NULL

  ORDER BY start_date ASC NULLS LAST;
END;
$$;
