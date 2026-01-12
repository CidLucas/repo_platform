"""
Vendas Agent API routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from vendas_agent.api.auth import get_auth_result
from vendas_agent.api.schemas import (
    ElicitationOption,
    ElicitationRequest,
    ElicitationType,
    ToolInfo,
    VendasChatRequest,
    VendasChatResponse,
    VendasContextResponse,
)
from vendas_agent.core.service import VendasService
from vizu_auth.core.models import AuthResult
from vizu_context_service.context_service import ContextService
from vizu_context_service.dependencies import get_context_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Dependency Injection
# =============================================================================

def get_vendas_service(
    context_service: ContextService = Depends(get_context_service),
) -> VendasService:
    """
    Factory for VendasService.
    """
    return VendasService(context_service)


# =============================================================================
# ENDPOINT 1: CHAT
# =============================================================================

@router.post("/chat", response_model=VendasChatResponse)
async def chat_endpoint(
    body: VendasChatRequest,
    auth_result: AuthResult = Depends(get_auth_result),
    service: VendasService = Depends(get_vendas_service),
):
    """
    Main chat endpoint for sales conversations.

    ## Usage

    Send a message and receive a response from the sales agent:

    ```json
    {
        "message": "Quero comprar um produto",
        "session_id": "unique-session-id"
    }
    ```

    ## Elicitation

    When the agent needs clarification (e.g., product category, budget),
    the response will include `elicitation_pending`. Respond with:

    ```json
    {
        "message": "smartphones",
        "session_id": "same-session-id",
        "elicitation_response": {
            "elicitation_id": "abc-123",
            "response": "smartphones"
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

        # Process message
        result = await service.process_message(
            client_id=auth_result.client_id,
            session_id=body.session_id,
            message_text=body.message,
            elicitation_response=elicitation_response,
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

        return VendasChatResponse(
            response=result.response,
            session_id=body.session_id,
            model_used=result.model_used,
            suggested_products=result.suggested_products,
            discount_available=result.discount_available,
            elicitation_pending=pending_elicitation,
            tools_called=result.tools_called,
        )

    except ValueError as e:
        logger.warning(f"Validation error in /chat: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        logger.error(f"Internal error in /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error.")


# =============================================================================
# ENDPOINT 2: CONTEXT
# =============================================================================

@router.get("/context", response_model=VendasContextResponse)
async def get_client_context(
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(get_context_service),
):
    """
    Returns the authenticated client's context.

    Shows which tools are enabled and sales-specific features.
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

    # Check sales-specific features
    enabled_tool_names = [t.name for t in available_tools]
    has_discount_tools = any(
        t in enabled_tool_names
        for t in ["aplicar_desconto", "calcular_desconto"]
    )
    has_product_search = "buscar_produtos" in enabled_tool_names

    return VendasContextResponse(
        nome_empresa=getattr(client_context, 'nome_empresa', 'Unknown'),
        tier=tier,
        available_tools=tool_info_list,
        has_discount_tools=has_discount_tools,
        has_product_search=has_product_search,
    )
