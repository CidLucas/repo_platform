# Design Patterns — Issue #31: Handoff Trigger Events (T4.3)

> Patterns identified in the codebase that inform the T4.3 implementation.
> Extracted: 2026-06-19

## 1. Tool Registration Pattern (MCP) — base para T4.3.1

**Fonte:** `memory_module.py:320-382`

```python
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    @mcp.tool(name="shared_memory_list", description="...")
    @mcp_inject_client_id
    async def shared_memory_list(ctx, ..., client_id=None) -> dict:
        if not client_id: raise ToolError("client_id is required")
        try:
            return await _shared_memory_list_logic(client_id=client_id, ...)
        except ValueError as exc:
            raise ToolError(str(exc))
    registered_tools.append("shared_memory_list")
    return registered_tools
```

**Aplicação para handoff_trigger_event:**
- Registrar como `@register_module` no mesmo `memory_module.py` (domínio de shared memory)
- Função de lógica `_handoff_trigger_event_logic` separada da tool MCP
- Chamar `fire_event_for_client` RPC via `get_supabase_client(use_service_role=True)`
- Tool não precisa de `@mcp_inject_client_id` se `client_id` vier do payload do handoff (não do contexto MCP)
- Decisão: incluir `@mcp_inject_client_id` para fallback de autenticação + aceitar `client_id` explícito no payload

## 2. fire_event_for_client RPC Call Pattern — base para T4.3.1

**Fonte:** `google_calendar_webhook_router.py:70-87`, `routine_artifacts.py:509-526`, `routines.py:1222-1227`

**Padrão com service_role, fire-and-forget:**
```python
db = get_supabase_client(use_service_role=True)
await asyncio.to_thread(
    lambda: db.rpc(
        "fire_event_for_client",
        {
            "p_event_type": "handoff",
            "p_client_id": client_id,
            "p_trigger_data": {
                "event_type": "handoff",
                "source_agent": source_agent,
                "target_agent": target_agent,
                "reason": reason,
                "session_id": session_id,
            },
        },
    ).execute()
)
```

**Aplicação:** `handoff_trigger_event` usa este padrão exato. O `event_type` é `"handoff"` — novo tipo que precisa ser suportado pelo `check_and_enqueue_triggers()` no engine de rotinas.

⚠️ O engine de rotinas atualmente filtra eventos por uma lista conhecida (ver `ROUTINES_SYSTEM.md` seção 3.3). O tipo `handoff` precisa ser adicionado ou o engine precisa ser genérico.

## 3. Handoff Sentinel Detection Pattern — hook point para T4.3.2

**Fonte:** `service.py:505-516`

```python
# Detect handoff signal from route_to_specialist tool.
msgs = output.get("messages") or []
sentinel_content = None
for _m in reversed(msgs):
    if isinstance(_m, ToolMessage):
        _c = str(getattr(_m, "content", ""))
        if _c.startswith("__ROUTE_TO_SPECIALIST__:"):
            sentinel_content = _c
            break
if sentinel_content:
    parts = sentinel_content.split(":", 2)
    specialist_slug = parts[1] if len(parts) > 1 else "frontdesk"
    reason = parts[2] if len(parts) > 2 else ""
```

**Aplicação para T4.3.2:**
- Após extrair `specialist_slug` e `reason` (linhas 519-520), e ANTES de executar o specialist graph (linha 523+), disparar `handoff_trigger_event` como fire-and-forget BackgroundTask
- A chamada NÃO deve bloquear o streaming — o handoff já foi detectado, o usuário está esperando a resposta do specialist
- Padrão de BackgroundTask já existe em outros lugares do agent_api (`_background_tasks` set em service.py linha 37)
- Usar `asyncio.create_task()` com try/except interno para não propagar exceções

## 4. BackgroundTask Fire-and-Forget Pattern

**Fonte:** `service.py:37` (`_background_tasks: set = set()`) + `routine_artifacts.py:506-526`

```python
_background_tasks: set = set()

async def _fire_and_forget_handoff_event(payload: dict) -> None:
    """Fire handoff event in background. Never fails the parent operation."""
    try:
        db = get_supabase_client(use_service_role=True)
        await asyncio.to_thread(
            lambda: db.rpc("fire_event_for_client", payload).execute()
        )
    except Exception as exc:
        logger.warning("handoff_trigger_event fire-and-forget failed: %s", exc)

# No handler:
task = asyncio.create_task(_fire_and_forget_handoff_event(payload))
_background_tasks.add(task)
task.add_done_callback(_background_tasks.discard)
```

**Aplicação:** Inserir esta chamada no `service.py` imediatamente após `logger.info("[ChatService/stream] Handoff → ...")` na linha 521. O payload inclui `source_agent` (frontdesk), `target_agent` (specialist_slug), `reason`, `client_id`, `session_id`.

## 5. Migration SQL Convention Pattern — base para T4.3.3

**Fonte:** `supabase/migrations/proposed/20260619000000_shared_business_memory.sql`

```sql
-- YYYYMMDDHHMMSS_description.sql
-- Fase X / TY.Z: descrição
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

CREATE TABLE IF NOT EXISTS public.handoff_events_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   uuid NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
    session_id  text NOT NULL,
    source_agent text NOT NULL,
    target_agent text NOT NULL,
    reason      text,
    triggered_at timestamptz NOT NULL DEFAULT now(),
    triggered_routines_count int NOT NULL DEFAULT 0
);

ALTER TABLE public.handoff_events_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "client_isolation" ON public.handoff_events_log
    FOR ALL USING (client_id = (auth.jwt()->>'client_id')::uuid);

CREATE INDEX idx_handoff_events_client ON public.handoff_events_log(client_id, triggered_at DESC);
CREATE INDEX idx_handoff_events_session ON public.handoff_events_log(session_id);

COMMIT;
```

**Aplicação:** Criar migration `20260620000000_handoff_events_log.sql` em `supabase/migrations/proposed/`.

## 6. Routine Catalog Pattern — base para T4.3.4

**Fonte:** `ROUTINES_SYSTEM.md` seção 2.1 (cross_agent_routines) + seção 9 (catálogo)

Event-triggered routine template:
```json
{
  "id": "handoff_watchdog",
  "name": "Handoff Watchdog",
  "trigger_type": "event",
  "trigger_config": {"event_type": "handoff", "cooldown_hours": 0},
  "steps": [
    {"id": "log_handoff", "type": "function", "function": "storage.log_handoff_event", "inputs": {"event_data": "{{trigger_data}}"}},
    {"id": "detect_loop", "type": "llm", "prompt_name": "blu/handoff_loop_detection", "model_tier": "fast", "outputs": {"loop_detected": "bool", "loop_detail": "string"}},
    {"id": "notify_loop", "type": "artifact", "artifact_type": "alert", "function": "channels.create_alert", "inputs": {"message": "{{loop_detail}}"}, "condition": "{{loop_detected}} == true"}
  ]
}
```

⚠️ Inserir no catálogo `cross_agent_routines` via migration SQL ou script admin.

## 7. Event Type Registration Pattern

**Fonte:** `ROUTINES_SYSTEM.md` seção 3.3

Eventos suportados: `ingestion_completed`, `onboarding_completed`, `monthly_close`, `new_integration`, `document_created`.

O novo evento `handoff` precisa ser aceito pelo poller. Onde a lista é definida? Provavelmente na função `dispatch_routine_event` (SQL) ou `check_and_enqueue_triggers()` (Python).

**Ação para coder:** Verificar e adicionar `'handoff'` se houver lista restritiva.
