"""
FastAPI dependencies for blu_auth.
"""

from blu_auth.dependencies.jwt_only import get_jwt_claims

__all__ = ["get_jwt_claims"]
