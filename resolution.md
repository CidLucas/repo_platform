# Resolução de Design — Issue #18: Post-flight Shared Memory (T1.2)

> Planejamento factory-planner, branch `phase-0/issue-18-sm-postflight`
> Gerado: 2026-06-19 | Fase 1, T1.2

## 1. Arquitetura de implementação

```
┌─────────────────────────────────────────────────────────┐
│  service.py (ChatService)                               │
│                                                         │
│  process_message() / process_message_stream()           │
│    │                                                    │
│    ├─ graph.ainvoke() ───────────────► final_state      │
│    │                                                    │
│    └─ [NOVO] _fire_and_forget(                          │
│         _shared_memory_post_flight_logic(               │
│           client_id, agent_slug, session_id,            │
│           agent_result, agent_metadata, suggested_links │
│         )                                               │
│       )                                                 │
└───────────────────────┬─────────────────────────────────┘
                        │ import
┌───────────────────────▼─────────────────────────────────┐
│  memory_post_flight.py (tool_pool)                      │
│                                                         │
│  _shared_memory_post_flight_logic(...)                  │
│    │                                                    │
│    ├─ Upsert agent_result → shared_business_memory      │
│    │   entity_type='agent_result'                       │
│    │   entity_name='<agent>:<session>'                  │
│    │   key='finding:<desc>' ou 'decision:<desc>'        │
│    │                                                    │
│    ├─ Upsert agent_metadata → shared_business_memory    │
│    │   entity_type='agent_metadata'                     │
│    │   entity_name='<agent>'                            │
│    │   key='session_id' | 'elapsed' | 'tool_usage:<t>' │
│    │                                                    │
│    └─ Insert suggested_links → shared_memory_links      │
│        entity_type='agent_link_pending' (source field)  │
│        source='agent_pending'                           │
└─────────────────────────────────────────────────────────┘
```

## 2. Esquema de dados no shared_business_memory

### 2.1 agent_result

| Campo | Valor | Exemplo |
|-------|-------|---------|
| `entity_type` | `agent_result` | |
| `entity_name` | `<agent_slug>:<session_id[:8]>` | `crm:a1b2c3d4` |
| `key` | `finding:cliente_inadimplente` | Prefixo `finding:` ou `decision:` |
| `value` | `jsonb` com conteúdo textual | `{"text": "Cliente X está 3 meses atrasado", "confidence": 0.9}` |
| `source` | `specialist` | |
| `confidence` | `0.0–1.0` | |

### 2.2 agent_metadata

| Campo | Valor | Exemplo |
|-------|-------|---------|
| `entity_type` | `agent_metadata` | |
| `entity_name` | `<agent_slug>` | `crm` |
| `key` | `session_id`, `elapsed`, `tool_usage:execute_sql` | Prefixo `tool_usage:` |
| `value` | `jsonb` | `{"elapsed_seconds": 12.5}` ou `{"tool": "execute_sql"}` |
| `source` | `system` | |
| `confidence` | `1.0` | |

### 2.3 agent_link_pending

Links sugeridos vão para `shared_memory_links` com `source='agent_pending'`:
- `source_entity_type` = tipo da entidade origem (skill, client, etc.)
- `target_entity_type` = tipo da entidade destino
- `source='agent_pending'` → rotina T4.4 valida depois

## 3. Fluxo do hook no service.py

### 3.1 process_message() (sync)

Após `final_state = await graph.ainvoke(...)` (linha 308), antes do `return ChatResult(...)` (linha 411):

```python
# Post-flight hook (fire-and-forget)
_fire_and_forget(
    _post_flight_for_state(
        final_state=final_state,
        client_id=client_id,
        agent_slug=_selected_agent,
        session_id=session_id,
        elapsed=elapsed,
    )
)
```

### 3.2 process_message_stream() (stream)

Após o `yield` do evento `done` (linha 585), antes de retornar:

```python
# Post-flight hook (fire-and-forget, não bloqueia stream)
if full_response_parts:
    _fire_and_forget(
        _post_flight_for_response(
            client_id=client_id,
            agent_slug=specialist_slug if sentinel else "frontdesk",
            session_id=session_id,
            response_text=full_response,
            tool_calls=tool_calls_seen,
            elapsed=elapsed,
        )
    )
```

### 3.3 Função helper compartilhada

```python
async def _post_flight_for_state(
    final_state: dict,
    client_id: str,
    agent_slug: str,
    session_id: str,
    elapsed: float,
) -> None:
    """Extrai dados do estado final e chama post-flight logic."""
    try:
        from tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic
        )
        
        msgs = final_state.get("messages") or []
        last_ai = None
        for m in reversed(msgs):
            if isinstance(m, AIMessage):
                last_ai = m
                break
        
        agent_result = None
        if last_ai and last_ai.content:
            agent_result = {
                "summary": last_ai.content[:2000],  # truncate
                "tool_calls": [
                    tc.get("name") for tc in getattr(last_ai, "tool_calls", []) or []
                ],
            }
        
        agent_metadata = {
            "session_id": session_id,
            "agent_slug": agent_slug,
            "elapsed_seconds": round(elapsed, 2),
        }
        
        await _shared_memory_post_flight_logic(
            client_id=client_id,
            agent_slug=agent_slug,
            session_id=session_id,
            agent_result=agent_result,
            agent_metadata=agent_metadata,
        )
    except Exception:
        logger.warning(
            "[ChatService] Post-flight failed for agent=%s session=%s",
            agent_slug, session_id, exc_info=True
        )
```

## 4. Migration SQL (T1.2a)

```sql
-- Migration: adiciona agent_result, agent_metadata, agent_link_pending
-- aos entity_types válidos na shared_business_memory

BEGIN;

-- 1. Remove constraint existente
ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

-- 2. Adiciona nova constraint com tipos expandidos
ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
    CHECK (entity_type IN (
        'skill', 'client', 'contact', 'supplier', 'user',
        'agent_result', 'agent_metadata'
    ));

-- 3. Comentário atualizado
COMMENT ON COLUMN public.shared_business_memory.entity_type IS
    'Entity taxonomy: skill | client | contact | supplier | user | agent_result | agent_metadata';

COMMIT;
```

Arquivo: `supabase/migrations/proposed/20260619000002_add_agent_entity_types.sql`

## 5. Módulo memory_post_flight.py (T1.2b)

Estrutura do arquivo `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_post_flight.py`:

```python
"""memory_post_flight.py — Post-flight persistence for agent results (T1.2)."""

import json, logging
from blu_supabase_client import get_supabase_client
from . import register_module

logger = logging.getLogger(__name__)

_TABLE = "shared_business_memory"
_LINKS_TABLE = "shared_memory_links"

_VALID_PREFIXES = {"decision:", "finding:", "summary:", "tool_usage:"}

async def _shared_memory_post_flight_logic(
    client_id: str,
    agent_slug: str,
    session_id: str,
    agent_result: dict | None = None,
    agent_metadata: dict | None = None,
    suggested_links: list[dict] | None = None,
) -> dict:
    """Persiste resultados do agente na shared memory."""
    ...
```

## 6. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| R1 — Noise | Média | Médio | DD-04: upsert, apenas último estado, TTL curto |
| R2 — Dependência pre-flight | Baixa | Baixo | T1.2 funciona sem T1.1. Ciclo completo só com ambos. |
| R3 — Fire-and-forget perde dados | Baixa | Médio | Retry 1x no módulo; log warning na falha |
| R4 — Mudanças no LangGraph | Baixa | Alto | try/except resiliente; fallback: salvar só metadata |
| R5 — Conflito com tools Fase 0 | Nenhum | Baixo | Post-flight escreve direto (Supabase client), não usa tools existentes |

## 7. Critérios de aceitação

1. Após execução de qualquer agente (frontdesk/specialist), `agent_result` é persistido na `shared_business_memory`
2. `agent_metadata` (session_id, elapsed, tool_usage) é persistido separadamente
3. Links sugeridos são salvos como `source='agent_pending'` na `shared_memory_links`
4. Post-flight NÃO bloqueia resposta ao usuário (fire-and-forget)
5. Falha no post-flight NÃO interrompe o fluxo principal (log warning)
6. Migration SQL aplicada sem erros e validada
7. Testes de integração cobrem: persistência, upsert, fire-and-forget, error handling
8. Documentação atualizada em SHARED_MEMORY_DESIGN.md e TOOL_INVENTORY.md

## 8. Ordem de implementação recomendada

```
1. T1.2a (migration SQL)          ← independente
2. T1.2d (documentação)           ← paralelo com T1.2a
3. T1.2b (memory_post_flight.py)  ← depende de T1.2a
4. T1.2c (hook service.py)        ← depende de T1.2b
5. T1.2e (testes)                 ← depende de T1.2b
6. T1.2f (TOOL_INVENTORY.md)      ← depende de T1.2b
```
