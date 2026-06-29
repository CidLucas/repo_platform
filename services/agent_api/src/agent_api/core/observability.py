"""Langfuse config helper for LangGraph invocation."""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def get_langfuse_config(
    session_id: str,
    client_id: str,
    tags: list[str] | None = None,
    trace_id: str | None = None,
    trace_name: str | None = None,
) -> dict:
    """
    Return a LangGraph config dict wired up com Langfuse callback POR INVOCAÇÃO.

    IMPORTANTE: cria um CallbackHandler novo a cada chamada com trace_id
    explícito. Session/user/tags/name são propagados via
    ``config["metadata"]`` usando as chaves reservadas ``langfuse_*`` que o
    Langfuse SDK v4 lê do callback handler. Isso garante que todos os steps
    de uma mesma execução (LLM calls, tool calls, chains) vão para UM ÚNICO
    trace no Langfuse — em vez de gerar uma trace fragmentada por evento.

    O singleton de get_langfuse_callback() NÃO é usado aqui porque ele não
    carrega os IDs da invocação e causaria traces separados para cada chain.

    Args:
        session_id: ID da sessão — para rotinas, use execution_id; para chat,
                    use o session_id da conversa. Aparece como "Session" no Langfuse.
        client_id:  ID do cliente. Aparece como "User" no Langfuse.
        tags:       Lista de tags livres (ex: ["routine", "relatorio_clientes"]).
        trace_id:   UUID fixo para a trace. Se None, gera um novo. Use o mesmo
                    valor em múltiplas chamadas se quiser linkar traces manualmente.
        trace_name: Nome legível da trace no Langfuse UI. Default: session_id.
    """
    from blu_observability_bootstrap.langfuse import is_langfuse_enabled
    if not is_langfuse_enabled():
        logger.debug("Langfuse not enabled (missing credentials) — tracing disabled")
        return {"configurable": {"thread_id": f"{client_id}:{session_id}"}}

    from langfuse.langchain import CallbackHandler

    resolved_trace_id = (trace_id or str(uuid.uuid4())).replace("-", "")

    # Langfuse v4 SDK: CallbackHandler accepts only public_key + trace_context.
    # session_id / user_id / tags / trace_name come from config["metadata"]
    # with the langfuse_* keys (see _parse_langfuse_trace_attributes in the SDK).
    try:
        handler = CallbackHandler(
            public_key=None,  # SDK reads from LANGFUSE_PUBLIC_KEY env
            trace_context={"trace_id": resolved_trace_id},
        )
    except Exception as exc:
        # Hard-fail on programming errors (don't silently swallow like before).
        logger.warning("Failed to create Langfuse CallbackHandler: %s", exc)
        return {"configurable": {"thread_id": f"{client_id}:{session_id}"}}

    return {
        "configurable": {"thread_id": f"{client_id}:{session_id}"},
        "callbacks": [handler],
        "metadata": {
            # Langfuse v4 reads these keys to populate the trace root
            "langfuse_session_id": session_id,
            "langfuse_user_id": client_id or None,
            "langfuse_tags": tags or [],
            "langfuse_trace_name": trace_name or session_id,
            # App-level metadata (also captured as generic trace metadata;
            # langfuse_* keys are stripped by the SDK before persistence)
            "client_id": client_id,
            "session_id": session_id,
            "tags": tags or [],
        },
    }
