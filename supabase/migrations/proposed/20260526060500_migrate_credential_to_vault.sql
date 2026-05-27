-- ============================================================================
-- Commit 1b — Generic credential → vault migration helper
--
-- Idempotent helper to move any legacy plaintext credential
-- (credencial_servico_externo.credenciais jsonb) into vault.secrets and
-- clear the plaintext column. Works for ANY connector (BigQuery, Drive,
-- Sheets, future).
--
-- Audit (2026-05-26): 0 legacy plaintext credentials. This is infra prep —
-- guards against any tenant migrated from blu_app or hand-inserted bypassing
-- create_bigquery_server.
--
-- Idempotent: re-running on an already-migrated row is a no-op.
-- Safe: never returns the secret content. Naming policy mirrors
-- create_bigquery_server: '<tipo>_credential_<random_uuid>'.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.migrate_credential_to_vault(p_credential_id bigint)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  v_my_client_id  uuid;
  v_caller_role   text;
  v_row           RECORD;
  v_secret_name   text;
  v_secret_uuid   uuid;
  v_vault_key_id  uuid;
  v_tipo_norm     text;
BEGIN
  -- AuthZ: caller is the tenant owner OR service_role.
  v_caller_role  := COALESCE(auth.jwt() ->> 'role', '');
  v_my_client_id := public.get_my_client_id();

  SELECT id, client_id, tipo, tipo_servico, credenciais, vault_key_id
    INTO v_row
    FROM public.credencial_servico_externo
   WHERE id = p_credential_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'credential not found');
  END IF;

  IF v_caller_role <> 'service_role' AND v_row.client_id <> v_my_client_id THEN
    RAISE EXCEPTION 'access denied for credential %', p_credential_id
      USING ERRCODE = '42501';
  END IF;

  -- Idempotency
  IF v_row.vault_key_id IS NOT NULL THEN
    RETURN jsonb_build_object(
      'success', true,
      'credential_id', v_row.id,
      'vault_key_id', v_row.vault_key_id,
      'migrated', false,
      'message', 'already in vault'
    );
  END IF;

  IF v_row.credenciais IS NULL OR v_row.credenciais = '{}'::jsonb THEN
    RETURN jsonb_build_object(
      'success', false,
      'credential_id', v_row.id,
      'error', 'nothing to migrate: credenciais is empty and vault_key_id is null'
    );
  END IF;

  -- Build a secret name consistent with create_bigquery_server convention.
  v_tipo_norm   := lower(COALESCE(v_row.tipo, v_row.tipo_servico, 'credential'));
  v_secret_uuid := gen_random_uuid();
  v_secret_name := v_tipo_norm || '_credential_' || v_secret_uuid::text;

  -- Push to vault
  SELECT vault.create_secret(v_row.credenciais::text, v_secret_name)
    INTO v_vault_key_id;

  IF v_vault_key_id IS NULL THEN
    RAISE EXCEPTION 'vault.create_secret returned NULL for credential %', v_row.id;
  END IF;

  -- Atomically flip the row: set vault_key_id, clear plaintext.
  UPDATE public.credencial_servico_externo
     SET vault_key_id = v_vault_key_id,
         credenciais  = '{}'::jsonb,
         updated_at   = now()
   WHERE id = v_row.id
     AND vault_key_id IS NULL;  -- defensive against race

  IF NOT FOUND THEN
    -- Lost the race: another caller migrated first. Roll back our secret.
    BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
    EXCEPTION WHEN OTHERS THEN NULL; END;
    SELECT vault_key_id INTO v_vault_key_id
      FROM public.credencial_servico_externo WHERE id = v_row.id;
    RETURN jsonb_build_object(
      'success', true,
      'credential_id', v_row.id,
      'vault_key_id', v_vault_key_id,
      'migrated', false,
      'message', 'concurrent migration won the race'
    );
  END IF;

  RETURN jsonb_build_object(
    'success', true,
    'credential_id', v_row.id,
    'vault_key_id', v_vault_key_id,
    'migrated', true
  );
END;
$function$;

COMMENT ON FUNCTION public.migrate_credential_to_vault(bigint) IS
  'Idempotent: moves credencial_servico_externo.credenciais (plaintext jsonb) '
  'into vault.secrets and clears the plaintext column. Re-running on an '
  'already-migrated credential is a no-op. Never returns the secret content. '
  'Authorized for the tenant owner or service_role.';

GRANT EXECUTE ON FUNCTION public.migrate_credential_to_vault(bigint) TO authenticated, service_role;

COMMIT;
