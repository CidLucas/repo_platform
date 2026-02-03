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
    "http://tool_pool_api:8000/mcp/"  # Default for docker-compose (service name with underscore)
)

logger.info(f"Initializing MCP manager with URL: {MCP_URL}")
mcp_manager = MCPConnectionManager(url=MCP_URL)

# Track connection state
_mcp_connected = False
_mcp_connection_lock = asyncio.Lock()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds (exponential backoff: 2, 4, 8)
CONNECTION_TIMEOUT = 30  # seconds


async def ensure_mcp_connected() -> bool:
    """
    Ensure MCP is connected, with lazy initialization and retry logic.

    Uses exponential backoff for retries (2s, 4s, 8s).
    Thread-safe via asyncio.Lock.

    Returns:
        True if connected, False otherwise
    """
    global _mcp_connected

    # Fast path: already connected
    if _mcp_connected:
        return True

    # Acquire lock to prevent concurrent connection attempts
    async with _mcp_connection_lock:
        # Double-check after acquiring lock
        if _mcp_connected:
            return True

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(
                    f"Connecting to MCP at {MCP_URL} (attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                await asyncio.wait_for(mcp_manager.connect(), timeout=CONNECTION_TIMEOUT)
                logger.info(f"MCP connected! Tools: {[t.name for t in mcp_manager.tools]}")
                _mcp_connected = True
                return True
            except TimeoutError:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(
                        f"Timeout connecting to MCP ({CONNECTION_TIMEOUT}s). "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"MCP connection timed out after {MAX_RETRIES} attempts - "
                        "continuing without tools"
                    )
                    return False
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(f"Failed to connect to MCP: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"MCP connection failed after {MAX_RETRIES} attempts: {e} - "
                        "continuing without tools"
                    )
                    return False

        return False

