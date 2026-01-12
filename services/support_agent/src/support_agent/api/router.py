"""
Support Agent API routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from support_agent.api.auth import get_auth_result
from support_agent.api.schemas import (
    CreateTicketRequest,
    CreateTicketResponse,
    ElicitationOption,
    ElicitationRequest,
    ElicitationType,
    SupportChatRequest,
    SupportChatResponse,
    SupportContextResponse,
    ToolInfo,
)
from support_agent.core.service import SupportService
from vizu_auth.core.models import AuthResult
from vizu_context_service.context_service import ContextService
from vizu_context_service.dependencies import get_context_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Dependency Injection
# =============================================================================

def get_support_service(
    context_service: ContextService = Depends(get_context_service),
) -> SupportService:
    """
    Factory for SupportService.
    """
    return SupportService(context_service)


# =============================================================================
# ENDPOINT 1: CHAT
# =============================================================================

@router.post("/chat", response_model=SupportChatResponse)
async def chat_endpoint(
    body: SupportChatRequest,
    auth_result: AuthResult = Depends(get_auth_result),
    service: SupportService = Depends(get_support_service),
):
    """
    Main chat endpoint for technical support conversations.

    ## Usage

    Send a message and receive a response from the support agent:

    ```json
    {
        "message": "Meu sistema está dando erro",
        "session_id": "unique-session-id"
    }
    ```

    ## Issue Classification

    The agent will classify your issue by category and severity.
    If escalation is needed, `escalation_needed` will be `true`.

    ## Elicitation

    When the agent needs more information (e.g., error details, steps to reproduce),
    the response will include `elicitation_pending`. Respond with:

    ```json
    {
        "message": "O erro acontece quando clico em salvar",
        "session_id": "same-session-id",
        "elicitation_response": {
            "elicitation_id": "abc-123",
            "response": "save_button_error"
        }
    }
    ```
    """
    try:
        # Prepare elicitation response if provided
        elicitation_response = None
        if body.elicitation_response:
            elicitation_response = {
                "elicitation_id": body.elicitation_response.elicitation_id,
                "response": body.elicitation_response.response,
            }

        # Prepare ticket context if continuing existing ticket
        ticket_context = None
        if body.existing_ticket_id:
            ticket_context = {"ticket_id": body.existing_ticket_id}

        # Process message
        result = await service.process_message(
            client_id=auth_result.client_id,
            session_id=body.session_id,
            message_text=body.message,
            elicitation_response=elicitation_response,
            ticket_context=ticket_context,
        )

        # Convert pending elicitation to API schema
        pending_elicitation = None
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

            pending_elicitation = ElicitationRequest(
                elicitation_id=pe["elicitation_id"],
                type=ElicitationType(pe["type"]),
                message=pe["message"],
                options=options,
                metadata=pe.get("metadata"),
            )

        return SupportChatResponse(
            response=result.response,
            session_id=body.session_id,
            model_used=result.model_used,
            issue_category=result.issue_category,
            severity=result.severity,
            escalation_needed=result.escalation_needed,
            elicitation_pending=pending_elicitation,
        )

    except ValueError as e:
        logger.warning(f"Validation error in /chat: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        logger.error(f"Internal error in /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error.")


# =============================================================================
# ENDPOINT 2: CREATE TICKET
# =============================================================================

@router.post("/ticket", response_model=CreateTicketResponse)
async def create_ticket_endpoint(
    body: CreateTicketRequest,
    auth_result: AuthResult = Depends(get_auth_result),
    service: SupportService = Depends(get_support_service),
):
    """
    Create a support ticket from the conversation.

    Use this when the issue needs to be tracked or escalated.
    """
    try:
        result = await service.create_ticket(
            client_id=auth_result.client_id,
            session_id=body.session_id,
            priority=body.priority.value,
            description=body.description,
        )

        return CreateTicketResponse(
            ticket_id=result["ticket_id"],
            status=result["status"],
            priority=result["priority"],
            message=result["message"],
        )

    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating ticket.")


# =============================================================================
# ENDPOINT 3: CONTEXT
# =============================================================================

@router.get("/context", response_model=SupportContextResponse)
async def get_client_context(
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(get_context_service),
):
    """
    Returns the authenticated client's context.

    Shows which tools are enabled and support-specific features.
    """
    from uuid import UUID

    from vizu_tool_registry import ToolRegistry

    try:
        uuid_obj = UUID(str(auth_result.client_id))
        client_context = await context_service.get_client_context_by_id(uuid_obj)
    except Exception as e:
        logger.error(f"Error getting client context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error loading client context"
        )

    if not client_context:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get enabled tools
    enabled_tools = client_context.get_enabled_tools_list() if hasattr(
        client_context, 'get_enabled_tools_list'
    ) else []

    tier = getattr(client_context, 'tier', 'BASIC')

    # Get available tools from registry
    available_tools = ToolRegistry.get_available_tools(
        enabled_tools=enabled_tools,
        tier=tier,
    )

    # Build tool info list
    tool_info_list = [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            enabled=True,
        )
        for tool in available_tools
    ]

    # Check support-specific features
    enabled_tool_names = [t.name for t in available_tools]
    has_escalation_tools = any(
        t in enabled_tool_names
        for t in ["escalar_ticket", "solicitar_humano", "transferir_atendente"]
    )
    has_rag_search = "executar_rag_cliente" in enabled_tool_names

    return SupportContextResponse(
        nome_empresa=getattr(client_context, 'nome_empresa', 'Unknown'),
        tier=tier,
        available_tools=tool_info_list,
        has_escalation_tools=has_escalation_tools,
        has_rag_search=has_rag_search,
    )
