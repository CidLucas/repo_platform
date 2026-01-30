"""
Token budgeting utilities for managing LLM context window limits.

Provides token estimation and message truncation to prevent "prompt too long" errors.
Uses character-based estimation (~4 chars per token) which is conservative and fast.

Usage:
    from vizu_llm_service import TokenBudget, estimate_tokens, truncate_messages

    # Simple estimation
    tokens = estimate_tokens("Hello world")

    # With message list
    budget = TokenBudget(max_tokens=120000)
    truncated = budget.truncate_messages(messages, system_prompt)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_PROMPT_TOKENS = 120000  # Leave 11K for response out of 131K limit
DEFAULT_CHARS_PER_TOKEN = 4  # Conservative estimate (~3.5 is typical for English)


def estimate_tokens(text: str, chars_per_token: int = DEFAULT_CHARS_PER_TOKEN) -> int:
    """
    Estimate token count from text using character-based heuristic.

    Args:
        text: Input text to estimate
        chars_per_token: Characters per token ratio (default: 4)

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // chars_per_token


def get_message_content(msg: Any) -> str:
    """
    Extract text content from a message object.

    Handles LangChain message types (HumanMessage, AIMessage, etc.)
    and multimodal content lists.

    Args:
        msg: Message object with .content attribute

    Returns:
        String content of the message
    """
    if hasattr(msg, "content"):
        content = msg.content
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle multimodal content (text + images)
            parts = []
            for c in content:
                if isinstance(c, str):
                    parts.append(c)
                elif isinstance(c, dict) and "text" in c:
                    parts.append(c["text"])
            return " ".join(parts)
    return str(msg)


@dataclass
class TokenBudgetResult:
    """Result of token budget calculation and truncation."""

    messages: list[Any]
    system_tokens: int
    history_tokens: int
    total_tokens: int
    was_truncated: bool
    messages_removed: int = 0


@dataclass
class TokenBudget:
    """
    Token budget manager for LLM context windows.

    Provides estimation and truncation to stay within model limits.

    Example:
        budget = TokenBudget(max_tokens=120000)
        result = budget.apply(messages, system_prompt)
        if result.was_truncated:
            logger.warning(f"Truncated {result.messages_removed} messages")
    """

    max_tokens: int = DEFAULT_MAX_PROMPT_TOKENS
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN
    min_history_messages: int = 1  # Always keep at least this many messages

    def estimate(self, text: str) -> int:
        """Estimate tokens for a text string."""
        return estimate_tokens(text, self.chars_per_token)

    def estimate_messages(self, messages: list[Any]) -> int:
        """Estimate total tokens for a list of messages."""
        return sum(self.estimate(get_message_content(m)) for m in messages)

    def apply(
        self,
        history_messages: list[Any],
        system_prompt: str,
        log_prefix: str = "[TOKEN_BUDGET]",
    ) -> TokenBudgetResult:
        """
        Apply token budget to messages, truncating if necessary.

        Args:
            history_messages: List of conversation messages (excluding system)
            system_prompt: The system prompt text
            log_prefix: Prefix for log messages

        Returns:
            TokenBudgetResult with potentially truncated messages and metrics
        """
        # Make a mutable copy
        messages = list(history_messages)

        # Calculate current usage
        system_tokens = self.estimate(system_prompt)
        history_tokens = self.estimate_messages(messages)
        total_tokens = system_tokens + history_tokens

        logger.info(
            f"{log_prefix} System: {system_tokens}, History: {history_tokens}, Total: {total_tokens}"
        )

        was_truncated = False
        messages_removed = 0

        # Progressive truncation if over budget
        if total_tokens > self.max_tokens:
            was_truncated = True
            logger.warning(
                f"{log_prefix} Over limit ({total_tokens} > {self.max_tokens}), truncating history"
            )

            # Remove oldest messages first, keeping at least min_history_messages
            while total_tokens > self.max_tokens and len(messages) > self.min_history_messages:
                removed = messages.pop(0)
                removed_tokens = self.estimate(get_message_content(removed))
                total_tokens -= removed_tokens
                messages_removed += 1
                history_tokens -= removed_tokens
                logger.debug(
                    f"{log_prefix} Removed message ({removed_tokens} tokens), "
                    f"new total: {total_tokens}"
                )

            logger.info(
                f"{log_prefix} After truncation: {len(messages)} messages, "
                f"{total_tokens} tokens (removed {messages_removed})"
            )

        return TokenBudgetResult(
            messages=messages,
            system_tokens=system_tokens,
            history_tokens=history_tokens,
            total_tokens=total_tokens,
            was_truncated=was_truncated,
            messages_removed=messages_removed,
        )


def truncate_messages(
    messages: list[Any],
    system_prompt: str,
    max_tokens: int = DEFAULT_MAX_PROMPT_TOKENS,
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN,
) -> list[Any]:
    """
    Convenience function to truncate messages to fit within token budget.

    Args:
        messages: List of conversation messages (excluding system)
        system_prompt: The system prompt text
        max_tokens: Maximum allowed tokens
        chars_per_token: Characters per token ratio

    Returns:
        Potentially truncated list of messages
    """
    budget = TokenBudget(max_tokens=max_tokens, chars_per_token=chars_per_token)
    result = budget.apply(messages, system_prompt)
    return result.messages
