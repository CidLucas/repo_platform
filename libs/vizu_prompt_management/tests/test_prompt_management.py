"""
Tests for vizu_prompt_management library.
"""


import pytest

from vizu_prompt_management.loader import LoadedPrompt, PromptLoader, PromptNotFoundError
from vizu_prompt_management.manager import PromptVersion
from vizu_prompt_management.renderer import SafeRenderer, TemplateRenderer
from vizu_prompt_management.templates import (
    ATENDENTE_SYSTEM_V1,
    BUILTIN_TEMPLATES,
    PromptCategory,
    get_builtin_template,
    list_builtin_templates,
)
from vizu_prompt_management.variables import (
    ContextVariableBuilder,
    PromptVariables,
    VariableExtractor,
)


class TestTemplates:
    """Tests for built-in templates."""

    def test_builtin_templates_exist(self):
        """Test that all expected templates exist."""
        assert "atendente/system/v1" in BUILTIN_TEMPLATES
        assert "atendente/system/v2" in BUILTIN_TEMPLATES
        assert "rag/query" in BUILTIN_TEMPLATES

    def test_template_structure(self):
        """Test template configuration structure."""
        assert ATENDENTE_SYSTEM_V1.name == "atendente/system/v1"
        assert ATENDENTE_SYSTEM_V1.category == PromptCategory.SYSTEM
        assert "nome_empresa" in ATENDENTE_SYSTEM_V1.required_variables
        assert len(ATENDENTE_SYSTEM_V1.content) > 0

    def test_get_builtin_template(self):
        """Test get_builtin_template function."""
        template = get_builtin_template("atendente/system/v1")
        assert template is not None
        assert template.name == "atendente/system/v1"

        missing = get_builtin_template("nonexistent")
        assert missing is None

    def test_list_builtin_templates(self):
        """Test list_builtin_templates function."""
        all_templates = list_builtin_templates()
        assert len(all_templates) > 0

        system_templates = list_builtin_templates(PromptCategory.SYSTEM)
        assert all(t.category == PromptCategory.SYSTEM for t in system_templates)


class TestRenderer:
    """Tests for template renderer."""

    def test_jinja2_render_simple(self):
        """Test simple Jinja2 rendering."""
        renderer = TemplateRenderer()
        result = renderer.render("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_jinja2_render_conditional(self):
        """Test Jinja2 conditional rendering."""
        renderer = TemplateRenderer()
        template = "{% if show %}Visible{% endif %}"

        result_show = renderer.render(template, {"show": True})
        assert result_show == "Visible"

        result_hide = renderer.render(template, {"show": False})
        assert result_hide == ""

    def test_jinja2_render_loop(self):
        """Test Jinja2 loop rendering."""
        renderer = TemplateRenderer()
        template = "{% for item in items %}{{ item }} {% endfor %}"

        result = renderer.render(template, {"items": ["a", "b", "c"]})
        assert result == "a b c "

    def test_simple_placeholder_render(self):
        """Test simple {placeholder} rendering."""
        renderer = TemplateRenderer()
        result = renderer.render("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_undefined_variable_empty(self):
        """Test undefined variable handling with empty behavior."""
        renderer = TemplateRenderer(undefined_behavior="empty")
        result = renderer.render("Hello {{ name }}!", {})
        assert result == "Hello !"

    def test_extract_variables(self):
        """Test variable extraction from template."""
        renderer = TemplateRenderer()

        variables = renderer.extract_variables("Hello {{ name }} and {{ title }}")
        assert "name" in variables
        assert "title" in variables

    def test_validate_template_valid(self):
        """Test template validation for valid template."""
        renderer = TemplateRenderer()
        errors = renderer.validate_template("Hello {{ name }}!")
        assert len(errors) == 0

    def test_validate_template_invalid(self):
        """Test template validation for invalid template."""
        renderer = TemplateRenderer()
        errors = renderer.validate_template("Hello {% if name %}")
        assert len(errors) > 0


class TestSafeRenderer:
    """Tests for safe renderer."""

    def test_max_template_size(self):
        """Test template size limit."""
        renderer = SafeRenderer(max_template_size=100)

        with pytest.raises(ValueError) as exc_info:
            renderer.render("x" * 200, {})
        assert "max size" in str(exc_info.value)

    def test_max_output_size(self):
        """Test output size truncation."""
        renderer = SafeRenderer(max_output_size=50)

        template = "{{ content }}"
        result = renderer.render(template, {"content": "x" * 100})
        assert len(result) <= 53  # 50 + "..."


class TestVariables:
    """Tests for variable extraction."""

    def test_prompt_variables_to_dict(self):
        """Test PromptVariables.to_dict()."""
        variables = PromptVariables(
            nome_empresa="Test Corp",
            tier="PROFISSIONAL",
        )

        result = variables.to_dict()
        assert result["nome_empresa"] == "Test Corp"
        assert result["tier"] == "PROFISSIONAL"

    def test_prompt_variables_set_custom(self):
        """Test setting custom variables."""
        variables = PromptVariables()
        variables.set("custom_key", "custom_value")

        result = variables.to_dict()
        assert result["custom_key"] == "custom_value"

    def test_extractor_from_dict(self):
        """Test extracting from dictionary."""
        data = {
            "nome_empresa": "Test Corp",
            "prompt_base": "Custom prompt",
            "tier": "PREMIUM",
        }

        variables = VariableExtractor.from_dict(data)
        assert variables.nome_empresa == "Test Corp"
        assert variables.prompt_personalizado == "Custom prompt"
        assert variables.tier == "PREMIUM"

    def test_format_horarios(self):
        """Test business hours formatting."""
        horarios = {
            "segunda": {"abertura": "09:00", "fechamento": "18:00"},
            "terça": {"abertura": "09:00", "fechamento": "18:00"},
        }

        formatted = VariableExtractor._format_horarios(horarios)
        assert "Segunda" in formatted
        assert "09:00" in formatted
        assert "18:00" in formatted

    def test_format_horarios_empty(self):
        """Test formatting empty hours."""
        formatted = VariableExtractor._format_horarios(None)
        assert "não configurado" in formatted.lower()


class TestContextVariableBuilder:
    """Tests for fluent variable builder."""

    def test_builder_chain(self):
        """Test builder fluent interface."""
        variables = (
            ContextVariableBuilder()
            .with_empresa("Test Corp")
            .with_tier("PREMIUM")
            .with_agent("Sales Agent", "Friendly and helpful")
            .build()
        )

        assert variables.nome_empresa == "Test Corp"
        assert variables.tier == "PREMIUM"
        assert variables.agent_name == "Sales Agent"
        assert variables.agent_personality == "Friendly and helpful"

    def test_builder_with_tools(self):
        """Test builder with tools."""
        variables = (
            ContextVariableBuilder()
            .with_tools(["tool1", "tool2"])
            .build()
        )

        assert "tool1" in variables.enabled_tools
        assert "tool2" in variables.enabled_tools
        assert "tool1" in variables.tools_description

    def test_builder_build_dict(self):
        """Test builder build_dict()."""
        result = (
            ContextVariableBuilder()
            .with_empresa("Test Corp")
            .build_dict()
        )

        assert isinstance(result, dict)
        assert result["nome_empresa"] == "Test Corp"


class TestPromptLoader:
    """Tests for prompt loader."""

    def test_load_builtin(self):
        """Test loading built-in prompt."""
        loader = PromptLoader()

        prompt = loader.load_builtin(
            "atendente/system/v1",
            {"nome_empresa": "Test Corp"},
        )

        assert prompt.name == "atendente/system/v1"
        assert "Test Corp" in prompt.content
        assert prompt.source == "builtin"

    def test_load_builtin_not_found(self):
        """Test loading non-existent built-in prompt."""
        loader = PromptLoader()

        with pytest.raises(PromptNotFoundError):
            loader.load_builtin("nonexistent/prompt", {})

    def test_load_builtin_with_defaults(self):
        """Test built-in prompt with default optional variables."""
        loader = PromptLoader()

        # V2 has optional_variables with defaults
        prompt = loader.load_builtin(
            "atendente/system/v2",
            {"nome_empresa": "Test Corp"},
        )

        # Should have default values applied
        assert "Test Corp" in prompt.content

    def test_list_available(self):
        """Test listing available prompts."""
        loader = PromptLoader()
        available = loader.list_available()

        assert "atendente/system/v1" in available
        assert "rag/query" in available


class TestPromptManager:
    """Tests for prompt manager."""

    def test_prompt_version_full_name(self):
        """Test PromptVersion.full_name property."""
        version = PromptVersion(
            name="test/prompt",
            version=2,
            content="Test content",
        )

        assert version.full_name == "test/prompt/v2"


class TestLoadedPrompt:
    """Tests for LoadedPrompt."""

    def test_as_system_message(self):
        """Test conversion to system message."""
        prompt = LoadedPrompt(
            name="test",
            content="Test content",
        )

        message = prompt.as_system_message()
        assert message["role"] == "system"
        assert message["content"] == "Test content"

    def test_as_user_message(self):
        """Test conversion to user message."""
        prompt = LoadedPrompt(
            name="test",
            content="Test content",
        )

        message = prompt.as_user_message()
        assert message["role"] == "user"
        assert message["content"] == "Test content"


class TestIntegration:
    """Integration tests."""

    def test_full_render_pipeline(self):
        """Test complete render pipeline."""
        # Build variables
        variables = (
            ContextVariableBuilder()
            .with_empresa("Acme Inc")
            .with_tools(["executar_rag_cliente", "executar_sql_agent"])
            .with_tier("PROFISSIONAL")
            .build()
        )

        # Load and render prompt
        loader = PromptLoader()
        renderer = TemplateRenderer()

        builtin = get_builtin_template("atendente/system/v2")
        content = renderer.render(builtin.content, variables.to_dict())

        assert "Acme Inc" in content
        assert len(content) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
