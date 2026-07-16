#!/usr/bin/env bash
# Aplica em prod as migrations que destravam RAG + LightRAG (review 2026-07-15).
# Uso:  ./scripts/apply_lightrag_migrations.sh
# Requer: supabase/.env.local com DATABASE_URL_PROD válida (refrescada em 2026-07-15).
set -euo pipefail

cd "$(dirname "$0")/.."
DBURL=$(grep -E "^DATABASE_URL_PROD=" supabase/.env.local | head -1 | cut -d= -f2-)
[ -n "$DBURL" ] || { echo "DATABASE_URL_PROD não encontrada em supabase/.env.local"; exit 1; }

MIG=supabase/migrations/proposed

echo "== 1/6 drop da assinatura antiga de vector_db.hybrid_match_documents =="
psql "$DBURL" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE sig text;
BEGIN
  FOR sig IN
    SELECT p.oid::regprocedure::text
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vector_db' AND p.proname = 'hybrid_match_documents'
  LOOP
    RAISE NOTICE 'DROP FUNCTION %', sig;
    EXECUTE 'DROP FUNCTION ' || sig;
  END LOOP;
END $$;
SQL

for f in \
  20260716000000_sbm_curated_expires.sql \
  20260619_shared_business_memory_meta.sql \
  20260619_shared_business_memory_versions.sql \
  20260623000000_content_hash_versioning.sql \
  20260625000000_hybrid_match_documents_12param.sql
do
  echo "== apply $f =="
  psql "$DBURL" -v ON_ERROR_STOP=1 -f "$MIG/$f"
done

echo "== verificação =="
psql "$DBURL" -v ON_ERROR_STOP=1 <<'SQL'
SELECT n.nspname || '.' || p.proname AS fn,
       array_length(string_to_array(pg_get_function_identity_arguments(p.oid), ','), 1) AS n_params
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.proname IN ('hybrid_match_documents', 'match_documents');

SELECT column_name FROM information_schema.columns
WHERE table_name = 'shared_business_memory'
  AND column_name IN ('curated', 'expires_at', 'content_hash');

SELECT to_regclass('public.shared_business_memory_meta') AS meta,
       to_regclass('public.shared_business_memory_versions') AS versions;

SELECT curated, count(*) FROM public.shared_business_memory GROUP BY curated;

-- PostgREST: recarrega o schema cache para os RPCs novos aparecerem via REST
NOTIFY pgrst, 'reload schema';
SQL

echo "== DONE =="
