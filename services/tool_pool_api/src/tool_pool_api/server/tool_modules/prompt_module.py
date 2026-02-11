# tool_pool_api/server/tool_modules/prompt_module.py
"""
Prompt Module - Native MCP Prompts for Prompt Management

Uses FastMCP's native @mcp.prompt decorator to expose prompts as first-class
MCP prompts (not tools). This follows the MCP specification where prompts are
reusable templates that clients can request with arguments.

Key advantages over tool-based approach:
- Native MCP protocol support (prompts appear in prompts/list)
- Typed arguments instead of JSON strings
- Better client integration

Singleton patterns:
- PromptLoader: Shared via get_prompt_loader() from vizu_prompt_management
- ContextService: Uses singleton Redis pool and Supabase client
"""

import logging
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.prompts import Message

from tool_pool_api.server.dependencies import get_context_service
from vizu_prompt_management import get_prompt_loader

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# NATIVE MCP PROMPTS
# =============================================================================


async def _build_atendente_system_prompt(
    nome_empresa: str,
    prompt_personalizado: str = "",
    horario_formatado: str = "",
    tools_description: str = "",
    agent_personality: str = "",
    cliente_id: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Build the atendente system prompt with all variables.

    Uses Redis caching via ContextService when available.
    """
    variables = {
        "nome_empresa": nome_empresa,
        "prompt_personalizado": prompt_personalizado,
        "horario_formatado": horario_formatado,
        "tools_description": tools_description,
        "agent_personality": agent_personality,
    }

    loader = get_prompt_loader()  # Shared singleton
    ctx_service = get_context_service()
    cliente_uuid = UUID(cliente_id) if cliente_id else None

    try:
        # Use cached prompt loading via context_service
        content = await ctx_service.get_cached_prompt(
            name="atendente/default",
            cliente_id=cliente_uuid,
            loader=loader,
            variables=variables,
        )
        return content
    except Exception as e:
        logger.warning(f"Cache miss, loading directly: {e}")
        # Fallback to builtin
        return loader.load_builtin("atendente/default", variables).content


async def _build_text_to_sql_prompt(
    question: str,
    schema_snapshot: str,
    role: str = "analyst",
    client_id: str = "",
    allowed_views: str = "",
    allowed_aggregates: str = "",
    max_rows: int = 1000,
    cliente_id: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Build the text-to-SQL system prompt.

    Uses the same pattern as atendente - loading from DB with fallback to builtin.
    """
    variables = {
        "question": question,
        "schema_snapshot": schema_snapshot,
        "role": role,
        "client_id": client_id,
        "allowed_views": allowed_views,
        "allowed_aggregates": allowed_aggregates,
        "max_rows": str(max_rows),
    }

    loader = get_prompt_loader()  # Shared singleton
    ctx_service = get_context_service()
    cliente_uuid = UUID(cliente_id) if cliente_id else None

    try:
        content = await ctx_service.get_cached_prompt(
            name="text_to_sql/system/v1",
            cliente_id=cliente_uuid,
            loader=loader,
            variables=variables,
        )
        return content
    except Exception as e:
        logger.warning(f"Text-to-SQL prompt not in DB, using builtin: {e}")
        # Try builtin or return a minimal prompt
        try:
            return loader.load_builtin("text_to_sql/system/v1", variables).content
        except Exception:
            # Minimal fallback
            return f"""You are a SQL expert. Generate a PostgreSQL query for:
Question: {question}

Schema:
{schema_snapshot}

Role: {role}
Max rows: {max_rows}

Generate ONLY the SQL query, no explanation."""


# =============================================================================
# MODULE REGISTRATION
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register prompt module with FastMCP using native @mcp.prompt decorator."""

    # Prompt 1: Atendente System Prompt
    @mcp.prompt(
        name="atendente_system",
        description=(
            "Build the system prompt for the atendente agent. "
            "Includes company info, tools, business hours, and formatting rules."
        ),
        tags={"system", "atendente"},
    )
    async def atendente_system_prompt(
        nome_empresa: str,
        prompt_personalizado: str = "",
        horario_formatado: str = "",
        tools_description: str = "",
        agent_personality: str = "",
        ctx: Context = None,
    ) -> Message:
        """Generate the atendente system prompt with dynamic variables."""
        content = await _build_atendente_system_prompt(
            nome_empresa=nome_empresa,
            prompt_personalizado=prompt_personalizado,
            horario_formatado=horario_formatado,
            tools_description=tools_description,
            agent_personality=agent_personality,
            ctx=ctx,
        )
        return Message(content, role="system")

    # Prompt 2: Text-to-SQL System Prompt
    @mcp.prompt(
        name="text_to_sql_system",
        description=(
            "Build the system prompt for text-to-SQL generation. "
            "Includes schema, role constraints, and safety rules."
        ),
        tags={"system", "sql"},
    )
    async def text_to_sql_system_prompt(
        question: str,
        schema_snapshot: str,
        role: str = "analyst",
        client_id: str = "",
        allowed_views: str = "",
        allowed_aggregates: str = "",
        max_rows: int = 1000,
        ctx: Context = None,
    ) -> Message:
        """Generate the text-to-SQL system prompt."""
        content = await _build_text_to_sql_prompt(
            question=question,
            schema_snapshot=schema_snapshot,
            role=role,
            client_id=client_id,
            allowed_views=allowed_views,
            allowed_aggregates=allowed_aggregates,
            max_rows=max_rows,
            ctx=ctx,
        )
        return Message(content, role="system")

    # Prompt 3: RAG Context Prompt (for injecting retrieved context)
    @mcp.prompt(
        name="rag_context",
        description="Build a prompt that includes RAG-retrieved context.",
        tags={"rag", "context"},
    )
    async def rag_context_prompt(
        user_question: str,
        retrieved_context: str,
        max_context_length: int = 4000,
        ctx: Context = None,
    ) -> list[Message]:
        """Generate prompt with RAG context for the LLM."""
        # Truncate context if needed
        if len(retrieved_context) > max_context_length:
            retrieved_context = retrieved_context[:max_context_length] + "..."

        return [
            Message(
                f"""Use the following context to answer the user's question.
If the context doesn't contain relevant information, say so.

CONTEXT:
{retrieved_context}

---
Answer based ONLY on the context above.""",
                role="system",
            ),
            Message(user_question, role="user"),
        ]

    # Prompt 4: Elicitation Prompt (for asking clarifying questions)
    @mcp.prompt(
        name="elicitation",
        description="Build a prompt for asking the user clarifying questions.",
        tags={"elicitation", "clarification"},
    )
    async def elicitation_prompt(
        original_request: str,
        missing_info: str,
        options: str = "",
        ctx: Context = None,
    ) -> Message:
        """Generate an elicitation prompt to gather missing information."""
        prompt = f"""The user requested: "{original_request}"

However, I need more information: {missing_info}
"""
        if options:
            prompt += f"\nAvailable options:\n{options}"

        prompt += "\n\nPlease provide the missing information to continue."
        return Message(prompt, role="assistant")

    logger.info(
        "[Prompt Module] Registered native MCP prompts: "
        "atendente_system, text_to_sql_system, rag_context, elicitation"
    )
    return ["atendente_system", "text_to_sql_system", "rag_context", "elicitation"]
