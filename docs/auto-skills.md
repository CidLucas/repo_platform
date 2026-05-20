# Auto-generated skills
_Generated from `blu_agent_framework.skills.SKILL_REGISTRY`._

## `analyze_csv`

- **description**: Execute SQL queries on uploaded CSV datasets and return structured results (tables, aggregates, trends).
- **prompt_name**: `skill:analyze_csv:system`
- **required_tools**: `peek_csv_columns`
- **max_turns**: 5
- **on_max_turns**: `return_partial`
- **tags**: analytics, csv, sql

## `extract_document`

- **description**: Extract text, tables, and structured fields from uploaded documents using OCR; optionally summarise sections.
- **prompt_name**: `skill:extract_document:system`
- **required_tools**: `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data`
- **max_turns**: 4
- **on_max_turns**: `return_partial`
- **tags**: ocr, documents, extraction

## `rag_search`

- **description**: Search the client knowledge base via vector similarity and synthesise an answer from the retrieved passages.
- **prompt_name**: `skill:rag_search:system`
- **required_tools**: `executar_rag_cliente`
- **max_turns**: 3
- **on_max_turns**: `return_partial`
- **tags**: rag, knowledge-base, search

## `write_to_kb`

- **description**: Save an analysis result, extracted data, or summary to the client knowledge base for future retrieval.
- **prompt_name**: `skill:write_to_kb:system`
- **required_tools**: `write_summary_to_kb`
- **max_turns**: 2
- **on_max_turns**: `return_partial`
- **tags**: knowledge-base, persistence, documents

