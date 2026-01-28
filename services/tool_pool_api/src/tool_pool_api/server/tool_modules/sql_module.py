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

    # Fallback: raw SQLDatabase schema - PRODUCTION SCHEMA ONLY
    # Focus on analytics_v2 star schema, exclude legacy analytics_silver and analytics_gold
    # NOTE: SQLDatabase requires schema parameter separately, not schema.table format
    production_tables = [
        "fact_sales",
        "dim_customer",
        "dim_supplier",
        "dim_product",
    ]

    # Filter to production tables only
    available_tables = production_tables if include_tables is None else include_tables

    try:
        # Use schema parameter to specify analytics_v2
        db = SQLDatabase(engine=engine, schema="analytics_v2", include_tables=available_tables)
        schema_info = db.get_table_info()

        # SECURITY: Remove any mention of client_id from schema - LLM must not know about it
        import re
        schema_info = re.sub(r'[,\s]*client_id[^\n,]*[,]?', '', schema_info, flags=re.IGNORECASE)
        schema_info = re.sub(r'\n\s*\n', '\n', schema_info)  # Clean up empty lines

        # Add guidance about the star schema
        schema_info = f"""
ANALYTICS V2 STAR SCHEMA (schema: analytics_v2)
================================================

{schema_info}

NOTE: All data is pre-filtered for your company. Write queries focusing on business logic only."""
        return schema_info
    except Exception as e:
        logger.error(f"Error loading production schema: {e}")
        # Final fallback: return a hardcoded schema for analytics_v2
        return _get_hardcoded_analytics_v2_schema()


def _get_hardcoded_analytics_v2_schema() -> str:
    """
    Fallback hardcoded schema for analytics_v2 when SQLDatabase fails.
    Security filtering is automatic - do NOT include client_id in queries.
    """
    return """
ANALYTICS V2 STAR SCHEMA (schema: analytics_v2)
================================================

TABLE: analytics_v2.fact_sales (grain: order_id, line_item_sequence)
- order_id (TEXT) - Order identifier
- line_item_sequence (INTEGER) - Line number
- data_transacao (TIMESTAMPTZ) - Transaction date (USE FOR DATE FILTERING)
- customer_id (UUID) - FK to dim_customer
- supplier_id (UUID) - FK to dim_supplier
- product_id (UUID) - FK to dim_product
- quantidade (NUMERIC) - Quantity
- valor_unitario (NUMERIC) - Unit price
- valor_total (NUMERIC) - Line total

TABLE: analytics_v2.dim_customer
- customer_id (UUID) - Primary key
- name (TEXT), cpf_cnpj (TEXT)
- endereco_cidade (TEXT), endereco_uf (TEXT)
- total_orders (INTEGER), total_revenue (NUMERIC)

TABLE: analytics_v2.dim_supplier
- supplier_id (UUID) - Primary key
- name (TEXT), cnpj (TEXT)
- endereco_cidade (TEXT), endereco_uf (TEXT)
- total_revenue (NUMERIC), total_orders_received (INTEGER)

TABLE: analytics_v2.dim_product
- product_id (UUID) - Primary key
- product_name (TEXT), categoria (TEXT)
- total_quantity_sold (NUMERIC), total_revenue (NUMERIC)

JOINS: fact_sales -> dim_customer/dim_supplier/dim_product via customer_id/supplier_id/product_id

"""


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


def _validate_sql_for_production_schema(sql: str) -> tuple[bool, str]:
    """
    Validate that generated SQL:
    1. Only references analytics_v2 schema
    2. Doesn't use legacy tables
    3. Doesn't contain sensitive data patterns


    Args:
        sql: Generated SQL query

    Returns:
        Tuple of (is_valid, error_message)
    """
    sql_lower = sql.lower()

    # Check 1: No legacy tables
    legacy_patterns = ["analytics_silver", "analytics_gold"]
    for pattern in legacy_patterns:
        if pattern in sql_lower:
            return False, f"Query references legacy table '{pattern}'. Use analytics_v2 schema instead."

    # Check 2: Must reference analytics_v2
    if "analytics_v2" not in sql_lower:
        return False, "Query does not reference analytics_v2 schema. All queries must use production schema."

    # Check 3: Reject if LLM tried to add client_id filter (it shouldn't)
    # This ensures the LLM isn't trying to manipulate security filters
    if "client_id" in sql_lower:
        return False, "Query contains client_id reference. Security filters are applied automatically - do not include them."

    return True, ""


def _inject_client_id_filter(sql: str, client_id: str) -> str:
    """
    HARD-INJECT client_id filter into the SQL query using subquery substitution.

    This function replaces each analytics_v2.table_name reference with a
    filtered subquery, ensuring client_id isolation regardless of query structure.

    Example transformation:
        FROM analytics_v2.fact_sales fs
        →
        FROM (SELECT * FROM analytics_v2.fact_sales WHERE client_id = 'xxx') fs

    Works for:
    - Simple SELECT queries
    - Queries with CTEs (WITH ... SELECT)
    - Queries with multiple joins and window functions
    - Any SQL structure - no WHERE clause manipulation needed

    Args:
        sql: Original SQL query (without client_id filter)
        client_id: Client UUID string to filter by

    Returns:
        SQL query with client_id filter injected via subqueries
    """
    import re

    # Remove trailing semicolon for processing
    sql_clean = sql.strip().rstrip(";")

    # Tables in analytics_v2 schema that need client_id filtering
    FILTERED_TABLES = ['fact_sales', 'dim_customer', 'dim_supplier', 'dim_product']

    # Pattern: analytics_v2.table_name followed by optional alias
    # Captures: (table_name) and optionally (alias)
    # Handles: FROM analytics_v2.fact_sales fs, JOIN analytics_v2.dim_customer c, etc.
    for table in FILTERED_TABLES:
        # Pattern matches: analytics_v2.table_name [AS] alias
        # We need to handle cases with and without alias
        pattern = rf'analytics_v2\.{table}(\s+(?:AS\s+)?(\w+))?'

        def replace_with_subquery(match):
            full_match = match.group(0)
            alias_part = match.group(1)  # includes space and optional AS
            alias = match.group(2)  # just the alias name

            # Build the filtered subquery
            subquery = f"(SELECT * FROM analytics_v2.{table} WHERE client_id = '{client_id}')"

            if alias:
                # Has alias: (SELECT * FROM ... WHERE ...) alias
                return f"{subquery} {alias}"
            else:
                # No alias: (SELECT * FROM ... WHERE ...) table_name
                # Use table name as default alias for compatibility
                return f"{subquery} {table}"

        sql_clean = re.sub(pattern, replace_with_subquery, sql_clean, flags=re.IGNORECASE)

    return sql_clean + ";"


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
        # SECURITY: LLM should NOT see or handle client_id, UUIDs, or sensitive identifiers
        # The client_id filter is HARD-INJECTED after SQL generation
        sql_generation_prompt = f"""You are a SQL expert for an analytics platform using a star schema architecture.

STAR SCHEMA ARCHITECTURE (schema: analytics_v2):
- FACT TABLE: fact_sales (transaction line items)
- DIMENSION TABLES: dim_customer, dim_supplier, dim_product

KEY TABLES AND COLUMNS (business data only):

fact_sales (grain: order_id, line_item_sequence):
- order_id (TEXT) - order identifier
- data_transacao (TIMESTAMPTZ) - USE THIS FOR DATE FILTERING
- quantidade (NUMERIC) - quantity sold
- valor_unitario (NUMERIC) - unit price
- valor_total (NUMERIC) - line total
- customer_id, supplier_id, product_id (UUID) - FKs to dimensions

dim_customer:
- customer_id (UUID) - Primary key for joins
- name (TEXT) - customer name
- cpf_cnpj (TEXT) - customer document
- telefone (TEXT) - phone
- total_orders (INT), total_revenue (NUMERIC), avg_order_value (NUMERIC)

dim_supplier:
- supplier_id (UUID) - Primary key for joins
- name (TEXT) - supplier name
- cnpj (TEXT) - supplier document
- telefone (TEXT) - phone
- endereco_cidade (TEXT) - city (USE FOR CITY/REGION GROUPING)
- endereco_uf (TEXT) - state (USE FOR STATE/REGION GROUPING)
- total_revenue (NUMERIC), total_orders_received (INT)

dim_product:
- product_id (UUID) - Primary key for joins
- product_name (TEXT), categoria (TEXT) - product info
- total_quantity_sold (NUMERIC), total_revenue (NUMERIC)

DATABASE SCHEMA:
{table_info}

RULES:
1. Generate ONLY valid SELECT queries - you can use WITH clauses (CTEs) followed by SELECT
2. Output ONLY the SQL query, nothing else - no explanations, no markdown
3. Use proper SQL syntax for PostgreSQL
4. MANDATORY: Use 'data_transacao' for date filtering (NOT 'order_date')
5. Use schema-qualified names: analytics_v2.fact_sales, analytics_v2.dim_customer, etc.
6. Use EXACT column names from the schema (case-sensitive)
7. Always include LIMIT clause (max 1000 rows) unless aggregating
8. Do NOT query analytics_silver or analytics_gold tables (deprecated)
9. Join fact_sales to dimensions via customer_id, supplier_id, product_id
10. NEVER output or reference specific IDs, or other sensitive identifiers in results
11. For ranking, use window functions like ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...) - very effective for top-N queries
12. All data is automatically scoped to the current client - write queries as if you're an employee querying your own company's data

EXAMPLE QUERIES:
1. "How many unique customers?"
   => SELECT COUNT(DISTINCT customer_id) FROM analytics_v2.dim_customer

2. "What is total revenue last month?"
   => SELECT SUM(valor_total) FROM analytics_v2.fact_sales
      WHERE data_transacao >= date_trunc('month', current_date - interval '1 month')
      AND data_transacao < date_trunc('month', current_date)

3. "List top 10 products by revenue"
   => SELECT product_name, SUM(valor_total) as revenue
      FROM analytics_v2.fact_sales
      JOIN analytics_v2.dim_product USING (product_id)
      GROUP BY product_name
      ORDER BY revenue DESC
      LIMIT 10

4. "Top 3 suppliers by city" (with CTE)
   => WITH supplier_sales AS (
       SELECT endereco_cidade as city, name as supplier_name,
              SUM(valor_total) as total_revenue
       FROM analytics_v2.fact_sales
       JOIN analytics_v2.dim_supplier USING (supplier_id)
       GROUP BY endereco_cidade, name
     )
     SELECT city, supplier_name, total_revenue,
            ROW_NUMBER() OVER (PARTITION BY city ORDER BY total_revenue DESC) as rank
     FROM supplier_sales
     WHERE rank <= 3
     ORDER BY city, rank

5. "Orders from last month for a specific product" (complex query)
   => SELECT order_id, data_transacao, quantidade, valor_total
      FROM analytics_v2.fact_sales
      JOIN analytics_v2.dim_product USING (product_id)
      WHERE product_name ILIKE '%product_keyword%'
      AND data_transacao >= date_trunc('month', current_date) - interval '1 month'
      AND data_transacao < date_trunc('month', current_date)
      LIMIT 1000

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

        logger.info(f"[SQL] Generated SQL (before injection): {generated_sql}")

        # Basic SQL validation - allow SELECT and WITH (CTEs)
        sql_upper = generated_sql.upper().strip()

        # Check if query is a valid SELECT or CTE (WITH...SELECT)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            logger.error(f"[SQL] Invalid SQL (must start with SELECT or WITH): {generated_sql}")
            return {"output": "Error: Only SELECT queries (including CTEs with WITH) are allowed.", "sql": generated_sql}

        # Must end with SELECT for CTEs
        if sql_upper.startswith("WITH") and "SELECT" not in sql_upper:
            logger.error(f"[SQL] Invalid CTE (no SELECT clause): {generated_sql}")
            return {"output": "Error: WITH clauses must end with a SELECT statement.", "sql": generated_sql}

        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for word in forbidden:
            if word in sql_upper:
                logger.error(f"[SQL] Forbidden keyword '{word}' in SQL: {generated_sql}")
                return {"output": f"Error: {word} queries are not allowed.", "sql": generated_sql}

        # PRODUCTION SCHEMA VALIDATION: Ensure analytics_v2 only, no client_id manipulation
        is_valid, error_msg = _validate_sql_for_production_schema(generated_sql)

        if not is_valid:
            logger.warning(f"[SQL] Production schema validation failed: {error_msg}")
            logger.warning(f"[SQL] Generated SQL: {generated_sql}")
            return {
                "output": f"Error: {error_msg}",
                "sql": generated_sql,
                "success": False
            }

        # SECURITY: HARD-INJECT client_id filter - LLM never sees this value
        client_id_str = str(real_client_id)
        final_sql = _inject_client_id_filter(generated_sql, client_id_str)
        logger.info(f"[SQL] Final SQL (with client_id injected): {final_sql}")

        # Execute the SQL directly with RLS context (defense in depth)
        # SECURITY: RLS policies on analytics_v2 tables provide additional enforcement
        try:
            with engine.connect() as conn:
                # Set RLS context for this session (defense in depth with hard-injected filter)
                # Use 'true' for local (transaction-scoped) setting
                conn.execute(
                    sa_text("SELECT set_config('app.current_cliente_id', :cliente_id, true)"),
                    {"cliente_id": client_id_str},
                )
                # NOTE: Do NOT commit here - keep RLS context and query in same transaction

                # Execute query within the same transaction where RLS context is set
                cursor = conn.execute(sa_text(final_sql))
                results = cursor.fetchall()

                if not results:
                    result = "No results found."
                else:
                    columns = list(cursor.keys())
                    result = str([dict(zip(columns, row)) for row in results])

                logger.info(f"[SQL] Query result: {result[:500] if len(result) > 500 else result}")

                return {
                    "output": result,
                    "sql": final_sql,  # Return the SQL with client_id for debugging
                    "success": True
                }
        except Exception as exec_error:
            logger.error(f"[SQL] Execution error: {exec_error}")
            return {
                "output": f"SQL execution error: {str(exec_error)}",
                "sql": final_sql,
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
            "Executes SQL queries on the client's analytics database using natural language. "
            "ALWAYS call this tool for ANY question about data, orders, sales, products, customers, suppliers, revenue, quantities, or analytics. "
            "DO NOT assume what columns exist - the tool has full schema access and will figure it out. "
            "\n\n"
            "Available tables in analytics_v2 schema:\n"
            "- fact_sales: transactional data (order_id, data_transacao, quantidade, valor_total, valor_unitario)\n"
            "- dim_customer: customer info (name, cpf_cnpj, telefone, endereco_*, total_orders, total_revenue)\n"
            "- dim_supplier: supplier info (name, cnpj, telefone, endereco_cidade, endereco_uf, total_revenue)\n"
            "- dim_product: product catalog (product_name, categoria, total_quantity_sold, total_revenue)\n"
            "\n"
            "ONLY requires ONE parameter: 'query' - the natural language question. "
            "Security filters are automatically applied. "
            "\n\n"
            "WHEN TO USE: Questions about top suppliers, revenue by region/city/state, product rankings, "
            "order history, customer analysis, sales trends, etc. "
            "ALWAYS TRY THIS TOOL FIRST for data questions - even if you're unsure about column names."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_sql_agent_logic))

    logger.info("[SQL Module] Ferramenta registrada: executar_sql_agent")
    return ["executar_sql_agent"]
