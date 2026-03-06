-- Migration: Drop pg_cron polling for embedding + metadata enrichment
-- ====================================================================
-- The cron jobs (every 10-30s) are replaced by on-demand invocation:
-- process-document now calls util.process_embeddings() and
-- util.process_metadata() directly after inserting chunks.
--
-- What stays:
--   - pgmq queues (embedding_jobs, metadata_jobs, DLQs)
--   - INSERT triggers (queue_embedding_if_null, queue_metadata_if_null)
--   - util.process_embeddings() / util.process_metadata() functions
--   - embed & enrich-metadata Edge Functions
--
-- Only the cron schedules are removed.

-- Drop embedding cron job (jobid=2, '10 seconds' / '30 seconds')
SELECT cron.unschedule('process-embeddings')
WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'process-embeddings'
);

-- Drop metadata enrichment cron job (jobid=3, '10 seconds' / '30 seconds')
SELECT cron.unschedule('process-metadata')
WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'process-metadata'
);

-- Also drop the duplicate embed trigger — there are TWO on document_chunks:
--   embed_chunk_on_insert  (original)
--   embed_on_insert         (duplicate from earlier migration)
-- Keep only embed_chunk_on_insert.
DROP TRIGGER IF EXISTS embed_on_insert ON vector_db.document_chunks;
