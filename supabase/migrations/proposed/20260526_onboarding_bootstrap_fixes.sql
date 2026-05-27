-- Migration: 20260526_onboarding_bootstrap_fixes.sql
-- Context: Investigação do trava "Iniciando seu bureau" (handoff 20260525_onboarding_trace_session.md)
--
-- Dois fixes:
--
-- 1) DROP triggers de _trace.capture() DUPLICADAS em 11 tabelas.
--    Cada tabela tinha `_trace_capture` (genérica) + `trace_<tabela>` (específica)
--    apontando para a MESMA função. Resultado: cada INSERT/UPDATE/DELETE gerava
--    2 linhas em _trace.onboarding_events. Não era a causa única da trava de 92s
--    mas dobrava a I/O do bootstrap. Mantemos apenas as `_trace_capture` genéricas.
--
-- 2) FIX bootstrap_knowledge_from_onboarding(uuid):
--    O UPDATE final fazia `cds.client_id = p_client_id::text` mas
--    public.client_data_sources.client_id é uuid (não text). A função inteira
--    abortava com `operator does not exist: uuid = text` em ~250ms. O edge
--    function onboarding-bootstrap chama essa RPC dentro de try/catch e apenas
--    loga warn, então o bug ficou silencioso desde sempre — nenhum cliente teve
--    docs upgrados para 'complete' via essa via.

-- ─────────────────────────────────────────────────────────────────────────────
-- Parte 1: drop triggers _trace duplicadas
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trace_clientes_blu                ON public.clientes_blu;
DROP TRIGGER IF EXISTS trace_bigquery_servers            ON public.bigquery_servers;
DROP TRIGGER IF EXISTS trace_bigquery_foreign_tables     ON public.bigquery_foreign_tables;
DROP TRIGGER IF EXISTS trace_client_data_sources         ON public.client_data_sources;
DROP TRIGGER IF EXISTS trace_integration_configs         ON public.integration_configs;
DROP TRIGGER IF EXISTS trace_integration_tokens          ON public.integration_tokens;
DROP TRIGGER IF EXISTS trace_client_enabled_agents       ON public.client_enabled_agents;
DROP TRIGGER IF EXISTS trace_client_routines             ON public.client_routines;
DROP TRIGGER IF EXISTS trace_client_routine_executions   ON public.client_routine_executions;

-- ─────────────────────────────────────────────────────────────────────────────
-- Parte 2: fix bootstrap_knowledge_from_onboarding
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bootstrap_knowledge_from_onboarding(p_client_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'vector_db'
AS $function$
DECLARE
  v_cp        jsonb;
  v_ts        jsonb;
  v_seeded    int := 0;
BEGIN
  SELECT company_profile, team_structure
    INTO v_cp, v_ts
    FROM public.clientes_blu
   WHERE client_id = p_client_id;

  IF (v_cp->>'legal_name') IS NOT NULL OR (v_cp->>'industry') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF (v_cp->>'industry') IS NOT NULL AND (v_cp->>'employee_count_range') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'perfil_empresarial', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF EXISTS (
    SELECT 1 FROM vector_db.documents
     WHERE client_id = p_client_id AND source = 'onboarding.website_context'
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'posicionamento', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF jsonb_array_length(COALESCE(v_ts->'key_contacts', '[]'::jsonb)) > 0 THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'organograma', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny','shopify','vtex','nuvemshop')
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'historico_pedidos',  'partial', 'erp'),
      (p_client_id, 'catalogo_produtos',  'partial', 'erp'),
      (p_client_id, 'fluxo_caixa_diario', 'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 3;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny')
  ) THEN
    INSERT INTO public.client_knowledge_documents (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'cadastro_fornecedores', 'partial', 'erp'),
      (p_client_id, 'controle_inventario',   'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 2;
  END IF;

  -- FIX (Mai/2026): client_data_sources.client_id é uuid (não text).
  -- Cast ::text quebrava o UPDATE com `operator does not exist: uuid = text`.
  UPDATE public.client_knowledge_documents ckd
     SET status     = 'complete',
         source     = 'erp_synced',
         updated_at = now()
    FROM public.client_data_sources cds
   WHERE cds.client_id = p_client_id
     AND cds.sync_status IN ('ready','success')
     AND ckd.client_id = p_client_id
     AND ckd.document_type_id = CASE cds.resource_type
           WHEN 'orders'       THEN 'historico_pedidos'
           WHEN 'pedidos'      THEN 'historico_pedidos'
           WHEN 'products'     THEN 'catalogo_produtos'
           WHEN 'inventory'    THEN 'controle_inventario'
           WHEN 'estoque'      THEN 'controle_inventario'
           WHEN 'customers'    THEN 'ficha_cliente'
           WHEN 'clientes'     THEN 'ficha_cliente'
           WHEN 'fornecedores' THEN 'cadastro_fornecedores'
           ELSE NULL
         END
     AND ckd.status != 'complete';

  RETURN jsonb_build_object('client_id', p_client_id, 'docs_seeded', v_seeded);
END;
$function$;
