# src/analytics_api/api/dependencies.py
from fastapi import Depends, HTTPException, status
# IMPORT CORRIGIDO: Importa a função geradora de sessão da biblioteca
from vizu_db_connector.database import get_db_session as get_vizu_db_session
from sqlalchemy.orm import Session # Importa o tipo Session
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.metric_service import MetricService
from analytics_api.core.config import settings
import logging

logger = logging.getLogger(__name__)

# --- Camada de Conexão (DB) ---

# Não precisamos mais do get_db_connector()

def get_postgres_repository(
    # Pede a Session diretamente usando a função da lib via Depends
    db_session: Session = Depends(get_vizu_db_session)
) -> PostgresRepository:
    """
    Instancia o Repositório de dados Prata.
    Recebe a sessão ativa do banco de dados via injeção de dependência.
    """
    logger.debug("Criando instância de PostgresRepository com sessão injetada.")
    # Passa a sessão ativa para o construtor do repositório
    return PostgresRepository(db_session=db_session)

# --- Camada de Autenticação (Simulada) ---

def get_client_id_from_token() -> str:
    """
    Simulação da extração do client_id a partir do Token JWT (Auth).
    Em produção, isto leria o header Authorization.

    Para o nosso MVP, usamos o ID mockado da Fazenda Soledade (ou outro).
    """
    client_id = settings.MOCK_CLIENT_ID
    logger.debug(f"Usando client_id mockado: {client_id}")
    if not client_id:
        logger.error("Client ID não configurado nas settings (MOCK_CLIENT_ID).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client ID não encontrado (Simulação de Token inválido)"
        )
    return client_id

# --- Camada de Serviço (O Cérebro) ---

def get_metric_service(
    # Pede o repositório, que por sua vez pede a sessão do banco
    repo: PostgresRepository = Depends(get_postgres_repository),
    # Pede o client_id (simulado)
    client_id: str = Depends(get_client_id_from_token)
) -> MetricService:
    """
    Função injetável principal (Dependency Injector).

    Cria a instância do MetricService para a requisição atual.
    O MetricService carrega o DataFrame Prata do cliente em memória
    (via PostgresRepository) e fica pronto para os cálculos.
    """
    logger.info(f"Inicializando MetricService para client_id: {client_id}")
    try:
        # A instância do serviço é criada POR REQUISIÇÃO.
        # Isto garante que o self.df carregado pertence ao cliente correto
        # e evita vazamento de dados entre clientes concorrentes.
        service_instance = MetricService(repository=repo, client_id=client_id)
        logger.info(f"MetricService inicializado com sucesso para {client_id}.")
        return service_instance
    except ValueError as e:
        # Ex: Mapeamento Prata não encontrado para o client_id em analytics_mapping.py
        logger.error(f"Erro ao inicializar MetricService para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Ex: Falha ao executar a query no PostgresRepository
        logger.error(f"Erro fatal ao inicializar MetricService para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao inicializar o serviço de métricas: {e}"
        )