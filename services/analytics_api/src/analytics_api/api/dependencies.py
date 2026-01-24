import logging
from typing import Optional

from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.indicator_service import IndicatorService
from analytics_api.services.metric_service import MetricService
from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from vizu_auth.dependencies.jwt_only import get_jwt_claims
from vizu_db_connector.database import get_db_session as get_vizu_db_session

logger = logging.getLogger(__name__)

# --- Camada de Conexão (DB) ---

def get_postgres_repository() -> PostgresRepository:
    """
    Create PostgresRepository instance.
    Now uses Supabase SDK for all operations (not direct SQLAlchemy).
    """
    logger.debug("Creating PostgresRepository instance (Supabase SDK).")
    return PostgresRepository()

# --- Camada de Autenticação (Real - No More Mocks!) ---

async def get_client_id(
    request: Request,
    client_id_param: Optional[str] = Query(None, alias="client_id"),
    db_session: Session = Depends(get_vizu_db_session),
) -> str:
    """
    Extract client_id from multiple sources (priority order):
    1. Query parameter ?client_id=xxx (for internal service-to-service calls)
    2. X-Client-ID header (for internal service calls)
    3. JWT token sub claim -> resolved to clientes_vizu.client_id

    IMPORTANT: JWT sub claim is the Supabase user ID (external_user_id).
    We must resolve it to the clientes_vizu.client_id for proper data isolation.
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
            from sqlalchemy import text

            token = auth_header.replace("Bearer ", "")
            claims = decode_jwt(token)
            if claims and claims.sub:
                external_user_id = claims.sub
                logger.debug(f"JWT sub (external_user_id): {external_user_id}")

                # Resolve external_user_id to clientes_vizu.client_id
                result = db_session.execute(
                    text("SELECT client_id FROM clientes_vizu WHERE external_user_id = :external_user_id"),
                    {"external_user_id": external_user_id}
                ).fetchone()

                if result:
                    actual_client_id = str(result[0])
                    logger.info(f"Resolved external_user_id={external_user_id} to client_id={actual_client_id}")
                    return actual_client_id
                else:
                    # User exists in Supabase but not in clientes_vizu
                    # Create a record for them
                    logger.warning(f"No clientes_vizu record for external_user_id={external_user_id}, creating one")
                    new_result = db_session.execute(
                        text("""
                            INSERT INTO clientes_vizu (external_user_id, nome_empresa, tipo_cliente, tier, created_at, updated_at)
                            VALUES (:external_user_id, :nome_empresa, 'standard', 'free', NOW(), NOW())
                            ON CONFLICT (external_user_id) DO UPDATE SET updated_at = NOW()
                            RETURNING client_id
                        """),
                        {"external_user_id": external_user_id, "nome_empresa": claims.email or "Empresa"}
                    ).fetchone()
                    db_session.commit()
                    actual_client_id = str(new_result[0])
                    logger.info(f"Created clientes_vizu record: external_user_id={external_user_id} -> client_id={actual_client_id}")
                    return actual_client_id
        except Exception as e:
            logger.warning(f"Failed to decode JWT or resolve client_id: {e}")

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

    Loads silver data, computes aggregations, and persists to analytics_v2 tables.
    """
    try:
        service_instance = MetricService(repository=repo, client_id=client_id)
        logger.info(f"MetricService initialized with persistence to analytics_v2 for {client_id}.")
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
    MetricService automatically persists aggregations to analytics_v2 tables.
    """
    try:
        service_instance = MetricService(repository=repo, client_id=client_id)
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
