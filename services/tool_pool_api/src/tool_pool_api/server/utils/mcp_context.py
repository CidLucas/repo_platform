"""
MCP request-context helpers for tool_pool_api tool modules.

Extracts metadata fields that the agent framework attaches to every MCP
request (client_id, uploaded document IDs, etc.) from the FastMCP
``Context`` object. Previously these were duplicated verbatim in
document_intelligence_module and ocr_extraction_module (and partially
hand-rolled in rag_module). Consolidating them here gives a single
source of truth and makes the extraction logic discoverable.

Note: ``_extract_client_id`` previously had a dead ``or meta.get("client_id")``
tail (checking the same key twice). The shared version drops the duplicate
— behaviour is preserved because the second branch was a no-op.
"""

from __future__ import annotations

from fastmcp import Context


def extract_meta(ctx: Context) -> dict:
    """Return the request metadata dict attached to an MCP call.

    Handles the FastMCP quirk of sometimes returning a Pydantic model
    (with ``model_dump()``) and sometimes a plain dict. Returns an empty
    dict when no metadata is attached.
    """
    if not ctx or not hasattr(ctx, "request_context"):
        return {}
    meta = getattr(ctx.request_context, "meta", None)
    if not meta:
        return {}
    return meta.model_dump() if hasattr(meta, "model_dump") else dict(meta)


def extract_document_ids(ctx: Context) -> list[str] | None:
    """Return the list of document IDs attached to this MCP call.

    Accepts both ``uploaded_document_ids`` (newer) and
    ``attached_document_ids`` (legacy) for backward compatibility.
    All IDs are stringified.
    """
    meta = extract_meta(ctx)
    raw = meta.get("uploaded_document_ids") or meta.get("attached_document_ids")
    if raw and isinstance(raw, list):
        return [str(d) for d in raw]
    return None


def extract_client_id(ctx: Context) -> str | None:
    """Return the ``client_id`` attached to this MCP call, or None."""
    meta = extract_meta(ctx)
    return meta.get("client_id")
