"""
vizu_prompt_management - Centralized prompt management for Vizu services.

This library provides:
- Prompt loading from database and files
- Versioning and A/B testing
- Variable substitution with Jinja2
- Client-specific overrides
- MCP integration
"""

__version__ = "0.1.0"

# Templates are exposed as module
from vizu_prompt_management import templates
from vizu_prompt_management.loader import LoadedPrompt, PromptLoader
from vizu_prompt_management.manager import PromptManager, PromptVersion

# Phase 1: Text-to-SQL prompt building
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

__all__ = [
    "__version__",
    # Loader
    "PromptLoader",
    "LoadedPrompt",
    # Manager
    "PromptManager",
    "PromptVersion",
    # Variables
    "VariableExtractor",
    "PromptVariables",
    "ContextVariableBuilder",
    # Renderer
    "TemplateRenderer",
    # Templates module
    "templates",
    # Phase 1: Text-to-SQL
    "TextToSqlPromptBuilder",
    "TextToSqlPromptContext",
    "get_prompt_builder",
]
