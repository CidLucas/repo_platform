"""
JWT authentication for standalone_agent_api using vizu_auth.

Mirrors the pattern from atendente_core/api/auth.py.
"""

from vizu_auth.fastapi.dependencies import get_auth_result  # noqa: F401
from vizu_auth.core.models import AuthResult  # noqa: F401
