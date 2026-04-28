---
name: fragment/google-export
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/google-export`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Google Sheets export tools and guidelines
-->

## Google Sheets Export

- **write_to_sheet** — Write data to an existing Google Sheet by ID
- **create_spreadsheet_with_data** — Create a new Google Sheet with data and return its URL

### Export Guidelines
- Offer export after presenting data results
- Use descriptive sheet names (e.g., "Revenue by City - Q1 2024")
- Include headers with clear column names
- Format numbers and dates appropriately for spreadsheets
