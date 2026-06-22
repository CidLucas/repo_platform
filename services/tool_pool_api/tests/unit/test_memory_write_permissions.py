"""
Tests for shared memory write permissions (T5.2).

Tests the _check_write_permission function logic directly.
Permission model (source → allowed entity_types):

  system:        ALL 9 entity types
  memory_agent:  ALL 9 entity types
  specialist:    ALL except routine
  manual:        business entities only (skill, client, contact, supplier, user)
  migration:     ALL 9 entity types

Unknown source raises ValueError (the caller-side fallback to "manual"
is tested in separate integration tests).
"""

import pytest

# ── Permission model (copied from memory_module.py lines 63-82) ──────────────

_WRITE_PERMISSIONS: dict[str, frozenset[str]] = {
    "system": frozenset({
        "skill", "client", "contact", "supplier", "user",
        "snapshot", "routine", "agent_result", "agent_metadata",
    }),
    "memory_agent": frozenset({
        "skill", "client", "contact", "supplier", "user",
        "snapshot", "routine", "agent_result", "agent_metadata",
    }),
    "specialist": frozenset({
        "skill", "client", "contact", "supplier", "user",
        "snapshot", "agent_result", "agent_metadata",
    }),
    "manual": frozenset({
        "skill", "client", "contact", "supplier", "user",
    }),
    "migration": frozenset({
        "skill", "client", "contact", "supplier", "user",
        "snapshot", "routine", "agent_result", "agent_metadata",
    }),
}


def _check_write_permission(
    source: str,
    entity_type: str,
    entity_name: str,
) -> None:
    """Replica of the function in memory_module.py lines 86-102."""
    allowed = _WRITE_PERMISSIONS.get(source)
    if allowed is None:
        raise ValueError(
            f"Unknown source '{source}'. "
            f"Must be one of: {sorted(_WRITE_PERMISSIONS.keys())}"
        )
    if entity_type not in allowed:
        raise ValueError(
            f"Write permission denied: source '{source}' cannot write to "
            f"entity_type '{entity_type}' (entity: {entity_name}). "
            f"Allowed types for '{source}': {sorted(allowed)}"
        )


# ── 1. ALLOWED WRITES ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,entity_type",
    [
        # system → ALL
        ("system", "skill"),
        ("system", "client"),
        ("system", "contact"),
        ("system", "supplier"),
        ("system", "user"),
        ("system", "snapshot"),
        ("system", "routine"),
        ("system", "agent_result"),
        ("system", "agent_metadata"),
        # memory_agent → ALL
        ("memory_agent", "skill"),
        ("memory_agent", "snapshot"),
        ("memory_agent", "routine"),
        ("memory_agent", "agent_result"),
        ("memory_agent", "agent_metadata"),
        # specialist → all except routine
        ("specialist", "skill"),
        ("specialist", "snapshot"),
        ("specialist", "agent_metadata"),
        ("specialist", "agent_result"),
        # manual → business entities only
        ("manual", "skill"),
        ("manual", "client"),
        ("manual", "contact"),
        ("manual", "supplier"),
        ("manual", "user"),
        # migration → ALL
        ("migration", "skill"),
        ("migration", "routine"),
        ("migration", "agent_result"),
    ],
)
def test_allowed_write(source, entity_type):
    """Each source CAN write to its permitted entity_types."""
    _check_write_permission(
        source=source, entity_type=entity_type, entity_name="test-entity",
    )


# ── 2. DENIED WRITES ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,entity_type",
    [
        # manual → NO snapshot/routine/agent_result/agent_metadata
        ("manual", "snapshot"),
        ("manual", "routine"),
        ("manual", "agent_result"),
        ("manual", "agent_metadata"),
        # specialist → NO routine
        ("specialist", "routine"),
    ],
)
def test_denied_write(source, entity_type):
    """Each source CANNOT write to disallowed entity_types."""
    with pytest.raises(ValueError, match="Write permission denied"):
        _check_write_permission(
            source=source, entity_type=entity_type, entity_name="test-entity",
        )


# ── 3. UNKNOWN SOURCE ───────────────────────────────────────────────────────


def test_unknown_source_raises_error():
    """An unrecognised source raises ValueError listing valid sources."""
    with pytest.raises(ValueError, match="Unknown source") as exc:
        _check_write_permission(
            source="hacker", entity_type="skill", entity_name="foo",
        )
    msg = str(exc.value).lower()
    for name in ("system", "memory_agent", "specialist", "manual", "migration"):
        assert name in msg, f"Error message should mention '{name}'"


# ── 4. ERROR MESSAGE CONTENT ────────────────────────────────────────────────


def test_denied_error_message_includes_entity_name():
    """The denial error message includes the entity name for traceability."""
    with pytest.raises(ValueError, match="my-precious-entity"):
        _check_write_permission(
            source="manual",
            entity_type="snapshot",
            entity_name="my-precious-entity",
        )


def test_denied_error_message_includes_source_name():
    """The denial error message mentions which source was denied."""
    with pytest.raises(ValueError, match="specialist"):
        _check_write_permission(
            source="specialist",
            entity_type="routine",
            entity_name="foo",
        )


def test_denied_error_message_includes_allowed_types():
    """The denial error message lists the allowed entity types for the source."""
    with pytest.raises(ValueError, match="skill") as exc:
        _check_write_permission(
            source="manual", entity_type="snapshot", entity_name="foo",
        )
    msg = str(exc.value)
    # manual can write to: skill, client, contact, supplier, user
    for t in ("skill", "client", "contact", "supplier", "user"):
        assert t in msg, f"Error message should include '{t}' in allowed types"


# ── 5. WHITESPACE / EDGE CASES ──────────────────────────────────────────────


def test_entity_name_whitespace():
    """The permission check accepts any entity_name string (validation is separate)."""
    _check_write_permission(source="system", entity_type="snapshot", entity_name="")
    _check_write_permission(source="system", entity_type="snapshot", entity_name="  ")
    _check_write_permission(source="system", entity_type="snapshot", entity_name="\n\t")


def test_source_case_sensitivity():
    """Source names are case-sensitive; wrong casing is an unknown source."""
    with pytest.raises(ValueError, match="Unknown source"):
        _check_write_permission(
            source="System", entity_type="skill", entity_name="test",
        )
    with pytest.raises(ValueError, match="Unknown source"):
        _check_write_permission(
            source="MANUAL", entity_type="skill", entity_name="test",
        )


# ── 6. ALL SOURCES IN PERMISSION MAP ────────────────────────────────────────


def test_all_sources_exist():
    """Verify every expected source key is in the permission map."""
    expected = {"system", "memory_agent", "specialist", "manual", "migration"}
    assert set(_WRITE_PERMISSIONS.keys()) == expected, (
        f"Expected sources {expected}, got {set(_WRITE_PERMISSIONS.keys())}"
    )


# ── 7. SPECIALIST vs SYSTEM DIFFERENCE ──────────────────────────────────────


def test_specialist_denied_routine_but_system_allowed():
    """specialist cannot write routine; system can (regression guard)."""
    with pytest.raises(ValueError, match="Write permission denied"):
        _check_write_permission(
            source="specialist", entity_type="routine", entity_name="reg-test",
        )
    # system is unaffected
    _check_write_permission(
        source="system", entity_type="routine", entity_name="reg-test",
    )


# ── 8. MANUAL LEAST PRIVILEGE GUARDIAN ──────────────────────────────────────


@pytest.mark.parametrize(
    "restricted_type",
    ["snapshot", "routine", "agent_result", "agent_metadata"],
)
def test_manual_cannot_write_non_business_types(restricted_type):
    """manual source has least privilege — only business entity types."""
    with pytest.raises(ValueError, match="Write permission denied"):
        _check_write_permission(
            source="manual",
            entity_type=restricted_type,
            entity_name="guard-test",
        )


# ── 9. ALL BUSINESS ENTITIES ACCEPTED BY MANUAL ─────────────────────────────


@pytest.mark.parametrize(
    "business_type",
    ["skill", "client", "contact", "supplier", "user"],
)
def test_manual_can_write_business_types(business_type):
    """manual source can write all 5 business entity types."""
    _check_write_permission(
        source="manual",
        entity_type=business_type,
        entity_name="entity-test",
    )
