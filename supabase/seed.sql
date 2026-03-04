-- Vault secret for Edge Function invocation from pg_net (local dev)
SELECT vault.create_secret('http://api.supabase.internal:8000', 'project_url');
