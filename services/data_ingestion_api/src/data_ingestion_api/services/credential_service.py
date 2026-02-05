# services/data_ingestion_api/services/credential_service.py

import logging
import uuid

from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
    CredencialResponse,
    SQLCredentialCreate,
)
from data_ingestion_api.services import supabase_client

logger = logging.getLogger(__name__)


class CredentialService:
    """
    Serviço de Lógica de Negócios para a manipulação de Credenciais.
    Responsabilidade: Segurança (Supabase Vault encryption) e Persistência (DB).
    """

    async def create_credential(self, credenciais: SQLCredentialCreate | BigQueryCredentialCreate) -> CredencialResponse:
        """
        Fluxo unificado para criar a credencial de um cliente Enterprise.

        Credentials are stored encrypted in Supabase Vault using pgsodium.
        Only a vault_key_id reference is stored in the database.
        """
        client_id = credenciais.client_id

        try:
            # 0. Log safe summary (never log actual credentials)
            tipo = credenciais.tipo_servico
            logger.info(
                "Creating credential: client_id=%s, tipo_servico=%s, nome_conexao=%s",
                client_id,
                tipo,
                credenciais.nome_conexao,
            )

            # 1. Prepare sensitive payload (credentials only, excluding metadata)
            sensitive_payload = credenciais.model_dump(exclude={"client_id", "nome_conexao", "tipo_servico"})

            # Mask secrets for logs
            safe_log = dict(sensitive_payload)
            if "password" in safe_log:
                safe_log["password"] = "***"
            if "service_account_json" in safe_log and isinstance(safe_log["service_account_json"], dict):
                saj = safe_log["service_account_json"]
                safe_log["service_account_json"] = {
                    "project_id": saj.get("project_id"),
                    "client_email": saj.get("client_email"),
                    "keys": list(saj.keys())
                }
            logger.debug("Sensitive payload summary: %s", safe_log)

            # 2. Check for existing credential to determine if update or create
            existing_creds = await supabase_client.select(
                "credencial_servico_externo",
                columns="*",
                filters={"client_id": client_id, "tipo_servico": credenciais.tipo_servico}
            )

            if existing_creds:
                # UPDATE path: existing credential found
                credential_id = existing_creds[0]["id"]
                logger.info("Updating existing credential: id=%s", credential_id)

                # Store credentials in vault (will overwrite existing)
                vault_key_id = await supabase_client.rpc(
                    "store_credential_in_vault",
                    {
                        "p_client_id": client_id,
                        "p_credential_id": credential_id,
                        "p_credentials": sensitive_payload,
                    }
                )
                logger.info("Credentials updated in vault: vault_key_id=%s", vault_key_id)

                # Update record with new vault_key_id and metadata
                await supabase_client.update(
                    "credencial_servico_externo",
                    {
                        "vault_key_id": vault_key_id,
                        "nome_servico": credenciais.nome_conexao,
                        "status": "active",
                    },
                    {"id": credential_id}
                )
                logger.info("Updated credential record with vault_key_id")
            else:
                # CREATE path: no existing credential
                # Use a two-step process since vault_key_id is NOT NULL:
                # 1. Call RPC to store in vault (we'll use a temporary credential_id)
                # 2. Insert record with the vault_key_id

                # Generate temporary ID for vault key naming (will use actual DB id later)
                temp_credential_id = 999999  # Temporary - will get overwritten by actual DB id

                logger.info("Creating new credential for client %s", client_id)

                # Store credentials in vault first (using temp ID)
                vault_key_id = await supabase_client.rpc(
                    "store_credential_in_vault",
                    {
                        "p_client_id": client_id,
                        "p_credential_id": temp_credential_id,
                        "p_credentials": sensitive_payload,
                    }
                )
                logger.info("Credentials stored in vault: vault_key_id=%s", vault_key_id)

                # Now insert record WITH vault_key_id
                db_payload = {
                    "client_id": client_id,
                    "nome_servico": credenciais.nome_conexao,
                    "tipo_servico": credenciais.tipo_servico,
                    "vault_key_id": vault_key_id,
                    "status": "active",
                }

                db_result = await supabase_client.insert("credencial_servico_externo", db_payload)
                credential_id = db_result.get("id")
                logger.info("Inserted credential record: id=%s with vault_key_id=%s", credential_id, vault_key_id)

            # 5. Return response
            response_data = {
                "id_credencial": str(credential_id),
                "secret_manager_id": f"vault:{vault_key_id}",
                "nome_conexao": credenciais.nome_conexao,
                "tipo_servico": credenciais.tipo_servico,
                "status": "ACTIVE" if existing_creds else "PENDENTE_VALIDACAO"
            }

            logger.info("Credential %s saved successfully (encrypted in vault).", credential_id)

            return CredencialResponse(**response_data)

        except Exception as e:
            logger.error("Failed to create credential for client %s: %s", client_id, e, exc_info=True)
            raise


credential_service = CredentialService()
