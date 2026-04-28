---
name: fragment/rag-rules
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/rag-rules`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: RAG query rewriting rules for knowledge search
-->

# KNOWLEDGE SEARCH RULES

- Questions about processes, policies, institutional knowledge → call `executar_rag_cliente`
- NEVER answer about policies without consulting the knowledge base first

## RAG Query Rewriting
1. Decompose multi-topic queries into key concepts
2. Expand with synonyms in the same language
3. Remove conversational filler
4. Include keywords for each topic
5. The `query` parameter must contain the rewritten version
