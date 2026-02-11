# vizu_prompt_management/dynamic_builder.py
"""
Unified Dynamic Prompt Builder

Single entry point for building all prompt types dynamically:
- Agent system prompts (atendente, orchestrator, etc.)
- Text-to-SQL prompts
- Task-specific prompts (RAG, elicitation, etc.)

Architecture (simplified):
1. Langfuse as source of truth (version control, A/B testing via labels)
2. Builtin templates as fallback
3. Redis caching via ContextService (optional)
4. Variables injected from SafeContext fields via {{}} syntax

Key changes:
- Removed cliente_id parameter (no per-client prompts in DB)
- Context is injected via variables (company_profile, nome_empresa, etc.)
- Added build_prompt_full() for access to LoadedPrompt + langfuse_prompt
"""

import logging
from typing import TYPE_CHECKING, Any

from vizu_prompt_management.loader import LoadedPrompt, PromptLoader
from vizu_prompt_management.variables import VariableExtractor

if TYPE_CHECKING:
    from vizu_context_service import ContextService

logger = logging.getLogger(__name__)

# =============================================================================
# SINGLETON PROMPT LOADER
# =============================================================================

_prompt_loader: PromptLoader | None = None


def _get_prompt_loader() -> PromptLoader:
    """Get singleton PromptLoader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader(cache_ttl_seconds=300)
        logger.info("PromptLoader singleton created")
    return _prompt_loader


def get_prompt_loader() -> PromptLoader:
    """
    Public accessor for singleton PromptLoader.

    Use this when you need to access the loader directly.
    """
    return _get_prompt_loader()


# =============================================================================
# UNIFIED PROMPT BUILDER
# =============================================================================


async def build_prompt(
    name: str,
    variables: dict[str, Any],
    context_service: "ContextService | None" = None,
    langfuse_label: str | None = None,
) -> str:
    """
    Build any prompt dynamically using the unified loading system.

    This is the single entry point for all prompt building across the platform.
    It handles:
    - Langfuse lookup (primary source of truth)
    - Builtin fallback
    - Redis caching via ContextService (if provided)
    - Variable substitution via Langfuse's {{variable}} syntax

    Args:
        name: Prompt template name (e.g., "atendente/default", "text_to_sql/system")
        variables: Variables for template rendering (from SafeContext fields)
        context_service: Optional ContextService for Redis caching
        langfuse_label: Override default Langfuse label ("production", "staging")

    Returns:
        Rendered prompt content

    Example:
        # Agent system prompt
        content = await build_prompt(
            name="atendente/default",
            variables={"nome_empresa": "Acme", "tools_description": "..."},
            context_service=ctx_service,
        )

        # Text-to-SQL prompt
        content = await build_prompt(
            name="text_to_sql/system/v1",
            variables={"schema_snapshot": "...", "role": "analyst"},
        )
    """
    loader = _get_prompt_loader()

    # Use context_service for Redis caching if available
    if context_service:
        try:
            content = await context_service.get_cached_prompt(
                name=name,
                loader=loader,
                variables=variables,
                langfuse_label=langfuse_label,
            )
            logger.debug(f"Loaded prompt '{name}' via ContextService (Redis cache)")
            return content
        except Exception as e:
            logger.warning(f"Context service prompt load failed for '{name}': {e}")

    # Direct load (no Redis cache)
    try:
        loaded = await loader.load(
            name=name,
            variables=variables,
            langfuse_label=langfuse_label,
        )
        logger.debug(f"Loaded prompt '{name}' directly via PromptLoader (source={loaded.source})")
        return loaded.content
    except Exception as e:
        logger.warning(f"Async load failed for '{name}': {e}, trying builtin")
        # Final fallback: builtin template
        try:
            return loader.load_builtin(name, variables).content
        except Exception as builtin_err:
            logger.error(f"Builtin fallback also failed for '{name}': {builtin_err}")
            raise


async def build_prompt_full(
    name: str,
    variables: dict[str, Any],
    context_service: "ContextService | None" = None,
    langfuse_label: str | None = None,
) -> LoadedPrompt:
    """
    Build prompt and return full LoadedPrompt object.

    Use this when you need access to:
    - langfuse_prompt object for trace linking
    - Prompt metadata (version, source, etc.)

    Args:
        name: Prompt template name
        variables: Variables for template rendering
        context_service: Optional ContextService for Redis caching
        langfuse_label: Override default Langfuse label

    Returns:
        LoadedPrompt with content and metadata

    Example:
        loaded = await build_prompt_full(
            name="atendente/default",
            variables={"nome_empresa": "Acme"},
        )
        # Use loaded.langfuse_prompt for trace linking
        # Use loaded.get_trace_metadata() for callbacks
    """
    loader = _get_prompt_loader()

    # Note: ContextService caching returns just the string, so we bypass it here
    # to get the full LoadedPrompt with langfuse_prompt object
    try:
        loaded = await loader.load(
            name=name,
            variables=variables,
            langfuse_label=langfuse_label,
        )
        logger.debug(f"Loaded prompt '{name}' (source={loaded.source}, version={loaded.version})")
        return loaded
    except Exception as e:
        logger.warning(f"Async load failed for '{name}': {e}, trying builtin")
        return loader.load_builtin(name, variables)


def build_prompt_sync(
    name: str,
    variables: dict[str, Any],
) -> str:
    """
    Synchronous version for contexts where async is not available.

    Uses builtin templates only (no Langfuse lookup, no caching).
    Prefer async build_prompt() whenever possible.

    Args:
        name: Prompt template name
        variables: Variables for rendering

    Returns:
        Rendered prompt content
    """
    loader = _get_prompt_loader()
    return loader.load_builtin(name, variables).content


# =============================================================================
# HELPER FUNCTIONS FOR COMMON PATTERNS
# =============================================================================


def filter_prompt_tools(prompt_base: str, available_tool_names: set[str]) -> str:
    """
    Filter tool references in prompt_base to only include enabled tools.

    This prevents the LLM from trying to use tools that are mentioned in the
    prompt but not actually available/enabled for the client.

    Args:
        prompt_base: The client's custom prompt
        available_tool_names: Set of tool names actually available

    Returns:
        Filtered prompt with unavailable tool sections removed
    """
    if not prompt_base:
        return ""

    # Deprecated tools that should always be removed from prompts
    deprecated_tools = {"query_database_text_to_sql"}

    # Active SQL tool
    sql_tools = {"executar_sql_agent"}

    lines = prompt_base.split('\n')
    filtered_lines = []
    skip_until_next_section = False

    for line in lines:
        # Always skip lines mentioning deprecated tools
        if any(tool in line for tool in deprecated_tools):
            skip_until_next_section = True
            continue

        # Skip SQL tool lines if not enabled
        if any(tool in line for tool in sql_tools) and not (sql_tools & available_tool_names):
            skip_until_next_section = True
            continue

        # Reset skip flag on new section headers
        if line.strip().startswith('###') or line.strip().startswith('##'):
            skip_until_next_section = False

        if not skip_until_next_section:
            filtered_lines.append(line)

    result = '\n'.join(filtered_lines)

    if result != prompt_base:
        logger.debug("Filtered unavailable/deprecated tools from prompt_base")

    return result


def build_tools_description(
    available_tools: list,
    tool_registry: Any | None = None,
) -> str:
    """
    Build formatted tool descriptions for prompt injection.

    Delegates to VariableExtractor.build_tools_description().

    Args:
        available_tools: List of tools (BaseTool objects or names)
        tool_registry: Optional ToolRegistry for descriptions

    Returns:
        Formatted tool descriptions string
    """
    return VariableExtractor.build_tools_description(available_tools, tool_registry)
