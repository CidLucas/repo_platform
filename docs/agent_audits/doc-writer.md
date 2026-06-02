<!-- Last snapshot: 2026-06-02T18:16:57Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T18:01:54Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T17:46:20Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T17:30:47Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T17:15:55Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T17:00:18Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T16:45:04Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T16:29:02Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T16:13:30Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

<!-- Last snapshot: 2026-06-02T15:58:13Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/doc-writer.md -->

# Agent Audit: doc-writer
**Date**: 2026-06-02
**Sync Status**: SYNCED (v2 PT → v3 EN)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production, v3)

```
You are the **Document Writer** of **{{ nome_empresa }}** — specialist in creating, editing, and structuring high-quality business documents. Always respond in the user's language.

Activated for: creating new documents, editing existing documents in Google Docs or Notion, searching the knowledge base for references, and submitting documents for approval.

{{ company_profile }}

<Instructions>
Core philosophy: structure before aesthetics. A well-structured document with clear language is worth more than ornate text without hierarchy.

**New document workflow:**
1. Understand: document type, target audience, objective, formality level.
2. Call `executar_rag_cliente` to find similar existing documents, standard tone and terminology, and relevant background information.
3. Draft the structure and share it: "I propose this outline: [list]. Shall I adjust anything before writing?"
4. Write the complete document.
5. Ask: "Save to Google Docs, Notion, or keep here in the conversation?"
6. Save with `google_docs_create` or `notion_create_page` after the user decides.
7. Submit for approval via `submit_document_for_approval` when the document is formal or high-impact.

**Edit existing document workflow:**
1. Read with `google_docs_read` or `notion_read_page`.
2. Apply the requested changes.
3. Show a before/after diff of changed sections for the user to review before saving.
4. Save with `google_docs_update` or `notion_update_page` after approval.

**Search workflow:**
1. Use `executar_rag_cliente` for semantic search across the knowledge base.
2. Use `notion_search` for Notion-specific search.
3. Return relevant excerpts with a link or reference to the source document.

**Document types handled with excellence:**
SOPs | Strategic briefs | Commercial proposals | Meeting minutes | Action plans | Presentations | Internal announcements | Policies | Simple contracts.
</Instructions>

<Tool Rules> ... </Tool Rules>
<Constraints> ... </Constraints>
<Output Format> ... </Output Format>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| data_access | 4/5 | Good; `executar_rag_cliente` present; no write access risk |
| knowledge_base_write | 4/5 | Good workflow (check before write); on_max_turns=raise ✓ |
| document_io | 3/5 | Skill prompt references Notion tools (now in separate `notion` skill) — stale |
| document_curation | 4/5 | OCR/extraction pipeline well-defined; on_max_turns=raise ✓ |
| notion | 5/5 | Complete tool list, clear rules, all CRUD covered |

## Tool Coverage
- **Present in skills**: `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list`, `write_to_sheet`, `list_spreadsheets`, `export_to_sheet`, `create_spreadsheet_with_data`, `executar_rag_cliente`, `execute_sql`, `notion_*` (full set), `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data`, `compile_time_series`, `write_summary_to_kb`, `get_knowledge_status`, `update_context_document`
- **Missing / Not implemented**: `submit_document_for_approval` — referenced in agent prompt and Tool Rules but does NOT exist in tool registry. This is a gap between prompt intent and implementation.
- **Unused**: None identified

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| templates.py | Synced from Langfuse v3 (EN); version 2→3; converted PT→EN; split tool rules per tool; added "Never expose technical document IDs" to Constraints; fixed `google_docs_update` → `google_docs_write` in local copy | Langfuse is source of truth; v3 is more explicit, bilingual, and better structured |
| skills.py | Clarified `document_io` description: removed Notion mention (now in separate `notion` skill), made action-oriented | Avoids confusion between `document_io` and `notion` skills |

## Remaining Issues
**P0:** 
- `submit_document_for_approval` tool is referenced in both prompt and tool rules but does not exist in the tool registry or any service. Either implement the tool or remove the reference from the prompt. Until resolved, the agent will fail silently when attempting to submit for approval.

**P1:**
- `document_io` skill prompt (in Langfuse, `skill:document_io:system`) still mentions Notion tools (`create_notion_page`, `read_notion_page`, `update_notion_page`) that are now handled by the dedicated `notion` skill. The skill prompt should be updated in Langfuse to remove Notion references and focus on Google Workspace only.
- Langfuse agent prompt still says `google_docs_update` in the Edit workflow (step 4) — the actual tool is `google_docs_write`. Fixed locally but Langfuse v3 should be corrected.

**P2:**
- `max_turns=8` for the agent is somewhat low for complex multi-section documents that require RAG + outline approval + write + save + approval cycles. Consider increasing to 12 or making turn count skill-dependent.
- `document_curation` skill is on doc-writer's skill list but its use case (OCR pipeline) is primarily driven by context-gatherer. Consider whether doc-writer truly needs this skill or if it causes confusion.

## Agent Logical Map

**Role**: The doc-writer is the primary document production agent. It's triggered when users want to create, edit, or search for business documents.

**Typical flow**:
1. User requests a document → agent calls `executar_rag_cliente` to gather context, existing templates, and company tone.
2. Agent proposes an outline → user approves or adjusts.
3. Agent writes the document → offers to save to Google Docs (external/formal) or Notion (internal/wiki).
4. For high-impact documents → triggers HITL approval via `submit_document_for_approval` (not yet implemented).

**Handoffs and dependencies**:
- Receives routing from **frontdesk** (when user says "write", "draft", "create a document", "edit this doc").
- Uses **data_access** skill to pull context from the knowledge base (`executar_rag_cliente`).
- Saves to **Google Docs** (external sharing) or **Notion** (internal KB).
- For financial/legal documents: should hand off or notify **financeiro** or **fiscal-agent** for content validation (not currently formalized).
- **context-gatherer** may ingest documents created by doc-writer into the KB via document_curation pipeline.
- **strategy** agent may trigger doc-writer to produce a formal brief or SOP based on strategic recommendations.
