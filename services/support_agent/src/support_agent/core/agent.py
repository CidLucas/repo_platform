"""
Support Agent - Technical support agent using vizu_agent_framework.

This is the CORE of the agent - only ~70 lines thanks to the shared framework!
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from langgraph.graph.graph import CompiledGraph

from vizu_agent_framework import AgentBuilder, AgentConfig, SUPPORT_CONFIG
from vizu_tool_registry import ToolRegistry
from vizu_models import VizuClientContext

logger = logging.getLogger(__name__)


class SupportAgent:
    """
    Technical support agent for issue classification and resolution.

    Uses AgentBuilder from vizu_agent_framework for 95% code reuse.

    Differences from other agents:
    - elicitation_strategy: "issue_classification" (specialized for tech support)
    - max_turns: 25 (longer for complex technical issues)
    - role: "Technical Support Specialist"
    """

    def __init__(
        self,
        cliente_context: VizuClientContext,
        redis_client: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        mcp_url: Optional[str] = None,
    ):
        """
        Initialize the support agent.

        Args:
            cliente_context: Client context with enabled_tools and tier
            redis_client: Optional Redis client for checkpointing
            llm_client: Optional LLM client for response generation
            mcp_url: Optional MCP server URL override
        """
        self.cliente_context = cliente_context

        # Get available tools from registry based on client's enabled_tools
        enabled_tools = cliente_context.get_enabled_tools_list() if hasattr(
            cliente_context, 'get_enabled_tools_list'
        ) else []

        tier = getattr(cliente_context, 'tier', 'BASIC')

        available_tools = ToolRegistry.get_available_tools(
            enabled_tools=enabled_tools,
            tier=tier,
        )

        # Build support-specific configuration
        config = AgentConfig(
            name="support_agent",
            role="Technical Support Specialist",
            elicitation_strategy="issue_classification",
            enabled_tools=[t.name for t in available_tools],
            max_turns=25,  # Longer for complex technical issues
            use_langfuse=True,
            mcp_url=mcp_url or "http://tool_pool_api:8000/mcp/v1",
            metadata={
                "cliente_id": str(cliente_context.id) if hasattr(cliente_context, 'id') else "",
                "nome_empresa": getattr(cliente_context, 'nome_empresa', ''),
                "tier": tier,
            }
        )

        # Build the agent using the framework
        builder = AgentBuilder(config)

        if llm_client:
            builder.with_llm(llm_client)

        if redis_client:
            from vizu_agent_framework import RedisCheckpointer
            builder.with_checkpointer(RedisCheckpointer(redis_client))

        # Use default graph structure
        builder.use_default_graph()

        self.agent: CompiledGraph = builder.build()
        self.config = config

        logger.info(
            f"SupportAgent initialized for {getattr(cliente_context, 'nome_empresa', 'unknown')} "
            f"with {len(available_tools)} tools"
        )

    async def process_message(
        self,
        message: str,
        session_id: str,
        elicitation_response: Optional[Dict[str, Any]] = None,
        ticket_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message.

        Args:
            message: User message text
            session_id: Session identifier for conversation continuity
            elicitation_response: Optional response to a pending elicitation
            ticket_context: Optional existing ticket context for continuity

        Returns:
            Dict with response, model_used, issue_category, and optional pending_elicitation
        """
        from langchain_core.messages import HumanMessage

        # Build initial state
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "cliente_id": str(self.cliente_context.id) if hasattr(self.cliente_context, 'id') else "",
            "enabled_tools": self.config.enabled_tools,
            "elicitation_response": elicitation_response,
            "ticket_context": ticket_context,
        }

        # Invoke the agent
        result = await self.agent.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
        )

        # Extract response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        response_text = getattr(last_message, "content", str(last_message)) if last_message else ""

        return {
            "response": response_text,
            "model_used": self.config.model,
            "pending_elicitation": result.get("pending_elicitation"),
            "tool_calls": result.get("tool_results", []),
            "issue_category": self._extract_issue_category(result),
            "severity": self._extract_severity(result),
        }

    def _extract_issue_category(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract issue category from classification results."""
        # Could be set by classification elicitation or tool
        return result.get("issue_category")

    def _extract_severity(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract issue severity from classification."""
        return result.get("severity", "medium")
