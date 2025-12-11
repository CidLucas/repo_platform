"""
Exceptions for elicitation service.
"""

import uuid
from typing import Any

from vizu_elicitation_service.models import PendingElicitation
from vizu_models import ElicitationOption, ElicitationType


class ElicitationError(Exception):
    """Base exception for elicitation errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or "ELICITATION_ERROR"


class ElicitationValidationError(ElicitationError):
    """Response validation failed."""

    def __init__(self, message: str, expected: str | None = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.expected = expected


class ElicitationTimeoutError(ElicitationError):
    """Elicitation timed out waiting for response."""

    def __init__(self, elicitation_id: str, timeout_seconds: int):
        super().__init__(
            f"Elicitation {elicitation_id} timed out after {timeout_seconds}s",
            "TIMEOUT_ERROR",
        )
        self.elicitation_id = elicitation_id
        self.timeout_seconds = timeout_seconds


class ElicitationNotFoundError(ElicitationError):
    """Pending elicitation not found."""

    def __init__(self, session_id: str):
        super().__init__(
            f"No pending elicitation found for session {session_id}",
            "NOT_FOUND_ERROR",
        )
        self.session_id = session_id


class ElicitationRequired(Exception):
    """
    Exception raised when a tool needs user input.

    This exception is caught by the graph executor which then
    configures the state to wait for user response.
    """

    def __init__(
        self,
        type: ElicitationType,
        message: str,
        tool_name: str,
        tool_args: dict[str, Any],
        options: list[ElicitationOption] | None = None,
        metadata: dict[str, Any] | None = None,
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
        """Convert to PendingElicitation for state storage."""
        from datetime import datetime

        return PendingElicitation(
            elicitation_id=self.elicitation_id,
            type=self.type.value if hasattr(self.type, "value") else str(self.type),
            message=self.message,
            options=[opt.to_dict() for opt in self.options] if self.options else None,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
            metadata=self.metadata,
            created_at=datetime.utcnow().isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "elicitation_id": self.elicitation_id,
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "message": self.message,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "options": [opt.to_dict() for opt in self.options] if self.options else [],
            "metadata": self.metadata,
        }
