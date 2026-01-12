# services/data_ingestion_api/services/credential_service.py

import json
import logging
import uuid
from typing import Any

# Note: SecretManager requires GCP credentials - disabled for now
# from vizu_auth import SecretManager

from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
    CredencialResponse,
    SQLCredentialCreate,
)
from data_ingestion_api.services import supabase_client

logger = logging.getLogger(__name__)

# NOTE: Secret Manager disabled - storing credentials directly in Supabase
# For production: Enable Secret Manager and configure GCP credentials
# secret_manager = SecretManager()

class CredentialService:
    """
    Serviço de Lógica de Negócios para a manipulação de Credenciais.
    Responsabilidade: Segurança (Supabase encrypted storage) e Persistência (DB).
    """

    async def create_credential(self, credenciais: SQLCredentialCreate | BigQueryCredentialCreate) -> CredencialResponse:
        """
        Fluxo unificado para criar a credencial de um cliente Enterprise.

        NOTE: Currently stores credentials directly in Supabase as JSON.
        For production: Use Google Secret Manager for better security.
        """
        client_id = credenciais.client_id

        try:
            # 0. Log safe summary
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
                    # Do not log private_key
                    "keys": list(saj.keys())
                }
            logger.info("Sensitive payload summary: %s", safe_log)

            # 2. Store credentials directly in Supabase
            # TODO: For production, use Secret Manager instead
            logger.info(f"Storing credentials for client {client_id} in Supabase.")
            credentials_json = json.dumps(sensitive_payload)

            # 3. Persist to Supabase with all metadata
            db_payload = {
                "client_id": client_id,
                "nome_servico": credenciais.nome_conexao,
                "tipo_servico": credenciais.tipo_servico,
                "credenciais_cifradas": credentials_json,  # Store JSON directly (Supabase encrypts at rest)
                "status": "pending",  # Will be updated after first successful sync
            }

            db_result = await supabase_client.insert("credencial_servico_externo", db_payload)
            logger.info("Supabase insert into credencial_servico_externo returned: id=%s", db_result.get("id"))

            # 4. Return response
            response_data = {
                "id_credencial": str(db_result.get("id", uuid.uuid4())),
                "secret_manager_id": f"supabase:{client_id}",  # Indicate storage location
                "nome_conexao": credenciais.nome_conexao,
                "tipo_servico": credenciais.tipo_servico,
                "status": "PENDENTE_VALIDACAO"
            }

            logger.info(f"Credential {response_data['id_credencial']} saved successfully.")

            return CredencialResponse(**response_data)

        except Exception as e:
            # Log error and re-raise
            logger.error(f"Failed to create credential for client {client_id}: {e}", exc_info=True)
            raise e

credential_service = CredentialService()
