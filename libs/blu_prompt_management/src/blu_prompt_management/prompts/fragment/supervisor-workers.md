---
name: fragment/supervisor-workers
category: system
version: 1
required_variables: []
optional_variables: {'workers_description': ''}
---

<!--
This file is the in-repo fallback for prompt `fragment/supervisor-workers`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Available specialist workers list — rendered from WorkerRegistry
-->

# WORKERS

{{ workers_description }}
