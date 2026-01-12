import logging
from typing import Optional

from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.indicator_service import IndicatorService
from analytics_api.services.metric_service import MetricService
from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from vizu_auth.dependencies.jwt_only import get_jwt_claims
from vizu_db_connector.database import get_db_session as get_vizu_db_session

logger = logging.getLogger(__name__)

# --- Camada de Conexão (DB) ---

def get_postgres_repository(
    db_session: Session = Depends(get_vizu_db_session)
) -> PostgresRepository:
    """
    Instancia o Repositório de dados Prata.
    Recebe a sessão ativa do banco de dados via injeção de dependência.
    """
    logger.debug("Criando instância de PostgresRepository com sessão injetada.")
    return PostgresRepository(db_session=db_session)

# --- Camada de Autenticação (Real - No More Mocks!) ---

async def get_client_id(
    request: Request,
    client_id_param: Optional[str] = Query(None, alias="client_id"),
) -> str:
    """
    Extract client_id from multiple sources (priority order):
    1. Query parameter ?client_id=xxx (for internal service-to-service calls)
    2. X-Client-ID header (for internal service calls)
    3. JWT token sub claim (for frontend user requests)

    This eliminates all mocks - real client_id is ALWAYS required.
    """
    # Priority 1: Query parameter (for ETL trigger calls)
    if client_id_param:
        logger.debug(f"Using client_id from query param: {client_id_param}")
        return client_id_param

    # Priority 2: X-Client-ID header (for internal service calls)
    header_client_id = request.headers.get("X-Client-ID")
    if header_client_id:
        logger.debug(f"Using client_id from X-Client-ID header: {header_client_id}")
        return header_client_id

    # Priority 3: JWT token (for frontend user requests)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # Extract and validate JWT
            from vizu_auth.core.jwt_decoder import decode_jwt
            token = auth_header.replace("Bearer ", "")
            claims = decode_jwt(token)
            if claims and claims.sub:
                logger.debug(f"Using client_id from JWT sub claim: {claims.sub}")
                return claims.sub
        except Exception as e:
            logger.warning(f"Failed to decode JWT for client_id: {e}")

    # No client_id found - this is an error
    logger.error("No client_id found in query params, headers, or JWT token")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Client ID required. Provide via ?client_id=, X-Client-ID header, or Authorization Bearer token."
    )

# --- Camada de Serviço (O Cérebro) ---

async def get_metric_service(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
) -> MetricService:
    """
    Função injetável principal (Dependency Injector) para consumo no frontend.

    Carrega dados prata apenas para leitura e NÃO persiste em tabelas ouro
    (write_gold=False). Use get_metric_service_ingest para fluxos de ingestão.
    """
    try:
        service_instance = MetricService(repository=repo, client_id=client_id, write_gold=False)
        logger.info(f"MetricService inicializado (read-only) para {client_id}.")
        return service_instance
    except ValueError as e:
        logger.error(f"Erro ao inicializar MetricService para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro fatal ao inicializar MetricService para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao inicializar o serviço de métricas: {e}"
        )


async def get_metric_service_ingest(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
) -> MetricService:
    """
    Dependency para fluxos de ingestão (ex.: modal de connector).
    Habilita persistência das agregações na camada ouro (write_gold=True).
    """
    try:
        service_instance = MetricService(repository=repo, client_id=client_id, write_gold=True)
        logger.info(f"MetricService inicializado (ingest) para {client_id}.")
        return service_instance
    except ValueError as e:
        logger.error(f"Erro ao inicializar MetricService (ingest) para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro fatal ao inicializar MetricService (ingest) para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao inicializar o serviço de métricas (ingest): {e}"
        )

async def get_indicator_service(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
) -> IndicatorService:
    """
    Cria instância do IndicatorService para indicadores com cache.
    """
    try:
        service_instance = IndicatorService(repository=repo, client_id=client_id)
        logger.info(f"IndicatorService inicializado para {client_id}.")
        return service_instance
    except Exception as e:
        logger.error(f"Erro ao inicializar IndicatorService para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao inicializar o serviço de indicadores: {e}"
        )
