-- ============================================================
-- Phase A1: Fix double-encoded metadata in existing chunks
-- ============================================================
-- Metadata was stored as JSONB string due to JSON.stringify() bug.
-- This converts them back to proper JSONB objects.
UPDATE vector_db.document_chunks
SET metadata = metadata::text::jsonb
WHERE jsonb_typeof(metadata) = 'string';

-- ============================================================
-- Phase B2 + B3: Upgraded match_documents with JOIN + document_ids filter
-- ============================================================
-- Adds:
--   - JOIN to vector_db.documents for file_name and document_title
--   - Optional p_document_ids parameter to scope search to specific docs
--   - Filter for completed documents only

CREATE OR REPLACE FUNCTION vector_db.match_documents(
  p_client_id UUID,
  p_query_embedding extensions.halfvec(384),
  p_match_count INT DEFAULT 5,
  p_match_threshold FLOAT DEFAULT 0.5,
  p_document_ids UUID[] DEFAULT NULL
)
RETURNS TABLE (
  id INTEGER,
  document_id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT,
  file_name TEXT,
  document_title TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'extensions', 'vector_db', 'public'
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.metadata,
    (1 - (dc.embedding <=> p_query_embedding))::float AS similarity,
    d.file_name,
    d.title AS document_title
  FROM vector_db.document_chunks dc
  JOIN vector_db.documents d ON d.id = dc.document_id
  WHERE dc.client_id = p_client_id
    AND dc.embedding IS NOT NULL
    AND d.status = 'completed'
    AND 1 - (dc.embedding <=> p_query_embedding) > p_match_threshold
    AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
  ORDER BY dc.embedding <=> p_query_embedding
  LIMIT p_match_count;
END;
$$;
