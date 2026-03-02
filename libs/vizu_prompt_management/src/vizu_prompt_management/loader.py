"""
Simplified Prompt Loader - Langfuse as source of truth with builtin fallback.

Architecture (simplified from 4-tier to 2-tier):
1. PRIMARY: Langfuse Prompt Management (label="production")
2. FALLBACK: Built-in template (Jinja2 support for {% if %}, {% for %})

Key changes from previous implementation:
- Removed database layer entirely (no more prompt_template table queries)
- No client-specific prompts — context is injected via variables
- Uses Langfuse SDK's native get_prompt() + compile()
- Langfuse SDK handles its own internal caching (cache_ttl_seconds)
- Redis caching handled at ContextService layer, not here
"""

import asyncio
import logging
import time as _time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vizu_prompt_management.renderer import TemplateRenderer
from vizu_prompt_management.templates import (
    BUILTIN_TEMPLATES,
    PromptCategory,
)

logger = logging.getLogger(__name__)


@dataclass
class LoadedPrompt:
    """A loaded and rendered prompt."""

    name: str
    content: str
    version: int = 1
    source: str = "builtin"  # "langfuse" or "builtin"
    category: PromptCategory | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    loaded_at: datetime | None = None
    langfuse_label: str | None = None  # For tracing
    langfuse_prompt: Any | None = None  # Raw Langfuse prompt object for trace linking

    def as_system_message(self) -> dict[str, str]:
        """Return as OpenAI-style system message."""
        return {"role": "system", "content": self.content}

    def as_user_message(self) -> dict[str, str]:
        """Return as OpenAI-style user message."""
        return {"role": "user", "content": self.content}

    def get_trace_metadata(self) -> dict[str, Any]:
        """Get metadata for Langfuse trace injection."""
        return {
            "prompt_name": self.name,
            "prompt_version": self.version,
            "prompt_source": self.source,
            "prompt_label": self.langfuse_label,
        }


class PromptLoader:
    """
    Load prompts with Langfuse-first strategy and builtin fallback.

    Simplified priority:
    1. Langfuse (label="production" by default)
    2. Built-in template

    Note: Redis caching is handled at the ContextService layer.
    Langfuse SDK has its own internal cache (cache_ttl_seconds parameter).
    """

    # Circuit breaker: skip Langfuse for this many seconds after a failure
    _langfuse_cooldown_until: float = 0.0
    _LANGFUSE_COOLDOWN_SECONDS: float = 60.0  # 1 minute (reduced from 5 for faster recovery)
    _LANGFUSE_TIMEOUT_SECONDS: float = 2.0  # max wait per fetch

    def __init__(
        self,
        cache_ttl_seconds: int = 300,
        renderer: TemplateRenderer | None = None,
        langfuse_label: str = "production",
    ):
        """
        Initialize PromptLoader.

        Args:
            cache_ttl_seconds: TTL for Langfuse SDK's internal cache
            renderer: Template renderer for builtin templates (creates default if None)
            langfuse_label: Default Langfuse label ("production", "staging", "latest")
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self.renderer = renderer or TemplateRenderer()
        self.langfuse_label = langfuse_label
        self._langfuse_client = None

    def _get_langfuse_client(self):
        """Lazily initialize Langfuse client. Returns None if in cooldown."""
        if _time.time() < self._langfuse_cooldown_until:
            remaining = int(self._langfuse_cooldown_until - _time.time())
            logger.debug(
                f"[PROMPT] Langfuse circuit breaker active, {remaining}s remaining until retry"
            )
            return None
        if self._langfuse_client is None:
            try:
                from vizu_observability_bootstrap.langfuse import (
                    LangfusePromptClient,
                    is_langfuse_enabled,
                )

                if is_langfuse_enabled():
                    self._langfuse_client = LangfusePromptClient()
                    logger.info("[PROMPT] Langfuse prompt client initialized successfully")
                else:
                    logger.warning(
                        "[PROMPT] Langfuse not enabled (missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY)"
                    )
            except ImportError:
                logger.debug("[PROMPT] vizu_observability_bootstrap not available")
            except Exception as e:
                logger.warning(f"[PROMPT] Failed to initialize Langfuse: {e}")
                self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
                logger.warning(
                    f"[PROMPT] Circuit breaker activated for {self._LANGFUSE_COOLDOWN_SECONDS}s"
                )
        return self._langfuse_client

    async def load(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        langfuse_label: str | None = None,
        allow_fallback: bool = False,
    ) -> LoadedPrompt:
        """
        Load and render a prompt.

        Langfuse is the source of truth. Fallback to builtin only if explicitly allowed.

        Args:
            name: Prompt name (e.g., "atendente/default")
            variables: Variables for template substitution
            langfuse_label: Override default Langfuse label
            allow_fallback: If True, fall back to builtin when Langfuse unavailable.
                           Default False - raises error if Langfuse prompt not found.

        Returns:
            LoadedPrompt with rendered content

        Raises:
            PromptNotFoundError: If prompt not in Langfuse and allow_fallback=False
        """
        variables = variables or {}
        label = langfuse_label or self.langfuse_label

        # 1. Try Langfuse (mandatory in production)
        langfuse_result = await self._load_from_langfuse(name, variables, label)
        if langfuse_result:
            logger.info(
                f"[PROMPT] Loaded '{name}' from Langfuse (version={langfuse_result.version}, label={label})"
            )
            return langfuse_result

        # 2. Langfuse failed - check if fallback allowed
        if not allow_fallback:
            logger.error(
                f"[PROMPT] CRITICAL: Prompt '{name}' not found in Langfuse (label={label}). "
                "Ensure prompt exists in Langfuse with correct name and label."
            )
            raise PromptNotFoundError(
                f"Prompt '{name}' not found in Langfuse (label={label}). "
                "Builtin fallback disabled - add prompt to Langfuse."
            )

        # 3. Fallback to builtin (only if explicitly allowed)
        logger.warning(
            f"[PROMPT] Falling back to builtin for '{name}' - Langfuse unavailable or prompt not found"
        )
        return self._load_from_builtin(name, variables)

    async def load_raw(
        self,
        name: str,
        langfuse_label: str | None = None,
    ) -> LoadedPrompt:
        """
        Load raw prompt template WITHOUT variable substitution.

        Useful for Redis caching scenarios where you want to cache
        the raw template and apply variables later.

        Args:
            name: Prompt name (e.g., "atendente/default")
            langfuse_label: Override default Langfuse label

        Returns:
            LoadedPrompt with raw (unrendered) content
        """
        label = langfuse_label or self.langfuse_label

        # 1. Try Langfuse first (raw template)
        langfuse_result = await self._load_raw_from_langfuse(name, label)
        if langfuse_result:
            return langfuse_result

        # 2. Fallback to builtin (raw template)
        return self._load_raw_from_builtin(name)

    async def _load_from_langfuse(
        self,
        name: str,
        variables: dict[str, Any],
        label: str = "production",
    ) -> LoadedPrompt | None:
        """Load and compile prompt from Langfuse with timeout and circuit breaker."""
        client = self._get_langfuse_client()
        if not client:
            return None

        try:
            # Run sync Langfuse call in a thread with a short timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    client.get_and_compile,
                    name,
                    variables,
                    label,
                    self.cache_ttl_seconds,
                ),
                timeout=self._LANGFUSE_TIMEOUT_SECONDS,
            )

            if result is None:
                return None

            compiled_text, prompt_obj = result
            actual_version = getattr(prompt_obj, "version", 1)

            return LoadedPrompt(
                name=name,
                content=compiled_text,
                version=actual_version,
                source="langfuse",
                metadata={"langfuse_prompt_id": getattr(prompt_obj, "id", None)},
                loaded_at=datetime.utcnow(),
                langfuse_label=label,
                langfuse_prompt=prompt_obj,
            )
        except TimeoutError:
            logger.warning(
                f"Langfuse timeout fetching '{name}', disabling for {self._LANGFUSE_COOLDOWN_SECONDS}s"
            )
            self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
            return None
        except Exception as e:
            logger.warning(f"Langfuse prompt '{name}' fetch failed (label={label}): {e}")
            if "Connection refused" in str(e) or "connection" in str(e).lower():
                self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
                logger.info(
                    f"Langfuse unreachable, disabling for {self._LANGFUSE_COOLDOWN_SECONDS}s"
                )
            return None

    async def _load_raw_from_langfuse(
        self,
        name: str,
        label: str = "production",
    ) -> LoadedPrompt | None:
        """Load raw prompt template from Langfuse (without variable substitution)."""
        client = self._get_langfuse_client()
        if not client:
            return None

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    client.get_prompt_template,
                    name,
                    label,
                    self.cache_ttl_seconds,
                ),
                timeout=self._LANGFUSE_TIMEOUT_SECONDS,
            )

            if result is None:
                return None

            raw_text, prompt_obj = result
            actual_version = getattr(prompt_obj, "version", 1)

            return LoadedPrompt(
                name=name,
                content=raw_text,
                version=actual_version,
                source="langfuse",
                metadata={"langfuse_prompt_id": getattr(prompt_obj, "id", None)},
                loaded_at=datetime.utcnow(),
                langfuse_label=label,
                langfuse_prompt=prompt_obj,
            )
        except TimeoutError:
            logger.warning(
                f"Langfuse timeout fetching raw '{name}', disabling for {self._LANGFUSE_COOLDOWN_SECONDS}s"
            )
            self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
            return None
        except Exception as e:
            logger.warning(f"Langfuse raw template '{name}' fetch failed (label={label}): {e}")
            return None

    def _load_from_builtin(
        self,
        name: str,
        variables: dict[str, Any],
    ) -> LoadedPrompt:
        """Load and render from builtin templates."""
        builtin = BUILTIN_TEMPLATES.get(name)
        if not builtin:
            raise PromptNotFoundError(f"Prompt not found: {name}")

        # Apply default values for optional variables
        optional_vars = (
            builtin.get_optional_variables_dict()
            if hasattr(builtin, "get_optional_variables_dict")
            else (
                builtin.optional_variables
                if isinstance(getattr(builtin, "optional_variables", None), dict)
                else {}
            )
        )
        merged_vars = {**optional_vars, **variables}
        content = self.renderer.render(builtin.content, merged_vars)

        return LoadedPrompt(
            name=builtin.name,
            content=content,
            version=builtin.version,
            source="builtin",
            category=builtin.category,
            metadata={
                "description": builtin.description,
                "required_variables": builtin.required_variables,
            },
            loaded_at=datetime.utcnow(),
        )

    def _load_raw_from_builtin(self, name: str) -> LoadedPrompt:
        """Load raw builtin template without variable substitution."""
        builtin = BUILTIN_TEMPLATES.get(name)
        if not builtin:
            raise PromptNotFoundError(f"Prompt not found: {name}")

        return LoadedPrompt(
            name=builtin.name,
            content=builtin.content,  # Raw content, no rendering
            version=builtin.version,
            source="builtin",
            category=builtin.category,
            metadata={
                "description": builtin.description,
                "required_variables": builtin.required_variables,
            },
            loaded_at=datetime.utcnow(),
        )

    def load_builtin(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
    ) -> LoadedPrompt:
        """
        Load a built-in prompt directly (no Langfuse lookup).

        Synchronous method for when you specifically want builtin.

        Args:
            name: Prompt name
            variables: Variables for substitution

        Returns:
            LoadedPrompt
        """
        variables = variables or {}
        return self._load_from_builtin(name, variables)

    def list_available(
        self,
        category: PromptCategory | None = None,
    ) -> list[str]:
        """
        List available prompt names from builtin templates.

        Args:
            category: Filter by category

        Returns:
            List of prompt names
        """
        names = set()

        for name, config in BUILTIN_TEMPLATES.items():
            if category is None or config.category == category:
                names.add(name)

        return sorted(names)

    def clear_cache(self, name: str | None = None) -> None:
        """
        Clear Langfuse client state (triggers re-initialization on next call).

        Note: Langfuse SDK manages its own internal cache. This resets the client.
        """
        if name:
            logger.debug(f"Cache clear requested for '{name}' - Langfuse SDK manages its own cache")
        else:
            self._langfuse_client = None
            logger.info("Langfuse client reset - will reinitialize on next prompt fetch")


class PromptNotFoundError(Exception):
    """Prompt not found error."""

    pass
