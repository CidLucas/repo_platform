import asyncio

from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, StateGraph

from .config import get_settings
from .nodes import (
    await_elicitation_node,
    execute_tools_node,
    should_continue,
    supervisor_node,
)

# Importação relativa para garantir acesso aos módulos irmãos
from .state import AgentState


class _CheckpointerAdapter:
    """Adapter to provide the async methods LangGraph expects.

    It wraps the saver returned by the library (which may be sync-only
    or provide different method names) and exposes `aget_tuple` and
    `get_next_version` used by the runtime.
    """

    def __init__(self, inner):
        self._inner = inner

    def get_next_version(self, *args, **kwargs):
        if hasattr(self._inner, "get_next_version"):
            return self._inner.get_next_version(*args, **kwargs)
        # Fallback: no versioning available
        return None

    async def aget_tuple(self, checkpoint_config):
        # Prefer a concrete sync `get_tuple` implementation if available
        # because some implementations expose a stub async method that
        # simply raises NotImplementedError (see langgraph/checkpoint/base).
        if hasattr(self._inner, "get_tuple"):
            return await asyncio.to_thread(self._inner.get_tuple, checkpoint_config)

        # Next, try an async implementation but guard against stubs that
        # raise NotImplementedError.
        if hasattr(self._inner, "aget_tuple"):
            try:
                return await self._inner.aget_tuple(checkpoint_config)
            except NotImplementedError:
                # Fall through to empty tuple fallback
                pass

        # Last resort: return an empty tuple (no checkpoint saved)
        return (None, None)

    async def aput_writes(self, *args, **kwargs):
        # Prefer concrete sync `put_writes` when available to avoid
        # hitting async stub implementations that raise NotImplementedError.
        if hasattr(self._inner, "put_writes"):
            return await asyncio.to_thread(self._inner.put_writes, *args, **kwargs)

        if hasattr(self._inner, "aput_writes"):
            try:
                return await self._inner.aput_writes(*args, **kwargs)
            except NotImplementedError:
                pass

        # No-op fallback
        return None

    async def aput_tuple(self, *args, **kwargs):
        # Prefer concrete sync `put_tuple` when present
        if hasattr(self._inner, "put_tuple"):
            return await asyncio.to_thread(self._inner.put_tuple, *args, **kwargs)

        if hasattr(self._inner, "aput_tuple"):
            try:
                return await self._inner.aput_tuple(*args, **kwargs)
            except NotImplementedError:
                pass

        return None

    async def aput(self, *args, **kwargs):
        """Generic aput used by langgraph BaseCheckpointSaver.

        Prefer concrete sync `put` when available, otherwise try async
        `aput` and guard against NotImplementedError from stubs.
        """
        if hasattr(self._inner, "put"):
            return await asyncio.to_thread(self._inner.put, *args, **kwargs)

        if hasattr(self._inner, "aput"):
            try:
                return await self._inner.aput(*args, **kwargs)
            except NotImplementedError:
                pass

        # Fallback: try to route to more specific helpers
        if hasattr(self._inner, "put_tuple"):
            return await asyncio.to_thread(self._inner.put_tuple, *args, **kwargs)

        return None

    def __getattr__(self, name):
        # Proxy attributes to the inner object. If an async-prefixed method is
        # requested (e.g. `aget_*`) and only a sync version exists, return an
        # async wrapper that runs the sync call in a thread.
        if hasattr(self._inner, name):
            return getattr(self._inner, name)

        if name.startswith("a"):
            sync_name = name[1:]
            if hasattr(self._inner, sync_name):

                def _make_async(sync_func):
                    async def _wrapped(*args, **kwargs):
                        return await asyncio.to_thread(sync_func, *args, **kwargs)

                    return _wrapped

                return _make_async(getattr(self._inner, sync_name))

        raise AttributeError(name)


def create_agent_graph() -> StateGraph:
    """
    Cria e compila o grafo do agente LangGraph com persistência no Redis.

    PHASE 3: Elicitation Support
    - Adiciona nó await_elicitation para pausar e aguardar input do usuário
    """
    # 1. Configura conexão com Redis para memória (Checkpointer)
    settings = get_settings()

    # CORREÇÃO: Usamos o método de fábrica .from_conn_string()
    # Isso gerencia a criação do cliente e a conexão corretamente.
    checkpointer = RedisSaver.from_conn_string(settings.REDIS_URL)

    # Some versions of the RedisSaver factory return a contextmanager
    # (a generator-based context). In that case the compiled graph expects a
    # concrete checkpointer instance with methods like `get_next_version`.
    # Unwrap context-managers returned by the factory so we pass the actual
    # saver object to `compile`. We call __enter__() directly because the
    # application is long-lived; the underlying library should manage
    # connection lifecycle, but if needed we could hook shutdown cleanup.
    if hasattr(checkpointer, "__enter__") and not hasattr(
        checkpointer, "get_next_version"
    ):
        try:
            checkpointer = checkpointer.__enter__()
        except Exception:
            # If unwrapping fails, leave the original object and let the
            # compile step raise a meaningful error.
            pass

    # Call setup() to create the required Redis indexes (checkpoint_writes, etc.)
    # This is needed for newer versions of langgraph-checkpoint-redis
    if hasattr(checkpointer, "setup"):
        try:
            checkpointer.setup()
        except Exception:
            # Ignore errors if setup fails (indexes may already exist)
            pass

    # 2. Inicializa o Grafo de Estado
    workflow = StateGraph(AgentState)

    # 3. Adiciona os Nós (Nodes)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("await_elicitation", await_elicitation_node)  # PHASE 3

    # 4. Define o Ponto de Entrada (Entry Point)
    workflow.set_entry_point("supervisor")

    # 5. Define as Arestas Condicionais (Conditional Edges)
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "await_elicitation": "await_elicitation",  # PHASE 3
            "__end__": END,
        },
    )

    # PHASE 3: Conditional edges from execute_tools
    # - If elicitation pending -> await_elicitation (pause)
    # - Otherwise -> supervisor (continue loop)
    def after_tools_continue(state: AgentState):
        if state.get("pending_elicitation"):
            return "await_elicitation"
        return "supervisor"

    workflow.add_conditional_edges(
        "execute_tools",
        after_tools_continue,
        {
            "await_elicitation": "await_elicitation",
            "supervisor": "supervisor",
        },
    )

    # PHASE 3: await_elicitation node ends the graph
    # User will respond via new /chat request
    workflow.add_edge("await_elicitation", END)

    # Wrap in an adapter to ensure the object implements the async
    # methods LangGraph expects (e.g. `aget_tuple`). This keeps the
    # code resilient across different langgraph/checkpoint versions.
    agent_graph = workflow.compile(checkpointer=_CheckpointerAdapter(checkpointer))

    return agent_graph
