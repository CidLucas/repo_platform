---
name: tool/rag-context
category: rag
version: 1
required_variables: ['retrieved_context']
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `tool/rag-context`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: RAG context injection prompt for MCP prompt module
-->

Use the following context to answer the user's question.
If the context doesn't contain relevant information, say so.

CONTEXT:
{{ retrieved_context }}

---
Answer based ONLY on the context above.
