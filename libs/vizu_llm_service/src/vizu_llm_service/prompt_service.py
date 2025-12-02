# vizu_llm_service/prompt_service.py
"""
Prompt Management Service - Langfuse-First with Local Fallback.

Architecture:
1. PRIMARY: Fetch prompts from Langfuse Prompt Management
2. CACHE: Store "production" (latest label) prompts in local DB
3. FALLBACK: Use cached prompts if Langfuse is unavailable

This ensures:
- Version control and A/B testing via Langfuse UI
- High availability with local cache
- No code deploys needed for prompt updates
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# MODELS
# ============================================================================

class PromptConfig(BaseModel):
    """Configuration returned with a prompt."""
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class FetchedPrompt(BaseModel):
    """A prompt fetched from Langfuse or cache."""
    name: str
    version: int
    content: str  # The prompt text (may have {{variables}})
    config: Optional[PromptConfig] = None
    labels: List[str] = []
    source: str = "langfuse"  # "langfuse" or "cache"
    fetched_at: datetime = datetime.utcnow()

    def compile(self, **variables) -> str:
        """
        Compile prompt with variables.

        Replaces {{variable}} placeholders with provided values.
        """
        result = self.content
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def to_messages(self, **variables) -> List[Dict[str, str]]:
        """
        Compile and return as chat messages.

        Assumes content is a system prompt.
        """
        return [{"role": "system", "content": self.compile(**variables)}]


# ============================================================================
# LANGFUSE CLIENT WRAPPER
# ============================================================================

class LangfusePromptClient:
    """
    Wrapper for Langfuse prompt management.

    Uses the Langfuse Python SDK to fetch prompts.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self._client = None
        self._public_key = public_key
        self._secret_key = secret_key
        self._host = host

    @property
    def client(self):
        """Lazy initialization of Langfuse client."""
        if self._client is None:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=self._public_key,
                    secret_key=self._secret_key,
                    host=self._host,
                )
                logger.info(f"Langfuse client initialized: {self._host}")
            except ImportError:
                logger.error("langfuse package not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {e}")
                raise

        return self._client

    def get_prompt(
        self,
        name: str,
        version: Optional[int] = None,
        label: Optional[str] = None,
    ) -> Optional[FetchedPrompt]:
        """
        Fetch a prompt from Langfuse.

        Args:
            name: Prompt name (e.g., "atendente/system")
            version: Specific version (optional)
            label: Label like "production" or "staging" (optional)

        Returns:
            FetchedPrompt or None if not found
        """
        try:
            # Build kwargs for get_prompt
            kwargs = {}
            if version is not None:
                kwargs["version"] = version
            if label is not None:
                kwargs["label"] = label

            prompt = self.client.get_prompt(name, **kwargs)

            # Extract config if available
            config = None
            if hasattr(prompt, "config") and prompt.config:
                config = PromptConfig(
                    model=prompt.config.get("model"),
                    temperature=prompt.config.get("temperature"),
                    max_tokens=prompt.config.get("max_tokens"),
                    extra={
                        k: v for k, v in prompt.config.items()
                        if k not in ("model", "temperature", "max_tokens")
                    },
                )

            # Get labels
            labels = getattr(prompt, "labels", []) or []

            return FetchedPrompt(
                name=name,
                version=prompt.version,
                content=prompt.prompt if hasattr(prompt, "prompt") else str(prompt),
                config=config,
                labels=labels,
                source="langfuse",
                fetched_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"Failed to fetch prompt '{name}' from Langfuse: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Langfuse is reachable."""
        try:
            # Simple health check - try to get any prompt
            self.client.auth_check()
            return True
        except Exception:
            return False


# ============================================================================
# LOCAL CACHE (DATABASE)
# ============================================================================

class PromptCacheDB:
    """
    Local database cache for prompts.

    Stores the "production" version of prompts locally for fallback.
    Uses the existing PromptTemplate model.
    """

    def __init__(self, db_session):
        """
        Initialize with async database session.

        Args:
            db_session: SQLModel async session
        """
        self.db = db_session

    async def get(
        self,
        name: str,
        cliente_vizu_id: Optional[str] = None,
    ) -> Optional[FetchedPrompt]:
        """
        Get cached prompt from local database.

        Args:
            name: Prompt name
            cliente_vizu_id: Optional client ID for client-specific prompts

        Returns:
            FetchedPrompt or None
        """
        try:
            from sqlmodel import select
            from vizu_models import PromptTemplate

            # Build query - get latest active version
            stmt = select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.is_active.is_(True),
            )

            if cliente_vizu_id:
                import uuid
                stmt = stmt.where(
                    PromptTemplate.cliente_vizu_id == uuid.UUID(cliente_vizu_id)
                )
            else:
                stmt = stmt.where(PromptTemplate.cliente_vizu_id.is_(None))

            stmt = stmt.order_by(PromptTemplate.version.desc()).limit(1)

            result = await self.db.exec(stmt)
            template = result.first()

            if template:
                return FetchedPrompt(
                    name=template.name,
                    version=template.version,
                    content=template.content,
                    config=PromptConfig(extra=template.variables) if template.variables else None,
                    labels=template.tags or [],
                    source="cache",
                    fetched_at=template.updated_at,
                )

            return None

        except Exception as e:
            logger.error(f"Error fetching cached prompt '{name}': {e}")
            return None

    async def upsert(
        self,
        prompt: FetchedPrompt,
        cliente_vizu_id: Optional[str] = None,
    ) -> bool:
        """
        Insert or update a prompt in the cache.

        This is called when we successfully fetch from Langfuse
        to keep the local cache in sync.

        Args:
            prompt: The fetched prompt to cache
            cliente_vizu_id: Optional client ID

        Returns:
            True if successful
        """
        try:
            from sqlmodel import select
            from vizu_models import PromptTemplate
            import uuid

            # Check if prompt with this name and version exists
            stmt = select(PromptTemplate).where(
                PromptTemplate.name == prompt.name,
                PromptTemplate.version == prompt.version,
            )

            if cliente_vizu_id:
                stmt = stmt.where(
                    PromptTemplate.cliente_vizu_id == uuid.UUID(cliente_vizu_id)
                )
            else:
                stmt = stmt.where(PromptTemplate.cliente_vizu_id.is_(None))

            result = await self.db.exec(stmt)
            existing = result.first()

            if existing:
                # Update content if changed
                existing.content = prompt.content
                existing.tags = prompt.labels
                existing.updated_at = datetime.utcnow()
                if prompt.config:
                    existing.variables = prompt.config.model_dump() if prompt.config else None
            else:
                # Create new
                template = PromptTemplate(
                    name=prompt.name,
                    version=prompt.version,
                    content=prompt.content,
                    tags=prompt.labels,
                    is_active=True,
                    variables=prompt.config.model_dump() if prompt.config else None,
                    cliente_vizu_id=uuid.UUID(cliente_vizu_id) if cliente_vizu_id else None,
                    created_by="langfuse_sync",
                )
                self.db.add(template)

            await self.db.commit()
            logger.debug(f"Cached prompt '{prompt.name}' v{prompt.version}")
            return True

        except Exception as e:
            logger.error(f"Error caching prompt '{prompt.name}': {e}")
            return False


# ============================================================================
# PROMPT SERVICE (MAIN API)
# ============================================================================

class PromptService:
    """
    Main Prompt Service - Langfuse-First with Local Fallback.

    Usage:
        # Initialize
        service = PromptService(db_session)

        # Get a prompt
        prompt = await service.get_prompt("atendente/system")

        # Compile with variables
        text = prompt.compile(client_name="Studio J", context="...")

        # Or get as messages
        messages = prompt.to_messages(client_name="Studio J")
    """

    # In-memory cache TTL
    MEMORY_CACHE_TTL = timedelta(minutes=5)

    def __init__(
        self,
        db_session=None,
        langfuse_client: Optional[LangfusePromptClient] = None,
        cache_to_db: bool = True,
    ):
        """
        Initialize the prompt service.

        Args:
            db_session: SQLModel async session (for local cache)
            langfuse_client: Optional pre-configured Langfuse client
            cache_to_db: Whether to sync fetched prompts to local DB
        """
        self.db = db_session
        self._langfuse = langfuse_client
        self.cache_to_db = cache_to_db
        self._db_cache = PromptCacheDB(db_session) if db_session else None

        # In-memory cache: {cache_key: (FetchedPrompt, expires_at)}
        self._memory_cache: Dict[str, tuple[FetchedPrompt, datetime]] = {}

    @property
    def langfuse(self) -> Optional[LangfusePromptClient]:
        """Lazy initialization of Langfuse client."""
        if self._langfuse is None:
            try:
                from .config import get_llm_settings
                settings = get_llm_settings()

                if settings.langfuse_enabled:
                    self._langfuse = LangfusePromptClient(
                        public_key=settings.LANGFUSE_PUBLIC_KEY,
                        secret_key=settings.LANGFUSE_SECRET_KEY,
                        host=settings.LANGFUSE_HOST,
                    )
                else:
                    logger.warning("Langfuse not configured, using cache-only mode")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")

        return self._langfuse

    def _cache_key(
        self,
        name: str,
        version: Optional[int] = None,
        label: Optional[str] = None,
        cliente_vizu_id: Optional[str] = None,
    ) -> str:
        """Generate cache key for a prompt."""
        parts = [name]
        if version:
            parts.append(f"v{version}")
        if label:
            parts.append(f"@{label}")
        if cliente_vizu_id:
            parts.append(f"#{cliente_vizu_id[:8]}")
        return ":".join(parts)

    async def get_prompt(
        self,
        name: str,
        version: Optional[int] = None,
        label: str = "production",
        cliente_vizu_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> Optional[FetchedPrompt]:
        """
        Get a prompt with Langfuse-first, local fallback strategy.

        Priority:
        1. Memory cache (if not expired)
        2. Langfuse API
        3. Local database cache

        Args:
            name: Prompt name (e.g., "atendente/system")
            version: Specific version (overrides label)
            label: Label to fetch (default: "production")
            cliente_vizu_id: Optional client ID for client-specific prompts
            use_cache: Whether to use memory cache

        Returns:
            FetchedPrompt or None if not found anywhere
        """
        cache_key = self._cache_key(name, version, label, cliente_vizu_id)

        # 1. Check memory cache
        if use_cache and cache_key in self._memory_cache:
            prompt, expires_at = self._memory_cache[cache_key]
            if datetime.utcnow() < expires_at:
                logger.debug(f"Prompt '{name}' from memory cache")
                return prompt
            else:
                del self._memory_cache[cache_key]

        # 2. Try Langfuse
        prompt = None
        if self.langfuse:
            prompt = self.langfuse.get_prompt(
                name=name,
                version=version,
                label=None if version else label,
            )

            if prompt:
                logger.info(f"Prompt '{name}' v{prompt.version} fetched from Langfuse")

                # Cache to memory
                self._memory_cache[cache_key] = (
                    prompt,
                    datetime.utcnow() + self.MEMORY_CACHE_TTL,
                )

                # Cache to database (async, for fallback)
                if self.cache_to_db and self._db_cache:
                    await self._db_cache.upsert(prompt, cliente_vizu_id)

                return prompt

        # 3. Fallback to local database cache
        if self._db_cache:
            prompt = await self._db_cache.get(name, cliente_vizu_id)
            if prompt:
                logger.warning(
                    f"Prompt '{name}' from LOCAL CACHE (Langfuse unavailable)"
                )
                # Cache to memory
                self._memory_cache[cache_key] = (
                    prompt,
                    datetime.utcnow() + self.MEMORY_CACHE_TTL,
                )
                return prompt

        logger.error(f"Prompt '{name}' not found in Langfuse or cache")
        return None

    async def get_prompt_or_default(
        self,
        name: str,
        default_content: str,
        **kwargs,
    ) -> FetchedPrompt:
        """
        Get a prompt with a hardcoded fallback.

        Useful for bootstrapping when prompts aren't yet in Langfuse.

        Args:
            name: Prompt name
            default_content: Fallback prompt content
            **kwargs: Additional args for get_prompt

        Returns:
            FetchedPrompt (always returns something)
        """
        prompt = await self.get_prompt(name, **kwargs)

        if prompt:
            return prompt

        # Return default
        logger.warning(f"Using hardcoded default for prompt '{name}'")
        return FetchedPrompt(
            name=name,
            version=0,
            content=default_content,
            source="default",
        )

    async def sync_production_prompts(
        self,
        prompt_names: List[str],
    ) -> Dict[str, bool]:
        """
        Sync all production prompts from Langfuse to local cache.

        Call this periodically (e.g., on startup, via cron) to ensure
        the local cache has the latest production prompts.

        Args:
            prompt_names: List of prompt names to sync

        Returns:
            Dict mapping prompt name to sync success
        """
        results = {}

        for name in prompt_names:
            try:
                prompt = await self.get_prompt(
                    name=name,
                    label="production",
                    use_cache=False,  # Force fetch from Langfuse
                )
                results[name] = prompt is not None
            except Exception as e:
                logger.error(f"Failed to sync prompt '{name}': {e}")
                results[name] = False

        synced = sum(1 for v in results.values() if v)
        logger.info(f"Synced {synced}/{len(prompt_names)} prompts to local cache")

        return results

    def clear_memory_cache(self):
        """Clear the in-memory prompt cache."""
        self._memory_cache.clear()
        logger.info("Memory cache cleared")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_prompt_service: Optional[PromptService] = None


def get_prompt_service(db_session=None) -> PromptService:
    """
    Get or create the global prompt service instance.

    Args:
        db_session: Optional database session

    Returns:
        PromptService singleton
    """
    global _prompt_service

    if _prompt_service is None:
        _prompt_service = PromptService(db_session=db_session)

    return _prompt_service


async def get_prompt(
    name: str,
    db_session=None,
    **kwargs,
) -> Optional[FetchedPrompt]:
    """
    Convenience function to get a prompt.

    Args:
        name: Prompt name
        db_session: Optional database session
        **kwargs: Additional args for PromptService.get_prompt

    Returns:
        FetchedPrompt or None
    """
    service = get_prompt_service(db_session)
    return await service.get_prompt(name, **kwargs)
