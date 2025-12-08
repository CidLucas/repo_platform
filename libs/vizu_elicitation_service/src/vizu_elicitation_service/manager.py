"""
Central manager for elicitation flows.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from vizu_models import ElicitationType, ElicitationOption

from vizu_elicitation_service.models import (
    PendingElicitation,
    ElicitationResult,
    ElicitationContext,
)
from vizu_elicitation_service.store import PendingElicitationStore
from vizu_elicitation_service.response_handler import ElicitationResponseHandler
from vizu_elicitation_service.exceptions import (
    ElicitationRequired,
    ElicitationError,
    ElicitationNotFoundError,
)

logger = logging.getLogger(__name__)


class ElicitationManager:
    """
    Central coordinator for elicitation flows.

    Provides:
    - Create elicitations
    - Store/retrieve pending elicitations
    - Process responses
    - Helper methods for common patterns
    """

    def __init__(
        self,
        redis_client: Any,
        ttl_seconds: int = 3600,
        store: Optional[PendingElicitationStore] = None,
        handler: Optional[ElicitationResponseHandler] = None,
    ):
        """
        Initialize manager.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Default TTL for pending elicitations
            store: Optional custom store (uses default if None)
            handler: Optional custom handler (uses default if None)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.store = store or PendingElicitationStore(redis_client, ttl_seconds)
        self.handler = handler or ElicitationResponseHandler()

    # =========================================================================
    # CREATE ELICITATIONS
    # =========================================================================

    def create_confirmation(
        self,
        message: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ElicitationRequired:
        """
        Create a confirmation elicitation (Yes/No).

        Args:
            message: Message to display
            tool_name: Name of requesting tool
            tool_args: Original tool arguments
            metadata: Additional context

        Returns:
            ElicitationRequired exception (raise it to pause)
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

    def create_selection(
        self,
        message: str,
        options: List[ElicitationOption],
        tool_name: str,
        tool_args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ElicitationRequired:
        """
        Create a selection elicitation (multiple choice).

        Args:
            message: Message to display
            options: List of options
            tool_name: Name of requesting tool
            tool_args: Original tool arguments
            metadata: Additional context

        Returns:
            ElicitationRequired exception
        """
        return ElicitationRequired(
            type=ElicitationType.SELECTION,
            message=message,
            tool_name=tool_name,
            tool_args=tool_args,
            options=options,
            metadata=metadata,
        )

    def create_text_input(
        self,
        message: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ElicitationRequired:
        """
        Create a text input elicitation.

        Args:
            message: Prompt message
            tool_name: Name of requesting tool
            tool_args: Original tool arguments
            metadata: Additional context

        Returns:
            ElicitationRequired exception
        """
        return ElicitationRequired(
            type=ElicitationType.TEXT_INPUT,
            message=message,
            tool_name=tool_name,
            tool_args=tool_args,
            metadata=metadata,
        )

    def create_datetime(
        self,
        message: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ElicitationRequired:
        """
        Create a datetime input elicitation.

        Args:
            message: Prompt message
            tool_name: Name of requesting tool
            tool_args: Original tool arguments
            metadata: Additional context

        Returns:
            ElicitationRequired exception
        """
        return ElicitationRequired(
            type=ElicitationType.DATE_TIME,
            message=message,
            tool_name=tool_name,
            tool_args=tool_args,
            metadata=metadata,
        )

    # =========================================================================
    # STORE/RETRIEVE
    # =========================================================================

    async def store_pending(
        self,
        session_id: str,
        elicitation: ElicitationRequired,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Store a pending elicitation.

        Args:
            session_id: Session identifier
            elicitation: ElicitationRequired to store
            ttl_seconds: Optional TTL override

        Returns:
            Elicitation ID
        """
        pending = elicitation.to_pending_elicitation()
        await self.store.save(session_id, pending, ttl_seconds)
        return elicitation.elicitation_id

    async def retrieve_pending(
        self,
        session_id: str,
    ) -> Optional[PendingElicitation]:
        """
        Retrieve pending elicitation for session.

        Args:
            session_id: Session identifier

        Returns:
            PendingElicitation if found
        """
        return await self.store.get(session_id)

    async def has_pending(self, session_id: str) -> bool:
        """Check if session has pending elicitation."""
        return await self.store.exists(session_id)

    async def clear_pending(self, session_id: str) -> bool:
        """Clear pending elicitation for session."""
        return await self.store.delete(session_id)

    # =========================================================================
    # PROCESS RESPONSES
    # =========================================================================

    async def process_response(
        self,
        session_id: str,
        response: Any,
        clear_pending: bool = True,
    ) -> ElicitationResult:
        """
        Process a user response to pending elicitation.

        Args:
            session_id: Session identifier
            response: User's response
            clear_pending: Whether to clear the pending elicitation

        Returns:
            ElicitationResult with processed response

        Raises:
            ElicitationNotFoundError: If no pending elicitation
        """
        # Get pending
        pending = await self.store.get_or_raise(session_id)

        # Process response
        result = self.handler.process(pending, response)

        # Clear if requested and successful
        if clear_pending and result.success:
            await self.store.delete(session_id)

        return result

    async def validate_response(
        self,
        session_id: str,
        response: Any,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a response without processing.

        Args:
            session_id: Session identifier
            response: User's response

        Returns:
            Tuple of (is_valid, error_message)
        """
        pending = await self.store.get(session_id)
        if not pending:
            return False, "No pending elicitation found"

        return self.handler.validate(pending, response)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def format_for_llm(self, pending: PendingElicitation) -> str:
        """
        Format pending elicitation as message for LLM.

        Used when informing the LLM about what input is needed.
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

    def build_tool_args_with_response(
        self,
        result: ElicitationResult,
    ) -> Dict[str, Any]:
        """
        Build tool arguments including the elicitation response.

        Used when retrying the tool after getting user response.
        """
        args = dict(result.tool_args or {})
        args["elicitation_response"] = {
            "confirmed": result.response if isinstance(result.response, bool) else None,
            "value": result.response,
            "elicitation_id": result.elicitation_id,
        }
        return args
