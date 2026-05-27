-- G5: Refresh dashboards async job
-- 1. Adiciona 'refresh_dashboards' ao CHECK constraint de job_type em reg_jobs
-- 2. Cria índice único parcial para debounce race-safe:
--    apenas 1 job refresh_dashboards pending por cliente ao mesmo tempo.
--    ON CONFLICT (client_id, job_type) WHERE job_type='refresh_dashboards' AND status='pending'
--    DO NOTHING — idempotente mesmo com apply_staging concorrente.

BEGIN;

-- 1. Ampliar o CHECK de job_type para incluir 'refresh_dashboards'
ALTER TABLE analytics_v2.reg_jobs
  DROP CONSTRAINT reg_jobs_job_type_check;

ALTER TABLE analytics_v2.reg_jobs
  ADD CONSTRAINT reg_jobs_job_type_check
  CHECK (job_type = ANY (ARRAY[
    'bigquery_sync'::text,
    'connector_sync'::text,
    'analytics_etl'::text,
    'custom'::text,
    'csv_sync'::text,
    'refresh_dashboards'::text
  ]));

-- 2. Índice único parcial: debounce race-safe para refresh_dashboards pending
--    Criado CONCURRENTLY fora de transação não é possível, mas como o índice é novo
--    e a tabela não tem volume crítico no momento da migration, criamos normal aqui.
--    Se a tabela tiver dados relevantes em prod, mover para CONCURRENTLY fora do BEGIN/COMMIT.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reg_jobs_refresh_pending
  ON analytics_v2.reg_jobs (client_id, job_type)
  WHERE job_type = 'refresh_dashboards' AND status = 'pending';

COMMENT ON INDEX analytics_v2.uq_reg_jobs_refresh_pending IS
  'Garante no máximo 1 job refresh_dashboards pending por cliente. '
  'Usado em ON CONFLICT (client_id, job_type) WHERE ... DO NOTHING no apply_staging_to_facts '
  'para debounce race-safe sem advisory locks.';

COMMIT;
