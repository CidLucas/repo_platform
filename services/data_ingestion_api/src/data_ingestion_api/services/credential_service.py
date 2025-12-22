# services/data_ingestion_api/services/credential_service.py

import logging
import uuid
from typing import Any

from vizu_auth import SecretManager

from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
    CredencialResponse,
    SQLCredentialCreate,
)
from data_ingestion_api.services import supabase_client

logger = logging.getLogger(__name__)

# Instanciação do Secret Manager
secret_manager = SecretManager()

class CredentialService:
    """
    Serviço de Lógica de Negócios para a manipulação de Credenciais.
    Responsabilidade: Segurança (Secret Manager) e Persistência (DB).
    """

    async def create_credential(self, credenciais: SQLCredentialCreate | BigQueryCredentialCreate) -> CredencialResponse:
        """
        Fluxo unificado para criar a credencial de um cliente Enterprise.
        """
        client_id = credenciais.cliente_vizu_id
        secret_id = None # CRÍTICO: Inicializar para garantir o escopo no bloco finally

        try:
            # 1. Armazenar credenciais sensíveis no Secret Manager
            # Convertemos o Pydantic para dict e filtramos dados sensíveis, se necessário
            # Nota: O Pydantic to_dict() garante que a senha seja convertida

            # Criamos o payload de credenciais (apenas os dados necessários para o conector)
            sensitive_payload = credenciais.model_dump(exclude={"cliente_vizu_id", "nome_conexao", "tipo_servico"})

            logger.info(f"Armazenando segredo para cliente {client_id} no Secret Manager.")
            secret_id = await secret_manager.store_secret(client_id, sensitive_payload)

            # 2. Persistir a REFERÊNCIA (Secret ID) no Supabase
            db_payload = {
                "cliente_vizu_id": client_id,
                "nome_servico": credenciais.nome_conexao,
                "credenciais_cifradas": secret_id,  # Store the Secret Manager ID
            }

            db_result = await supabase_client.insert("credencial_servico_externo", db_payload)

            # 3. Finalizar e Retornar
            # Map Supabase response to expected format
            response_data = {
                "id_credencial": str(db_result.get("id", uuid.uuid4())),
                "secret_manager_id": secret_id,
                "nome_conexao": credenciais.nome_conexao,
                "tipo_servico": credenciais.tipo_servico,
                "status": "PENDENTE_VALIDACAO"
            }

            logger.info(f"Referência de credencial {response_data['id_credencial']} salva com Secret ID {secret_id}.")

            return CredencialResponse(**response_data)

        except Exception as e:
            # Fluxo de Rollback: Se o Secret Manager teve sucesso, mas a persistência ou o retorno falharam
            if secret_id:
                logger.warning(f"Persistência falhou. Iniciando ROLLBACK: Deletando segredo {secret_id}.")
                # Adicionamos um try interno para não obscurecer o erro original
                try:
                    await secret_manager.delete_secret(secret_id)
                    logger.warning(f"Rollback bem-sucedido: Segredo {secret_id} deletado.")
                except Exception as rollback_e:
                    logger.error(f"FALHA CRÍTICA: Rollback do segredo {secret_id} falhou: {rollback_e}")

            # Re-lança o erro original, garantindo que a API retorne um 500
            raise e

credential_service = CredentialService()
