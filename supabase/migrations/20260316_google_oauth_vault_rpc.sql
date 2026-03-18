-- Migration: Platform-level Google OAuth config via Supabase Vault
-- Purpose: RPC functions to store and retrieve platform Google OAuth credentials from Vault
-- Pattern: Follows 20260203_vault_credential_storage.sql

-- =============================================================================
-- 1. RPC: STORE A NAMED SECRET IN VAULT (upsert)
-- =============================================================================

create or replace function public.store_vault_secret(
  p_name text,
  p_secret text,
  p_description text default ''
) returns uuid
language plpgsql
security definer
set search_path = public, vault
as $$
declare
  v_existing_id uuid;
  v_new_id uuid;
begin
  -- Check for existing secret with same name
  select id into v_existing_id
  from vault.secrets
  where name = p_name
  limit 1;

  if v_existing_id is not null then
    perform vault.update_secret(v_existing_id, p_secret, p_name, p_description);
    return v_existing_id;
  else
    select vault.create_secret(p_secret, p_name, p_description) into v_new_id;
    return v_new_id;
  end if;
end;
$$;

comment on function public.store_vault_secret is
  'Upserts a named secret in Supabase Vault. Updates if name exists, creates otherwise.';

revoke execute on function public.store_vault_secret from public;
revoke execute on function public.store_vault_secret from anon;
revoke execute on function public.store_vault_secret from authenticated;
grant execute on function public.store_vault_secret to service_role;

-- =============================================================================
-- 2. RPC: GET PLATFORM GOOGLE OAUTH CONFIG FROM VAULT
-- =============================================================================
-- Platform-level secrets are stored in vault.secrets with names:
--   google_oauth_client_id
--   google_oauth_client_secret
-- Use scripts/seed_google_oauth_vault.py to populate them.

create or replace function public.get_platform_google_oauth_config()
returns jsonb
language plpgsql
security definer
set search_path = public, vault
as $$
declare
  v_client_id text;
  v_client_secret text;
begin
  select decrypted_secret into v_client_id
  from vault.decrypted_secrets
  where name = 'google_oauth_client_id'
  limit 1;

  select decrypted_secret into v_client_secret
  from vault.decrypted_secrets
  where name = 'google_oauth_client_secret'
  limit 1;

  if v_client_id is null or v_client_secret is null then
    return null;
  end if;

  return jsonb_build_object(
    'client_id', v_client_id,
    'client_secret', v_client_secret
  );
end;
$$;

comment on function public.get_platform_google_oauth_config is
  'Retrieves platform-level Google OAuth credentials from Supabase Vault. '
  'Returns NULL if not configured. Used as fallback when no per-client config exists.';

-- Only service_role can call this (backend only, not exposed to anon/authenticated)
revoke execute on function public.get_platform_google_oauth_config from public;
revoke execute on function public.get_platform_google_oauth_config from anon;
revoke execute on function public.get_platform_google_oauth_config from authenticated;
grant execute on function public.get_platform_google_oauth_config to service_role;
