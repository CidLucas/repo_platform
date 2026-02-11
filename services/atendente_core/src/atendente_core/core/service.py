"""
AtendenteService - Main service for processing chat messages.

Uses custom graph with Context 2.0 aware supervisor_node.
"""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from atendente_core.core.config import get_settings
from atendente_core.core.hitl_integration import HitlIntegration
from atendente_core.core.observability import get_langfuse_config
from atendente_core.core.state import AgentState, PendingElicitation
from atendente_core.services.mcp_client import ensure_mcp_connected
from vizu_context_service.context_service import ContextService
from vizu_db_connector.operations import VizuDBConnector

logger = logging.getLogger(__name__)


class ProcessMessageResult:
    """Resultado do processamento de mensagem com suporte a elicitation."""

    def __init__(
        self,
        response: str,
        model_used: str | None = None,
        pending_elicitation: PendingElicitation | None = None,
        structured_data: dict[str, Any] | None = None,
    ):
        self.response = response
        self.model_used = model_used
        self.pending_elicitation = pending_elicitation
        self.structured_data = structured_data

    @property
    def has_pending_elicitation(self) -> bool:
        return self.pending_elicitation is not None


# Background task set to keep references (prevents garbage collection)
_background_tasks: set = set()


def _create_background_task(coro):
    """Create a fire-and-forget task that won't be garbage collected."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


class AtendenteService:
    """
    Main service for the Atendente agent.

    Designed as a singleton — the graph and heavy dependencies are created
    once and reused across requests.  The per-request ContextService is
    passed into process_message() instead.
    """

    def __init__(self):
        self.settings = get_settings()
        self.db = VizuDBConnector()
        self.hitl = HitlIntegration()

        logger.info("Building agent graph with custom supervisor_node")

        # Singleton graph — avoids creating a new RedisSaver per request
        from .graph import get_agent_graph
        self.graph = get_agent_graph()

    async def _persist_message(self, conversa_id: UUID, role: str, content: str) -> None:
        """Fire-and-forget message persistence for OPT-4.

        Runs in background task, logs errors but doesn't propagate them.
        """
        try:
            await self.db.add_mensagem(conversa_id, role, content)
        except Exception:
            logger.exception(f"Background message persistence failed ({role})")

    async def process_message(
        self,
        session_id: str,
        message_text: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        elicitation_response: dict[str, Any] | None = None,
        user_jwt: str | None = None,
    ) -> ProcessMessageResult:
        """
        Recebe a mensagem crua, hidrata com o contexto do cliente e executa o agente.

        Args:
            session_id: ID da sessão
            message_text: Mensagem do usuário
            client_id: ID do cliente (autenticado via JWT)
            context_service: Per-request ContextService for DB/cache access
            model_override: Nome do modelo LLM a usar (opcional)
            elicitation_response: Resposta do usuário a uma elicitation pendente (opcional)

        Returns:
            ProcessMessageResult com resposta, modelo usado e possível elicitation pendente
        """
        # 1. Get client context using the external_user_id from JWT
        # Note: client_id from JWT is actually external_user_id (Supabase Auth user ID)
        # We need to look up the cliente by external_user_id, not by internal id
        client_context = await context_service.get_client_context_by_external_user_id(
            str(client_id)
        )

        if not client_context:
            logger.warning(f"Cliente não encontrado para external_user_id: {client_id}")
            raise ValueError("Cliente não encontrado.")

        logger.info(f"Atendendo: {client_context.nome_empresa} | Sessão: {session_id}")

        # 2. Preparação do Estado do Grafo
        # OTIMIZAÇÃO: Contextos são buscados on-demand no supervisor_node usando cliente_id
        # Isso evita trace bloat (vizu_context, safe_context, _internal_context não vão para o estado)
        initial_state = AgentState(
            messages=[HumanMessage(content=message_text)],
            tools=[],  # Será preenchido pelo nó supervisor via MCP
            model_override=model_override,  # Modelo específico para este request
            # cliente_id é usado para buscar contexto on-demand no supervisor_node
            cliente_id=client_context.id,
            # Include original user's JWT so executor can propagate to tools
            user_jwt=user_jwt,
            # PHASE 3: Elicitation fields
            pending_elicitation=None,
            elicitation_response=elicitation_response,  # Inject response if provided
            # Framework state fields (prevent premature termination)
            ended=False,
            turn_count=0,
            structured_data=None,
            # OPT-7: Cached system prompt (populated on first supervisor call)
            _cached_system_prompt=None,
        )

        # Log if we're resuming from elicitation
        if elicitation_response:
            logger.info(
                f"Resuming from elicitation: {elicitation_response.get('elicitation_id')}"
            )

        # Determina qual modelo será usado (para retornar na resposta)
        from vizu_llm_service import MODEL_MAPPINGS, LLMProvider, ModelTier, get_llm_settings

        llm_settings = get_llm_settings()
        if model_override:
            model_used = model_override
        else:
            provider = LLMProvider(llm_settings.LLM_PROVIDER)
            model_used = MODEL_MAPPINGS.get(provider, {}).get(ModelTier.DEFAULT, "default")

        # Persiste a conversa e a mensagem inicial
        # OPT-4: create_or_get_conversa must await (need conversa_id), but add_mensagem is fire-and-forget
        conversa_id = None
        try:
            # cliente_final_id pode ser desconhecido no momento; passamos None
            # client_id vem do contexto autenticado
            conversa_id = await self.db.create_or_get_conversa(
                session_id,
                cliente_final_id=None,
                client_id=str(client_context.id)
            )
            # Fire-and-forget: persist user message in background
            _create_background_task(self._persist_message(conversa_id, "user", message_text))
        except Exception:
            logger.exception("Falha ao criar/obter conversa (não bloqueante)")

        # 4. Execução do Grafo (com Memória via session_id e Observabilidade via Langfuse)
        # get_langfuse_config retorna config com callbacks do Langfuse se configurado
        config = get_langfuse_config(
            session_id=session_id,
            cliente_id=str(client_context.id),
            tags=["atendente", safe_ctx.nome_empresa],
        )

        try:
            # Ensure MCP connection is established before graph execution
            await ensure_mcp_connected()

            # OPT-3: Set context_service for supervisor_node to enable Redis-cached prompts
            from atendente_core.core.nodes import set_node_context_service
            set_node_context_service(context_service)

            # .ainvoke roda o grafo inteiro até chegar no END
            start_time = time.time()
            final_state = await self.graph.ainvoke(initial_state, config)
            # Prune final_state messages to a bounded window to avoid
            # persisting entire conversation in the state (reduces span size
            # and memory bloat). Uses same window size as the node.
            history_window = getattr(self.settings, "SESSION_HISTORY_WINDOW", 6)
            if final_state and "messages" in final_state and isinstance(final_state["messages"], list):
                final_state["messages"] = final_state["messages"][-history_window:]
            response_time = time.time() - start_time

            # 5. Extração da Resposta
            last_message = final_state["messages"][-1]

            # PHASE 3: Check for pending elicitation
            pending_elicitation = final_state.get("pending_elicitation")
            if pending_elicitation:
                logger.info(
                    f"Elicitation pending: {pending_elicitation.get('elicitation_id')}"
                )

            if isinstance(last_message, AIMessage):
                agent_response = last_message.content

                # OPT-4: Fire-and-forget persist AI response in background
                if conversa_id:
                    _create_background_task(self._persist_message(conversa_id, "ai", agent_response))

                # PHASE 6: HITL Evaluation
                # Avalia se esta interação deve ir para revisão humana
                tools_called = final_state.get("tools_called", [])
                tool_errors = final_state.get("tool_errors", [])
                confidence = final_state.get("confidence_score")  # Se disponível

                await self.hitl.evaluate_and_submit(
                    user_message=message_text,
                    agent_response=agent_response,
                    client_id=client_context.id,
                    session_id=session_id,
                    trace_id=config.get("metadata", {}).get("trace_id"),
                    tools_called=tools_called,
                    tool_errors=tool_errors,
                    confidence_score=confidence,
                    elicitation_pending=pending_elicitation is not None,
                    response_time_seconds=response_time,
                    model_used=model_used,
                )

                # Extract structured_data from state (populated by SQL tools)
                structured_data = final_state.get("structured_data")

                return ProcessMessageResult(
                    response=agent_response,
                    model_used=model_used,
                    pending_elicitation=pending_elicitation,
                    structured_data=structured_data,
                )

            return ProcessMessageResult(
                response="",
                model_used=model_used,
                pending_elicitation=pending_elicitation,
            )

        except Exception as e:
            logger.exception(
                f"Erro crítico ao processar mensagem na sessão {session_id}"
            )
            # Re-lançamos para o Router tratar e retornar 500
            raise e
