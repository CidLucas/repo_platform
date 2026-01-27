"""
Support Agent service - Business logic layer.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from support_agent.core.agent import SupportAgent
from support_agent.core.config import get_settings
from vizu_context_service.context_service import ContextService

logger = logging.getLogger(__name__)


@dataclass
class SupportResult:
    """Result of a support agent interaction."""
    response: str
    model_used: str
    pending_elicitation: dict[str, Any] | None = None
    issue_category: str | None = None
    severity: str = "medium"
    escalation_needed: bool = False


class SupportService:
    """
    Service layer for the Support Agent.

    Handles:
    - Client context resolution
    - Agent instantiation
    - LLM client setup
    - Result formatting
    - Ticket creation
    """

    def __init__(self, context_service: ContextService):
        """
        Initialize the service.

        Args:
            context_service: Service for resolving client context
        """
        self.context_service = context_service
        self.settings = get_settings()
        self._llm_client = None
        self._redis_client = None

    async def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            try:
                from vizu_llm_service import get_model
                self._llm_client = get_model()
            except Exception as e:
                logger.warning(f"Could not create LLM client: {e}")
        return self._llm_client

    async def _get_redis_client(self):
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.settings.REDIS_URL)
            except Exception as e:
                logger.warning(f"Could not create Redis client: {e}")
        return self._redis_client

    async def process_message(
        self,
        client_id: UUID,
        session_id: str,
        message_text: str,
        elicitation_response: dict[str, Any] | None = None,
        ticket_context: dict[str, Any] | None = None,
    ) -> SupportResult:
        """
        Process a support message.

        Args:
            client_id: Client UUID
            session_id: Session identifier
            message_text: User message
            elicitation_response: Optional response to pending elicitation
            ticket_context: Optional existing ticket context

        Returns:
            SupportResult with response and metadata
        """
        # 1. Get client context using external_user_id from JWT
        # Note: client_id from JWT is actually external_user_id (Supabase Auth user ID)
        client_context = await self.context_service.get_client_context_by_external_user_id(
            str(client_id)
        )
        if not client_context:
            raise ValueError(f"Client not found for external_user_id: {client_id}")

        # 2. Get dependencies
        llm_client = await self._get_llm_client()
        redis_client = await self._get_redis_client()

        # 3. Create agent
        agent = SupportAgent(
            cliente_context=client_context,
            redis_client=redis_client,
            llm_client=llm_client,
            mcp_url=self.settings.MCP_SERVER_URL,
        )

        # 4. Process message
        result = await agent.process_message(
            message=message_text,
            session_id=session_id,
            elicitation_response=elicitation_response,
            ticket_context=ticket_context,
        )

        # 5. Format result
        return SupportResult(
            response=result["response"],
            model_used=result["model_used"],
            pending_elicitation=result.get("pending_elicitation"),
            issue_category=result.get("issue_category"),
            severity=result.get("severity", "medium"),
            escalation_needed=self._check_escalation_needed(result),
        )

    def _check_escalation_needed(self, result: dict[str, Any]) -> bool:
        """Check if the issue needs escalation to human agent."""
        severity = result.get("severity", "medium")
        tool_calls = result.get("tool_calls", [])

        # Escalate if high severity or escalation tool was called
        if severity == "critical":
            return True

        for tool_call in tool_calls:
            if tool_call.get("tool_name") in ["escalar_ticket", "solicitar_humano"]:
                return True

        return False

    async def create_ticket(
        self,
        client_id: UUID,
        session_id: str,
        priority: str = "medium",
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a support ticket from the conversation.

        Args:
            client_id: Client UUID
            session_id: Session identifier (to get conversation history)
            priority: Ticket priority (low, medium, high, critical)
            description: Optional ticket description

        Returns:
            Dict with ticket_id and status
        """
        # This would integrate with a ticketing system
        # For now, return a mock response
        import uuid

        ticket_id = str(uuid.uuid4())[:8].upper()

        logger.info(
            f"Created ticket {ticket_id} for session {session_id} "
            f"with priority {priority}"
        )

        return {
            "ticket_id": ticket_id,
            "status": "created",
            "priority": priority,
            "session_id": session_id,
            "message": f"Ticket #{ticket_id} created successfully",
        }
