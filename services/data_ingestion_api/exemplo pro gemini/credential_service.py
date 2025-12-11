# services/data_ingestion_api/services/credential_service.py

import logging
from typing import Any

from src.schemas import BigQueryCredentialCreate, CredencialResponse, SQLCredentialCreate

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

# TODO: Substituir por import real do nosso módulo de Secrets
class SecretManager:
    """Mock para simular a integração com o Google Secret Manager."""
    async def store_secret(self, client_id: str, credentials: dict[str, Any]) -> str:
        # Lógica real faria a chamada ao GCP/AWS/Azure
        # Retorna o ID do segredo
        import hashlib
        secret_hash = hashlib.sha256(str(credentials).encode()).hexdigest()
        return f"vizu-secret-id-{client_id}-{secret_hash[:8]}"

    # NOVO MÉTODO: Essencial para o Rollback
    async def delete_secret(self, secret_id: str) -> bool:
        """Simula a deleção de um segredo durante o Rollback."""
        logger.info(f"Rollback: Deletando segredo {secret_id} do Secret Manager.")
        return True # Retorno booleano para indicar sucesso

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
