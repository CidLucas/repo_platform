"""
Supervisor-mode chat endpoints.

POST /v1/chat         — sync JSON (inter-agent / simple clients)
POST /v1/chat/stream  — SSE streaming (human-facing UI)
GET  /v1/models       — list available LLM models
GET  /v1/context      — client context & tool availability
"""

import json
import logging

from blu_context_service import ContextService
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from agent_api.api.auth import AuthResult, get_auth_result
from agent_api.api.schemas import (
    ChatRequest,
    ChatResponse,
    ElicitationOption,
    ElicitationRequest,
    ElicitationType,
)
from agent_api.core.factory import get_context_service, get_mcp_manager
from agent_api.core.service import get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_context_service() -> ContextService:
    return get_context_service()


# ---------------------------------------------------------------------------
# POST /v1/chat  — sync
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
    authorization: str | None = Header(None, alias="Authorization"),
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(_get_context_service),
):
    """
    Sync chat endpoint for supervisor-mode agents.

    Suitable for inter-agent calls and simple HTTP clients that don't require
    streaming. Returns a complete JSON response after the agent finishes.

    Supports elicitation: include ``elicitation_response`` to resume a paused workflow.
    """
    service = get_chat_service()
    model_override = body.model or x_llm_model
    elicitation_response = None
    if body.elicitation_response:
        elicitation_response = {
            "elicitation_id": body.elicitation_response.elicitation_id,
            "response": body.elicitation_response.response,
        }

    try:
        result = await service.process_message(
            session_id=body.session_id,
            message=body.message,
            client_id=auth_result.client_id,
            context_service=context_service,
            model_override=model_override,
            elicitation_response=elicitation_response,
            user_jwt=authorization,
            extra_tags=body.tags or [],
            system_prompt_override=body.system_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception:
        logger.exception("Error in POST /chat")
        raise HTTPException(status_code=500, detail="Internal processing error")

    # Map elicitation to API schema
    pending = None
    if result.pending_elicitation:
        pe = result.pending_elicitation
        options = None
        if pe.get("options"):
            options = [
                ElicitationOption(
                    value=opt["value"],
                    label=opt["label"],
                    description=opt.get("description"),
                )
                for opt in pe["options"]
            ]
        pending = ElicitationRequest(
            elicitation_id=pe["elicitation_id"],
            type=ElicitationType(pe["type"]),
            message=pe["message"],
            options=options,
            metadata=pe.get("metadata"),
        )

    return ChatResponse(
        response=result.response,
        session_id=body.session_id,
        agent_slug=result.agent_slug,
        model_used=result.model_used,
        elicitation_pending=pending,
        structured_data=result.structured_data,
        structured_data_list=result.structured_data_list,
    )


# ---------------------------------------------------------------------------
# POST /v1/chat/stream  — SSE
# ---------------------------------------------------------------------------


@router.post("/chat/stream")
async def chat_stream_endpoint(
    body: ChatRequest,
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
    authorization: str | None = Header(None, alias="Authorization"),
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(_get_context_service),
) -> StreamingResponse:
    """
    SSE streaming chat endpoint for human-facing interactions.

    Events emitted:
    - ``{"event": "token", "data": "..."}``          — LLM token chunk
    - ``{"event": "tool_start", "data": {...}}``      — tool invocation began
    - ``{"event": "tool_end", "data": {...}}``        — tool invocation finished
    - ``{"event": "done", "data": {...}}``            — complete response + metadata
    - ``{"event": "error", "data": {...}}``           — processing error

    Elicitation is not supported in stream mode. Use ``POST /v1/chat`` instead.
    """
    service = get_chat_service()
    model_override = body.model or x_llm_model

    async def event_generator():
        try:
            async for chunk in service.process_message_stream(
                session_id=body.session_id,
                message=body.message,
                client_id=auth_result.client_id,
                context_service=context_service,
                model_override=model_override,
                user_jwt=authorization,
            ):
                yield chunk
        except Exception:
            logger.exception("Error in POST /chat/stream generator")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'Internal error'}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /v1/models
# ---------------------------------------------------------------------------


@router.get("/models")
async def list_models():
    """List available LLM models from the configured provider."""
    from blu_llm_service import MODEL_MAPPINGS, LLMProvider, ModelTier, get_llm_settings

    settings = get_llm_settings()
    current_provider = LLMProvider(settings.LLM_PROVIDER)
    provider_models = MODEL_MAPPINGS.get(current_provider, {})

    models = []
    for tier, model_name in provider_models.items():
        models.append({
            "name": model_name,
            "provider": current_provider.value,
            "tier": tier.value,
        })

    return {
        "models": models,
        "current_provider": current_provider.value,
        "default_model": provider_models.get(ModelTier.DEFAULT, "unknown"),
    }


# ---------------------------------------------------------------------------
# GET /v1/context
# ---------------------------------------------------------------------------


@router.get("/context")
async def get_client_context(
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(_get_context_service),
):
    """Return client context and available tool info."""
    from blu_models.safe_client_context import InternalClientContext

    try:
        client_ctx = await context_service.get_client_context_by_external_user_id(
            str(auth_result.client_id)
        )
    except Exception as exc:
        logger.error("Error fetching client context: %s", exc)
        raise HTTPException(status_code=500, detail="Error loading client context")

    if not client_ctx:
        raise HTTPException(status_code=404, detail="Client not found")

    internal_ctx = InternalClientContext.from_blu_client_context(client_ctx)
    safe_ctx = internal_ctx.get_safe_context()

    mcp_mgr = get_mcp_manager()
    all_tools = getattr(mcp_mgr, "tools", None) or []

    return {
        "nome_empresa": safe_ctx.nome_empresa,
        "tier": safe_ctx.tier,
        "enabled_tools": safe_ctx.enabled_tools,
        "has_rag_collection": "executar_rag_cliente" in safe_ctx.enabled_tools,
        "tool_count": len(all_tools),
    }
