"""Authentication dependencies for file_upload_api.

Thin adapter around the canonical helpers in
``vizu_auth.fastapi.dependencies`` so all services share the same JWT
parsing, validation, and 401-mapping behaviour.
"""

import logging
import uuid

from fastapi import Depends

from vizu_auth.core.models import AuthResult
from vizu_auth.fastapi.dependencies import get_auth_result

logger = logging.getLogger(__name__)


async def get_client_id_from_token(
    auth: AuthResult = Depends(get_auth_result),
) -> uuid.UUID:
    """Return the authenticated tenant's ``client_id`` (UUID).

    Delegates JWT parsing and 401 handling to
    :func:`vizu_auth.fastapi.dependencies.get_auth_result`. Kept as a
    convenience wrapper because the upload endpoints only need the
    ``client_id`` and never the rest of :class:`AuthResult`.
    """
    logger.debug("file_upload_api: authenticated client_id=%s", auth.client_id)
    return auth.client_id
