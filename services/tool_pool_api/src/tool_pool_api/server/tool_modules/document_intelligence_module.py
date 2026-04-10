# tool_pool_api/server/tool_modules/document_intelligence_module.py
"""
Document Intelligence Module — Phase 2 Tools

Tools for structured data extraction from documents, time series compilation,
and knowledge base persistence. Designed for the Document Intelligence Agent.
"""

import json
import logging
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_helpers import is_tool_accessible_by_tier
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id

from . import register_module

logger = logging.getLogger(__name__)

MAX_CHUNKS_FOR_EXTRACTION = 80
MAX_CONTENT_CHARS = 120_000  # ~30k tokens for gpt-4o


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
    """Extract document IDs from context metadata (supports both key names)."""
    meta = _extract_meta(ctx)
    raw = meta.get("uploaded_document_ids") or meta.get("attached_document_ids")
    if raw and isinstance(raw, list):
        return [str(d) for d in raw]
    return None


def _extract_cliente_id(ctx: Context) -> str | None:
    """Extract cliente_id from context metadata."""
    meta = _extract_meta(ctx)
    return meta.get("cliente_id") or meta.get("client_id")


# =============================================================================
# TOOL 1: extract_structured_data
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = (
    "You are a precise data extraction agent. Your task is to extract structured "
    "data from document chunks.\n\n"
    "RULES:\n"
    "1. Extract ONLY data that is explicitly present in the provided chunks\n"
    "2. Do NOT infer, estimate, or fabricate data points\n"
    "3. If a field cannot be found for a record, use null\n"
    "4. Return a valid JSON array of objects\n"
    "5. Each object should have exactly the fields requested\n"
    "6. If no data can be extracted, return an empty array []\n\n"
    "OUTPUT FORMAT:\n"
    "Return ONLY a JSON array. No markdown, no explanation, no code blocks. "
    "Just the raw JSON array."
)


async def _extract_structured_data_logic(
    query: str,
    fields: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> str:
    """
    **Tool: extract_structured_data**

    **Purpose:** Extract structured data from uploaded documents into a JSON table.
    Searches the session's attached documents for relevant content, then uses AI
    to extract specific fields into structured records.

    **When to use this tool:**
    - User wants to extract specific data points from documents
      (e.g., "extract all revenue figures")
    - User needs a structured table from unstructured document content
    - User asks to parse, extract, or tabulate information from uploaded files
    - You need structured data for further analysis or compilation

    **Parameters:**
    - query: (string) Describe what data to extract. Be specific about what
      records to look for.
      Example: "Extract quarterly revenue, operating costs, and net income
      from each financial period mentioned"
    - fields: (string) JSON array of field names for the output schema.
      Example: '["period", "revenue", "operating_costs", "net_income", "currency"]'

    **Returns:** JSON array of extracted records. Each record has exactly the
    requested fields.

    **IMPORTANT:** This tool only searches documents attached to the current
    session. Upload documents first, then use this tool to extract data from them.
    """
    # 1. Validate fields parameter
    try:
        field_list = json.loads(fields)
        if not isinstance(field_list, list) or not all(isinstance(f, str) for f in field_list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise ToolError(
            "Invalid 'fields' parameter. Must be a JSON array of strings. "
            'Example: \'["revenue", "quarter", "year"]\''
        )

    # 2. Get document IDs from context
    document_ids = _extract_document_ids(ctx)
    if not document_ids:
        raise ToolError(
            "No documents attached to this session. "
            "Please upload documents before using this tool."
        )

    # 3. Resolve client context for auth
    if not cliente_id:
        cliente_id = _extract_cliente_id(ctx)
    if not cliente_id:
        raise ToolError("Could not determine client identity.")

    ctx_service = get_context_service()
    vizu_context = await ctx_service.get_client_context_by_id(UUID(cliente_id))
    if not vizu_context:
        raise ToolError(f"Client context not found: {cliente_id}")

    if not is_tool_accessible_by_tier("extract_structured_data", vizu_context):
        raise ToolError("Tool 'extract_structured_data' is not enabled for this client.")

    # 4. Fetch document chunks from vector_db
    from vizu_supabase_client import get_supabase_client

    supabase = get_supabase_client()
    chunk_result = (
        supabase.schema("vector_db")
        .table("document_chunks")
        .select("content,chunk_index,document_id,metadata")
        .in_("document_id", document_ids)
        .order("document_id")
        .order("chunk_index")
        .limit(MAX_CHUNKS_FOR_EXTRACTION)
        .execute()
    )
    chunks = chunk_result.data or []

    if not chunks:
        raise ToolError(
            "No content found in the attached documents. "
            "Documents may still be processing."
        )

    # 5. Build context text from chunks (truncate if too long)
    chunk_texts = []
    total_chars = 0
    for chunk in chunks:
        content = chunk.get("content", "")
        if total_chars + len(content) > MAX_CONTENT_CHARS:
            break
        doc_id = chunk.get("document_id", "unknown")
        idx = chunk.get("chunk_index", 0)
        chunk_texts.append(f"[Document {doc_id} | Chunk {idx}]\n{content}")
        total_chars += len(content)

    context_text = "\n\n---\n\n".join(chunk_texts)

    # 6. Call LLM for extraction
    from langchain_core.messages import HumanMessage, SystemMessage
    from vizu_llm_service import ModelTier, get_model

    llm = get_model(
        tier=ModelTier.DEFAULT,
        task="extraction",
        user_id=str(vizu_context.id),
        tags=["tool_pool", "document_intelligence", "extraction"],
    )

    extraction_prompt = (
        f"EXTRACTION QUERY: {query}\n\n"
        f"FIELDS TO EXTRACT: {json.dumps(field_list)}\n\n"
        f"DOCUMENT CONTENT:\n{context_text}\n\n"
        f"Extract all matching records from the document content above. "
        f"Return a JSON array where each object has these exact fields: "
        f"{json.dumps(field_list)}. "
        f"Return ONLY the JSON array, no other text."
    )

    response = await llm.ainvoke([
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=extraction_prompt),
    ])
    result_text = response.content.strip()

    # 7. Parse and validate response — strip markdown fences if present
    if result_text.startswith("```"):
        lines = result_text.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        result_text = "\n".join(lines[1:end]).strip()

    try:
        parsed = json.loads(result_text)
        if not isinstance(parsed, list):
            parsed = [parsed]
    except json.JSONDecodeError:
        logger.warning(
            f"[ExtractStructuredData] LLM returned non-JSON: {result_text[:200]}"
        )
        # Return raw text — the agent can handle it
        return result_text

    logger.info(
        f"[ExtractStructuredData] Extracted {len(parsed)} records with "
        f"{len(field_list)} fields from {len(chunk_texts)} chunks of "
        f"{len(document_ids)} documents"
    )

    return json.dumps(parsed, ensure_ascii=False, indent=2)


# =============================================================================
# TOOL 2: compile_time_series
# =============================================================================


async def _compile_time_series_logic(
    data_json: str,
    time_field: str,
    value_fields: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> str:
    """
    **Tool: compile_time_series**

    **Purpose:** Compile structured data records into a sorted time series
    with summary statistics. Takes JSON data (from extract_structured_data
    or conversation context), sorts by time field, and produces a clean time
    series with trend analysis.

    **When to use this tool:**
    - You have extracted data with a time dimension and want to compile a time series
    - User asks to see trends, evolution, or changes over time
    - You need to organize temporal data for presentation
    - You want to identify patterns across time periods

    **Parameters:**
    - data_json: (string) JSON array of records to compile.
      Example: '[{"quarter": "Q1 2024", "revenue": 1000},
                 {"quarter": "Q2 2024", "revenue": 1200}]'
    - time_field: (string) Name of the field to use as time axis.
      Example: "quarter"
    - value_fields: (string) JSON array of field names to track as values/metrics.
      Example: '["revenue", "costs"]'

    **Returns:** JSON object with "series" (sorted records) and "summary"
    (stats per metric: count, min, max, avg, trend, change_pct).

    **Tip:** Use extract_structured_data first to extract temporal data,
    then pass the result here.
    """
    # 1. Parse inputs
    try:
        data = json.loads(data_json)
        if not isinstance(data, list):
            raise ValueError("data_json must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        raise ToolError(f"Invalid data_json: {e}")

    try:
        v_fields = json.loads(value_fields)
        if not isinstance(v_fields, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise ToolError("Invalid value_fields: must be a JSON array of strings")

    if not data:
        raise ToolError("data_json is empty — no records to compile.")

    # 2. Validate field existence
    sample = data[0]
    if time_field not in sample:
        raise ToolError(
            f"time_field '{time_field}' not found in data. "
            f"Available fields: {list(sample.keys())}"
        )

    missing = [f for f in v_fields if f not in sample]
    if missing:
        raise ToolError(
            f"value_fields {missing} not found in data. "
            f"Available fields: {list(sample.keys())}"
        )

    # 3. Sort by time_field
    sorted_data = sorted(data, key=lambda r: str(r.get(time_field, "")))

    # 4. Build series (only time + value fields)
    series = []
    for record in sorted_data:
        entry = {time_field: record.get(time_field)}
        for vf in v_fields:
            entry[vf] = record.get(vf)
        series.append(entry)

    # 5. Compute summary statistics per value field
    summary = {}
    for vf in v_fields:
        values = []
        for record in sorted_data:
            v = record.get(vf)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    continue

        if values:
            first_val = values[0]
            last_val = values[-1]
            trend = (
                "increasing" if last_val > first_val
                else ("decreasing" if last_val < first_val else "stable")
            )
            change_pct = (
                ((last_val - first_val) / abs(first_val) * 100)
                if first_val != 0 else None
            )
            summary[vf] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": round(sum(values) / len(values), 2),
                "first": first_val,
                "last": last_val,
                "trend": trend,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
            }
        else:
            summary[vf] = {"count": 0, "note": "No numeric values found"}

    result = {
        "time_field": time_field,
        "value_fields": v_fields,
        "total_records": len(series),
        "series": series,
        "summary": summary,
    }

    logger.info(
        f"[CompileTimeSeries] Compiled {len(series)} records, "
        f"{len(v_fields)} metrics, time_field='{time_field}'"
    )

    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# TOOL 3: write_summary_to_kb
# =============================================================================

KNOWLEDGE_BASE_BUCKET = "knowledge-base"


async def _write_summary_to_kb_logic(
    title: str,
    content: str,
    ctx: Context,
    category: str = "agent_summary",
    cliente_id: str | None = None,
) -> str:
    """
    **Tool: write_summary_to_kb**

    **Purpose:** Persist an analysis summary or extracted data back to the
    knowledge base. Creates a new document in the vector database that can
    be retrieved by future sessions.

    **When to use this tool:**
    - User asks to save the analysis results
    - You've completed an extraction or compilation and want to persist it
    - User wants the summary available for future reference
    - You want to create a knowledge artifact from the analysis

    **Parameters:**
    - title: (string) Title for the saved document. Be descriptive.
      Example: "Revenue Analysis Q1-Q4 2024"
    - content: (string) The full text content to save. Can be a summary,
      extracted data in text form, or a report.
    - category: (string, optional) Category tag. Default: "agent_summary".
      Options: "agent_summary", "extraction_result", "time_series_report",
      "analysis"

    **Returns:** Confirmation with the document ID of the saved document.

    **IMPORTANT:** Only call this when the user explicitly asks to save or
    persist results, or when you have a complete, valuable analysis to store.
    """
    if not title or not title.strip():
        raise ToolError("Title is required.")
    if not content or not content.strip():
        raise ToolError("Content is required.")

    # 1. Resolve client
    if not cliente_id:
        cliente_id = _extract_cliente_id(ctx)
    if not cliente_id:
        raise ToolError("Could not determine client identity.")

    ctx_service = get_context_service()
    vizu_context = await ctx_service.get_client_context_by_id(UUID(cliente_id))
    if not vizu_context:
        raise ToolError(f"Client context not found: {cliente_id}")

    if not is_tool_accessible_by_tier("write_summary_to_kb", vizu_context):
        raise ToolError("Tool 'write_summary_to_kb' is not enabled for this client.")

    # 2. Insert document record
    from vizu_supabase_client import get_storage, get_supabase_client

    supabase = get_supabase_client()
    real_client_id = str(vizu_context.id)
    safe_title = title.strip()[:80].replace(" ", "_")
    file_name = f"{safe_title}.md"

    try:
        doc_result = (
            supabase.schema("vector_db")
            .table("documents")
            .insert({
                "client_id": real_client_id,
                "file_name": file_name,
                "title": title.strip(),
                "file_type": "md",
                "source": "agent",
                "processing_mode": "simple",
                "status": "processing",
                "scope": "client",
                "category": category.strip() if category else "agent_summary",
                "description": f"Agent-generated: {title.strip()[:200]}",
            })
            .select("id")
            .single()
            .execute()
        )
        document_id = doc_result.data["id"]
    except Exception as e:
        logger.exception(f"[WriteSummaryToKB] Failed to insert document: {e}")
        raise ToolError(f"Failed to create document record: {e}")

    # 3. Upload content to Supabase Storage
    storage_path = f"{real_client_id}/{document_id}-{file_name}"
    try:
        storage = get_storage(bucket=KNOWLEDGE_BASE_BUCKET)
        storage.upload_file(content.encode("utf-8"), storage_path)
    except Exception as e:
        logger.warning(f"[WriteSummaryToKB] Storage upload failed: {e}")
        # Continue — fallback below will insert chunk directly

    # 4. Invoke process-document Edge Function for chunking + embedding
    try:
        supabase.functions.invoke(
            "process-document",
            invoke_options={
                "body": {
                    "document_id": document_id,
                    "storage_path": storage_path,
                    "client_id": real_client_id,
                    "file_name": file_name,
                    "file_type": "md",
                }
            },
        )
    except Exception as e:
        logger.warning(f"[WriteSummaryToKB] Edge Function failed: {e}, inserting chunk directly")
        # Fallback: insert single chunk (embedding trigger will handle it)
        try:
            supabase.schema("vector_db").table("document_chunks").insert({
                "document_id": document_id,
                "client_id": real_client_id,
                "content": content,
                "chunk_index": 0,
                "metadata": {"source": "agent", "title": title.strip()},
                "scope": "client",
                "category": category or "agent_summary",
            }).execute()
            supabase.schema("vector_db").table("documents").update(
                {"status": "ready"}
            ).eq("id", document_id).execute()
        except Exception as fallback_err:
            logger.exception(
                f"[WriteSummaryToKB] Fallback chunk insert failed: {fallback_err}"
            )

    logger.info(
        f"[WriteSummaryToKB] Saved document '{title.strip()}' "
        f"(id={document_id}) for client {real_client_id}"
    )

    return json.dumps({
        "success": True,
        "document_id": document_id,
        "title": title.strip(),
        "message": f"Summary '{title.strip()}' saved to knowledge base. "
                   f"It will be searchable shortly.",
    }, ensure_ascii=False)


# =============================================================================
# REGISTRATION
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register Document Intelligence tools."""

    mcp.tool(
        name="extract_structured_data",
        description=(
            "Extract structured data from uploaded documents into a JSON table. "
            "Parameters: query (describe what to extract), "
            "fields (JSON array of field names, e.g. '[\"revenue\", \"quarter\", \"year\"]'). "
            "Returns JSON array of extracted records. "
            "Documents must be uploaded to the session first."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_extract_structured_data_logic))

    mcp.tool(
        name="compile_time_series",
        description=(
            "Compile structured data records into a sorted time series with "
            "summary statistics. Parameters: data_json (JSON array of records), "
            "time_field (field name for time axis), "
            "value_fields (JSON array of metric field names). "
            "Returns sorted series + stats (min, max, avg, trend, change%). "
            "Use after extract_structured_data to organize temporal data."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_compile_time_series_logic))

    mcp.tool(
        name="write_summary_to_kb",
        description=(
            "Save an analysis summary or report to the knowledge base for "
            "future retrieval. Parameters: title (descriptive name), "
            "content (full text to save), category (optional: 'agent_summary', "
            "'extraction_result', 'time_series_report', 'analysis'). "
            "Only use when user asks to save/persist results or when you have "
            "a valuable artifact to store."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_write_summary_to_kb_logic))

    logger.info(
        "[Document Intelligence Module] 3 tools registered: "
        "extract_structured_data, compile_time_series, write_summary_to_kb"
    )
    return ["extract_structured_data", "compile_time_series", "write_summary_to_kb"]
