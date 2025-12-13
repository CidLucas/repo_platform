"""
MCP Client for atendente_core.

Uses the shared MCPConnectionManager from vizu_agent_framework.
"""

import asyncio
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

# Track if we've already tried to connect
_mcp_connection_attempted = False
_mcp_connected = False


async def ensure_mcp_connected():
    """Ensure MCP is connected, with lazy initialization on first use."""
    global _mcp_connection_attempted, _mcp_connected
    
    if _mcp_connection_attempted:
        return _mcp_connected
    
    _mcp_connection_attempted = True
    
    try:
        logger.info(f"Lazily connecting to MCP at {MCP_URL}...")
        await asyncio.wait_for(mcp_manager.connect(), timeout=10)
        logger.info(f"✅ MCP connected! Tools: {[t.name for t in mcp_manager.tools]}")
        _mcp_connected = True
        return True
    except asyncio.TimeoutError:
        logger.warning("⚠️  Timeout connecting to MCP - continuing without tools")
        return False
    except Exception as e:
        logger.warning(f"⚠️  Failed to connect to MCP: {e} - continuing without tools")
        return False

