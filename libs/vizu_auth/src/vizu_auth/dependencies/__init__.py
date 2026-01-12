"""
FastAPI dependencies for vizu_auth.
"""

from vizu_auth.dependencies.jwt_only import get_jwt_claims

__all__ = ["get_jwt_claims"]
