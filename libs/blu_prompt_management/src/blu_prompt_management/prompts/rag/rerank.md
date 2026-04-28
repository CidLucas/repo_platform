---
name: rag/rerank
category: rag
version: 1
required_variables: ['question', 'passage']
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `rag/rerank`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: LLM-based reranker scoring prompt (query-passage relevance 0-10)
-->

Rate how relevant and useful this document passage is for answering the given question.
Score from 0 to 10 where:
- 0 = completely irrelevant
- 5 = somewhat relevant but not directly useful
- 10 = highly relevant and directly answers the question

Respond with ONLY a single integer number, nothing else.

Question: {{ question }}

Passage: {{ passage }}

Score:
