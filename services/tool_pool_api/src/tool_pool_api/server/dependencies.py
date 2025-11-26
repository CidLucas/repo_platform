import logging
import os
from functools import lru_cache
from typing import Optional, List

# --- CORREÇÃO AQUI ---
from fastapi import Depends
# ---------------------
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import AccessToken, get_access_token
# Importa o provider OAuth pré-configurado para Google
from fastmcp.server.auth.providers.google import GoogleProvider

from tool_pool_api.core.config import Settings, get_settings

# Importações Vizu
from vizu_context_service.context_service import ContextService
from vizu_context_service.dependencies import \
    get_context_service as get_vizu_context_service
from vizu_models.vizu_client_context import VizuClientContext

logger = logging.getLogger(__name__)

# --- DEPENDÊNCIAS DE SERVIÇO VIZU (Existentes) ---

@lru_cache
def get_app_settings() -> Settings:
    return get_settings()

@lru_cache
def get_context_service() -> ContextService:
    logger.debug("Getting context service")
    return get_vizu_context_service()

async def load_context_from_token(
    ctx_service: ContextService,
    access_token: Optional[AccessToken]
) -> VizuClientContext:
    """
    Função helper pura e testável.
    Carrega o VizuClientContext com base no token de acesso.
    """
    try:
        if not access_token:
            logger.warning("Tentativa de acesso sem AccessToken no contexto.")
            raise ToolError("Autenticação necessária. Token não encontrado.")

        # O 'sub' (subject) do token JWT é o ID do usuário externo
        external_user_id = access_token.claims.get("sub")
        user_email = access_token.claims.get("email", "EmailNãoDisponível")

        if not external_user_id:
            logger.error(f"Token inválido. Claim 'sub' (subject) não encontrada. Email: {user_email}")
            raise ToolError("Token de autenticação inválido: 'subject' não encontrado.")

        logger.debug(
            f"Carregando contexto 'lazy' para external_user_id: {external_user_id} "
            f"(Email: {user_email})"
        )

        vizu_context = await ctx_service.get_context_by_external_user_id(
            external_user_id=external_user_id
        )

        if not vizu_context:
            logger.error(
                f"Contexto Vizu não encontrado para o external_user_id: {external_user_id} "
                f"(Email: {user_email})"
            )
            raise ToolError(
                f"Nenhum cliente Vizu associado a este usuário. (ID: {external_user_id})"
            )

        # Sucesso!
        return vizu_context

    except Exception as e:
        if isinstance(e, ToolError):
            raise e
        logger.error(
            f"Falha ao carregar VizuClientContext da dependência: {e}",
            exc_info=True
        )
        raise ToolError("Erro interno ao autorizar o contexto do cliente.")
# --- NOVAS DEPENDÊNCIAS DE AUTENTICAÇÃO (OAuth) ---

def _get_google_secret(secret_id: str) -> Optional[str]:
    """
    Busca o Google Client Secret.

    Para testes (conforme combinado), lê da variável de ambiente
    'MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV'.
    Em produção, deve buscar do Google Secret Manager usando 'secret_id'.
    """
    if not secret_id:
        logger.warning(
            "'MCP_AUTH_GOOGLE_CLIENT_SECRET_ID' não configurado. "
            "Tentando fallback para .env 'MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV'..."
        )

    # Lógica de fallback para testes com .env
    dev_secret = os.getenv("MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV")
    if dev_secret:
        logger.debug("Usando Google Client Secret do .env (MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV)")
        return dev_secret

    if not secret_id:
        logger.error("Nenhum ID de secret nem segredo de dev (.env) fornecidos para o Google Auth.")
        return None

    # --- LÓGICA DE PRODUÇÃO (Google Secret Manager) ---
    # TODO: Implementar a busca do 'secret_id' no Google Secret Manager
    logger.warning(
        f"Lógica do Secret Manager para '{secret_id}' ainda não implementada. "
        "Auth falhará se o segredo de dev não estiver no .env."
    )
    return None # Retorna None por enquanto


@lru_cache
def get_auth_provider() -> Optional[GoogleProvider]:
    """
    Instancia e retorna o GoogleProvider (OAuthProxy) se configurado.
    Esta função é cacheada e chamada na inicialização do servidor.
    """
    settings = get_app_settings()

    google_secret = _get_google_secret(
        settings.MCP_AUTH_GOOGLE_CLIENT_SECRET_ID
    )

    if not all([
        settings.MCP_AUTH_GOOGLE_CLIENT_ID,
        google_secret,
        settings.MCP_AUTH_BASE_URL
    ]):
        logger.warning(
            "Autenticação Google (OAuth) desabilitada. Faltam uma ou mais configs: "
            "MCP_AUTH_GOOGLE_CLIENT_ID, MCP_AUTH_GOOGLE_CLIENT_SECRET_ID (ou _DEV), "
            "ou MCP_AUTH_BASE_URL."
        )
        return None

    try:
        # Parseia os escopos do .env (string separada por vírgula)
        scopes = [
            scope.strip() for scope in settings.MCP_AUTH_REQUIRED_SCOPES.split(",")
            if scope.strip()
        ]
        if not scopes:
            logger.warning("Nenhum 'MCP_AUTH_REQUIRED_SCOPES' definido, usando padrões.")
            scopes = ["email", "profile"] # Escopos mínimos

        logger.info(f"Configurando GoogleProvider com escopos: {scopes}")

        provider = GoogleProvider(
            client_id=settings.MCP_AUTH_GOOGLE_CLIENT_ID,
            client_secret=google_secret,
            base_url=settings.MCP_AUTH_BASE_URL,
            required_scopes=scopes
        )
        logger.info("GoogleProvider (OAuthProxy) instanciado com sucesso.")
        return provider

    except Exception as e:
        logger.error(f"Falha ao instanciar GoogleProvider: {e}", exc_info=True)
        return None


async def get_current_vizu_context(
    ctx_service: ContextService = Depends(get_context_service)
) -> VizuClientContext:
    """
    Dependência FastMCP para "lazy load" do VizuClientContext.
    """
    try:


        user_email = access_token.claims.get("email", "EmailNãoDisponível")
        logger.debug(
            f"Carregando contexto 'lazy' para external_user_id: {external_user_id} "
            f"(Email: {user_email})"
        )

        vizu_context = await ctx_service.get_context_by_external_user_id(
            external_user_id=external_user_id
        )

        if not vizu_context:
            logger.error(
                f"Contexto Vizu não encontrado para o external_user_id: {external_user_id} "
                f"(Email: {user_email})"
            )
            raise ToolError(
                f"Nenhum cliente Vizu associado a este usuário. (ID: {external_user_id})"
            )

        return vizu_context

    except Exception as e:
        if isinstance(e, ToolError):
            raise e
        logger.error(
            f"Falha ao carregar VizuClientContext da dependência: {e}",
            exc_info=True
        )
        raise ToolError("Erro interno ao autorizar o contexto do cliente.")