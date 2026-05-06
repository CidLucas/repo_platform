-- Migration: Add missing columns to client_data_sources
-- Date: 2026-04-28
-- Purpose: Add 10 missing columns that the admin mapping UI expects

-- Add missing columns for column mapping workflow
ALTER TABLE public.client_data_sources
  ADD COLUMN IF NOT EXISTS unmapped_columns JSONB COMMENT 'Columns from source that edge function could not match to canonical schema',
  ADD COLUMN IF NOT EXISTS needs_review_columns JSONB COMMENT 'Columns with medium-confidence matches (0.70-0.85) requiring user review',
  ADD COLUMN IF NOT EXISTS match_confidence JSONB COMMENT 'Confidence scores for each matched column {source_col: 0.95, ...}',
  ADD COLUMN IF NOT EXISTS detected_entity_context TEXT COMMENT 'Entity type inferred from columns: customer | supplier | product | neutral',
  ADD COLUMN IF NOT EXISTS auto_column_mapping JSONB COMMENT 'Immutable snapshot of initial auto-matched columns (for audit trail)',
  ADD COLUMN IF NOT EXISTS ignored_columns TEXT[] COMMENT 'Columns user explicitly chose to skip during mapping',
  ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT false COMMENT 'true = mapping came from edge function; false = user manually mapped',
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE COMMENT 'Timestamp when user completed mapping review',
  ADD COLUMN IF NOT EXISTS user_column_changes JSONB COMMENT 'Diff of user changes vs auto match: {source_col: {from: auto_value, to: user_value}, ...}',
  ADD COLUMN IF NOT EXISTS ingestion_quality JSONB COMMENT 'Quality report from sync: rows_loaded, rows_inserted, date_range, null_counts, etc.';
