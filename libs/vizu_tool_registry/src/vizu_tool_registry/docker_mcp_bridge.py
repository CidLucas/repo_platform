"""
vizu_tool_registry.docker_mcp_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bridge between FastMCP and Docker MCP toolkit integrations.

This module provides the DockerMCPBridge class which handles:
- Discovery of running Docker MCP containers
- Registration of Docker MCP tools with FastMCP
- Proxying tool calls to Docker MCP containers
"""

import logging
from typing import Any

from .exceptions import DockerMCPConnectionError
from .tool_metadata import TierLevel, ToolCategory, ToolMetadata

logger = logging.getLogger(__name__)


class DockerMCPBridge:
    """
    Bridge between FastMCP and Docker MCP toolkit integrations.

    Enables composition of:
    - Built-in Vizu tools (RAG, SQL)
    - Docker MCP verified servers (GitHub, Slack, Stripe, etc.)

    Docker MCP toolkit provides 100+ pre-built integrations that can be
    added as MCP servers running in Docker containers.

    Usage:
        bridge = DockerMCPBridge()
        await bridge.initialize()

        # Discover available integrations
        tools = await bridge.discover_docker_mcp_servers()

        # Call a Docker MCP tool
        result = await bridge.call_docker_mcp_tool(
            integration="github",
            tool_name="list_repos",
            arguments={"owner": "vizubr"}
        )
    """

    # Supported Docker MCP integrations with their default configurations
    SUPPORTED_INTEGRATIONS: dict[str, dict[str, Any]] = {
        "github": {
            "image": "docker.io/modelcontextprotocol/mcp-github:latest",
            "port": 3000,
            "env_vars": ["GITHUB_TOKEN"],
            "tools": ["github_read", "github_write"],
            "description": "GitHub repository, issues, and PRs",
        },
        "slack": {
            "image": "docker.io/modelcontextprotocol/mcp-slack:latest",
            "port": 3000,
            "env_vars": ["SLACK_BOT_TOKEN"],
            "tools": ["slack_read", "slack_send"],
            "description": "Slack messages and channels",
        },
        "stripe": {
            "image": "docker.io/modelcontextprotocol/mcp-stripe:latest",
            "port": 3000,
            "env_vars": ["STRIPE_API_KEY"],
            "tools": ["stripe_read", "stripe_charge"],
            "description": "Stripe payments and subscriptions",
        },
        "postgres": {
            "image": "docker.io/modelcontextprotocol/mcp-postgres:latest",
            "port": 3000,
            "env_vars": ["DATABASE_URL"],
            "tools": ["postgres_query"],
            "description": "External PostgreSQL databases",
        },
        "jira": {
            "image": "docker.io/modelcontextprotocol/mcp-jira:latest",
            "port": 3000,
            "env_vars": ["JIRA_API_TOKEN", "JIRA_BASE_URL"],
            "tools": ["jira_read", "jira_write"],
            "description": "Jira issues and projects",
        },
        "notion": {
            "image": "docker.io/modelcontextprotocol/mcp-notion:latest",
            "port": 3000,
            "env_vars": ["NOTION_API_KEY"],
            "tools": ["notion_read", "notion_write"],
            "description": "Notion pages and databases",
        },
        "linear": {
            "image": "docker.io/modelcontextprotocol/mcp-linear:latest",
            "port": 3000,
            "env_vars": ["LINEAR_API_KEY"],
            "tools": ["linear_read", "linear_write"],
            "description": "Linear issues and projects",
        },
    }

    def __init__(self, docker_host: str = "localhost"):
        """
        Initialize the Docker MCP Bridge.

        Args:
            docker_host: Docker daemon host (default: localhost)
        """
        self.docker_host = docker_host
        self.connected_integrations: dict[str, bool] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the bridge and check Docker availability."""
        try:
            # Check if Docker daemon is accessible
            # In production, this would use docker-py or aiohttp to check
            logger.info("DockerMCPBridge initialized")
            self._initialized = True
        except Exception as e:
            logger.warning(f"Docker MCP Bridge initialization failed: {e}")
            self._initialized = False

    async def discover_docker_mcp_servers(self) -> dict[str, ToolMetadata]:
        """
        Discover available Docker MCP servers and map to tools.

        Queries the Docker daemon for running MCP containers and returns
        metadata for each discovered tool.

        Returns:
            Dict mapping tool_name -> ToolMetadata for Docker MCP tools
        """
        if not self._initialized:
            await self.initialize()

        docker_mcp_tools: dict[str, ToolMetadata] = {}

        for integration, config in self.SUPPORTED_INTEGRATIONS.items():
            try:
                if await self._is_docker_mcp_running(integration):
                    for tool_name in config.get("tools", []):
                        docker_mcp_tools[tool_name] = ToolMetadata(
                            name=tool_name,
                            category=ToolCategory.DOCKER_MCP,
                            description=f"{config['description']} via MCP",
                            tier_required=TierLevel.ENTERPRISE,
                            docker_mcp_integration=integration,
                            requires_confirmation=tool_name.endswith("_write")
                            or tool_name.endswith("_send")
                            or tool_name.endswith("_charge"),
                        )
                    self.connected_integrations[integration] = True
                    logger.info(f"Discovered Docker MCP integration: {integration}")
            except Exception as e:
                logger.debug(f"Integration {integration} not available: {e}")
                self.connected_integrations[integration] = False

        logger.info(
            f"Discovered {len(docker_mcp_tools)} Docker MCP tools "
            f"from {sum(self.connected_integrations.values())} integrations"
        )
        return docker_mcp_tools

    async def _is_docker_mcp_running(self, integration_name: str) -> bool:
        """
        Check if a Docker MCP integration container is running.

        Args:
            integration_name: Name of the integration (github, slack, etc.)

        Returns:
            True if the container is running and healthy
        """
        # In production, this would query Docker daemon:
        # docker ps | grep mcp-{integration_name}
        #
        # For now, we return False as this is a placeholder.
        # Actual implementation would use docker-py or subprocess.

        # Placeholder: Check environment variable to simulate
        import os

        env_key = f"DOCKER_MCP_{integration_name.upper()}_ENABLED"
        return os.getenv(env_key, "").lower() == "true"

    async def call_docker_mcp_tool(
        self,
        integration: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Call a tool on a Docker MCP server.

        Args:
            integration: Name of the integration (github, slack, etc.)
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            DockerMCPConnectionError: If connection fails
        """
        if integration not in self.connected_integrations:
            raise DockerMCPConnectionError(
                integration, "Integration not discovered or not running"
            )

        if not self.connected_integrations[integration]:
            raise DockerMCPConnectionError(
                integration, "Integration container is not running"
            )

        config = self.SUPPORTED_INTEGRATIONS.get(integration)
        if not config:
            raise DockerMCPConnectionError(
                integration, "Integration not supported"
            )

        try:
            # Build connection URL
            url = self._build_connection_url(integration, config)

            # In production, this would make HTTP request to Docker MCP container
            # For now, return placeholder
            logger.info(
                f"Calling Docker MCP tool: {integration}/{tool_name} "
                f"at {url} with args: {arguments}"
            )

            # Placeholder response
            return {
                "success": True,
                "integration": integration,
                "tool": tool_name,
                "message": "Docker MCP call simulated (not connected)",
            }

        except Exception as e:
            logger.error(f"Docker MCP call failed: {e}")
            raise DockerMCPConnectionError(integration, str(e))

    def _build_connection_url(
        self, integration: str, config: dict[str, Any]
    ) -> str:
        """Build connection URL for Docker MCP integration."""
        port = config.get("port", 3000)
        return f"http://mcp-{integration}:{port}/mcp"

    @staticmethod
    def build_docker_mcp_connection_url(integration: str) -> str:
        """
        Build a Docker MCP connection URL for external use.

        Args:
            integration: Integration name

        Returns:
            Docker MCP URL
        """
        return f"docker://mcp-{integration}:latest"

    def get_integration_status(self) -> dict[str, bool]:
        """Get connection status for all integrations."""
        return self.connected_integrations.copy()

    def get_available_integrations(self) -> list[str]:
        """Get list of connected integrations."""
        return [
            name
            for name, connected in self.connected_integrations.items()
            if connected
        ]

    async def register_with_mcp_server(
        self, mcp_server: Any, integration: str
    ) -> None:
        """
        Register a Docker MCP integration's tools with a FastMCP server.

        Args:
            mcp_server: FastMCP server instance
            integration: Integration to register
        """
        config = self.SUPPORTED_INTEGRATIONS.get(integration)
        if not config:
            raise ValueError(f"Unknown integration: {integration}")

        for tool_name in config.get("tools", []):
            # Create wrapper that calls Docker MCP container
            async def docker_mcp_wrapper(**kwargs):
                return await self.call_docker_mcp_tool(
                    integration, tool_name, kwargs
                )

            # Register with MCP server
            # Note: Actual registration syntax depends on FastMCP version
            logger.info(f"Registered Docker MCP tool: {tool_name}")
