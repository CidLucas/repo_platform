"""
JWT authentication for standalone_agent_api using blu_auth.

Mirrors the pattern from atendente_core/api/auth.py.
"""

from blu_auth.core.models import AuthResult  # noqa: F401
from blu_auth.fastapi.dependencies import (
    get_admin_auth_result,  # noqa: F401
    get_auth_result,  # noqa: F401
)
