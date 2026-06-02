---
name: skill:document_io:system
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `skill:document_io:system`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Document IO skill — Google Docs, Sheets, Notion create/read/edit.
-->

## Document IO Skill

Criação e edição de documentos no Google Workspace e Notion.

### Ferramentas
**Google Docs**: create_doc, read_doc, update_doc, append_to_doc
**Google Sheets**: create_sheet, read_sheet, update_sheet, append_rows
**Notion**: create_notion_page, read_notion_page, update_notion_page

### Quando usar cada um
- Google Docs: documentos narrativos (relatórios, propostas, atas).
- Google Sheets: dados estruturados (orçamentos, listas, trackers).
- Notion: base de conhecimento e wiki interna.

### Regras
- Confirme nome e pasta de destino antes de criar.
- Para edições: leia o conteúdo atual primeiro, depois aplique edições cirúrgicas.
- Retorne URL ou ID do documento após a escrita.
