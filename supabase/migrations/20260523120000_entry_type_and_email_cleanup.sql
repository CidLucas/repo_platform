-- =============================================================================
-- Migration: entry_type + email cleanup
-- =============================================================================
-- 1. Add entry_type column to fato_transacoes (system-derived direction)
-- 2. Backfill entry_type for existing rows (Polp already = 'banking', BQ NFs = 'revenue')
-- 3. Add email + email_domain to clientes_blu
-- 4. Drop fato_compras (empty table, superseded by entry_type='purchase')
-- =============================================================================

-- 1. entry_type column
ALTER TABLE analytics_v2.fato_transacoes
    ADD COLUMN IF NOT EXISTS entry_type text;

COMMENT ON COLUMN analytics_v2.fato_transacoes.entry_type IS
    'System-derived transaction direction: revenue | purchase | expense | banking. '
    'Never mapped directly from user CSV — always set by backend classification logic.';

-- 2. Backfill
-- Polp rows already have tipo_lancamento='bancario'
UPDATE analytics_v2.fato_transacoes
SET entry_type = 'banking'
WHERE entry_type IS NULL
  AND tipo_lancamento = 'bancario';

-- BQ NF rows: NULL tipo_lancamento but have a source_type hint (or we use cnpj cross)
-- Safe default: treat all unclassified non-Polp rows as 'revenue'
-- (they come from BQ NF-e pipeline where the client is the issuer)
UPDATE analytics_v2.fato_transacoes
SET entry_type = 'revenue'
WHERE entry_type IS NULL;

-- 3. email + email_domain on clientes_blu
ALTER TABLE public.clientes_blu
    ADD COLUMN IF NOT EXISTS email text,
    ADD COLUMN IF NOT EXISTS email_domain text GENERATED ALWAYS AS (
        CASE
            WHEN email IS NOT NULL AND position('@' IN email) > 0
            THEN split_part(email, '@', 2)
            ELSE NULL
        END
    ) STORED;

COMMENT ON COLUMN public.clientes_blu.email IS 'Primary contact email for the client business.';
COMMENT ON COLUMN public.clientes_blu.email_domain IS 'Derived email domain — used for meeting participant matching.';

-- 4. Drop fato_compras (was empty — 0 rows; all purchases now go to fato_transacoes with entry_type=''purchase'')
DROP TABLE IF EXISTS analytics_v2.fato_compras;
