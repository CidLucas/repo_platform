---
name: tool/rag-context
category: rag
version: 2
required_variables: ['retrieved_context']
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `tool/rag-context`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: RAG context injection prompt — synthesise retrieved passages, cite sources, handle empty results
-->

{% if retrieved_context %}
Use the following retrieved passages to answer the user's question.

RETRIEVED CONTEXT:
{{ retrieved_context }}

---

Rules:
- Answer using ONLY the content from the passages above. Never invent or extrapolate beyond what is written.
- Cite the source document when possible: "According to [Document Name]..."
- If multiple passages cover different aspects of the question, synthesise them into one coherent answer.
- If the passages partially cover the question, answer what is covered and clearly state what information was not found.
{% else %}
No relevant passages were retrieved for this query.

Inform the user: "I couldn't find relevant information about this in the knowledge base. Try rephrasing your question, or check whether the relevant document has been uploaded."
{% endif %}
