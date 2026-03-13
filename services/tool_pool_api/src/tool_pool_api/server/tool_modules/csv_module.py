# tool_pool_api/server/tool_modules/csv_module.py
"""
Módulo CSV - execute_csv_query e list_csv_datasets

Tools for CSV processing in standalone agent sessions.

**Architecture**:
- Single tool pool managing multiple session engines
- Session isolation: each session's CSVs loaded into dedicated DuckDB instance
- Tool scoping via session_id: client_id determines session ownership, RLS enforced by Supabase Storage

**Security**:
- session_id: Extracted from lifespan context (set by agent state)
- client_id: Injected server-side via middleware
- SQL Validation: Only SELECT queries allowed, forbidden keywords blocked
- Storage Access: RLS enforced by Supabase on all file operations
"""

import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.csv_engine import DuckDBQueryEngine
from tool_pool_api.server.dependencies import get_context_service
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# SESSION ENGINES CACHE
# =============================================================================
# Cache DuckDB engines per session to avoid reloading CSVs
_session_engines: dict[str, DuckDBQueryEngine] = {}


def _get_session_engine(session_id: str) -> DuckDBQueryEngine:
    """Get or create DuckDB engine for a session."""
    if session_id not in _session_engines:
        _session_engines[session_id] = DuckDBQueryEngine()
    return _session_engines[session_id]


async def _execute_csv_query_logic(
    sql: str,
    ctx: Context,
) -> dict:
    """
    Execute a SQL query against uploaded CSV datasets.

    Args:
        sql: SQL SELECT query (e.g., 'SELECT * FROM vendas WHERE preco > 100')
        ctx: MCP context

    Returns:
        dict with:
            - output: Formatted result as string
            - structured_data: Result rows as list of dicts
            - row_count: Number of rows returned
            - columns: Column names
    """
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")
    session_id = ctx.request_context.lifespan_context.get("session_id")

    if not cliente_id or not session_id:
        raise ToolError("Missing cliente_id or session_id in context")

    try:
        # Get engine for this session (CSVs already loaded)
        engine = _get_session_engine(session_id)

        # Execute query
        result = await engine.execute_query(sql)

        logger.info(
            f"[CSV] Query executed for session {session_id}: {result['row_count']} rows"
        )

        return {
            "output": result["output"],
            "structured_data": result["structured_data"],
            "row_count": result["row_count"],
            "columns": result["columns"],
            "cache_ref_id": session_id,
        }

    except ValueError as e:
        raise ToolError(f"Invalid query: {str(e)}")
    except Exception as e:
        logger.error(f"[CSV] Query execution failed: {e}")
        raise ToolError(f"Query execution failed: {str(e)}")


async def _list_csv_datasets_logic(ctx: Context) -> list[dict]:
    """
    List all CSV datasets available in the current session.

    Returns:
        List of datasets with:
            - name: Table name (sanitized from file name)
            - columns: Column names
            - row_count: Number of rows

    This tool's output is injected into the agent's system prompt so it always
    knows what CSV datasets are available.
    """
    session_id = ctx.request_context.lifespan_context.get("session_id")
    cliente_id = ctx.request_context.lifespan_context.get("cliente_id")

    if not session_id or not cliente_id:
        raise ToolError("Missing session_id or cliente_id in context")

    try:
        # Get engine for this session
        engine = _get_session_engine(session_id)

        # List all loaded tables
        datasets = engine.list_tables()

        logger.info(
            f"[CSV] Listed {len(datasets)} datasets for session {session_id}"
        )

        # Format for agent display
        formatted = []
        for dataset in datasets:
            formatted.append(
                {
                    "name": dataset["name"],
                    "columns": [c["name"] for c in dataset["columns"]],
                    "row_count": dataset["row_count"],
                    "column_types": {
                        c["name"]: c["type"] for c in dataset["columns"]
                    },
                }
            )

        return formatted

    except Exception as e:
        logger.error(f"[CSV] Failed to list datasets: {e}")
        raise ToolError(f"Failed to list datasets: {str(e)}")


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register CSV tools for standalone agent sessions."""

    # CSV Query Tool
    mcp.tool(
        name="execute_csv_query",
        description=(
            "Execute SQL queries against uploaded CSV datasets."
            "\n\n"
            "Available tables: Use list_csv_datasets to see what data is loaded."
            "\n\n"
            "Supports full SQL: SELECT, JOINs, GROUP BY, aggregations, window functions, CTEs."
            "\n\n"
            "⚠️ IMPORTANT: Pass valid PostgreSQL SELECT syntax."
            "e.g. 'SELECT product, SUM(revenue) as total FROM vendas GROUP BY product ORDER BY total DESC'"
        ),
    )(mcp_inject_cliente_id(get_context_service)(_execute_csv_query_logic))

    # CSV Dataset Listing Tool
    mcp.tool(
        name="list_csv_datasets",
        description=(
            "List all CSV datasets available in the current session."
            "\n\n"
            "Returns table names, columns, and row counts."
            "\n\n"
            "Use this to discover what data is available before writing queries."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_list_csv_datasets_logic))

    logger.info(
        "[CSV Module] Tools registered: execute_csv_query, list_csv_datasets"
    )

    return [
        "execute_csv_query",
        "list_csv_datasets",
    ]
