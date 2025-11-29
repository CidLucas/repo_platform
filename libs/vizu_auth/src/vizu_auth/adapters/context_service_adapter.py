"""
Adapters para integrar `vizu_auth` com `vizu_context_service`.

Este módulo expõe fábricas de funções de lookup que aceitam um
`ContextService` (instância) e retornam callables assíncronos compatíveis
com as assinaturas esperadas por `vizu_auth` (`Callable[[str], Awaitable[Optional[UUID]]]`).

Nota sobre integração FastAPI:
- Em uma aplicação FastAPI você normalmente obtém uma instância de
  `ContextService` via dependency `Depends(get_context_service)`.
- Para usar o adapter com `create_auth_dependency`, crie um wrapper que
  injete `ContextService` via `Depends` e chame a função retornada pela
  fábrica. Exemplo (em `atendente_core/api/auth.py`):

```py
from fastapi import Depends
from vizu_context_service.dependencies import get_context_service
from vizu_auth.adapters.context_service_adapter import api_key_lookup_from_context_service
from vizu_auth.fastapi import create_auth_dependency

def make_api_key_lookup(ctx_service: ContextService = Depends(get_context_service)):
    # Esta função será usada como lookup_fn em create_auth_dependency
    lookup = api_key_lookup_from_context_service(ctx_service)

    async def _inner(api_key: str):
        return await lookup(api_key)

    return _inner

# No startup da aplicação
auth_dep = create_auth_dependency(api_key_lookup_fn=make_api_key_lookup)
```

As diferenças de como FastAPI resolve dependências significam que o
wrapper acima (`make_api_key_lookup`) deve ser passado *como* dependency
em pontos onde FastAPI resolve `Depends` (por exemplo, quando criando
o `AuthDependencyFactory` você pode passar o wrapper ou usá-lo na hora
de registrar a dependency no router). Ajuste conforme a arquitetura do
seu serviço.
"""

from typing import Optional, Callable, Awaitable, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    # Import apenas para tipos em tempo de checagem (evita import runtime em testes)
    from vizu_context_service.context_service import ContextService


def api_key_lookup_from_context_service(ctx_service: "ContextService") -> Callable[[str], Awaitable[Optional[UUID]]]:
    """
    Retorna uma função async que mapeia `api_key -> cliente_vizu_id` usando
    uma instância de `ContextService`.

    Uso:
        lookup = api_key_lookup_from_context_service(ctx_service)
        cliente_id = await lookup(api_key)
    """

    async def _lookup(api_key: str) -> Optional[UUID]:
        if not api_key:
            return None
        ctx = await ctx_service.get_client_context_by_api_key(api_key)
        return ctx.id if ctx else None

    return _lookup


def external_user_lookup_from_context_service(ctx_service: "ContextService") -> Callable[[str], Awaitable[Optional[UUID]]]:
    """
    Retorna uma função async que tenta mapear `external_user_id (sub)` para
    `cliente_vizu_id` usando `ContextService`.

    Observação: nem todas as versões de `ContextService` expõem um método
    para buscar por `external_user_id`. Esta fábrica tenta usar
    `get_context_by_external_user_id` quando disponível; caso contrário
    retorna uma função que sempre retorna `None`.
    """

    # Se a implementação do ContextService tiver suporte, usaremos.
    if hasattr(ctx_service, "get_context_by_external_user_id"):
        async def _lookup(external_user_id: str) -> Optional[UUID]:
            if not external_user_id:
                return None
            ctx = await ctx_service.get_context_by_external_user_id(external_user_id=external_user_id)
            return ctx.id if ctx else None

        return _lookup

    # Fallback: não há suporte para lookup por external_user_id
    async def _noop(_: str) -> Optional[UUID]:
        return None

    return _noop
