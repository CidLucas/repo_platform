-- ============================================================================
-- Sprint 4 / D2 — Dedupe de artefatos side-effectful
-- ============================================================================
-- Problema: se uma rotina é redispachada (retry, redispatch_after_approval, ou
--   bug no executor), passos do tipo "artifact" que enviam email/whatsapp/doc
--   podem ser executados duas vezes — entregando duplicidade real ao cliente.
--
-- Solução: tabela de auditoria `artifact_log` com UNIQUE(execution_id, step_id).
--   O executor faz INSERT-claim com ON CONFLICT DO NOTHING ANTES da entrega.
--   - Insert sucedido (1 row)  → primeira tentativa, prossegue com delivery
--   - Insert ignorado  (0 rows) → já foi entregue, skip
--   Após entrega bem-sucedida, faz UPDATE status='sent'+sent_at; falha →
--   status='failed', permitindo reprocessamento manual via DELETE da row.
--
-- Tipos side-effectful protegidos (definido no executor, não no schema):
--   email, whatsapp, document
-- NÃO protegidos (idempotentes / leitura): alert, approval (já tem dedupe
--   próprio via execution_id no payload).
--
-- NÃO APLICAR AUTOMATICAMENTE.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.artifact_log (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id   uuid NOT NULL
                 REFERENCES public.client_routine_executions(id)
                 ON DELETE CASCADE,
  step_id        text NOT NULL,
  client_id      uuid NOT NULL
                 REFERENCES public.clientes_blu(client_id)
                 ON DELETE CASCADE,
  artifact_type  text NOT NULL,             -- 'email' | 'whatsapp' | 'document'
  function_name  text NOT NULL,             -- 'channels.send_email_batch' etc.
  status         text NOT NULL DEFAULT 'claimed',  -- claimed|sent|failed
  outputs        jsonb,                     -- payload de retorno do artifact
  error          text,
  claimed_at     timestamptz NOT NULL DEFAULT now(),
  sent_at        timestamptz,
  CONSTRAINT artifact_log_dedupe_uq UNIQUE (execution_id, step_id),
  CONSTRAINT artifact_log_status_chk CHECK (
    status IN ('claimed','sent','failed')
  )
);

COMMENT ON TABLE public.artifact_log IS
  'Sprint 4/D2 — Dedupe de artefatos side-effectful. UNIQUE(execution_id, step_id) '
  'impede reentrega de email/whatsapp/document em retries/redispatches.';

CREATE INDEX IF NOT EXISTS idx_artifact_log_client_type
  ON public.artifact_log (client_id, artifact_type, claimed_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_log_failed
  ON public.artifact_log (claimed_at DESC) WHERE status = 'failed';

-- RLS: cliente só vê seus próprios artefatos (consistente com approval_requests)
ALTER TABLE public.artifact_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "own client" ON public.artifact_log;
CREATE POLICY "own client"
  ON public.artifact_log
  TO authenticated
  USING (client_id = get_my_client_id())
  WITH CHECK (client_id = get_my_client_id());

-- Service role (executor) usa bypass via SUPABASE_SERVICE_KEY, não precisa policy.

-- ============================================================================
-- Verificação pós-apply:
--   SELECT count(*) FROM artifact_log;  -- 0
--   \d artifact_log
--   SELECT polname FROM pg_policy WHERE polrelid='artifact_log'::regclass;
-- ============================================================================
