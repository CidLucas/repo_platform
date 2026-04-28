---
name: tool/elicitation-clarify
category: elicitation
version: 1
required_variables: ['original_request', 'missing_info']
optional_variables: {'options': ''}
---

<!--
This file is the in-repo fallback for prompt `tool/elicitation-clarify`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Elicitation prompt for asking clarifying questions via MCP
-->

The user requested: "{{ original_request }}"

However, I need more information: {{ missing_info }}

{% if options %}
Available options:
{{ options }}
{% endif %}

Please provide the missing information to continue.
