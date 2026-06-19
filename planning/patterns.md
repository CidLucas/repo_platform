# Patterns — Issue #20: Validação de Integridade da Shared Memory (T1.4)

> Gerado por factory-planner em 2026-06-19
> Branch: phase-1/issue-20-validacao-integridade-shared-memory

## P1 — Padrão de Tool Registration (memory_module.py)

```python
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    registered_tools: list[str] = []

    @mcp.tool(name="tool_name", description="...")
    @mcp_inject_client_id
    async def tool_name(ctx: Context, ..., client_id: str | None = None) -> dict:
        if not client_id:
            raise ToolError("client_id is required")
        try:
            return await _tool_logic(...)
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            logger.error("[memory_module] tool_name failed: %s", exc)
            raise ToolError(f"Failed to ...: {exc}")

    logger.info("[Memory Module] Tool 'tool_name' registered.")
    registered_tools.append("tool_name")
    return registered_tools
```

**Implicações:** Novas tools (shared_memory_integrity_check, shared_memory_consistency_report) devem seguir este padrão: função lógica separada, wrapper MCP com error handling, registro no final.

## P2 — Separação Lógica/Ferramenta

Todas as 4 tools separam lógica de negócio (funções `_*_logic()`) do wrapper MCP (função decorada com `@mcp.tool`). A lógica retorna dicts, o wrapper lida com autenticação e error handling.

**Implicações:** T1.4b (validação) deve adicionar validação pré-DB nas funções `_*_logic()`, não nos wrappers. T1.4c (hook) deve ser uma função lógica separada chamada após write.

## P3 — Domain Projection via _DOMAIN_SECTIONS (context_service.py)

```python
_DOMAIN_SECTIONS: dict[str, frozenset[str]] = {
    "analytics": frozenset({"data_schema", "available_tools", "company_profile"}),
    "knowledge": frozenset({"company_profile", "policies", "brand_voice"}),
    ...
}
```

O método `get_domain_projection(domain, client_id)` filtra as seções do BluClientContext para o domínio solicitado. Domínios não mapeados recebem todas as 6 seções.

**Implicações:** T1.4d deve adicionar entradas para 'memory' ou expandir 'knowledge'/'rag'/'documents'. Se optar por expandir existentes, não quebra _ALL_CONTEXT_SECTIONS.

## P4 — Migrations SQL (supabase/migrations/proposed/)

Padrão de migration:
- Nome: `YYYYMMDDHHMMSS_descricao.sql`
- Sempre dentro de `BEGIN; ... COMMIT;`
- `CREATE TABLE IF NOT EXISTS` para idempotência
- Constraints CHECK inline na definição da coluna
- Índices com `IF NOT EXISTS`
- Triggers com `DROP TRIGGER IF EXISTS ... CREATE TRIGGER`
- RLS: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY`
- Grants: `GRANT ALL ON ... TO authenticated; GRANT ALL ON ... TO service_role;`

**Implicações:** T1.4a (migration de integridade) deve seguir este padrão. Nome sugerido: `20260619000002_shared_memory_integrity.sql`.

## P5 — Validação no lado do Python (memory_module.py)

```python
_VALID_ENTITY_TYPES: frozenset[str] = frozenset({"skill", "client", "contact", "supplier", "user"})

def _validate_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    if entity_type not in _VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid {field_name} '{entity_type}'. Must be one of: {sorted(_VALID_ENTITY_TYPES)}")

def _normalize_entity_name(name: str) -> str:
    return name.strip().lower()
```

**Implicações:** T1.4b deve adicionar validação de payload (value/body) seguindo o mesmo padrão: função `_validate_memory_payload()` com ValueError para dados inválidos. A flag `integrity_check: bool` deve ser um parâmetro opcional nos wrappers MCP.

## P6 — Estrutura de Retorno das Tools

Todas as tools retornam dicts com campos de sumário + dados:

```python
return {
    "total_entities": N,
    "client_id": client_id,
    "entity_type_filter": entity_type,
    "by_type": {...},
    "entities": [...],
}
```

**Implicações:** Novas tools (integrity_check, consistency_report) devem retornar dicts com sumário + detalhes, consistentes com o padrão. Output ETL-friendly = flat arrays de dicts com campos bem definidos.

## P7 — Async Fire-and-Forget (ausente no módulo atual)

O módulo atual NÃO tem padrão de operações assíncronas fire-and-forget. Todas as operações são síncronas (retornam resultado diretamente).

**Implicações:** T1.4c (hook assíncrono) precisará introduzir `asyncio.create_task()` ou similar. O hook deve ser não-bloqueante: a tool de write retorna imediatamente, e o hook processa em background com log de erros separado.

## P8 — BluClientContext.get_section() mapping (blu_client_context.py)

```python
def get_section(self, section_name: str) -> dict[str, Any] | None:
    section_map = {
        "company_profile": self.company_profile,
        "brand_voice": self.brand_voice,
        "team_structure": self.team_structure,
        "policies": self.policies,
        "data_schema": self.data_schema,
        "available_tools": self.available_tools,
    }
    return section_map.get(section_name)
```

**Implicações:** Se T1.4d adicionar novas seções ao BluClientContext (processes, projects, etc. do roadmap Fase 1.3), o `get_section()` e `_DOMAIN_SECTIONS` precisam ser atualizados em sincronia. O `to_safe_context()` também precisa de update.

## P9 — Tool Naming Convention

Tools no memory_module usam prefixo `shared_memory_`:
- shared_memory_list
- shared_memory_link
- shared_memory_unlink
- shared_memory_get_links

**Implicações:** Novas tools devem seguir: `shared_memory_integrity_check`, `shared_memory_consistency_report`. O nome `shared_memory_write` (referenciado no plan.json) ainda não existe — se criado, deve seguir o prefixo.

## P10 — Logging Pattern

```python
logger = logging.getLogger(__name__)
logger.info("[memory_module] tool_name client_id=%s entity_type=%s", ...)
logger.error("[memory_module] tool_name failed: %s", exc)
```

**Implicações:** T1.4b menciona "logging estruturado". Todas as novas validações devem logar com contexto suficiente para debugging (client_id truncado, entity_type, operação).
