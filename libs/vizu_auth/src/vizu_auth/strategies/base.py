"""
Interface base para estratégias de autenticação.
"""

from abc import ABC, abstractmethod

from vizu_auth.core.models import AuthRequest, AuthResult


class AuthStrategy(ABC):
    @abstractmethod
    async def authenticate(self, request: AuthRequest) -> AuthResult | None:
        """Tenta autenticar. Retorna AuthResult se sucesso, None se não aplicável."""

    @abstractmethod
    def can_handle(self, request: AuthRequest) -> bool:
        """Indica se a estratégia pode processar essa request."""
