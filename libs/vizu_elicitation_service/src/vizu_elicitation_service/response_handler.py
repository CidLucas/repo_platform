"""
Process and validate elicitation responses.
"""

import logging
from typing import Any, Tuple, Optional

from vizu_models import ElicitationType

from vizu_elicitation_service.models import PendingElicitation, ElicitationResult
from vizu_elicitation_service.exceptions import ElicitationValidationError

logger = logging.getLogger(__name__)


class ElicitationResponseHandler:
    """
    Handle and validate user responses to elicitations.

    Provides:
    - Response validation per elicitation type
    - Response normalization
    - Error message generation
    """

    def validate(
        self,
        elicitation: PendingElicitation,
        response: Any,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a response against the elicitation.

        Args:
            elicitation: Pending elicitation
            response: User's response

        Returns:
            Tuple of (is_valid, error_message)
        """
        elicit_type = elicitation.get("type", "")

        if elicit_type == ElicitationType.CONFIRMATION.value:
            return self._validate_confirmation(response)

        elif elicit_type == ElicitationType.SELECTION.value:
            return self._validate_selection(elicitation, response)

        elif elicit_type == ElicitationType.TEXT_INPUT.value:
            return self._validate_text_input(response)

        elif elicit_type == ElicitationType.DATE_TIME.value:
            return self._validate_datetime(response)

        # Accept by default for unknown types
        return True, None

    def _validate_confirmation(self, response: Any) -> Tuple[bool, Optional[str]]:
        """Validate confirmation response."""
        if isinstance(response, bool):
            return True, None

        if isinstance(response, str):
            normalized = response.lower().strip()
            valid_values = {
                "yes", "no", "sim", "não", "nao",
                "true", "false", "1", "0",
                "y", "n", "s"
            }
            if normalized in valid_values:
                return True, None

        return False, "Resposta de confirmação deve ser Sim ou Não"

    def _validate_selection(
        self,
        elicitation: PendingElicitation,
        response: Any,
    ) -> Tuple[bool, Optional[str]]:
        """Validate selection response."""
        options = elicitation.get("options", [])
        if not options:
            return True, None  # No options defined, accept any

        valid_values = {str(opt.get("value", "")) for opt in options}

        # Also accept numeric indices (1-based)
        valid_indices = {str(i + 1) for i in range(len(options))}

        str_response = str(response).strip()

        if str_response in valid_values or str_response in valid_indices:
            return True, None

        options_str = ", ".join(sorted(valid_values))
        return False, f"Escolha deve ser uma das opções: {options_str}"

    def _validate_text_input(self, response: Any) -> Tuple[bool, Optional[str]]:
        """Validate text input response."""
        if response is None:
            return False, "Entrada de texto não pode estar vazia"

        if isinstance(response, str) and len(response.strip()) > 0:
            return True, None

        return False, "Entrada de texto não pode estar vazia"

    def _validate_datetime(self, response: Any) -> Tuple[bool, Optional[str]]:
        """Validate datetime response."""
        if response is None:
            return False, "Data/hora não informada"

        # Try to parse as ISO format or common formats
        from datetime import datetime

        if isinstance(response, datetime):
            return True, None

        if isinstance(response, str):
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
            ]
            for fmt in formats:
                try:
                    datetime.strptime(response, fmt)
                    return True, None
                except ValueError:
                    continue

        return False, "Formato de data/hora inválido"

    def normalize(
        self,
        elicitation: PendingElicitation,
        response: Any,
    ) -> Any:
        """
        Normalize a response to a standard format.

        Args:
            elicitation: Pending elicitation
            response: User's response

        Returns:
            Normalized response value
        """
        elicit_type = elicitation.get("type", "")

        if elicit_type == ElicitationType.CONFIRMATION.value:
            return self._normalize_confirmation(response)

        elif elicit_type == ElicitationType.SELECTION.value:
            return self._normalize_selection(elicitation, response)

        elif elicit_type == ElicitationType.TEXT_INPUT.value:
            return str(response).strip() if response else ""

        elif elicit_type == ElicitationType.DATE_TIME.value:
            return self._normalize_datetime(response)

        return response

    def _normalize_confirmation(self, response: Any) -> bool:
        """Normalize confirmation to boolean."""
        if isinstance(response, bool):
            return response

        if isinstance(response, str):
            return response.lower().strip() in {
                "yes", "sim", "true", "1", "y", "s"
            }

        return False

    def _normalize_selection(
        self,
        elicitation: PendingElicitation,
        response: Any,
    ) -> str:
        """Normalize selection to option value."""
        options = elicitation.get("options", [])
        str_response = str(response).strip()

        # Check if it's a numeric index (1-based)
        try:
            idx = int(str_response) - 1
            if 0 <= idx < len(options):
                return options[idx].get("value", str_response)
        except ValueError:
            pass

        # Return as-is if it matches an option value
        for opt in options:
            if opt.get("value") == str_response:
                return str_response

        return str_response

    def _normalize_datetime(self, response: Any) -> str:
        """Normalize datetime to ISO format."""
        from datetime import datetime

        if isinstance(response, datetime):
            return response.isoformat()

        if isinstance(response, str):
            formats = [
                ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S"),
                ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"),
                ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:00"),
                ("%Y-%m-%d", "%Y-%m-%d"),
                ("%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:00"),
                ("%d/%m/%Y", "%Y-%m-%d"),
            ]
            for input_fmt, output_fmt in formats:
                try:
                    dt = datetime.strptime(response, input_fmt)
                    return dt.strftime(output_fmt)
                except ValueError:
                    continue

        return str(response)

    def process(
        self,
        elicitation: PendingElicitation,
        response: Any,
    ) -> ElicitationResult:
        """
        Process a response: validate and normalize.

        Args:
            elicitation: Pending elicitation
            response: User's response

        Returns:
            ElicitationResult with processed response
        """
        # Validate
        is_valid, error = self.validate(elicitation, response)

        if not is_valid:
            return ElicitationResult(
                elicitation_id=elicitation.get("elicitation_id", ""),
                success=False,
                error=error,
                tool_name=elicitation.get("tool_name"),
                tool_args=elicitation.get("tool_args"),
            )

        # Normalize
        normalized = self.normalize(elicitation, response)

        return ElicitationResult(
            elicitation_id=elicitation.get("elicitation_id", ""),
            success=True,
            response=normalized,
            tool_name=elicitation.get("tool_name"),
            tool_args=elicitation.get("tool_args"),
            metadata=elicitation.get("metadata", {}),
        )
