"""
Authentication helpers for Vendas Agent API.

Uses vizu_auth for JWT and API key validation.
"""

import logging

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vizu_auth.adapters.context_service_adapter import (
    api_key_lookup_from_context_service,
    external_user_lookup_from_context_service,
)
from vizu_auth.fastapi import create_auth_dependency
from vizu_context_service.context_service import ContextService
from vizu_context_service.dependencies import get_context_service

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_result(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-KEY"),
    ctx_service: ContextService = Depends(get_context_service),
):
    """
    Dependency FastAPI que constrói, em runtime, um `AuthDependencyFactory`
    usando o `ContextService` e os adapters; em seguida delega a validação
    para `AuthDependencyFactory.get_auth_result`.
    """

    # Cria funções de lookup atreladas à instância do ContextService
    api_key_lookup = api_key_lookup_from_context_service(ctx_service)
    external_user_lookup = external_user_lookup_from_context_service(ctx_service)

    # Cria factory (leve) e delega a validação passando os objetos já resolvidos
    auth_factory = create_auth_dependency(
        api_key_lookup_fn=api_key_lookup,
        external_user_lookup_fn=external_user_lookup,
        allow_auth_disabled=False,
    )

    # Delegamos chamando o método do factory passando explicitamente os valores
    return await auth_factory.get_auth_result(
        request=request,
        credentials=credentials,
        x_api_key=x_api_key,
    )
