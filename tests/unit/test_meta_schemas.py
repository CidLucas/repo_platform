"""
Unit tests for SharedMemoryMeta Pydantic types and validators.

Fase 4 / T4.2b — Tests for context_schemas.py additions:
MetaEntityType, SharedMemoryMetaEntry, SharedMemoryMetaUpsertPayload,
SharedMemoryMetaQuery, validate_meta_entity_type, _VALID_META_ENTITY_TYPES.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from blu_models.context_schemas import (
    MetaEntityType,
    SharedMemoryMetaEntry,
    SharedMemoryMetaQuery,
    SharedMemoryMetaUpsertPayload,
    _VALID_META_ENTITY_TYPES,
    validate_meta_entity_type,
)


# ---------------------------------------------------------------------------
# MetaEntityType enum
# ---------------------------------------------------------------------------


class TestMetaEntityType:
    def test_enum_values(self):
        assert MetaEntityType.SYNTHESIS_OUTPUT == "synthesis_output"
        assert MetaEntityType.DEDUP_MAPPING == "dedup_mapping"
        assert MetaEntityType.KG_SUMMARY == "kg_summary"

    def test_string_coercion(self):
        assert MetaEntityType("synthesis_output") == MetaEntityType.SYNTHESIS_OUTPUT
        assert MetaEntityType("dedup_mapping") == MetaEntityType.DEDUP_MAPPING
        assert MetaEntityType("kg_summary") == MetaEntityType.KG_SUMMARY

    def test_invalid_coercion(self):
        with pytest.raises(ValueError):
            MetaEntityType("invalid")


# ---------------------------------------------------------------------------
# _VALID_META_ENTITY_TYPES
# ---------------------------------------------------------------------------


class TestValidMetaEntityTypes:
    def test_frozenset_values(self):
        assert _VALID_META_ENTITY_TYPES == frozenset(
            {"synthesis_output", "dedup_mapping", "kg_summary"}
        )

    def test_immutable(self):
        # frozenset does not support mutation
        with pytest.raises(AttributeError):
            _VALID_META_ENTITY_TYPES.add("new_type")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# validate_meta_entity_type
# ---------------------------------------------------------------------------


class TestValidateMetaEntityType:
    @pytest.mark.parametrize(
        "entity_type",
        ["synthesis_output", "dedup_mapping", "kg_summary"],
    )
    def test_accepts_valid(self, entity_type):
        validate_meta_entity_type(entity_type)  # no exception

    def test_rejects_invalid(self):
        with pytest.raises(ValueError, match="invalid_type"):
            validate_meta_entity_type("invalid_type")

    def test_error_message_contains_allowed(self):
        with pytest.raises(ValueError) as exc_info:
            validate_meta_entity_type("bogus")
        msg = str(exc_info.value)
        assert "dedup_mapping" in msg
        assert "kg_summary" in msg
        assert "synthesis_output" in msg


# ---------------------------------------------------------------------------
# SharedMemoryMetaUpsertPayload
# ---------------------------------------------------------------------------


class TestSharedMemoryMetaUpsertPayload:
    def test_minimal_valid(self):
        payload = SharedMemoryMetaUpsertPayload(
            entity_type="synthesis_output",
            entity_name="acme_corp",
            key="resumo_semanal",
            value={"resumo": "teste"},
        )
        assert payload.entity_type == MetaEntityType.SYNTHESIS_OUTPUT
        assert payload.entity_name == "acme_corp"
        assert payload.key == "resumo_semanal"
        assert payload.value == {"resumo": "teste"}
        # defaults
        assert payload.source == "system"
        assert payload.confidence == 1.0
        assert payload.metadata == {}

    def test_full_valid(self):
        payload = SharedMemoryMetaUpsertPayload(
            entity_type="dedup_mapping",
            entity_name="skill_analise_credito",
            key="mapa_skills_duplicados",
            value={"duplicates": ["skill_a", "skill_b"]},
            source="specialist",
            confidence=0.85,
            metadata={"run_id": "abc123"},
        )
        assert payload.entity_type == MetaEntityType.DEDUP_MAPPING
        assert payload.source == "specialist"
        assert payload.confidence == 0.85
        assert payload.metadata["run_id"] == "abc123"

    def test_confidence_gt_1_rejected(self):
        with pytest.raises(ValidationError, match="confidence"):
            SharedMemoryMetaUpsertPayload(
                entity_type="synthesis_output",
                entity_name="acme_corp",
                key="test",
                value={},
                confidence=1.5,
            )

    def test_confidence_lt_0_rejected(self):
        with pytest.raises(ValidationError, match="confidence"):
            SharedMemoryMetaUpsertPayload(
                entity_type="synthesis_output",
                entity_name="acme_corp",
                key="test",
                value={},
                confidence=-0.1,
            )

    def test_confidence_boundary_values(self):
        # 0.0 and 1.0 should be accepted
        SharedMemoryMetaUpsertPayload(
            entity_type="synthesis_output",
            entity_name="acme_corp",
            key="test_zero",
            value={},
            confidence=0.0,
        )
        SharedMemoryMetaUpsertPayload(
            entity_type="synthesis_output",
            entity_name="acme_corp",
            key="test_one",
            value={},
            confidence=1.0,
        )

    def test_invalid_entity_type_rejected(self):
        with pytest.raises(ValidationError):
            SharedMemoryMetaUpsertPayload(
                entity_type="invalid_type",
                entity_name="acme_corp",
                key="test",
                value={},
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            SharedMemoryMetaUpsertPayload(
                entity_type="synthesis_output",
                # entity_name missing
                key="test",
                value={},
            )

    def test_source_default(self):
        payload = SharedMemoryMetaUpsertPayload(
            entity_type="kg_summary",
            entity_name="summary_ent",
            key="test",
            value={},
        )
        assert payload.source == "system"


# ---------------------------------------------------------------------------
# SharedMemoryMetaEntry
# ---------------------------------------------------------------------------


class TestSharedMemoryMetaEntry:
    def test_full_roundtrip(self):
        client_id = uuid4()
        entry_id = uuid4()
        entry = SharedMemoryMetaEntry(
            id=entry_id,
            client_id=client_id,
            entity_type="dedup_mapping",
            entity_name="skill_analise_credito",
            key="mapa_skills_duplicados",
            value={"duplicates": ["skill_a", "skill_b"]},
            source="specialist",
            confidence=0.85,
            metadata={"run_id": "abc123"},
        )
        assert entry.id == entry_id
        assert entry.client_id == client_id
        assert entry.entity_type == MetaEntityType.DEDUP_MAPPING
        assert entry.entity_name == "skill_analise_credito"
        assert entry.key == "mapa_skills_duplicados"
        assert entry.value == {"duplicates": ["skill_a", "skill_b"]}
        assert entry.source == "specialist"
        assert entry.confidence == 0.85
        assert entry.metadata == {"run_id": "abc123"}

    def test_id_is_optional(self):
        client_id = uuid4()
        entry = SharedMemoryMetaEntry(
            client_id=client_id,
            entity_type="synthesis_output",
            entity_name="test",
            key="test",
            value={},
        )
        assert entry.id is None
        assert entry.created_at is None
        assert entry.updated_at is None

    def test_defaults(self):
        client_id = uuid4()
        entry = SharedMemoryMetaEntry(
            client_id=client_id,
            entity_type="synthesis_output",
            entity_name="test",
            key="test",
            value={},
        )
        assert entry.source == "system"
        assert entry.confidence == 1.0
        assert entry.metadata == {}

    def test_invalid_entity_type_rejected(self):
        client_id = uuid4()
        with pytest.raises(ValidationError):
            SharedMemoryMetaEntry(
                client_id=client_id,
                entity_type="invalid",
                entity_name="test",
                key="test",
                value={},
            )


# ---------------------------------------------------------------------------
# SharedMemoryMetaQuery
# ---------------------------------------------------------------------------


class TestSharedMemoryMetaQuery:
    def test_all_none_defaults(self):
        query = SharedMemoryMetaQuery()
        assert query.entity_type is None
        assert query.key is None

    def test_with_filters(self):
        query = SharedMemoryMetaQuery(
            entity_type="synthesis_output",
            key="resumo_semanal",
        )
        assert query.entity_type == MetaEntityType.SYNTHESIS_OUTPUT
        assert query.key == "resumo_semanal"

    def test_key_only(self):
        query = SharedMemoryMetaQuery(key="resumo_semanal")
        assert query.entity_type is None
        assert query.key == "resumo_semanal"

    def test_entity_type_only(self):
        query = SharedMemoryMetaQuery(entity_type="dedup_mapping")
        assert query.entity_type == MetaEntityType.DEDUP_MAPPING
        assert query.key is None
