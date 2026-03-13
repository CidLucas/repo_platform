# tool_pool_api/server/tool_modules/config_helper_module.py
"""
Módulo Config Helper - Ferramentas para o agente de configuração de agentes standalone

Tools for the Config Helper agent that guides users through agent setup.

**Architecture**:
- Config Helper is a full LLM agent (runs in standalone_agent_api)
- These tools handle session state mutations and queries
- All operations scoped by session_id + client_id

**Context Injection**:
- session_id: From agent state (passed in lifespan context)
- client_id: From JWT (injected by middleware)
"""

import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.dependencies import get_context_service
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_supabase_client import get_supabase_client

from . import register_module

logger = logging.getLogger(__name__)


async def _check_config_completeness_logic(ctx: Context) -> dict:
    """
    Check how many required config fields have been filled.

    Used by Config Helper to determine what info still needs to be collected.

    Returns:
        dict with:
            - total_fields: Total required fields in catalog
            - filled_fields: Number of fields already filled
            - missing: List of missing field definitions with labels
            - percent_complete: Completion percentage (0-100)
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        db = get_supabase_client()

        result = await db.table("standalone_agent_sessions").select(
            "collected_context,agent_catalog_id"
        ).eq("id", session_id).single().execute()

        session_data = result.data
        collected = session_data.get("collected_context") or {}

        # Fetch catalog to get required fields
        catalog_id = session_data.get("agent_catalog_id")
        if not catalog_id:
            raise ToolError("Session has no agent catalog configured")

        catalog_result = await db.table("agent_catalog").select(
            "required_context"
        ).eq("id", catalog_id).single().execute()

        catalog_data = catalog_result.data
        required_fields = catalog_data.get("required_context") or []

        # Count filled fields
        filled_fields = [
            f for f in required_fields if f.get("field") in collected
        ]
        missing_fields = [
            f for f in required_fields if f.get("field") not in collected
        ]

        percent = (
            int((len(filled_fields) / len(required_fields) * 100))
            if required_fields
            else 0
        )

        logger.info(
            f"[Config] Completeness check: {len(filled_fields)}/{len(required_fields)} fields filled"
        )

        return {
            "total_fields": len(required_fields),
            "filled_fields": len(filled_fields),
            "missing": missing_fields,
            "percent_complete": percent,
        }

    except Exception as e:
        logger.error(f"[Config] Failed to check completeness: {e}")
        raise ToolError(f"Failed to check completeness: {str(e)}")


async def _save_config_field_logic(
    field_name: str,
    value: str,
    ctx: Context,
) -> dict:
    """
    Save a config field value to the session.

    Config Helper calls this to persist user-provided context information.

    Args:
        field_name: Name of the field (must match catalog's required_context)
        value: Value provided by user

    Returns:
        dict confirming the save with filled count
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        db = get_supabase_client()

        # Fetch current collected_context
        result = await db.table("standalone_agent_sessions").select(
            "collected_context"
        ).eq("id", session_id).single().execute()

        current = result.data.get("collected_context") or {}

        # Validate field exists in catalog
        session_result = await db.table("standalone_agent_sessions").select(
            "agent_catalog_id"
        ).eq("id", session_id).single().execute()

        catalog_id = session_result.data.get("agent_catalog_id")
        if not catalog_id:
            raise ToolError("Session has no agent catalog")

        catalog_result = await db.table("agent_catalog").select(
            "required_context"
        ).eq("id", catalog_id).single().execute()

        required_fields = catalog_result.data.get("required_context") or []
        valid_fields = [f.get("field") for f in required_fields]

        if field_name not in valid_fields:
            raise ToolError(
                f"Invalid field name: {field_name}. Valid fields: {valid_fields}"
            )

        # Update field
        current[field_name] = value

        # Save back
        await db.table("standalone_agent_sessions").update(
            {"collected_context": current}
        ).eq("id", session_id).execute()

        logger.info(
            f"[Config] Saved field '{field_name}' for session {session_id}"
        )

        # Return updated completeness
        completeness = await _check_config_completeness_logic(ctx)

        return {
            "field_name": field_name,
            "value": value,
            "status": "saved",
            "percent_complete": completeness["percent_complete"],
        }

    except Exception as e:
        logger.error(f"[Config] Failed to save field: {e}")
        raise ToolError(f"Failed to save field: {str(e)}")


async def _get_agent_requirements_logic(
    ctx: Context,
) -> dict:
    """
    Get requirements for the agent catalog of the current session.

    Returns:
        dict with:
            - agent_name: Name of selected agent
            - required_context: Fields to collect
            - required_files: CSV/document file requirements
            - requires_google: Whether Google Sheets access needed
            - uploaded_csv_count: Already uploaded CSVs
            - uploaded_doc_count: Already uploaded documents
            - google_connected: Whether Google account is linked
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        db = get_supabase_client()

        session_result = await db.table("standalone_agent_sessions").select(
            "agent_catalog_id,uploaded_file_ids,uploaded_document_ids,google_account_email"
        ).eq("id", session_id).single().execute()

        session_data = session_result.data

        # Fetch catalog
        catalog_id = session_data.get("agent_catalog_id")
        if not catalog_id:
            raise ToolError("Session has no agent catalog configured")

        catalog_result = await db.table("agent_catalog").select(
            "name,required_context,required_files,requires_google"
        ).eq("id", catalog_id).single().execute()

        catalog = catalog_result.data

        return {
            "agent_name": catalog.get("name"),
            "required_context": catalog.get("required_context", []),
            "required_files": catalog.get("required_files", {}),
            "requires_google": catalog.get("requires_google", False),
            "uploaded_csv_count": len(
                session_data.get("uploaded_file_ids") or []
            ),
            "uploaded_doc_count": len(
                session_data.get("uploaded_document_ids") or []
            ),
            "google_connected": (
                session_data.get("google_account_email") is not None
            ),
        }

    except Exception as e:
        logger.error(f"[Config] Failed to get requirements: {e}")
        raise ToolError(f"Failed to get requirements: {str(e)}")


async def _finalize_config_logic(ctx: Context) -> dict:
    """
    Finalize configuration and mark session as ready.

    Validates all required fields are filled, then sets config_status='ready'.
    After this, the Config Helper finishes and the main agent takes over.

    Returns:
        dict with finalize status and summary for confirmation
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        # Check completeness first
        completeness = await _check_config_completeness_logic(ctx)

        if completeness["percent_complete"] < 100:
            missing_names = [
                f.get("label", f.get("field"))
                for f in completeness["missing"]
            ]
            raise ToolError(
                f"Configuration incomplete. Missing: {', '.join(missing_names)}"
            )

        # Update status to 'ready'
        db = get_supabase_client()
        await db.table("standalone_agent_sessions").update(
            {"config_status": "ready"}
        ).eq("id", session_id).execute()

        # Fetch full session for summary
        result = await db.table("standalone_agent_sessions").select(
            "agent_catalog_id,collected_context,uploaded_file_ids"
        ).eq("id", session_id).single().execute()

        session_data = result.data

        # Fetch agent name
        catalog_result = await db.table("agent_catalog").select(
            "name"
        ).eq("id", session_data.get("agent_catalog_id")).single().execute()

        agent_name = catalog_result.data.get("name", "Agent")

        logger.info(f"[Config] Configuration finalized for session {session_id}")

        return {
            "status": "finalized",
            "session_id": session_id,
            "agent_name": agent_name,
            "files_count": len(session_data.get("uploaded_file_ids") or []),
            "context_fields": len(session_data.get("collected_context") or {}),
            "message": "Configuration is complete! The agent is ready to use.",
        }

    except Exception as e:
        logger.error(f"[Config] Failed to finalize config: {e}")
        raise ToolError(f"Failed to finalize config: {str(e)}")


async def _peek_csv_columns_logic(
    file_id: str,
    ctx: Context,
) -> dict:
    """
    Peek at a CSV file's structure to help Config Helper understand data.

    Used when Config Helper wants to suggest context based on uploaded data.

    Returns:
        dict with:
            - file_name: Original file name
            - columns: Column definitions with sample values
            - row_count: Number of rows
            - file_size: File size in bytes
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        db = get_supabase_client()

        # Fetch file metadata
        result = await db.table("uploaded_files_metadata").select(
            "file_name,columns_schema,records_count,file_size"
        ).eq("id", file_id).single().execute()

        file_data = result.data

        if not file_data.get("columns_schema"):
            raise ToolError(
                f"CSV schema not yet extracted for {file_data['file_name']}"
            )

        logger.info(
            f"[Config] Peeked CSV {file_data['file_name']}: "
            f"{len(file_data['columns_schema'])} columns"
        )

        return {
            "file_name": file_data["file_name"],
            "columns": file_data["columns_schema"],
            "row_count": file_data["records_count"],
            "file_size": file_data["file_size"],
        }

    except Exception as e:
        logger.error(f"[Config] Failed to peek CSV: {e}")
        raise ToolError(f"Failed to peek CSV: {str(e)}")


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register Config Helper tools for standalone agent setup."""

    mcp.tool(
        name="check_config_completeness",
        description=(
            "Check how many required configuration fields have been filled."
            "\n\n"
            "Use this to determine what information still needs to be collected from the user."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_check_config_completeness_logic))

    mcp.tool(
        name="save_config_field",
        description=(
            "Save a configuration field value to the session."
            "\n\n"
            "After collecting user input, call this to persist it."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_save_config_field_logic))

    mcp.tool(
        name="get_agent_requirements",
        description=(
            "Get the requirements (fields, files, integrations) for the selected agent."
            "\n\n"
            "Use this to understand what needs to be configured for the current agent."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_get_agent_requirements_logic))

    mcp.tool(
        name="finalize_config",
        description=(
            "Finalize configuration and mark session as ready to activate."
            "\n\n"
            "Call this when all required fields are filled and files are uploaded."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_finalize_config_logic))

    mcp.tool(
        name="peek_csv_columns",
        description=(
            "Peek at a CSV file's columns to understand the data structure."
            "\n\n"
            "Use this to suggest context or confirm data matches requirements."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_peek_csv_columns_logic))

    logger.info(
        "[Config Helper Module] Tools registered: "
        "check_config_completeness, save_config_field, get_agent_requirements, "
        "finalize_config, peek_csv_columns"
    )

    return [
        "check_config_completeness",
        "save_config_field",
        "get_agent_requirements",
        "finalize_config",
        "peek_csv_columns",
    ]
