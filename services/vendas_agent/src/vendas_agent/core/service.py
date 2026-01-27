"""
Vendas Agent service - Business logic layer.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from vendas_agent.core.agent import VendasAgent
from vendas_agent.core.config import get_settings
from vizu_agent_framework import MCPConnectionManager
from vizu_context_service.context_service import ContextService
from vizu_models import VizuClientContext

logger = logging.getLogger(__name__)

# Shared MCP connection manager for this service
_mcp_manager: MCPConnectionManager | None = None


async def get_mcp_manager() -> MCPConnectionManager:
    """Get or create the MCP connection manager."""
    global _mcp_manager

    if _mcp_manager is None:
        settings = get_settings()
        _mcp_manager = MCPConnectionManager(url=settings.MCP_SERVER_URL)
        await _mcp_manager.connect()
        logger.info(f"MCP Manager initialized with {len(_mcp_manager.tools)} tools")

    return _mcp_manager


@dataclass
class VendasResult:
    """Result of a sales agent interaction."""
    response: str
    model_used: str
    pending_elicitation: dict[str, Any] | None = None
    suggested_products: list | None = None
    discount_available: bool = False
    tools_called: list | None = None


class VendasService:
    """
    Service layer for the Vendas Agent.

    Handles:
    - Client context resolution
    - Agent instantiation
    - MCP client setup
    - Result formatting
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

    async def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            try:
                from vizu_llm_service import get_model
                self._llm_client = get_model()
            except Exception as e:
                logger.warning(f"Could not create LLM client: {e}")
        return self._llm_client

    async def process_message(
        self,
        client_id: UUID,
        session_id: str,
        message_text: str,
        elicitation_response: dict[str, Any] | None = None,
    ) -> VendasResult:
        """
        Process a sales message.

        Args:
            client_id: Client UUID
            session_id: Session identifier
            message_text: User message
            elicitation_response: Optional response to pending elicitation

        Returns:
            VendasResult with response and metadata
        """
        # 1. Get client context using external_user_id from JWT
        # Note: client_id from JWT is actually external_user_id (Supabase Auth user ID)
        client_context = await self.context_service.get_client_context_by_external_user_id(
            str(client_id)
        )
        if not client_context:
            raise ValueError(f"Client not found for external_user_id: {client_id}")

        # 2. Get MCP manager
        mcp_manager = await get_mcp_manager()

        # 3. Get LLM client
        llm_client = await self._get_llm_client()

        # 4. Create agent
        agent = VendasAgent(
            cliente_context=client_context,
            mcp_manager=mcp_manager,
            llm_client=llm_client,
        )

        # 5. Process message
        result = await agent.process_message(
            message=message_text,
            session_id=session_id,
            elicitation_response=elicitation_response,
        )

        # 6. Format result
        return VendasResult(
            response=result["response"],
            model_used=result["model_used"],
            pending_elicitation=result.get("pending_elicitation"),
            suggested_products=self._extract_suggested_products(result),
            discount_available=self._check_discount_availability(client_context),
            tools_called=result.get("tool_calls"),
        )

    def _extract_suggested_products(self, result: dict[str, Any]) -> list | None:
        """Extract suggested products from tool results."""
        tool_calls = result.get("tool_calls", [])
        for tool_call in tool_calls:
            if tool_call.get("tool_name") == "buscar_produtos":
                return tool_call.get("result", {}).get("products", [])
        return None

    def _check_discount_availability(self, context: VizuClientContext) -> bool:
        """Check if client has discount tools enabled."""
        enabled_tools = context.get_enabled_tools_list() if hasattr(
            context, 'get_enabled_tools_list'
        ) else []
        return "aplicar_desconto" in enabled_tools or "calcular_desconto" in enabled_tools
