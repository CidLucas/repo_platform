"""
vizu_elicitation_service - Human-in-the-loop elicitation for Vizu agents.

This library provides:
- Elicitation flow management
- Pending elicitation storage (Redis)
- Response validation and processing
- Helper functions for common elicitation patterns
"""

__version__ = "0.1.0"

from vizu_elicitation_service.models import (
    PendingElicitation,
    ElicitationResult,
)

from vizu_elicitation_service.exceptions import (
    ElicitationRequired,
    ElicitationError,
    ElicitationValidationError,
    ElicitationTimeoutError,
    ElicitationNotFoundError,
)

from vizu_elicitation_service.manager import ElicitationManager

from vizu_elicitation_service.store import PendingElicitationStore

from vizu_elicitation_service.response_handler import ElicitationResponseHandler

from vizu_elicitation_service.helpers import (
    create_confirmation_elicitation,
    create_selection_elicitation,
    create_text_input_elicitation,
    create_datetime_elicitation,
    format_elicitation_for_llm,
    normalize_confirmation_response,
    validate_elicitation_response,
    build_options_from_list,
)

__all__ = [
    "__version__",
    # Models
    "PendingElicitation",
    "ElicitationResult",
    # Exceptions
    "ElicitationRequired",
    "ElicitationError",
    "ElicitationValidationError",
    "ElicitationTimeoutError",
    "ElicitationNotFoundError",
    # Core classes
    "ElicitationManager",
    "PendingElicitationStore",
    "ElicitationResponseHandler",
    # Helpers
    "create_confirmation_elicitation",
    "create_selection_elicitation",
    "create_text_input_elicitation",
    "create_datetime_elicitation",
    "format_elicitation_for_llm",
    "normalize_confirmation_response",
    "validate_elicitation_response",
    "build_options_from_list",
]
