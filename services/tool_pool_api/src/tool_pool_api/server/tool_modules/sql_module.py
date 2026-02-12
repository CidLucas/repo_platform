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

**Context 2.0**:
- Uses modular context sections for enriched prompts
- data_schema, policies, and company_profile guide SQL generation
"""

import logging
import time
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import AccessToken, get_access_token, get_http_headers

from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token,
)
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_llm_service import ModelTier, get_model

# Context 2.0: Import ContextSection for selective injection
from vizu_models.enums import ContextSection
from vizu_models.vizu_client_context import VizuClientContext
from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# HELPERS
# =============================================================================

import re


def _strip_markdown_code_block(text: str) -> str:
    """
    Remove markdown code block markers from text.

    Handles various formats:
    - ```sql ... ```
    - ```python ... ```
    - ``` ... ```

    Args:
        text: Text potentially wrapped in markdown code block

    Returns:
        Text with markdown code block markers removed
    """
    text = text.strip()
    # Pattern matches ```language\n content \n``` or just ```\n content \n```
    pattern = r"^```(?:\w+)?\n?(.*?)```$"
    match = re.match(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else text


async def _get_enriched_schema_context(
    cliente_id: UUID,
    engine,
    include_tables: list[str] | None = None,
    context_service=None,
) -> str:
    """
    Build enriched schema context for the LLM.

    This function:
    1. Gets SqlTableConfig entries via ContextService (Redis-cached)
    2. Falls back to raw SQLDatabase schema if no config exists
    3. Adds semantic metadata (descriptions, enum values, examples)

    Args:
        cliente_id: UUID of the client
        engine: SQLAlchemy engine
        include_tables: Optional list of tables to include
        context_service: Optional ContextService for cached config retrieval

    Returns:
        Enriched schema string for the LLM prompt
    """
    from langchain_community.utilities.sql_database import SQLDatabase

    # Try to get client-specific table configs (cached via ContextService)
    try:
        # Use context_service if provided, otherwise get singleton
        if context_service is None:
            context_service = get_context_service()

        configs = await context_service.get_sql_table_configs(cliente_id)

        if configs:
            # Build enriched schema from configs
            schema_parts = []

            # Sort: primary tables first, then by name
            sorted_configs = sorted(
                configs, key=lambda c: (not c.get("is_primary", False), c.get("table_name", ""))
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
        logger.warning(
            f"Error loading SqlTableConfig from Supabase: {e}, falling back to raw schema"
        )

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

        schema_info = re.sub(r"[,\s]*client_id[^\n,]*[,]?", "", schema_info, flags=re.IGNORECASE)
        schema_info = re.sub(r"\n\s*\n", "\n", schema_info)  # Clean up empty lines

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
- product_name (TEXT) - USE FOR FILTERING BY PRODUCT TYPE (e.g., ILIKE '%ALUMINIO%')
- categoria (TEXT) - OFTEN NULL, prefer product_name for searches
- total_quantity_sold (NUMERIC), total_revenue (NUMERIC)

JOINS: fact_sales -> dim_customer/dim_supplier/dim_product via customer_id/supplier_id/product_id

"""


def _build_context_guidance(vizu_context: VizuClientContext) -> str:
    """
    Build context-aware guidance for SQL generation using Context 2.0 sections.

    Extracts relevant information from:
    - data_schema: Available data, key metrics, report preferences
    - policies: Data handling rules, operational limits
    - company_profile: Industry context for better understanding

    Returns:
        Formatted guidance string for the LLM
    """
    guidance_parts = []

    # Extract company context for industry understanding
    company = vizu_context.company_profile
    if company:
        industry = company.get("industry", "")
        business_type = company.get("business_archetype", "")
        if industry or business_type:
            guidance_parts.append(
                f"BUSINESS CONTEXT: {industry or ''} {business_type or ''}".strip()
            )

    # Extract data schema guidance
    data_schema = vizu_context.data_schema
    if data_schema:
        key_metrics = data_schema.get("key_metrics", [])
        if key_metrics:
            guidance_parts.append(f"KEY METRICS: {', '.join(key_metrics[:5])}")

        report_types = data_schema.get("report_types", [])
        if report_types:
            guidance_parts.append(f"COMMON REPORTS: {', '.join(report_types[:5])}")

        data_notes = data_schema.get("data_notes", "")
        if data_notes:
            guidance_parts.append(f"DATA NOTES: {data_notes}")

    # Extract policies for data handling
    policies = vizu_context.policies
    if policies:
        data_rules = policies.get("data_handling_rules", [])
        if data_rules:
            guidance_parts.append(f"DATA RULES: {'; '.join(data_rules[:3])}")

    if not guidance_parts:
        return ""

    return "\n=== CLIENT CONTEXT ===\n" + "\n".join(guidance_parts) + "\n"


# Use shared helper - see tool_helpers.py for implementation
from tool_pool_api.server.tool_helpers import is_tool_enabled_for_client


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
            return (
                False,
                f"Query references legacy table '{pattern}'. Use analytics_v2 schema instead.",
            )

    # Check 2: Must reference analytics_v2
    if "analytics_v2" not in sql_lower:
        return (
            False,
            "Query does not reference analytics_v2 schema. All queries must use production schema.",
        )

    # Check 3: Reject if LLM tried to add client_id filter (it shouldn't)
    # This ensures the LLM isn't trying to manipulate security filters
    if "client_id" in sql_lower:
        return (
            False,
            "Query contains client_id reference. Security filters are applied automatically - do not include them.",
        )

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
    FILTERED_TABLES = ["fact_sales", "dim_customer", "dim_supplier", "dim_product"]

    # Pattern: analytics_v2.table_name followed by optional alias
    # Captures: (table_name) and optionally (alias)
    # Handles: FROM analytics_v2.fact_sales fs, JOIN analytics_v2.dim_customer c, etc.
    for table in FILTERED_TABLES:
        # Pattern matches: analytics_v2.table_name [AS] alias
        # We need to handle cases with and without alias
        pattern = rf"analytics_v2\.{table}(\s+(?:AS\s+)?(\w+))?"

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
        # Include cause in error for better debugging
        raise ToolError(f"Erro interno no serviço de ferramentas: {type(e).__name__}: {e}")

    # 2. Resolver o Contexto Vizu
    # Priority: 1) cliente_id param (injected by decorator), 2) access token
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
            # Fallback to FastMCP access token (direct API calls)
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

    if not is_tool_enabled_for_client("executar_sql_agent", vizu_context):
        logger.warning(f"[SQL] Ferramenta desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta SQL não está habilitada para este cliente.")

    # 4. SIMPLIFIED APPROACH: Direct SQL generation and execution
    # Instead of using LangChain SQL Agent (which requires ReAct/function-calling),
    # we use a single LLM call to generate SQL and execute it directly.
    try:
        from langchain_core.messages import SystemMessage
        from sqlalchemy import text as sa_text

        from vizu_sql_factory.factory import get_shared_engine

        llm = get_model(
            tier=ModelTier.DEFAULT,
            task="sql_agent",
            user_id=str(real_client_id),
            tags=["tool_pool", "sql_module"],
        )

        schema_start = time.perf_counter()

        # Get enriched schema context (uses Redis-cached SqlTableConfig)
        engine = get_shared_engine()
        table_info = await _get_enriched_schema_context(
            real_client_id, engine, context_service=ctx_service
        )

        # Context 2.0: Get client-specific guidance from context sections
        context_guidance = _build_context_guidance(vizu_context)

        logger.debug(f"[SQL] Schema loaded in {(time.perf_counter() - schema_start) * 1000:.1f}ms")

        logger.info(f"[SQL] Schema context length: {len(table_info)} chars")
        logger.info(f"[SQL] Context guidance length: {len(context_guidance)} chars")
        logger.info(f"[SQL] User question: {query}")

        # FULL PROMPT DEBUG - Enable with LOG_LEVEL=DEBUG to inspect complete SQL generation prompt
        logger.debug("=== SQL GENERATION FULL PROMPT ===")
        logger.debug(f"Context guidance:\n{context_guidance}")
        logger.debug(f"\nTable info:\n{table_info}")
        logger.debug(f"\nUser question: {query}")
        logger.debug("=== END SQL GENERATION PROMPT ===")

        # Single LLM call to generate SQL
        # SECURITY: LLM should NOT see or handle client_id, UUIDs, or sensitive identifiers
        # The client_id filter is HARD-INJECTED after SQL generation
        # Prompt loaded from Langfuse (with Redis cache) → builtin fallback
        from vizu_prompt_management import build_prompt as _build_prompt

        sql_generation_prompt = await _build_prompt(
            name="tool/sql-generation",
            variables={
                "query": query,
                "context_guidance": context_guidance,
                "table_info": table_info,
            },
            context_service=ctx_service,
        )

        llm_start = time.perf_counter()

        # Use both SystemMessage (with schema/rules) and HumanMessage (explicit query)
        # This improves instruction-following for open-source models
        from langchain_core.messages import HumanMessage

        response = await llm.ainvoke(
            [
                SystemMessage(content=sql_generation_prompt),
                HumanMessage(
                    content=f"Generate SQL for: {query}\n\nRespond with ONLY the SQL query, no explanations."
                ),
            ],
            config={
                "metadata": {
                    "langfuse_trace_name": "sql_generation",
                    "langfuse_session_id": str(real_client_id),
                    "langfuse_user_id": str(real_client_id),
                    "langfuse_tags": ["sql_generation", "tool_pool"],
                },
                "run_name": "sql_generation",
            },
        )

        generated_sql = response.content.strip()

        llm_duration = (time.perf_counter() - llm_start) * 1000
        logger.info(f"[SQL] LLM generated SQL in {llm_duration:.1f}ms")

        # Clean up the SQL (remove markdown code blocks if present)
        generated_sql = _strip_markdown_code_block(generated_sql)
        generated_sql = generated_sql.strip().rstrip(";") + ";"

        logger.info(f"[SQL] Generated SQL (before injection): {generated_sql}")

        # Basic SQL validation - allow SELECT and WITH (CTEs)
        sql_upper = generated_sql.upper().strip()

        # Check if query is a valid SELECT or CTE (WITH...SELECT)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            logger.error(f"[SQL] Invalid SQL (must start with SELECT or WITH): {generated_sql}")
            return {
                "output": "Error: Only SELECT queries (including CTEs with WITH) are allowed.",
                "sql": generated_sql,
            }

        # Must end with SELECT for CTEs
        if sql_upper.startswith("WITH") and "SELECT" not in sql_upper:
            logger.error(f"[SQL] Invalid CTE (no SELECT clause): {generated_sql}")
            return {
                "output": "Error: WITH clauses must end with a SELECT statement.",
                "sql": generated_sql,
            }

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
            return {"output": f"Error: {error_msg}", "sql": generated_sql, "success": False}

        # SECURITY: HARD-INJECT client_id filter - LLM never sees this value
        client_id_str = str(real_client_id)
        final_sql = _inject_client_id_filter(generated_sql, client_id_str)
        logger.info(f"[SQL] Final SQL (with client_id injected): {final_sql}")

        # Execute the SQL directly with RLS context (defense in depth)
        # SECURITY: RLS policies on analytics_v2 tables provide additional enforcement

        exec_start = time.perf_counter()

        try:
            from .structured_data_formatter import format_sql_result

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
                    return {
                        "output": "Nenhum resultado encontrado.",
                        "sql": final_sql,
                        "success": True,
                        "structured_data": None,
                    }

                columns = list(cursor.keys())
                rows_as_dicts = [dict(zip(columns, row)) for row in results]

                # Create structured data for frontend display
                # Truncate query for title display
                title_query = query[:60] + "..." if len(query) > 60 else query
                structured_data = format_sql_result(
                    columns=columns,
                    rows=rows_as_dicts,
                    sql_query=final_sql,
                    title=f"Resultado: {title_query}",
                )

                # Keep text result for backward compatibility / text-based clients
                result = str(rows_as_dicts[:20])  # Limit text output

                logger.info(
                    f"[SQL] Query result: {len(rows_as_dicts)} rows, structured_data generated"
                )

                # Store full data in Redis cache to avoid context bloat
                # The cache ref_id allows retrieval for exports without
                # storing massive datasets in conversation history
                try:
                    from vizu_context_service.tool_cache import get_tool_cache

                    cache = get_tool_cache()
                    session_id = ctx.request_context.lifespan_context.get("session_id", "default")

                    # Store full result in cache (1 hour TTL, session-scoped)
                    cache_ref_id = cache.store(
                        session_id=session_id,
                        tool_name="executar_sql_agent",
                        args={"query": query, "cliente_id": client_id_str},
                        result={
                            "all_rows": rows_as_dicts,
                            "columns": columns,
                            "sql": final_sql,
                            "row_count": len(rows_as_dicts),
                        },
                        metadata={
                            "cliente_id": client_id_str,
                            "query_preview": title_query,
                        },
                    )
                    logger.info(
                        f"[SQL] Full data cached: ref_id={cache_ref_id}, rows={len(rows_as_dicts)}"
                    )
                except Exception as cache_err:
                    logger.warning(f"[SQL] Cache store failed (non-fatal): {cache_err}")
                    cache_ref_id = None

                exec_duration = (time.perf_counter() - exec_start) * 1000
                logger.debug(f"[SQL] Query executed in {exec_duration:.1f}ms")

                # Flush Langfuse traces before returning
                from vizu_observability_bootstrap.langfuse import flush_langfuse_async

                await flush_langfuse_async()

                # Return dict - MCP handles JSON serialization
                # Use model_dump(mode='json') to ensure all values are JSON-serializable
                return {
                    "output": f"{len(rows_as_dicts)} registros encontrados",
                    "sql": final_sql,
                    "success": True,
                    "structured_data": structured_data.model_dump(mode="json"),
                    "row_count": len(rows_as_dicts),
                    "cache_ref_id": cache_ref_id,
                }
        except Exception as exec_error:
            logger.error(f"[SQL] Execution error: {exec_error}")

            # Flush Langfuse traces before returning error
            from vizu_observability_bootstrap.langfuse import flush_langfuse_async

            await flush_langfuse_async()

            return {
                "output": f"SQL execution error: {str(exec_error)}",
                "sql": final_sql,
                "success": False,
                "structured_data": None,
            }

    except Exception as e:
        logger.exception(f"[SQL] Erro ao executar para {real_client_id}: {e}")

        # Flush Langfuse traces before raising error
        from vizu_observability_bootstrap.langfuse import flush_langfuse_async

        await flush_langfuse_async()

        raise ToolError(f"Erro ao processar a consulta SQL: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo SQL."""
    # Register executar_sql_agent - simple natural language to SQL tool
    # Uses mcp_inject_cliente_id decorator to inject cliente_id from auth
    mcp.tool(
        name="executar_sql_agent",
        description=(
            "Answers data questions by querying the analytics database. "
            "\n\n"
            "⚠️ CRITICAL: Pass the user's question IN NATURAL LANGUAGE. Do NOT write SQL - the tool generates SQL internally."
            "\n\n"
            "PARAMETER 'query': The user's question exactly as they asked it (e.g., 'top 10 suppliers by revenue', 'sales by city last month')."
            "\n\n"
            "DATA AVAILABLE: sales transactions, customers, suppliers, products, revenue, quantities, dates, addresses (city/state)."
            "\n\n"
            "WHEN TO USE: Any question about data, analytics, rankings, trends, totals, comparisons. "
            "ALWAYS try this tool for data questions - it knows the schema and will figure out the right query."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_sql_agent_logic))

    logger.info("[SQL Module] Tool registered: executar_sql_agent")
    return ["executar_sql_agent"]
