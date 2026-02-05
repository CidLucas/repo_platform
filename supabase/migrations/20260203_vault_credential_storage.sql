-- Migration: Secure credential storage with Supabase Vault
-- Purpose: Store external service credentials (BigQuery, SQL, Shopify, etc.) encrypted in vault
-- Pattern: Same as BigQuery FDW in 20251219_setup_bigquery_wrapper.sql

-- =============================================================================
-- 1. ADD VAULT_KEY_ID COLUMN
-- =============================================================================

alter table credencial_servico_externo
  add column if not exists vault_key_id uuid;

comment on column credencial_servico_externo.vault_key_id is
  'UUID reference to encrypted credentials in vault.secrets';

-- =============================================================================
-- 2. RPC FUNCTION: STORE CREDENTIAL IN VAULT
-- =============================================================================

create or replace function public.store_credential_in_vault(
  p_client_id uuid,
  p_credential_id bigint,
  p_credentials jsonb
) returns uuid
language plpgsql
security definer
set search_path = public, vault
as $$
declare
  v_key_name text;
  v_vault_key_id uuid;
  v_existing_id uuid;
begin
  -- Generate deterministic key name
  v_key_name := 'cred_' || p_client_id || '_' || p_credential_id;

  -- Check for existing secret with same name
  select id into v_existing_id
  from vault.secrets
  where name = v_key_name
  limit 1;

  -- Update existing or create new
  if v_existing_id is not null then
    -- Update existing secret
    perform vault.update_secret(v_existing_id, p_credentials::text);
    v_vault_key_id := v_existing_id;
  else
    -- Create new encrypted secret
    select vault.create_secret(
      p_credentials::text,
      v_key_name,
      'External service credential for client ' || p_client_id
    ) into v_vault_key_id;
  end if;

  return v_vault_key_id;
end;
$$;

comment on function public.store_credential_in_vault is
  'Stores credentials encrypted in Supabase Vault, returns vault_key_id';

-- =============================================================================
-- 3. RPC FUNCTION: GET CREDENTIAL FROM VAULT
-- =============================================================================

create or replace function public.get_credential_from_vault(
  p_vault_key_id uuid
) returns jsonb
language plpgsql
security definer
set search_path = public, vault
as $$
declare
  v_secret text;
begin
  -- Retrieve decrypted secret
  select decrypted_secret into v_secret
  from vault.decrypted_secrets
  where id = p_vault_key_id;

  if v_secret is null then
    raise exception 'Credential not found in vault: %', p_vault_key_id;
  end if;

  return v_secret::jsonb;
end;
$$;

comment on function public.get_credential_from_vault is
  'Retrieves and decrypts credentials from Supabase Vault';

-- =============================================================================
-- 4. RPC FUNCTION: DELETE CREDENTIAL FROM VAULT
-- =============================================================================

create or replace function public.delete_credential_from_vault(
  p_vault_key_id uuid
) returns void
language plpgsql
security definer
set search_path = public, vault
as $$
begin
  perform vault.delete_secret(p_vault_key_id);
end;
$$;

comment on function public.delete_credential_from_vault is
  'Deletes credentials from Supabase Vault';

-- =============================================================================
-- 5. GRANTS
-- =============================================================================

grant execute on function public.store_credential_in_vault to service_role;
grant execute on function public.get_credential_from_vault to service_role;
grant execute on function public.delete_credential_from_vault to service_role;

-- =============================================================================
-- 6. MIGRATE EXISTING PLAIN-TEXT CREDENTIALS TO VAULT
-- =============================================================================

do $$
declare
  r record;
  v_vault_key_id uuid;
  v_migrated_count int := 0;
begin
  raise notice 'Starting credential migration to vault...';

  for r in
    select id, client_id, credenciais_cifradas
    from credencial_servico_externo
    where vault_key_id is null
      and credenciais_cifradas is not null
      and credenciais_cifradas != ''
  loop
    begin
      -- Store in vault
      select public.store_credential_in_vault(
        r.client_id,
        r.id,
        r.credenciais_cifradas::jsonb
      ) into v_vault_key_id;

      -- Update record: set vault_key_id, clear plaintext
      update credencial_servico_externo
      set vault_key_id = v_vault_key_id,
          credenciais_cifradas = null
      where id = r.id;

      v_migrated_count := v_migrated_count + 1;
      raise notice 'Migrated credential id=% to vault', r.id;

    exception when others then
      raise warning 'Failed to migrate credential id=%: %', r.id, sqlerrm;
    end;
  end loop;

  raise notice 'Migration complete. Migrated % credentials to vault.', v_migrated_count;
end $$;
