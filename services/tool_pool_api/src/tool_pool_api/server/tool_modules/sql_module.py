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

        # Add guidance about the star schema with ACTUAL column names
        schema_info = f"""
ANALYTICS V2 STAR SCHEMA (schema: analytics_v2)
================================================

This is a production star schema with fact tables and dimension tables.
All tables have a client_id column (TEXT) for multi-tenant isolation.
All tables are in the 'analytics_v2' schema - use schema-qualified names.

DATABASE SCHEMA:
{schema_info}

FACT TABLE - fact_sales:
- sale_id (UUID PK)
- client_id (TEXT) - MANDATORY filter for multi-tenant isolation
- customer_id, supplier_id, product_id (UUID FKs to dimensions)
- order_id (TEXT), line_item_sequence (INTEGER) - grain
- data_transacao (TIMESTAMPTZ) - transaction date/time column
- quantidade (NUMERIC), valor_unitario (NUMERIC), valor_total (NUMERIC)
- customer_cpf_cnpj, supplier_cnpj (TEXT) - denormalized for convenience

DIMENSION TABLES:
- dim_customer: customer_id (PK), name, cpf_cnpj, total_orders, total_revenue, etc.
- dim_supplier: supplier_id (PK), name, cnpj, total_revenue, etc.
- dim_product: product_id (PK), product_name, categoria, total_quantity_sold, etc.

KEY RELATIONSHIPS:
- analytics_v2.fact_sales.customer_id → analytics_v2.dim_customer.customer_id
- analytics_v2.fact_sales.supplier_id → analytics_v2.dim_supplier.supplier_id
- analytics_v2.fact_sales.product_id → analytics_v2.dim_product.product_id

CRITICAL COLUMN NAMES:
- Date filtering: Use 'data_transacao' column (NOT 'order_date')
- Revenue: Use 'valor_total' for line total, 'total_revenue' on dimensions
- Quantity: Use 'quantidade' on fact_sales, 'total_quantity_sold' on dim_product

IMPORTANT NOTES:
- All queries MUST include: WHERE client_id = '<client-id>'
- fact_sales grain: (order_id, line_item_sequence) - one row per line item
- All client_id values are TEXT type (UUID as string)
- Always use schema-qualified names: analytics_v2.fact_sales, analytics_v2.dim_customer, etc.
"""
        return schema_info
    except Exception as e:
        logger.error(f"Error loading production schema: {e}")
        # Final fallback: return a hardcoded schema for analytics_v2
        return _get_hardcoded_analytics_v2_schema()


def _get_hardcoded_analytics_v2_schema() -> str:
    """
    Fallback hardcoded schema for analytics_v2 when SQLDatabase fails.

    This ensures the LLM always has accurate schema information even if
    the database introspection fails.
    """
    return """
ANALYTICS V2 STAR SCHEMA (schema: analytics_v2)
================================================

This database uses a star schema for analytics. All tables are in the 'analytics_v2' schema.

TABLE: analytics_v2.fact_sales
- sale_id (UUID) - Primary key
- client_id (TEXT) - MANDATORY filter for all queries
- customer_id (UUID) - FK to dim_customer
- supplier_id (UUID) - FK to dim_supplier
- product_id (UUID) - FK to dim_product
- order_id (TEXT) - Order identifier
- line_item_sequence (INTEGER) - Line number in order
- data_transacao (TIMESTAMPTZ) - Transaction date/time (USE THIS FOR DATE FILTERING)
- quantidade (NUMERIC) - Quantity sold
- valor_unitario (NUMERIC) - Unit price
- valor_total (NUMERIC) - Line total (quantidade * valor_unitario)
- customer_cpf_cnpj (TEXT) - Customer document (denormalized)
- supplier_cnpj (TEXT) - Supplier document (denormalized)
- created_at, updated_at (TIMESTAMPTZ)

TABLE: analytics_v2.dim_customer
- customer_id (UUID) - Primary key
- client_id (TEXT) - MANDATORY filter
- cpf_cnpj (TEXT) - Customer document
- name (TEXT) - Customer name
- telefone (TEXT), endereco_* (TEXT) - Contact info
- total_orders (INTEGER), total_revenue (NUMERIC), avg_order_value (NUMERIC)
- total_quantity (NUMERIC), orders_last_30_days (INTEGER)
- frequency_per_month (NUMERIC), recency_days (INTEGER)
- lifetime_start_date, lifetime_end_date (DATE)
- created_at, updated_at (TIMESTAMPTZ)

TABLE: analytics_v2.dim_supplier
- supplier_id (UUID) - Primary key
- client_id (TEXT) - MANDATORY filter
- cnpj (TEXT) - Supplier document
- name (TEXT) - Supplier name
- telefone (TEXT), endereco_cidade, endereco_uf (TEXT) - Contact info
- total_orders_received (INTEGER), total_revenue (NUMERIC), avg_order_value (NUMERIC)
- total_products_supplied (INTEGER), frequency_per_month (NUMERIC), recency_days (INTEGER)
- first_transaction_date, last_transaction_date (DATE)
- created_at, updated_at (TIMESTAMPTZ)

TABLE: analytics_v2.dim_product
- product_id (UUID) - Primary key
- client_id (TEXT) - MANDATORY filter
- product_name (TEXT) - Product name
- categoria (TEXT) - Category
- ncm, cfop (TEXT) - Tax codes
- total_quantity_sold (NUMERIC), total_revenue (NUMERIC), avg_price (NUMERIC)
- number_of_orders (INTEGER), avg_quantity_per_order (NUMERIC)
- frequency_per_month (NUMERIC), recency_days (INTEGER), last_sale_date (DATE)
- cluster_score (NUMERIC), cluster_tier (VARCHAR)
- created_at, updated_at (TIMESTAMPTZ)

KEY RELATIONSHIPS:
- analytics_v2.fact_sales.customer_id → analytics_v2.dim_customer.customer_id
- analytics_v2.fact_sales.supplier_id → analytics_v2.dim_supplier.supplier_id
- analytics_v2.fact_sales.product_id → analytics_v2.dim_product.product_id

CRITICAL RULES:
1. ALL queries MUST filter by client_id
2. Use 'data_transacao' for date filtering (NOT 'order_date')
3. Use schema-qualified names: analytics_v2.fact_sales, analytics_v2.dim_customer, etc.
4. Revenue columns: valor_total (fact), total_revenue (dimensions)
5. Quantity columns: quantidade (fact), total_quantity_sold (dim_product)
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


def _validate_sql_for_production_schema(sql: str, client_id_str: str) -> tuple[bool, str]:
    """
    Validate that generated SQL:
    1. Only references analytics_v2 schema
    2. Includes client_id filter
    3. Doesn't use legacy tables

    Args:
        sql: Generated SQL query
        client_id_str: String representation of client_id UUID

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

    # Check 3: Must include client_id filter
    client_id_patterns = [
        f"client_id = '{client_id_str}'",
        f"client_id = \"{client_id_str}\"",
        f".client_id = '{client_id_str}'",
        f'.client_id = "{client_id_str}"',
    ]

    has_client_filter = any(pattern in sql for pattern in client_id_patterns)
    if not has_client_filter:
        return False, f"Query missing client_id filter. Must include: WHERE client_id = '{client_id_str}'"

    return True, ""


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
        # CRITICAL: Pass client_id to LLM so it filters by client for multi-tenant isolation
        sql_generation_prompt = f"""You are a SQL expert for a multi-tenant analytics platform using a star schema architecture.

CRITICAL CONTEXT:
- All queries are for CLIENT_ID: {real_client_id}
- EVERY query MUST include: WHERE client_id = '{real_client_id}'
- This is NON-NEGOTIABLE for multi-tenant data isolation

STAR SCHEMA ARCHITECTURE (schema: analytics_v2):
- FACT TABLE: fact_sales (transaction line items)
- DIMENSION TABLES: dim_customer, dim_supplier, dim_product

KEY TABLES AND COLUMNS:

fact_sales (grain: order_id, line_item_sequence):
- client_id (TEXT) - MANDATORY filter
- customer_id, supplier_id, product_id (UUID) - FKs to dimensions
- order_id (TEXT), line_item_sequence (INTEGER)
- data_transacao (TIMESTAMPTZ) - USE THIS FOR DATE FILTERING
- quantidade (NUMERIC), valor_unitario (NUMERIC), valor_total (NUMERIC)
- customer_cpf_cnpj, supplier_cnpj (TEXT) - denormalized

dim_customer:
- customer_id (UUID PK), client_id (TEXT)
- name, cpf_cnpj (TEXT)
- total_orders (INT), total_revenue (NUMERIC), avg_order_value (NUMERIC)

dim_supplier:
- supplier_id (UUID PK), client_id (TEXT)
- name, cnpj (TEXT)
- total_revenue (NUMERIC), total_orders_received (INT)

dim_product:
- product_id (UUID PK), client_id (TEXT)
- product_name, categoria (TEXT)
- total_quantity_sold (NUMERIC), total_revenue (NUMERIC)

DATABASE SCHEMA:
{table_info}

RULES:
1. Generate ONLY a valid SELECT query - no INSERT, UPDATE, DELETE, or DDL
2. Output ONLY the SQL query, nothing else - no explanations, no markdown
3. Use proper SQL syntax for PostgreSQL
4. MANDATORY: Include WHERE clause with client_id = '{real_client_id}'
5. MANDATORY: Use 'data_transacao' for date filtering (NOT 'order_date')
6. Use schema-qualified names: analytics_v2.fact_sales, analytics_v2.dim_customer, etc.
7. Use EXACT column names from the schema (case-sensitive)
8. Always include LIMIT clause (max 1000 rows) unless aggregating
9. Do NOT query analytics_silver or analytics_gold tables (deprecated)
10. Join fact_sales to dimensions via customer_id, supplier_id, product_id

EXAMPLE QUERIES:
1. "How many unique customers?"
   → SELECT COUNT(DISTINCT c.customer_id) FROM analytics_v2.dim_customer c
      WHERE c.client_id = '{real_client_id}'

2. "What is total revenue last month?"
   → SELECT SUM(fs.valor_total) FROM analytics_v2.fact_sales fs
      WHERE fs.client_id = '{real_client_id}'
      AND fs.data_transacao >= date_trunc('month', current_date - interval '1 month')
      AND fs.data_transacao < date_trunc('month', current_date)

3. "List top 10 products by revenue"
   → SELECT p.product_name, SUM(fs.valor_total) as revenue
      FROM analytics_v2.fact_sales fs
      JOIN analytics_v2.dim_product p ON fs.product_id = p.product_id
      WHERE fs.client_id = '{real_client_id}'
      GROUP BY p.product_name
      ORDER BY revenue DESC
      LIMIT 10

4. "Orders from last month for a specific product"
   → SELECT fs.order_id, fs.data_transacao, fs.quantidade, fs.valor_total
      FROM analytics_v2.fact_sales fs
      JOIN analytics_v2.dim_product p ON fs.product_id = p.product_id
      WHERE fs.client_id = '{real_client_id}'
      AND p.product_name ILIKE '%product_keyword%'
      AND fs.data_transacao >= date_trunc('month', current_date) - interval '1 month'
      AND fs.data_transacao < date_trunc('month', current_date)
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

        # PRODUCTION SCHEMA VALIDATION: Ensure analytics_v2 only
        client_id_str = str(real_client_id)
        is_valid, error_msg = _validate_sql_for_production_schema(generated_sql, client_id_str)

        if not is_valid:
            logger.warning(f"[SQL] Production schema validation failed: {error_msg}")
            logger.warning(f"[SQL] Generated SQL: {generated_sql}")
            return {
                "output": f"Error: {error_msg}",
                "sql": generated_sql,
                "success": False
            }

        # All validations passed
        logger.info(f"[SQL] SQL validation passed. Ready for execution.")

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
            "Executes SQL queries on the client's analytics database. "
            "SCHEMA IS ALREADY LOADED - DO NOT ask the user about tables or columns. "
            "Available tables in analytics_v2 schema:\n"
            "- fact_sales: order_id, data_transacao (date), quantidade (qty), valor_total (revenue), valor_unitario, customer_id, supplier_id, product_id, client_id\n"
            "- dim_customer: customer_id, name, cpf_cnpj, total_orders, total_revenue, client_id\n"
            "- dim_supplier: supplier_id, name, cnpj, total_revenue, client_id\n"
            "- dim_product: product_id, product_name, categoria, total_quantity_sold, client_id\n"
            "ONLY requires ONE parameter: 'query' - the natural language question. "
            "The client_id filter is automatically applied - DO NOT ask user for it. "
            "Examples: 'List orders from last month', 'Total revenue by supplier', 'Top 10 products by quantity', "
            "'Orders of aluminum products from last month'. "
            "ALWAYS call this tool for questions about orders, sales, products, customers, suppliers, revenue, or quantities."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_sql_agent_logic))

    logger.info("[SQL Module] Ferramenta registrada: executar_sql_agent")
    return ["executar_sql_agent"]
