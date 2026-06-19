"""Tests for context_schemas — KnowledgeGraphSummary, EntitySummary, AvailableTools."""

from pydantic import ValidationError
import pytest

from blu_models.context_schemas import (
    AvailableTools,
    EntitySummary,
    KnowledgeGraphSummary,
)


# =============================================================================
# EntitySummary
# =============================================================================


class TestEntitySummary:
    """EntitySummary: required fields and type validation."""

    def test_valid_entity_summary(self):
        entity = EntitySummary(name="Acme Corp", type="organization", degree=15)
        assert entity.name == "Acme Corp"
        assert entity.type == "organization"
        assert entity.degree == 15

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            EntitySummary(type="organization", degree=15)
        assert "name" in str(exc_info.value)

    def test_missing_type_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            EntitySummary(name="Acme Corp", degree=15)
        assert "type" in str(exc_info.value)

    def test_missing_degree_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            EntitySummary(name="Acme Corp", type="organization")
        assert "degree" in str(exc_info.value)

    def test_degree_wrong_type_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            EntitySummary(name="Acme Corp", type="organization", degree="many")
        assert "degree" in str(exc_info.value)


# =============================================================================
# KnowledgeGraphSummary
# =============================================================================


class TestKnowledgeGraphSummary:
    """KnowledgeGraphSummary: required fields, defaults, top_entities limit."""

    def test_minimal_instance_defaults(self):
        """Defaults apply when no fields are provided."""
        kg = KnowledgeGraphSummary()
        assert kg.total_documents == 0
        assert kg.total_entities == 0
        assert kg.top_entities == []
        assert kg.last_sync is None
        assert kg.version == 1

    def test_populated_instance(self):
        entities = [
            EntitySummary(name="Acme", type="organization", degree=42),
            EntitySummary(name="Bob", type="person", degree=7),
        ]
        kg = KnowledgeGraphSummary(
            total_documents=150,
            total_entities=80,
            top_entities=entities,
            last_sync="2025-06-19T12:00:00Z",
            version=2,
        )
        assert kg.total_documents == 150
        assert kg.total_entities == 80
        assert kg.top_entities == entities
        assert kg.last_sync == "2025-06-19T12:00:00Z"
        assert kg.version == 2

    def test_total_documents_coerces_string_to_int(self):
        """Pydantic coerces strings to ints (no strict mode)."""
        kg = KnowledgeGraphSummary(total_documents="150")  # noqa
        assert kg.total_documents == 150

    def test_total_documents_list_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGraphSummary(total_documents=[1, 2, 3])
        assert "total_documents" in str(exc_info.value)

    def test_total_entities_coerces_string_to_int(self):
        """Pydantic coerces strings to ints (no strict mode)."""
        kg = KnowledgeGraphSummary(total_entities="80")  # noqa
        assert kg.total_entities == 80

    def test_total_entities_list_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGraphSummary(total_entities=[4, 5])
        assert "total_entities" in str(exc_info.value)

    def test_top_entities_max_length_10(self):
        """Max 10 entities. Pydantic truncates silently? No — raises on too many."""
        entities = [
            EntitySummary(name=f"Entity{i}", type="org", degree=i)
            for i in range(15)
        ]
        with pytest.raises(ValidationError):
            KnowledgeGraphSummary(top_entities=entities)

    def test_top_entities_exactly_10_ok(self):
        entities = [
            EntitySummary(name=f"Entity{i}", type="org", degree=i)
            for i in range(10)
        ]
        kg = KnowledgeGraphSummary(top_entities=entities)
        assert len(kg.top_entities) == 10

    def test_version_defaults_to_1(self):
        kg = KnowledgeGraphSummary()
        assert kg.version == 1

    def test_version_coerces_string_to_int(self):
        """Pydantic coerces strings to ints (no strict mode)."""
        kg = KnowledgeGraphSummary(version="2")  # noqa
        assert kg.version == 2

    def test_version_list_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeGraphSummary(version=[1, 2])

    def test_last_sync_accepts_none(self):
        kg = KnowledgeGraphSummary(last_sync=None)
        assert kg.last_sync is None

    def test_last_sync_accepts_string(self):
        kg = KnowledgeGraphSummary(last_sync="2025-06-19T12:00:00Z")
        assert kg.last_sync == "2025-06-19T12:00:00Z"


# =============================================================================
# AvailableTools
# =============================================================================


class TestAvailableTools:
    """AvailableTools: knowledge_graph_summary optional field."""

    def test_without_kg_summary_defaults_to_none(self):
        tools = AvailableTools()
        assert tools.knowledge_graph_summary is None
        assert tools.tier == "BASIC"
        assert tools.enabled_tool_names == []

    def test_with_kg_summary_populated(self):
        entities = [
            EntitySummary(name="Acme", type="organization", degree=15),
        ]
        kg = KnowledgeGraphSummary(
            total_documents=50,
            total_entities=30,
            top_entities=entities,
            last_sync="2025-06-19T12:00:00Z",
            version=1,
        )
        tools = AvailableTools(knowledge_graph_summary=kg)
        assert tools.knowledge_graph_summary is not None
        assert tools.knowledge_graph_summary.total_documents == 50
        assert tools.knowledge_graph_summary.total_entities == 30
        assert len(tools.knowledge_graph_summary.top_entities) == 1
        assert tools.knowledge_graph_summary.top_entities[0].name == "Acme"

    def test_kg_summary_roundtrip_via_dict(self):
        """KnowledgeGraphSummary survives a dict roundtrip (JSONB storage)."""
        data = {
            "total_documents": 100,
            "total_entities": 60,
            "top_entities": [
                {"name": "Acme", "type": "organization", "degree": 20},
            ],
            "last_sync": "2025-06-19T12:00:00Z",
            "version": 1,
        }
        kg = KnowledgeGraphSummary.model_validate(data)
        assert kg.total_documents == 100
        assert kg.top_entities[0].name == "Acme"

    def test_kg_summary_with_empty_top_entities(self):
        kg = KnowledgeGraphSummary(
            total_documents=0,
            total_entities=0,
            top_entities=[],
        )
        assert kg.top_entities == []
        assert kg.total_documents == 0
