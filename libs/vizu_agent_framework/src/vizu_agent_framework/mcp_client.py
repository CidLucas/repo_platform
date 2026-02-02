"""
MCP Client Manager for agent framework.

Provides a shared MCP connection manager using StreamableHTTP transport,
compatible with tool_pool_api's FastMCP server.
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any

from anyio import BrokenResourceError, ClosedResourceError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """
    Gerencia conexão com servidor MCP via HTTP (Streamable HTTP transport).

    O transporte HTTP é mais moderno e robusto que SSE:
    - Suporta bidirecional nativo
    - Melhor handling de erros
    - Compatível com proxies/load balancers

    Inclui reconnect automático quando a sessão fecha inesperadamente.
    """

    def __init__(self, url: str = "http://tool_pool_api:9000/mcp/"):
        """
        Initialize MCP connection manager.

        Args:
            url: MCP server URL (e.g., "http://tool_pool_api:9000/mcp/")
        """
        self.url = url
        self.tools: list[BaseTool] = []
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected and self._session is not None

    async def connect(self):
        """Estabelece conexão HTTP com reconexão automática."""
        async with self._lock:
            await self._connect_inner()

    async def _connect_inner(self):
        """Internal connect (must be called under lock)."""
        backoff = 1
        max_retries = 5

        for attempt in range(max_retries):
            try:
                logger.debug(f"MCP connect attempt {attempt + 1}/{max_retries}: {self.url}")

                # Close previous stack if exists
                if self._exit_stack:
                    try:
                        await self._exit_stack.aclose()
                    except Exception:
                        pass
                self._exit_stack = AsyncExitStack()

                # Conecta via Streamable HTTP (transporte moderno)
                read, write, _ = await self._exit_stack.enter_async_context(
                    streamablehttp_client(url=self.url)
                )

                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read, write)
                )

                await self._session.initialize()

                # Carrega as ferramentas
                self.tools = await load_mcp_tools(self._session)
                self._connected = True

                logger.debug(
                    f"MCP connected, tools: {[t.name for t in self.tools]}"
                )
                return

            except Exception as e:
                logger.error(f"❌ Erro na conexão MCP (tentativa {attempt + 1}): {e}")
                if hasattr(e, "exceptions"):
                    for idx, sub_exc in enumerate(e.exceptions):
                        logger.error(f"   Sub-erro {idx+1}: {sub_exc}")

                self.tools = []
                self._session = None
                self._connected = False

                if attempt < max_retries - 1:
                    logger.debug(f"MCP reconnecting in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                else:
                    logger.error("MCP max retries reached")
                    raise

    async def disconnect(self):
        """Fecha conexão MCP."""
        async with self._lock:
            if self._exit_stack:
                logger.debug("Closing MCP connection...")
                try:
                    await self._exit_stack.aclose()
                except Exception:
                    pass
                self._exit_stack = None
            self._session = None
            self._connected = False
            self.tools = []

    async def ensure_connected(self):
        """Ensure session is connected, reconnect if needed."""
        if not self.is_connected:
            await self.connect()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call an MCP tool with automatic reconnect on ClosedResourceError.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool result

        Raises:
            Exception: If call fails after retry
        """
        await self.ensure_connected()

        for attempt in range(2):
            try:
                if self._session is None:
                    raise ClosedResourceError("Session is None")
                result = await self._session.call_tool(tool_name, arguments)
                return result
            except (ClosedResourceError, BrokenResourceError) as e:
                logger.warning(
                    f"[MCP] Connection error ao chamar '{tool_name}' (tentativa {attempt+1}/2): {e}"
                )
                if attempt == 0:
                    logger.debug("[MCP] Reconnecting and retrying...")
                    await self.disconnect()
                    await self.connect()
                else:
                    raise

    def get_tool_by_name(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_map(self) -> dict[str, BaseTool]:
        """Get a dict mapping tool names to tools."""
        return {t.name: t for t in self.tools}


# Singleton instance for shared use
# Note: Each agent should create its own instance if needed for isolation
_default_mcp_manager: MCPConnectionManager | None = None


def get_mcp_manager(url: str = "http://tool_pool_api:9000/mcp/") -> MCPConnectionManager:
    """
    Get or create the default MCP connection manager.

    Args:
        url: MCP server URL

    Returns:
        MCPConnectionManager instance
    """
    global _default_mcp_manager

    if _default_mcp_manager is None:
        _default_mcp_manager = MCPConnectionManager(url=url)

    return _default_mcp_manager


async def initialize_mcp(url: str = "http://tool_pool_api:9000/mcp/") -> MCPConnectionManager:
    """
    Initialize and connect the default MCP manager.

    Args:
        url: MCP server URL

    Returns:
        Connected MCPConnectionManager instance
    """
    manager = get_mcp_manager(url)
    await manager.connect()
    return manager
