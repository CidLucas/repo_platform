# services/data_ingestion_api/services/credential_service.py

import logging
from typing import Any

from src.schemas import BigQueryCredentialCreate, CredencialResponse, SQLCredentialCreate
from google.cloud import secretmanager
import json
import os

logger = logging.getLogger(__name__)

# TODO: Substituir por import real do libs/vizu_db_connector
class VizuDBConnector:
    """Mock do nosso vizu_db_connector para simular a persistência."""
    async def save_credential_reference(self, data: dict[str, Any]) -> dict[str, Any]:
        # Simula salvar no banco
        import uuid
        return {
            "id_credencial": str(uuid.uuid4()),
            "secret_manager_id": data['secret_manager_id'],
            "nome_conexao": data['nome_conexao'],
            "tipo_servico": data['tipo_servico'],
            "status": "PENDENTE_VALIDACAO"
        }

class SecretManager:
    """Integração real com o Google Secret Manager."""
    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        self.client = secretmanager.SecretManagerServiceClient()

    async def store_secret(self, client_id: str, credentials: dict[str, Any]) -> str:
        """
        Cria um segredo (ou usa existente) e adiciona uma nova versão com as credenciais.
        Retorna o secret_id:version.
        """
        secret_id = f"bq-cred-{client_id}"
        parent = f"projects/{self.project_id}"
        # Cria o segredo se não existir
        try:
            self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except Exception:
            pass  # Já existe
        # Adiciona uma nova versão
        payload = json.dumps(credentials).encode("UTF-8")
        response = self.client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_id}",
                "payload": {"data": payload},
            }
        )
        return f"{secret_id}:{response.name.split('/')[-1]}"

    async def access_secret(self, secret_id: str, version: str = "latest") -> dict:
        """
        Recupera o segredo do Secret Manager.
        """
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
        response = self.client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return json.loads(payload)

    async def delete_secret(self, secret_id: str) -> bool:
        """
        Deleta o segredo do Secret Manager.
        """
        name = f"projects/{self.project_id}/secrets/{secret_id}"
        self.client.delete_secret(request={"name": name})
        logger.info(f"Rollback: Deletando segredo {secret_id} do Secret Manager.")
        return True

# Instanciação dos mocks como dependências do serviço
db_connector = VizuDBConnector()
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

            # 2. Persistir a REFERÊNCIA (Secret ID) no vizu_db_connector
            db_payload = {
                "cliente_vizu_id": client_id,
                "nome_conexao": credenciais.nome_conexao,
                "tipo_servico": credenciais.tipo_servico,
                "secret_manager_id": secret_id
            }

            db_result = await db_connector.save_credential_reference(db_payload)

            # 3. Finalizar e Retornar
            # Padrão Vizu: Assumimos que o await resolveu o AsyncMock para o dict (Corrigido pelo Mock no Teste)
            logger.info(f"Referência de credencial {db_result['id_credencial']} salva com Secret ID {secret_id}.")

            return CredencialResponse(**db_result)

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
