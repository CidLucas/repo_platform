"""
Adapter for resolving cliente_id from external_user_id via ContextService.

With JWT-only authentication (Supabase), the external_user_id (JWT sub claim)
IS the cliente_id (Supabase user UUID). This adapter provides the lookup
function expected by the MCP auth middleware.
"""

from collections.abc import Awaitable, Callable
from uuid import UUID


def external_user_lookup_from_context_service(
    context_service: object,
) -> Callable[[str], Awaitable[str | None]]:
    """
    Returns an async lookup function that resolves external_user_id to cliente_id.

    With JWT-only auth, the external_user_id (JWT sub) IS the cliente_id,
    so this lookup simply validates the UUID format and returns it.

    For backwards compatibility with API-key flows (if ever needed), this could
    be extended to query the ContextService for mappings.

    Args:
        context_service: ContextService instance (currently unused for JWT-only flow)

    Returns:
        Async function: (external_user_id: str) -> cliente_id: str | None
    """

    async def lookup(external_user_id: str) -> str | None:
        """
        Resolve external_user_id to cliente_id.

        With JWT-only authentication, the external_user_id from the JWT sub claim
        IS the Supabase user UUID, which is also the cliente_id.

        Args:
            external_user_id: The external user identifier (JWT sub claim)

        Returns:
            The cliente_id (same as external_user_id for JWT auth), or None if invalid
        """
        if not external_user_id:
            return None

        # Validate UUID format
        try:
            UUID(external_user_id)
            return external_user_id
        except (ValueError, TypeError):
            # Invalid UUID format
            return None

    return lookup
