"""
tests/test_feature_registry.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for FeatureRegistry and ResourceResolver (Fase 1 — Tier Enforcement Redesign).

Run from the lib root:
    cd libs/blu_tool_registry
    python -m pytest tests/test_feature_registry.py -v
"""

import pytest

from blu_tool_registry.features import (
    FEATURES,
    TIER_FEATURES,
    FeatureConfig,
    FeatureRegistry,
)
from blu_tool_registry.resource_resolver import ResourceResolver
from blu_tool_registry.tool_metadata import TierLevel


# ===========================================================================
# Fixtures / helpers
# ===========================================================================

ALL_TIERS = ["FREE", "BASIC", "SME", "PREMIUM", "ENTERPRISE", "ADMIN"]
ORDERED_TIERS = ALL_TIERS  # cumulative order


# ===========================================================================
# FeatureConfig
# ===========================================================================


class TestFeatureConfig:
    def test_frozen(self):
        """FeatureConfig must be immutable (frozen dataclass)."""
        fc = FEATURES["rag"]
        with pytest.raises((AttributeError, TypeError)):
            fc.name = "hacked"  # type: ignore[misc]

    def test_agents_and_tools_are_tuples(self):
        for name, fc in FEATURES.items():
            assert isinstance(fc.agents, tuple), f"{name}.agents should be tuple"
            assert isinstance(fc.tools, tuple), f"{name}.tools should be tuple"

    def test_tier_min_is_tier_level(self):
        for name, fc in FEATURES.items():
            assert isinstance(fc.tier_min, TierLevel), \
                f"{name}.tier_min should be TierLevel"

    def test_repr_contains_name_and_tier(self):
        fc = FEATURES["fiscal"]
        r = repr(fc)
        assert "fiscal" in r
        assert "ENTERPRISE" in r


# ===========================================================================
# FEATURES dict sanity
# ===========================================================================


class TestFeatureDictSanity:
    def test_all_features_present(self):
        expected = {
            "chat_basico", "diagnostico",
            "rag", "onboarding", "monitoramento_web",
            "sql_analytics", "platform_ops", "synthesis",
            "compras_basico", "financeiro", "agenda_basico",
            "documentos", "ocr_extraction", "notion", "monday", "whatsapp",
            "compras_avancado", "crm_avancado", "google_integrations",
            "estrategia", "slack", "asana_linear",
            "fiscal", "docker_mcp",
        }
        assert set(FEATURES) == expected

    def test_tier_features_covers_all_tiers(self):
        assert set(TIER_FEATURES.keys()) == set(ALL_TIERS)

    def test_tier_features_reference_existing_features(self):
        for tier, names in TIER_FEATURES.items():
            for name in names:
                assert name in FEATURES, \
                    f"TIER_FEATURES[{tier!r}] references unknown feature {name!r}"

    def test_each_feature_has_at_least_one_agent_and_tool(self):
        for name, fc in FEATURES.items():
            assert len(fc.agents) >= 1, f"{name} has no agents"
            assert len(fc.tools) >= 1, f"{name} has no tools"

    def test_feature_name_matches_key(self):
        for key, fc in FEATURES.items():
            assert fc.name == key, f"FEATURES[{key!r}].name = {fc.name!r}"


# ===========================================================================
# Cumulative tier coverage
# ===========================================================================


class TestCumulativeTierCoverage:
    def test_free_subset_of_basic(self):
        free = set(TIER_FEATURES["FREE"])
        basic = set(TIER_FEATURES["BASIC"])
        assert free <= basic, f"FREE features not in BASIC: {free - basic}"

    def test_basic_subset_of_sme(self):
        assert set(TIER_FEATURES["BASIC"]) <= set(TIER_FEATURES["SME"])

    def test_sme_subset_of_premium(self):
        assert set(TIER_FEATURES["SME"]) <= set(TIER_FEATURES["PREMIUM"])

    def test_premium_subset_of_enterprise(self):
        assert set(TIER_FEATURES["PREMIUM"]) <= set(TIER_FEATURES["ENTERPRISE"])

    def test_enterprise_subset_of_admin(self):
        assert set(TIER_FEATURES["ENTERPRISE"]) <= set(TIER_FEATURES["ADMIN"])

    def test_fiscal_only_enterprise_and_above(self):
        for tier in ["FREE", "BASIC", "SME", "PREMIUM"]:
            assert "fiscal" not in TIER_FEATURES[tier]
        assert "fiscal" in TIER_FEATURES["ENTERPRISE"]
        assert "fiscal" in TIER_FEATURES["ADMIN"]

    def test_docker_mcp_only_enterprise_and_above(self):
        for tier in ["FREE", "BASIC", "SME", "PREMIUM"]:
            assert "docker_mcp" not in TIER_FEATURES[tier]
        assert "docker_mcp" in TIER_FEATURES["ENTERPRISE"]


# ===========================================================================
# FeatureRegistry.get_features_for_tier
# ===========================================================================


class TestGetFeaturesForTier:
    def test_returns_list_of_feature_configs(self):
        result = FeatureRegistry.get_features_for_tier("BASIC")
        assert isinstance(result, list)
        for fc in result:
            assert isinstance(fc, FeatureConfig)

    def test_free_has_two_features(self):
        result = FeatureRegistry.get_features_for_tier("FREE")
        names = {fc.name for fc in result}
        assert names == {"chat_basico", "diagnostico"}

    def test_sme_includes_financeiro(self):
        names = {fc.name for fc in FeatureRegistry.get_features_for_tier("SME")}
        assert "financeiro" in names

    def test_accepts_tier_level_enum(self):
        result = FeatureRegistry.get_features_for_tier(TierLevel.ENTERPRISE)
        names = {fc.name for fc in result}
        assert "fiscal" in names

    def test_invalid_tier_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            FeatureRegistry.get_features_for_tier("ULTRAPLAN")


# ===========================================================================
# FeatureRegistry.get_agents_for_tier
# ===========================================================================


class TestGetAgentsForTier:
    def test_free_only_frontdesk(self):
        agents = FeatureRegistry.get_agents_for_tier("FREE")
        assert agents == ["frontdesk"]

    def test_basic_includes_context_gatherer(self):
        agents = FeatureRegistry.get_agents_for_tier("BASIC")
        assert "context-gatherer" in agents

    def test_sme_includes_specialist_agents(self):
        agents = FeatureRegistry.get_agents_for_tier("SME")
        for slug in ["synthesis", "data-analyst", "platform", "financeiro",
                     "compras", "agenda", "documentos", "supplier-agent",
                     "scheduler-agent", "doc-writer"]:
            assert slug in agents, f"{slug!r} should be accessible at SME"

    def test_enterprise_includes_fiscal_agent(self):
        agents = FeatureRegistry.get_agents_for_tier("ENTERPRISE")
        assert "fiscal-agent" in agents

    def test_premium_does_not_include_fiscal_agent(self):
        agents = FeatureRegistry.get_agents_for_tier("PREMIUM")
        assert "fiscal-agent" not in agents

    def test_no_duplicates(self):
        for tier in ALL_TIERS:
            agents = FeatureRegistry.get_agents_for_tier(tier)
            assert len(agents) == len(set(agents)), \
                f"Duplicate agents in tier {tier!r}"

    def test_crm_requires_premium(self):
        sme_agents = FeatureRegistry.get_agents_for_tier("SME")
        premium_agents = FeatureRegistry.get_agents_for_tier("PREMIUM")
        assert "crm" not in sme_agents
        assert "crm" in premium_agents


# ===========================================================================
# FeatureRegistry.get_tools_for_tier
# ===========================================================================


class TestGetToolsForTier:
    def test_free_has_only_public_test_tool(self):
        tools = FeatureRegistry.get_tools_for_tier("FREE")
        assert tools == ["ferramenta_publica_de_teste"]

    def test_basic_includes_rag(self):
        tools = FeatureRegistry.get_tools_for_tier("BASIC")
        assert "executar_rag_cliente" in tools

    def test_sme_includes_execute_sql(self):
        tools = FeatureRegistry.get_tools_for_tier("SME")
        assert "execute_sql" in tools

    def test_enterprise_includes_fiscal_tools(self):
        tools = FeatureRegistry.get_tools_for_tier("ENTERPRISE")
        assert "fiscal_preparar_dados_nfe" in tools
        assert "fiscal_status_integracao" in tools

    def test_no_duplicates_per_tier(self):
        for tier in ALL_TIERS:
            tools = FeatureRegistry.get_tools_for_tier(tier)
            assert len(tools) == len(set(tools)), \
                f"Duplicate tools in tier {tier!r}"

    def test_higher_tier_is_superset(self):
        basic = set(FeatureRegistry.get_tools_for_tier("BASIC"))
        sme = set(FeatureRegistry.get_tools_for_tier("SME"))
        assert basic <= sme


# ===========================================================================
# FeatureRegistry.get_tools_for_agent_and_tier
# ===========================================================================


class TestGetToolsForAgentAndTier:
    def test_frontdesk_free_gets_public_tool(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("frontdesk", "FREE")
        assert "ferramenta_publica_de_teste" in tools

    def test_frontdesk_basic_gets_rag_too(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("frontdesk", "BASIC")
        assert "executar_rag_cliente" in tools

    def test_financeiro_sme_gets_execute_sql(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("financeiro", "SME")
        assert "execute_sql" in tools

    def test_fiscal_agent_enterprise_gets_nfe_tools(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("fiscal-agent", "ENTERPRISE")
        assert "fiscal_preparar_dados_nfe" in tools
        assert "fiscal_status_integracao" in tools

    def test_fiscal_agent_premium_returns_empty(self):
        """fiscal-agent is not accessible at PREMIUM — should return []."""
        tools = FeatureRegistry.get_tools_for_agent_and_tier("fiscal-agent", "PREMIUM")
        assert tools == []

    def test_unknown_agent_returns_empty(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("nonexistent-agent", "ENTERPRISE")
        assert tools == []

    def test_no_duplicates(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("compras", "SME")
        assert len(tools) == len(set(tools))

    def test_supplier_agent_premium_gets_rfq_whatsapp(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("supplier-agent", "PREMIUM")
        assert "dispatch_rfq_whatsapp" in tools

    def test_supplier_agent_sme_no_rfq_whatsapp(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("supplier-agent", "SME")
        assert "dispatch_rfq_whatsapp" not in tools

    def test_scheduler_agent_premium_gets_google_tools(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("scheduler-agent", "PREMIUM")
        assert "query_calendar" in tools

    def test_scheduler_agent_sme_no_google_tools(self):
        tools = FeatureRegistry.get_tools_for_agent_and_tier("scheduler-agent", "SME")
        assert "query_calendar" not in tools


# ===========================================================================
# FeatureRegistry.is_agent_accessible / is_tool_accessible
# ===========================================================================


class TestAccessChecks:
    def test_frontdesk_accessible_at_free(self):
        assert FeatureRegistry.is_agent_accessible("frontdesk", "FREE") is True

    def test_fiscal_agent_not_accessible_at_sme(self):
        assert FeatureRegistry.is_agent_accessible("fiscal-agent", "SME") is False

    def test_fiscal_agent_accessible_at_enterprise(self):
        assert FeatureRegistry.is_agent_accessible("fiscal-agent", "ENTERPRISE") is True

    def test_crm_not_accessible_at_sme(self):
        assert FeatureRegistry.is_agent_accessible("crm", "SME") is False

    def test_crm_accessible_at_premium(self):
        assert FeatureRegistry.is_agent_accessible("crm", "PREMIUM") is True

    def test_execute_sql_not_at_basic(self):
        assert FeatureRegistry.is_tool_accessible("execute_sql", "BASIC") is False

    def test_execute_sql_at_sme(self):
        assert FeatureRegistry.is_tool_accessible("execute_sql", "SME") is True


# ===========================================================================
# ResourceResolver
# ===========================================================================


class TestResourceResolver:
    def test_resolve_tools_returns_list(self):
        result = ResourceResolver.resolve_tools("frontdesk", "BASIC")
        assert isinstance(result, list)

    def test_resolve_tools_inaccessible_agent_empty(self):
        result = ResourceResolver.resolve_tools("fiscal-agent", "SME")
        assert result == []

    def test_resolve_tools_with_override_filters(self):
        # override keeps only the tools in the explicit list
        result = ResourceResolver.resolve_tools(
            "frontdesk", "BASIC",
            enabled_tools_override=["executar_rag_cliente", "does_not_exist"]
        )
        assert result == ["executar_rag_cliente"]

    def test_resolve_tools_empty_override_does_not_filter(self):
        """Empty override list = use all feature-derived tools."""
        without = ResourceResolver.resolve_tools("frontdesk", "BASIC")
        with_empty = ResourceResolver.resolve_tools(
            "frontdesk", "BASIC", enabled_tools_override=[]
        )
        assert with_empty == without

    def test_resolve_agents_free(self):
        agents = ResourceResolver.resolve_agents("FREE")
        assert "frontdesk" in agents
        assert "fiscal-agent" not in agents

    def test_resolve_agents_enterprise_includes_fiscal(self):
        agents = ResourceResolver.resolve_agents("ENTERPRISE")
        assert "fiscal-agent" in agents

    def test_can_access_agent_true(self):
        assert ResourceResolver.can_access_agent("frontdesk", "FREE") is True

    def test_can_access_agent_false(self):
        assert ResourceResolver.can_access_agent("fiscal-agent", "PREMIUM") is False

    def test_can_access_tool_true(self):
        assert ResourceResolver.can_access_tool("execute_sql", "SME") is True

    def test_can_access_tool_false(self):
        assert ResourceResolver.can_access_tool("execute_sql", "BASIC") is False

    def test_resolve_all_tools_for_tier_superset(self):
        sme = set(ResourceResolver.resolve_all_tools_for_tier("SME"))
        basic = set(ResourceResolver.resolve_all_tools_for_tier("BASIC"))
        assert basic < sme

    def test_unknown_tier_falls_back_to_free(self):
        """Unknown tier should warn and fall back to FREE, not raise."""
        result = ResourceResolver.resolve_agents("UNKNOWN_TIER")
        # FREE returns only frontdesk
        assert result == ["frontdesk"]

    def test_resolve_tools_accepts_tier_level_enum(self):
        result = ResourceResolver.resolve_tools("financeiro", TierLevel.SME)
        assert "execute_sql" in result

    def test_can_access_agent_accepts_tier_level_enum(self):
        assert ResourceResolver.can_access_agent("fiscal-agent", TierLevel.ENTERPRISE) is True
