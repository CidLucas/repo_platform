"""
FastAPI integration exports for vizu_auth.
"""

from vizu_auth.fastapi.dependencies import (
	get_auth_result,
	get_optional_auth_result,
)

__all__ = [
	"get_auth_result",
	"get_optional_auth_result",
]
