"""
Load prompts from Langfuse (primary) with database and built-in fallbacks.

Architecture:
1. PRIMARY: Langfuse Prompt Management (label="production")
2. FALLBACK: Client-specific database prompt
3. FALLBACK: Global database prompt
4. FALLBACK: Built-in template

This enables prompt editing via Langfuse UI while maintaining backward compatibility.
"""

import asyncio
import logging
import time as _time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

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
    source: str = "builtin"  # "langfuse", "database", "builtin"
    category: PromptCategory | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    loaded_at: datetime | None = None
    langfuse_label: str | None = None  # For tracing

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
    Load prompts with Langfuse-first strategy.

    Priority:
    1. Langfuse (label="production" by default)
    2. Client-specific database prompt
    3. Global database prompt
    4. Built-in template
    """

    def __init__(
        self,
        db_session: Any | None = None,
        cache_ttl_seconds: int = 300,
        renderer: TemplateRenderer | None = None,
        langfuse_label: str = "production",
    ):
        """
        Initialize PromptLoader.

        Args:
            db_session: SQLAlchemy session for database access
            cache_ttl_seconds: TTL for cached prompts
            renderer: Template renderer (creates default if None)
            langfuse_label: Default Langfuse label ("production", "staging", "latest")
        """
        self.db_session = db_session
        self.cache_ttl_seconds = cache_ttl_seconds
        self.renderer = renderer or TemplateRenderer()
        self.langfuse_label = langfuse_label
        self._cache: dict[str, tuple] = {}  # (prompt, timestamp)
        self._langfuse_client = None

    # Circuit breaker: skip Langfuse for this many seconds after a failure
    _langfuse_cooldown_until: float = 0.0
    _LANGFUSE_COOLDOWN_SECONDS: float = 300.0  # 5 minutes
    _LANGFUSE_TIMEOUT_SECONDS: float = 2.0  # max wait per fetch

    def _get_langfuse_client(self):
        """Lazily initialize Langfuse client. Returns None if in cooldown."""
        if _time.time() < self._langfuse_cooldown_until:
            return None
        if self._langfuse_client is None:
            try:
                from vizu_observability_bootstrap.langfuse import (
                    LangfusePromptClient,
                    is_langfuse_enabled,
                )
                if is_langfuse_enabled():
                    self._langfuse_client = LangfusePromptClient()
                    logger.info("Langfuse prompt client initialized")
                else:
                    logger.warning("Langfuse not enabled (missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY)")
            except ImportError:
                logger.debug("vizu_observability_bootstrap not available")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
        return self._langfuse_client

    async def load(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        cliente_id: UUID | None = None,
        version: int | None = None,
        use_cache: bool = True,
        langfuse_label: str | None = None,
    ) -> LoadedPrompt:
        """
        Load and render a prompt.

        Priority:
        1. Langfuse (if enabled and prompt exists)
        2. Client-specific database prompt
        3. Global database prompt
        4. Built-in template

        Args:
            name: Prompt name (e.g., "atendente/system/v3")
            variables: Variables for template substitution
            cliente_id: Optional client ID for client-specific DB prompts
            version: Optional specific version (skips Langfuse if set)
            use_cache: Whether to use cached version
            langfuse_label: Override default Langfuse label

        Returns:
            LoadedPrompt with rendered content
        """
        import time

        variables = variables or {}
        label = langfuse_label or self.langfuse_label

        # Try cache
        cache_key = f"{name}:{cliente_id}:{version}:{label}"
        if use_cache and cache_key in self._cache:
            cached_prompt, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl_seconds:
                # Re-render with new variables
                content = self.renderer.render(cached_prompt.content, variables)
                return LoadedPrompt(
                    name=cached_prompt.name,
                    content=content,
                    version=cached_prompt.version,
                    source=cached_prompt.source,
                    category=cached_prompt.category,
                    metadata=cached_prompt.metadata,
                    loaded_at=datetime.utcnow(),
                    langfuse_label=cached_prompt.langfuse_label,
                )

        # 1. Try Langfuse first (only if no specific version requested)
        if version is None:
            langfuse_prompt = await self._load_from_langfuse(name, label)
            if langfuse_prompt:
                content = self.renderer.render(langfuse_prompt.content, variables)
                loaded = LoadedPrompt(
                    name=langfuse_prompt.name,
                    content=content,
                    version=langfuse_prompt.version,
                    source="langfuse",
                    metadata=langfuse_prompt.metadata,
                    loaded_at=datetime.utcnow(),
                    langfuse_label=label,
                )
                self._cache[cache_key] = (langfuse_prompt, time.time())
                logger.debug(f"Loaded prompt '{name}' v{langfuse_prompt.version} from Langfuse")
                return loaded

        # 2. Try database (SQLAlchemy if session available, else Supabase)
        db_prompt = None
        if self.db_session:
            db_prompt = await self._load_from_database(name, cliente_id, version)
        else:
            db_prompt = await self._load_from_supabase(name, cliente_id, version)

        if db_prompt:
            content = self.renderer.render(db_prompt.content, variables)
            loaded = LoadedPrompt(
                name=db_prompt.name,
                content=content,
                version=db_prompt.version,
                source="database",
                metadata=db_prompt.metadata,
                loaded_at=datetime.utcnow(),
            )
            self._cache[cache_key] = (db_prompt, time.time())
            return loaded

        # Fallback to builtin
        builtin = BUILTIN_TEMPLATES.get(name)
        if builtin:
            # Apply default values for optional variables
            optional_vars = builtin.get_optional_variables_dict() if hasattr(builtin, 'get_optional_variables_dict') else (builtin.optional_variables if isinstance(builtin.optional_variables, dict) else {})
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

        # Not found
        raise PromptNotFoundError(f"Prompt not found: {name}")

    async def _load_from_database(
        self,
        name: str,
        cliente_id: UUID | None,
        version: int | None,
    ) -> LoadedPrompt | None:
        """Load prompt from database via SQLAlchemy."""
        if not self.db_session:
            return None

        try:
            from sqlmodel import select

            from vizu_models import PromptTemplate

            # Try client-specific first
            if cliente_id:
                query = select(PromptTemplate).where(
                    PromptTemplate.name == name,
                    PromptTemplate.client_id == cliente_id,
                    PromptTemplate.is_active == True,
                )
                if version:
                    query = query.where(PromptTemplate.version == version)
                else:
                    query = query.order_by(PromptTemplate.version.desc())

                result = self.db_session.exec(query).first()
                if result:
                    return self._db_to_loaded(result)

            # Fallback to global
            query = select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.client_id == None,
                PromptTemplate.is_active == True,
            )
            if version:
                query = query.where(PromptTemplate.version == version)
            else:
                query = query.order_by(PromptTemplate.version.desc())

            result = self.db_session.exec(query).first()
            if result:
                return self._db_to_loaded(result)

        except Exception as e:
            logger.error(f"Error loading prompt from database: {e}")

        return None

    async def _load_from_langfuse(
        self,
        name: str,
        label: str = "production",
    ) -> LoadedPrompt | None:
        """Load prompt from Langfuse Prompt Management with timeout and circuit breaker."""
        client = self._get_langfuse_client()
        if not client:
            return None

        try:
            # Run sync Langfuse call in a thread with a short timeout
            prompt_text = await asyncio.wait_for(
                asyncio.to_thread(client.get_prompt_text, name, None, label),
                timeout=self._LANGFUSE_TIMEOUT_SECONDS,
            )
            meta = client.get_last_prompt_meta()

            return LoadedPrompt(
                name=name,
                content=prompt_text,
                version=meta.get("prompt_version", 1),
                source="langfuse",
                metadata=meta,
                loaded_at=datetime.utcnow(),
                langfuse_label=label,
            )
        except TimeoutError:
            logger.warning(f"Langfuse timeout fetching '{name}', disabling for {self._LANGFUSE_COOLDOWN_SECONDS}s")
            self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
            return None
        except Exception as e:
            logger.warning(f"Langfuse prompt '{name}' fetch failed (label={label}): {e}")
            if "Connection refused" in str(e) or "connection" in str(e).lower():
                self._langfuse_cooldown_until = _time.time() + self._LANGFUSE_COOLDOWN_SECONDS
                logger.info(f"Langfuse unreachable, disabling for {self._LANGFUSE_COOLDOWN_SECONDS}s")
            return None

    def _db_to_loaded(self, db_prompt) -> LoadedPrompt:
        """Convert database prompt to LoadedPrompt."""
        return LoadedPrompt(
            name=db_prompt.name,
            content=db_prompt.content,
            version=db_prompt.version,
            source="database",
            metadata={
                "id": str(db_prompt.id) if hasattr(db_prompt, "id") else None,
                "client_id": str(db_prompt.client_id)
                if db_prompt.client_id
                else None,
            },
        )

    async def _load_from_supabase(
        self,
        name: str,
        cliente_id: UUID | None,
        version: int | None,
    ) -> LoadedPrompt | None:
        """Load prompt from Supabase when no SQLAlchemy session available."""
        try:
            from vizu_supabase_client import get_supabase_client

            supabase = get_supabase_client()  # Singleton

            # Try client-specific first
            if cliente_id:
                query = (
                    supabase
                    .table("prompt_template")
                    .select("*")
                    .eq("name", name)
                    .eq("client_id", str(cliente_id))
                    .eq("is_active", True)
                )
                if version:
                    query = query.eq("version", version)
                else:
                    query = query.order("version", desc=True)

                response = query.limit(1).execute()
                if response.data:
                    return self._dict_to_loaded(response.data[0])

            # Fallback to global
            query = (
                supabase
                .table("prompt_template")
                .select("*")
                .eq("name", name)
                .is_("client_id", "null")
                .eq("is_active", True)
            )
            if version:
                query = query.eq("version", version)
            else:
                query = query.order("version", desc=True)

            response = query.limit(1).execute()
            if response.data:
                return self._dict_to_loaded(response.data[0])

        except ImportError:
            logger.debug("vizu_supabase_client not available for prompt loading")
        except Exception as e:
            logger.warning(f"Supabase prompt load failed: {e}")

        return None

    def _dict_to_loaded(self, data: dict) -> LoadedPrompt:
        """Convert Supabase dict to LoadedPrompt."""
        return LoadedPrompt(
            name=data.get("name", ""),
            content=data.get("content", ""),
            version=data.get("version", 1),
            source="database",
            metadata={
                "id": data.get("id"),
                "client_id": data.get("client_id"),
            },
        )

    def load_builtin(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
    ) -> LoadedPrompt:
        """
        Load a built-in prompt directly (no database lookup).

        Args:
            name: Prompt name
            variables: Variables for substitution

        Returns:
            LoadedPrompt
        """
        variables = variables or {}

        builtin = BUILTIN_TEMPLATES.get(name)
        if not builtin:
            raise PromptNotFoundError(f"Built-in prompt not found: {name}")

        optional_vars = builtin.get_optional_variables_dict() if hasattr(builtin, 'get_optional_variables_dict') else (builtin.optional_variables if isinstance(builtin.optional_variables, dict) else {})
        merged_vars = {**optional_vars, **variables}
        content = self.renderer.render(builtin.content, merged_vars)

        return LoadedPrompt(
            name=builtin.name,
            content=content,
            version=builtin.version,
            source="builtin",
            category=builtin.category,
            loaded_at=datetime.utcnow(),
        )

    def list_available(
        self,
        category: PromptCategory | None = None,
        include_db: bool = True,
    ) -> list[str]:
        """
        List available prompt names.

        Args:
            category: Filter by category
            include_db: Include database prompts

        Returns:
            List of prompt names
        """
        names = set()

        # Built-in
        for name, config in BUILTIN_TEMPLATES.items():
            if category is None or config.category == category:
                names.add(name)

        # Database
        if include_db and self.db_session:
            try:
                from sqlmodel import select

                from vizu_models import PromptTemplate

                query = select(PromptTemplate.name).where(
                    PromptTemplate.is_active == True
                ).distinct()

                for row in self.db_session.exec(query):
                    names.add(row[0] if isinstance(row, tuple) else row)

            except Exception as e:
                logger.warning(f"Error listing database prompts: {e}")

        return sorted(names)

    def clear_cache(self, name: str | None = None) -> None:
        """Clear prompt cache."""
        if name:
            keys_to_remove = [k for k in self._cache if k.startswith(name)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()


class PromptNotFoundError(Exception):
    """Prompt not found error."""
    pass
