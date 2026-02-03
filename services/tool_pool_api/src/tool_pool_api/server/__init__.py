"""
MCP Server Components

Este pacote contém todos os componentes do servidor MCP:
- tools.py: Ferramentas executáveis (RAG, SQL, etc.) + prompts via prompt_module
- resources.py: Dados read-only (knowledge base, config)
- dependencies.py: Injeção de dependências (DB, Redis, Auth)
- mcp_server.py: Factory principal do servidor
"""

from .mcp_server import create_mcp_server
from .resources import register_resources
from .tools import register_tools

__all__ = [
    "create_mcp_server",
    "register_tools",
    "register_resources",
]
