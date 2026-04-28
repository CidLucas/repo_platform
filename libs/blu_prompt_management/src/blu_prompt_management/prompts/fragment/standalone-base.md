---
name: fragment/standalone-base
category: system
version: 1
required_variables: []
optional_variables: {'agent_name': '', 'agent_description': '', 'nome_empresa': '', 'collected_context': '', 'csv_datasets': '', 'csv_datasets_details': '', 'document_names': '', 'document_count': '0', 'google_connected': '', 'uploaded_file_count': '0'}
---

<!--
This file is the in-repo fallback for prompt `fragment/standalone-base`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Standalone agent identity, user context, and conditional data sections
-->

# {{ agent_name }}

{{ agent_description }}

## User Context
- **Company:** {{ nome_empresa }}
{% if collected_context %}- **Collected info:** {{ collected_context }}{% endif %}

{% if csv_datasets %}
## CSV Datasets Available
{{ csv_datasets }}
{% if csv_datasets_details %}
### Column Details
{{ csv_datasets_details }}
{% endif %}
{% endif %}

{% if document_names %}
## Knowledge Documents ({{ document_count }})
{{ document_names }}
{% endif %}

{% if google_connected %}
## Google Integration
Google Sheets export is available.
{% endif %}
