"""
Adapter for resolving cliente_id from external_user_id via ContextService.

With JWT-only authentication (Supabase):
- external_user_id (JWT sub claim) = Supabase Auth user ID
- cliente_id (internal) = Vizu's internal client ID

These are intentionally different:
- external_user_id: Used for authentication with external providers (Supabase Auth)
- cliente_id (id): Used internally for data isolation (RLS, caching, etc.)

This adapter queries the database to resolve external_user_id -> cliente_id.
"""

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

logger = logging.getLogger(__name__)


def external_user_lookup_from_context_service(
    context_service: object,
) -> Callable[[str], Awaitable[str | None]]:
    """
    Returns an async lookup function that resolves external_user_id to cliente_id.

    Looks up the cliente_vizu record by external_user_id and returns the internal id.

    Args:
        context_service: ContextService instance (used to lookup cliente by external_user_id)

    Returns:
        Async function: (external_user_id: str) -> cliente_id: str | None
    """

    async def lookup(external_user_id: str) -> str | None:
        """
        Resolve external_user_id to cliente_id by querying the database.

        Args:
            external_user_id: The external user identifier (JWT sub claim / Supabase Auth user ID)

        Returns:
            The internal cliente_id, or None if not found
        """
        if not external_user_id:
            return None

        # Validate UUID format
        try:
            UUID(external_user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid UUID format for external_user_id: {external_user_id}")
            return None

        # Lookup cliente by external_user_id using ContextService
        try:
            client_context = await context_service.get_client_context_by_external_user_id(
                external_user_id
            )

            if client_context:
                cliente_id = str(client_context.id)
                logger.debug(
                    f"Resolved external_user_id={external_user_id} -> cliente_id={cliente_id}"
                )
                return cliente_id

            logger.warning(f"No cliente found for external_user_id: {external_user_id}")
            return None

        except Exception as e:
            logger.error(f"Error looking up cliente by external_user_id: {e}")
            return None

    return lookup
