"""
vizu_prompt_management - Simplified prompt management for Vizu services.

Architecture (simplified):
1. Langfuse as source of truth (version control, A/B testing via labels)
2. Builtin templates as fallback
3. Variables injected from SafeContext fields via {{}} syntax

Key features:
- Prompt loading from Langfuse (primary) with builtin fallback
- Variable substitution with Jinja2 (for builtin) or {{}} (for Langfuse)
- Redis caching via ContextService
- Unified dynamic prompt building

NOTE: Prompt versioning and A/B testing are managed via Langfuse UI.
Client-specific prompts are achieved via variable injection, not DB overrides.
"""

__version__ = "0.2.0"

# Templates are exposed as module
from vizu_prompt_management import templates
from vizu_prompt_management.loader import LoadedPrompt, PromptLoader, PromptNotFoundError
from vizu_prompt_management.renderer import TemplateRenderer
from vizu_prompt_management.templates import (
    BUILTIN_TEMPLATES,
    METADATA_ENRICHMENT_PROMPT,
    RAG_RERANK_PROMPT,
    RAG_TOOL_PROMPT,
    SQL_AGENT_PREFIX,
    SQL_AGENT_SUFFIX,
    get_builtin_template,
    list_builtin_templates,
)
from vizu_prompt_management.variables import (
    ContextVariableBuilder,
    PromptVariables,
    VariableExtractor,
)

# Unified dynamic prompt building
from vizu_prompt_management.dynamic_builder import (
    build_prompt,
    build_prompt_full,
    build_prompt_sync,
    build_tools_description,
    filter_prompt_tools,
    get_prompt_loader,
)

__all__ = [
    "__version__",
    # Loader
    "PromptLoader",
    "LoadedPrompt",
    "PromptNotFoundError",
    # Variables
    "VariableExtractor",
    "PromptVariables",
    "ContextVariableBuilder",
    # Renderer
    "TemplateRenderer",
    # Templates module
    "templates",
    # Template registry
    "BUILTIN_TEMPLATES",
    "get_builtin_template",
    "list_builtin_templates",
    # Tool prompts (commonly used)
    "SQL_AGENT_PREFIX",
    "SQL_AGENT_SUFFIX",
    "RAG_TOOL_PROMPT",
    "RAG_RERANK_PROMPT",
    "METADATA_ENRICHMENT_PROMPT",
    # Unified Dynamic Builder
    "build_prompt",
    "build_prompt_full",
    "build_prompt_sync",
    "build_tools_description",
    "filter_prompt_tools",
    "get_prompt_loader",
]
