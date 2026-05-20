"""
BL-004 — TierLevel.get_order normalisation + AgentTypeRegistry.for_tier robustness.

All tests are fully offline (no external services required).
"""

import logging

import pytest

from blu_agent_framework.registry import AgentTypeRegistry
from blu_tool_registry.tool_metadata import TierLevel

# ---------------------------------------------------------------------------
# TierLevel.get_order — normalisation
# ---------------------------------------------------------------------------


class TestTierLevelGetOrder:
    def test_canonical_upper(self):
        assert TierLevel.get_order("BASIC") == 1

    def test_lowercase_normalised(self):
        assert TierLevel.get_order("sme") == 2

    def test_mixed_case_normalised(self):
        assert TierLevel.get_order("Premium") == 3

    def test_leading_trailing_whitespace(self):
        assert TierLevel.get_order("  ENTERPRISE  ") == 4

    def test_admin_highest(self):
        assert TierLevel.get_order("admin") == 99

    def test_free_is_zero(self):
        assert TierLevel.get_order("FREE") == 0

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown TierLevel"):
            TierLevel.get_order("GOLD")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Unknown TierLevel"):
            TierLevel.get_order("")

    def test_none_like_raises(self):
        # non-str input: normalised to "" which is unknown
        with pytest.raises((ValueError, AttributeError)):
            TierLevel.get_order(None)  # type: ignore[arg-type]

    def test_order_monotone(self):
        """Ordering must be FREE < BASIC < SME < PREMIUM < ENTERPRISE < ADMIN."""
        tiers = ["FREE", "BASIC", "SME", "PREMIUM", "ENTERPRISE", "ADMIN"]
        orders = [TierLevel.get_order(t) for t in tiers]
        assert orders == sorted(orders)

    def test_is_admin_still_works_after_normalisation(self):
        assert TierLevel.is_admin("ADMIN") is True
        assert TierLevel.is_admin("admin") is False  # is_admin uses raw == value


# ---------------------------------------------------------------------------
# AgentTypeRegistry.for_tier — normalisation + unknown-tier fallback
# ---------------------------------------------------------------------------


class TestAgentTypeRegistryForTier:
    def test_canonical_returns_list(self):
        result = AgentTypeRegistry.for_tier("BASIC")
        assert isinstance(result, list)

    def test_lowercase_same_as_upper(self):
        upper = AgentTypeRegistry.for_tier("BASIC")
        lower = AgentTypeRegistry.for_tier("basic")
        assert {c.slug for c in upper} == {c.slug for c in lower}

    def test_mixed_case_normalised(self):
        sme_mixed = AgentTypeRegistry.for_tier("Sme")
        sme_upper = AgentTypeRegistry.for_tier("SME")
        assert {c.slug for c in sme_mixed} == {c.slug for c in sme_upper}

    def test_whitespace_stripped(self):
        padded = AgentTypeRegistry.for_tier("  SME  ")
        clean  = AgentTypeRegistry.for_tier("SME")
        assert {c.slug for c in padded} == {c.slug for c in clean}

    def test_higher_tier_includes_lower(self):
        """SME must be a superset of BASIC."""
        basic = {c.slug for c in AgentTypeRegistry.for_tier("BASIC")}
        sme   = {c.slug for c in AgentTypeRegistry.for_tier("SME")}
        assert basic.issubset(sme)

    def test_unknown_tier_falls_back_to_basic(self, caplog):
        with caplog.at_level(logging.WARNING, logger="blu_agent_framework.registry"):
            result_unknown = AgentTypeRegistry.for_tier("GOLD")
        result_basic = AgentTypeRegistry.for_tier("BASIC")
        assert {c.slug for c in result_unknown} == {c.slug for c in result_basic}
        assert "Unknown tier" in caplog.text

    def test_unknown_tier_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="blu_agent_framework.registry"):
            AgentTypeRegistry.for_tier("DOES_NOT_EXIST")
        assert any("DOES_NOT_EXIST" in r.message for r in caplog.records)

    def test_empty_string_falls_back_to_basic(self, caplog):
        with caplog.at_level(logging.WARNING, logger="blu_agent_framework.registry"):
            result = AgentTypeRegistry.for_tier("")
        result_basic = AgentTypeRegistry.for_tier("BASIC")
        assert {c.slug for c in result} == {c.slug for c in result_basic}

    def test_admin_returns_all(self):
        """ADMIN should have access to every registered agent type."""
        all_slugs = set(AgentTypeRegistry.all().keys())
        admin_slugs = {c.slug for c in AgentTypeRegistry.for_tier("ADMIN")}
        assert all_slugs == admin_slugs
