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

from vizu_prompt_management.loader import PromptLoader, LoadedPrompt
from vizu_prompt_management.manager import PromptManager, PromptVersion
from vizu_prompt_management.variables import VariableExtractor, PromptVariables
from vizu_prompt_management.renderer import TemplateRenderer

# Templates are exposed as module
from vizu_prompt_management import templates

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
    # Renderer
    "TemplateRenderer",
    # Templates module
    "templates",
]
