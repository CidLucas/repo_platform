-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 · Arquitetura C — Room Monitors
--
-- BIB-MON-01 · BibliotecaMonitor (built-in, cron diário 06h00)
--
-- Responsabilidades:
--   - Auditar documentos sem embedding ou com status pendente
--   - Gerar sumário do conhecimento disponível na base do cliente
--   - Identificar gaps: perguntas frequentes sem cobertura documental
--   - Submeter documentos novos para aprovação HITL antes de indexar
--   - Gravar estado na dimension_state['biblioteca'] TTL 12h
--
-- Steps:
--   1. biblioteca.get_document_status   → contagem por status (pending/indexed/rejected)
--   2. biblioteca.get_recent_uploads    → documentos novos (últimas 24h)
--   3. biblioteca.get_unanswered_queries → queries RAG sem resultado satisfatório
--   4. skill: biblioteca (rag_query)    → sumário do conhecimento disponível
--   5. biblioteca.submit_pending_for_hitl → dispara HITL para docs sem aprovação
--   6. memory.write_dimension_state    → grava dimension_state['biblioteca'] TTL 12h
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'biblioteca_monitor',
  'Monitor de Biblioteca Diário',
  'biblioteca',
  'biblioteca',
  'cron',
  '{"expression": "0 6 * * *"}'::jsonb,
  '[
    {"key": "hours_lookback",  "label": "Horas para buscar uploads recentes", "type": "number", "default": 24,  "required": false},
    {"key": "hitl_auto",       "label": "Submeter docs novos para HITL automaticamente", "type": "boolean", "default": true, "required": false},
    {"key": "ttl_hours",       "label": "TTL do estado em horas",               "type": "number", "default": 12, "required": false},
    {"key": "min_gap_queries", "label": "Mínimo de queries sem resposta para alertar", "type": "number", "default": 3, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_doc_status",
      "step": 1,
      "type": "function",
      "function": "biblioteca.get_document_status",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_recent_uploads",
      "step": 2,
      "type": "function",
      "function": "biblioteca.get_recent_uploads",
      "inputs": {"hours_lookback": "{{hours_lookback}}"},
      "on_failure": "continue"
    },
    {
      "id": "get_unanswered_queries",
      "step": 3,
      "type": "function",
      "function": "biblioteca.get_unanswered_queries",
      "inputs": {"min_count": "{{min_gap_queries}}"},
      "on_failure": "continue"
    },
    {
      "id": "rag_summary",
      "step": 4,
      "type": "skill",
      "skill_slug": "biblioteca",
      "task_template": "Você é o BibliotecaMonitor da {{nome_empresa}}. Analise o estado atual da base de conhecimento e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nDocumentos por status: {{doc_status}}\nUploads recentes ({{hours_lookback}}h): {{recent_count}} documento(s)\nQueries sem cobertura adequada: {{unanswered_count}}\n\nGere um parágrafo conciso com: cobertura atual da base, documentos novos aguardando indexação, e gaps de conhecimento identificados (perguntas sem resposta satisfatória). Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.",
      "outputs": {"memory_summary": "resumo da biblioteca para dimension_state"},
      "on_failure": "continue"
    },
    {
      "id": "submit_hitl",
      "step": 5,
      "type": "function",
      "function": "biblioteca.submit_pending_for_hitl",
      "inputs": {
        "auto_submit": "{{hitl_auto}}",
        "document_ids": "{{pending_document_ids}}"
      },
      "on_failure": "continue"
    },
    {
      "id": "write_memory",
      "step": 6,
      "type": "function",
      "function": "memory.write_dimension_state",
      "inputs": {
        "dimension": "biblioteca",
        "summary":   "{{memory_summary}}",
        "structured": {
          "doc_status":        "{{doc_status}}",
          "recent_uploads":    "{{recent_count}}",
          "unanswered_queries": "{{unanswered_count}}",
          "pending_hitl":      "{{pending_hitl_count}}"
        },
        "ttl_hours": "{{ttl_hours}}"
      },
      "on_failure": "continue"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO UPDATE SET
  name           = EXCLUDED.name,
  steps          = EXCLUDED.steps,
  config_schema  = EXCLUDED.config_schema,
  trigger_config = EXCLUDED.trigger_config;


-- ─────────────────────────────────────────────────────────────────────────────
-- Funções de suporte ao BibliotecaMonitor
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Status dos documentos da base (por status de indexação)
CREATE OR REPLACE FUNCTION biblioteca.get_document_status(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = vector_db, public
AS $$
DECLARE
  v_result jsonb;
BEGIN
  SELECT jsonb_build_object(
    'indexed',  COUNT(*) FILTER (WHERE status = 'indexed'),
    'pending',  COUNT(*) FILTER (WHERE status = 'pending'  OR status IS NULL),
    'failed',   COUNT(*) FILTER (WHERE status = 'failed'),
    'rejected', COUNT(*) FILTER (WHERE status = 'rejected'),
    'total',    COUNT(*)
  )
  INTO v_result
  FROM vector_db.documents
  WHERE client_id = p_client_id;

  RETURN COALESCE(v_result, '{}'::jsonb);
END;
$$;

-- 2. Uploads recentes (últimas N horas)
CREATE OR REPLACE FUNCTION biblioteca.get_recent_uploads(
  p_client_id    uuid,
  p_hours_lookback int DEFAULT 24
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = vector_db, public
AS $$
DECLARE
  v_docs  jsonb;
  v_count int;
BEGIN
  SELECT
    COUNT(*),
    jsonb_agg(jsonb_build_object(
      'id',        id,
      'file_name', file_name,
      'file_type', file_type,
      'status',    COALESCE(status, 'pending'),
      'created_at', created_at
    ) ORDER BY created_at DESC)
  INTO v_count, v_docs
  FROM vector_db.documents
  WHERE client_id = p_client_id
    AND created_at >= NOW() - (p_hours_lookback || ' hours')::interval;

  RETURN jsonb_build_object(
    'count',     COALESCE(v_count, 0),
    'documents', COALESCE(v_docs, '[]'::jsonb)
  );
END;
$$;

-- 3. Queries sem cobertura (baixo score de similaridade nos últimos 7 dias)
--    Lê de rag_query_log se existir; retorna vazio se tabela não existir (soft fail)
CREATE OR REPLACE FUNCTION biblioteca.get_unanswered_queries(
  p_client_id uuid,
  p_min_count int DEFAULT 3
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_result jsonb := '{"count": 0, "queries": []}'::jsonb;
BEGIN
  -- Tenta ler de rag_query_log; ignora se a tabela não existir
  BEGIN
    SELECT jsonb_build_object(
      'count',   COUNT(*),
      'queries', jsonb_agg(query_text ORDER BY created_at DESC) FILTER (WHERE query_text IS NOT NULL)
    )
    INTO v_result
    FROM public.rag_query_log
    WHERE client_id = p_client_id
      AND max_score < 0.6
      AND created_at >= NOW() - INTERVAL '7 days'
    HAVING COUNT(*) >= p_min_count;
  EXCEPTION WHEN undefined_table THEN
    -- tabela ainda não existe; retorna vazio
    NULL;
  END;

  RETURN COALESCE(v_result, '{"count": 0, "queries": []}'::jsonb);
END;
$$;

-- 4. Submeter documentos pendentes para HITL de aprovação documental
CREATE OR REPLACE FUNCTION biblioteca.submit_pending_for_hitl(
  p_client_id   uuid,
  p_auto_submit boolean DEFAULT true,
  p_document_ids uuid[] DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = vector_db, public
AS $$
DECLARE
  v_submitted int := 0;
  v_doc       record;
  v_ids       uuid[];
BEGIN
  IF NOT p_auto_submit THEN
    RETURN jsonb_build_object('submitted', 0, 'skipped', true);
  END IF;

  -- Se IDs explícitos passados, usa eles; caso contrário pega todos pending
  IF p_document_ids IS NOT NULL AND array_length(p_document_ids, 1) > 0 THEN
    v_ids := p_document_ids;
  ELSE
    SELECT array_agg(id)
    INTO v_ids
    FROM vector_db.documents
    WHERE client_id = p_client_id
      AND (status IS NULL OR status = 'pending')
      -- Só submete se ainda não há approval pendente para este doc
      AND id NOT IN (
        SELECT (payload->>'document_id')::uuid
        FROM public.approvals
        WHERE client_id = p_client_id
          AND approval_type = 'document_indexing'
          AND status = 'pending'
          AND payload->>'document_id' IS NOT NULL
      );
  END IF;

  IF v_ids IS NULL OR array_length(v_ids, 1) = 0 THEN
    RETURN jsonb_build_object('submitted', 0, 'reason', 'no_pending_docs');
  END IF;

  -- Cria approval para cada documento pendente
  FOR v_doc IN
    SELECT id, file_name, file_type
    FROM vector_db.documents
    WHERE id = ANY(v_ids)
      AND client_id = p_client_id
  LOOP
    INSERT INTO public.approvals (
      client_id,
      approval_type,
      status,
      payload,
      created_at
    ) VALUES (
      p_client_id,
      'document_indexing',
      'pending',
      jsonb_build_object(
        'document_id', v_doc.id,
        'file_name',   v_doc.file_name,
        'file_type',   v_doc.file_type,
        'submitted_by', 'biblioteca_monitor'
      ),
      NOW()
    )
    ON CONFLICT DO NOTHING;

    v_submitted := v_submitted + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'submitted', v_submitted,
    'document_ids', to_jsonb(v_ids)
  );
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- RLS: funções SECURITY DEFINER, sem expose de dados cross-tenant
-- Grants para service_role (chamadas de rotina via backend)
-- ─────────────────────────────────────────────────────────────────────────────

GRANT EXECUTE ON FUNCTION biblioteca.get_document_status(uuid)                          TO service_role;
GRANT EXECUTE ON FUNCTION biblioteca.get_recent_uploads(uuid, int)                      TO service_role;
GRANT EXECUTE ON FUNCTION biblioteca.get_unanswered_queries(uuid, int)                  TO service_role;
GRANT EXECUTE ON FUNCTION biblioteca.submit_pending_for_hitl(uuid, boolean, uuid[])     TO service_role;
