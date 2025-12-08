"""
Tests for vizu_tool_registry.

These tests verify:
- ToolRegistry lookup and filtering
- TierValidator access control
- ToolMetadata tier comparison
"""

import pytest
from vizu_tool_registry import (
    ToolRegistry,
    TierValidator,
    ToolMetadata,
    ToolCategory,
    ToolNotFoundError,
    TierAccessDeniedError,
)
from vizu_tool_registry.tool_metadata import TierLevel


class TestToolMetadata:
    """Tests for ToolMetadata class."""

    def test_create_tool_metadata(self):
        """Test creating a ToolMetadata instance."""
        tool = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RAG,
            description="A test tool",
            tier_required=TierLevel.BASIC,
        )
        assert tool.name == "test_tool"
        assert tool.category == ToolCategory.RAG
        assert tool.tier_required == TierLevel.BASIC
        assert tool.requires_confirmation is False

    def test_tier_accessibility_basic(self):
        """Test tier accessibility for BASIC tier tool."""
        tool = ToolMetadata(
            name="basic_tool",
            category=ToolCategory.RAG,
            description="Basic tool",
            tier_required=TierLevel.BASIC,
        )
        assert tool.is_accessible_by_tier("FREE") is False
        assert tool.is_accessible_by_tier("BASIC") is True
        assert tool.is_accessible_by_tier("SME") is True
        assert tool.is_accessible_by_tier("ENTERPRISE") is True

    def test_tier_accessibility_sme(self):
        """Test tier accessibility for SME tier tool."""
        tool = ToolMetadata(
            name="sme_tool",
            category=ToolCategory.SQL,
            description="SME tool",
            tier_required=TierLevel.SME,
        )
        assert tool.is_accessible_by_tier("FREE") is False
        assert tool.is_accessible_by_tier("BASIC") is False
        assert tool.is_accessible_by_tier("SME") is True
        assert tool.is_accessible_by_tier("ENTERPRISE") is True

    def test_tier_accessibility_enterprise(self):
        """Test tier accessibility for ENTERPRISE tier tool."""
        tool = ToolMetadata(
            name="enterprise_tool",
            category=ToolCategory.DOCKER_MCP,
            description="Enterprise tool",
            tier_required=TierLevel.ENTERPRISE,
        )
        assert tool.is_accessible_by_tier("FREE") is False
        assert tool.is_accessible_by_tier("BASIC") is False
        assert tool.is_accessible_by_tier("SME") is False
        assert tool.is_accessible_by_tier("ENTERPRISE") is True

    def test_is_docker_mcp_tool(self):
        """Test Docker MCP tool detection."""
        regular_tool = ToolMetadata(
            name="regular",
            category=ToolCategory.RAG,
            description="Regular tool",
        )
        docker_tool = ToolMetadata(
            name="docker",
            category=ToolCategory.DOCKER_MCP,
            description="Docker tool",
            docker_mcp_integration="github",
        )
        assert regular_tool.is_docker_mcp_tool() is False
        assert docker_tool.is_docker_mcp_tool() is True

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        tool = ToolMetadata(
            name="test",
            category=ToolCategory.RAG,
            description="Test tool",
            tier_required=TierLevel.SME,
            requires_confirmation=True,
            tags=["test", "example"],
        )
        data = tool.to_dict()
        restored = ToolMetadata.from_dict(data)

        assert restored.name == tool.name
        assert restored.category == tool.category
        assert restored.tier_required == tool.tier_required
        assert restored.requires_confirmation == tool.requires_confirmation
        assert restored.tags == tool.tags


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_get_tool_builtin(self):
        """Test getting a builtin tool."""
        tool = ToolRegistry.get_tool("executar_rag_cliente")
        assert tool is not None
        assert tool.name == "executar_rag_cliente"
        assert tool.category == ToolCategory.RAG

    def test_get_tool_not_found(self):
        """Test getting a non-existent tool."""
        tool = ToolRegistry.get_tool("nonexistent_tool")
        assert tool is None

    def test_get_available_tools_basic_tier(self):
        """Test that BASIC tier only gets basic tools."""
        available = ToolRegistry.get_available_tools(
            enabled_tools=["executar_rag_cliente", "executar_sql_agent"],
            tier="BASIC",
        )
        tool_names = [t.name for t in available]
        assert "executar_rag_cliente" in tool_names
        assert "executar_sql_agent" not in tool_names  # Requires SME

    def test_get_available_tools_sme_tier(self):
        """Test that SME tier gets RAG and SQL tools."""
        available = ToolRegistry.get_available_tools(
            enabled_tools=["executar_rag_cliente", "executar_sql_agent"],
            tier="SME",
        )
        tool_names = [t.name for t in available]
        assert "executar_rag_cliente" in tool_names
        assert "executar_sql_agent" in tool_names

    def test_get_available_tools_enterprise_tier(self):
        """Test that ENTERPRISE tier can access Docker MCP tools."""
        available = ToolRegistry.get_available_tools(
            enabled_tools=["executar_rag_cliente", "github_read"],
            tier="ENTERPRISE",
            include_docker_mcp=True,
        )
        tool_names = [t.name for t in available]
        assert "executar_rag_cliente" in tool_names
        assert "github_read" in tool_names

    def test_get_available_tools_excludes_disabled(self):
        """Test that disabled tools are not returned."""
        # Get a tool and mark it disabled
        tool = ToolRegistry.get_tool("executar_rag_cliente")
        original_enabled = tool.enabled
        tool.enabled = False

        try:
            available = ToolRegistry.get_available_tools(
                enabled_tools=["executar_rag_cliente"],
                tier="BASIC",
            )
            assert len(available) == 0
        finally:
            # Restore original state
            tool.enabled = original_enabled

    def test_validate_client_tools_valid(self):
        """Test validation of valid tool configuration."""
        is_valid, errors = ToolRegistry.validate_client_tools(
            enabled_tools=["executar_rag_cliente"],
            tier="BASIC",
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_client_tools_invalid_tier(self):
        """Test validation fails when tool requires higher tier."""
        is_valid, errors = ToolRegistry.validate_client_tools(
            enabled_tools=["executar_sql_agent"],
            tier="BASIC",
        )
        assert is_valid is False
        assert len(errors) == 1
        assert "requires SME" in errors[0]

    def test_validate_client_tools_not_found(self):
        """Test validation fails for unknown tool."""
        is_valid, errors = ToolRegistry.validate_client_tools(
            enabled_tools=["nonexistent_tool"],
            tier="ENTERPRISE",
        )
        assert is_valid is False
        assert "not found" in errors[0]

    def test_get_tools_for_tier(self):
        """Test getting all tools accessible at a tier."""
        basic_tools = ToolRegistry.get_tools_for_tier("BASIC")
        sme_tools = ToolRegistry.get_tools_for_tier("SME")

        # SME should have more tools than BASIC
        assert len(sme_tools) > len(basic_tools)

        # Basic should only have BASIC/FREE tools
        for tool in basic_tools:
            assert tool.tier_required.value in ["FREE", "BASIC"]

    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        rag_tools = ToolRegistry.get_tools_by_category(ToolCategory.RAG)
        assert len(rag_tools) > 0
        for tool in rag_tools:
            assert tool.category == ToolCategory.RAG

    def test_get_confirmation_required_tools(self):
        """Test getting tools that require confirmation."""
        tools = ToolRegistry.get_confirmation_required_tools()
        assert len(tools) > 0
        for tool in tools:
            assert tool.requires_confirmation is True

    def test_get_tool_names_for_legacy_flags(self):
        """Test converting legacy boolean flags to tool names."""
        tools = ToolRegistry.get_tool_names_for_legacy_flags(
            rag_enabled=True,
            sql_enabled=True,
            scheduling_enabled=False,
        )
        assert "executar_rag_cliente" in tools
        assert "executar_sql_agent" in tools
        assert "agendar_consulta" not in tools

    def test_register_custom_tool(self):
        """Test registering a custom tool at runtime."""
        custom_tool = ToolMetadata(
            name="custom_test_tool",
            category=ToolCategory.CUSTOM,
            description="A custom test tool",
            tier_required=TierLevel.BASIC,
        )
        ToolRegistry.register_custom_tool(custom_tool)

        retrieved = ToolRegistry.get_tool("custom_test_tool")
        assert retrieved is not None
        assert retrieved.name == "custom_test_tool"

        # Cleanup
        del ToolRegistry.BUILTIN_TOOLS["custom_test_tool"]


class TestTierValidator:
    """Tests for TierValidator class."""

    def test_get_default_tools_for_tier(self):
        """Test getting default tools for each tier."""
        basic_tools = TierValidator.get_default_tools_for_tier("BASIC")
        sme_tools = TierValidator.get_default_tools_for_tier("SME")

        assert "executar_rag_cliente" in basic_tools
        assert "executar_sql_agent" not in basic_tools

        assert "executar_rag_cliente" in sme_tools
        assert "executar_sql_agent" in sme_tools
        assert "agendar_consulta" in sme_tools

    def test_can_access_tool(self):
        """Test checking tier access to tools."""
        assert TierValidator.can_access_tool("executar_rag_cliente", "BASIC") is True
        assert TierValidator.can_access_tool("executar_sql_agent", "BASIC") is False
        assert TierValidator.can_access_tool("executar_sql_agent", "SME") is True

    def test_upgrade_tier_tools(self):
        """Test upgrading tier adds new tools."""
        current_tools = ["executar_rag_cliente"]
        upgraded = TierValidator.upgrade_tier_tools(current_tools, "SME")

        assert "executar_rag_cliente" in upgraded
        assert "executar_sql_agent" in upgraded
        assert "agendar_consulta" in upgraded

    def test_upgrade_tier_preserves_custom_tools(self):
        """Test that tier upgrade preserves existing tools."""
        # Register a custom tool first
        custom_tool = ToolMetadata(
            name="my_custom_tool",
            category=ToolCategory.CUSTOM,
            description="Custom",
            tier_required=TierLevel.BASIC,
        )
        ToolRegistry.register_custom_tool(custom_tool)

        try:
            current_tools = ["executar_rag_cliente", "my_custom_tool"]
            upgraded = TierValidator.upgrade_tier_tools(current_tools, "SME")

            # Should have both SME defaults and custom tool
            assert "executar_rag_cliente" in upgraded
            assert "executar_sql_agent" in upgraded
            assert "my_custom_tool" in upgraded
        finally:
            del ToolRegistry.BUILTIN_TOOLS["my_custom_tool"]

    def test_downgrade_tier_removes_inaccessible(self):
        """Test downgrading tier removes inaccessible tools."""
        current_tools = ["executar_rag_cliente", "executar_sql_agent"]
        downgraded = TierValidator.downgrade_tier_tools(
            current_tools, "BASIC", remove_inaccessible=True
        )

        assert "executar_rag_cliente" in downgraded
        assert "executar_sql_agent" not in downgraded

    def test_downgrade_tier_keeps_all(self):
        """Test downgrading tier can keep all tools if requested."""
        current_tools = ["executar_rag_cliente", "executar_sql_agent"]
        downgraded = TierValidator.downgrade_tier_tools(
            current_tools, "BASIC", remove_inaccessible=False
        )

        # Should keep all tools
        assert "executar_rag_cliente" in downgraded
        assert "executar_sql_agent" in downgraded

    def test_get_tier_limits(self):
        """Test getting tier rate limits."""
        basic_limits = TierValidator.get_tier_limits("BASIC")
        assert basic_limits["max_queries_per_day"] == 100

        enterprise_limits = TierValidator.get_tier_limits("ENTERPRISE")
        assert enterprise_limits["max_queries_per_day"] is None  # Unlimited

    def test_get_tier_features(self):
        """Test getting tier features."""
        basic_features = TierValidator.get_tier_features("BASIC")
        assert "rag" in basic_features
        assert "docker_mcp" not in basic_features

        enterprise_features = TierValidator.get_tier_features("ENTERPRISE")
        assert "docker_mcp" in enterprise_features

    def test_compare_tiers(self):
        """Test tier comparison."""
        assert TierValidator.compare_tiers("BASIC", "SME") == -1
        assert TierValidator.compare_tiers("SME", "SME") == 0
        assert TierValidator.compare_tiers("ENTERPRISE", "BASIC") == 1

    def test_is_tier_higher_or_equal(self):
        """Test tier >= comparison."""
        assert TierValidator.is_tier_higher_or_equal("SME", "BASIC") is True
        assert TierValidator.is_tier_higher_or_equal("BASIC", "BASIC") is True
        assert TierValidator.is_tier_higher_or_equal("BASIC", "SME") is False

    def test_get_tier_diff(self):
        """Test getting difference between tiers."""
        diff = TierValidator.get_tier_diff("BASIC", "SME")

        assert diff["is_upgrade"] is True
        assert "executar_sql_agent" in diff["tools_added"]
        assert "agendar_consulta" in diff["tools_added"]
        assert len(diff["tools_removed"]) == 0

        # Test downgrade
        diff_down = TierValidator.get_tier_diff("SME", "BASIC")
        assert diff_down["is_upgrade"] is False
        assert "executar_sql_agent" in diff_down["tools_removed"]
