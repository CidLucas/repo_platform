"""
FastMCP middleware helpers for vizu_auth.

Provides a decorator factory `mcp_inject_cliente_id` which, when applied to
tool callables, will attempt to resolve `cliente_id` from the FastMCP
`AccessToken` (via `get_access_token`) and inject it into the tool kwargs
as `cliente_id` when not already provided.

This middleware is intentionally lightweight and non-invasive: if no
access token is present or no mapping exists, it leaves the kwargs
unchanged and lets the tool handle auth/fallbacks.
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps

logger = logging.getLogger(__name__)

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token, get_http_headers

from vizu_auth.adapters.context_service_adapter import external_user_lookup_from_context_service


def mcp_inject_cliente_id(get_context_service_fn: Callable[[], object]) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """
    Factory that returns a decorator for FastMCP tool callables.

    Args:
        get_context_service_fn: Callable (no-arg) that returns a ContextService
            instance at runtime (typically imported from the host app's
            dependencies module, e.g. `tool_pool_api.server.dependencies.get_context_service`).

    Usage:
        @mcp_inject_cliente_id(get_context_service)
        async def my_tool(..., cliente_id: str | None = None):
            ...
    """

    def decorator(fn: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # Priority for cliente_id resolution:
            # 1. X-Cliente-Id header (set by atendente_core after JWT validation)
            # 2. AccessToken claims.sub -> lookup via ContextService
            # 3. Caller-provided cliente_id (fallback)

            cliente_id = None

            # Method 1: Check X-Cliente-Id header (preferred for internal calls)
            # This is set by atendente_core which already validated the JWT
            headers = get_http_headers(include_all=True)
            header_cliente_id = headers.get("x-cliente-id")
            if header_cliente_id:
                cliente_id = header_cliente_id
                logger.info(f"[mcp_inject_cliente_id] Got cliente_id from X-Cliente-Id header: {cliente_id}")

            # Method 2: Try JWT claims.sub if no header
            if not cliente_id:
                try:
                    access_token = get_access_token()
                except Exception:
                    access_token = None

                if access_token:
                    external_user_id = getattr(access_token, "claims", {}).get("sub") if hasattr(access_token, "claims") else None
                    if external_user_id:
                        logger.debug(f"[mcp_inject_cliente_id] Trying to resolve from JWT sub: {external_user_id}")
                        try:
                            ctx_service = get_context_service_fn()
                            lookup = external_user_lookup_from_context_service(ctx_service)
                            cliente_id = await lookup(external_user_id)
                            if cliente_id:
                                logger.info(f"[mcp_inject_cliente_id] Resolved cliente_id from JWT: {cliente_id}")
                        except ToolError:
                            raise
                        except Exception as e:
                            logger.warning(f"[mcp_inject_cliente_id] Failed to resolve from JWT: {e}")

            # Inject cliente_id if resolved
            if cliente_id:
                kwargs["cliente_id"] = str(cliente_id)
            else:
                logger.warning("[mcp_inject_cliente_id] No cliente_id resolved, using caller-provided value")

            return await fn(*args, **kwargs)

        return wrapper

    return decorator
