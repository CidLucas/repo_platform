"""
AtendenteService - Main service for processing chat messages.

Phase 3: Refactored to use vizu_agent_framework for graph construction.
"""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from atendente_core.core.config import get_settings

# Legacy imports for compatibility during transition
from atendente_core.core.graph import create_agent_graph

# PHASE 6: HITL Integration
from atendente_core.core.hitl_integration import HitlIntegration
from atendente_core.core.observability import get_langfuse_config

# Local state types
from atendente_core.core.state import PendingElicitation

# Phase 3: Use the new agent framework
from vizu_agent_framework import ATENDENTE_CONFIG, AgentBuilder
from vizu_agent_framework.state import AgentState
from vizu_context_service.context_service import ContextService
from vizu_db_connector.operations import VizuDBConnector
from vizu_models.safe_client_context import InternalClientContext
from vizu_models.vizu_client_context import VizuClientContext
from atendente_core.services.mcp_client import ensure_mcp_connected

logger = logging.getLogger(__name__)


class ProcessMessageResult:
    """Resultado do processamento de mensagem com suporte a elicitation."""

    def __init__(
        self,
        response: str,
        model_used: str | None = None,
        pending_elicitation: PendingElicitation | None = None,
    ):
        self.response = response
        self.model_used = model_used
        self.pending_elicitation = pending_elicitation

    @property
    def has_pending_elicitation(self) -> bool:
        return self.pending_elicitation is not None


class AtendenteService:
    """
    Main service for the Atendente agent.

    Phase 3: Supports both legacy graph and new AgentBuilder.
    Set USE_NEW_FRAMEWORK=true in env to enable new framework.
    """

    def __init__(self, context_service: ContextService):
        self.context_service = context_service
        self.settings = get_settings()
        self.db = VizuDBConnector()
        self.hitl = HitlIntegration()

        # Phase 3: Choose which graph builder to use
        self._use_new_framework = getattr(self.settings, "USE_NEW_FRAMEWORK", False)

        if self._use_new_framework:
            logger.info("Using vizu_agent_framework (new)")
            self.graph = self._build_new_graph()
        else:
            logger.info("Using legacy graph builder")
            self.graph = create_agent_graph()

    def _build_new_graph(self):
        """Build agent graph using vizu_agent_framework."""
        return (
            AgentBuilder()
            .with_config(ATENDENTE_CONFIG)
            .with_redis_checkpointer(self.settings.REDIS_URL)
            .build()
        )

    async def process_message(
        self,
        session_id: str,
        message_text: str,
        client_id: UUID,
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
            model_override: Nome do modelo LLM a usar (opcional)
            elicitation_response: Resposta do usuário a uma elicitation pendente (opcional)

        Returns:
            ProcessMessageResult com resposta, modelo usado e possível elicitation pendente
        """
        # 1. Get client context using the external_user_id from JWT
        # Note: client_id from JWT is actually external_user_id (Supabase Auth user ID)
        # We need to look up the cliente by external_user_id, not by internal id
        client_context = await self.context_service.get_client_context_by_external_user_id(
            str(client_id)
        )

        if not client_context:
            logger.warning(f"Cliente não encontrado para external_user_id: {client_id}")
            raise ValueError("Cliente não encontrado.")

        logger.info(f"Atendendo: {client_context.nome_empresa} | Sessão: {session_id}")

        # 2. Separar contexto seguro do sensível
        # InternalClientContext mantém dados sensíveis (api_key, id) separados
        # SafeClientContext contém apenas dados seguros para a LLM
        internal_ctx = InternalClientContext.from_vizu_client_context(client_context)
        safe_ctx = internal_ctx.get_safe_context()

        # 3. Preparação do Estado do Grafo
        # O system prompt é construído dinamicamente no nó supervisor via build_dynamic_system_prompt()
        # safe_context vai para a LLM, _internal_context fica para uso interno
        initial_state = AgentState(
            messages=[HumanMessage(content=message_text)],
            safe_context=safe_ctx,
            _internal_context=internal_ctx,
            tools=[],  # Será preenchido pelo nó supervisor via MCP
            model_override=model_override,  # Modelo específico para este request
            # PHASE 5: cliente_id para buscar prompts customizados
            cliente_id=client_context.id,
            # Include original user's JWT so executor can propagate to tools
            user_jwt=user_jwt,
            # PHASE 3: Elicitation fields
            pending_elicitation=None,
            elicitation_response=elicitation_response,  # Inject response if provided
        )

        # Log if we're resuming from elicitation
        if elicitation_response:
            logger.info(
                f"Resuming from elicitation: {elicitation_response.get('elicitation_id')}"
            )

        # Determina qual modelo será usado (para retornar na resposta)
        from vizu_llm_service import get_llm_settings

        settings = get_llm_settings()
        model_used = model_override or settings.OLLAMA_CLOUD_DEFAULT_MODEL or "default"

        # Persiste a conversa e a mensagem inicial
        try:
            # cliente_final_id pode ser desconhecido no momento; passamos None
            # client_id vem do contexto autenticado
            conversa_id = await self.db.create_or_get_conversa(
                session_id,
                cliente_final_id=None,
                client_id=str(client_context.id)
            )
            # Armazena a mensagem do usuário
            await self.db.add_mensagem(conversa_id, "user", message_text)
        except Exception:
            logger.exception("Falha ao persistir conversa/mensagem (não bloqueante)")

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

                # Persiste a resposta do assistente
                try:
                    await self.db.add_mensagem(conversa_id, "ai", agent_response)
                except Exception:
                    logger.exception(
                        "Falha ao persistir mensagem do assistente (não bloqueante)"
                    )

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

                return ProcessMessageResult(
                    response=agent_response,
                    model_used=model_used,
                    pending_elicitation=pending_elicitation,
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
