"""
Configuração de autenticação carregada de variáveis de ambiente.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """
    Configurações de autenticação.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === JWT (Supabase) ===
    supabase_jwt_secret: str = ""
    supabase_jwt_jwk: str = ""  # JSON Web Key for ES256/RS256
    jwt_algorithm: str = "ES256"  # Default to ES256 for Supabase
    jwt_audience: str = "authenticated"

    # === Desenvolvimento ===
    auth_enabled: bool = True

    # Claim customizada para client_id
    jwt_client_id_claim: str = "client_id"

    @property
    def has_jwt_secret(self) -> bool:
        """Verifica se o secret JWT está configurado e tem tamanho mínimo."""
        # For ES256/RS256, we need JWK. For HS256, we need secret.
        if self.jwt_algorithm in ("ES256", "RS256"):
            return bool(self.supabase_jwt_jwk and len(self.supabase_jwt_jwk) >= 10)
        return bool(self.supabase_jwt_secret and len(self.supabase_jwt_secret) >= 32)

    def validate_production_config(self) -> None:
        if self.auth_enabled and not self.has_jwt_secret:
            raise ValueError(
                "SUPABASE_JWT_SECRET não configurado ou muito curto."
            )


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()


def clear_auth_settings_cache() -> None:
    get_auth_settings.cache_clear()
