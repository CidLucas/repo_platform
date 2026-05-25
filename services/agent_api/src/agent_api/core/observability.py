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

    IMPORTANTE: cria um CallbackHandler novo a cada chamada com trace_id,
    session_id e user_id explícitos. Isso garante que todos os steps de uma
    mesma execução (LLM calls, tool calls, chains) vão para UM ÚNICO trace no
    Langfuse — em vez de gerar uma trace fragmentada por evento.

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
    try:
        from blu_observability_bootstrap.langfuse import is_langfuse_enabled, get_langfuse_settings
        if not is_langfuse_enabled():
            raise RuntimeError("Langfuse not configured")

        from langfuse.langchain import CallbackHandler

        resolved_trace_id = trace_id or str(uuid.uuid4())

        # CallbackHandler por invocação — todos os eventos desta execução
        # (LLM start/end, tool start/end, chain start/end) ficam sob a mesma trace.
        settings = get_langfuse_settings()
        handler = CallbackHandler(
            public_key=settings["public_key"],
            secret_key=settings["secret_key"],
            host=settings["host"],
            trace_id=resolved_trace_id,
            session_id=session_id,
            user_id=client_id or None,
            tags=tags or [],
            trace_name=trace_name or session_id,
        )

        return {
            "configurable": {"thread_id": f"{client_id}:{session_id}"},
            "callbacks": [handler],
            "metadata": {
                "trace_id": resolved_trace_id,
                "client_id": client_id,
                "session_id": session_id,
                "tags": tags or [],
            },
        }
    except Exception as exc:
        logger.debug("Langfuse not available: %s", exc)
        return {"configurable": {"thread_id": f"{client_id}:{session_id}"}}
