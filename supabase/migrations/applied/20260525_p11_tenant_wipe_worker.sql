-- ============================================================================
-- P11: Tenant Wipe Worker — async paginated client deletion
-- ============================================================================
-- Substitui DELETE direto em clientes_blu (que dispara CASCADE síncrono e
-- trava o pooler com 180k+ rows) por uma fila + worker pg_cron que deleta
-- filhas em batches keyset-paginados de 5k linhas.
--
-- Uso:
--   SELECT admin.request_client_deletion('<uuid>', 'reason text');
--
-- Observabilidade:
--   SELECT * FROM admin.v_active_wipes;
--   SELECT * FROM admin.tenant_wipe_jobs ORDER BY created_at DESC LIMIT 10;
--
-- Segurança:
--   - DELETE direto em clientes_blu permanece bloqueado por RLS para roles
--     non-superuser; o caminho oficial é a função abaixo.
--   - FKs CASCADE permanecem como defesa em profundidade.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Schema admin + tabelas
-- ----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS admin;

CREATE TABLE IF NOT EXISTS admin.tenant_wipe_jobs (
  job_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id           uuid NOT NULL,
  reason              text NOT NULL,
  requested_by        uuid,                   -- auth.uid() no momento do request
  status              text NOT NULL DEFAULT 'queued'
                      CHECK (status IN ('queued','running','completed','failed','cancelled')),
  current_table       text,                   -- ex: 'analytics_v2.fato_transacoes'
  last_pk             text,                   -- cursor keyset (PK como texto)
  rows_deleted_total  bigint NOT NULL DEFAULT 0,
  rows_total_estimate bigint,
  progress_pct        numeric(5,2) NOT NULL DEFAULT 0,
  error               text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  started_at          timestamptz,
  updated_at          timestamptz NOT NULL DEFAULT now(),
  completed_at        timestamptz
);

CREATE INDEX IF NOT EXISTS idx_tenant_wipe_jobs_status
  ON admin.tenant_wipe_jobs (status, created_at)
  WHERE status IN ('queued','running');

CREATE INDEX IF NOT EXISTS idx_tenant_wipe_jobs_client
  ON admin.tenant_wipe_jobs (client_id);

CREATE TABLE IF NOT EXISTS admin.tenant_wipe_audit (
  audit_id     bigserial PRIMARY KEY,
  job_id       uuid NOT NULL REFERENCES admin.tenant_wipe_jobs(job_id) ON DELETE CASCADE,
  table_name   text NOT NULL,
  batch_no     int NOT NULL,
  rows_deleted int NOT NULL,
  duration_ms  int NOT NULL,
  at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenant_wipe_audit_job ON admin.tenant_wipe_audit(job_id, at);

-- Coluna de soft-delete em clientes_blu (idempotente)
ALTER TABLE public.clientes_blu
  ADD COLUMN IF NOT EXISTS deletion_status text
    CHECK (deletion_status IN ('active','deleting','deleted')) DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS deletion_requested_at timestamptz;

-- ----------------------------------------------------------------------------
-- 2. Lookup de filhas (descoberta dinâmica via pg_catalog)
-- ----------------------------------------------------------------------------
-- Ordem manual de prioridade (maiores volumes primeiro). Tabelas não listadas
-- entram depois em ordem alfabética. Atualizar conforme novas tabelas surgirem.
CREATE TABLE IF NOT EXISTS admin.wipe_table_priority (
  table_fqn text PRIMARY KEY,
  priority  int NOT NULL DEFAULT 100
);

INSERT INTO admin.wipe_table_priority(table_fqn, priority) VALUES
  ('analytics_v2.fato_transacoes', 10),
  ('analytics_v2.dim_inventory',   20),
  ('analytics_v2.dim_clientes',    30),
  ('analytics_v2.dim_fornecedores',40),
  ('analytics_v2.reg_jobs',        50),
  ('vector_db.documents',          60),
  ('public.client_routine_executions', 70),
  ('public.approval_requests',     80),
  ('public.client_routines',       90),
  ('public.messages',              95),
  ('public.notifications',         96),
  ('public.conversa',              97)
ON CONFLICT (table_fqn) DO UPDATE SET priority = EXCLUDED.priority;

-- View resolvendo (schema.table, pk_column) na ordem desejada
CREATE OR REPLACE VIEW admin.v_wipe_target_tables AS
SELECT
  fk.child_schema || '.' || fk.child_table AS table_fqn,
  fk.child_schema,
  fk.child_table,
  fk.fk_column,
  fk.pk_column,
  COALESCE(p.priority, 1000) AS priority
FROM (
  SELECT DISTINCT
    nsp.nspname AS child_schema,
    cls.relname AS child_table,
    att.attname AS fk_column,
    (SELECT a.attname
       FROM pg_index i
       JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
      WHERE i.indrelid = cls.oid AND i.indisprimary
      ORDER BY array_position(i.indkey::int[], a.attnum::int)
      LIMIT 1) AS pk_column
  FROM pg_constraint con
  JOIN pg_class cls ON cls.oid = con.conrelid
  JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
  JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
  JOIN pg_class rcls ON rcls.oid = con.confrelid
  JOIN pg_namespace rnsp ON rnsp.oid = rcls.relnamespace
  WHERE con.contype = 'f'
    AND rcls.relname = 'clientes_blu'
    AND rnsp.nspname = 'public'
    AND att.attname = 'client_id'
) fk
LEFT JOIN admin.wipe_table_priority p ON p.table_fqn = fk.child_schema||'.'||fk.child_table
WHERE fk.pk_column IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. Request API (chamada pelos endpoints / superadmin)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION admin.request_client_deletion(
  p_client_id uuid,
  p_reason    text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, admin
AS $$
DECLARE
  v_job_id uuid;
  v_existing_job uuid;
BEGIN
  -- Validações
  IF p_client_id IS NULL THEN
    RAISE EXCEPTION 'client_id is required';
  END IF;
  IF p_reason IS NULL OR length(trim(p_reason)) < 5 THEN
    RAISE EXCEPTION 'reason must be at least 5 chars';
  END IF;

  -- Cliente existe?
  IF NOT EXISTS (SELECT 1 FROM public.clientes_blu WHERE client_id = p_client_id) THEN
    RAISE EXCEPTION 'client_id % not found in clientes_blu', p_client_id;
  END IF;

  -- Job ativo já existente?
  SELECT job_id INTO v_existing_job
  FROM admin.tenant_wipe_jobs
  WHERE client_id = p_client_id AND status IN ('queued','running')
  LIMIT 1;

  IF v_existing_job IS NOT NULL THEN
    RAISE NOTICE 'Wipe already scheduled: %', v_existing_job;
    RETURN v_existing_job;
  END IF;

  -- Soft-delete: bloqueia logins/rotinas imediatamente
  UPDATE public.clientes_blu
     SET deletion_status = 'deleting',
         deletion_requested_at = now()
   WHERE client_id = p_client_id;

  -- Enfileira
  INSERT INTO admin.tenant_wipe_jobs (client_id, reason, requested_by, status)
  VALUES (p_client_id, p_reason, auth.uid(), 'queued')
  RETURNING job_id INTO v_job_id;

  RETURN v_job_id;
END;
$$;

REVOKE ALL ON FUNCTION admin.request_client_deletion(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin.request_client_deletion(uuid, text) TO service_role;

-- ----------------------------------------------------------------------------
-- 4. Worker — uma chamada = um "tick" de até ~25s
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION admin.tenant_wipe_tick(
  p_batch_size int DEFAULT 5000,
  p_max_seconds int DEFAULT 25
)
RETURNS TABLE(job_id uuid, table_fqn text, rows_deleted int, finished boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, admin
AS $$
DECLARE
  v_job          admin.tenant_wipe_jobs%ROWTYPE;
  v_target       record;
  v_rows         int;
  v_total_rows   int := 0;
  v_t0           timestamptz := clock_timestamp();
  v_t_batch      timestamptz;
  v_batch_no     int := 0;
  v_finished_job boolean := false;
  v_sql          text;
BEGIN
  -- Pega próximo job (queued primeiro, depois running mais antigo)
  SELECT * INTO v_job
  FROM admin.tenant_wipe_jobs
  WHERE status IN ('queued','running')
  ORDER BY (status='queued') DESC, COALESCE(started_at, created_at) ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF v_job.status = 'queued' THEN
    UPDATE admin.tenant_wipe_jobs
       SET status='running', started_at=now(), updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;
    v_job.status := 'running';
    v_job.started_at := now();
  END IF;

  -- Itera tabelas na ordem de prioridade, pulando as já completas (current_table avança)
  FOR v_target IN
    SELECT *
    FROM admin.v_wipe_target_tables
    WHERE (v_job.current_table IS NULL)
       OR (table_fqn >= v_job.current_table)
    ORDER BY priority, table_fqn
  LOOP
    -- Loop de batches dentro da tabela
    LOOP
      -- Time budget?
      IF EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds THEN
        EXIT;
      END IF;

      v_t_batch := clock_timestamp();
      v_batch_no := v_batch_no + 1;

      -- DELETE batch usando ctid (mais barato que pk pra deleção em massa)
      v_sql := format(
        'WITH victim AS (
           SELECT ctid FROM %I.%I
           WHERE %I = $1
           LIMIT $2
         )
         DELETE FROM %I.%I t USING victim WHERE t.ctid = victim.ctid',
        v_target.child_schema, v_target.child_table, v_target.fk_column,
        v_target.child_schema, v_target.child_table
      );

      EXECUTE v_sql USING v_job.client_id, p_batch_size;
      GET DIAGNOSTICS v_rows = ROW_COUNT;
      v_total_rows := v_total_rows + v_rows;

      -- Audit
      INSERT INTO admin.tenant_wipe_audit(job_id, table_name, batch_no, rows_deleted, duration_ms)
      VALUES (
        v_job.job_id, v_target.table_fqn, v_batch_no, v_rows,
        EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_t_batch))::int
      );

      -- Retorna pra caller (uma linha por batch)
      job_id := v_job.job_id;
      table_fqn := v_target.table_fqn;
      rows_deleted := v_rows;
      finished := false;
      RETURN NEXT;

      EXIT WHEN v_rows = 0;

      -- pausa minúscula entre batches pra liberar locks
      PERFORM pg_sleep(0.05);
    END LOOP;

    -- Tabela acabou OU acabou o time budget. Persiste cursor.
    UPDATE admin.tenant_wipe_jobs
       SET current_table = v_target.table_fqn,
           rows_deleted_total = rows_deleted_total + v_total_rows,
           updated_at = now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    EXIT WHEN EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds;
  END LOOP;

  -- Verificação: se zero filhas em todas as target tables, finaliza
  PERFORM 1
    FROM admin.v_wipe_target_tables t
    WHERE admin._table_has_client(t.child_schema, t.child_table, t.fk_column, v_job.client_id)
    LIMIT 1;

  IF NOT FOUND THEN
    -- DELETE final: vault + auth.users (capturar antes do CASCADE) + clientes_blu

    -- 1. Captura user_ids ANTES do clientes_blu DELETE (que cascateia client_users)
    DROP TABLE IF EXISTS _users_to_delete;
    CREATE TEMP TABLE _users_to_delete ON COMMIT DROP AS
      SELECT user_id FROM public.client_users WHERE client_id = v_job.client_id;

    -- 2. Vault — padrões observados em prod (oauth_google_*, bigquery_service_account_*, bigquery_*_sa_key, integration_*)
    DELETE FROM vault.secrets
      WHERE name LIKE 'oauth_google_'    || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'oauth_%_'         || v_job.client_id || '\_%' ESCAPE '\'
         OR name = 'bigquery_service_account_' || v_job.client_id
         OR name LIKE 'bigquery_'        || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'integration_%\_'  || v_job.client_id || '%' ESCAPE '\';

    -- 3. clientes_blu (cascateia client_users + restantes)
    DELETE FROM public.clientes_blu WHERE client_id = v_job.client_id;

    -- 4. auth.users (usando lista capturada)
    DELETE FROM auth.users WHERE id IN (SELECT user_id FROM _users_to_delete);

    -- 5. Foreign servers BigQuery (per-tenant) — limpa também foreign tables + user mappings via CASCADE
    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS bigquery_%s CASCADE', v_job.client_id);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Skipping FDW server drop for %: %', v_job.client_id, SQLERRM;
    END;

    UPDATE admin.tenant_wipe_jobs
       SET status='completed',
           progress_pct=100,
           completed_at=now(),
           updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    v_finished_job := true;
  END IF;

  -- Retorna marca de fim (linha sentinel)
  job_id := v_job.job_id;
  table_fqn := COALESCE(v_target.table_fqn, '(end)');
  rows_deleted := 0;
  finished := v_finished_job;
  RETURN NEXT;
END;
$$;

-- Helper: dynamic count-exists (separado pra evitar SQL injection nas chamadas)
CREATE OR REPLACE FUNCTION admin._table_has_client(
  p_schema text, p_table text, p_fk text, p_client_id uuid
) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER
AS $$
DECLARE v_exists boolean;
BEGIN
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I.%I WHERE %I = $1 LIMIT 1)',
                 p_schema, p_table, p_fk)
    USING p_client_id INTO v_exists;
  RETURN v_exists;
END;
$$;

REVOKE ALL ON FUNCTION admin.tenant_wipe_tick(int,int) FROM PUBLIC;

-- ----------------------------------------------------------------------------
-- 5. View de observabilidade
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW admin.v_active_wipes AS
SELECT
  j.job_id,
  j.client_id,
  j.status,
  j.current_table,
  j.rows_deleted_total,
  j.progress_pct,
  j.started_at,
  EXTRACT(EPOCH FROM (now() - j.started_at))::int AS elapsed_sec,
  j.error
FROM admin.tenant_wipe_jobs j
WHERE j.status IN ('queued','running','failed')
ORDER BY j.created_at;

GRANT SELECT ON admin.v_active_wipes TO service_role;

-- ----------------------------------------------------------------------------
-- 6. pg_cron — tick a cada 30s
-- ----------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_cron') THEN
    PERFORM cron.unschedule(jobid) FROM cron.job WHERE jobname = 'tenant_wipe_worker';
    PERFORM cron.schedule(
      'tenant_wipe_worker',
      '* * * * *',  -- a cada minuto (pg_cron mínimo); tick interno consome ~25s
      $cron$ SELECT count(*) FROM admin.tenant_wipe_tick(5000, 25) $cron$
    );
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- VERIFICAÇÃO PÓS-APLICAÇÃO
-- ============================================================================
-- SELECT * FROM admin.v_wipe_target_tables ORDER BY priority;
-- SELECT cron.schedule FROM cron.job WHERE jobname='tenant_wipe_worker';
-- Teste (NÃO rodar em prod sem cliente de teste!):
--   SELECT admin.request_client_deletion('<test-uuid>', 'smoke test');
--   SELECT * FROM admin.v_active_wipes;
