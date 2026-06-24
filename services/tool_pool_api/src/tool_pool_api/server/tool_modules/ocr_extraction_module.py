# tool_pool_api/server/tool_modules/ocr_extraction_module.py
"""
OCR & Structured Data Extraction Module

Tools for document OCR with configurable extraction options (language, table mode),
structured table extraction, and LLM-powered section summarization.

Designed for AgentBuilder integration — an agent can configure extraction settings
through conversation and extract structured data from uploaded documents.

Architecture:
- Downloads document from Supabase Storage (via document_id)
- Runs Docling with configurable pipeline (OCR language, table mode)
- Returns structured output: markdown + tables (JSON) + text sections
- Optionally enriches with LLM summarization
"""

import io
import json
import logging
import re
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_helpers import is_tool_accessible_by_tier

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_BUCKET = "knowledge-base"
MAX_CONTENT_CHARS_FOR_SUMMARY = 80_000  # ~20k tokens


# =============================================================================
# HELPERS
# =============================================================================


def _extract_meta(ctx: Context) -> dict:
    """Extract metadata dict from MCP request context."""
    if not ctx or not hasattr(ctx, "request_context"):
        return {}
    meta = getattr(ctx.request_context, "meta", None)
    if not meta:
        return {}
    return meta.model_dump() if hasattr(meta, "model_dump") else dict(meta)


def _extract_document_ids(ctx: Context) -> list[str] | None:
    """Extract document IDs from context metadata."""
    meta = _extract_meta(ctx)
    raw = meta.get("uploaded_document_ids") or meta.get("attached_document_ids")
    if raw and isinstance(raw, list):
        return [str(d) for d in raw]
    return None


def _extract_client_id(ctx: Context) -> str | None:
    """Extract client_id from context metadata."""
    meta = _extract_meta(ctx)
    return meta.get("client_id") or meta.get("client_id")


def _parse_brazilian_number(val: str) -> float | None:
    """Convert Brazilian number format (1.234,56) to float."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if val in ("-", "", " ", "n/a", "N/A"):
        return None
    val = re.sub(r"[R$\s]", "", val)
    val = val.replace(".", "").replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


# =============================================================================
# TOOL 1: extract_document_with_ocr
# =============================================================================


async def _extract_document_with_ocr_logic(
    ocr_languages: str,
    table_mode: str,
    ctx: Context,
    client_id: str | None = None,
) -> str:
    """
    **Tool: extract_document_with_ocr**

    **Purpose:** Extract text, tables, and structured data from uploaded documents
    using OCR with configurable options. Returns markdown text plus tables as
    structured JSON data — not just plain text.

    **When to use this tool:**
    - User uploads a PDF/DOCX that contains scanned content, images, or tables
    - You need to extract tables from financial reports, price lists, invoices
    - User needs OCR for documents in Portuguese or other non-English languages
    - You need structured table data (columns, rows) rather than just text

    **Parameters:**
    - ocr_languages: (string) Comma-separated ISO 639-3 language codes for OCR.
      Examples: "pt,en" (Portuguese + English), "en" (English only),
      "es,en" (Spanish + English). Use "pt,en" for Brazilian documents.
    - table_mode: (string) Table extraction quality: "fast" or "accurate".
      Use "accurate" for complex tables (merged cells, multi-level headers).
      Use "fast" for simple tables or when speed matters.

    **Returns:** JSON object with:
    - markdown: Full document as markdown text
    - tables: List of tables with columns and data as JSON records
    - text_sections: Document text split by headers
    - stats: Extraction statistics (chars, table count, settings used)

    **IMPORTANT:** Documents must be uploaded to the session first.
    This tool processes the uploaded documents with enhanced OCR, which is
    more thorough than the default text extraction.
    """
    # 1. Parse and validate parameters
    languages = [lang.strip() for lang in ocr_languages.split(",") if lang.strip()]
    if not languages:
        languages = ["en"]

    if table_mode not in ("fast", "accurate"):
        raise ToolError("table_mode must be 'fast' or 'accurate'")

    # 2. Get document IDs from context
    document_ids = _extract_document_ids(ctx)
    if not document_ids:
        raise ToolError(
            "No documents attached to this session. "
            "Please upload documents before using this tool."
        )

    # 3. Resolve client context
    if not client_id:
        client_id = _extract_client_id(ctx)
    if not client_id:
        raise ToolError("Could not determine client identity.")

    ctx_service = get_context_service()
    blu_context = await ctx_service.get_client_context_by_id(UUID(client_id))
    if not blu_context:
        raise ToolError(f"Client context not found: {client_id}")

    if not is_tool_accessible_by_tier("extract_document_with_ocr", blu_context):
        raise ToolError("Tool 'extract_document_with_ocr' is not enabled for this client.")

    # 4. Fetch document metadata from vector_db
    from blu_supabase_client import get_storage, get_supabase_client

    supabase = get_supabase_client()
    real_client_id = str(blu_context.id)

    doc_result = (
        supabase.schema("vector_db")
        .table("documents")
        .select("id,file_name,storage_path,file_type")
        .in_("id", document_ids)
        .execute()
    )
    documents = doc_result.data or []

    if not documents:
        raise ToolError("No document records found for the provided IDs.")

    # 5. Process each document with Docling
    from blu_parsers.parsers.docling_parser import (
        DoclingExtractionOptions,
        DoclingParser,
    )

    options = DoclingExtractionOptions(
        ocr_enabled=True,
        ocr_languages=languages,
        table_mode=table_mode,
        do_table_structure=True,
    )
    parser = DoclingParser(options=options)
    storage = get_storage(bucket=KNOWLEDGE_BASE_BUCKET)

    all_results = []
    for doc_meta in documents:
        doc_id = doc_meta["id"]
        file_name = doc_meta.get("file_name", "unknown")
        storage_path = doc_meta.get("storage_path")

        if not storage_path:
            # Try to build path from convention
            storage_path = f"{real_client_id}/{doc_id}-{file_name}"

        try:
            file_bytes = storage.download_file(storage_path)
            file_stream = io.BytesIO(file_bytes)

            extraction = parser.parse_structured(file_stream)
            extraction["document_id"] = doc_id
            extraction["file_name"] = file_name
            all_results.append(extraction)

            logger.info(
                f"[OCR Extraction] {file_name}: "
                f"{extraction['stats'].get('total_chars', 0)} chars, "
                f"{extraction['stats'].get('num_tables', 0)} tables"
            )
        except Exception as e:
            logger.error(f"[OCR Extraction] Failed to process {file_name}: {e}")
            all_results.append({
                "document_id": doc_id,
                "file_name": file_name,
                "markdown": "",
                "tables": [],
                "stats": {"error": str(e)},
            })

    # 6. Build response
    combined = {
        "documents_processed": len(all_results),
        "extraction_options": options.to_dict(),
        "results": [],
    }

    for result in all_results:
        # Split markdown into sections by headers
        markdown = result.get("markdown", "")
        sections = re.split(r"(^#+\s+.+$)", markdown, flags=re.MULTILINE)
        text_sections = []
        current_header = None
        for part in sections:
            part = part.strip()
            if not part:
                continue
            if re.match(r"^#+\s+", part):
                current_header = part.lstrip("# ").strip()
            else:
                text_sections.append({
                    "header": current_header,
                    "content": part[:2000],
                    "char_count": len(part),
                })

        combined["results"].append({
            "document_id": result.get("document_id"),
            "file_name": result.get("file_name"),
            "tables": result.get("tables", []),
            "text_sections": text_sections,
            "stats": result.get("stats", {}),
        })

    logger.info(
        f"[OCR Extraction] Processed {len(all_results)} documents, "
        f"languages={languages}, table_mode={table_mode}"
    )

    return json.dumps(combined, ensure_ascii=False, default=str)


# =============================================================================
# TOOL 2: summarize_document_sections
# =============================================================================


async def _summarize_document_sections_logic(
    sections_json: str,
    language: str,
    ctx: Context,
    client_id: str | None = None,
) -> str:
    """
    **Tool: summarize_document_sections**

    **Purpose:** Summarize text sections extracted from a document using LLM.
    Takes the text_sections output from extract_document_with_ocr and produces
    concise summaries for each section.

    **When to use this tool:**
    - After using extract_document_with_ocr, to summarize the text content
    - User wants a quick overview of what the document contains
    - You need to condense long narrative sections into key points

    **Parameters:**
    - sections_json: (string) JSON array of section objects from
      extract_document_with_ocr. Each object should have "header" and "content".
      Example: '[{"header": "Market Analysis", "content": "The market..."}]'
    - language: (string) Language for the summary output.
      Options: "pt" (Portuguese), "en" (English), "auto" (same as input).
      Default: "auto"

    **Returns:** JSON array of sections with added "summary" field.

    **Tip:** Use extract_document_with_ocr first, then pass the text_sections
    to this tool for summarization.
    """
    # 1. Parse input
    try:
        sections = json.loads(sections_json)
        if not isinstance(sections, list):
            raise ValueError("Must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        raise ToolError(f"Invalid sections_json: {e}")

    if not sections:
        raise ToolError("No sections provided.")

    if language not in ("pt", "en", "auto"):
        language = "auto"

    # 2. Resolve client context
    if not client_id:
        client_id = _extract_client_id(ctx)
    if not client_id:
        raise ToolError("Could not determine client identity.")

    ctx_service = get_context_service()
    blu_context = await ctx_service.get_client_context_by_id(UUID(client_id))
    if not blu_context:
        raise ToolError(f"Client context not found: {client_id}")

    # 3. Summarize with LLM
    from langchain_core.messages import HumanMessage, SystemMessage

    from blu_llm_service import ModelTier, get_model

    llm = get_model(
        tier=ModelTier.FAST,
        task="extraction",
        user_id=str(blu_context.id),
        tags=["tool_pool", "ocr_extraction", "summarization"],
    )

    lang_instruction = {
        "pt": "Respond in Portuguese.",
        "en": "Respond in English.",
        "auto": "Respond in the same language as the input text.",
    }[language]

    system_prompt = (
        "You are a data extraction assistant. For each document section, "
        "produce a concise summary in 2-3 bullet points. "
        "Focus on key data points, trends, and actionable insights. "
        f"{lang_instruction}"
    )

    summarized = []
    total_chars = 0
    for section in sections:
        content = section.get("content", "")
        header = section.get("header", "")

        if len(content) < 50 or total_chars > MAX_CONTENT_CHARS_FOR_SUMMARY:
            summarized.append({**section, "summary": None})
            continue

        try:
            context_prefix = f"Section: {header}\n\n" if header else ""
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"{context_prefix}{content[:3000]}"),
            ])
            summarized.append({**section, "summary": response.content})
            total_chars += len(content)
        except Exception as e:
            logger.warning(f"[SummarizeSections] Failed for '{header}': {e}")
            summarized.append({**section, "summary": f"Summarization failed: {e}"})

    logger.info(
        f"[SummarizeSections] Summarized {sum(1 for s in summarized if s.get('summary'))} "
        f"of {len(sections)} sections"
    )

    return json.dumps(summarized, ensure_ascii=False)


# =============================================================================
# REGISTRATION
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register OCR & Extraction tools."""

    mcp.tool(
        name="extract_document_with_ocr",
        description=(
            "Extract text, tables, and structured data from uploaded documents "
            "using OCR with configurable options. "
            "Parameters: ocr_languages (comma-separated ISO 639-1 codes, e.g. 'pt,en'), "
            "table_mode ('fast' or 'accurate'). "
            "Returns JSON with markdown text, tables as structured data, "
            "and text sections split by headers. "
            "Documents must be uploaded to the session first. "
            "Use 'pt,en' for Brazilian documents, 'accurate' for complex tables."
        ),
    )(mcp_inject_client_id(get_context_service)(_extract_document_with_ocr_logic))

    mcp.tool(
        name="summarize_document_sections",
        description=(
            "Summarize text sections from a document using LLM. "
            "Parameters: sections_json (JSON array of {header, content} objects — "
            "use the text_sections output from extract_document_with_ocr), "
            "language ('pt', 'en', or 'auto'). "
            "Returns sections with added 'summary' field. "
            "Use after extract_document_with_ocr to get quick overviews."
        ),
    )(mcp_inject_client_id(get_context_service)(_summarize_document_sections_logic))

    logger.info(
        "[OCR Extraction Module] 2 tools registered: "
        "extract_document_with_ocr, summarize_document_sections"
    )
    return ["extract_document_with_ocr", "summarize_document_sections"]
