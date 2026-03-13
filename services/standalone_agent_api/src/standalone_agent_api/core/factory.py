"""Standalone Agent Factory - Builds agents from catalog entries."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

import redis as redis_lib
from langgraph.checkpoint.redis import RedisSaver
from vizu_agent_framework import AgentBuilder, AgentConfig
from vizu_agent_framework.mcp_executor import MCPToolExecutor
from vizu_agent_framework.state import AgentState, create_initial_state
from vizu_context_service import ContextService
from vizu_context_service.redis_service import RedisService
from vizu_supabase_client import get_supabase_client
from vizu_llm_service import get_model
from vizu_prompt_management.dynamic_builder import build_prompt_full

from standalone_agent_api.config import get_settings

logger = logging.getLogger(__name__)


# Module-level singletons (same pattern as atendente_core)
_checkpointer = None
_context_service: ContextService | None = None


def _get_checkpointer():
    """Get or create the RedisSaver checkpointer singleton."""
    global _checkpointer
    if _checkpointer is None:
        settings = get_settings()
        cp = RedisSaver.from_conn_string(settings.REDIS_URL)
        # Unwrap context-manager if needed (same as atendente_core)
        if hasattr(cp, "__enter__") and not hasattr(cp, "get_next_version"):
            try:
                cp = cp.__enter__()
            except Exception:
                pass
        if hasattr(cp, "setup"):
            try:
                cp.setup()
            except Exception:
                pass
        _checkpointer = cp
    return _checkpointer


def get_context_service() -> ContextService:
    """Singleton ContextService for standalone_agent_api (Supabase mode)."""
    global _context_service
    if _context_service is None:
        settings = get_settings()
        pool = redis_lib.ConnectionPool.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        redis_client = redis_lib.Redis(connection_pool=pool)
        redis_service = RedisService(redis_client=redis_client)
        _context_service = ContextService(
            cache_service=redis_service, use_supabase=True
        )
        logger.info("ContextService singleton created (standalone_agent_api)")
    return _context_service


@dataclass
class BuiltAgent:
    """Result of building an agent — includes context for initial state."""
    graph: object  # CompiledGraph
    system_prompt: str = ""
    agent_name: str = "standalone_agent"
    agent_role: str = "Assistant"
    enabled_tools: list[str] = field(default_factory=list)
    client_context: dict = field(default_factory=dict)


class StandaloneAgentFactory:
    """
    Factory for building and caching standalone agents from catalog entries.

    Each agent is a compiled LangGraph instance scoped to a session.
    Compiled graphs are cached per session_id to avoid rebuilding.
    """

    def __init__(
        self,
        mcp_url: str | None = None,
    ):
        """Initialize factory with dependencies."""
        settings = get_settings()
        self.mcp_url = mcp_url or settings.TOOL_POOL_API_URL
        self.db = get_supabase_client()

        # Caching
        self._agent_cache: dict[str, BuiltAgent] = {}

    async def build_agent(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
    ) -> BuiltAgent:
        """
        Build a compiled LangGraph agent for a standalone session.

        Returns BuiltAgent with the graph AND context data needed for
        create_initial_state (system_prompt, enabled_tools, etc.).
        """
        # Check cache first
        if session_id in self._agent_cache:
            logger.info(f"[Factory] Returning cached agent for session {session_id}")
            return self._agent_cache[session_id]

        logger.info(f"[Factory] Building agent for session {session_id}")

        # 1. Fetch catalog entry
        catalog_result = self.db.table("agent_catalog").select(
            "id,name,agent_config,prompt_name,requires_google"
        ).eq("id", str(agent_catalog_id)).single().execute()

        catalog = catalog_result.data
        agent_config_dict = catalog.get("agent_config") or {}

        # 2. Fetch session (for context, files, etc)
        session_result = self.db.table("standalone_agent_sessions").select(
            "id,collected_context,uploaded_file_ids,uploaded_document_ids,google_account_email"
        ).eq("id", session_id).single().execute()

        session_data = session_result.data
        collected_context = session_data.get("collected_context") or {}
        uploaded_file_ids = session_data.get("uploaded_file_ids") or []
        uploaded_doc_ids = session_data.get("uploaded_document_ids") or []
        google_email = session_data.get("google_account_email")

        # 3. Build AgentConfig from catalog JSONB
        if "name" not in agent_config_dict:
            agent_config_dict["name"] = catalog.get("name", "standalone_agent")
        if "role" not in agent_config_dict:
            agent_config_dict["role"] = catalog.get("name", "Assistant")

        try:
            agent_config = AgentConfig(**agent_config_dict)
        except Exception as e:
            raise ValueError(
                f"Invalid agent_config in catalog: {str(e)}"
            ) from e

        # 4. Fetch client context via ContextService (on-demand, Redis-cached)
        context_service = get_context_service()
        client_context_data = {}
        try:
            vizu_ctx = await context_service.get_client_context_by_id(client_id)
            if vizu_ctx:
                client_context_data = {
                    "nome_empresa": getattr(vizu_ctx, "nome_empresa", ""),
                    "tier": getattr(vizu_ctx, "tier", "BASIC"),
                    "enabled_tools": getattr(vizu_ctx, "enabled_tools", []),
                }
                logger.info(
                    f"[Factory] Client context loaded: tier={client_context_data['tier']}, "
                    f"empresa={client_context_data['nome_empresa']}"
                )
        except Exception as e:
            logger.warning(f"[Factory] ContextService lookup failed for {client_id}: {e}")
            # Fallback: direct DB query
            try:
                client_result = self.db.table("clientes_vizu").select(
                    "client_id,tier,nome_empresa"
                ).eq("client_id", str(client_id)).single().execute()
                if client_result.data:
                    client_context_data = {
                        "nome_empresa": client_result.data.get("nome_empresa", ""),
                        "tier": client_result.data.get("tier", "BASIC"),
                        "enabled_tools": [],
                    }
            except Exception:
                logger.warning("[Factory] Fallback DB query also failed")

        # 5. Build prompt with dynamic variables
        prompt_vars = {
            "agent_name": catalog.get("name"),
            "agent_description": catalog.get("description", ""),
            "nome_empresa": client_context_data.get("nome_empresa", ""),
            "collected_context": collected_context,
            "csv_datasets": [],
            "document_names": [],
            "csv_datasets_details": "",
            "filled_fields": len(collected_context),
            "total_fields": agent_config_dict.get("max_turns", 20),
            "uploaded_file_count": len(uploaded_file_ids),
            "google_connected": google_email is not None,
            "knowledge_updated_at": "Just loaded",
            "document_count": len(uploaded_doc_ids),
        }

        try:
            loaded_prompt = await build_prompt_full(
                name=catalog.get("prompt_name"),
                variables=prompt_vars,
                context_service=context_service,
            )
            system_prompt = loaded_prompt.content
        except Exception as e:
            logger.warning(
                f"[Factory] Failed to load prompt {catalog.get('prompt_name')}: {e}"
            )
            system_prompt = f"You are {catalog.get('name')}. User context: {collected_context}"

        # 6. Build LLM
        model_spec = agent_config.model or ""
        model_name = None
        if ":" in model_spec:
            _, model_name = model_spec.split(":", 1)
        elif model_spec:
            model_name = model_spec

        llm = get_model(model_name=model_name)

        # 7. Set system_prompt on the config
        agent_config.system_prompt = system_prompt

        # 8. Inject tool scoping context into config metadata
        agent_config.metadata = agent_config.metadata or {}
        agent_config.metadata.update(
            {
                "session_id": session_id,
                "client_id": str(client_id),
                "uploaded_file_ids": [str(fid) for fid in uploaded_file_ids],
                "uploaded_document_ids": [str(did) for did in uploaded_doc_ids],
                "google_account_email": google_email,
            }
        )

        # 9. Build agent using builder
        checkpointer = _get_checkpointer()
        mcp_executor = MCPToolExecutor(mcp_url=self.mcp_url)

        builder = AgentBuilder(agent_config)
        builder.with_llm(llm)
        builder.with_checkpointer(checkpointer)
        builder.with_mcp(mcp_executor)

        graph = builder.use_default_graph().build()

        # 10. Cache and return BuiltAgent with context
        built = BuiltAgent(
            graph=graph,
            system_prompt=system_prompt,
            agent_name=agent_config.name,
            agent_role=agent_config.role,
            enabled_tools=agent_config.enabled_tools,
            client_context=client_context_data,
        )
        self._agent_cache[session_id] = built

        logger.info(
            f"[Factory] Built and cached agent for session {session_id}: "
            f"{agent_config.name}, tools={agent_config.enabled_tools}"
        )

        return built

    def clear_session_cache(self, session_id: str) -> None:
        """Clear cached agent for a session (e.g., after config change)."""
        if session_id in self._agent_cache:
            del self._agent_cache[session_id]
            logger.info(f"[Factory] Cleared cache for session {session_id}")

    def prune_cache(self, max_size: int | None = None) -> None:
        """Manually prune cache to max size using LRU."""
        max_size = max_size or get_settings().MAX_CACHED_AGENTS
        if len(self._agent_cache) > max_size:
            # Simple FIFO pruning (not strict LRU, but good enough)
            to_remove = len(self._agent_cache) - max_size
            for session_id in list(self._agent_cache.keys())[:to_remove]:
                del self._agent_cache[session_id]
            logger.info(
                f"[Factory] Pruned cache from {len(self._agent_cache) + to_remove} to {len(self._agent_cache)}"
            )


# Global factory instance
_factory: StandaloneAgentFactory | None = None


def get_factory() -> StandaloneAgentFactory:
    """Get or create factory singleton."""
    global _factory
    if _factory is None:
        _factory = StandaloneAgentFactory()
    return _factory
