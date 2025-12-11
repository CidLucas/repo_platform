"""
Authentication and context injection middleware for MCP services.

Provides decorators and middleware for:
- Automatic client context injection
- Tool access validation
- Tier-based authorization
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any
from uuid import UUID

from vizu_mcp_commons.auth import MCPTokenExtractor
from vizu_mcp_commons.exceptions import (
    MCPAuthError,
    MCPContextError,
    MCPTierAccessError,
    MCPToolDisabledError,
)
from vizu_models.vizu_client_context import VizuClientContext

logger = logging.getLogger(__name__)


def inject_cliente_context(
    get_context_service_fn: Callable[[], Any],
    require_auth: bool = True,
    validate_tool: str | None = None,
) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """
    Decorator factory that injects VizuClientContext into tool functions.

    This middleware:
    1. Extracts external_user_id from FastMCP AccessToken
    2. Resolves the corresponding VizuClientContext
    3. Injects it as `cliente_context` kwarg
    4. Optionally validates tool access

    Args:
        get_context_service_fn: Factory function that returns ContextService
        require_auth: If True, raises MCPAuthError when no auth token found
        validate_tool: If set, validates that client has access to this tool

    Usage:
        @inject_cliente_context(get_context_service)
        async def my_tool(query: str, *, cliente_context: VizuClientContext) -> str:
            return f"Hello {cliente_context.nome_cliente}"
    """

    def decorator(fn: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # Skip if context already provided
            if "cliente_context" in kwargs and kwargs["cliente_context"] is not None:
                return await fn(*args, **kwargs)

            # Try to get cliente_id from kwargs (tunnel mode)
            cliente_id = kwargs.get("cliente_id")
            cliente_context: VizuClientContext | None = None

            if cliente_id:
                # Tunnel mode: cliente_id explicitly provided
                logger.debug(f"Using injected cliente_id: {cliente_id}")
                cliente_context = await _resolve_context_by_id(
                    get_context_service_fn, cliente_id
                )
            else:
                # Token mode: extract from FastMCP context
                external_user_id = MCPTokenExtractor.extract_external_user_id()

                if external_user_id:
                    logger.debug(f"Resolving context for external_user_id: {external_user_id}")
                    cliente_context = await _resolve_context_by_external_id(
                        get_context_service_fn, external_user_id
                    )
                elif require_auth:
                    raise MCPAuthError("Autenticação necessária. Token não encontrado.")

            if cliente_context is None and require_auth:
                raise MCPContextError("Não foi possível resolver o contexto do cliente.")

            # Validate tool access if specified
            if validate_tool and cliente_context:
                _validate_tool_access(cliente_context, validate_tool)

            # Inject context
            kwargs["cliente_context"] = cliente_context

            return await fn(*args, **kwargs)

        return wrapper

    return decorator


async def _resolve_context_by_id(
    get_context_service_fn: Callable,
    cliente_id: str,
) -> VizuClientContext:
    """Resolve VizuClientContext by cliente_id UUID."""
    try:
        uuid_obj = UUID(cliente_id)
    except ValueError:
        raise MCPContextError(f"ID de cliente inválido: {cliente_id}")

    ctx_service = get_context_service_fn()
    try:
        context = await ctx_service.get_client_context_by_id(uuid_obj)
        if not context:
            raise MCPContextError(f"Contexto não encontrado para ID: {cliente_id}")
        return context
    except MCPContextError:
        raise
    except Exception as e:
        logger.exception(f"Error resolving context by ID: {e}")
        raise MCPContextError("Erro interno ao carregar contexto do cliente.")


async def _resolve_context_by_external_id(
    get_context_service_fn: Callable,
    external_user_id: str,
) -> VizuClientContext:
    """Resolve VizuClientContext by external user ID (OAuth sub claim)."""
    ctx_service = get_context_service_fn()
    try:
        context = await ctx_service.get_context_by_external_user_id(
            external_user_id=external_user_id
        )
        if not context:
            raise MCPContextError(
                f"Nenhum cliente Vizu associado a este usuário. (ID: {external_user_id})"
            )
        return context
    except MCPContextError:
        raise
    except Exception as e:
        logger.exception(f"Error resolving context by external ID: {e}")
        raise MCPContextError("Erro interno ao carregar contexto do cliente.")


def _validate_tool_access(context: VizuClientContext, tool_name: str) -> None:
    """Validate that client has access to the specified tool."""
    enabled_tools = context.get_enabled_tools_list()
    if tool_name not in enabled_tools:
        raise MCPToolDisabledError(
            f"Ferramenta '{tool_name}' não está habilitada para este cliente.",
            tool_name=tool_name,
        )


def require_tool(
    tool_name: str,
    get_context_service_fn: Callable[[], Any],
) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """
    Decorator that ensures client has access to a specific tool.

    Combines inject_cliente_context with tool validation.

    Usage:
        @require_tool("executar_rag_cliente", get_context_service)
        async def rag_tool(query: str, *, cliente_context: VizuClientContext) -> str:
            ...
    """
    return inject_cliente_context(
        get_context_service_fn,
        require_auth=True,
        validate_tool=tool_name,
    )


def require_tier(
    min_tier: str,
    get_context_service_fn: Callable[[], Any],
) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """
    Decorator that ensures client has minimum tier level.

    Usage:
        @require_tier("PROFISSIONAL", get_context_service)
        async def premium_tool(*, cliente_context: VizuClientContext) -> str:
            ...
    """

    def decorator(fn: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        @inject_cliente_context(get_context_service_fn, require_auth=True)
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            context: VizuClientContext = kwargs.get("cliente_context")
            if context:
                from vizu_models.enums import TierCliente

                try:
                    required = TierCliente(min_tier)
                    current = TierCliente(context.tier.value if hasattr(context.tier, 'value') else context.tier)

                    if current < required:
                        raise MCPTierAccessError(
                            f"Tier {min_tier} necessário para esta funcionalidade.",
                            required_tier=min_tier,
                            current_tier=current.value,
                        )
                except ValueError:
                    logger.warning(f"Invalid tier comparison: {min_tier} vs {context.tier}")

            return await fn(*args, **kwargs)

        return wrapper

    return decorator


class MCPAuthMiddleware:
    """
    FastAPI/Starlette middleware for MCP authentication.

    Validates tokens and attaches user context to request state.
    """

    def __init__(
        self,
        app,
        get_context_service_fn: Callable,
        exclude_paths: list | None = None,
    ):
        self.app = app
        self.get_context_service_fn = get_context_service_fn
        self.exclude_paths = exclude_paths or ["/health", "/info", "/docs", "/openapi.json"]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Extract and validate token
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if auth_header:
            try:
                from vizu_mcp_commons.auth import TokenValidator

                validator = TokenValidator()
                claims = validator.validate(auth_header)

                # Attach to scope for downstream use
                scope["user_claims"] = claims
            except MCPAuthError:
                # Log but don't block - let handlers decide
                pass

        await self.app(scope, receive, send)
