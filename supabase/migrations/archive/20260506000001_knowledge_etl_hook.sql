-- migration: 20260506000001_knowledge_etl_hook
-- Purpose: DB trigger that upserts client_knowledge_documents when an ETL
--          sync job completes, mapping resource_type → document_type_id.
--
-- This is the Phase 1.3 hook for the Knowledge Domain Mind Map.
-- The edge function run-sync-etl only queues the job; the actual ETL runs in
-- pg_cron via analytics_v2.run_etl_job(). The trigger fires when the job row
-- transitions to status = 'completed', giving us the resource_type set by the
-- ETL engine.

-- ─────────────────────────────────────────────────────────────────────────────
-- Helper: map resource_type string → knowledge document_type_id
-- Returns NULL for unrecognised resource types (skip, don't guess).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.etl_resource_to_doc_type(p_resource_type text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = analytics_v2, public
AS $$
  SELECT CASE lower(trim(p_resource_type))
    WHEN 'orders'           THEN 'historico_pedidos'
    WHEN 'pedidos'          THEN 'historico_pedidos'
    WHEN 'products'         THEN 'catalogo_produtos'
    WHEN 'produtos'         THEN 'catalogo_produtos'
    WHEN 'inventory'        THEN 'controle_inventario'
    WHEN 'estoque'          THEN 'controle_inventario'
    WHEN 'customers'        THEN 'ficha_cliente'
    WHEN 'clientes'         THEN 'ficha_cliente'
    WHEN 'fornecedores'     THEN 'cadastro_fornecedores'
    WHEN 'suppliers'        THEN 'cadastro_fornecedores'
    WHEN 'financial'        THEN 'dre_mensal'
    WHEN 'dre'              THEN 'dre_mensal'
    WHEN 'fluxo_caixa'      THEN 'fluxo_caixa_diario'
    WHEN 'cashflow'         THEN 'fluxo_caixa_diario'
    ELSE NULL
  END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger function: runs AFTER UPDATE on analytics_v2.reg_jobs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.on_etl_job_completed()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
  v_doc_type_id text;
BEGIN
  -- Only act when status transitions to 'completed' for a bigquery_sync job
  IF NEW.status <> 'completed' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = 'completed' THEN
    RETURN NEW;  -- idempotent: already processed
  END IF;
  IF NEW.job_type <> 'bigquery_sync' THEN
    RETURN NEW;
  END IF;
  IF NEW.client_id IS NULL OR NEW.resource_type IS NULL THEN
    RETURN NEW;
  END IF;

  v_doc_type_id := analytics_v2.etl_resource_to_doc_type(NEW.resource_type);

  IF v_doc_type_id IS NOT NULL THEN
    -- Upsert: promote to 'complete' if we had a partial, or insert fresh.
    -- Never downgrade an existing 'complete' row to 'partial'.
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (NEW.client_id, v_doc_type_id, 'complete', 'erp_sync', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'erp_sync',
          updated_at = now()
      WHERE client_knowledge_documents.status <> 'complete';
  END IF;

  RETURN NEW;
EXCEPTION
  WHEN others THEN
    -- Best-effort: never let the trigger break the ETL job update
    RAISE WARNING '[knowledge] ETL hook failed for job %: %', NEW.job_id, SQLERRM;
    RETURN NEW;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Attach trigger to reg_jobs
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_knowledge_on_etl_completed ON analytics_v2.reg_jobs;

CREATE TRIGGER trg_knowledge_on_etl_completed
  AFTER UPDATE OF status ON analytics_v2.reg_jobs
  FOR EACH ROW
  EXECUTE FUNCTION analytics_v2.on_etl_job_completed();
