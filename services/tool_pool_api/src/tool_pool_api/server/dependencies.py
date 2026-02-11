import logging
import os
from functools import lru_cache

import redis
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import AccessToken

from tool_pool_api.core.config import Settings, get_settings

# Importações Vizu
from vizu_context_service.context_service import ContextService
from vizu_context_service.redis_service import RedisService
from vizu_models.vizu_client_context import VizuClientContext

logger = logging.getLogger(__name__)

# ============================================================================
# DEPENDÊNCIAS DE INFRAESTRUTURA (Singletons)
# ============================================================================


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


# Pool Redis compartilhado
_redis_pool: redis.ConnectionPool | None = None


def _get_redis_pool() -> redis.ConnectionPool:
    """Obtém ou cria o pool de conexões Redis (singleton)."""
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required but not set")
        _redis_pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
        logger.info(f"Pool Redis criado: {redis_url}")
    return _redis_pool


_context_service: ContextService | None = None


def get_context_service() -> ContextService:
    """
    Returns singleton ContextService with shared Redis pool.

    The ContextService is stateless beyond the Redis pool and Supabase client,
    both of which are already singletons, so a single instance is safe to reuse.
    """
    global _context_service
    if _context_service is None:
        pool = _get_redis_pool()
        redis_client = redis.Redis(connection_pool=pool)
        redis_service = RedisService(redis_client=redis_client)
        _context_service = ContextService(
            cache_service=redis_service, use_supabase=True
        )
        logger.info("ContextService singleton created (tool_pool_api)")
    return _context_service


# ============================================================================
# HELPERS DE CONTEXTO
# ============================================================================


async def load_context_from_token(
    ctx_service: ContextService, access_token: AccessToken | None
) -> VizuClientContext:
    """
    Função helper para carregar VizuClientContext com base no token de acesso.

    Args:
        ctx_service: Instância do ContextService
        access_token: Token JWT do usuário

    Returns:
        VizuClientContext do cliente associado

    Raises:
        ToolError: Se autenticação falhar ou cliente não for encontrado
    """
    if not access_token:
        logger.warning("Tentativa de acesso sem AccessToken no contexto.")
        raise ToolError("Autenticação necessária. Token não encontrado.")

    external_user_id = access_token.claims.get("sub")
    user_email = access_token.claims.get("email", "EmailNãoDisponível")

    if not external_user_id:
        logger.error(f"Token inválido. Claim 'sub' não encontrada. Email: {user_email}")
        raise ToolError("Token de autenticação inválido: 'subject' não encontrado.")

    logger.debug(
        f"Carregando contexto para external_user_id: {external_user_id} (Email: {user_email})"
    )

    try:
        vizu_context = await ctx_service.get_client_context_by_external_user_id(
            external_user_id=external_user_id
        )

        if not vizu_context:
            logger.error(
                f"Contexto Vizu não encontrado para external_user_id: {external_user_id}"
            )
            raise ToolError(
                f"Nenhum cliente Vizu associado a este usuário. (ID: {external_user_id})"
            )

        return vizu_context

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Falha ao carregar VizuClientContext: {e}", exc_info=True)
        raise ToolError("Erro interno ao autorizar o contexto do cliente.")


# ============================================================================
# AUTENTICAÇÃO OAUTH (Google)
# ============================================================================


def _get_google_secret(secret_id: str) -> str | None:
    """
    Busca o Google Client Secret.

    Para testes, lê de 'MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV'.
    Em produção, deve buscar do Google Secret Manager.
    """
    # Fallback para desenvolvimento
    dev_secret = os.getenv("MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV")
    if dev_secret:
        logger.debug(
            "Usando Google Client Secret do .env (MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV)"
        )
        return dev_secret

    if not secret_id:
        logger.warning(
            "Nenhum ID de secret nem segredo de dev fornecidos para Google Auth."
        )
        return None

    # TODO: Implementar busca no Google Secret Manager
    logger.warning(f"Lógica do Secret Manager para '{secret_id}' não implementada.")
    return None


@lru_cache
def get_auth_provider() -> GoogleProvider | None:
    """
    Instancia e retorna o GoogleProvider se configurado.
    """
    settings = get_app_settings()

    google_secret = _get_google_secret(settings.MCP_AUTH_GOOGLE_CLIENT_SECRET_ID)

    if not all(
        [settings.MCP_AUTH_GOOGLE_CLIENT_ID, google_secret, settings.MCP_AUTH_BASE_URL]
    ):
        logger.warning(
            "Autenticação Google desabilitada. Faltam configs: "
            "MCP_AUTH_GOOGLE_CLIENT_ID, MCP_AUTH_GOOGLE_CLIENT_SECRET, MCP_AUTH_BASE_URL"
        )
        return None

    try:
        scopes = [
            scope.strip()
            for scope in settings.MCP_AUTH_REQUIRED_SCOPES.split(",")
            if scope.strip()
        ]
        if not scopes:
            scopes = ["email", "profile"]

        logger.info(f"Configurando GoogleProvider com escopos: {scopes}")

        provider = GoogleProvider(
            client_id=settings.MCP_AUTH_GOOGLE_CLIENT_ID,
            client_secret=google_secret,
            base_url=settings.MCP_AUTH_BASE_URL,
            required_scopes=scopes,
        )
        logger.info("GoogleProvider instanciado com sucesso.")
        return provider

    except Exception as e:
        logger.error(f"Falha ao instanciar GoogleProvider: {e}", exc_info=True)
        return None
