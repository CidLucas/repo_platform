# Resolution — Issue #20: Conflitos e Decisões de Planejamento

> Gerado por factory-planner em 2026-06-19
> Branch: phase-1/issue-20-validacao-integridade-shared-memory

## Conflitos Detectados

### C1 — Schema: `body` vs `value` (T1.4a)

**Conflito:** O plan.json referencia `CHECK body > 0` e validação da coluna `body`, mas o schema real em `20260619000000_shared_business_memory.sql` usa a coluna `value jsonb NOT NULL DEFAULT '{}'::jsonb`. A coluna `body` não existe.

**Impacto:** Alto. Qualquer migration que tente criar CHECK em `body` falhará.

**Resolução:** T1.4a deve validar `value` (jsonb), não `body`. O CHECK `value IS NOT NULL` já existe via `NOT NULL` na definição da coluna. Para validação semântica, usar `jsonb_typeof(value)` em vez de comparar com string vazia. A function plpgsql deve verificar `value IS NOT NULL AND value != '{}'::jsonb`.

**Ação:** Atualizar T1.4a description no coder task para referenciar `value`, não `body`.

---

### C2 — Ferramenta shared_memory_write não existe (T1.4b, T1.4c)

**Conflito:** T1.4b menciona "payload validation pré-DB nas tools" e T1.4c menciona "hook pós-escrita", mas não existe ferramenta `shared_memory_write` no memory_module.py. As 4 tools existentes são apenas de leitura/consulta (list, link, unlink, get_links).

**Impacto:** Alto. T1.4b e T1.4c não podem ser implementadas sem uma ferramenta de escrita.

**Resolução:** Três opções:
1. **(Recomendado)** Criar `shared_memory_write` como parte de T1.4b, usando o schema existente (`value jsonb`) e seguindo o padrão de tool registration (P1). A validação de payload é incorporada na tool.
2. Separar: criar task adicional para implementar `shared_memory_write` antes de T1.4b.
3. Usar `context_service.py` diretamente (sem tool MCP), como sugere Risk R5.

**Decisão:** Opção 1. T1.4b implementa `shared_memory_write` com validação integrada. O factory-coder receberá instrução explícita de criar a tool de escrita como pré-requisito da validação.

---

### C3 — Ferramenta shared_memory_read não existe (T1.4e)

**Conflito:** T1.4e (auditoria de integridade) precisa ler da shared_business_memory e shared_memory_links. As tools existentes permitem listar e consultar links, mas não ler facts individuais por key.

**Impacto:** Médio. A auditoria pode usar queries diretas ao Supabase (como `get_business_memory_snapshot()` faz), sem depender de uma tool MCP.

**Resolução:** T1.4e pode usar `get_supabase_client()` diretamente para queries de auditoria (padrão visto em `context_service.py`). Não é necessário criar `shared_memory_read` como pré-requisito. A tool `shared_memory_integrity_check` fará queries diretas.

---

### C4 — Domínio 'memory' não existe em _DOMAIN_SECTIONS (T1.4d)

**Conflito:** O plan.json sugere "adicionar domínio 'memory'" mas DQ3 recomenda "expandir 'knowledge'/'rag'/'documents'" em vez de criar novo domínio. Existem 12 domínios, nenhum chamado 'memory'.

**Impacto:** Baixo. É uma decisão de design, não um bloqueador técnico.

**Resolução:** Seguir recomendação DQ3: expandir os domínios existentes 'knowledge', 'rag', 'documents' para incluir `company_profile`, `policies`, `available_tools` (eles já têm `brand_voice`). Adicionar domínio 'memory-agent' separado como fallback para agentes de memória que precisam de contexto completo. O domínio 'memory-agent' mapearia para `_ALL_CONTEXT_SECTIONS` (todas as 6 seções).

**Ação:** T1.4d deve (1) expandir 'knowledge'/'rag'/'documents' com seções adicionais, (2) adicionar 'memory-agent' como domínio com acesso completo.

---

### C5 — Migration file naming e ordenação (T1.4a)

**Conflito:** O plan.json referencia `20260619000002_shared_memory_integrity.sql` mas o timestamp `000002` pode colidir com outras migrations propostas no mesmo dia.

**Impacto:** Baixo. O diretório `proposed/` contém migrations não aplicadas — a ordenação importa apenas quando aplicadas.

**Resolução:** Usar `20260619000002_shared_memory_integrity.sql` como nome. Se houver colisão de timestamp com outra migration proposta, incrementar para `000003`. O factory-coder deve verificar o diretório antes de criar o arquivo.

---

### C6 — docs/llm_wiki/ não existe (T1.4f)

**Conflito:** A documentação SHARED_MEMORY_DESIGN.md deve ser criada em `docs/llm_wiki/`, mas esse diretório não existe.

**Impacto:** Baixo. É criação de diretório + arquivo.

**Resolução:** T1.4f deve criar o diretório `docs/llm_wiki/` e o arquivo `SHARED_MEMORY_DESIGN.md` com o índice completo (T0.0-T0.5, T1.2-T1.4). Seguir o padrão de project-bound wiki do LLM-wiki skill: slugs numerados para ordenação, links markdown simples, footer-style provenance.

---

## Riscos Confirmados e Mitigações

| Risco | Status | Mitigação |
|-------|--------|-----------|
| R1 — Performance (latência de validação) | Confirmado | Flag `integrity_check: bool` opcional nas tools. Hook assíncrono (fire-and-forget) para não bloquear response. |
| R2 — Falsos positivos na auditoria | Confirmado | Auditoria deve tratar entities-only-as-links como válidas. Filtrar por `source != 'system'`. |
| R3 — Domain projection desatualizada | Confirmado | Teste que verifica todos os campos de BluClientContext em ao menos um domínio. Adicionar assertion no test suite. |
| R4 — Nomes normalizados colidem | Confirmado | Documentar edge case no SHARED_MEMORY_DESIGN.md. Recomendar uso de source_memory_id para desambiguação. |
| R5 — shared_memory_write não existe | **Crítico** | Criar como parte de T1.4b (ver C2). |

## Design Questions — Respostas

| DQ | Recomendação | Justificativa |
|----|-------------|---------------|
| DQ1 — DB triggers vs tool validation? | Ambos | DB como safety net (não contornável), tool Python para UX rica (warnings, logging). CHECK/triggers no DB + `_validate_memory_payload()` no Python. |
| DQ2 — Hook síncrono vs assíncrono? | Assíncrono | Fire-and-forget com `asyncio.create_task()`. Não bloqueia a resposta ao agente. Log de erros separado para debugging. |
| DQ3 — Novo domínio 'memory' vs expandir existentes? | Expandir existentes + 'memory-agent' | 'knowledge', 'rag', 'documents' ganham seções adicionais. 'memory-agent' como novo domínio com acesso completo (_ALL_CONTEXT_SECTIONS). |
| DQ4 — shared_memory_write como MCP tool? | Sim, MCP tool | Agents precisam escrever via MCP para usar o middleware de auth (client_id injection). Implementar em T1.4b. |

## Dependências Críticas (fora do escopo T1.4)

1. **shared_business_memory + shared_memory_links migrations** — Existem como proposed mas NÃO foram aplicadas no Supabase. T1.4 assume que as tabelas existem. O factory-coder deve verificar antes de criar triggers/views de integridade.
2. **pgvector** — Habilitado no Supabase? As migrations de Fase 0 incluem embedding (não usado em T1.4, mas relevante para contexto).
3. **clientes_blu** — Tabela referenciada como FK. Deve existir e ter RLS configurada.

## Recomendações para o Factory-Coder

1. **Ordem de implementação:** T1.4a → T1.4b (inclui criar shared_memory_write) → T1.4c → T1.4d → T1.4e → T1.4f
2. **T1.4b deve criar shared_memory_write** como pré-requisito da validação. O nome da tool deve seguir o padrão `shared_memory_write`.
3. **Coluna é `value` (jsonb), não `body`**. Todo código de validação deve referenciar `value`.
4. **Migrações proposed existentes são idempotentes** (CREATE TABLE IF NOT EXISTS) — aplicar é seguro.
5. **Testes:** T1.4d precisa de teste que verifica todos os campos em ao menos um domínio. T1.4a precisa de teste de integridade (tentar INSERT com value inválido).
