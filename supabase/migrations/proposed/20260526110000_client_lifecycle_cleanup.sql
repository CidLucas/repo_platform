-- =============================================================================
-- Client lifecycle cleanup
-- Garante que DELETE em clientes_blu limpa 100% dos dados do cliente.
--
-- Gaps corrigidos:
--   1. polp_integrations/accounts/bills/transactions — sem FK para clientes_blu
--   2. vault.secrets órfãs — credencial deletada via cascade mas secret fica
--   3. storage.objects órfãos — uploaded_files_metadata deletada mas arquivo fica
--   4. auth.users zumbis — client_users deletada mas user fica em auth.users
--      (só deleta se o user não tiver vínculo com nenhum outro cliente)
--   5. audit_log — tinha só índice, sem FK/cascade
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. POLP: limpar órfãos e adicionar FK com ON DELETE CASCADE para clientes_blu
-- ---------------------------------------------------------------------------
-- Remover dados órfãos (client_id sem registro em clientes_blu) antes de criar FK
DELETE FROM public.polp_transactions
  WHERE client_id NOT IN (SELECT client_id FROM public.clientes_blu);
DELETE FROM public.polp_bills
  WHERE client_id NOT IN (SELECT client_id FROM public.clientes_blu);
DELETE FROM public.polp_accounts
  WHERE client_id NOT IN (SELECT client_id FROM public.clientes_blu);
DELETE FROM public.polp_integrations
  WHERE client_id NOT IN (SELECT client_id FROM public.clientes_blu);

-- Limpar audit_log órfão também
DELETE FROM public.audit_log
  WHERE client_id NOT IN (SELECT client_id FROM public.clientes_blu);

-- polp_integrations é a raiz (polp_accounts → polp_integrations via CASCADE já existe)
ALTER TABLE public.polp_integrations
  ADD CONSTRAINT polp_integrations_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id)
  ON DELETE CASCADE;

-- polp_bills e polp_transactions têm client_id direto (além da chain via polp_accounts)
-- adicionamos FK direta para garantir cleanup mesmo se a chain quebrar
ALTER TABLE public.polp_bills
  ADD CONSTRAINT polp_bills_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id)
  ON DELETE CASCADE;

ALTER TABLE public.polp_transactions
  ADD CONSTRAINT polp_transactions_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id)
  ON DELETE CASCADE;

-- ---------------------------------------------------------------------------
-- 2. AUDIT LOG: adicionar FK com ON DELETE CASCADE
-- ---------------------------------------------------------------------------
ALTER TABLE public.audit_log
  ADD CONSTRAINT audit_log_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id)
  ON DELETE CASCADE;

-- ---------------------------------------------------------------------------
-- 3. VAULT SECRETS: trigger para limpar vault.secrets quando credencial é deletada
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cleanup_credential_vault_secret()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, vault
AS $$
BEGIN
  IF OLD.vault_key_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = OLD.vault_key_id;
  END IF;
  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_cleanup_credential_vault_secret ON public.credencial_servico_externo;
CREATE TRIGGER trg_cleanup_credential_vault_secret
  BEFORE DELETE ON public.credencial_servico_externo
  FOR EACH ROW
  EXECUTE FUNCTION public.cleanup_credential_vault_secret();

-- ---------------------------------------------------------------------------
-- 4. STORAGE OBJECTS: trigger para limpar arquivos físicos quando o registro
--    de metadata é deletado (uploaded_files_metadata deletada via CASCADE do cliente)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cleanup_storage_object()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, storage
AS $$
BEGIN
  -- Deleta o objeto físico do bucket. Ignora erro se já não existir.
  DELETE FROM storage.objects
  WHERE bucket_id = OLD.bucket
    AND name = OLD.storage_path;
  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_cleanup_storage_object ON public.uploaded_files_metadata;
CREATE TRIGGER trg_cleanup_storage_object
  BEFORE DELETE ON public.uploaded_files_metadata
  FOR EACH ROW
  EXECUTE FUNCTION public.cleanup_storage_object();

-- Também limpar arquivos em client_data_sources.storage_location (CSV/Drive imports)
-- storage_location pode ser NULL (BigQuery sources não têm arquivo)
CREATE OR REPLACE FUNCTION public.cleanup_datasource_storage_object()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, storage
AS $$
DECLARE
  v_bucket text;
  v_path   text;
BEGIN
  IF OLD.storage_location IS NULL THEN
    RETURN OLD;
  END IF;

  -- Inferir bucket pelo prefixo do path
  -- Padrões conhecidos:
  --   csv_uploads/{client_id}/...    → bucket: file-uploads
  --   drive_imports/{client_id}/...  → bucket: file-uploads
  --   knowledge-base/...             → bucket: knowledge-base
  IF OLD.storage_location LIKE 'csv_uploads/%' OR OLD.storage_location LIKE 'drive_imports/%' THEN
    v_bucket := 'file-uploads';
    v_path   := OLD.storage_location;
  ELSIF OLD.storage_location LIKE 'knowledge-base/%' OR OLD.storage_location LIKE 'onboarding/%' THEN
    v_bucket := 'knowledge-base';
    v_path   := OLD.storage_location;
  ELSE
    -- Path desconhecido — não tenta deletar para evitar deleção acidental
    RETURN OLD;
  END IF;

  DELETE FROM storage.objects
  WHERE bucket_id = v_bucket AND name = v_path;

  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_cleanup_datasource_storage ON public.client_data_sources;
CREATE TRIGGER trg_cleanup_datasource_storage
  BEFORE DELETE ON public.client_data_sources
  FOR EACH ROW
  EXECUTE FUNCTION public.cleanup_datasource_storage_object();

-- ---------------------------------------------------------------------------
-- 5. AUTH.USERS: trigger para deletar user zumbi após remoção de client_users
--    Só deleta se o user não tiver mais nenhum vínculo com outro cliente.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cleanup_auth_user_if_orphaned()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
  v_remaining int;
BEGIN
  IF OLD.auth_user_id IS NULL THEN
    RETURN OLD;
  END IF;

  -- Contar quantos outros clientes esse user ainda tem
  SELECT count(*) INTO v_remaining
  FROM public.client_users
  WHERE auth_user_id = OLD.auth_user_id
    AND client_id != OLD.client_id;  -- excluir o que está sendo deletado

  IF v_remaining = 0 THEN
    -- Sem outros vínculos: deletar o usuário de auth.users
    DELETE FROM auth.users WHERE id = OLD.auth_user_id;
  END IF;

  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_cleanup_auth_user_orphan ON public.client_users;
CREATE TRIGGER trg_cleanup_auth_user_orphan
  AFTER DELETE ON public.client_users
  FOR EACH ROW
  EXECUTE FUNCTION public.cleanup_auth_user_if_orphaned();

-- ---------------------------------------------------------------------------
-- Comentários
-- ---------------------------------------------------------------------------
COMMENT ON FUNCTION public.cleanup_credential_vault_secret IS
'BEFORE DELETE ON credencial_servico_externo. Limpa o vault.secret correspondente '
'(vault_key_id). Chamada via CASCADE quando o cliente é deletado.';

COMMENT ON FUNCTION public.cleanup_storage_object IS
'BEFORE DELETE ON uploaded_files_metadata. Remove o objeto físico do Storage '
'quando o registro de metadata é deletado (ex: via CASCADE de cliente).';

COMMENT ON FUNCTION public.cleanup_datasource_storage_object IS
'BEFORE DELETE ON client_data_sources. Remove arquivo físico do Storage '
'(csv_uploads/*, drive_imports/*, knowledge-base/*) quando a data source é deletada.';

COMMENT ON FUNCTION public.cleanup_auth_user_if_orphaned IS
'AFTER DELETE ON client_users. Deleta auth.users se o user não tiver mais '
'nenhum vínculo com outro cliente (user zumbi sem tenant).';

COMMIT;
