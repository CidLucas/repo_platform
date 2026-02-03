"""
Support Agent API schemas.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# Re-export from vizu_models for consistency
from vizu_models import (
    ElicitationOption,
    ElicitationRequest,
    ElicitationType,
)


class TicketPriority(Enum):
    """Ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ElicitationResponse(BaseModel):
    """Response to a pending elicitation."""
    elicitation_id: str = Field(..., description="ID of the elicitation being responded to")
    response: Any = Field(..., description="User's response (bool, str, or option value)")


class SupportChatRequest(BaseModel):
    """Request for support chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier for conversation continuity")

    # Support-specific fields
    existing_ticket_id: str | None = Field(None, description="Existing ticket ID if continuing")

    # Elicitation handling
    elicitation_response: ElicitationResponse | None = Field(
        None,
        description="Response to a pending elicitation"
    )


class SupportChatResponse(BaseModel):
    """Response from support chat endpoint."""
    response: str = Field(..., description="Agent response text")
    session_id: str = Field(..., description="Session identifier")
    model_used: str = Field(..., description="LLM model used for generation")

    # Support-specific fields
    issue_category: str | None = Field(
        None,
        description="Classified issue category (e.g., 'billing', 'technical', 'account')"
    )
    severity: str = Field(
        "medium",
        description="Issue severity (low, medium, high, critical)"
    )
    escalation_needed: bool = Field(
        False,
        description="Whether the issue needs escalation to human agent"
    )

    # Elicitation pending
    elicitation_pending: ElicitationRequest | None = Field(
        None,
        description="Pending elicitation requiring user response"
    )


class CreateTicketRequest(BaseModel):
    """Request to create a support ticket."""
    session_id: str = Field(..., description="Session identifier for conversation history")
    priority: TicketPriority = Field(
        TicketPriority.MEDIUM,
        description="Ticket priority"
    )
    description: str | None = Field(None, description="Optional ticket description")


class CreateTicketResponse(BaseModel):
    """Response from ticket creation."""
    ticket_id: str = Field(..., description="Created ticket ID")
    status: str = Field(..., description="Ticket status")
    priority: str = Field(..., description="Ticket priority")
    message: str = Field(..., description="Status message")


class ToolInfo(BaseModel):
    """Information about an available tool."""
    name: str = Field(..., description="Tool name")
    description: str | None = Field(None, description="Tool description")
    enabled: bool = Field(True, description="Whether enabled for this client")


class SupportContextResponse(BaseModel):
    """Client context for support agent."""
    nome_empresa: str = Field(..., description="Company name")
    tier: str = Field("BASIC", description="Client tier")
    available_tools: list[ToolInfo] = Field(
        default_factory=list,
        description="List of available tools"
    )
    has_escalation_tools: bool = Field(False, description="Whether escalation tools are enabled")
    has_rag_search: bool = Field(False, description="Whether RAG search is enabled")
