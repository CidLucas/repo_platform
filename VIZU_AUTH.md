# 🔐 Implementação: Biblioteca `vizu_auth` - Autenticação Centralizada

## 📋 Visão Geral

**Objetivo:** Criar `libs/vizu_auth` para centralizar autenticação JWT (Supabase) e API-Key em todos os serviços do monorepo.

**Princípios:**
- Modularidade: Core sem dependências pesadas
- Simplicidade: Estratégias plugáveis (JWT, API-Key)
- Segurança: `cliente_vizu_id` derivado APENAS de credenciais validadas
- Integração: FastAPI dependencies + FastMCP middleware

---

## ✅ Checklist de Progresso

- [ ] **Fase 1:** Estrutura base e configuração
- [ ] **Fase 2:** Core (exceptions, models, JWT decoder)
- [ ] **Fase 3:** Estratégias de autenticação
- [ ] **Fase 4:** FastAPI dependencies
- [ ] **Fase 5:** Testes unitários
- [ ] **Fase 6:** Integração `atendente_core`
- [ ] **Fase 7:** Integração `tool_pool_api` (FastMCP)
- [ ] **Fase 8:** Atualizar outros serviços

---

# 📁 FASE 1: Estrutura Base e Configuração

## Task 1. 1: Criar estrutura de diretórios

**Tempo estimado:** 3 minutos

**Comandos:**
```bash
mkdir -p libs/vizu_auth/src/vizu_auth/core
mkdir -p libs/vizu_auth/src/vizu_auth/strategies
mkdir -p libs/vizu_auth/src/vizu_auth/fastapi
mkdir -p libs/vizu_auth/src/vizu_auth/mcp
mkdir -p libs/vizu_auth/tests

touch libs/vizu_auth/src/vizu_auth/__init__.py
touch libs/vizu_auth/src/vizu_auth/core/__init__.py
touch libs/vizu_auth/src/vizu_auth/strategies/__init__.py
touch libs/vizu_auth/src/vizu_auth/fastapi/__init__.py
touch libs/vizu_auth/src/vizu_auth/mcp/__init__.py
touch libs/vizu_auth/tests/__init__.py
```

**Estrutura final:**
```
libs/vizu_auth/
├── pyproject.toml
├── README.md
├── src/
│   └── vizu_auth/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── exceptions.py
│       │   ├── models.py
│       │   └── jwt_decoder.py
│       ├── strategies/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── jwt_strategy.py
│       │   └── api_key_strategy. py
│       ├── fastapi/
│       │   ├── __init__.py
│       │   └── dependencies.py
│       └── mcp/
│           ├── __init__.py
│           └── auth_middleware.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_jwt_decoder.py
    └── test_strategies.py
```

**Checkpoint ✓:**
```bash
find libs/vizu_auth -type f -name "*.py" | wc -l
# Deve retornar: 15 (ou mais)
```

---

## Task 1.2: Criar pyproject.toml

**Tempo estimado:** 3 minutos

**Arquivo:** `libs/vizu_auth/pyproject.toml`

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "vizu_auth"
version = "0.1.0"
description = "Centralized authentication library for Vizu services (JWT + API-Key)"
authors = ["Vizu Team"]
readme = "README.md"
packages = [{include = "vizu_auth", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
pyjwt = "^2.8.0"
pydantic = "^2.0"
pydantic-settings = "^2.0"

# Optional FastAPI integration
fastapi = {version = "^0.100.0", optional = true}

[tool.poetry.extras]
fastapi = ["fastapi"]

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-asyncio = "^0.21"
httpx = "^0.25. 0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth && poetry check
# Deve retornar: All set!
```

---

## Task 1.3: Criar configuração

**Tempo estimado:** 5 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/core/config.py`

```python
"""
Configuração de autenticação carregada de variáveis de ambiente.
Suporta Supabase JWT e API-Key.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """
    Configurações de autenticação.

    Variáveis de ambiente:
    - SUPABASE_JWT_SECRET: Secret para validar tokens Supabase (OBRIGATÓRIO em prod)
    - JWT_ALGORITHM: Algoritmo de assinatura (default: HS256)
    - JWT_AUDIENCE: Audience esperada (default: authenticated)
    - AUTH_ENABLED: Se False, bypassa autenticação (apenas dev)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === JWT (Supabase) ===
    supabase_jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "authenticated"

    # === Desenvolvimento ===
    # CUIDADO: Apenas para dev local.  Em prod DEVE ser True.
    auth_enabled: bool = True

    # === Claim customizada para cliente_vizu_id ===
    # Se o JWT contiver esta claim, usamos diretamente
    jwt_cliente_vizu_id_claim: str = "cliente_vizu_id"

    @property
    def has_jwt_secret(self) -> bool:
        """Verifica se o secret JWT está configurado."""
        return bool(self.supabase_jwt_secret and len(self.supabase_jwt_secret) >= 32)

    def validate_production_config(self) -> None:
        """Valida configuração para produção.  Lança exceção se inválida."""
        if self.auth_enabled and not self. has_jwt_secret:
            raise ValueError(
                "SUPABASE_JWT_SECRET não configurado ou muito curto. "
                "Configure a variável de ambiente ou defina AUTH_ENABLED=false para dev."
            )


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Retorna instância cacheada das configurações de auth."""
    return AuthSettings()


def clear_auth_settings_cache() -> None:
    """Limpa o cache de configurações.  Útil para testes."""
    get_auth_settings. cache_clear()
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core.config import get_auth_settings
s = get_auth_settings()
print(f'Auth enabled: {s.auth_enabled}')
print(f'Has JWT secret: {s.has_jwt_secret}')
print('Config OK')
"
```

---

# 📁 FASE 2: Core (Exceptions, Models, JWT Decoder)

## Task 2. 1: Criar exceptions

**Tempo estimado:** 3 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/core/exceptions.py`

```python
"""
Exceções customizadas para autenticação.
Hierarquia permite catch granular ou genérico.
"""


class AuthError(Exception):
    """Erro base de autenticação."""

    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR"):
        self.message = message
        self. code = code
        super().__init__(self.message)


class MissingCredentialsError(AuthError):
    """Credenciais não fornecidas (nem JWT nem API-Key)."""

    def __init__(self, message: str = "No authentication credentials provided"):
        super().__init__(message, code="MISSING_CREDENTIALS")


class InvalidTokenError(AuthError):
    """Token JWT inválido ou malformado."""

    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message, code="INVALID_TOKEN")


class TokenExpiredError(AuthError):
    """Token JWT expirado."""

    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message, code="TOKEN_EXPIRED")


class InvalidSignatureError(InvalidTokenError):
    """Assinatura do JWT inválida."""

    def __init__(self, message: str = "Token signature verification failed"):
        super().__init__(message)
        self.code = "INVALID_SIGNATURE"


class InvalidApiKeyError(AuthError):
    """API-Key inválida ou não encontrada."""

    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, code="INVALID_API_KEY")


class ClientNotFoundError(AuthError):
    """Cliente Vizu não encontrado para as credenciais fornecidas."""

    def __init__(self, message: str = "Client not found for provided credentials"):
        super().__init__(message, code="CLIENT_NOT_FOUND")


class AuthDisabledError(AuthError):
    """Autenticação desabilitada (apenas dev)."""

    def __init__(self, message: str = "Authentication is disabled"):
        super().__init__(message, code="AUTH_DISABLED")
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core.exceptions import (
    AuthError, MissingCredentialsError, InvalidTokenError,
    TokenExpiredError, InvalidApiKeyError, ClientNotFoundError
)
print('All exceptions imported OK')
"
```

---

## Task 2.2: Criar models

**Tempo estimado:** 5 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/core/models.py`

```python
"""
Modelos Pydantic para autenticação.
Independentes de framework (FastAPI, FastMCP, etc).
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    """Método de autenticação utilizado."""
    JWT = "jwt"
    API_KEY = "api_key"
    NONE = "none"  # Auth desabilitada (dev only)


class JWTClaims(BaseModel):
    """
    Claims extraídas de um token JWT Supabase.

    Claims padrão:
    - sub: ID do usuário no Supabase
    - email: Email do usuário
    - aud: Audience (deve ser 'authenticated')
    - exp: Timestamp de expiração
    - iat: Timestamp de emissão
    - role: Role do usuário

    Claims customizadas Vizu:
    - cliente_vizu_id: UUID do cliente (se presente)
    """

    # Claims padrão JWT
    sub: str = Field(... , description="Subject - Supabase user ID")
    aud: Optional[str] = Field(None, description="Audience")
    exp: Optional[int] = Field(None, description="Expiration timestamp")
    iat: Optional[int] = Field(None, description="Issued at timestamp")

    # Claims Supabase
    email: Optional[str] = Field(None, description="User email")
    phone: Optional[str] = Field(None, description="User phone")
    role: Optional[str] = Field(None, description="User role")

    # Claims customizadas Vizu
    cliente_vizu_id: Optional[UUID] = Field(
        None,
        description="Vizu client UUID (custom claim)"
    )

    # Metadados Supabase
    app_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"  # Permite claims adicionais


class AuthResult(BaseModel):
    """
    Resultado da autenticação.

    Este é o objeto principal retornado após autenticação bem-sucedida.
    Contém o cliente_vizu_id que deve ser usado para carregar o contexto.
    """

    # ID do cliente Vizu (SEMPRE presente após auth bem-sucedida)
    cliente_vizu_id: UUID = Field(..., description="Vizu client UUID")

    # Método de autenticação utilizado
    auth_method: AuthMethod = Field(... , description="Authentication method used")

    # ID do usuário externo (do JWT sub claim, se auth via JWT)
    external_user_id: Optional[str] = Field(
        None,
        description="External user ID from JWT"
    )

    # Email (se disponível)
    email: Optional[str] = Field(None, description="User email if available")

    # Claims originais (para auditoria/debug)
    raw_claims: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original JWT claims or API-Key metadata"
    )

    @property
    def is_jwt_auth(self) -> bool:
        """Retorna True se autenticação foi via JWT."""
        return self.auth_method == AuthMethod.JWT

    @property
    def is_api_key_auth(self) -> bool:
        """Retorna True se autenticação foi via API-Key."""
        return self.auth_method == AuthMethod.API_KEY


class AuthRequest(BaseModel):
    """
    Dados de entrada para autenticação.
    Usado internamente pelas estratégias.
    """

    # Token JWT (Authorization: Bearer <token>)
    jwt_token: Optional[str] = Field(None, description="JWT Bearer token")

    # API-Key (X-API-KEY header)
    api_key: Optional[str] = Field(None, description="API key")

    def has_credentials(self) -> bool:
        """Verifica se alguma credencial foi fornecida."""
        return bool(self.jwt_token or self.api_key)
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from uuid import uuid4
from vizu_auth.core.models import AuthResult, AuthMethod, JWTClaims

result = AuthResult(
    cliente_vizu_id=uuid4(),
    auth_method=AuthMethod.JWT,
    external_user_id='user-123'
)
print(f'Cliente ID: {result.cliente_vizu_id}')
print(f'Is JWT: {result.is_jwt_auth}')
print('Models OK')
"
```

---

## Task 2.3: Criar JWT decoder

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/core/jwt_decoder.py`

```python
"""
Decodificador e validador de tokens JWT.
Usa apenas pyjwt, sem dependências de framework.
"""

import logging
from typing import Optional
from uuid import UUID

import jwt

from vizu_auth.core. config import get_auth_settings
from vizu_auth.core.exceptions import (
    AuthError,
    InvalidSignatureError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.models import JWTClaims

logger = logging.getLogger(__name__)


def decode_jwt(
    token: str,
    *,
    verify_exp: bool = True,
    verify_aud: bool = True,
) -> JWTClaims:
    """
    Decodifica e valida um token JWT.

    Args:
        token: Token JWT string
        verify_exp: Verificar expiração (default: True)
        verify_aud: Verificar audience (default: True)

    Returns:
        JWTClaims com claims validadas

    Raises:
        InvalidTokenError: Token malformado ou inválido
        TokenExpiredError: Token expirado
        InvalidSignatureError: Assinatura inválida
        AuthError: Secret não configurado
    """
    settings = get_auth_settings()

    if not settings.has_jwt_secret:
        logger.error("JWT secret not configured")
        raise AuthError(
            "JWT authentication not configured. Set SUPABASE_JWT_SECRET.",
            code="CONFIG_ERROR"
        )

    # Remove "Bearer " prefix se presente
    if token.lower().startswith("bearer "):
        token = token[7:]

    token = token.strip()

    if not token:
        raise InvalidTokenError("Empty token provided")

    # Opções de decodificação
    options = {
        "verify_exp": verify_exp,
        "verify_aud": verify_aud and bool(settings.jwt_audience),
        "verify_signature": True,
    }

    audience = settings.jwt_audience if verify_aud else None

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=audience,
            options=options,
        )

        # Parse cliente_vizu_id se presente
        cliente_id_claim = settings.jwt_cliente_vizu_id_claim
        if cliente_id_claim in payload:
            raw_id = payload[cliente_id_claim]
            try:
                payload[cliente_id_claim] = UUID(str(raw_id))
            except (ValueError, TypeError):
                logger.warning(f"Invalid cliente_vizu_id in token: {raw_id}")
                payload[cliente_id_claim] = None

        logger.debug(f"JWT decoded successfully for sub: {payload.get('sub', 'unknown')}")
        return JWTClaims(**payload)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise TokenExpiredError()

    except jwt.InvalidSignatureError:
        logger.warning("JWT signature verification failed")
        raise InvalidSignatureError()

    except jwt.InvalidAudienceError as e:
        logger.warning(f"JWT audience invalid: {e}")
        raise InvalidTokenError(f"Invalid token audience: {e}")

    except jwt.DecodeError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError(f"Failed to decode token: {e}")

    except jwt.InvalidTokenError as e:
        logger. warning(f"JWT invalid: {e}")
        raise InvalidTokenError(f"Invalid token: {e}")


def extract_cliente_vizu_id_from_jwt(token: str) -> Optional[UUID]:
    """
    Extrai cliente_vizu_id de um token JWT, se presente.

    Retorna None se:
    - Token inválido
    - Claim não presente
    - Claim com valor inválido
    """
    try:
        claims = decode_jwt(token)
        return claims.cliente_vizu_id
    except AuthError:
        return None


def validate_jwt(token: str) -> bool:
    """
    Valida um token JWT sem extrair claims.

    Returns:
        True se válido, False caso contrário.
    """
    try:
        decode_jwt(token)
        return True
    except AuthError:
        return False
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core.jwt_decoder import validate_jwt

# Deve retornar False (token inválido)
result = validate_jwt('invalid. token. here')
print(f'Invalid token validation: {result}')
assert result == False
print('JWT decoder OK')
"
```

---

## Task 2.4: Atualizar core/__init__.py

**Tempo estimado:** 2 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/core/__init__.py`

```python
"""
vizu_auth.core - Core authentication components.
No framework dependencies (pure Python + pyjwt).
"""

from vizu_auth.core.config import (
    AuthSettings,
    clear_auth_settings_cache,
    get_auth_settings,
)
from vizu_auth. core.exceptions import (
    AuthDisabledError,
    AuthError,
    ClientNotFoundError,
    InvalidApiKeyError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import (
    decode_jwt,
    extract_cliente_vizu_id_from_jwt,
    validate_jwt,
)
from vizu_auth.core.models import (
    AuthMethod,
    AuthRequest,
    AuthResult,
    JWTClaims,
)

__all__ = [
    # Config
    "AuthSettings",
    "get_auth_settings",
    "clear_auth_settings_cache",
    # Exceptions
    "AuthError",
    "MissingCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InvalidSignatureError",
    "InvalidApiKeyError",
    "ClientNotFoundError",
    "AuthDisabledError",
    # JWT
    "decode_jwt",
    "validate_jwt",
    "extract_cliente_vizu_id_from_jwt",
    # Models
    "AuthMethod",
    "AuthRequest",
    "AuthResult",
    "JWTClaims",
]
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core import (
    AuthError, AuthResult, AuthMethod,
    decode_jwt, validate_jwt, get_auth_settings
)
print('Core imports OK')
"
```

---

# 📁 FASE 3: Estratégias de Autenticação

## Task 3.1: Criar estratégia base

**Tempo estimado:** 5 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/strategies/base.py`

```python
"""
Interface base para estratégias de autenticação.
Padrão Strategy para suportar JWT, API-Key, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional

from vizu_auth.core. models import AuthRequest, AuthResult


class AuthStrategy(ABC):
    """
    Interface abstrata para estratégias de autenticação.

    Cada estratégia implementa uma forma de autenticar:
    - JWTStrategy: Valida tokens JWT
    - ApiKeyStrategy: Valida API-Keys
    """

    @abstractmethod
    async def authenticate(self, request: AuthRequest) -> Optional[AuthResult]:
        """
        Tenta autenticar com base na request.

        Args:
            request: Dados de autenticação (JWT, API-Key, etc)

        Returns:
            AuthResult se autenticação bem-sucedida, None caso contrário.

        Raises:
            AuthError: Se credencial presente mas inválida.
        """
        pass

    @abstractmethod
    def can_handle(self, request: AuthRequest) -> bool:
        """
        Verifica se esta estratégia pode processar a request.

        Args:
            request: Dados de autenticação

        Returns:
            True se a estratégia pode tentar autenticar.
        """
        pass
```

**Checkpoint ✓:** Arquivo criado

---

## Task 3.2: Criar JWT Strategy

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/strategies/jwt_strategy.py`

```python
"""
Estratégia de autenticação via JWT (Supabase).
"""

import logging
from typing import Callable, Optional, Awaitable
from uuid import UUID

from vizu_auth.core.exceptions import (
    AuthError,
    ClientNotFoundError,
    InvalidTokenError,
)
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult, JWTClaims
from vizu_auth.strategies.base import AuthStrategy

logger = logging.getLogger(__name__)

# Type alias para função de lookup
ClienteLookupFn = Callable[[str], Awaitable[Optional[UUID]]]


class JWTStrategy(AuthStrategy):
    """
    Autenticação via JWT (Supabase).

    Fluxo:
    1.  Decodifica e valida o token JWT
    2. Extrai cliente_vizu_id da claim customizada OU
    3. Usa lookup function para mapear external_user_id → cliente_vizu_id
    """

    def __init__(
        self,
        cliente_lookup_fn: Optional[ClienteLookupFn] = None,
    ):
        """
        Args:
            cliente_lookup_fn: Função async que mapeia external_user_id → cliente_vizu_id.
                              Se não fornecida, exige que JWT contenha cliente_vizu_id claim.
        """
        self._cliente_lookup_fn = cliente_lookup_fn

    def can_handle(self, request: AuthRequest) -> bool:
        """Retorna True se request contém JWT token."""
        return bool(request. jwt_token)

    async def authenticate(self, request: AuthRequest) -> Optional[AuthResult]:
        """
        Autentica via JWT.

        Returns:
            AuthResult se sucesso, None se JWT não presente.

        Raises:
            InvalidTokenError: Token inválido
            ClientNotFoundError: Não foi possível resolver cliente_vizu_id
        """
        if not request.jwt_token:
            return None

        # 1. Decodificar JWT
        claims: JWTClaims = decode_jwt(request.jwt_token)

        logger.debug(f"JWT validated for user: {claims.sub}")

        # 2. Resolver cliente_vizu_id
        cliente_vizu_id: Optional[UUID] = None

        # 2a. Tentar claim customizada primeiro
        if claims.cliente_vizu_id:
            cliente_vizu_id = claims.cliente_vizu_id
            logger.debug(f"cliente_vizu_id from JWT claim: {cliente_vizu_id}")

        # 2b. Fallback: lookup por external_user_id
        elif self._cliente_lookup_fn:
            cliente_vizu_id = await self._cliente_lookup_fn(claims.sub)
            if cliente_vizu_id:
                logger.debug(f"cliente_vizu_id from lookup: {cliente_vizu_id}")

        # 3.  Validar que temos um cliente
        if not cliente_vizu_id:
            logger.warning(
                f"Could not resolve cliente_vizu_id for user {claims.sub} "
                f"(email: {claims.email})"
            )
            raise ClientNotFoundError(
                f"No Vizu client associated with user: {claims.sub}"
            )

        # 4.  Retornar resultado
        return AuthResult(
            cliente_vizu_id=cliente_vizu_id,
            auth_method=AuthMethod.JWT,
            external_user_id=claims.sub,
            email=claims.email,
            raw_claims=claims. model_dump(exclude_none=True),
        )
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies.jwt_strategy import JWTStrategy
from vizu_auth.core.models import AuthRequest

strategy = JWTStrategy()
request = AuthRequest(jwt_token='test. token. here')
print(f'Can handle: {strategy.can_handle(request)}')
print('JWT Strategy OK')
"
```

---

## Task 3.3: Criar API-Key Strategy

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/strategies/api_key_strategy.py`

```python
"""
Estratégia de autenticação via API-Key.
Usado para chamadas internas/service-to-service e RLS.
"""

import logging
from typing import Callable, Optional, Awaitable
from uuid import UUID

from vizu_auth.core. exceptions import ClientNotFoundError, InvalidApiKeyError
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult
from vizu_auth.strategies. base import AuthStrategy

logger = logging.getLogger(__name__)

# Type alias para função de lookup
ApiKeyLookupFn = Callable[[str], Awaitable[Optional[UUID]]]


class ApiKeyStrategy(AuthStrategy):
    """
    Autenticação via API-Key.

    Fluxo:
    1. Recebe API-Key do header X-API-KEY
    2.  Usa lookup function para mapear api_key → cliente_vizu_id
    """

    def __init__(self, api_key_lookup_fn: ApiKeyLookupFn):
        """
        Args:
            api_key_lookup_fn: Função async que mapeia api_key → cliente_vizu_id.
                              Retorna None se API-Key inválida.
        """
        if not api_key_lookup_fn:
            raise ValueError("api_key_lookup_fn is required for ApiKeyStrategy")
        self._api_key_lookup_fn = api_key_lookup_fn

    def can_handle(self, request: AuthRequest) -> bool:
        """Retorna True se request contém API-Key."""
        return bool(request.api_key)

    async def authenticate(self, request: AuthRequest) -> Optional[AuthResult]:
        """
        Autentica via API-Key.

        Returns:
            AuthResult se sucesso, None se API-Key não presente.

        Raises:
            InvalidApiKeyError: API-Key fornecida mas inválida
            ClientNotFoundError: Cliente não encontrado
        """
        if not request.api_key:
            return None

        api_key = request.api_key. strip()

        if not api_key:
            raise InvalidApiKeyError("Empty API key provided")

        # Lookup cliente_vizu_id
        cliente_vizu_id = await self._api_key_lookup_fn(api_key)

        if not cliente_vizu_id:
            # Log apenas os últimos 4 caracteres por segurança
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
            logger.warning(f"Invalid API key ending in ... {key_suffix}")
            raise InvalidApiKeyError("Invalid or expired API key")

        logger.debug(f"API key authenticated for cliente: {cliente_vizu_id}")

        return AuthResult(
            cliente_vizu_id=cliente_vizu_id,
            auth_method=AuthMethod.API_KEY,
            external_user_id=None,
            email=None,
            raw_claims={"api_key_suffix": api_key[-4:]},
        )
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy
from vizu_auth.core.models import AuthRequest

# Deve falhar sem lookup function
try:
    strategy = ApiKeyStrategy(api_key_lookup_fn=None)
    print('ERROR: Should have raised')
except ValueError as e:
    print(f'Correctly raised: {e}')
print('API Key Strategy OK')
"
```

---

## Task 3.4: Criar Authenticator (orquestrador)

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/strategies/authenticator.py`

```python
"""
Orquestrador de autenticação.
Tenta múltiplas estratégias em ordem de prioridade.
"""

import logging
from typing import List, Optional

from vizu_auth.core. config import get_auth_settings
from vizu_auth.core.exceptions import AuthDisabledError, AuthError, MissingCredentialsError
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult
from vizu_auth. strategies.base import AuthStrategy

logger = logging.getLogger(__name__)


class Authenticator:
    """
    Orquestrador que tenta múltiplas estratégias de autenticação.

    Ordem padrão:
    1. JWT (se presente)
    2. API-Key (se presente)

    Uso:
        authenticator = Authenticator([jwt_strategy, api_key_strategy])
        result = await authenticator.authenticate(request)
    """

    def __init__(
        self,
        strategies: List[AuthStrategy],
        *,
        allow_auth_disabled: bool = False,
    ):
        """
        Args:
            strategies: Lista de estratégias em ordem de prioridade.
            allow_auth_disabled: Se True, retorna resultado mock quando AUTH_ENABLED=false.
        """
        self._strategies = strategies
        self._allow_auth_disabled = allow_auth_disabled

    async def authenticate(
        self,
        request: AuthRequest,
        *,
        require_auth: bool = True,
    ) -> Optional[AuthResult]:
        """
        Tenta autenticar usando as estratégias configuradas.

        Args:
            request: Dados de autenticação
            require_auth: Se True, lança exceção se nenhuma credencial fornecida

        Returns:
            AuthResult se autenticação bem-sucedida

        Raises:
            MissingCredentialsError: Nenhuma credencial fornecida (se require_auth=True)
            AuthError: Credencial fornecida mas inválida
            AuthDisabledError: AUTH_ENABLED=false (apenas se allow_auth_disabled=False)
        """
        settings = get_auth_settings()

        # Verificar se auth está desabilitada (dev only)
        if not settings.auth_enabled:
            if self._allow_auth_disabled:
                logger.warning("⚠️ AUTH DISABLED - Development mode only!")
                return self._create_disabled_result()
            else:
                raise AuthDisabledError(
                    "Authentication is disabled but allow_auth_disabled=False"
                )

        # Verificar se alguma credencial foi fornecida
        if not request.has_credentials():
            if require_auth:
                raise MissingCredentialsError()
            return None

        # Tentar cada estratégia
        last_error: Optional[AuthError] = None

        for strategy in self._strategies:
            if not strategy.can_handle(request):
                continue

            try:
                result = await strategy.authenticate(request)
                if result:
                    logger.info(
                        f"Authentication successful via {result.auth_method.value} "
                        f"for cliente: {result.cliente_vizu_id}"
                    )
                    return result
            except AuthError as e:
                # Guarda o erro mas continua tentando outras estratégias
                logger.debug(f"Strategy {strategy.__class__.__name__} failed: {e}")
                last_error = e

        # Nenhuma estratégia funcionou
        if last_error:
            raise last_error

        if require_auth:
            raise MissingCredentialsError("No valid credentials provided")

        return None

    def _create_disabled_result(self) -> AuthResult:
        """Cria resultado mock para quando auth está desabilitada."""
        from uuid import UUID

        # UUID fixo para dev (pode ser configurável)
        dev_cliente_id = UUID("00000000-0000-0000-0000-000000000001")

        return AuthResult(
            cliente_vizu_id=dev_cliente_id,
            auth_method=AuthMethod. NONE,
            external_user_id="dev-user",
            email="dev@vizu.local",
            raw_claims={"dev_mode": True},
        )
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.core. models import AuthRequest

auth = Authenticator(strategies=[])
print('Authenticator OK')
"
```

---

## Task 3.5: Atualizar strategies/__init__.py

**Tempo estimado:** 2 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/strategies/__init__.py`

```python
"""
vizu_auth.strategies - Pluggable authentication strategies.
"""

from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.strategies. base import AuthStrategy
from vizu_auth.strategies.jwt_strategy import JWTStrategy

__all__ = [
    "AuthStrategy",
    "JWTStrategy",
    "ApiKeyStrategy",
    "Authenticator",
]
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies import (
    Authenticator, JWTStrategy, ApiKeyStrategy, AuthStrategy
)
print('Strategies imports OK')
"
```

---

# 📁 FASE 4: FastAPI Dependencies

## Task 4.1: Criar FastAPI dependencies

**Tempo estimado:** 15 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/fastapi/dependencies.py`

```python
"""
FastAPI dependencies para autenticação.
Integra vizu_auth com injeção de dependência do FastAPI.
"""

import logging
from typing import Callable, Optional, Awaitable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vizu_auth.core. config import get_auth_settings
from vizu_auth.core. exceptions import (
    AuthDisabledError,
    AuthError,
    ClientNotFoundError,
    InvalidApiKeyError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from vizu_auth.core. models import AuthMethod, AuthRequest, AuthResult
from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.strategies. jwt_strategy import JWTStrategy

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)

# Type aliases
ApiKeyLookupFn = Callable[[str], Awaitable[Optional[UUID]]]
ExternalUserLookupFn = Callable[[str], Awaitable[Optional[UUID]]]


class AuthDependencyFactory:
    """
    Factory para criar dependencies de autenticação.

    Uso:
        # No startup da aplicação
        auth_factory = AuthDependencyFactory(
            api_key_lookup_fn=my_api_key_lookup,
            external_user_lookup_fn=my_user_lookup,
        )

        # Nos endpoints
        @app.get("/protected")
        async def protected(
            auth: AuthResult = Depends(auth_factory. get_auth_result)
        ):
            ...
    """

    def __init__(
        self,
        api_key_lookup_fn: ApiKeyLookupFn,
        external_user_lookup_fn: Optional[ExternalUserLookupFn] = None,
        *,
        allow_auth_disabled: bool = False,
    ):
        """
        Args:
            api_key_lookup_fn: Função que mapeia API-Key → cliente_vizu_id
            external_user_lookup_fn: Função que mapeia external_user_id → cliente_vizu_id
            allow_auth_disabled: Permitir AUTH_ENABLED=false (dev only)
        """
        self._api_key_lookup_fn = api_key_lookup_fn
        self._external_user_lookup_fn = external_user_lookup_fn
        self._allow_auth_disabled = allow_auth_disabled

        # Criar estratégias
        self._jwt_strategy = JWTStrategy(
            cliente_lookup_fn=external_user_lookup_fn
        )
        self._api_key_strategy = ApiKeyStrategy(
            api_key_lookup_fn=api_key_lookup_fn
        )

        # Criar authenticator
        self._authenticator = Authenticator(
            strategies=[self._jwt_strategy, self._api_key_strategy],
            allow_auth_disabled=allow_auth_disabled,
        )

    async def get_auth_result(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    ) -> AuthResult:
        """
        Dependency que retorna AuthResult validado.

        Tenta:
        1. JWT Bearer token
        2. X-API-KEY header

        Raises:
            HTTPException 401: Credenciais inválidas ou ausentes
            HTTPException 403: Cliente não encontrado
        """
        auth_request = AuthRequest(
            jwt_token=credentials.credentials if credentials else None,
            api_key=x_api_key,
        )

        try:
            result = await self._authenticator.authenticate(auth_request)

            if not result:
                raise MissingCredentialsError()

            return result

        except MissingCredentialsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.  Provide Bearer token or X-API-KEY.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please refresh your authentication.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except (InvalidTokenError, InvalidApiKeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

        except ClientNotFoundError as e:
            raise HTTPException(
                status_code=status. HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        except AuthDisabledError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is disabled.",
            )

        except AuthError as e:
            logger.error(f"Unexpected auth error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_optional_auth_result(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    ) -> Optional[AuthResult]:
        """
        Dependency que retorna AuthResult ou None.
        Não lança exceção se credenciais não fornecidas.
        """
        auth_request = AuthRequest(
            jwt_token=credentials.credentials if credentials else None,
            api_key=x_api_key,
        )

        try:
            return await self._authenticator.authenticate(
                auth_request,
                require_auth=False,
            )
        except AuthError as e:
            logger.debug(f"Optional auth failed: {e}")
            return None

    async def get_cliente_vizu_id(
        self,
        auth_result: AuthResult = Depends(lambda self=None: None),  # Placeholder
    ) -> UUID:
        """
        Dependency de conveniência que retorna apenas o cliente_vizu_id.

        Nota: Este método precisa ser usado via closure no setup.
        """
        return auth_result.cliente_vizu_id


def create_auth_dependency(
    api_key_lookup_fn: ApiKeyLookupFn,
    external_user_lookup_fn: Optional[ExternalUserLookupFn] = None,
    *,
    allow_auth_disabled: bool = False,
) -> AuthDependencyFactory:
    """
    Cria uma factory de dependencies configurada.

    Uso no serviço:
        from vizu_auth.fastapi import create_auth_dependency

        async def lookup_api_key(key: str) -> Optional[UUID]:
            cliente = await db.get_cliente_by_api_key(key)
            return cliente.id if cliente else None

        auth = create_auth_dependency(api_key_lookup_fn=lookup_api_key)

        @app.get("/protected")
        async def protected(result: AuthResult = Depends(auth.get_auth_result)):
            return {"cliente_id": str(result.cliente_vizu_id)}
    """
    return AuthDependencyFactory(
        api_key_lookup_fn=api_key_lookup_fn,
        external_user_lookup_fn=external_user_lookup_fn,
        allow_auth_disabled=allow_auth_disabled,
    )
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.fastapi.dependencies import create_auth_dependency
print('FastAPI dependencies OK')
"
```

---

## Task 4.2: Atualizar fastapi/__init__.py

**Tempo estimado:** 2 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/fastapi/__init__. py`

```python
"""
vizu_auth.fastapi - FastAPI integration.
"""

from vizu_auth.fastapi. dependencies import (
    AuthDependencyFactory,
    create_auth_dependency,
)

__all__ = [
    "AuthDependencyFactory",
    "create_auth_dependency",
]
```

---

## Task 4.3: Atualizar vizu_auth/__init__.py principal

**Tempo estimado:** 3 minutos

**Arquivo:** `libs/vizu_auth/src/vizu_auth/__init__.py`

```python
"""
vizu_auth - Centralized authentication library for Vizu services.

Supports:
- JWT authentication (Supabase)
- API-Key authentication (internal/RLS)

Usage:
    # Core (no framework dependencies)
    from vizu_auth. core import decode_jwt, AuthResult, AuthError

    # FastAPI integration
    from vizu_auth. fastapi import create_auth_dependency

    # Strategies
    from vizu_auth. strategies import JWTStrategy, ApiKeyStrategy, Authenticator
"""

__version__ = "0.1. 0"

# Re-export commonly used items at top level
from vizu_auth.core import (
    # Config
    AuthSettings,
    get_auth_settings,
    # Exceptions
    AuthError,
    ClientNotFoundError,
    InvalidApiKeyError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
    # Models
    AuthMethod,
    AuthRequest,
    AuthResult,
    JWTClaims,
    # JWT
    decode_jwt,
    validate_jwt,
)

__all__ = [
    # Version
    "__version__",
    # Config
    "AuthSettings",
    "get_auth_settings",
    # Exceptions
    "AuthError",
    "MissingCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InvalidApiKeyError",
    "ClientNotFoundError",
    # Models
    "AuthMethod",
    "AuthRequest",
    "AuthResult",
    "JWTClaims",
    # JWT
    "decode_jwt",
    "validate_jwt",
]
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth import (
    AuthResult, AuthMethod, AuthError,
    decode_jwt, validate_jwt, get_auth_settings,
    __version__
)
print(f'vizu_auth v{__version__} OK')
"
```

---

# 📁 FASE 5: Testes Unitários

## Task 5. 1: Criar conftest.py

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/tests/conftest.py`

```python
"""
Pytest fixtures para testes vizu_auth.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import uuid4

import jwt
import pytest

# Configurar variáveis de ambiente ANTES de importar vizu_auth
TEST_JWT_SECRET = "test-secret-key-must-be-at-least-32-characters-long!"
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_AUDIENCE"] = "authenticated"
os.environ["AUTH_ENABLED"] = "true"

from vizu_auth.core.config import clear_auth_settings_cache


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings cache antes e depois de cada teste."""
    clear_auth_settings_cache()
    yield
    clear_auth_settings_cache()


@pytest.fixture
def jwt_secret() -> str:
    return TEST_JWT_SECRET


@pytest.fixture
def sample_cliente_vizu_id():
    return uuid4()


@pytest.fixture
def sample_external_user_id() -> str:
    return f"supabase-user-{uuid4()}"


@pytest.fixture
def valid_jwt_payload(sample_external_user_id: str, sample_cliente_vizu_id) -> Dict[str, Any]:
    """Payload JWT válido com cliente_vizu_id."""
    now = datetime.now(timezone.utc)
    return {
        "sub": sample_external_user_id,
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "cliente_vizu_id": str(sample_cliente_vizu_id),
    }


@pytest.fixture
def valid_jwt_token(jwt_secret: str, valid_jwt_payload: Dict[str, Any]) -> str:
    """Token JWT válido."""
    return jwt.encode(valid_jwt_payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def jwt_without_cliente_id(jwt_secret: str, sample_external_user_id: str) -> str:
    """Token JWT sem cliente_vizu_id claim."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sample_external_user_id,
        "email": "test@example.com",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)). timestamp()),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def expired_jwt_token(jwt_secret: str, sample_external_user_id: str) -> str:
    """Token JWT expirado."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sample_external_user_id,
        "aud": "authenticated",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def invalid_signature_token(valid_jwt_payload: Dict[str, Any]) -> str:
    """Token com assinatura inválida."""
    return jwt.encode(valid_jwt_payload, "wrong-secret-32-chars-long-xxxxx", algorithm="HS256")


@pytest.fixture
def sample_api_key() -> str:
    return f"vizu_key_{uuid4(). hex}"
```

**Checkpoint ✓:** Arquivo criado

---

## Task 5.2: Criar testes do JWT decoder

**Tempo estimado:** 10 minutos

**Arquivo:** `libs/vizu_auth/tests/test_jwt_decoder. py`

```python
"""
Testes para vizu_auth.core.jwt_decoder
"""

import pytest

from vizu_auth.core. exceptions import (
    InvalidSignatureError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import decode_jwt, validate_jwt
from vizu_auth.core. models import JWTClaims


class TestDecodeJWT:
    """Testes para decode_jwt()"""

    def test_decode_valid_token(
        self,
        valid_jwt_token: str,
        sample_external_user_id: str,
        sample_cliente_vizu_id,
    ):
        """Deve decodificar token válido com sucesso."""
        claims = decode_jwt(valid_jwt_token)

        assert isinstance(claims, JWTClaims)
        assert claims.sub == sample_external_user_id
        assert claims.email == "test@example.com"
        assert claims.cliente_vizu_id == sample_cliente_vizu_id

    def test_decode_token_with_bearer_prefix(self, valid_jwt_token: str):
        """Deve aceitar token com prefixo 'Bearer '."""
        token_with_prefix = f"Bearer {valid_jwt_token}"
        claims = decode_jwt(token_with_prefix)

        assert isinstance(claims, JWTClaims)

    def test_decode_expired_token_raises_error(self, expired_jwt_token: str):
        """Deve lançar TokenExpiredError para token expirado."""
        with pytest.raises(TokenExpiredError):
            decode_jwt(expired_jwt_token)

    def test_decode_expired_token_with_verify_false(self, expired_jwt_token: str):
        """Deve decodificar token expirado quando verify_exp=False."""
        claims = decode_jwt(expired_jwt_token, verify_exp=False)
        assert isinstance(claims, JWTClaims)

    def test_decode_invalid_signature_raises_error(self, invalid_signature_token: str):
        """Deve lançar InvalidSignatureError para assinatura inválida."""
        with pytest.raises(InvalidSignatureError):
            decode_jwt(invalid_signature_token)

    def test_decode_malformed_token_raises_error(self):
        """Deve lançar InvalidTokenError para token malformado."""
        with pytest.raises(InvalidTokenError):
            decode_jwt("not. a.valid.jwt")

    def test_decode_empty_token_raises_error(self):
        """Deve lançar InvalidTokenError para token vazio."""
        with pytest.raises(InvalidTokenError):
            decode_jwt("")

    def test_decode_whitespace_token_raises_error(self):
        """Deve lançar InvalidTokenError para token só com espaços."""
        with pytest.raises(InvalidTokenError):
            decode_jwt("   ")


class TestValidateJWT:
    """Testes para validate_jwt()"""

    def test_validate_valid_token_returns_true(self, valid_jwt_token: str):
        """Deve retornar True para token válido."""
        assert validate_jwt(valid_jwt_token) is True

    def test_validate_expired_token_returns_false(self, expired_jwt_token: str):
        """Deve retornar False para token expirado."""
        assert validate_jwt(expired_jwt_token) is False

    def test_validate_invalid_token_returns_false(self):
        """Deve retornar False para token inválido."""
        assert validate_jwt("invalid") is False
```

**Checkpoint ✓:**
```bash
cd libs/vizu_auth && poetry run pytest tests/test_jwt_decoder. py -v
# Todos os testes devem passar
```

---

## Task 5.3: Criar testes das strategies

**Tempo estimado:** 15 minutos

**Arquivo:** `libs/vizu_auth/tests/test_strategies.py`

```python
"""
Testes para vizu_auth.strategies
"""

from typing import Optional
from uuid import UUID, uuid4

import pytest

from vizu_auth.core.exceptions import ClientNotFoundError, InvalidApiKeyError
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult
from vizu_auth.strategies. api_key_strategy import ApiKeyStrategy
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.strategies.jwt_strategy import JWTStrategy


class TestJWTStrategy:
    """Testes para JWTStrategy"""

    @pytest.fixture
    def jwt_strategy(self):
        return JWTStrategy()

    def test_can_handle_with_jwt(self, jwt_strategy):
        """Deve retornar True quando JWT presente."""
        request = AuthRequest(jwt_token="some. token. here")
        assert jwt_strategy.can_handle(request) is True

    def test_can_handle_without_jwt(self, jwt_strategy):
        """Deve retornar False quando JWT ausente."""
        request = AuthRequest(api_key="some-key")
        assert jwt_strategy. can_handle(request) is False

    @pytest.mark.asyncio
    async def test_authenticate_