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
    Supports auth headers for authenticated tool calls.
    """

    def __init__(self, url: str = "http://tool_pool_api:9000/mcp/", headers: dict[str, str] | None = None):
        """
        Initialize MCP connection manager.

        Args:
            url: MCP server URL (e.g., "http://tool_pool_api:9000/mcp/")
            headers: Optional HTTP headers (e.g., {"Authorization": "Bearer <token>"})
        """
        self.url = url
        self.headers = headers or {}
        self.tools: list[BaseTool] = []
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()
        self._connected = False

    def set_auth_token(self, token: str) -> None:
        """
        Set the Authorization header for authenticated requests.

        Header changes invalidate the MCP connection because streamablehttp_client
        captures headers at connection time (httpx copies them). A reconnect is
        needed for the new header to take effect.

        Args:
            token: JWT or Bearer token (can include "Bearer " prefix or not)
        """
        # Normalize token format
        if token:
            # Remove "Bearer " prefix if present to avoid duplication
            clean_token = token.removeprefix("Bearer ").strip()
            new_auth = f"Bearer {clean_token}"
        else:
            new_auth = None

        # Skip if header unchanged (avoids unnecessary reconnection)
        current_auth = self.headers.get("Authorization")
        if current_auth == new_auth:
            return

        # Update header and mark connection stale
        if new_auth:
            self.headers["Authorization"] = new_auth
            logger.debug(f"[MCP] Auth header updated (token: {clean_token[:20]}...)")
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]
            logger.debug("[MCP] Auth header cleared")

        self._connected = False

    def set_cliente_id(self, cliente_id: str) -> None:
        """
        Set the X-Cliente-Id header for server-side client identification.

        This is the preferred authentication method for internal service-to-service
        calls where the caller (atendente_core) has already validated the JWT and
        resolved the cliente_id.

        Header changes invalidate the MCP connection because streamablehttp_client
        captures headers at connection time (httpx copies them). A reconnect is
        needed for the new header to take effect. The "skip if same" check avoids
        unnecessary reconnections when the same client sends multiple requests.

        Args:
            cliente_id: The resolved Vizu client UUID
        """
        if not cliente_id:
            if "X-Cliente-Id" in self.headers:
                del self.headers["X-Cliente-Id"]
                self._connected = False
                logger.debug("[MCP] X-Cliente-Id header cleared, will reconnect")
            return

        # Skip if header unchanged (avoids unnecessary reconnection)
        current_cliente_id = self.headers.get("X-Cliente-Id")
        if current_cliente_id == cliente_id:
            return

        # Update header and mark connection stale
        self.headers["X-Cliente-Id"] = cliente_id
        self._connected = False
        logger.debug(f"[MCP] X-Cliente-Id header set: {cliente_id}, will reconnect")

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
                # Pass headers for authentication if configured
                logger.info(f"[MCP] Connecting with headers: {list(self.headers.keys()) if self.headers else 'None'}")
                read, write, _ = await self._exit_stack.enter_async_context(
                    streamablehttp_client(url=self.url, headers=self.headers if self.headers else None)
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

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> Any:
        """
        Call an MCP tool with automatic reconnect on ClosedResourceError.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            meta: Optional metadata (passed as _meta, not visible to LLM schema)
                  Use for auth info like cliente_id

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
                # Pass meta if the session supports it
                if meta and hasattr(self._session, "call_tool"):
                    # Try to pass meta - some MCP versions support it
                    try:
                        result = await self._session.call_tool(tool_name, arguments, meta=meta)
                    except TypeError:
                        # Fallback if meta not supported
                        result = await self._session.call_tool(tool_name, arguments)
                else:
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
