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

# Phase 1: Text-to-SQL prompt building (legacy - consider using dynamic_builder)
from vizu_prompt_management.prompt_builder import (
    TextToSqlPromptBuilder,
    TextToSqlPromptContext,
    get_prompt_builder,
)
from vizu_prompt_management.renderer import TemplateRenderer
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
    format_horario,
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
    # Phase 1: Text-to-SQL (legacy)
    "TextToSqlPromptBuilder",
    "TextToSqlPromptContext",
    "get_prompt_builder",
    # Unified Dynamic Builder
    "build_prompt",
    "build_prompt_full",
    "build_prompt_sync",
    "build_tools_description",
    "filter_prompt_tools",
    "format_horario",
    "get_prompt_loader",
]
