"""
Vendas Agent API schemas.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export from vizu_models for consistency
from vizu_models import (
    ElicitationOption,
    ElicitationRequest,
    ElicitationType,
)


class ElicitationResponse(BaseModel):
    """Response to a pending elicitation."""
    elicitation_id: str = Field(..., description="ID of the elicitation being responded to")
    response: Any = Field(..., description="User's response (bool, str, or option value)")


class VendasChatRequest(BaseModel):
    """Request for sales chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier for conversation continuity")

    # Sales-specific fields
    customer_id: UUID | None = Field(None, description="Optional customer ID if known")
    product_category: str | None = Field(None, description="Product category filter")

    # Elicitation handling
    elicitation_response: ElicitationResponse | None = Field(
        None,
        description="Response to a pending elicitation"
    )


class VendasChatResponse(BaseModel):
    """Response from sales chat endpoint."""
    response: str = Field(..., description="Agent response text")
    session_id: str = Field(..., description="Session identifier")
    model_used: str = Field(..., description="LLM model used for generation")

    # Sales-specific fields
    suggested_products: list[str] | None = Field(
        None,
        description="List of suggested product names/IDs"
    )
    discount_available: bool = Field(
        False,
        description="Whether discount tools are available for this client"
    )

    # Elicitation pending
    elicitation_pending: ElicitationRequest | None = Field(
        None,
        description="Pending elicitation requiring user response"
    )

    # Tool calls (for debugging/tracing)
    tools_called: list[dict[str, Any]] | None = Field(
        None,
        description="List of tools that were called during processing"
    )


class ToolInfo(BaseModel):
    """Information about an available tool."""
    name: str = Field(..., description="Tool name")
    description: str | None = Field(None, description="Tool description")
    enabled: bool = Field(True, description="Whether enabled for this client")


class VendasContextResponse(BaseModel):
    """Client context for sales agent."""
    nome_empresa: str = Field(..., description="Company name")
    tier: str = Field("BASIC", description="Client tier")
    available_tools: list[ToolInfo] = Field(
        default_factory=list,
        description="List of available tools"
    )
    has_discount_tools: bool = Field(False, description="Whether discount tools are enabled")
    has_product_search: bool = Field(False, description="Whether product search is enabled")
