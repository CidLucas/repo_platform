"""
Helper functions for common elicitation patterns.
"""

from typing import Any, Dict, List, Optional

from vizu_models import ElicitationType, ElicitationOption

from vizu_elicitation_service.models import PendingElicitation
from vizu_elicitation_service.exceptions import ElicitationRequired


def create_confirmation_elicitation(
    message: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ElicitationRequired:
    """
    Create a confirmation elicitation (Yes/No).

    Args:
        message: Message to display (e.g., "Confirm appointment for Jan 15?")
        tool_name: Name of the requesting tool
        tool_args: Original tool arguments
        metadata: Additional context data

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
    Create a selection elicitation (multiple choice).

    Args:
        message: Message to display (e.g., "Which service do you want?")
        options: List of options for the user to choose
        tool_name: Name of the tool
        tool_args: Original tool arguments
        metadata: Additional data

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
    Create a text input elicitation.

    Args:
        message: Prompt message (e.g., "Please enter your CPF:")
        tool_name: Name of the tool
        tool_args: Original tool arguments
        metadata: Additional data

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


def create_datetime_elicitation(
    message: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ElicitationRequired:
    """
    Create a datetime input elicitation.

    Args:
        message: Prompt message (e.g., "When would you like to schedule?")
        tool_name: Name of the tool
        tool_args: Original tool arguments
        metadata: Additional data

    Returns:
        ElicitationRequired exception to be raised
    """
    return ElicitationRequired(
        type=ElicitationType.DATE_TIME,
        message=message,
        tool_name=tool_name,
        tool_args=tool_args,
        metadata=metadata,
    )


def format_elicitation_for_llm(pending: PendingElicitation) -> str:
    """
    Format a pending elicitation as a message for the LLM.

    Used when informing the LLM about the pending elicitation
    so it can generate an appropriate message to the user.

    Args:
        pending: PendingElicitation dict

    Returns:
        Formatted string for LLM
    """
    elicit_type = pending.get("type", "unknown")
    message = pending.get("message", "")
    options = pending.get("options")

    if elicit_type == ElicitationType.CONFIRMATION.value:
        return f"[AGUARDANDO CONFIRMAÇÃO]\n{message}\nOpções: Sim / Não"

    elif elicit_type == ElicitationType.SELECTION.value and options:
        options_text = "\n".join([
            f"- {opt['label']}" +
            (f": {opt.get('description', '')}" if opt.get("description") else "")
            for opt in options
        ])
        return f"[AGUARDANDO SELEÇÃO]\n{message}\nOpções:\n{options_text}"

    elif elicit_type == ElicitationType.TEXT_INPUT.value:
        return f"[AGUARDANDO INPUT]\n{message}"

    elif elicit_type == ElicitationType.DATE_TIME.value:
        return f"[AGUARDANDO DATA/HORA]\n{message}"

    return f"[AGUARDANDO RESPOSTA]\n{message}"


def normalize_confirmation_response(response: Any) -> bool:
    """
    Normalize a confirmation response to boolean.

    Accepts: True, False, "yes", "no", "sim", "não", "nao", "y", "n", "s"

    Args:
        response: User response

    Returns:
        Boolean value
    """
    if isinstance(response, bool):
        return response

    if isinstance(response, str):
        return response.lower().strip() in {
            "yes", "sim", "true", "1", "y", "s"
        }

    return False


def validate_elicitation_response(
    pending: PendingElicitation,
    response: Any,
) -> tuple[bool, Optional[str]]:
    """
    Validate a response against a pending elicitation.

    Args:
        pending: PendingElicitation dict
        response: User response

    Returns:
        Tuple of (is_valid, error_message)
    """
    elicit_type = pending.get("type")

    if elicit_type == ElicitationType.CONFIRMATION.value:
        if isinstance(response, bool):
            return True, None
        if isinstance(response, str) and response.lower().strip() in {
            "yes", "no", "sim", "não", "nao", "y", "n", "s"
        }:
            return True, None
        return False, "Resposta de confirmação deve ser Sim ou Não"

    elif elicit_type == ElicitationType.SELECTION.value:
        options = pending.get("options", [])
        valid_values = {opt["value"] for opt in options}
        if str(response) in valid_values:
            return True, None
        # Also check numeric index
        try:
            idx = int(response)
            if 1 <= idx <= len(options):
                return True, None
        except (ValueError, TypeError):
            pass
        return False, f"Valor deve ser um de: {', '.join(sorted(valid_values))}"

    elif elicit_type == ElicitationType.TEXT_INPUT.value:
        if isinstance(response, str) and len(response.strip()) > 0:
            return True, None
        return False, "Entrada de texto não pode estar vazia"

    elif elicit_type == ElicitationType.DATE_TIME.value:
        if response is not None:
            return True, None
        return False, "Data/hora não informada"

    return True, None  # Accept by default


def build_options_from_list(
    items: List[str],
    add_descriptions: Optional[Dict[str, str]] = None,
) -> List[ElicitationOption]:
    """
    Build ElicitationOption list from simple string list.

    Args:
        items: List of option values/labels
        add_descriptions: Optional dict mapping values to descriptions

    Returns:
        List of ElicitationOption
    """
    options = []
    descriptions = add_descriptions or {}

    for item in items:
        options.append(
            ElicitationOption(
                value=item,
                label=item,
                description=descriptions.get(item),
            )
        )

    return options
