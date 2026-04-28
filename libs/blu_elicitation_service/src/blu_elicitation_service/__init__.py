"""
blu_elicitation_service - Human-in-the-loop elicitation for Blu agents.

This library provides:
- Elicitation flow management
- Pending elicitation storage (Redis)
- Response validation and processing
- Helper functions for common elicitation patterns
"""

__version__ = "0.1.0"

from blu_elicitation_service.exceptions import (
    ElicitationError,
    ElicitationNotFoundError,
    ElicitationRequired,
    ElicitationTimeoutError,
    ElicitationValidationError,
)
from blu_elicitation_service.helpers import (
    build_options_from_list,
    create_confirmation_elicitation,
    create_datetime_elicitation,
    create_selection_elicitation,
    create_text_input_elicitation,
    format_elicitation_for_llm,
    normalize_confirmation_response,
    validate_elicitation_response,
)
from blu_elicitation_service.manager import ElicitationManager
from blu_elicitation_service.models import (
    ElicitationResult,
    PendingElicitation,
)
from blu_elicitation_service.response_handler import ElicitationResponseHandler
from blu_elicitation_service.store import PendingElicitationStore

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
