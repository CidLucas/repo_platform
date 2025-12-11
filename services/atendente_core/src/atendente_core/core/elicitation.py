# src/atendente_core/core/elicitation.py
"""
Módulo de Elicitation para Human-in-the-Loop.

Este módulo implementa o padrão de elicitation que permite ao agente
pausar a execução para aguardar input do usuário, salvando o estado
no Redis e retomando quando a resposta chegar.

Fluxo:
1. Tool detecta necessidade de confirmação/input
2. Tool retorna ElicitationRequired ao invés do resultado
3. LangGraph detecta e salva estado com pending_elicitation
4. API retorna resposta com elicitation_pending
5. Usuário responde via /chat com elicitation_response
6. LangGraph retoma do estado salvo e passa resposta ao tool
7. Tool completa execução

Exemplo de uso em um tool:
```python
@mcp.tool()
async def agendar_servico(data: str, horario: str, ctx: Context):
    # Checa se já temos confirmação do usuário
    if hasattr(ctx, 'elicitation_response') and ctx.elicitation_response:
        if ctx.elicitation_response.get('confirmed'):
            return await _criar_agendamento(data, horario)
        return "Agendamento cancelado pelo usuário."

    # Solicita confirmação
    raise ElicitationRequired(
        type=ElicitationType.CONFIRMATION,
        message=f"Confirmar agendamento para {data} às {horario}?",
        tool_name="agendar_servico",
        tool_args={"data": data, "horario": horario}
    )
```
"""

import uuid
import logging
from typing import Optional, List, Dict, Any

from .state import PendingElicitation

# Importa tipos compartilhados de vizu_models
from vizu_models import ElicitationType, ElicitationOption

logger = logging.getLogger(__name__)


class ElicitationRequired(Exception):
    """
    Exceção lançada quando um tool precisa de input do usuário.

    Esta exceção é capturada pelo execute_tools_node que então
    configura o estado para aguardar resposta do usuário.
    """

    def __init__(
        self,
        type: ElicitationType,
        message: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        options: Optional[List[ElicitationOption]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.elicitation_id = str(uuid.uuid4())
        self.type = type
        self.message = message
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.options = options or []
        self.metadata = metadata or {}

        super().__init__(f"Elicitation required: {message}")

    def to_pending_elicitation(self) -> PendingElicitation:
        """Converte para PendingElicitation para armazenar no state"""
        return PendingElicitation(
            elicitation_id=self.elicitation_id,
            type=self.type.value,
            message=self.message,
            options=[opt.to_dict() for opt in self.options] if self.options else None,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
            metadata=self.metadata,
        )


def create_confirmation_elicitation(
    message: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ElicitationRequired:
    """
    Helper para criar elicitation de confirmação (Sim/Não).

    Args:
        message: Mensagem a exibir (ex: "Confirmar agendamento para 15/01?")
        tool_name: Nome do tool que está solicitando
        tool_args: Argumentos originais do tool
        metadata: Dados extras para contexto

    Returns:
        ElicitationRequired exception to be raised
    """
    return ElicitationRequired(
        type=ElicitationType.CONFIRMATION,
        message=message,
        tool_name=tool_name,
        tool_args=tool_args,
        options=[
            ElicitationOption(value="yes", label="Sim"),
            ElicitationOption(value="no", label="Não"),
        ],
        metadata=metadata,
    )


def create_selection_elicitation(
    message: str,
    options: List[ElicitationOption],
    tool_name: str,
    tool_args: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ElicitationRequired:
    """
    Helper para criar elicitation de seleção.

    Args:
        message: Mensagem a exibir (ex: "Qual serviço você deseja?")
        options: Lista de opções para o usuário escolher
        tool_name: Nome do tool
        tool_args: Argumentos originais do tool
        metadata: Dados extras

    Returns:
        ElicitationRequired exception to be raised
    """
    return ElicitationRequired(
        type=ElicitationType.SELECTION,
        message=message,
        tool_name=tool_name,
        tool_args=tool_args,
        options=options,
        metadata=metadata,
    )


def create_text_input_elicitation(
    message: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ElicitationRequired:
    """
    Helper para criar elicitation de entrada de texto.

    Args:
        message: Mensagem/prompt (ex: "Por favor, informe seu CPF:")
        tool_name: Nome do tool
        tool_args: Argumentos originais do tool
        metadata: Dados extras

    Returns:
        ElicitationRequired exception to be raised
    """
    return ElicitationRequired(
        type=ElicitationType.TEXT_INPUT,
        message=message,
        tool_name=tool_name,
        tool_args=tool_args,
        metadata=metadata,
    )


def format_elicitation_for_llm(pending: PendingElicitation) -> str:
    """
    Formata a elicitation pendente como mensagem para a LLM.

    Usado quando precisamos informar a LLM sobre a elicitation pendente
    para que ela possa gerar uma mensagem adequada ao usuário.
    """
    elicit_type = pending.get("type", "unknown")
    message = pending.get("message", "")
    options = pending.get("options")

    if elicit_type == ElicitationType.CONFIRMATION.value:
        return f"[AGUARDANDO CONFIRMAÇÃO]\n{message}\nOpções: Sim / Não"

    elif elicit_type == ElicitationType.SELECTION.value and options:
        options_text = "\n".join(
            [
                f"- {opt['label']}"
                + (f": {opt['description']}" if opt.get("description") else "")
                for opt in options
            ]
        )
        return f"[AGUARDANDO SELEÇÃO]\n{message}\nOpções:\n{options_text}"

    elif elicit_type == ElicitationType.TEXT_INPUT.value:
        return f"[AGUARDANDO INPUT]\n{message}"

    return f"[AGUARDANDO RESPOSTA]\n{message}"


def validate_elicitation_response(
    pending: PendingElicitation, response: Any
) -> tuple[bool, Optional[str]]:
    """
    Valida a resposta do usuário para uma elicitation.

    Returns:
        Tuple (is_valid, error_message)
    """
    elicit_type = pending.get("type")

    if elicit_type == ElicitationType.CONFIRMATION.value:
        if isinstance(response, bool):
            return True, None
        if isinstance(response, str) and response.lower() in (
            "yes",
            "no",
            "sim",
            "não",
            "nao",
        ):
            return True, None
        return False, "Resposta de confirmação deve ser Sim ou Não"

    elif elicit_type == ElicitationType.SELECTION.value:
        options = pending.get("options", [])
        valid_values = [opt["value"] for opt in options]
        if response in valid_values:
            return True, None
        return False, f"Valor deve ser um de: {', '.join(valid_values)}"

    elif elicit_type == ElicitationType.TEXT_INPUT.value:
        if isinstance(response, str) and len(response.strip()) > 0:
            return True, None
        return False, "Entrada de texto não pode estar vazia"

    return True, None  # Aceita por padrão


def normalize_confirmation_response(response: Any) -> bool:
    """
    Normaliza resposta de confirmação para boolean.

    Aceita: True, False, "yes", "no", "sim", "não", "nao"
    """
    if isinstance(response, bool):
        return response
    if isinstance(response, str):
        return response.lower() in ("yes", "sim", "true", "1")
    return False
