# tool_pool_api/server/tool_modules/sql_module.py
"""
Módulo SQL - executar_sql_agent

Natural language to SQL tool for client data queries.

**Architecture**:
- Single LLM call for SQL generation + direct execution
- Pipeline: Schema → LLM generates SQL → Execute with RLS → Return results
- client_id is injected server-side, never exposed to the LLM

**Security**:
- client_id: Injected server-side via middleware
- RLS: PostgreSQL Row-Level Security enforces data isolation
- SQL Validation: Only SELECT queries allowed, forbidden keywords blocked
"""

import logging
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import AccessToken, get_access_token

from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token,
)
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_llm_service import ModelTier, get_model
from vizu_models.vizu_client_context import VizuClientContext

# Phase 3: Use ToolRegistry for validation
from vizu_tool_registry import ToolRegistry

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# HELPERS
# =============================================================================


async def _get_enriched_schema_context(
    cliente_id: UUID,
    engine,
    include_tables: list[str] | None = None,
) -> str:
    """
    Build enriched schema context for the LLM.

    This function:
    1. Gets SqlTableConfig entries from Supabase for the client (if any)
    2. Falls back to raw SQLDatabase schema if no config exists
    3. Adds semantic metadata (descriptions, enum values, examples)

    Args:
        cliente_id: UUID of the client
        engine: SQLAlchemy engine
        include_tables: Optional list of tables to include

    Returns:
        Enriched schema string for the LLM prompt
    """
    from langchain_community.utilities.sql_database import SQLDatabase

    from vizu_supabase_client import get_supabase_client

    # Try to get client-specific table configs from Supabase
    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("sql_table_config")
            .select("*")
            .eq("client_id", str(cliente_id))
            .eq("is_active", True)
            .execute()
        )

        configs = response.data or []

        if configs:
            # Build enriched schema from configs
            schema_parts = []

            # Sort: primary tables first, then by name
            sorted_configs = sorted(
                configs,
                key=lambda c: (not c.get("is_primary", False), c.get("table_name", ""))
            )

            for config in sorted_configs:
                table_name = config.get("table_name", "")
                display_name = config.get("display_name")
                description = config.get("description")
                column_descriptions = config.get("column_descriptions") or {}
                enum_values = config.get("enum_values") or {}
                example_queries = config.get("example_queries") or []

                part = f"\n## Table: {table_name}"
                if display_name:
                    part += f" ({display_name})"
                part += "\n"

                if description:
                    part += f"Description: {description}\n"

                # Get actual schema for this table
                try:
                    db = SQLDatabase(engine=engine, include_tables=[table_name])
                    table_schema = db.get_table_info()
                    part += f"\n{table_schema}\n"
                except Exception as schema_err:
                    logger.warning(f"Could not get schema for {table_name}: {schema_err}")

                # Add column descriptions
                if column_descriptions:
                    part += "\nColumn Details:\n"
                    for col, desc in column_descriptions.items():
                        part += f"  - {col}: {desc}\n"

                # Add enum values (CRITICAL for case-sensitivity!)
                if enum_values:
                    part += "\nValid Values (use EXACTLY as shown):\n"
                    for col, values in enum_values.items():
                        part += f"  - {col}: {values}\n"

                # Add example queries
                if example_queries:
                    part += "\nExample Queries:\n"
                    for ex in example_queries[:3]:  # Max 3 examples
                        part += f"  Q: {ex.get('question', '')}\n"
                        part += f"  SQL: {ex.get('sql', '')}\n\n"

                schema_parts.append(part)

            return "\n".join(schema_parts)

    except Exception as e:
        logger.warning(f"Error loading SqlTableConfig from Supabase: {e}, falling back to raw schema")

    # Fallback: raw SQLDatabase schema
    db = SQLDatabase(engine=engine, include_tables=include_tables)
    return db.get_table_info()


def _is_tool_enabled_for_client(
    tool_name: str, context: VizuClientContext
) -> bool:
    """
    Check if a tool is enabled for a client.

    Supports both:
    - New `enabled_tools` list field
    - Legacy boolean flags

    Args:
        tool_name: Name of the tool (e.g., "executar_sql_agent")
        context: VizuClientContext

    Returns:
        True if tool is enabled
    """
    # Only use the new `enabled_tools` list and tier checks. Legacy boolean
    # flags have been removed from the models and DB via migration.
    enabled = getattr(context, "enabled_tools", None) or []

    if tool_name not in enabled:
        return False

    tier = getattr(context, "tier", "BASIC") or "BASIC"
    tool_meta = ToolRegistry.get_tool(tool_name)
    if tool_meta and not tool_meta.is_accessible_by_tier(tier):
        return False

    return True


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _executar_sql_agent_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> dict:
    """
    Executes a natural language query against the database.

    SIMPLIFIED APPROACH: Instead of using LangChain SQL Agent (which requires
    models with ReAct or function-calling support), this uses a single LLM call
    to generate SQL, then directly executes it.

    Pipeline:
    1. Get table schema info
    2. Ask LLM to generate SQL from natural language
    3. Execute SQL directly with RLS context
    4. Return results

    Args:
        query: Natural language query (e.g., "How many laptop products?")
        ctx: MCP context
        cliente_id: Client ID (injected by middleware)

    Returns:
        Dict with SQL query results
    """
    # 1. Obter dependências
    try:
        ctx_service = get_context_service()
    except Exception as e:
        logger.exception(f"Erro ao obter serviço de contexto: {e}")
        raise ToolError("Erro interno no serviço de ferramentas.")

    # 2. Resolver o Contexto Vizu
    vizu_context: VizuClientContext | None = None

    try:
        if cliente_id:
            logger.info(f"[SQL] Usando cliente_id injetado: {cliente_id}")
            try:
                uuid_obj = UUID(cliente_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {cliente_id}")

            vizu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not vizu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {cliente_id}")
        else:
            access_token: AccessToken | None = get_access_token()
            vizu_context = await load_context_from_token(ctx_service, access_token)

    except ToolError as e:
        logger.warning(f"[SQL] Falha na autorização: {e}")
        raise e
    except Exception as e:
        logger.exception(f"[SQL] Erro inesperado ao carregar contexto: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validations - Using ToolRegistry (Phase 3)
    real_client_id = vizu_context.id
    logger.info(f"[SQL] Executando para {real_client_id}...")

    if not _is_tool_enabled_for_client("executar_sql_agent", vizu_context):
        logger.warning(f"[SQL] Ferramenta desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta SQL não está habilitada para este cliente.")

    # 4. SIMPLIFIED APPROACH: Direct SQL generation and execution
    # Instead of using LangChain SQL Agent (which requires ReAct/function-calling),
    # we use a single LLM call to generate SQL and execute it directly.
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from sqlalchemy import text as sa_text

        from vizu_sql_factory.factory import get_shared_engine

        llm = get_model(
            tier=ModelTier.DEFAULT,
            task="sql_agent",
            user_id=str(real_client_id),
            tags=["tool_pool", "sql_module"],
        )

        # Get enriched schema context (uses SqlTableConfig if available)
        engine = get_shared_engine()
        table_info = await _get_enriched_schema_context(real_client_id, engine)

        logger.info(f"[SQL] Schema context length: {len(table_info)} chars")
        logger.info(f"[SQL] User question: {query}")

        # Single LLM call to generate SQL
        sql_generation_prompt = f"""You are a SQL expert. Given a database schema and a question, generate a SQL SELECT query.

DATABASE SCHEMA:
{table_info}

RULES:
1. Generate ONLY a valid SELECT query - no INSERT, UPDATE, DELETE, or DDL
2. Output ONLY the SQL query, nothing else - no explanations, no markdown
3. Use proper SQL syntax for PostgreSQL
4. If counting, use COUNT(*)
5. Use EXACT table and column names from the schema
6. For categorical columns, use the EXACT values shown in "Valid Values" section (case-sensitive!)

USER QUESTION: {query}

SQL QUERY:"""

        response = llm.invoke([
            SystemMessage(content="You are a SQL query generator. Output only valid SQL."),
            HumanMessage(content=sql_generation_prompt)
        ])

        generated_sql = response.content.strip()

        # Clean up the SQL (remove markdown code blocks if present)
        if generated_sql.startswith("```"):
            lines = generated_sql.split("\n")
            # Remove first and last lines (``` markers)
            generated_sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        generated_sql = generated_sql.strip().rstrip(";") + ";"

        logger.info(f"[SQL] Generated SQL: {generated_sql}")

        # Basic SQL validation - only allow SELECT
        sql_upper = generated_sql.upper()
        if not sql_upper.strip().startswith("SELECT"):
            logger.error(f"[SQL] Invalid SQL (not SELECT): {generated_sql}")
            return {"output": "Error: Only SELECT queries are allowed.", "sql": generated_sql}

        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for word in forbidden:
            if word in sql_upper:
                logger.error(f"[SQL] Forbidden keyword '{word}' in SQL: {generated_sql}")
                return {"output": f"Error: {word} queries are not allowed.", "sql": generated_sql}

        # Execute the SQL directly with a fresh connection (no RLS for now - add back later)
        try:
            with engine.connect() as conn:
                # Set RLS context
                conn.execute(
                    sa_text("SELECT set_config('app.current_cliente_id', :cliente_id, false)"),
                    {"cliente_id": str(real_client_id)},
                )
                conn.commit()

                # Execute query
                cursor = conn.execute(sa_text(generated_sql))
                results = cursor.fetchall()

                if not results:
                    result = "No results found."
                else:
                    columns = list(cursor.keys())
                    result = str([dict(zip(columns, row)) for row in results])

                logger.info(f"[SQL] Query result: {result[:500] if len(result) > 500 else result}")

                return {
                    "output": result,
                    "sql": generated_sql,
                    "success": True
                }
        except Exception as exec_error:
            logger.error(f"[SQL] Execution error: {exec_error}")
            return {
                "output": f"SQL execution error: {str(exec_error)}",
                "sql": generated_sql,
                "success": False
            }

    except Exception as e:
        logger.exception(f"[SQL] Erro ao executar para {real_client_id}: {e}")
        raise ToolError(f"Erro ao processar a consulta SQL: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo SQL."""
    # Register executar_sql_agent - simple natural language to SQL tool
    mcp.tool(
        name="executar_sql_agent",
        description=(
            "Executes SQL queries on the client's database to answer questions about structured data "
            "(orders, inventory, products, history, etc.). "
            "ONLY requires ONE parameter: 'query' - the natural language question. "
            "The client_id is automatically injected - do NOT ask the user for it. "
            "Example: query='How many laptop products do we have?' "
            "Use this tool whenever the user asks about data, counts, or statistics."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_sql_agent_logic))

    logger.info("[SQL Module] Ferramenta registrada: executar_sql_agent")
    return ["executar_sql_agent"]
