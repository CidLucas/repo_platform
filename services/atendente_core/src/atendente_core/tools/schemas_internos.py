from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal


class SQLQuery(BaseModel):
    """Ferramenta para executar uma consulta SQL quando o usuário perguntar sobre pedidos, estoque, etc."""

    query: str = Field(
        description="A pergunta completa do usuário em linguagem natural."
    )
    # Adicionamos o campo para as credenciais. O executor irá preenchê-lo.
    db_credentials: Dict[str, Any] = Field(
        description="Credenciais para conexão com o banco de dados."
    )


class RAGQuery(BaseModel):
    """Ferramenta para responder perguntas gerais sobre o negócio, com base em documentos."""

    query: str = Field(
        description="A pergunta do usuário sobre políticas, horários, etc."
    )


class SchedulingTool(BaseModel):
    """
    Use esta ferramenta para criar, verificar ou cancelar agendamentos.
    Sempre extraia as informações relevantes da conversa do usuário.
    """

    intent: Literal["book", "check_availability", "cancel"] = Field(
        description="A intenção do usuário: criar um agendamento (book), verificar horários (check_availability) ou cancelar (cancel)."
    )
    service: Optional[str] = Field(
        None,
        description="O serviço que o cliente deseja agendar, ex: 'corte de cabelo'.",
    )
    date: Optional[str] = Field(
        None, description="A data para o agendamento no formato AAAA-MM-DD."
    )
    time: Optional[str] = Field(
        None, description="A hora para o agendamento no formato HH:MM."
    )
    cancellation_id: Optional[str] = Field(
        None, description="O ID do agendamento a ser cancelado."
    )
