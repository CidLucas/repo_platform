"""
Load prompts from database with fallback to built-in templates.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from vizu_prompt_management.templates import (
    BUILTIN_TEMPLATES,
    PromptTemplateConfig,
    PromptCategory,
)
from vizu_prompt_management.renderer import TemplateRenderer
from vizu_prompt_management.variables import PromptVariables

logger = logging.getLogger(__name__)


@dataclass
class LoadedPrompt:
    """A loaded and rendered prompt."""

    name: str
    content: str
    version: int = 1
    source: str = "builtin"  # "builtin", "database", "file"
    category: Optional[PromptCategory] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None

    def as_system_message(self) -> Dict[str, str]:
        """Return as OpenAI-style system message."""
        return {"role": "system", "content": self.content}

    def as_user_message(self) -> Dict[str, str]:
        """Return as OpenAI-style user message."""
        return {"role": "user", "content": self.content}


class PromptLoader:
    """
    Load prompts from various sources with caching.

    Priority:
    1. Client-specific database prompt
    2. Global database prompt
    3. Built-in template
    """

    def __init__(
        self,
        db_session: Optional[Any] = None,
        cache_ttl_seconds: int = 300,
        renderer: Optional[TemplateRenderer] = None,
    ):
        """
        Initialize PromptLoader.

        Args:
            db_session: SQLAlchemy session for database access
            cache_ttl_seconds: TTL for cached prompts
            renderer: Template renderer (creates default if None)
        """
        self.db_session = db_session
        self.cache_ttl_seconds = cache_ttl_seconds
        self.renderer = renderer or TemplateRenderer()
        self._cache: Dict[str, tuple] = {}  # (prompt, timestamp)

    async def load(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
        cliente_id: Optional[UUID] = None,
        version: Optional[int] = None,
        use_cache: bool = True,
    ) -> LoadedPrompt:
        """
        Load and render a prompt.

        Args:
            name: Prompt name (e.g., "atendente/system/v2")
            variables: Variables for template substitution
            cliente_id: Optional client ID for client-specific prompts
            version: Optional specific version
            use_cache: Whether to use cached version

        Returns:
            LoadedPrompt with rendered content
        """
        import time

        variables = variables or {}

        # Try cache
        cache_key = f"{name}:{cliente_id}:{version}"
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
                )

        # Try database first
        db_prompt = await self._load_from_database(name, cliente_id, version)
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
            merged_vars = {**builtin.optional_variables, **variables}
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
        cliente_id: Optional[UUID],
        version: Optional[int],
    ) -> Optional[LoadedPrompt]:
        """Load prompt from database."""
        if not self.db_session:
            return None

        try:
            from sqlmodel import select
            from vizu_models import PromptTemplate

            # Try client-specific first
            if cliente_id:
                query = select(PromptTemplate).where(
                    PromptTemplate.name == name,
                    PromptTemplate.cliente_vizu_id == cliente_id,
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
                PromptTemplate.cliente_vizu_id == None,
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

    def _db_to_loaded(self, db_prompt) -> LoadedPrompt:
        """Convert database prompt to LoadedPrompt."""
        return LoadedPrompt(
            name=db_prompt.name,
            content=db_prompt.content,
            version=db_prompt.version,
            source="database",
            metadata={
                "id": str(db_prompt.id) if hasattr(db_prompt, "id") else None,
                "cliente_vizu_id": str(db_prompt.cliente_vizu_id)
                if db_prompt.cliente_vizu_id
                else None,
            },
        )

    def load_builtin(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
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

        merged_vars = {**builtin.optional_variables, **variables}
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
        category: Optional[PromptCategory] = None,
        include_db: bool = True,
    ) -> List[str]:
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

    def clear_cache(self, name: Optional[str] = None) -> None:
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
