
-- Migration: 20260522020100_get_unified_tasks_schedule_cron.sql
-- Adiciona schedule_cron ao shape de get_unified_tasks e corrige datas de rotinas cron
-- start_date = CURRENT_DATE (próxima estimada), due_date = NULL (pin, sem barra)

DROP FUNCTION IF EXISTS public.get_unified_tasks(uuid);

CREATE OR REPLACE FUNCTION public.get_unified_tasks(p_client_id uuid)
  RETURNS TABLE(
    task_id      text,
    title        text,
    domain       text,
    start_date   date,
    due_date     date,
    status       text,
    source       text,
    schedule_cron text
  )
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
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

COMMENT ON FUNCTION public.get_unified_tasks(uuid) IS 
  'Retorna tarefas unificadas (approvals + routines) para o Gantt. 
   schedule_cron: expressão cron para rotinas periódicas (o frontend gera pins múltiplos).
   due_date=null em rotinas indica pin pontual (sem barra de duração).
   Atualizado: 2026-05-22 — adicionado schedule_cron, corrigido shape de rotinas.';
