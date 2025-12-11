"""
Jinja2-based template rendering with safety features.
"""

import logging
import re
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, select_autoescape

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Render prompt templates with variable substitution.

    Supports:
    - Jinja2 syntax ({{ variable }}, {% if %}, {% for %})
    - Simple placeholder syntax ({variable})
    - Safe rendering with undefined variable handling
    """

    def __init__(
        self,
        autoescape: bool = False,
        undefined_behavior: str = "empty",
    ):
        """
        Initialize renderer.

        Args:
            autoescape: Whether to autoescape HTML (default False for prompts)
            undefined_behavior: How to handle undefined variables:
                - "empty": Replace with empty string
                - "keep": Keep the placeholder
                - "error": Raise error
        """
        self.undefined_behavior = undefined_behavior

        # Configure Jinja2 environment
        if undefined_behavior == "empty":
            from jinja2 import Undefined
            undefined_class = Undefined
        elif undefined_behavior == "keep":
            from jinja2 import DebugUndefined
            undefined_class = DebugUndefined
        else:
            from jinja2 import StrictUndefined
            undefined_class = StrictUndefined

        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape() if autoescape else False,
            undefined=undefined_class,
        )

    def render(
        self,
        template: str,
        variables: dict[str, Any],
        strict: bool = False,
    ) -> str:
        """
        Render a template with variables.

        Args:
            template: Template string (Jinja2 or simple format)
            variables: Variables to substitute
            strict: If True, raise error on missing variables

        Returns:
            Rendered string
        """
        if not template:
            return ""

        # Try Jinja2 first
        try:
            jinja_template = self.env.from_string(template)
            return jinja_template.render(**variables)
        except TemplateSyntaxError:
            # Fall back to simple substitution
            return self._simple_render(template, variables, strict)
        except Exception as e:
            if strict:
                raise
            logger.warning(f"Template rendering error: {e}")
            return self._simple_render(template, variables, strict)

    def _simple_render(
        self,
        template: str,
        variables: dict[str, Any],
        strict: bool,
    ) -> str:
        """Simple {variable} substitution fallback."""
        result = template

        for key, value in variables.items():
            # Replace {key} and {{key}}
            result = result.replace(f"{{{{{key}}}}}", str(value))
            result = result.replace(f"{{{key}}}", str(value))

        # Handle remaining placeholders
        if strict:
            remaining = re.findall(r'\{(\w+)\}', result)
            if remaining:
                raise ValueError(f"Missing variables: {remaining}")

        return result

    def extract_variables(self, template: str) -> set[str]:
        """
        Extract variable names from a template.

        Args:
            template: Template string

        Returns:
            Set of variable names
        """
        variables = set()

        # Jinja2 style: {{ variable }}
        jinja_vars = re.findall(r'\{\{\s*(\w+)\s*\}\}', template)
        variables.update(jinja_vars)

        # Simple style: {variable}
        simple_vars = re.findall(r'\{(\w+)\}', template)
        variables.update(simple_vars)

        # Jinja2 block variables: {% for item in items %}
        block_vars = re.findall(r'\{%\s*for\s+\w+\s+in\s+(\w+)\s*%\}', template)
        variables.update(block_vars)

        # Jinja2 if conditions: {% if variable %}
        if_vars = re.findall(r'\{%\s*if\s+(\w+)\s*%\}', template)
        variables.update(if_vars)

        return variables

    def validate_template(self, template: str) -> list[str]:
        """
        Validate template syntax.

        Args:
            template: Template string

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        try:
            self.env.from_string(template)
        except TemplateSyntaxError as e:
            errors.append(f"Jinja2 syntax error: {e}")

        # Check for unclosed braces
        open_braces = template.count('{') - template.count('{{')
        close_braces = template.count('}') - template.count('}}')

        if open_braces != close_braces:
            errors.append("Mismatched braces in template")

        return errors


class SafeRenderer(TemplateRenderer):
    """
    Renderer with additional safety features.

    - Limits template size
    - Limits variable depth
    - Sanitizes output
    """

    def __init__(
        self,
        max_template_size: int = 50000,
        max_output_size: int = 100000,
        max_variable_depth: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_template_size = max_template_size
        self.max_output_size = max_output_size
        self.max_variable_depth = max_variable_depth

    def render(
        self,
        template: str,
        variables: dict[str, Any],
        strict: bool = False,
    ) -> str:
        """Render with safety checks."""
        # Check template size
        if len(template) > self.max_template_size:
            raise ValueError(f"Template exceeds max size of {self.max_template_size}")

        # Flatten deep variables
        safe_variables = self._flatten_variables(variables)

        # Render
        result = super().render(template, safe_variables, strict)

        # Check output size
        if len(result) > self.max_output_size:
            logger.warning(f"Output truncated from {len(result)} to {self.max_output_size}")
            result = result[:self.max_output_size] + "..."

        return result

    def _flatten_variables(
        self,
        variables: dict[str, Any],
        prefix: str = "",
        depth: int = 0,
    ) -> dict[str, Any]:
        """Flatten nested variables up to max depth."""
        if depth > self.max_variable_depth:
            return {}

        result = {}
        for key, value in variables.items():
            full_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict) and depth < self.max_variable_depth:
                nested = self._flatten_variables(
                    value,
                    f"{full_key}_",
                    depth + 1,
                )
                result.update(nested)
                result[full_key] = value
            else:
                result[full_key] = value

        return result
