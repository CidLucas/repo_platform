-- Enable pg_stat_statements extension for query performance tracking
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_stat_statements';
