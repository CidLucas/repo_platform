# 🔐 Guia de Implementação: Biblioteca `vizu_auth`

## 📋 Contexto para o Copilot

Você vai criar uma biblioteca de autenticação centralizada para um monorepo Python.

**Repositório:** `vizubr/vizu-mono`

**Problema:** Os serviços do monorepo usam autenticação inconsistente (stubs, mocks, diferentes implementações).  Precisamos centralizar JWT (Supabase) e API-Key em uma única biblioteca.

**Arquitetura existente relevante:**
- `libs/vizu_context_service` - Já existe, tem `ContextService` com métodos `get_client_context_by_api_key()` e `get_client_context_by_id()`
- `libs/vizu_models` - Já existe, tem `VizuClientContext` e modelos SQLModel
- `services/atendente_core` - Usa `X-API-KEY` header para identificar clientes
- `services/tool_pool_api` - Usa FastMCP com `AccessToken`

**Objetivo:** Criar `libs/vizu_auth` que:
1. Valida tokens JWT (Supabase)
2. Valida API-Keys (interno/RLS)
3. Retorna `cliente_vizu_id` validado
4. Integra com FastAPI e FastMCP

---

## ✅ Checklist Geral

- [ ] Fase 1: Estrutura e configuração
- [ ] Fase 2: Core (exceptions, models, JWT decoder)
- [ ] Fase 3: Estratégias de autenticação
- [ ] Fase 4: FastAPI dependencies
- [ ] Fase 5: Testes unitários
- [ ] Fase 6: Integração atendente_core
- [ ] Fase 7: Integração tool_pool_api

---

# 📁 FASE 1: Estrutura e Configuração

## Task 1. 1: Criar estrutura de diretórios

**Objetivo:** Criar a estrutura de pastas seguindo o padrão das outras libs do monorepo.

**Instruções:**
1. Observe a estrutura de `libs/vizu_context_service` e `libs/vizu_models` como referência
2. Crie a estrutura em `libs/vizu_auth/` com:
   - Pasta `src/vizu_auth/` para o código fonte
   - Subpastas: `core/`, `strategies/`, `fastapi/`, `mcp/`
   - Pasta `tests/` para testes
   - Arquivos `__init__.py` em todas as pastas Python

**Verificação:**
```bash
# Deve listar todos os __init__.py criados
find libs/vizu_auth -name "*.py" -type f
```

**Critério de sucesso:** Estrutura similar às outras libs, com pelo menos 10 arquivos `. py` criados.

---

## Task 1.2: Criar pyproject.toml

**Objetivo:** Configurar o projeto Poetry seguindo o padrão do monorepo.

**Instruções:**
1. Observe o `pyproject.toml` de `libs/vizu_context_service` como referência
2.  Crie `libs/vizu_auth/pyproject.toml` com:
   - Nome: `vizu_auth`
   - Versão: `0.1.0`
   - Packages apontando para `src/`
   - Dependências mínimas: `pyjwt`, `pydantic`, `pydantic-settings`
   - FastAPI como dependência opcional (extras)
   - Dependências de dev: `pytest`, `pytest-asyncio`

**Verificação:**
```bash
cd libs/vizu_auth && poetry check
```

**Critério de sucesso:** Comando retorna "All set!" sem erros.

---

## Task 1.3: Criar módulo de configuração

**Objetivo:** Criar configuração que lê variáveis de ambiente para JWT.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/core/config.py`
2. Use `pydantic-settings` (BaseSettings) como nas outras libs
3. Variáveis necessárias:
   - `SUPABASE_JWT_SECRET` - Secret para validar JWT (string, obrigatório em prod)
   - `JWT_ALGORITHM` - Algoritmo (default: "HS256")
   - `JWT_AUDIENCE` - Audience esperada (default: "authenticated")
   - `AUTH_ENABLED` - Flag para desabilitar auth em dev (default: True)
4. Adicione uma property `has_jwt_secret` que verifica se o secret tem pelo menos 32 caracteres
5. Use `@lru_cache` para cachear as settings (padrão do monorepo)
6. Adicione função `clear_auth_settings_cache()` para testes

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core.config import get_auth_settings
settings = get_auth_settings()
print(f'Auth enabled: {settings.auth_enabled}')
print(f'Algorithm: {settings.jwt_algorithm}')
"
```

**Critério de sucesso:** Importa sem erros e mostra os valores default.

---

# 📁 FASE 2: Core (Exceptions, Models, JWT Decoder)

## Task 2.1: Criar módulo de exceptions

**Objetivo:** Criar hierarquia de exceções para erros de autenticação.

**Instruções:**
1.  Crie `libs/vizu_auth/src/vizu_auth/core/exceptions.py`
2. Crie uma classe base `AuthError(Exception)` com atributos `message` e `code`
3. Crie exceções específicas que herdam de `AuthError`:
   - `MissingCredentialsError` - Nenhuma credencial fornecida
   - `InvalidTokenError` - Token JWT inválido/malformado
   - `TokenExpiredError` - Token expirado
   - `InvalidSignatureError` - Assinatura JWT inválida (herda de InvalidTokenError)
   - `InvalidApiKeyError` - API-Key inválida
   - `ClientNotFoundError` - Cliente não encontrado para as credenciais
4. Cada exceção deve ter um `code` único (ex: "TOKEN_EXPIRED", "INVALID_API_KEY")

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core. exceptions import AuthError, TokenExpiredError, InvalidApiKeyError
e = TokenExpiredError()
print(f'Message: {e.message}')
print(f'Code: {e.code}')
assert e.code == 'TOKEN_EXPIRED'
print('OK')
"
```

**Critério de sucesso:** Todas as exceções importam e têm os atributos esperados.

---

## Task 2.2: Criar módulo de models

**Objetivo:** Criar modelos Pydantic para representar dados de autenticação.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/core/models.py`
2.  Crie um Enum `AuthMethod` com valores: `JWT`, `API_KEY`, `NONE`
3. Crie modelo `JWTClaims(BaseModel)` para claims do token Supabase:
   - `sub: str` (obrigatório) - ID do usuário
   - `email: Optional[str]`
   - `aud: Optional[str]`
   - `exp: Optional[int]`
   - `iat: Optional[int]`
   - `role: Optional[str]`
   - `cliente_vizu_id: Optional[UUID]` - Claim customizada Vizu
   - Configure `extra = "allow"` para aceitar claims extras
4. Crie modelo `AuthResult(BaseModel)` - resultado da autenticação:
   - `cliente_vizu_id: UUID` (obrigatório)
   - `auth_method: AuthMethod`
   - `external_user_id: Optional[str]`
   - `email: Optional[str]`
   - `raw_claims: Dict[str, Any]` - Claims originais para debug
5. Crie modelo `AuthRequest(BaseModel)` - entrada para autenticação:
   - `jwt_token: Optional[str]`
   - `api_key: Optional[str]`
   - Método `has_credentials()` que retorna True se algum campo preenchido

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from uuid import uuid4
from vizu_auth. core.models import AuthResult, AuthMethod, AuthRequest

# Testar AuthResult
result = AuthResult(
    cliente_vizu_id=uuid4(),
    auth_method=AuthMethod.JWT,
    external_user_id='user-123'
)
print(f'Cliente: {result.cliente_vizu_id}')

# Testar AuthRequest
req = AuthRequest(jwt_token='token')
print(f'Has credentials: {req.has_credentials()}')
print('OK')
"
```

**Critério de sucesso:** Modelos instanciam corretamente com validação Pydantic.

---

## Task 2.3: Criar JWT decoder

**Objetivo:** Criar função que decodifica e valida tokens JWT usando pyjwt.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/core/jwt_decoder.py`
2. Importe `jwt` (pyjwt) e as exceptions/models criadas
3. Crie função `decode_jwt(token: str, *, verify_exp: bool = True, verify_aud: bool = True) -> JWTClaims`:
   - Obtenha settings via `get_auth_settings()`
   - Verifique se `has_jwt_secret` é True, senão lance `AuthError`
   - Remova prefixo "Bearer " do token se presente
   - Use `jwt.decode()` com:
     - Secret do settings
     - Algorithm do settings
     - Audience do settings (se verify_aud=True)
   - Capture exceções do pyjwt e converta para nossas exceções:
     - `jwt.ExpiredSignatureError` → `TokenExpiredError`
     - `jwt.InvalidSignatureError` → `InvalidSignatureError`
     - `jwt.InvalidAudienceError` → `InvalidTokenError`
     - `jwt. DecodeError` → `InvalidTokenError`
   - Parse `cliente_vizu_id` para UUID se presente na claim
   - Retorne `JWTClaims` com os dados
4. Crie função auxiliar `validate_jwt(token: str) -> bool`:
   - Tenta decode_jwt, retorna True se sucesso, False se exceção

**Verificação:**
```bash
cd libs/vizu_auth
# Primeiro, setar secret temporário
export SUPABASE_JWT_SECRET="test-secret-key-must-be-at-least-32-characters!"

poetry run python -c "
from vizu_auth.core.jwt_decoder import validate_jwt

# Deve retornar False para token inválido
result = validate_jwt('invalid. token. here')
print(f'Invalid token result: {result}')
assert result == False
print('OK')
"
```

**Critério de sucesso:** Função retorna False para tokens inválidos sem crashar.

---

## Task 2.4: Criar e atualizar __init__.py do core

**Objetivo:** Exportar todos os componentes do módulo core.

**Instruções:**
1. Atualize `libs/vizu_auth/src/vizu_auth/core/__init__.py`
2. Importe e re-exporte:
   - De config: `AuthSettings`, `get_auth_settings`, `clear_auth_settings_cache`
   - De exceptions: Todas as exceções criadas
   - De models: `AuthMethod`, `AuthRequest`, `AuthResult`, `JWTClaims`
   - De jwt_decoder: `decode_jwt`, `validate_jwt`
3. Defina `__all__` com todos os exports

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.core import (
    AuthError, TokenExpiredError, InvalidApiKeyError,
    AuthResult, AuthMethod, JWTClaims,
    decode_jwt, validate_jwt,
    get_auth_settings
)
print('All core imports OK')
"
```

**Critério de sucesso:** Todos os imports funcionam a partir de `vizu_auth.core`.

---

# 📁 FASE 3: Estratégias de Autenticação

## Task 3.1: Criar classe base AuthStrategy

**Objetivo:** Definir interface abstrata para estratégias de autenticação (Strategy Pattern).

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/strategies/base.py`
2. Crie classe abstrata `AuthStrategy(ABC)` com métodos:
   - `async def authenticate(self, request: AuthRequest) -> Optional[AuthResult]`
     - Docstring explicando que retorna None se não pode processar, AuthResult se sucesso, ou lança AuthError se credencial presente mas inválida
   - `def can_handle(self, request: AuthRequest) -> bool`
     - Verifica se esta estratégia pode processar a request

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies. base import AuthStrategy
print(f'AuthStrategy is abstract: {AuthStrategy.__abstractmethods__}')
print('OK')
"
```

**Critério de sucesso:** Classe é abstrata com métodos abstratos definidos.

---

## Task 3.2: Criar JWTStrategy

**Objetivo:** Implementar estratégia de autenticação via JWT.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/strategies/jwt_strategy.py`
2.  Crie classe `JWTStrategy(AuthStrategy)` que:
   - Recebe no `__init__` uma função opcional `cliente_lookup_fn: Callable[[str], Awaitable[Optional[UUID]]]`
     - Esta função mapeia `external_user_id` (sub do JWT) para `cliente_vizu_id`
     - Se não fornecida, exige que JWT tenha claim `cliente_vizu_id`
   - `can_handle()`: Retorna True se `request.jwt_token` está preenchido
   - `authenticate()`:
     1. Decodifica JWT usando `decode_jwt()`
     2. Tenta obter `cliente_vizu_id` da claim customizada
     3. Se não tiver claim e tiver `cliente_lookup_fn`, chama ela com `claims.sub`
     4. Se não conseguir resolver `cliente_vizu_id`, lança `ClientNotFoundError`
     5.  Retorna `AuthResult` com os dados

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies. jwt_strategy import JWTStrategy
from vizu_auth.core.models import AuthRequest

strategy = JWTStrategy()
request = AuthRequest(jwt_token='test. token')
print(f'Can handle JWT request: {strategy.can_handle(request)}')
print(f'Can handle API key request: {strategy.can_handle(AuthRequest(api_key=\"key\"))}')
print('OK')
"
```

**Critério de sucesso:** `can_handle` retorna True apenas para requests com JWT.

---

## Task 3. 3: Criar ApiKeyStrategy

**Objetivo:** Implementar estratégia de autenticação via API-Key.

**Instruções:**
1.  Crie `libs/vizu_auth/src/vizu_auth/strategies/api_key_strategy.py`
2. Crie classe `ApiKeyStrategy(AuthStrategy)` que:
   - Recebe no `__init__` uma função **obrigatória** `api_key_lookup_fn: Callable[[str], Awaitable[Optional[UUID]]]`
     - Esta função mapeia `api_key` para `cliente_vizu_id`
     - Levante `ValueError` se não fornecida
   - `can_handle()`: Retorna True se `request.api_key` está preenchido
   - `authenticate()`:
     1. Valida que API-Key não está vazia
     2. Chama `api_key_lookup_fn` com a key
     3. Se retornar None, lança `InvalidApiKeyError`
     4.  Retorna `AuthResult` com `auth_method=AuthMethod.API_KEY`
   - Por segurança, nos logs mostre apenas os últimos 4 caracteres da key

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy

# Deve falhar sem lookup function
try:
    strategy = ApiKeyStrategy(api_key_lookup_fn=None)
    print('ERROR: Should have raised')
except (ValueError, TypeError) as e:
    print(f'Correctly raised error: {type(e).__name__}')
print('OK')
"
```

**Critério de sucesso:** Construtor exige `api_key_lookup_fn`.

---

## Task 3. 4: Criar Authenticator (orquestrador)

**Objetivo:** Criar classe que orquestra múltiplas estratégias de autenticação.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/strategies/authenticator.py`
2. Crie classe `Authenticator` que:
   - Recebe no `__init__`:
     - `strategies: List[AuthStrategy]` - Lista de estratégias em ordem de prioridade
     - `allow_auth_disabled: bool = False` - Se True, permite bypass quando `AUTH_ENABLED=false`
   - Método `async authenticate(request: AuthRequest, *, require_auth: bool = True) -> Optional[AuthResult]`:
     1. Verifica `settings.auth_enabled`.  Se False e `allow_auth_disabled=True`, retorna um AuthResult mock para desenvolvimento
     2. Se False e `allow_auth_disabled=False`, lança exceção
     3. Se request não tem credenciais e `require_auth=True`, lança `MissingCredentialsError`
     4. Itera pelas estratégias, chama `can_handle()` e `authenticate()`
     5.  Retorna primeiro resultado bem-sucedido
     6. Se nenhuma funcionou mas alguma lançou erro, re-lança o último erro
     7. Se nenhuma funcionou sem erro e `require_auth=True`, lança `MissingCredentialsError`

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies.authenticator import Authenticator

auth = Authenticator(strategies=[])
print('Authenticator created')
print('OK')
"
```

**Critério de sucesso:** Classe instancia sem erros.

---

## Task 3.5: Atualizar strategies/__init__.py

**Objetivo:** Exportar componentes do módulo strategies.

**Instruções:**
1. Atualize `libs/vizu_auth/src/vizu_auth/strategies/__init__.py`
2. Exporte: `AuthStrategy`, `JWTStrategy`, `ApiKeyStrategy`, `Authenticator`

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.strategies import (
    AuthStrategy, JWTStrategy, ApiKeyStrategy, Authenticator
)
print('All strategy imports OK')
"
```

**Critério de sucesso:** Todos os imports funcionam.

---

# 📁 FASE 4: FastAPI Dependencies

## Task 4.1: Criar FastAPI dependencies

**Objetivo:** Criar dependencies FastAPI que integram com o Authenticator.

**Instruções:**
1. Crie `libs/vizu_auth/src/vizu_auth/fastapi/dependencies.py`
2.  Importe `HTTPBearer`, `Header`, `Depends`, `HTTPException` do FastAPI
3. Crie classe `AuthDependencyFactory`:
   - `__init__` recebe:
     - `api_key_lookup_fn` - Função de lookup de API-Key (obrigatória)
     - `external_user_lookup_fn` - Função de lookup de user (opcional)
     - `allow_auth_disabled` - Flag para dev
   - Internamente, cria as estratégias e o `Authenticator`
   - Método `async get_auth_result(...)` que é uma dependency do FastAPI:
     - Recebe `credentials` via `Depends(HTTPBearer(auto_error=False))`
     - Recebe `x_api_key` via `Header(None, alias="X-API-KEY")`
     - Monta `AuthRequest` com os valores
     - Chama `authenticator.authenticate()`
     - Converte exceções `AuthError` para `HTTPException`:
       - `MissingCredentialsError` → 401
       - `TokenExpiredError` → 401
       - `InvalidTokenError`, `InvalidApiKeyError` → 401
       - `ClientNotFoundError` → 403
     - Retorna `AuthResult`
4. Crie função factory `create_auth_dependency(...)` que retorna `AuthDependencyFactory` configurada

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth.fastapi.dependencies import create_auth_dependency
print('FastAPI dependencies imported OK')
"
```

**Critério de sucesso:** Import funciona (pode dar erro de FastAPI não instalado, OK).

---

## Task 4.2: Atualizar fastapi/__init__.py e vizu_auth/__init__.py

**Objetivo:** Organizar exports da biblioteca.

**Instruções:**
1. Atualize `libs/vizu_auth/src/vizu_auth/fastapi/__init__.py` para exportar `create_auth_dependency` e `AuthDependencyFactory`
2. Atualize `libs/vizu_auth/src/vizu_auth/__init__.py` para:
   - Re-exportar itens mais usados do `core` no nível raiz
   - Definir `__version__ = "0.1.0"`
   - NÃO importar fastapi/* no nível raiz (é opcional)

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
from vizu_auth import (
    AuthResult, AuthMethod, AuthError,
    decode_jwt, validate_jwt,
    __version__
)
print(f'vizu_auth v{__version__}')
print('Main imports OK')
"
```

**Critério de sucesso:** Imports básicos funcionam sem FastAPI instalado.

---

# 📁 FASE 5: Testes Unitários

## Task 5. 1: Criar conftest.py com fixtures

**Objetivo:** Criar fixtures pytest para gerar tokens JWT de teste.

**Instruções:**
1. Crie `libs/vizu_auth/tests/conftest.py`
2.  No início do arquivo, configure variáveis de ambiente de teste ANTES de importar vizu_auth:
   - `SUPABASE_JWT_SECRET` com valor de teste (32+ caracteres)
   - `AUTH_ENABLED=true`
3. Crie fixture `autouse=True` que limpa cache de settings antes/depois de cada teste
4. Crie fixtures para gerar tokens JWT usando `pyjwt`:
   - `jwt_secret` - Retorna o secret de teste
   - `sample_cliente_vizu_id` - Retorna UUID aleatório
   - `sample_external_user_id` - Retorna string de ID
   - `valid_jwt_payload` - Dict com claims válidas (sub, email, aud, exp, iat, cliente_vizu_id)
   - `valid_jwt_token` - Token encodado com payload válido
   - `expired_jwt_token` - Token com exp no passado
   - `invalid_signature_token` - Token assinado com secret errado
   - `jwt_without_cliente_id` - Token válido mas sem claim cliente_vizu_id

**Verificação:**
```bash
cd libs/vizu_auth
poetry run python -c "
import sys
sys.path.insert(0, 'tests')
from conftest import *
print('Conftest imports OK')
"
```

**Critério de sucesso:** Arquivo criado sem erros de sintaxe.

---

## Task 5.2: Criar testes do JWT decoder

**Objetivo:** Testar todas as funções do jwt_decoder.

**Instruções:**
1. Crie `libs/vizu_auth/tests/test_jwt_decoder.py`
2. Crie classe `TestDecodeJWT` com testes:
   - `test_decode_valid_token` - Token válido retorna JWTClaims correto
   - `test_decode_token_with_bearer_prefix` - Aceita "Bearer " no início
   - `test_decode_expired_token_raises_error` - Lança TokenExpiredError
   - `test_decode_expired_token_with_verify_false` - Permite decode com verify_exp=False
   - `test_decode_invalid_signature_raises_error` - Lança InvalidSignatureError
   - `test_decode_malformed_token_raises_error` - Lança InvalidTokenError
   - `test_decode_empty_token_raises_error` - Lança erro para string vazia
3. Crie classe `TestValidateJWT` com testes:
   - `test_validate_valid_token_returns_true`
   - `test_validate_expired_token_returns_false`
   - `test_validate_invalid_token_returns_false`

**Verificação:**
```bash
cd libs/vizu_auth
poetry run pytest tests/test_jwt_decoder.py -v
```

**Critério de sucesso:** Todos os testes passam.

---

## Task 5.3: Criar testes das strategies

**Objetivo:** Testar JWTStrategy, ApiKeyStrategy e Authenticator.

**Instruções:**
1. Crie `libs/vizu_auth/tests/test_strategies.py`
2. Para `JWTStrategy`:
   - Teste `can_handle` com/sem JWT
   - Teste `authenticate` com token válido contendo cliente_vizu_id
   - Teste `authenticate` com lookup function quando não tem claim
   - Teste que lança `ClientNotFoundError` quando não consegue resolver ID
3. Para `ApiKeyStrategy`:
   - Teste `can_handle` com/sem API-Key
   - Teste `authenticate` com lookup que retorna ID
   - Teste `authenticate` com lookup que retorna None (deve lançar `InvalidApiKeyError`)
4. Para `Authenticator`:
   - Teste autenticação com JWT (primeira estratégia)
   - Teste fallback para API-Key quando JWT falha
   - Teste `MissingCredentialsError` quando sem credenciais

**Verificação:**
```bash
cd libs/vizu_auth
poetry run pytest tests/test_strategies.py -v
```

**Critério de sucesso:** Todos os testes passam.

---

# 📁 FASE 6: Integração com atendente_core

## Task 6.1: Atualizar atendente_core para usar vizu_auth

**Objetivo:** Substituir autenticação por API-Key atual para usar vizu_auth.

**Contexto atual:**
- `atendente_core/api/router.py` usa `X-API-KEY` header
- Chama `service.process_message(api_key=x_api_key, ... )`
- `AtendenteService` usa `context_service.get_client_context_by_api_key(api_key)`

**Instruções:**
1. Adicione `vizu_auth` como dependência no `pyproject.toml` do `atendente_core`
2. Crie um arquivo `atendente_core/api/auth.py`:
   - Importe `create_auth_dependency` de `vizu_auth. fastapi`
   - Crie função `get_cliente_by_api_key` que usa o `ContextService` existente para lookup
   - Configure o `AuthDependencyFactory` com esta função
   - Exporte a dependency `get_auth_result`
3. Atualize `atendente_core/api/router.py`:
   - Substitua o `Header(... , alias="X-API-KEY")` pela dependency `get_auth_result`
   - O endpoint agora recebe `AuthResult` em vez de `x_api_key: str`
   - Passe `auth_result. cliente_vizu_id` para o service
4. Atualize `AtendenteService. process_message`:
   - Mude assinatura para receber `cliente_vizu_id: UUID` em vez de `api_key: str`
   - Use `context_service.get_client_context_by_id(cliente_vizu_id)`

**Verificação:**
```bash
cd services/atendente_core
poetry run python -c "
from atendente_core.api.auth import get_auth_result
print('Auth dependency created')
"

# Teste endpoint (requer serviço rodando)
curl -X POST http://localhost:8001/chat \
  -H "X-API-KEY: sua-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "oi", "session_id": "test"}'
```

**Critério de sucesso:** Endpoint continua funcionando com X-API-KEY.

---

## Task 6. 2: Adicionar suporte a JWT no atendente_core

**Objetivo:** Permitir autenticação via Bearer token além de API-Key.

**Instruções:**
1. Atualize `atendente_core/api/auth.py`:
   - Configure `JWTStrategy` no factory
   - Se não tiver função de lookup de user, deixe apenas a claim `cliente_vizu_id` como opção
2. Teste com token JWT que contenha claim `cliente_vizu_id`

**Verificação:**
```bash
# Gerar token de teste (exemplo Python)
import jwt
from datetime import datetime, timedelta
token = jwt.encode({
    "sub": "user-123",
    "cliente_vizu_id": "seu-cliente-uuid",
    "aud": "authenticated",
    "exp": datetime.utcnow() + timedelta(hours=1)
}, "seu-supabase-secret", algorithm="HS256")
print(token)

# Testar
curl -X POST http://localhost:8001/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "oi", "session_id": "test"}'
```

**Critério de sucesso:** Endpoint aceita tanto X-API-KEY quanto Bearer token.

---

# 📁 FASE 7: Integração com tool_pool_api (FastMCP)

## Task 7.1: Criar middleware MCP para vizu_auth

**Objetivo:** Integrar vizu_auth com FastMCP para autenticar chamadas de tools.

**Contexto:**
- `tool_pool_api` usa FastMCP com `AccessToken`
- Tools recebem `cliente_id` injetado via parâmetro
- Atualmente usa Google OAuth Provider

**Instruções:**
1.  Crie `libs/vizu_auth/src/vizu_auth/mcp/auth_middleware.py`
2.  Estude como o FastMCP atual injeta `cliente_id` nas tools em `tool_pool_api/server/tools.py`
3. Crie classe ou função que:
   - Extrai token do contexto MCP
   - Usa `vizu_auth` para validar
   - Injeta `cliente_vizu_id` nos parâmetros das tools
4. Este é o passo mais complexo - pode precisar estudar o código FastMCP

**Verificação:**
- Funcionalidade existente de `cliente_id` injection continua funcionando
- Logs mostram validação via vizu_auth

**Critério de sucesso:** Tools MCP recebem cliente_id validado pelo vizu_auth.

---

## Task 7.2: Remover Google OAuth Provider do tool_pool_api

**Objetivo:** Consolidar autenticação no vizu_auth.

**Instruções:**
1. Em `tool_pool_api/server/dependencies.py`, remova ou comente código do `GoogleProvider`
2. Substitua pela integração com `vizu_auth`
3. Mantenha compatibilidade com o fluxo existente de `AccessToken`

**Verificação:**
```bash
# Rodar testes existentes do tool_pool_api
cd services/tool_pool_api
poetry run pytest -v
```

**Critério de sucesso:** Testes passam sem Google OAuth.

---

# 📋 Checklist Final

Antes de considerar a implementação completa, verifique:

- [ ] `poetry check` passa em `libs/vizu_auth`
- [ ] `poetry run pytest` passa em `libs/vizu_auth` (todos os testes)
- [ ] `atendente_core` aceita X-API-KEY
- [ ] `atendente_core` aceita Bearer JWT com claim `cliente_vizu_id`
- [ ] `tool_pool_api` tools recebem `cliente_id` validado
- [ ] Nenhum hardcoded secret no código (apenas via env vars)
- [ ] Logs não expõem tokens completos (apenas últimos 4 chars de API-Key)

---

# 🔧 Troubleshooting

## Erro: "JWT secret not configured"
- Verifique se `SUPABASE_JWT_SECRET` está no `. env`
- Secret deve ter pelo menos 32 caracteres

## Erro: "Module not found: vizu_auth"
- Verifique se `vizu_auth` está no PYTHONPATH
- Em Docker, verifique volumes e `docker-compose.yml`

## Erro: "ClientNotFoundError"
- JWT não tem claim `cliente_vizu_id`
- E não há função de lookup configurada
- Ou API-Key não existe no banco

## Testes falhando por settings
- Verifique se `conftest.py` configura env vars ANTES de importar vizu_auth
- Use `clear_auth_settings_cache()` entre testes