-- ============================================================
-- Phase C3: Content deduplication via content_hash
-- ============================================================
-- Add content_hash column (SHA-256 hex string) for deduplication.
-- Unique constraint per (document_id, content_hash) prevents
-- duplicate chunks when the same file is re-uploaded.

ALTER TABLE vector_db.document_chunks
ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- Create unique constraint for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_document_content_hash
ON vector_db.document_chunks (document_id, content_hash)
WHERE content_hash IS NOT NULL;

-- Backfill existing chunks with SHA-256 hash
UPDATE vector_db.document_chunks
SET content_hash = encode(sha256(content::bytea), 'hex')
WHERE content_hash IS NULL;
