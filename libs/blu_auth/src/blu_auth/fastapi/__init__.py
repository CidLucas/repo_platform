"""
FastAPI integration exports for blu_auth.
"""

from blu_auth.fastapi.dependencies import (
	get_admin_auth_result,
	get_auth_result,
	get_optional_auth_result,
)

__all__ = [
	"get_admin_auth_result",
	"get_auth_result",
	"get_optional_auth_result",
]
