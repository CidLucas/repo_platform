"""
Service layer for agent_api.

ChatService — supervisor-mode sync + streaming chat.
AgentService — standalone agent streaming chat.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from blu_context_service import ContextService
from blu_llm_service import MODEL_MAPPINGS, LLMProvider, ModelTier, get_llm_settings
from blu_prompt_management import build_prompt
from blu_prompt_management.variables import VariableExtractor
from langchain_core.messages import AIMessage, HumanMessage

from agent_api.config import get_settings
from agent_api.core.factory import (
    BuiltAgent,
    get_context_service,
    get_factory,
    get_mcp_manager,
)

logger = logging.getLogger(__name__)

# Fire-and-forget task registry (prevents GC of background tasks)
_background_tasks: set = set()


def _render_company_profile(company_profile: dict | None) -> str:
    """Render company_profile JSONB dict to a markdown string for prompt injection."""
    if not company_profile or not isinstance(company_profile, dict):
        return ""
    lines = []
    for key, value in company_profile.items():
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {value}")
    return "\n".join(lines)


async def _build_frontdesk_prompt(
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Assemble variables from client_ctx and call build_prompt for agents/frontdesk."""
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get("frontdesk")
    prompt_name = cfg.prompt_name if cfg else "agents/frontdesk"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""

    # SQL schema: use per-client table configs; fall back to static analytics_v2 schema.
    sql_schema_context = VariableExtractor.render_sql_schema(
        getattr(client_ctx, "data_schema", None)
    )
    if not sql_schema_context:
        try:
            sql_schema_context = await build_prompt(
                "fragment/sql-schema", {}, context_service=context_service
            )
        except Exception:
            sql_schema_context = ""

    company_profile = _render_company_profile(
        getattr(client_ctx, "company_profile", None)
    )

    variables: dict = {
        "nome_empresa": nome_empresa,
        "sql_schema_context": sql_schema_context,
        "company_profile": company_profile,
    }

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        return (
            f"You are the Frontdesk assistant for {nome_empresa}. "
            "Answer in the user's language. Use available tools when appropriate."
        )


async def _build_synthesis_prompt(
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Assemble the Synthesis Agent system prompt with full business snapshot."""
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get("synthesis")
    prompt_name = cfg.prompt_name if cfg else "agents/synthesis"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
    client_id_str: str = str(getattr(client_ctx, "id", ""))

    # Fetch the full dimension_state snapshot to inject into the synthesis prompt
    snapshot = ""
    try:
        snapshot = await context_service.get_business_memory_snapshot(
            client_id_str, max_chars=8000
        )
    except Exception as exc:
        logger.warning("[synthesis] get_business_memory_snapshot failed: %s", exc)

    variables: dict = {
        "nome_empresa": nome_empresa,
        "business_snapshot": snapshot,
    }

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        snapshot_block = f"\n\n## Estado do Negócio\n{snapshot}" if snapshot else ""
        return (
            f"Você é o Agente de Síntese do {nome_empresa}. "
            "Sua função é cruzar informações de múltiplas dimensões do negócio "
            "(financeiro, compras, clientes, agenda) para gerar insights estratégicos. "
            "Responda em português, seja direto e baseie-se nos dados disponíveis."
            + snapshot_block
        )


async def _build_platform_prompt(
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Assemble the Platform Agent system prompt."""
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get("platform")
    prompt_name = cfg.prompt_name if cfg else "agents/platform"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""

    variables: dict = {"nome_empresa": nome_empresa}

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        return (
            f"Você é o Agente de Plataforma do {nome_empresa}. "
            "Sua função é executar configurações operacionais: ativar rotinas, "
            "definir metas e registrar dados estruturados. "
            "Use as ferramentas disponíveis. Confirme cada ação realizada. "
            "Responda em português."
        )


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# Cross-dimensional keywords that signal the Synthesis Agent should handle the request.
_SYNTHESIS_KEYWORDS = [
    # strategic connectors (cross-domain) — NOT strategic planning (→ estrategia agent)
    "investimento", "prioridade", "priorizar",
    "tendência", "tendencia", "projeção", "projecao",
    "cenário", "cenario", "planejamento",
    # cross-domain connectors
    "puxando", "impacto", "correlação", "correlacao", "causa",
    "influencia", "influência", "comparado", "versus",
    "ao mesmo tempo", "combinando", "cruzando",
]

# Dimension terms — if 2+ appear in the same message → synthesis
_DIMENSION_TERMS = [
    ["financeiro", "caixa", "receita", "faturamento", "custo", "despesa", "fluxo"],
    ["estoque", "compras", "fornecedor", "pedido", "sku", "produto", "cobertura"],
    ["cliente", "clientes", "churn", "nps", "pipeline", "lead", "inadimplente"],
    ["agenda", "prazo", "reunião", "reuniao", "entrega", "cronograma", "monday"],
]

# Imperative verbs and operational phrases that signal the Platform Agent.
_PLATFORM_KEYWORDS = [
    # creation / activation
    "cria uma rotina", "criar rotina", "ativa a rotina", "ativar rotina",
    "ativa o monitor", "ativar monitor", "monitor de estoque", "monitor de ",
    "adiciona ", "adicionar ", "cadastra ", "cadastrar ",
    "registra ", "registrar ",
    # goal setting
    "define uma meta", "definir meta", "quero atingir", "meta de ",
    "meta:", "objetivo de ", "quero chegar",
    # configuration
    "configura ", "configurar ", "agenda uma rotina", "agendar rotina",
    "desativa ", "desativar ", "pausa ", "pausar ",
]


def detect_platform_intent(message: str) -> bool:
    """Return True if the message is an operational/configuration command.

    Platform Agent handles imperative requests to CREATE or CONFIGURE
    things (routines, goals, data entries). Checked BEFORE synthesis
    intent so explicit creation commands don't get routed to synthesis.
    """
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in _PLATFORM_KEYWORDS)


def detect_synthesis_intent(message: str) -> bool:
    """Return True if the message warrants the Synthesis Agent.

    Triggers when:
    - A strategic keyword is present, OR
    - Terms from 2+ distinct business dimensions are mentioned.
    """
    msg_lower = message.lower()

    # Strategic keyword match
    for kw in _SYNTHESIS_KEYWORDS:
        if kw in msg_lower:
            return True

    # Count how many dimensions are referenced
    dims_hit = sum(
        1 for dim_terms in _DIMENSION_TERMS
        if any(t in msg_lower for t in dim_terms)
    )
    return dims_hit >= 2


# ---------------------------------------------------------------------------
# Specialist routing — domain-specific agents
# ---------------------------------------------------------------------------

_SPECIALIST_ROUTING: list[tuple[str, list[str]]] = [
    # (slug, keyword_triggers) — checked in order, first match wins
    # Supplier Agent
    ("supplier-agent", [
        "cotação", "cotacao", "fornecedor", "fornecedores",
        "rfq", "whatsapp fornecedor", "pedido de compra",
        "preço do fornecedor", "preco do fornecedor",
        "enviar para fornecedor", "contatar fornecedor",
    ]),
    # Scheduler Agent
    ("scheduler-agent", [
        "agenda para", "agenda uma", "agendar", "marcar reunião", "marcar reuniao",
        "verificar disponibilidade", "quando posso", "conflito de agenda",
        "prazo", "cronograma", "horário livre", "horario livre",
    ]),
    # Fiscal Agent
    ("fiscal-agent", [
        "nota fiscal", "nf-e", "nfse", "nfs-e", "emitir nota",
        "emissão de nf", "emissao de nf", "sefaz",
        "danfe", "xml fiscal", "regime tributário", "regime tributario",
    ]),
    # DocWriter
    ("doc-writer", [
        "escreve um documento", "escrever documento",
        "cria um relatório", "criar relatorio", "criar relatório",
        "elabora um", "elaborar um",
        "redige ", "redigir ", "draft de ",
        "sop de ", "procedimento para ",
        "ata da reunião", "ata da reuniao",
        "proposta comercial",
    ]),
    # CRM Specialist (deep analytics)
    ("crm", [
        "ltv", "lifetime value", "coorte", "cohort",
        "churn", "churn rate", "taxa de churn", "risco de churn", "nps detalhado",
        "segmento de clientes", "segmentacao", "segmentação de clientes",
        "clientes vip", "clientes em risco",
    ]),
    # Strategic Planner
    ("estrategia", [
        "planejamento estratégico", "planejamento estrategico",
        "plano mensal", "plano trimestral", "plano anual",
        "brief estratégico", "brief estrategico",
        "oportunidade de crescimento", "onde crescer",
        "foco estratégico", "foco estrategico",
    ]),
]


def detect_specialist_intent(message: str) -> str | None:
    """Return the specialist agent slug if the message matches a specialist domain.

    Returns None if no specialist matches (falls through to frontdesk).
    Checked AFTER platform and synthesis routing.
    """
    msg_lower = message.lower()
    for slug, keywords in _SPECIALIST_ROUTING:
        if any(kw in msg_lower for kw in keywords):
            return slug
    return None


async def _build_specialist_prompt(
    slug: str,
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Build system prompt for any specialist agent.

    Specialists that need business_snapshot (crm, estrategia) get it injected.
    Others (supplier, scheduler, doc-writer, fiscal) get a lighter prompt.
    """
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get(slug)
    prompt_name = cfg.prompt_name if cfg else f"agents/{slug}"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
    client_id_str: str = str(getattr(client_ctx, "id", ""))

    needs_snapshot = slug in ("crm", "estrategia", "data-analyst")
    snapshot = ""
    if needs_snapshot:
        try:
            snapshot = await context_service.get_business_memory_snapshot(
                client_id_str, max_chars=6000
            )
        except Exception as exc:
            logger.warning("[specialist:%s] snapshot failed: %s", slug, exc)

    variables: dict = {"nome_empresa": nome_empresa, "business_snapshot": snapshot}

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        return (
            f"Você é um especialista do {nome_empresa}. "
            "Responda em português com base nos dados disponíveis."
        )


# ---------------------------------------------------------------------------
# ChatResult
# ---------------------------------------------------------------------------


class ChatResult:
    def __init__(
        self,
        response: str,
        model_used: str | None = None,
        agent_slug: str = "frontdesk",
        pending_elicitation: dict | None = None,
        structured_data: dict[str, Any] | None = None,
        structured_data_list: list[dict[str, Any]] | None = None,
    ) -> None:
        self.response = response
        self.model_used = model_used
        self.agent_slug = agent_slug
        self.pending_elicitation = pending_elicitation
        self.structured_data = structured_data
        self.structured_data_list = structured_data_list


# ---------------------------------------------------------------------------
# ChatService — supervisor mode
# ---------------------------------------------------------------------------


class ChatService:
    """
    Handles supervisor-mode chat (sync + streaming).

    The supervisor graph is built once per tier and shared across all sessions.
    Per-session conversation state lives in the Redis checkpointer (thread_id="{client_id}:{session_id}").
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve_model_used(self, override: str | None) -> str:
        if override:
            return override
        llm_settings = get_llm_settings()
        provider = LLMProvider(llm_settings.LLM_PROVIDER)
        return MODEL_MAPPINGS.get(provider, {}).get(ModelTier.DEFAULT, "default")

    async def _get_client_context(self, external_user_id: str, ctx_service: ContextService):
        """Resolve client context from external_user_id (Supabase auth UUID)."""
        client_context = await ctx_service.get_client_context_by_external_user_id(external_user_id)
        if not client_context:
            raise ValueError(f"Client not found for user_id={external_user_id}")
        return client_context

    async def _connect_mcp(self, client_id: str, session_id: str, user_jwt: str | None = None) -> None:
        """Ensure MCP is connected with correct client headers."""
        mcp_mgr = get_mcp_manager()
        mcp_mgr.set_client_id(client_id)
        mcp_mgr.set_session_id(session_id)
        if user_jwt:
            mcp_mgr.set_auth_token(user_jwt)

        if not getattr(mcp_mgr, "is_connected", False):
            try:
                await asyncio.wait_for(mcp_mgr.connect(), timeout=45)
                logger.info("[ChatService] MCP connected")
            except asyncio.CancelledError:
                # anyio cancel scope leaks CancelledError as BaseException — swallow it
                # so the worker survives; mcp_client will reconnect on next tool call.
                logger.warning("[ChatService] MCP connect cancelled (scope leak) — continuing without MCP")
            except Exception as exc:
                logger.warning("[ChatService] MCP connect failed (will retry on tool call): %s", exc)

    def _build_langfuse_config(self, session_id: str, client_id: str, tags: list[str]) -> dict:
        try:
            from agent_api.core.observability import get_langfuse_config
            return get_langfuse_config(session_id=session_id, client_id=client_id, tags=tags)
        except Exception:
            return {"configurable": {"thread_id": f"{client_id}:{session_id}"}}

    async def process_message(
        self,
        session_id: str,
        message: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        elicitation_response: dict[str, Any] | None = None,
        user_jwt: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> ChatResult:
        """Run frontdesk graph and return a sync ChatResult."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        client_id = str(client_ctx.id)

        logger.info("[ChatService] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(client_id=client_id, session_id=session_id, user_jwt=user_jwt)

        factory = get_factory()
        system_prompt = await _build_frontdesk_prompt(
            client_ctx=client_ctx,
            context_service=context_service,
        )

        # Route to Platform Agent for operational/configuration commands (highest priority)
        is_platform = detect_platform_intent(message)
        _selected_agent = "frontdesk"
        if is_platform:
            try:
                system_prompt = await _build_platform_prompt(
                    client_ctx=client_ctx,
                    context_service=context_service,
                )
                _selected_agent = "platform"
                logger.info("[ChatService] Routing to PlatformAgent for session=%s", session_id)
            except Exception as exc:
                logger.warning("[ChatService] PlatformAgent prompt failed, falling back: %s", exc)

        # Route to Synthesis Agent for cross-dimensional or strategic requests
        is_synthesis = (not is_platform) and detect_synthesis_intent(message)
        if is_synthesis:
            try:
                system_prompt = await _build_synthesis_prompt(
                    client_ctx=client_ctx,
                    context_service=context_service,
                )
                _selected_agent = "synthesis"
                logger.info("[ChatService] Routing to SynthesisAgent for session=%s", session_id)
            except Exception as exc:
                logger.warning("[ChatService] SynthesisAgent prompt failed, falling back: %s", exc)

        # Specialist routing — domain-specific agents
        if not is_platform and not is_synthesis:
            specialist_slug = detect_specialist_intent(message)
            if specialist_slug:
                try:
                    system_prompt = await _build_specialist_prompt(
                        slug=specialist_slug,
                        client_ctx=client_ctx,
                        context_service=context_service,
                    )
                    _selected_agent = specialist_slug
                    logger.info(
                        "[ChatService] Routing to specialist=%s for session=%s",
                        specialist_slug, session_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "[ChatService] specialist=%s prompt failed, falling back: %s",
                        specialist_slug, exc,
                    )

        # Build initial state
        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            client_id=client_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            system_prompt=system_prompt,
            pending_elicitation=None,
            elicitation_response=elicitation_response,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
        )

        graph = factory.get_frontdesk_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["frontdesk", nome_empresa] + (extra_tags or []),
        )
        config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}"

        start = time.time()
        final_state = await graph.ainvoke(initial_state, config)
        elapsed = time.time() - start
        logger.info("[ChatService] Graph completed in %.2fs", elapsed)

        # Trim message history in state to bounded window
        window = self.settings.SESSION_HISTORY_WINDOW
        if final_state and isinstance(final_state.get("messages"), list):
            final_state["messages"] = final_state["messages"][-window:]

        last_msg = (final_state.get("messages") or [])[-1] if final_state.get("messages") else None
        response_text = str(last_msg.content) if isinstance(last_msg, AIMessage) else ""

        return ChatResult(
            response=response_text,
            model_used=self._resolve_model_used(model_override),
            agent_slug=_selected_agent,
            pending_elicitation=final_state.get("pending_elicitation"),
            structured_data=final_state.get("structured_data"),
            structured_data_list=final_state.get("structured_data_list") or None,
        )

    async def process_message_stream(
        self,
        session_id: str,
        message: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        user_jwt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream frontdesk graph response as SSE events."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        client_id = str(client_ctx.id)

        logger.info("[ChatService/stream] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(client_id=client_id, session_id=session_id, user_jwt=user_jwt)

        factory = get_factory()
        system_prompt = await _build_frontdesk_prompt(
            client_ctx=client_ctx,
            context_service=context_service,
        )

        # Route to Platform Agent for operational/configuration commands (highest priority)
        is_platform = detect_platform_intent(message)
        if is_platform:
            try:
                system_prompt = await _build_platform_prompt(
                    client_ctx=client_ctx,
                    context_service=context_service,
                )
                logger.info("[ChatService] Routing to PlatformAgent for session=%s", session_id)
            except Exception as exc:
                logger.warning("[ChatService] PlatformAgent prompt failed, falling back: %s", exc)

        # Route to Synthesis Agent for cross-dimensional or strategic requests
        is_synthesis = (not is_platform) and detect_synthesis_intent(message)
        if is_synthesis:
            try:
                system_prompt = await _build_synthesis_prompt(
                    client_ctx=client_ctx,
                    context_service=context_service,
                )
                logger.info("[ChatService] Routing to SynthesisAgent for session=%s", session_id)
            except Exception as exc:
                logger.warning("[ChatService] SynthesisAgent prompt failed, falling back: %s", exc)

        # Specialist routing — domain-specific agents
        if not is_platform and not is_synthesis:
            specialist_slug = detect_specialist_intent(message)
            if specialist_slug:
                try:
                    system_prompt = await _build_specialist_prompt(
                        slug=specialist_slug,
                        client_ctx=client_ctx,
                        context_service=context_service,
                    )
                    logger.info(
                        "[ChatService] Routing to specialist=%s for session=%s",
                        specialist_slug, session_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "[ChatService] specialist=%s prompt failed, falling back: %s",
                        specialist_slug, exc,
                    )

        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            client_id=client_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            system_prompt=system_prompt,
            pending_elicitation=None,
            elicitation_response=None,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
        )

        graph = factory.get_frontdesk_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["frontdesk", "stream", nome_empresa],
        )
        config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}"

        full_response_parts: list[str] = []
        model_used = self._resolve_model_used(model_override)
        structured_data = None

        try:
            async for event in graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                data = event.get("data", {})

                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response_parts.append(token)
                        yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield f"data: {json.dumps({'event': 'tool_start', 'data': {'name': tool_name, 'args': data.get('input', {})}})}\n\n"

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    preview = str(output)[:200] if output else ""
                    yield f"data: {json.dumps({'event': 'tool_end', 'data': {'name': tool_name, 'output': preview}})}\n\n"

                elif event_type == "on_chain_end" and event.get("name") == "LangGraph":
                    output = data.get("output") or {}
                    structured_data = output.get("structured_data")

        except Exception as exc:
            logger.exception("[ChatService/stream] Error streaming")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"
            return

        full_response = "".join(full_response_parts)
        done_data: dict[str, Any] = {"response": full_response, "model": model_used}
        if structured_data:
            done_data["structured_data"] = structured_data
        yield f"data: {json.dumps({'event': 'done', 'data': done_data}, ensure_ascii=False, default=str)}\n\n"


# ---------------------------------------------------------------------------
# AgentService — standalone agents
# ---------------------------------------------------------------------------


class AgentService:
    """
    Handles standalone agent chat (streaming).

    Each session has its own compiled graph, built from the agent_catalog entry.
    """

    async def stream_agent_response(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
        user_message: str,
    ) -> AsyncIterator[str]:
        """Stream standalone agent response as SSE dicts (without data: prefix)."""
        try:
            built: BuiltAgent = await get_factory().get_standalone_agent(
                session_id=session_id,
                client_id=client_id,
                agent_catalog_id=agent_catalog_id,
            )
        except Exception as exc:
            logger.error("[AgentService] Failed to build agent: %s", exc)
            yield {"event": "error", "message": str(exc)}
            return

        ctx_service = get_context_service()
        client_ctx = await ctx_service.get_client_context_by_external_user_id(str(client_id))
        client_id = str(client_ctx.id) if client_ctx else ""

        # Set MCP headers for this session
        mcp_mgr = get_mcp_manager()
        if client_id:
            mcp_mgr.set_client_id(client_id)
            mcp_mgr.set_session_id(session_id)

        initial_state = create_initial_state(
            session_id=session_id,
            client_id=client_id,
            messages=[HumanMessage(content=user_message)],
            system_prompt=built.system_prompt,
            agent_name=built.agent_name,
            agent_role=built.agent_role,
            client_context=built.client_context,
            metadata=built.metadata,
        )
        # Issue 4: create_initial_state reads tier from client_context, which here
        # is the session's collected_context (not BluClientContext). Inject explicitly.
        initial_state["tier"] = built.tier

        from agent_api.core.observability import get_langfuse_config
        config = get_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["standalone", built.agent_name or ""],
        )

        full_response_parts: list[str] = []

        try:
            async for event in built.graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                data = event.get("data", {})

                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response_parts.append(token)
                        yield {"event": "token", "data": token}

                elif event_type == "on_tool_start":
                    yield {"event": "tool_start", "data": {"name": event.get("name", ""), "args": data.get("input", {})}}

                elif event_type == "on_tool_end":
                    yield {"event": "tool_end", "data": {"name": event.get("name", ""), "output": str(data.get("output", ""))[:200]}}

        except Exception as exc:
            logger.exception("[AgentService] Error during stream")
            yield {"event": "error", "message": str(exc)}
            return

        yield {"event": "done", "data": "".join(full_response_parts)}


# ---------------------------------------------------------------------------
# Service singletons
# ---------------------------------------------------------------------------

_chat_service: ChatService | None = None
_agent_service: AgentService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


# ---------------------------------------------------------------------------
# Import guard for create_initial_state
# ---------------------------------------------------------------------------

from blu_agent_framework.state import create_initial_state  # noqa: E402
