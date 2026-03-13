# vizu_auth

Centralized authentication library for the Vizu monorepo.
Decodes Supabase JWT tokens and provides ready-to-use FastAPI dependencies for extracting `client_id` from Bearer tokens.

## Architecture

```
vizu_auth/
├── core/
│   ├── config.py          # AuthSettings (reads env vars)
│   ├── exceptions.py      # AuthError, InvalidTokenError, TokenExpiredError, ...
│   ├── jwt_decoder.py     # decode_jwt() — validates & decodes Supabase JWTs
│   ├── models.py          # JWTClaims, AuthResult, AuthMethod
│   └── secret_manager.py  # Google Cloud Secret Manager integration
├── fastapi/
│   └── dependencies.py    # get_auth_result() — primary FastAPI dependency
├── dependencies/
│   └── jwt_only.py        # get_jwt_claims() — lighter dependency (no AuthResult)
├── adapters/              # Protocol adapters
├── mcp/                   # FastMCP middleware
├── oauth2/                # Google OAuth2 flow
└── strategies/            # Auth strategy pattern
```

## Key Concept

**`client_id = UUID(jwt.sub)`** — The Supabase user ID from the JWT `sub` claim IS the `client_id`. No database lookup needed.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPABASE_JWT_SECRET` | Yes* | — | HMAC secret for HS256 tokens |
| `SUPABASE_JWT_JWK` | Yes* | — | JSON Web Key for ES256/RS256 tokens |
| `JWT_ALGORITHM` | No | `ES256` | Algorithm: `ES256`, `RS256`, or `HS256` |
| `AUTH_ENABLED` | No | `true` | Set to `false` to disable auth (dev only) |

\* At least one of `SUPABASE_JWT_SECRET` or `SUPABASE_JWT_JWK` must be set.

These are automatically available to all Docker Compose services via the `x-common-env` anchor in `docker-compose.yml`.

## Usage in FastAPI Services

### 1. Add dependency to `pyproject.toml`

```toml
[tool.poetry.dependencies]
vizu-auth = { path = "../../libs/vizu_auth", develop = true }
```

### 2. Create a local `auth.py` (recommended)

```python
# services/my_service/src/my_service/api/auth.py
from vizu_auth.fastapi.dependencies import get_auth_result  # noqa: F401
from vizu_auth.core.models import AuthResult  # noqa: F401
```

### 3. Use in route handlers

```python
from fastapi import APIRouter, Depends
from my_service.api.auth import AuthResult, get_auth_result

router = APIRouter()

@router.get("/sessions")
async def list_sessions(
    auth_result: AuthResult = Depends(get_auth_result),
):
    # auth_result.client_id  → UUID (extracted from JWT sub claim)
    # auth_result.email      → str | None
    # auth_result.auth_method → AuthMethod.JWT
    sessions = await service.list_sessions(client_id=auth_result.client_id)
    return sessions
```

### 4. For lighter JWT-only validation (no AuthResult wrapper)

```python
from vizu_auth.dependencies.jwt_only import get_jwt_claims
from vizu_auth.core.models import JWTClaims

@router.get("/me")
async def get_me(claims: JWTClaims = Depends(get_jwt_claims)):
    # claims.sub   → Supabase user ID (string)
    # claims.email → str | None
    ...
```

## Models

### `AuthResult`

```python
class AuthResult(BaseModel):
    client_id: UUID           # Supabase user ID (from JWT sub)
    auth_method: AuthMethod   # AuthMethod.JWT
    external_user_id: str     # Raw sub claim
    email: str | None
    raw_claims: dict          # Full decoded JWT payload
```

### `JWTClaims`

```python
class JWTClaims(BaseModel):
    sub: str                  # Supabase user ID
    aud: str | None           # Audience (usually "authenticated")
    exp: int | None           # Expiration timestamp
    email: str | None
    role: str | None
    # ... extra fields allowed
```

## Error Handling

The `get_auth_result` dependency raises `HTTPException(401)` automatically for:

| Scenario | Detail message |
|---|---|
| No Bearer token | `Authentication required. Provide Bearer token.` |
| Expired token | `Token has expired. Please refresh your authentication.` |
| Invalid token | `Invalid authentication token` |
| Invalid UUID in sub | `Invalid user ID format in token.` |

## Auth Flow

```
Frontend (React)
  │  supabase.auth.getSession() → session.access_token
  │
  ▼
HTTP Request
  │  Authorization: Bearer <jwt>
  │
  ▼
FastAPI Dependency (get_auth_result)
  │  HTTPBearer extracts token
  │  decode_jwt(token) validates signature + expiry
  │  UUID(claims.sub) → client_id
  │
  ▼
AuthResult { client_id, email, auth_method }
  │
  ▼
Route handler uses auth_result.client_id
```

## Services Using This Pattern

| Service | Auth file | Notes |
|---|---|---|
| `atendente_core` | `api/auth.py` | Full copy of dependency (historical) |
| `standalone_agent_api` | `api/auth.py` | Re-exports from `vizu_auth.fastapi.dependencies` |

## Anti-Patterns

**Don't** accept `client_id` as a query parameter from the frontend:
```python
# ❌ WRONG — client can send any client_id
@router.get("/sessions")
async def list_sessions(client_id: UUID = Query(...)):
    ...

# ✅ CORRECT — client_id extracted from validated JWT
@router.get("/sessions")
async def list_sessions(auth_result: AuthResult = Depends(get_auth_result)):
    sessions = await service.list_sessions(client_id=auth_result.client_id)
    ...
```
