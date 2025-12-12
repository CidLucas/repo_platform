"""
MCP Client for atendente_core.

Uses the shared MCPConnectionManager from vizu_agent_framework.
"""

import logging
import os

from vizu_agent_framework.mcp_client import MCPConnectionManager

logger = logging.getLogger(__name__)

# Get MCP URL from environment, default to local docker-compose setup
# For Cloud Run: Set to https://tool-pool-api-<PROJECT_ID>.southamerica-east1.run.app/mcp/
MCP_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://tool-pool-api:9000/mcp/"  # Default for docker-compose
)

logger.info(f"Initializing MCP manager with URL: {MCP_URL}")
mcp_manager = MCPConnectionManager(url=MCP_URL)
