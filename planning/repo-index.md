# Repo Index — Issue #20: Validação de Integridade da Shared Memory (T1.4)

> Gerado por factory-planner em 2026-06-19
> Branch: phase-1/issue-20-validacao-integridade-shared-memory

## Mapa de Arquivos por Subtarefa

### T1.4a — Data integrity constraints (migration SQL)

| Arquivo | Status | Papel |
|---------|--------|-------|
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Existe (111 linhas) | Tabela base com CHECK entity_type, CHECK key length, CHECK confidence, unique constraint, RLS, trigger updated_at |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Existe (147 linhas) | Tabela de links com CHECK entity_type, CHECK link_type length, trigger normalize, RLS |
| `supabase/migrations/proposed/20260619000002_shared_memory_integrity.sql` | **NÃO EXISTE** | A ser criado: CHECK value NOT NULL, function plpgsql de validação semântica, trigger BEFORE INSERT OR UPDATE, view audit_shared_memory_integrity |

**Atenção:** O plan.json referencia `body` como coluna, mas o schema real usa `value` (jsonb). O CHECK deve validar `value`, não `body`.

### T1.4b — Tool-level validation (memory_module.py)

| Arquivo | Status | Papel |
|---------|--------|-------|
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` | Existe (606 linhas) | 4 tools registradas: list, link, unlink, get_links. Validação existente: _validate_entity_type(), _normalize_entity_name(). |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py` | Existe | @register_module decorator, registro MCP |

**Atenção:** Não existe tool shared_memory_write nem shared_memory_read. T1.4b depende de write tool existir (criada em tarefa anterior ou a ser criada). Validação de payload pré-DB precisa de uma tool de escrita para validar.

### T1.4c — Consistency hook pós-escrita

| Arquivo | Status | Papel |
|---------|--------|-------|
| `memory_module.py` (acima) | Hook a ser adicionado | Hook assíncrono após write/upsert. Validação de links existentes, detecção de conflitos semânticos. |
| (Nova tool) shared_memory_consistency_report | **NÃO EXISTE** | Tool a ser criada para report de consistência |

**Atenção:** Hook assíncrono pressupõe infra de background tasks (asyncio.create_task ou fila). O módulo atual não tem padrão de hooks — todos os calls são síncronos direto ao DB.

### T1.4d — Domain Projection (context_service.py)

| Arquivo | Status | Papel |
|---------|--------|-------|
| `libs/blu_context_service/src/blu_context_service/context_service.py` | Existe (1152 linhas) | _DOMAIN_SECTIONS com 12 domínios. _ALL_CONTEXT_SECTIONS com 6 seções. get_domain_projection() filtra por domínio. |
| `libs/blu_models/src/blu_models/blu_client_context.py` | Existe (137 linhas) | BluClientContext com 6 context sections. get_section() mapeia os mesmos 6 nomes. |
| `libs/blu_models/src/blu_models/context_schemas.py` | Existe | Schemas Pydantic para CompanyProfile, BrandVoice, TeamStructure, Policies, DataSchema, AvailableTools |

**Domínios existentes em _DOMAIN_SECTIONS:** analytics, data, sql, rfq, communication, sales, customer, knowledge, rag, documents, config, settings

**Ausente:** domínio 'memory' ou 'memory-agent'. DQ3 recomenda expandir 'knowledge'/'rag'/'documents' ao invés de criar novo.

### T1.4e — Auditoria de integridade (tool e job)

| Arquivo | Status | Papel |
|---------|--------|-------|
| (Nova tool) shared_memory_integrity_check | **NÃO EXISTE** | Tool de varredura de shared_business_memory + shared_memory_links |
| `memory_module.py` | Registrar nova tool | Seguir padrão @mcp.tool + @mcp_inject_client_id |
| `libs/blu_context_service/src/blu_context_service/context_service.py` | get_business_memory_snapshot() existente | Pode ser estendido ou usado como referência para query de múltiplas tabelas |

### T1.4f — Documentação (SHARED_MEMORY_DESIGN.md)

| Arquivo | Status | Papel |
|---------|--------|-------|
| `docs/llm_wiki/` | **NÃO EXISTE** | Diretório a ser criado |
| `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | **NÃO EXISTE** | Doc a ser criado com índice T0.0-T0.5, T1.2-T1.4 |
| `docs/roadmap/blu-intelligent-memory.md` | Existe (357 linhas) | Referência de design. Fase 1 seção 1.4 cobre Domain Projection. |
| `docs/system_reference/TOOL_INVENTORY.md` | Existe (240 linhas) | Lista 4 tools shared_memory atuais. Será atualizado com novas tools. |

## Dependências entre Subtarefas

```
T1.4a (migration SQL) ─────────────┐
                                    ├──► T1.4b (tool validation) ──► T1.4c (hook)
                                    │
T1.4d (domain projection) ─────────┤ (paralelo com T1.4a/T1.4b)
                                    │
T1.4a + T1.4b ─────────────────────┼──► T1.4e (auditoria)
                                    │
TODAS ─────────────────────────────┴──► T1.4f (documentação)
```

## Artefatos de Design

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `docs/roadmap/blu-intelligent-memory.md` | Roadmap | Visão completa 5 fases. Fase 1 seções 1.1-1.5 |
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Schema | Tabela base com constraints e índices |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Schema | Tabela de links semânticos |
| `memory_module.py` | Código | 4 tools MCP registradas (list, link, unlink, get_links) |
| `context_service.py` | Código | Domain projection com 12 domínios mapeados |

## Resumo Quantitativo

- **Arquivos existentes analisados:** 8
- **Arquivos a criar:** 6 (1 migration SQL, 2 tools MCP, 1 doc design, 1 hook, 1 view)
- **Arquivos a modificar:** 3 (memory_module.py, context_service.py, TOOL_INVENTORY.md)
- **Conflitos detectados:** 6 (ver resolution.md)
