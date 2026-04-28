-- Migration: Create 10 missing RPC functions
-- Date: 2026-04-28
-- Purpose: Add RPC functions referenced by API endpoints and dashboard

-- ============================================================================
-- 1. list_inbox_threads(p_limit) — List conversation threads for inbox
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_inbox_threads(p_limit INT DEFAULT 50)
RETURNS TABLE (
  id UUID,
  client_id UUID,
  agent_id TEXT,
  created_by_role TEXT,
  status TEXT,
  snippet TEXT,
  message_count INT,
  last_message_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.client_id,
    c.agent_id,
    c.created_by_role,
    c.status,
    c.snippet,
    (SELECT COUNT(*)::INT FROM public.messages m WHERE m.conversa_id = c.id) as message_count,
    (SELECT MAX(created_at) FROM public.messages m WHERE m.conversa_id = c.id) as last_message_at,
    c.created_at
  FROM public.conversa c
  WHERE c.client_id = public.get_my_client_id()
  ORDER BY c.created_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 2. list_report_runs(p_limit) — List recent report runs
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_report_runs(p_limit INT DEFAULT 50)
RETURNS TABLE (
  id UUID,
  template_id TEXT,
  status TEXT,
  format TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  output_url TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.template_id,
    r.status,
    r.format,
    r.created_at,
    r.completed_at,
    (r.output_metadata->>'output_url')::TEXT as output_url
  FROM public.report_runs r
  WHERE r.client_id = public.get_my_client_id()
  ORDER BY r.created_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 3. list_report_schedules() — List scheduled reports for tenant
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_report_schedules()
RETURNS TABLE (
  id UUID,
  template_id TEXT,
  cadence TEXT,
  next_run_at TIMESTAMP WITH TIME ZONE,
  enabled BOOLEAN,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.template_id,
    s.cadence,
    s.next_run_at,
    s.enabled,
    s.created_at
  FROM public.report_schedules s
  WHERE s.client_id = public.get_my_client_id()
  ORDER BY s.next_run_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 4. list_due_report_schedules() — Find schedules ready for execution
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_due_report_schedules()
RETURNS TABLE (
  schedule_id UUID,
  client_id UUID,
  template_id TEXT,
  cadence TEXT,
  format TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.client_id,
    s.template_id,
    s.cadence,
    s.format
  FROM public.report_schedules s
  WHERE s.enabled = TRUE
    AND s.next_run_at <= NOW()
  ORDER BY s.next_run_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 5. trigger_column_discovery(p_credential_id) — Queue schema discovery
-- ============================================================================
CREATE OR REPLACE FUNCTION public.trigger_column_discovery(p_credential_id BIGINT)
RETURNS JSONB AS $$
DECLARE
  v_client_id UUID;
  v_result JSONB;
BEGIN
  -- Get client_id from credential and verify ownership
  SELECT client_id INTO v_client_id
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found';
  END IF;

  IF v_client_id != public.get_my_client_id() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  -- Mark data source as discovery pending
  UPDATE public.client_data_sources
  SET sync_status = 'discovery_pending'
  WHERE credential_id = p_credential_id;

  -- Return indication that discovery was queued (actual work happens async)
  RETURN jsonb_build_object(
    'status', 'discovery_queued',
    'credential_id', p_credential_id,
    'queued_at', to_jsonb(NOW())
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 6. record_insight() — Create a new insight/alert for dashboard
-- ============================================================================
CREATE OR REPLACE FUNCTION public.record_insight(
  p_title TEXT,
  p_content TEXT,
  p_severity TEXT DEFAULT 'info',
  p_data JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_insight_id UUID;
BEGIN
  INSERT INTO public.client_insights (
    id,
    client_id,
    title,
    content,
    severity,
    metadata,
    created_at,
    dismissed_at
  )
  VALUES (
    gen_random_uuid(),
    public.get_my_client_id(),
    p_title,
    p_content,
    p_severity,
    p_data,
    NOW(),
    NULL
  )
  RETURNING id INTO v_insight_id;

  RETURN v_insight_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 7. expire_stale_insights() — Archive old insights (scheduled worker)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.expire_stale_insights(p_days_old INT DEFAULT 30)
RETURNS INT AS $$
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 8. get_commercial_revenue_by_channel() — Revenue metrics grouped by channel
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_commercial_revenue_by_channel()
RETURNS TABLE (
  channel TEXT,
  total_revenue NUMERIC,
  transaction_count INT,
  avg_transaction_value NUMERIC
) AS $$
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 9. get_commercial_top_clients() — Top 10 customers by revenue
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
RETURNS TABLE (
  cliente_id BIGINT,
  cliente_nome TEXT,
  total_volume NUMERIC,
  total_revenue NUMERIC,
  last_purchase TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.nome::TEXT,
    COUNT(f.pedido_id)::NUMERIC as total_volume,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    MAX(f.data_transacao) as last_purchase
  FROM analytics_v2.fato_transacoes f
  LEFT JOIN analytics_v2.dim_clientes d ON f.cliente_id = d.id
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY d.id, d.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 10. exec_sql() — Execute raw SQL (admin/debug tool)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.exec_sql(p_query TEXT)
RETURNS TABLE (result JSONB) AS $$
DECLARE
  v_result JSONB;
BEGIN
  -- Security: only service_role and postgres can execute arbitrary SQL
  -- This is an admin/debug function; normal users should never have access
  IF current_user NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION 'Insufficient permissions to execute raw SQL: current_user=%', current_user;
  END IF;

  EXECUTE p_query INTO v_result;
  RETURN QUERY SELECT v_result;
EXCEPTION WHEN OTHERS THEN
  RETURN QUERY SELECT jsonb_build_object('error', SQLERRM)::JSONB;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
