"""
Internal schemas for tool execution.

These schemas are used by atendente_core for specific tool integrations
that require custom fields beyond what's provided by MCP tools.
"""

from typing import Any

from pydantic import BaseModel, Field


class SQLQuery(BaseModel):
    """Ferramenta para executar uma consulta SQL quando o usuário perguntar sobre pedidos, estoque, etc."""

    query: str = Field(
        description="A pergunta completa do usuário em linguagem natural."
    )
    # Adicionamos o campo para as credenciais. O executor irá preenchê-lo.
    db_credentials: dict[str, Any] = Field(
        description="Credenciais para conexão com o banco de dados."
    )


class RAGQuery(BaseModel):
    """Ferramenta para responder perguntas gerais sobre o negócio, com base em documentos."""

    query: str = Field(
        description="A pergunta do usuário sobre políticas, horários, etc."
    )
