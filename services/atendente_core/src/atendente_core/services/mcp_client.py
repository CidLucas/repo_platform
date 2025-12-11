"""
MCP Client for atendente_core.

Uses the shared MCPConnectionManager from vizu_agent_framework.
"""

from vizu_agent_framework.mcp_client import MCPConnectionManager

# URL do servidor MCP (HTTP transport)
# Endpoint: /mcp (FastMCP http_app monta em /mcp por padrão)
mcp_manager = MCPConnectionManager(url="http://tool_pool_api:9000/mcp/")
