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

from collections.abc import Awaitable, Callable
from functools import wraps

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

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
            # If an access token is present we will prefer server-resolved cliente_id
            # over any caller-supplied value. If no access token is present we
            # preserve any provided cliente_id (legacy tunnel usage).

            try:
                access_token = get_access_token()
            except Exception:
                # get_access_token may raise if not in a request context; fallback.
                access_token = None

            if access_token is None:
                # No token available: preserve caller-provided cliente_id
                return await fn(*args, **kwargs)

            external_user_id = getattr(access_token, "claims", {}).get("sub") if hasattr(access_token, "claims") else None

            if not external_user_id:
                return await fn(*args, **kwargs)

            # Resolve ContextService and perform lookup
            try:
                ctx_service = get_context_service_fn()
                lookup = external_user_lookup_from_context_service(ctx_service)
                cliente_id = await lookup(external_user_id)
                if cliente_id:
                    # Override any caller-provided cliente_id with server-resolved one.
                    kwargs["cliente_id"] = str(cliente_id)
            except ToolError:
                # ToolError indicates authentication/authorization problems — re-raise
                raise
            except Exception:
                # Any failure resolving should be non-fatal for injection; continue
                pass

            return await fn(*args, **kwargs)

        return wrapper

    return decorator
