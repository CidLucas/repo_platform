---
name: skill:data_access:system
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `skill:data_access:system`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Data Access skill — unified READ-ONLY access to SQL and RAG.
-->

## Data Access Skill

Acesso unificado READ-ONLY aos dados do cliente via SQL e RAG.

### Ferramentas

**execute_sql(input, mode='agent'|'direct', scope='read')**
- mode='agent': descreva o que precisa em linguagem natural — SQL gerado internamente.
- mode='direct': forneça o SQL diretamente para analytics precisos.
- scope sempre READ-ONLY — INSERT/UPDATE/DELETE são bloqueados.

**executar_rag_cliente(query)**
- Busca semântica em documentos ingeridos, base de conhecimento e contexto.

**query_data_catalog()**
- Lista tabelas disponíveis, descrições e schemas de colunas.

### Quando usar cada um
- Dados numéricos/estruturados (vendas, transações, estoque) → execute_sql
- Contexto narrativo/não-estruturado (info da empresa, processos, docs) → executar_rag_cliente
- Cenário desconhecido → query_data_catalog primeiro, depois execute_sql

### Restrições
- Acesso READ-ONLY. Nenhuma escrita via esta skill.
- Queries sempre escopadas ao cliente autenticado (enforçado server-side).
