-- ============================================================
-- Phase C6: Dead-letter queue for failed embeddings
-- ============================================================

-- 1. Create DLQ queue for embedding jobs that exhaust retries
SELECT pgmq.create('embedding_jobs_dlq');

-- 2. Add 'partially_failed' to the documents status CHECK constraint
-- First drop the existing constraint, then re-create with the new value
ALTER TABLE vector_db.documents
DROP CONSTRAINT IF EXISTS documents_status_check;

ALTER TABLE vector_db.documents
ADD CONSTRAINT documents_status_check
CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'partially_failed'));
