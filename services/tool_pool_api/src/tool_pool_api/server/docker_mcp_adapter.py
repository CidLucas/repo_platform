"""
Docker MCP Adapter for Tool Pool API.

Enables discovery and registration of Docker MCP container-based tools
with the FastMCP server.

Supported Docker MCP integrations:
- GitHub (read repos, issues, PRs)
- Slack (send messages, read channels)
- Google Suite (Calendar, Docs, etc.) - via vizu_google_suite_client
- Stripe (payments)
- And more from the Docker MCP catalog
"""

import logging
import os
from typing import Any

from vizu_tool_registry import DockerMCPBridge, ToolRegistry

logger = logging.getLogger(__name__)


class DockerMCPAdapter:
    """
    Adapter for integrating Docker MCP containers with FastMCP.

    This adapter:
    1. Discovers running Docker MCP containers
    2. Registers their tools with the FastMCP server
    3. Proxies tool calls to the appropriate container
    """

    def __init__(self):
        """Initialize the Docker MCP Adapter."""
        self.bridge = DockerMCPBridge()
        self.registered_integrations: dict[str, bool] = {}
        self.enabled = os.getenv("DOCKER_MCP_ENABLED", "false").lower() == "true"
        self.integrations_config = self._parse_integrations_env()

    def _parse_integrations_env(self) -> list[str]:
        """Parse MCP_INTEGRATIONS env var to get list of enabled integrations."""
        integrations_str = os.getenv("MCP_INTEGRATIONS", "")
        if not integrations_str:
            return []
        return [i.strip() for i in integrations_str.split(",") if i.strip()]

    async def initialize(self) -> None:
        """Initialize the adapter and Docker MCP bridge."""
        if not self.enabled:
            logger.info("Docker MCP integration is disabled (DOCKER_MCP_ENABLED=false)")
            return

        await self.bridge.initialize()
        logger.info(
            f"Docker MCP Adapter initialized. "
            f"Configured integrations: {self.integrations_config}"
        )

    async def discover_and_register(self, mcp_server: Any) -> dict[str, bool]:
        """
        Discover Docker MCP servers and register their tools.

        Args:
            mcp_server: FastMCP server instance

        Returns:
            Dict mapping tool_name -> registration success
        """
        if not self.enabled:
            logger.debug("Docker MCP disabled, skipping discovery")
            return {}

        # 1. Discover available Docker MCP containers
        docker_tools = await self.bridge.discover_docker_mcp_servers()

        logger.info(f"Discovered {len(docker_tools)} Docker MCP tools")

        # 2. Register each tool with FastMCP
        for tool_name, tool_metadata in docker_tools.items():
            # Only register if integration is in config (or all if empty)
            if self.integrations_config:
                if tool_metadata.docker_mcp_integration not in self.integrations_config:
                    logger.debug(
                        f"Skipping {tool_name} - integration "
                        f"{tool_metadata.docker_mcp_integration} not in config"
                    )
                    continue

            try:
                await self._register_docker_mcp_tool(mcp_server, tool_metadata)
                self.registered_integrations[tool_name] = True
                logger.info(f"Registered Docker MCP tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to register {tool_name}: {e}")
                self.registered_integrations[tool_name] = False

        # 3. Also register with ToolRegistry for tier-based filtering
        ToolRegistry.register_docker_mcp_tools(docker_tools)

        return self.registered_integrations

    async def _register_docker_mcp_tool(
        self,
        mcp_server: Any,
        tool_metadata: Any
    ) -> None:
        """
        Register a single Docker MCP tool with FastMCP.

        Args:
            mcp_server: FastMCP server instance
            tool_metadata: ToolMetadata for the Docker MCP tool
        """
        # Create wrapper that proxies to Docker MCP container
        integration = tool_metadata.docker_mcp_integration
        tool_name = tool_metadata.name

        async def docker_mcp_wrapper(
            cliente_id: str = "",
            **kwargs
        ) -> dict[str, Any]:
            """
            Wrapper that calls the Docker MCP container.

            Args:
                cliente_id: Client ID for context (injected by MCP)
                **kwargs: Tool-specific arguments
            """
            try:
                result = await self.bridge.call_docker_mcp_tool(
                    integration=integration,
                    tool_name=tool_name,
                    arguments=kwargs,
                )
                return result
            except Exception as e:
                logger.error(f"Docker MCP tool {tool_name} failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name,
                    "integration": integration,
                }

        # Register with FastMCP
        # Note: The actual registration depends on FastMCP API
        # This is a placeholder that should work with mcp.tool() decorator
        if hasattr(mcp_server, 'tool'):
            decorated = mcp_server.tool(
                name=tool_name,
                description=tool_metadata.description or f"Docker MCP: {tool_name}",
            )(docker_mcp_wrapper)
            logger.debug(f"Registered {tool_name} with FastMCP")
        else:
            logger.warning(f"Could not register {tool_name} - mcp_server has no tool() method")

    def get_status(self) -> dict[str, Any]:
        """Get the current status of Docker MCP integrations."""
        return {
            "enabled": self.enabled,
            "configured_integrations": self.integrations_config,
            "registered_tools": self.registered_integrations,
            "bridge_status": self.bridge.get_integration_status(),
        }

    def get_available_tools(self) -> list[str]:
        """Get list of successfully registered Docker MCP tools."""
        return [
            name for name, success in self.registered_integrations.items()
            if success
        ]


# Singleton instance for use across the application
_docker_mcp_adapter: DockerMCPAdapter | None = None


def get_docker_mcp_adapter() -> DockerMCPAdapter:
    """Get or create the Docker MCP adapter singleton."""
    global _docker_mcp_adapter
    if _docker_mcp_adapter is None:
        _docker_mcp_adapter = DockerMCPAdapter()
    return _docker_mcp_adapter


async def initialize_docker_mcp(mcp_server: Any) -> dict[str, bool]:
    """
    Initialize Docker MCP integration and register tools.

    Call this during FastMCP server startup.

    Args:
        mcp_server: FastMCP server instance

    Returns:
        Dict mapping tool_name -> registration success
    """
    adapter = get_docker_mcp_adapter()
    await adapter.initialize()
    return await adapter.discover_and_register(mcp_server)
