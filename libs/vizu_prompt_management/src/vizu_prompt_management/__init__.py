"""
vizu_prompt_management - Centralized prompt management for Vizu services.

This library provides:
- Prompt loading from Langfuse (primary) or database (fallback)
- Variable substitution with Jinja2
- Client-specific overrides
- MCP integration
- Unified dynamic prompt building

NOTE: Prompt versioning and A/B testing are managed via Langfuse UI.
"""

__version__ = "0.1.0"

# Templates are exposed as module
from vizu_prompt_management import templates
from vizu_prompt_management.loader import LoadedPrompt, PromptLoader

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
    "build_prompt_sync",
    "build_tools_description",
    "filter_prompt_tools",
    "format_horario",
    "get_prompt_loader",
]
