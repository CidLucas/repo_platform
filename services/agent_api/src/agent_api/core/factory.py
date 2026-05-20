"""
UnifiedAgentFactory — builds and caches compiled LangGraph agents.

Two graph modes:
  frontdesk   — AgentBuilder.use_default_graph(); one graph per tier cached indefinitely.
  standalone  — AgentBuilder.use_default_graph() or custom graph; one graph per session_id.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from blu_agent_framework import AgentBuilder, AgentConfig
from blu_agent_framework.checkpointer import create_checkpointer
from blu_agent_framework.mcp_client import MCPConnectionManager
from blu_agent_framework.mcp_executor import MCPToolExecutor
from blu_agent_framework.registry import AgentTypeRegistry
from blu_context_service import ContextService
from blu_context_service.redis_service import RedisService
from blu_llm_service import get_model
from blu_prompt_management import build_prompt
from blu_prompt_management.dynamic_builder import _join_fragments
from blu_supabase_client import get_supabase_client

from agent_api.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_checkpointer = None
_context_service: ContextService | None = None
_mcp_manager: MCPConnectionManager | None = None
_mcp_executor: MCPToolExecutor | None = None
_frontdesk_graphs: dict[str, Any] = {}   # "frontdesk:{tier}" → CompiledGraph
_standalone_graphs: dict[str, Any] = {}  # session_id → CompiledGraph
_factory_instance: UnifiedAgentFactory | None = None


def get_mcp_manager() -> MCPConnectionManager:
    global _mcp_manager
    if _mcp_manager is None:
        settings = get_settings()
        _mcp_manager = MCPConnectionManager(url=settings.MCP_SERVER_URL)
    return _mcp_manager


def get_mcp_executor() -> MCPToolExecutor:
    global _mcp_executor
    if _mcp_executor is None:
        settings = get_settings()
        # Share the same MCPConnectionManager so that auth headers set by
        # service._connect_mcp() (X-Cliente-Id, X-Session-Id) are visible to
        # every tool call made through the executor.
        _mcp_executor = MCPToolExecutor(
            mcp_url=settings.MCP_SERVER_URL,
            mcp_manager=get_mcp_manager(),
        )
    return _mcp_executor


def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        settings = get_settings()
        _checkpointer = create_checkpointer(settings.REDIS_URL)
    return _checkpointer


def get_context_service() -> ContextService:
    global _context_service
    if _context_service is None:
        import redis as redis_lib
        settings = get_settings()
        pool = redis_lib.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client = redis_lib.Redis(connection_pool=pool)
        redis_service = RedisService(redis_client=redis_client)
        _context_service = ContextService(cache_service=redis_service)
        logger.info("ContextService singleton created")
    return _context_service


# ---------------------------------------------------------------------------
# Built-agent result type (for standalone)
# ---------------------------------------------------------------------------


@dataclass
class BuiltAgent:
    """Compiled standalone agent with associated context."""

    graph: Any                           # CompiledGraph
    system_prompt: str = ""
    agent_name: str = "agent"
    agent_role: str = "Assistant"
    enabled_tools: list[str] = field(default_factory=list)
    client_context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# UnifiedAgentFactory
# ---------------------------------------------------------------------------


class UnifiedAgentFactory:
    """
    Builds and caches compiled LangGraph agents.

    Supervisor graphs are shared across all sessions for the same tier.
    Standalone graphs are per-session (rebuilt when catalog config changes).
    """

    def get_frontdesk_graph(self, tier: str, context_service: ContextService) -> Any:
        """
        Return a cached compiled Frontdesk graph for *tier*, building it if needed.

        Uses use_default_graph() — same topology as standalone agents.
        One compiled graph per tier; per-session state lives in the Redis checkpointer.
        """
        cache_key = f"frontdesk:{tier}"
        if cache_key not in _frontdesk_graphs:
            settings = get_settings()
            llm = get_model()
            mcp_exec = get_mcp_executor()
            checkpointer = get_checkpointer()

            cfg = AgentTypeRegistry.get("frontdesk")
            enabled_tools = cfg.enabled_tools if cfg else ["executar_rag_cliente", "execute_sql"]
            max_turns = cfg.max_turns if cfg else 4

            graph = (
                AgentBuilder(
                    AgentConfig(
                        name="Frontdesk",
                        role="Entry point specialist",
                        mcp_url=settings.MCP_SERVER_URL,
                        enabled_tools=enabled_tools,
                        max_turns=max_turns,
                        use_langfuse=True,
                    ),
                    mcp_executor=mcp_exec,
                )
                .with_llm(llm)
                .with_checkpointer(checkpointer)
                .with_context_service(context_service)
                .use_default_graph()
                .build()
            )
            _frontdesk_graphs[cache_key] = graph
            logger.info("[Factory] Built frontdesk graph for tier=%s", tier)

        return _frontdesk_graphs[cache_key]

    async def get_standalone_agent(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
    ) -> BuiltAgent:
        """
        Return a cached BuiltAgent for *session_id*, building it if needed.

        Reads agent config from the ``agent_catalog`` Supabase table and assembles
        a compiled graph using the framework AgentBuilder.
        """
        if session_id in _standalone_graphs:
            return _standalone_graphs[session_id]

        db = get_supabase_client()
        ctx_service = get_context_service()
        settings = get_settings()

        # 1. Fetch catalog entry
        result = db.table("agent_catalog").select(
            "id,name,slug,agent_config,prompt_name,required_context,"
            "requires_google,tier_required,workflow_graph"
        ).eq("id", str(agent_catalog_id)).eq("is_active", True).execute()

        if not result.data:
            raise ValueError(f"Agent catalog entry {agent_catalog_id} not found or inactive")

        catalog = result.data[0]
        agent_config_data: dict = catalog.get("agent_config") or {}
        slug: str = catalog.get("slug", "")

        # 2. Fetch session for client context
        session_result = db.table("agent_sessions").select(
            "id,collected_context,agent_catalog_id"
        ).eq("id", session_id).execute()
        collected_context: dict = {}
        if session_result.data:
            collected_context = session_result.data[0].get("collected_context") or {}

        # 3. Fetch client context for company name
        client_context_obj = await ctx_service.get_client_context_by_external_user_id(
            str(client_id)
        )
        nome_empresa = getattr(client_context_obj, "nome_empresa", "") if client_context_obj else ""
        tier = getattr(client_context_obj, "tier", "BASIC") if client_context_obj else "BASIC"
        enabled_tools: list[str] = (
            agent_config_data.get("enabled_tools") or
            (AgentTypeRegistry.get(slug).enabled_tools if AgentTypeRegistry.get(slug) else [])
        )

        # 4. Build system prompt
        prompt_name: str = catalog.get("prompt_name") or ""
        system_prompt = ""

        # Use AgentTypeRegistry fragments if available, otherwise prompt_name
        registry_cfg = AgentTypeRegistry.get(slug)

        from blu_prompt_management.variables import VariableExtractor

        # Render dynamic SQL schema if this agent uses execute_sql
        sql_schema_context = ""
        if registry_cfg and "execute_sql" in (registry_cfg.enabled_tools or []):
            sql_schema_context = VariableExtractor.render_sql_schema(
                getattr(client_context_obj, "data_schema", None)
            )

        variables: dict = {
            "nome_empresa": nome_empresa,
            "agent_name": catalog.get("name", "Agent"),
            "agent_description": catalog.get("slug", ""),
            "context_sections": "",
            "tools_description": "",
            "csv_datasets": collected_context.get("csv_datasets", []),
            "document_names": collected_context.get("document_names", []),
            "csv_datasets_details": "",
            "collected_context": collected_context,
            "filled_fields": len(collected_context),
            "total_fields": 0,
            "uploaded_file_count": 0,
            "google_connected": bool(collected_context.get("google_email")),
            "knowledge_updated_at": "",
            "document_count": 0,
            "sql_schema_context": sql_schema_context,
        }

        if prompt_name:
            try:
                system_prompt = await build_prompt(
                    name=prompt_name, variables=variables, context_service=ctx_service
                )
            except Exception as exc:
                logger.warning("[Factory] build_prompt(%s) failed: %s", prompt_name, exc)

        if not system_prompt and registry_cfg and registry_cfg.fragments:
            try:
                system_prompt = await _join_fragments(
                    fragments=registry_cfg.fragments, variables=variables,
                    context_service=ctx_service
                )
            except Exception as exc:
                logger.warning("[Factory] fragment join failed: %s", exc)

        if not system_prompt:
            system_prompt = (
                f"You are {catalog.get('name', 'an assistant')} for {nome_empresa}.\n"
                "Answer in the user's language. Use available tools when appropriate."
            )

        # 5. Build AgentConfig
        agent_cfg = AgentConfig(
            name=agent_config_data.get("name", catalog.get("name", "agent")),
            role=agent_config_data.get("role", catalog.get("name", "Assistant")),
            mcp_url=settings.MCP_SERVER_URL,
            enabled_tools=enabled_tools,
            max_turns=agent_config_data.get("max_turns", 5),
            use_langfuse=True,
        )

        # 6. Compile graph
        llm = get_model()
        mcp_exec = get_mcp_executor()
        checkpointer = get_checkpointer()

        workflow_graph = catalog.get("workflow_graph")
        builder = (
            AgentBuilder(agent_cfg, mcp_executor=mcp_exec)
            .with_llm(llm)
            .with_checkpointer(checkpointer)
        )
        if workflow_graph:
            builder.use_custom_graph(workflow_graph)
        else:
            builder.use_default_graph()

        compiled_graph = builder.build()

        built = BuiltAgent(
            graph=compiled_graph,
            system_prompt=system_prompt,
            agent_name=agent_cfg.name,
            agent_role=agent_cfg.role,
            enabled_tools=enabled_tools,
            client_context=collected_context,
            metadata={"tier": tier, "nome_empresa": nome_empresa},
        )

        _standalone_graphs[session_id] = built
        logger.info("[Factory] Built standalone agent '%s' for session=%s", slug, session_id)
        return built

    def clear_session_cache(self, session_id: str) -> None:
        _standalone_graphs.pop(session_id, None)

    def clear_frontdesk_cache(self) -> None:
        _frontdesk_graphs.clear()


# Module-level factory singleton
def get_factory() -> UnifiedAgentFactory:
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = UnifiedAgentFactory()
    return _factory_instance
