"""
Data models for elicitation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class PendingElicitation(TypedDict, total=False):
    """
    Elicitation pending user response.

    Stores the state needed to resume tool execution
    after receiving the user's response.
    """

    elicitation_id: str  # Unique ID for correlation
    type: str  # confirmation, selection, text_input, date_time
    message: str  # Message to display to user
    options: Optional[List[Dict[str, Any]]]  # Options for selection type
    tool_name: str  # Name of tool that requested
    tool_args: Dict[str, Any]  # Original tool arguments
    metadata: Optional[Dict[str, Any]]  # Additional data
    created_at: Optional[str]  # ISO timestamp
    expires_at: Optional[str]  # ISO timestamp for expiration


@dataclass
class ElicitationResult:
    """Result of processing an elicitation response."""

    elicitation_id: str
    success: bool
    response: Any = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def should_retry_tool(self) -> bool:
        """Whether the tool should be retried with the response."""
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "elicitation_id": self.elicitation_id,
            "success": self.success,
            "response": self.response,
            "error": self.error,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "metadata": self.metadata,
        }


@dataclass
class ElicitationContext:
    """Context for elicitation execution."""

    session_id: str
    cliente_id: Optional[str] = None
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    channel: Optional[str] = None  # whatsapp, web, api
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ElicitationOption:
    """An option for selection-type elicitation."""

    value: str
    label: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "value": self.value,
            "label": self.label,
        }
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ElicitationOption":
        """Create from dictionary."""
        return cls(
            value=data["value"],
            label=data["label"],
            description=data.get("description"),
            metadata=data.get("metadata"),
        )
