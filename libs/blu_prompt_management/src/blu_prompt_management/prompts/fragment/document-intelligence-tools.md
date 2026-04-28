---
name: fragment/document-intelligence-tools
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/document-intelligence-tools`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Document intelligence extraction tool descriptions
-->

## Document Extraction Tools

- **extract_structured_data** — Extract structured records from documents into a JSON table. Provide a `query` describing what to extract and a `fields` list of column names.
  Example: `extract_structured_data(query="Extract quarterly revenue figures", fields=["period", "revenue", "currency", "source_document"])`

- **compile_time_series** — Organize extracted data into a sorted time series with summary statistics (min, max, avg, trend, change%). Use after extraction when data has a time dimension.
  Example: `compile_time_series(time_field="period", value_fields=["revenue"])`

- **write_summary_to_kb** — Save an analysis summary or structured report to the knowledge base for future retrieval. Only persist when the user asks to save, or when you have a complete polished analysis.
